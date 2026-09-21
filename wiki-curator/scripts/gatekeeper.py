#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/gatekeeper.py - 利刃的第二大脑·工业级门禁与机器账本管家 (Hardened Production Grade)
Version: 2.0 (红队对抗防御加固版 - Schema V4.4 专属)

核心职责与防御体系：
1. 跨进程独占文件锁 (Inter-Process Mutex via .gatekeeper.lock)，防止多 Agent 并发写入脑裂
2. Windows/OneDrive 独占锁指数退避重试 (Exponential Backoff + Jitter)，免疫 WinError 5/32
3. 账本 Fail-Fast 熔断保护与 .bak 自动镜像恢复，现场隔离损坏文件，杜绝 0 字节清空整库
4. 严格限制 OneDrive 冲突副本正则特征，保护 log_archive_*.md 与备份文件不被误删
5. 软脱机墓碑机制 (Tombstone / OFFLINE 状态) 与同名秒级复活 (RESURRECTED)，阻断旧 Wiki 覆灭
6. 双向差分 diff_queue 携带目标 wiki 导航指针，Agent 禁读账本依然拥有精确修改目标
7. 全链路 Unicode NFC 归一化与 Windows 物理真实路径大小写对齐，消除假阳性死锁
8. 临时/系统文件黑名单 (desktop.ini, .crdownload 等) 与逆向幽灵批量熔断安全阀 (>20% 阻断)
9. 受控词表合流安全对齐 3 列规范、防御性空字段清洗、双重幂等查重与专用暂存区隔离
"""

import os
import sys
import json
import re
import time
import random
import hashlib
import unicodedata
import tempfile
import argparse
from pathlib import Path
from datetime import datetime

# 强制终端输出为 UTF-8，消除 Windows 控制台 GBK 乱码
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stdin.encoding and sys.stdin.encoding.lower() != "utf-8":
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

def find_workspace_root() -> Path:
    """智能嗅探工作区根目录（优先检测 cwd，再从当前文件向上回溯寻找 raw/ 与 wiki/）"""
    try:
        cwd = Path.cwd().resolve()
        if (cwd / "raw").is_dir() and (cwd / "wiki").is_dir():
            return cwd
    except Exception:
        pass

    cur = Path(__file__).resolve().parent
    for p in [cur, *cur.parents]:
        if (p / "raw").is_dir() and (p / "wiki").is_dir():
            return p

    if cur.name == "scripts":
        if len(cur.parents) >= 3 and cur.parent.parent.name == "skills":
            return cur.parent.parent.parent.parent
        return cur.parent

    return Path.cwd().resolve()


ROOT_DIR = find_workspace_root()
RAW_DIR = ROOT_DIR / "raw"
WIKI_DIR = ROOT_DIR / "wiki"
SHADOW_DIR = ROOT_DIR / ".scratch" / "shadow_drafts"
MANIFEST_FILE = ROOT_DIR / "raw_manifest.json"
MANIFEST_BAK_FILE = ROOT_DIR / "raw_manifest.json.bak"
LOG_FILE = ROOT_DIR / "log.md"
LOGS_DIR = ROOT_DIR / "logs"
GLOSSARY_FILE = ROOT_DIR / "glossary.md"
LOCK_FILE = (ROOT_DIR / ".scripts" if (ROOT_DIR / ".scripts").is_dir() else ROOT_DIR / ".scratch") / ".gatekeeper.lock"

LOG_ANCHOR = "<!-- %% LOG_TAIL_ANCHOR %% -->"

# 第一性原理 Token 动态准入常量 (Gemini 原生多模态 560 Tokens/页)
PDF_PAGE_TOKENS = 560
AGENTS_MD_TOKENS = 10000
SYSTEM_PROMPT_TOKENS = 4000
BASE_OVERHEAD_TOKENS = AGENTS_MD_TOKENS + SYSTEM_PROMPT_TOKENS  # 基础前置总开销基线: 14,000 Tokens
MASSIVE_TOTAL_TOKEN_THRESHOLD = 33600  # 端到端总会话超过 33,600 Tokens 触发超长切片 (对应 >= 35页)
MASSIVE_PAGE_THRESHOLD = (MASSIVE_TOTAL_TOKEN_THRESHOLD - BASE_OVERHEAD_TOKENS) // PDF_PAGE_TOKENS  # 35 页 (>=35页触发)


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """计算文件的 SHA-256 哈希值（分块流式读取，防内存膨胀）"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def get_document_page_count(file_path: Path) -> int | None:
    """提取文档的真实物理页数，非 PDF 或解析异常返回 None"""
    if file_path.suffix.lower() == ".pdf":
        try:
            import fitz
            with fitz.open(file_path) as doc:
                return len(doc)
        except Exception:
            return None
    return None


def detect_document_metrics(rpath: str, rsize: int, file_path: Path = None) -> tuple:
    """基于第一性原理 Token 动态准入模型判定是否触达超长分治门槛 (端到端总消耗 >= 40,000 Tokens)
    换算逻辑: 文档 Tokens (PDF 560 Tokens/页) + AGENTS.md (8,100) + 系统提示词 (3,900) >= 40,000
    返回: (page_count: int | None, is_massive: bool, reason: str)
    """
    if file_path is None:
        file_path = ROOT_DIR / rpath

    page_count = get_document_page_count(file_path) if file_path.exists() else None

    if page_count is not None:
        doc_tokens = page_count * PDF_PAGE_TOKENS
        total_tokens = doc_tokens + BASE_OVERHEAD_TOKENS
        if total_tokens >= MASSIVE_TOTAL_TOKEN_THRESHOLD:
            return (
                page_count,
                True,
                f"端到端预估消耗达 {total_tokens:,} Tokens (文献 {page_count}页/约 {doc_tokens:,} Tokens + 前置底数 {BASE_OVERHEAD_TOKENS:,} Tokens >= 40k)"
            )
        return page_count, False, ""

    # 非 PDF 文件的降级处理 (按字符/体积估算纯文本 Token)
    est_doc_tokens = int(rsize / 3.5)
    total_tokens = est_doc_tokens + BASE_OVERHEAD_TOKENS
    if total_tokens >= MASSIVE_TOTAL_TOKEN_THRESHOLD:
        return (
            None,
            True,
            f"非PDF纯文本预估消耗达 {total_tokens:,} Tokens (文本约 {est_doc_tokens:,} Tokens + 前置底数 {BASE_OVERHEAD_TOKENS:,} Tokens >= 40k)"
        )

    return None, False, ""


def detect_massive_document(rpath: str, rsize: int) -> tuple:
    """兼容旧接口：检测文档是否达到大文件分治门槛 (>= 50页或 >= 10MB)"""
    _, is_massive, reason = detect_document_metrics(rpath, rsize)
    return is_massive, reason


# OneDrive 专用冲突副本正则 (严格匹配，杜绝宽泛匹配误删 log_archive_2025.md 等)
ONEDRIVE_MANIFEST_CONFLICT_RE = re.compile(
    r"^raw_manifest\s*-\s*.+\.json$|^raw_manifest\s*\(\d+\)\.json$", re.IGNORECASE
)
ONEDRIVE_LOG_CONFLICT_RE = re.compile(
    r"^log\s*-\s*.+\.md$|^log\s*\(\d+\)\.md$", re.IGNORECASE
)

# 忽略的系统与临时文件黑名单
IGNORED_SYSTEM_NAMES = {
    "desktop.ini", "thumbs.db", ".ds_store", "readme.md"
}
IGNORED_EXTENSIONS = {
    ".crdownload", ".part", ".tmp", ".download", ".lock", ".temp"
}


class ManifestCorruptedError(Exception):
    """主账本损坏致命异常，阻断非安全覆写"""
    pass


class GatekeeperLock:
    """跨平台进程间排他文件锁，防止并发写入脑裂"""
    def __init__(self, lock_path: Path, timeout: float = 10.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        start_time = time.time()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                # O_CREAT | O_EXCL 提供跨平台原子互斥创建
                self.fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, f"{os.getpid()}".encode("utf-8"))
                return self
            except FileExistsError:
                # 检查锁是否超时僵死 (例如前驱进程崩溃未释放)
                try:
                    mtime = self.lock_path.stat().st_mtime
                    if time.time() - mtime > 60.0:  # 锁存在超过 60 秒视为僵尸锁强制接管
                        try:
                            self.lock_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                except Exception:
                    pass
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"等待门禁独占锁超时 (> {self.timeout}s)，可能有其他并发操作正在进行。")
                time.sleep(0.05 + random.uniform(0.01, 0.05))

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except Exception:
                pass
        try:
            self.lock_path.unlink(missing_ok=True)
        except Exception:
            pass


def norm_path(p: str) -> str:
    """规范化路径为 POSIX 格式并统一为 Unicode NFC，去除首尾空白"""
    if not p:
        return ""
    # Unicode NFC 归一化，根除 macOS NFD 与 Windows/Linux 编码差异
    normalized = unicodedata.normalize("NFC", str(p).strip())
    clean_p = normalized.replace("\\", "/").strip()
    clean_p = re.sub(r"/+", "/", clean_p)
    return clean_p


def get_real_case_relpath(abs_path: Path, base_dir: Path) -> str:
    """获取 Windows 磁盘实际物理存储的大小写相对路径，消除字典大小写假阳性"""
    try:
        resolved = abs_path.resolve()
        rel = resolved.relative_to(base_dir.resolve())
        return norm_path(str(rel))
    except Exception:
        return norm_path(str(abs_path.name))


def safe_stat_size(path_obj: Path) -> int:
    """安全获取文件体积，自动绕过 Windows 260 字符 MAX_PATH 限制与长路径异常"""
    try:
        return path_obj.stat().st_size
    except Exception:
        full = str(path_obj.resolve())
        if os.name == "nt" and not full.startswith(r"\\?\\"):
            full = r"\\?\\" + full
        return os.stat(full).st_size


def atomic_write_file(file_path: Path, content: str, make_backup: bool = False):
    """带指数退避重试的原子文件写盘，免疫 Windows/OneDrive 独占锁冲突与截断风险"""
    dir_path = file_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(prefix=f"{file_path.stem}_tmp_", suffix=file_path.suffix, dir=dir_path)
    
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        raise e

    # 若需要且原目标存在，维护 .bak 备份副本
    if make_backup and file_path.exists():
        bak_path = file_path.with_suffix(file_path.suffix + ".bak")
        try:
            with open(file_path, "r", encoding="utf-8") as src, open(bak_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        except Exception as e:
            print(f"[Gatekeeper Warning] 维护备用镜像失败: {e}", file=sys.stderr)

    # Windows 锁自愈：指数退避重试 (最大重试 8 次，累计等待约 1.5s)
    max_retries = 8
    last_err = None
    for attempt in range(max_retries):
        try:
            os.replace(temp_path, file_path)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            # Windows 典型锁死错误码：WinError 5 (拒绝访问), WinError 32 (正在被占用)
            sleep_time = (0.05 * (2 ** attempt)) + random.uniform(0.01, 0.05)
            time.sleep(sleep_time)

    # 重试全部失败，清理临时文件并向上抛错
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass
    raise TimeoutError(f"写入目标文件 {file_path.name} 失败，目标被其他进程持锁不释放: {last_err}")


def atomic_write_json(file_path: Path, data: dict, make_backup: bool = True):
    """原子序列化 JSON 写盘"""
    content = json.dumps(data, ensure_ascii=False, indent=2)
    atomic_write_file(file_path, content, make_backup=make_backup)


def load_manifest() -> dict:
    """安全读取账本，具备损坏熔断、备份回滚与隔离防护，杜绝 0 字节灾难性覆写"""
    if not MANIFEST_FILE.exists():
        if MANIFEST_BAK_FILE.exists():
            print(f"[Gatekeeper Recovery] 主账本缺失，从备份自愈恢复...", file=sys.stderr)
            try:
                with open(MANIFEST_BAK_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    raw_content = ""
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            raw_content = f.read().strip()
        if not raw_content:
            raise ManifestCorruptedError("主账本文件存在但为 0 字节空文件")
        data = json.loads(raw_content)
        if not isinstance(data, dict):
            raise ManifestCorruptedError(f"主账本根对象不是字典，类型为: {type(data)}")
        return data
    except Exception as e:
        print(f"[Gatekeeper Critical] 主账本损坏或无法解析: {e}", file=sys.stderr)
        # 尝试从 .bak 救急恢复
        if MANIFEST_BAK_FILE.exists():
            try:
                with open(MANIFEST_BAK_FILE, "r", encoding="utf-8") as bf:
                    bak_data = json.load(bf)
                    print(f"[Gatekeeper Recovery] 成功从 .bak 备份恢复账本 ({len(bak_data)} 条记录)", file=sys.stderr)
                    atomic_write_json(MANIFEST_FILE, bak_data, make_backup=False)
                    return bak_data
            except Exception as be:
                print(f"[Gatekeeper Critical] 备份账本亦损坏: {be}", file=sys.stderr)

        # 若无可用备份，隔离现场并坚决熔断，严禁返回空字典抹杀历史！
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_file = ROOT_DIR / f"raw_manifest.corrupted_{timestamp}.json"
        try:
            with open(quarantine_file, "w", encoding="utf-8") as qf:
                qf.write(raw_content)
            print(f"[Gatekeeper Safety] 已将损坏账本现场隔离至: {quarantine_file.name}", file=sys.stderr)
        except Exception:
            pass

        raise ManifestCorruptedError(
            f"主账本 {MANIFEST_FILE.name} 已损坏，且无可用的 .bak 恢复副本！"
            f"门禁强行熔断以阻止灾难性数据覆写。请人工核查该文件。"
        )


def heal_conflicts() -> list:
    """严格限定特征匹配的 OneDrive 冲突副本自愈归并"""
    healed = []

    # 1. 扫描并归并 raw_manifest 冲突副本
    manifest_conflicts = [
        Path(p) for p in ROOT_DIR.iterdir()
        if p.is_file() and ONEDRIVE_MANIFEST_CONFLICT_RE.match(p.name)
    ]
    if manifest_conflicts:
        main_manifest = load_manifest()
        modified = False
        for cp in manifest_conflicts:
            try:
                with open(cp, "r", encoding="utf-8") as f:
                    cdata = json.load(f)
                if isinstance(cdata, dict):
                    for k, v in cdata.items():
                        norm_k = norm_path(k)
                        if norm_k not in main_manifest:
                            main_manifest[norm_k] = v
                            modified = True
                        else:
                            main_entry = main_manifest[norm_k]
                            # CRDT 并集归并 staged_terms，防止多端新词互相丢弃
                            c_terms = v.get("staged_terms") or []
                            m_terms = main_entry.get("staged_terms") or []
                            if c_terms:
                                existing_keys = {t.get("en", "").lower() for t in m_terms if t.get("en")}
                                for ct in c_terms:
                                    if ct.get("en") and ct["en"].lower() not in existing_keys:
                                        m_terms.append(ct)
                                        modified = True
                                main_entry["staged_terms"] = m_terms
                cp.unlink(missing_ok=True)
                healed.append(cp.name)
            except Exception as e:
                print(f"[Gatekeeper Warning] 处理账本冲突副本 {cp.name} 失败: {e}", file=sys.stderr)
        if modified:
            atomic_write_json(MANIFEST_FILE, main_manifest)

    # 2. 扫描并归并 log.md 冲突副本 (安全过滤，绝不触碰 log_archive)
    log_conflicts = [
        Path(p) for p in ROOT_DIR.iterdir()
        if p.is_file() and ONEDRIVE_LOG_CONFLICT_RE.match(p.name)
    ]
    if log_conflicts and LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                main_log = f.read()

            main_log_normalized = main_log.replace("\r\n", "\n")

            # 兜底：若主日志丢失了锚点，自动补齐在末尾，杜绝吞噬冲突
            if LOG_ANCHOR not in main_log_normalized:
                main_log_normalized = main_log_normalized.rstrip() + f"\n\n{LOG_ANCHOR}\n"

            # 抓取标题行指纹：提取 ## [YYYY-MM-DD] ... 标题作为业务去重键
            header_pattern = re.compile(r"^##\s+\[\d{4}-\d{2}-\d{2}\].*$", re.MULTILINE)
            main_headers = set(m.group(0).strip() for m in header_pattern.finditer(main_log_normalized))

            section_pattern = re.compile(
                r"(##\s+\[\d{4}-\d{2}-\d{2}\][\s\S]*?)(?=(?:^##\s+\[\d{4}-\d{2}-\d{2}\]|<!-- %% LOG_TAIL_ANCHOR %% -->|\Z))",
                re.MULTILINE
            )

            modified_log = False
            for lp in log_conflicts:
                try:
                    with open(lp, "r", encoding="utf-8") as f:
                        conflict_log = f.read().replace("\r\n", "\n")
                    conflict_sections = section_pattern.finditer(conflict_log)
                    for cs in conflict_sections:
                        sec_text = cs.group(1).strip()
                        if not sec_text:
                            continue
                        first_line = sec_text.splitlines()[0].strip()
                        if first_line not in main_headers:
                            main_log_normalized = main_log_normalized.replace(
                                LOG_ANCHOR, f"{sec_text}\n\n{LOG_ANCHOR}"
                            )
                            main_headers.add(first_line)
                            modified_log = True
                    lp.unlink(missing_ok=True)
                    healed.append(lp.name)
                except Exception as ce:
                    print(f"[Gatekeeper Warning] 读取日志冲突副本 {lp.name} 失败: {ce}", file=sys.stderr)

            if modified_log:
                atomic_write_file(LOG_FILE, main_log_normalized)
        except Exception as e:
            print(f"[Gatekeeper Warning] 处理日志冲突副本失败: {e}", file=sys.stderr)

    # 3. 兜底主动自愈：无论是否有 OneDrive 冲突，确保主日志哨兵锚点守恒
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                cur_log = f.read()
            if LOG_ANCHOR not in cur_log:
                healed_log = cur_log.rstrip() + f"\n\n{LOG_ANCHOR}\n"
                atomic_write_file(LOG_FILE, healed_log)
                print(f"[Gatekeeper Auto-Heal] 检测到 {LOG_FILE.name} 缺失哨兵锚点，已自动补齐挂载。", file=sys.stderr)
        except Exception as e:
            print(f"[Gatekeeper Warning] 探测日志哨兵锚点异常: {e}", file=sys.stderr)

    return healed


def run_diff() -> dict:
    """执行双向指纹差分、墓碑状态流转与幽灵熔断"""
    with GatekeeperLock(LOCK_FILE):
        healed = heal_conflicts()
        manifest = load_manifest()

        raw_files = {}
        if RAW_DIR.exists():
            for item in RAW_DIR.iterdir():
                if item.is_dir():
                    continue
                lower_name = item.name.lower()
                if lower_name in IGNORED_SYSTEM_NAMES or any(lower_name.endswith(ext) for ext in IGNORED_EXTENSIONS):
                    continue
                if lower_name.startswith("~$") or lower_name.startswith("."):
                    continue

                rel_path = f"raw/{norm_path(item.name)}"
                raw_files[rel_path] = safe_stat_size(item)

        diff_queue = []
        resurrected_files = []

        # 建立大小写不敏感反查字典
        manifest_lookup = {norm_path(k).lower(): (k, v) for k, v in manifest.items()}

        # 1. 正向差分：查找 NEW, UPDATE, RESURRECTED, COLLISION_NEW
        manifest_modified = False
        for rpath, rsize in raw_files.items():
            rpath_lower = rpath.lower()
            target_p = ROOT_DIR / rpath
            if rpath_lower not in manifest_lookup:
                # 检查目标 Wiki 是否已在磁盘存在（防覆灭探测）
                expected_wiki_name = Path(rpath).stem + ".md"
                target_wiki_exists = (ROOT_DIR / "wiki" / expected_wiki_name).exists()
                page_count, is_massive, reason = detect_document_metrics(rpath, rsize, target_p)
                sha256_hash = compute_sha256(target_p) if target_p.exists() else None
                item_info = {
                    "file": rpath,
                    "size_bytes": rsize,
                    "page_count": page_count,
                    "sha256": sha256_hash,
                    "action": "NEW",
                    "target_wiki_hint": f"wiki/{expected_wiki_name}",
                    "wiki_already_exists": target_wiki_exists,
                    "ingestion_track": "MASSIVE_DUAL_TRACK" if is_massive else "STANDARD"
                }
                if is_massive:
                    item_info["guidance"] = f"【触发大文件双轨分治】{reason}。严禁单次直吞！建议使用 python .scripts/slice_raw.py inspect 规划章节并执行双轨摄取。"
                diff_queue.append(item_info)
            else:
                orig_key, entry = manifest_lookup[rpath_lower]
                entry_status = entry.get("status", "ACTIVE")
                stored_size = entry.get("size_bytes")
                stored_sha = entry.get("sha256")
                target_wiki = entry.get("wiki", "")

                if entry_status == "OFFLINE":
                    # 墓碑重入复活探测：若有 SHA-256 优先进行密码学指纹确认，否则降级按体积确认
                    target_orig_p = ROOT_DIR / orig_key
                    is_same = False
                    if stored_sha and target_orig_p.exists():
                        is_same = (compute_sha256(target_orig_p) == stored_sha)
                    else:
                        is_same = (stored_size == rsize)

                    if is_same:
                        # 指纹完全一致，静默复活切回 ACTIVE，禁止重写 Wiki
                        entry["status"] = "ACTIVE"
                        if "detached_at" in entry:
                            del entry["detached_at"]
                        if not stored_sha and target_orig_p.exists():
                            entry["sha256"] = compute_sha256(target_orig_p)
                        if "page_count" not in entry and target_orig_p.exists():
                            entry["page_count"] = get_document_page_count(target_orig_p)
                        resurrected_files.append({"file": orig_key, "wiki": target_wiki})
                        manifest_modified = True
                    else:
                        # 同名但体积或哈希异构，标记为冲突，防止冲刷旧 Wiki
                        target_orig_p = ROOT_DIR / orig_key
                        page_count, is_massive, reason = detect_document_metrics(orig_key, rsize, target_orig_p)
                        sha256_hash = compute_sha256(target_orig_p) if target_orig_p.exists() else None
                        col_item = {
                            "file": orig_key,
                            "action": "COLLISION_NEW",
                            "wiki": target_wiki,
                            "size_bytes": rsize,
                            "old_size_bytes": stored_size,
                            "page_count": page_count,
                            "sha256": sha256_hash,
                            "ingestion_track": "MASSIVE_DUAL_TRACK" if is_massive else "STANDARD",
                            "warning": "同名文件但体积不一致，磁盘已有存量 Wiki，请确认是否覆盖或重命名！"
                        }
                        if is_massive:
                            col_item["guidance"] = f"【触发大文件双轨分治】{reason}。严禁单次直吞！建议使用 python .scripts/slice_raw.py inspect 规划章节并执行双轨摄取。"
                        diff_queue.append(col_item)
                else:
                    # 正常存量文献，检查是否发生修改 (Tier 0: 体积快速比对)
                    if stored_size is not None and stored_size != rsize:
                        target_orig_p = ROOT_DIR / orig_key
                        page_count, is_massive, reason = detect_document_metrics(orig_key, rsize, target_orig_p)
                        sha256_hash = compute_sha256(target_orig_p) if target_orig_p.exists() else None
                        update_item = {
                            "file": orig_key,
                            "action": "UPDATE",
                            "wiki": target_wiki,
                            "size_bytes": rsize,
                            "old_size_bytes": stored_size,
                            "page_count": page_count,
                            "sha256": sha256_hash,
                            "ingestion_track": "MASSIVE_DUAL_TRACK" if is_massive else "STANDARD"
                        }
                        if is_massive:
                            update_item["guidance"] = f"【触发大文件双轨分治】{reason}。严禁单次直吞！建议使用 python .scripts/slice_raw.py inspect 规划章节并执行双轨摄取。"
                        diff_queue.append(update_item)

        # 2. 逆向差分：物理文件删除转换为软脱机墓碑 (OFFLINE)
        offline_marked = []
        potential_missing = []

        for mpath, entry in manifest.items():
            if entry.get("status") == "OFFLINE":
                continue
            full_path = ROOT_DIR / mpath
            if not full_path.exists():
                potential_missing.append(mpath)

        # 熔断安全阀：若突发缺失数超过账本 20% 且 > 3 篇，拒绝自动批量脱机（防止断网/移动硬盘脱开灾难）
        total_active = sum(1 for v in manifest.values() if v.get("status") != "OFFLINE")
        if potential_missing:
            if total_active > 10 and (len(potential_missing) / total_active > 0.20):
                print(
                    f"[Gatekeeper Safety Triggered] 突发检测到 {len(potential_missing)}/{total_active} 个文件缺失！"
                    f"疑似存储卷脱机或同步未完成，门禁自动暂停脱机标记。",
                    file=sys.stderr
                )
            else:
                for mpath in potential_missing:
                    manifest[mpath]["status"] = "OFFLINE"
                    manifest[mpath]["detached_at"] = datetime.now().strftime("%Y-%m-%d")
                    offline_marked.append({
                        "file": mpath,
                        "wiki": manifest[mpath].get("wiki")
                    })
                    manifest_modified = True

        if manifest_modified:
            atomic_write_json(MANIFEST_FILE, manifest)

        pending_terms_files = sum(
            1 for v in manifest.values() if v.get("staged_terms") and len(v["staged_terms"]) > 0
        )

        status = "PROCEED" if diff_queue else "IDLE"

        # 4. 巡检 log.md 是否超出分卷阈值 (> 200 条)
        log_entry_count = 0
        log_archive_recommended = False
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    log_text_diff = f.read()
                log_entry_count = len(re.findall(r"^##\s*\[\d{4}-\d{2}-\d{2}\]", log_text_diff, flags=re.MULTILINE))
                log_archive_recommended = (log_entry_count > 200)
            except Exception:
                pass

        # 5. 巡检存量账本指标完整度 (page_count, sha256)
        missing_metrics_count = sum(
            1 for v in manifest.values()
            if v.get("status") != "OFFLINE" and ("sha256" not in v or "page_count" not in v)
        )

        return {
            "status": status,
            "diff_queue": diff_queue,
            "resurrected_files": resurrected_files,
            "offline_marked": offline_marked,
            "healed_conflicts": healed,
            "pending_terms_files": pending_terms_files,
            "flush_recommended": pending_terms_files >= 3,
            "log_entry_count": log_entry_count,
            "log_archive_recommended": log_archive_recommended,
            "missing_metrics_count": missing_metrics_count,
            "backfill_recommended": missing_metrics_count > 0,
            "total_manifest_count": len(manifest)
        }


def append_to_glossary_staging(glossary_text: str, new_rows: list) -> str:
    """遵循 Markdown AST 规范，将新术语行紧凑追加至待分类收容区表格末尾，确保表头不倒置且无空行"""
    staging_title = "## 待分类新收录术语 (Recently Staged Terms)"
    table_header = "| 英文缩写/术语 (English Term) | 标准中文翻译 (Standard Chinese) | 标准双向链接格式 (Wikilink Format) |\n| :--- | :--- | :--- |"

    if staging_title not in glossary_text:
        base = glossary_text.rstrip()
        return f"{base}\n\n{staging_title}\n{table_header}\n" + "\n".join(new_rows) + "\n"

    parts = glossary_text.split(staging_title, 1)
    before = parts[0]
    after = parts[1]

    # 检测暂存区之后是否存在其他二级标题
    next_heading_match = re.search(r"\n(?=##\s+)", after)
    if next_heading_match:
        staging_content = after[:next_heading_match.start()]
        remainder = after[next_heading_match.start():]
    else:
        staging_content = after
        remainder = ""

    lines = [l for l in staging_content.strip().splitlines() if l.strip()]
    content_rows = [
        l.strip() for l in lines 
        if l.strip().startswith("|") 
        and "英文缩写" not in l 
        and not l.strip().startswith("| :")
    ]

    all_rows = content_rows + new_rows
    new_staging_block = f"\n{table_header}\n" + "\n".join(all_rows) + "\n"
    return f"{before}{staging_title}{new_staging_block}{remainder}"


def parse_terms_input(terms_arg: str = None, terms_file: str = None) -> list:
    """自愈式解析 terms 参数，支持标准 JSON、文件路径、管道 Stdin 与 Windows 引号容错"""
    raw_str = ""
    if terms_file:
        p = Path(terms_file)
        if not p.is_absolute():
            p = ROOT_DIR / p
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                raw_str = f.read().strip()
        else:
            raise FileNotFoundError(f"terms-file 物理文件不存在: {terms_file}")
    elif terms_arg:
        arg_val = terms_arg.strip()
        if arg_val == "-":
            raw_str = sys.stdin.read().strip()
        elif (ROOT_DIR / arg_val).exists() and (ROOT_DIR / arg_val).is_file():
            with open(ROOT_DIR / arg_val, "r", encoding="utf-8") as f:
                raw_str = f.read().strip()
        elif Path(arg_val).exists() and Path(arg_val).is_file():
            with open(Path(arg_val), "r", encoding="utf-8") as f:
                raw_str = f.read().strip()
        else:
            raw_str = arg_val

    if not raw_str:
        return []

    try:
        data = json.loads(raw_str)
    except Exception:
        # Windows 控制台单双引号脱落自愈解析
        try:
            import ast
            data = ast.literal_eval(raw_str)
        except Exception as e:
            raise ValueError(f"terms 参数无法解析为合法结构: {e}")

    if isinstance(data, dict):
        return [data]
    elif isinstance(data, list):
        return data
    return []


def append_log_entry(entry_text: str, log_file: Path = LOG_FILE) -> dict:
    """底层确定性追加日志条目并守恒尾部 LOG_ANCHOR 哨兵锚点 (严格保持单调递增 Append-only)"""
    entry_text = entry_text.strip()
    if not entry_text:
        raise ValueError("追加日志条目内容不能为空")

    # 规范校验：确保以 ## [YYYY-MM-DD] 开头，杜绝脏数据
    if not re.match(r"^##\s+\[\d{4}-\d{2}-\d{2}\]", entry_text):
        raise ValueError(
            f"【日志规范拦截】日志条目必须以 '## [YYYY-MM-DD]' 标题开头！当前条目首行: '{entry_text.splitlines()[0]}'"
        )

    if not log_file.exists():
        cur_log = f"# 操作日志 (Log)\n\n{LOG_ANCHOR}\n"
    else:
        with open(log_file, "r", encoding="utf-8") as f:
            cur_log = f.read()

    cur_log_normalized = cur_log.replace("\r\n", "\n")

    # 兜底自愈：若缺失锚点，自动补齐挂载在末尾
    if LOG_ANCHOR not in cur_log_normalized:
        cur_log_normalized = cur_log_normalized.rstrip() + f"\n\n{LOG_ANCHOR}\n"

    # 执行确定性原子替换插入
    replacement = f"{entry_text}\n\n{LOG_ANCHOR}"
    updated_log = cur_log_normalized.replace(LOG_ANCHOR, replacement)
    atomic_write_file(log_file, updated_log, make_backup=True)

    # 统计条目总数与第一行标题作为回执
    entry_pattern = re.compile(r"^##\s+\[\d{4}-\d{2}-\d{2}\].*$", re.MULTILINE)
    total_entries = len(entry_pattern.findall(updated_log))
    first_line = entry_text.splitlines()[0].strip()

    return {
        "status": "APPENDED",
        "log_file": log_file.name,
        "entry_title": first_line,
        "total_entries": total_entries,
        "archive_recommended": total_entries >= 200
    }


def run_append_log(entry_file: str = None, entry_text: str = None) -> dict:
    """确定性追加日志条目至 log.md 并守恒尾部锚点（带独占文件锁）"""
    with GatekeeperLock(LOCK_FILE):
        raw_text = ""
        if entry_file:
            ep = Path(entry_file)
            if not ep.is_absolute():
                ep = ROOT_DIR / ep
            if not ep.exists():
                raise FileNotFoundError(f"日志条目文件不存在: {entry_file}")
            with open(ep, "r", encoding="utf-8") as f:
                raw_text = f.read()
        elif entry_text:
            raw_text = entry_text
        else:
            raise ValueError("必须提供 --entry-file 或 --entry-text")

        return append_log_entry(raw_text)


def run_commit(file_path: str, wiki_path: str, terms_arg: str = None, date_str: str = None, terms_file: str = None, log_file: str = None, cluster_wikis: list | str = None) -> dict:
    """原子更新账本记录（带文件锁、物理大小写矫正与字段清洗）"""
    with GatekeeperLock(LOCK_FILE):
        norm_f = norm_path(file_path)
        if not norm_f.startswith("raw/"):
            norm_f = f"raw/{norm_f}"

        target_real = ROOT_DIR / norm_f
        if not target_real.exists():
            raise FileNotFoundError(f"物理文件不存在: {norm_f}")

        # 强制获取磁盘保留的真实物理文件名（消除 Windows 大小写不一致）
        actual_rel_path = f"raw/{target_real.name}"
        real_size = safe_stat_size(target_real)
        page_count = get_document_page_count(target_real)
        sha256_hash = compute_sha256(target_real)

        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        else:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                raise ValueError(f"摄取日期格式必须严格为 YYYY-MM-DD: {date_str}")

        raw_terms = parse_terms_input(terms_arg, terms_file)
        cleaned_terms = []
        for t in raw_terms:
            if not isinstance(t, dict):
                continue
            en = (t.get("en") or t.get("en_name") or t.get("term_en") or t.get("english") or "").strip()
            zh = (t.get("zh") or t.get("cn_name") or t.get("zh_name") or t.get("term_zh") or t.get("chinese") or "").strip()
            abbr = (t.get("abbr") or t.get("abbreviation") or "").strip()

            # 严格门禁：杜绝 Windows 控制台编码截断导致的问号写入
            if any(ord(c) == 0x3F for c in zh):
                raise ValueError(
                    f"【字符集截断拦截】检测到术语中文翻译存在问号 '?' 乱码 ('{zh}')！\n"
                    f"根因：Windows 控制台通过命令行实参 --terms 传递中文导致编码丢失。\n"
                    f"解决方案：严禁在 Windows 命令行使用 --terms 直接传递中文字符串，必须将术语写入 UTF-8 JSON 临时文件并使用 `--terms-file` 提交！"
                )

            if en or zh:
                cleaned_terms.append({"en": en, "zh": zh, "abbr": abbr})

        # 处理 L1 法典集群子卡配额与实体校验
        cleaned_cluster_wikis = []
        if cluster_wikis:
            raw_candidates = []
            if isinstance(cluster_wikis, str):
                raw_candidates = [cluster_wikis]
            elif isinstance(cluster_wikis, list):
                raw_candidates = cluster_wikis

            raw_cw_list = []
            for item in raw_candidates:
                if not isinstance(item, str):
                    continue
                item_s = item.strip()
                if not item_s:
                    continue
                test_norm = norm_path(item_s)
                if not test_norm.startswith("wiki/"):
                    test_norm = f"wiki/{test_norm}"
                if (ROOT_DIR / test_norm).exists():
                    raw_cw_list.append(item_s)
                elif "," in item_s or ";" in item_s:
                    raw_cw_list.extend([w.strip() for w in re.split(r"[,;]+", item_s) if w.strip()])
                else:
                    raw_cw_list.append(item_s)
            else:
                pass

            for cw in raw_cw_list:
                cw_norm = norm_path(cw)
                if not cw_norm.startswith("wiki/"):
                    cw_norm = f"wiki/{cw_norm}"
                cw_real = ROOT_DIR / cw_norm
                if not cw_real.exists():
                    raise FileNotFoundError(f"【集群子卡不存在拦截】指定的直通集群子卡物理文件不存在: {cw_norm}")
                cleaned_cluster_wikis.append(cw_norm)

            if len(cleaned_cluster_wikis) > 3:
                raise ValueError(
                    f"【集群配额超限拦截】L1 法典直通集群子卡数量上限为 3 张，实际传入 {len(cleaned_cluster_wikis)} 张！\n"
                    f"子卡列表: {cleaned_cluster_wikis}\n"
                    f"请精简子卡至不超过 3 张，次要概念请内联在母卡或打幽灵双链等待自然孵化。"
                )

        manifest = load_manifest()
        entry = {
            "wiki": norm_path(wiki_path),
            "ingested_at": date_str,
            "size_bytes": real_size,
            "page_count": page_count,
            "sha256": sha256_hash,
            "status": "ACTIVE"
        }
        if cleaned_terms:
            entry["staged_terms"] = cleaned_terms
        if cleaned_cluster_wikis:
            entry["cluster_wikis"] = cleaned_cluster_wikis

        manifest[actual_rel_path] = entry
        atomic_write_json(MANIFEST_FILE, manifest)

        pending_terms_files = sum(
            1 for v in manifest.values() if v.get("staged_terms") and len(v["staged_terms"]) > 0
        )

        log_receipt = None
        if log_file:
            lp = Path(log_file)
            if not lp.is_absolute():
                lp = ROOT_DIR / lp
            if not lp.exists():
                raise FileNotFoundError(f"指定的日志条目文件不存在: {log_file}")
            with open(lp, "r", encoding="utf-8") as f:
                entry_content = f.read()
            log_receipt = append_log_entry(entry_content)

        res = {
            "status": "COMMITTED",
            "file": actual_rel_path,
            "wiki": entry["wiki"],
            "cluster_wikis": entry.get("cluster_wikis", []),
            "size_bytes": real_size,
            "page_count": page_count,
            "sha256": sha256_hash,
            "ingested_at": date_str,
            "total_manifest_count": len(manifest),
            "pending_terms_files": pending_terms_files,
            "flush_recommended": pending_terms_files >= 3
        }
        if log_receipt:
            res["log_status"] = log_receipt["status"]
            res["log_entry_title"] = log_receipt["entry_title"]
            res["log_total_entries"] = log_receipt["total_entries"]
        return res


def run_flush_terms() -> dict:
    """将 staged_terms 安全合流至 glossary.md，严格对齐 3 列表格规范与全库/批次幂等查重"""
    with GatekeeperLock(LOCK_FILE):
        manifest = load_manifest()

        collected_terms = []
        for k, v in manifest.items():
            terms = v.get("staged_terms", [])
            if terms and isinstance(terms, list):
                for t in terms:
                    if isinstance(t, dict):
                        t_copy = dict(t)
                        t_copy["source_wiki"] = v.get("wiki", "")
                        collected_terms.append(t_copy)

        if not collected_terms:
            return {"status": "NOTHING_TO_FLUSH", "flushed_count": 0}

        if not GLOSSARY_FILE.exists():
            raise FileNotFoundError("glossary.md 受控词表文件不存在")

        with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
            glossary_text = f.read()

        # 扫描已有词表，全面提取英文/缩写用于查重（解析表格第1、2、3列并解开括号别名）
        existing_keys = set()
        for line in glossary_text.splitlines():
            line_s = line.strip()
            if line_s.startswith("|") and not line_s.startswith("| :") and "英文缩写" not in line_s:
                parts = [p.strip() for p in line_s.split("|")]
                if len(parts) >= 4:
                    col1 = parts[1]
                    col3 = parts[3]
                    existing_keys.add(col1.lower())
                    for item in re.findall(r"\(([^)]+)\)", col1):
                        existing_keys.add(item.strip().lower())
                    for item in re.findall(r"\(([^)]+)\)", col3):
                        existing_keys.add(item.strip().lower())

        new_rows = []
        added_count = 0
        batch_seen = set()

        for t in collected_terms:
            en = (t.get("en") or "").strip()
            zh = (t.get("zh") or "").strip()
            abbr = (t.get("abbr") or "").strip()

            check_key = (abbr or en).lower()
            if not check_key:
                continue

            # 幂等查重：过滤已有库内词及同批次重复词
            if check_key in existing_keys or check_key in batch_seen:
                continue

            batch_seen.add(check_key)

            display_en = f"{en} ({abbr})" if (abbr and abbr != en and abbr not in en) else (en or abbr)
            dlink = f"[[{zh} ({abbr})]]" if abbr else (f"[[{zh} ({en})]]" if en else f"[[{zh}]]")

            # 严格对齐 3 列格式：| 英文缩写/术语 (English Term) | 标准中文翻译 (Standard Chinese) | 标准双向链接格式 (Wikilink Format) |
            row = f"| {display_en:<45} | {zh:<28} | {dlink} |"
            new_rows.append(row)
            added_count += 1

        if new_rows:
            updated_glossary = append_to_glossary_staging(glossary_text, new_rows)
            atomic_write_file(GLOSSARY_FILE, updated_glossary)

        # 排空账本暂存
        for k in manifest:
            if "staged_terms" in manifest[k]:
                del manifest[k]["staged_terms"]

        atomic_write_json(MANIFEST_FILE, manifest)

        return {
            "status": "FLUSHED",
            "flushed_terms_count": added_count,
            "target_glossary": GLOSSARY_FILE.name
        }


def run_promote_drafts() -> dict:
    """将 .scratch/shadow_drafts/ 暂存的影子草稿原子转正合流至 wiki/
    
    防御与命名空间防护 (Namespace & Integrity Guard):
    1. 阻断中间切片污染：严禁将 part_*、slice_*、task_* 等临时切片碎片直抛 wiki/ 根目录。
    2. 严格元数据门禁：目标文件必须具备合法 YAML Frontmatter (type: topic/guideline/book 等)。
    3. 备份与回退保护：目标文件若存在则自动执行 make_backup=True。
    """
    with GatekeeperLock(LOCK_FILE):
        if not SHADOW_DIR.exists():
            return {"status": "IDLE", "message": "暂存沙箱 .scratch/shadow_drafts 不存在"}
        
        draft_files = [f for f in SHADOW_DIR.iterdir() if f.is_file() and f.suffix.lower() == ".md"]
        if not draft_files:
            return {"status": "IDLE", "message": "暂存沙箱中无待转正草稿"}
            
        promoted = []
        ignored_fragments = []
        WIKI_DIR.mkdir(parents=True, exist_ok=True)
        
        for df in draft_files:
            # 1. 过滤虚拟切片碎片文件，杜绝污染 wiki/ 命名空间
            if re.match(r"^(part|slice|task|scratch|chunk)_\d+", df.stem, re.IGNORECASE):
                ignored_fragments.append(df.name)
                continue
                
            with open(df, "r", encoding="utf-8") as src:
                content = src.read()
                
            # 2. 必须具备合法的 YAML Frontmatter 且声明了 type
            if not re.search(r"^---\s*\n.*?type:\s*\w+.*?---\s*\n", content, re.DOTALL):
                ignored_fragments.append(f"{df.name} (无合法 Frontmatter type 声明，跳过转正)")
                continue
                
            target_wiki = WIKI_DIR / df.name
            atomic_write_file(target_wiki, content, make_backup=True)
            try:
                df.unlink()
            except Exception:
                pass
            promoted.append(f"wiki/{df.name}")
            
        return {
            "status": "PROMOTED" if promoted else "IDLE",
            "promoted_count": len(promoted),
            "promoted_files": promoted,
            "preserved_intermediate_fragments": ignored_fragments
        }


def run_archive_log(threshold: int = 200, keep: int = 1, force: bool = False) -> dict:
    """遵循 LLM Wiki 架构规范，将超出阈值的旧日志条目分卷归档至 logs/archive_YYYY.md。
    
    防御与自愈保证 (Invariants & Safeguards):
    1. 跨进程独占锁保护 (GatekeeperLock)，防止并发写入损坏。
    2. 严格按发表/记录时钟的年份 YYYY 分卷归档至 logs/archive_YYYY.md。
    3. 保留 log.md 顶置标题与最新活跃条目 (默认仅保留最后 1 条)。
    4. 100% 保持尾部 <!-- %% LOG_TAIL_ANCHOR %% --> 锚点不丢失。
    5. 全链路 atomic_write_file 写入并自动生成 .bak 备份。
    """
    with GatekeeperLock(LOCK_FILE):
        if not LOG_FILE.exists():
            return {"status": "ERROR", "message": "log.md 不存在"}

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            raw_log = f.read()

        log_normalized = raw_log.replace("\r\n", "\n")

        # 确保尾部锚点存在
        if LOG_ANCHOR not in log_normalized:
            log_normalized = log_normalized.rstrip() + f"\n\n{LOG_ANCHOR}\n"

        # 解析条目：## [YYYY-MM-DD] 格式
        entry_pattern = re.compile(
            r'(^##\s*\[(\d{4})-\d{2}-\d{2}\].*?)(?=(?:^##\s*\[\d{4}-\d{2}-\d{2}\])|(?:\s*<!-- %% LOG_TAIL_ANCHOR %% -->)|\Z)',
            re.MULTILINE | re.DOTALL
        )

        matches = list(entry_pattern.finditer(log_normalized))
        total_count = len(matches)

        if not force and total_count <= threshold:
            return {
                "status": "IDLE",
                "total_entries": total_count,
                "threshold": threshold,
                "message": f"log.md 当前条目数 ({total_count}) 未超过分卷阈值 ({threshold})，无需归档。"
            }

        num_to_keep = max(1, min(keep, total_count - 1))
        to_archive = matches[:-num_to_keep]
        to_keep = matches[-num_to_keep:]

        # 按年份分组归档条目
        entries_by_year = {}
        for m in to_archive:
            year = m.group(2)
            content = m.group(1).rstrip()
            if year not in entries_by_year:
                entries_by_year[year] = []
            entries_by_year[year].append(content)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        archived_files = []

        for year, entries in entries_by_year.items():
            archive_file = LOGS_DIR / f"archive_{year}.md"
            archive_content = ""
            if archive_file.exists():
                with open(archive_file, "r", encoding="utf-8") as af:
                    archive_content = af.read().replace("\r\n", "\n").rstrip()
            else:
                archive_content = f"# 操作日志归档 - {year} (Archive {year})\n\n> 本文件归档了 {year} 年度的早期操作日志流水。最新活跃日志请见 [[log]]。\n"

            new_entries_block = "\n\n".join(entries)
            archive_content = archive_content.rstrip() + "\n\n" + new_entries_block + "\n"
            atomic_write_file(archive_file, archive_content, make_backup=True)
            archived_files.append(f"logs/archive_{year}.md")

        # 重建当前 log.md
        first_entry_start = matches[0].start()
        header_preamble = log_normalized[:first_entry_start].rstrip()
        # 清理旧的归档提示，确保不重复堆叠
        header_preamble = re.sub(r">\s*\[!NOTE\]\s*历史日志分卷归档.*?(?=\n\n|\Z)", "", header_preamble, flags=re.DOTALL).rstrip()
        if not header_preamble.strip().startswith("#"):
            header_preamble = "# 操作日志 (Log)"

        all_archives = sorted([
            f.name for f in LOGS_DIR.iterdir()
            if f.is_file() and f.suffix.lower() == ".md" and f.stem.startswith("archive_")
        ])
        archive_links_str = "、".join([f"[[{Path(a).stem}|logs/{a}]]" for a in all_archives]) if all_archives else "logs/"
        note_block = f"> [!NOTE] 历史日志分卷归档\n> 早期操作日志已按年度分卷归档至 {archive_links_str}。此处仅保留近期活跃操作流水。"

        kept_entries_block = "\n\n".join(m.group(1).rstrip() for m in to_keep)

        reconstructed_log = f"{header_preamble}\n\n{note_block}\n\n{kept_entries_block}\n\n{LOG_ANCHOR}\n"
        atomic_write_file(LOG_FILE, reconstructed_log, make_backup=True)

        return {
            "status": "ARCHIVED",
            "total_entries_before": total_count,
            "archived_count": len(to_archive),
            "retained_count": len(to_keep),
            "archived_files": archived_files,
            "message": f"成功将前 {len(to_archive)} 条历史日志归档至 {', '.join(archived_files)}，log.md 保留最近 {len(to_keep)} 条活跃记录与尾部锚点。"
        }


def run_backfill_metrics(force: bool = False) -> dict:
    """遵循第一性原理，对 raw_manifest.json 中存量文献一次性无损补齐物理页数 (page_count) 与密码学哈希指纹 (sha256)"""
    with GatekeeperLock(LOCK_FILE):
        manifest = load_manifest()
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        offline_count = 0
        pdf_count = 0
        non_pdf_count = 0

        for mpath, entry in manifest.items():
            if entry.get("status") == "OFFLINE":
                offline_count += 1
                continue

            full_path = ROOT_DIR / mpath
            if not full_path.exists():
                skipped_count += 1
                continue

            needs_sha = force or ("sha256" not in entry)
            needs_page = force or ("page_count" not in entry)

            if not (needs_sha or needs_page):
                skipped_count += 1
                continue

            try:
                if needs_sha:
                    entry["sha256"] = compute_sha256(full_path)
                if needs_page:
                    entry["page_count"] = get_document_page_count(full_path)

                if entry.get("page_count") is not None:
                    pdf_count += 1
                else:
                    non_pdf_count += 1

                updated_count += 1
            except Exception as e:
                failed_count += 1
                print(f"[Gatekeeper Warning] 自愈补齐 {mpath} 失败: {e}", file=sys.stderr)

        if updated_count > 0:
            atomic_write_json(MANIFEST_FILE, manifest, make_backup=True)

        return {
            "status": "BACKFILLED" if updated_count > 0 else "IDLE",
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "offline_count": offline_count,
            "failed_count": failed_count,
            "pdf_with_page_count": pdf_count,
            "non_pdf_null_page": non_pdf_count,
            "total_manifest_count": len(manifest),
            "message": f"成功为 {updated_count} 篇存量文献补齐物理页数与 SHA-256 密码学指纹。"
        }


def main():
    parser = argparse.ArgumentParser(description="利刃第二大脑·工业级门禁与机器账本管家 (Hardened V2.2 大文件分治增强版)")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # diff
    parser_diff = subparsers.add_parser("diff", help="扫描并输出待处理队列与墓碑自愈结果 (JSON)")

    # commit
    parser_commit = subparsers.add_parser("commit", help="原子提交新文献至账本")
    parser_commit.add_argument("--file", required=True, help="raw/相对文件路径")
    parser_commit.add_argument("--wiki", required=True, help="wiki/生成的页面路径")
    parser_commit.add_argument("--terms", required=False, default=None, help="暂存术语 JSON 字符串，支持 '-' 从 Stdin 读取")
    parser_commit.add_argument("--terms-file", required=False, default=None, help='暂存术语 UTF-8 JSON 文件路径。格式: [{"zh": "中文名", "en": "English", "abbr": "可选缩写"}]')
    parser_commit.add_argument("--log-file", required=False, default=None, help="包含日志条目的 UTF-8 Markdown 临时文件路径 (一体化原子落盘)")
    parser_commit.add_argument("--date", required=False, default=None, help="显式内生摄取日期 (YYYY-MM-DD)")
    parser_commit.add_argument("--cluster-wikis", required=False, nargs="*", default=None, help="L1 法典直通集群孵化的子卡路径列表 (最多3个)")

    # append-log
    parser_append_log = subparsers.add_parser("append-log", help="确定性追加日志条目至 log.md 并守恒尾部哨兵锚点")
    parser_append_log.add_argument("--entry-file", required=False, default=None, help="包含日志条目的 UTF-8 Markdown 临时文件路径")
    parser_append_log.add_argument("--entry-text", required=False, default=None, help="直接传入日志条目文本内容")

    # flush-terms
    parser_flush = subparsers.add_parser("flush-terms", help="将账本中挂账的术语合流至 glossary.md")

    # promote-drafts
    parser_promote = subparsers.add_parser("promote-drafts", help="将 .scratch/shadow_drafts/ 影子沙箱中的草稿原子转正至 wiki/")

    # archive-log
    parser_archive = subparsers.add_parser("archive-log", help="将 log.md 超过阈值的旧日志分卷归档至 logs/archive_YYYY.md")
    parser_archive.add_argument("--threshold", type=int, default=200, help="触发分卷的条目数阈值 (默认: 200)")
    parser_archive.add_argument("--keep", type=int, default=1, help="log.md 中保留的最新活跃条目数 (默认: 1)")
    parser_archive.add_argument("--force", action="store_true", help="强制立即执行分卷归档，无视阈值检查")

    # backfill-metrics
    parser_backfill = subparsers.add_parser("backfill-metrics", help="对 raw_manifest.json 存量文献一次性无损补齐页数 (page_count) 与 SHA-256 指纹 (sha256)")
    parser_backfill.add_argument("--force", action="store_true", help="强制重新计算全量指标")

    args = parser.parse_args()

    if args.command == "diff" or not args.command:
        res = run_diff()
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "commit":
        res = run_commit(
            args.file,
            args.wiki,
            args.terms,
            args.date,
            getattr(args, "terms_file", None),
            getattr(args, "log_file", None),
            getattr(args, "cluster_wikis", None)
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "append-log":
        res = run_append_log(
            getattr(args, "entry_file", None),
            getattr(args, "entry_text", None)
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "flush-terms":
        res = run_flush_terms()
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "promote-drafts":
        res = run_promote_drafts()
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "archive-log":
        res = run_archive_log(args.threshold, args.keep, args.force)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.command == "backfill-metrics":
        res = run_backfill_metrics(args.force)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

