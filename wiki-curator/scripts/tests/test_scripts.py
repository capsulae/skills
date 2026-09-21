#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.scripts/tests/test_scripts.py - 防线 2：无头管家脚本状态机断言测试
全沙箱隔离测试 gatekeeper.py、scan_ghosts.py、slice_raw.py 的状态机与边界拦截
"""

import os
import sys
import json
import time
import shutil
import tempfile
from pathlib import Path

# 强制终端 UTF-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
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
TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import gatekeeper
import scan_ghosts
import slice_raw


class SandboxVault:
    """自动化临时沙箱隔离环境，提供 100% 生产数据防污染隔离"""
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault_dir = Path(self.tmp.name)
        self.raw_dir = self.vault_dir / "raw"
        self.wiki_dir = self.vault_dir / "wiki"
        self.scratch_dir = self.vault_dir / ".scratch"
        self.scripts_dir = self.vault_dir / ".scripts"
        self.manifest_file = self.vault_dir / "raw_manifest.json"
        self.log_file = self.vault_dir / "log.md"
        self.glossary_file = self.vault_dir / "glossary.md"
        self.lock_file = self.scripts_dir / ".gatekeeper.lock"

        self.orig_gk = {}
        self.orig_sg = {}

    def __enter__(self):
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        self.scripts_dir.mkdir(parents=True, exist_ok=True)

        # 初始化空账本与日志
        self.manifest_file.write_text("{}", encoding="utf-8")
        self.log_file.write_text(f"# 操作日志 (Log)\n\n{gatekeeper.LOG_ANCHOR}\n", encoding="utf-8")

        # 复制真实 glossary.md 结构供测试使用
        real_glossary = ROOT_DIR / "glossary.md"
        if real_glossary.exists():
            shutil.copy2(real_glossary, self.glossary_file)
        else:
            self.glossary_file.write_text("| 英文 | 中文 | 双链 |\n| :--- | :--- | :--- |\n", encoding="utf-8")

        # Monkeypatch gatekeeper
        for attr in ["ROOT_DIR", "RAW_DIR", "WIKI_DIR", "MANIFEST_FILE", "LOG_FILE", "GLOSSARY_FILE", "LOCK_FILE"]:
            self.orig_gk[attr] = getattr(gatekeeper, attr)
        gatekeeper.ROOT_DIR = self.vault_dir
        gatekeeper.RAW_DIR = self.raw_dir
        gatekeeper.WIKI_DIR = self.wiki_dir
        gatekeeper.MANIFEST_FILE = self.manifest_file
        gatekeeper.MANIFEST_BAK_FILE = self.manifest_file.with_suffix(".json.bak")
        gatekeeper.LOG_FILE = self.log_file
        gatekeeper.GLOSSARY_FILE = self.glossary_file
        gatekeeper.LOCK_FILE = self.lock_file

        # Monkeypatch scan_ghosts
        for attr in ["ROOT_DIR", "WIKI_DIR", "GLOSSARY_FILE", "SCRATCH_DIR", "RADAR_CACHE_FILE"]:
            self.orig_sg[attr] = getattr(scan_ghosts, attr)
        scan_ghosts.ROOT_DIR = self.vault_dir
        scan_ghosts.WIKI_DIR = self.wiki_dir
        scan_ghosts.GLOSSARY_FILE = self.glossary_file
        scan_ghosts.SCRATCH_DIR = self.scratch_dir
        scan_ghosts.RADAR_CACHE_FILE = self.scratch_dir / "ghost_radar_cache.json"

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for attr, val in self.orig_gk.items():
            setattr(gatekeeper, attr, val)
        for attr, val in self.orig_sg.items():
            setattr(scan_ghosts, attr, val)
        self.tmp.cleanup()


def test_gatekeeper_diff_state_machine() -> dict:
    """用例 1：验证 gatekeeper.py diff 状态机流转与字段断言"""
    with SandboxVault() as vault:
        # 1. 空状态断言: 无新文件应为 IDLE
        res_idle = gatekeeper.run_diff()
        assert res_idle["status"] == "IDLE", f"空状态断言失败，预期 IDLE，实际: {res_idle['status']}"
        assert len(res_idle["diff_queue"]) == 0, "空状态队列长度断言失败"

        # 2. 新文件注入断言: 拷入 L3 测试夹具
        fixture_src = ROOT_DIR / "raw" / "fixtures" / "L3_fixture_empirical_paper.md"
        shutil.copy2(fixture_src, vault.raw_dir / "L3_test_paper.md")

        res_proceed = gatekeeper.run_diff()
        assert res_proceed["status"] == "PROCEED", f"新文件断言失败，预期 PROCEED，实际: {res_proceed['status']}"
        assert len(res_proceed["diff_queue"]) == 1, "队列长度应为 1"

        item = res_proceed["diff_queue"][0]
        assert item["action"] == "NEW", "动效应为 NEW"
        assert item["ingestion_track"] == "STANDARD", "小文件轨道应为 STANDARD"
        assert item["file"] == "raw/L3_test_paper.md", "文件路径不匹配"
        assert "sha256" in item and len(item["sha256"]) == 64, "SHA-256 哈希缺失或长度不合法"
        assert item["size_bytes"] > 0, "物理体积应大于 0"

    return {
        "test": "test_gatekeeper_diff_state_machine",
        "status": "PASS",
        "detail": "门禁差分状态机 IDLE/PROCEED 与字段契约全部通过"
    }


def test_gatekeeper_cluster_quota_enforcement() -> dict:
    """用例 2：验证 L1 法典集群子卡配额与实体存在性硬拦截"""
    with SandboxVault() as vault:
        # 准备主资料与主卡
        fixture_src = ROOT_DIR / "raw" / "fixtures" / "L1_fixture_standard.md"
        raw_target = vault.raw_dir / "ISO_13485_standard.md"
        shutil.copy2(fixture_src, raw_target)
        wiki_target = vault.wiki_dir / "ISO_13485_standard.md"
        wiki_target.write_text("# 医疗器械质量管理体系\n", encoding="utf-8")

        # 1. 配额超限拦截断言：传入 4 张子卡必须报 ValueError 且含【集群配额超限拦截】
        # 先在磁盘创建 4 个合法文件
        for i in range(1, 5):
            (vault.wiki_dir / f"cluster_card_{i}.md").write_text(f"# 子卡 {i}\n", encoding="utf-8")

        quota_blocked = False
        try:
            gatekeeper.run_commit(
                file_path="raw/ISO_13485_standard.md",
                wiki_path="wiki/ISO_13485_standard.md",
                cluster_wikis=[
                    "wiki/cluster_card_1.md",
                    "wiki/cluster_card_2.md",
                    "wiki/cluster_card_3.md",
                    "wiki/cluster_card_4.md"
                ]
            )
        except ValueError as ve:
            if "【集群配额超限拦截】" in str(ve):
                quota_blocked = True

        assert quota_blocked, "集群配额超限拦截断言失败：传入 4 张子卡未被阻断"

        # 2. 物理子卡不存在拦截断言：传入不存在的子卡
        missing_blocked = False
        try:
            gatekeeper.run_commit(
                file_path="raw/ISO_13485_standard.md",
                wiki_path="wiki/ISO_13485_standard.md",
                cluster_wikis=["wiki/cluster_card_1.md", "wiki/non_existent_card.md"]
            )
        except FileNotFoundError as fe:
            if "【集群子卡不存在拦截】" in str(fe):
                missing_blocked = True

        assert missing_blocked, "集群子卡不存在拦截断言失败：不存在物理文件未被阻断"

        # 3. 正常集群提交断言：传入 2 张真实存在的子卡，必须成功落盘账本
        res = gatekeeper.run_commit(
            file_path="raw/ISO_13485_standard.md",
            wiki_path="wiki/ISO_13485_standard.md",
            cluster_wikis=["wiki/cluster_card_1.md", "wiki/cluster_card_2.md"]
        )
        assert res["status"] == "COMMITTED", "正常提交断言失败"

        # 校验账本内容
        manifest = json.loads(vault.manifest_file.read_text(encoding="utf-8"))
        entry = manifest.get("raw/ISO_13485_standard.md")
        assert entry is not None, "账本记录缺失"
        assert "cluster_wikis" in entry, "账本未记录 cluster_wikis 字段"
        assert len(entry["cluster_wikis"]) == 2, f"集群子卡记录数量不符合预期: {entry['cluster_wikis']}"

    return {
        "test": "test_gatekeeper_cluster_quota_enforcement",
        "status": "PASS",
        "detail": "集群配额拦截、物理存在性校验与合规入账断言全部通过"
    }


def test_gatekeeper_log_append_and_anchor() -> dict:
    """用例 3：验证 log.md 确定性原子追加与哨兵锚点守恒"""
    with SandboxVault() as vault:
        # 1. 规范格式拦截断言：非 ## [YYYY-MM-DD] 开头必须报 ValueError
        invalid_format_blocked = False
        try:
            gatekeeper.append_log_entry("### 摄取测试文献\n- 非法开头", log_file=vault.log_file)
        except ValueError as ve:
            if "【日志规范拦截】" in str(ve):
                invalid_format_blocked = True

        assert invalid_format_blocked, "日志格式校验拦截断言失败"

        # 2. 合法格式追加断言
        valid_entry = """## [2026-09-17] 摄取 | 质量体系测试标准
- **新增资料出处 (1篇)**: [[医疗器械质量管理体系与设计控制规程标准]]
- **全新孵化主题 (2个)**: [[设计转换 (Design Transfer)]], [[无菌屏障系统 (Sterile Barrier System)]]"""

        res = gatekeeper.append_log_entry(valid_entry, log_file=vault.log_file)
        assert res["status"] == "APPENDED", "追加状态断言失败"
        assert res["total_entries"] == 1, "条目总数断言失败"

        # 3. 哨兵锚点守恒断言
        log_content = vault.log_file.read_text(encoding="utf-8")
        assert gatekeeper.LOG_ANCHOR in log_content, "哨兵锚点丢失断言失败"
        assert log_content.strip().endswith(gatekeeper.LOG_ANCHOR), "哨兵锚点未保持在尾部断言失败"

    return {
        "test": "test_gatekeeper_log_append_and_anchor",
        "status": "PASS",
        "detail": "日志规范拦截与尾部哨兵锚点守恒断言通过"
    }


def test_scan_ghosts_composite_scoring() -> dict:
    """用例 4：验证 scan_ghosts.py 复合认知权重与白名单保护断言"""
    with SandboxVault() as vault:
        # 构造测试场景：
        # 文献 A (高权威 L1): 引用 [[低共熔溶剂 (DES)]] 与 [[设计验证 (Design Verification)]]
        doc_a = vault.wiki_dir / "标准文献A.md"
        doc_a.write_text("""---
title: "标准文献A"
type: standard
evidence_level: L1_standard
---
这是规范正文，引用 [[低共熔溶剂 (DES)]] 以及 [[设计验证 (Design Verification)]]。
""", encoding="utf-8")

        # 文献 B (常规 L3): 引用 [[低共熔溶剂 (Deep Eutectic Solvents)]]
        doc_b = vault.wiki_dir / "实证文献B.md"
        doc_b.write_text("""---
title: "实证文献B"
type: paper
evidence_level: L3_empirical_peer_reviewed
---
这是实验正文，再次引用 [[低共熔溶剂 (Deep Eutectic Solvents)]]。
""", encoding="utf-8")

        # 主题卡 C (零实证纯概念): 仅在 concept 中反复引用 [[纯内卷概念 (Pure Concept)]] 5 次
        doc_c = vault.wiki_dir / "概念主题C.md"
        doc_c.write_text("""---
title: "概念主题C"
type: topic
---
内卷自嗨：[[纯内卷概念 (Pure Concept)]] [[纯内卷概念 (Pure Concept)]]
""", encoding="utf-8")

        # 执行扫描 (threshold = 2)
        candidates = scan_ghosts.scan_knowledge_graph(threshold=2)
        cand_names = [c["name"] for c in candidates]
        cand_bases = [c["base"] for c in candidates]

        # 断言 1: 零实证一票否决：纯内卷概念绝对不出现在候选名单中
        assert not any("纯内卷概念" in b for b in cand_bases), "零实证一票否决断言失败：无外部文献支撑概念被放行"

        # 断言 2: 中文基底安全聚类：低共熔溶剂 (DES) 与 (Deep Eutectic Solvents) 聚合为统一候选
        des_cands = [c for c in candidates if c["base"] == "低共熔溶剂"]
        assert len(des_cands) == 1, f"中文基底聚类断言失败，预期 1 个聚合候选，实际: {len(des_cands)}"
        assert des_cands[0]["sources_count"] == 2, f"出处频次断言失败，预期 2，实际: {des_cands[0]['sources_count']}"
        assert des_cands[0]["score"] >= 2.0, f"复合认知评分断言失败，预期 >= 2.0，实际: {des_cands[0]['score']}"

        # 断言 3: 消歧白名单保护：DISAMBIGUATION_PROTECTED 词条提取基底不剥离括号
        protected_base, stripped = scan_ghosts.extract_base_key("设计验证 (Design Verification)")
        assert stripped is False, "消歧白名单断言失败：保护词条被强制剥离"
        assert protected_base == "设计验证 (Design Verification)", "保护词条基底名称篡改断言失败"

    return {
        "test": "test_scan_ghosts_composite_scoring",
        "status": "PASS",
        "detail": "零实证一票否决、中文基底聚类与消歧白名单保护断言全部通过"
    }


def test_slice_raw_page_threshold_boundary() -> dict:
    """用例 5：验证超长文档 Token 准入临界点断言 (34页 STANDARD vs 35页 MASSIVE)"""
    # 基于第一性原理常量换算：
    # Tokens = 页数 * 560 + 14000
    # 34 页: 34 * 560 + 14000 = 19040 + 14000 = 33040 < 33600 -> STANDARD
    # 35 页: 35 * 560 + 14000 = 19600 + 14000 = 33600 >= 33600 -> MASSIVE_DUAL_TRACK
    
    # 验证常量定义
    assert slice_raw.MASSIVE_PAGE_THRESHOLD == 35, f"超长页数门槛定义断言失败: {slice_raw.MASSIVE_PAGE_THRESHOLD}"
    assert slice_raw.MASSIVE_TOTAL_TOKEN_THRESHOLD == 33600, f"Token 总门槛断言失败: {slice_raw.MASSIVE_TOTAL_TOKEN_THRESHOLD}"

    # 验证动态判定逻辑 (纯数学推导断言)
    def calc_is_massive(pages: int) -> bool:
        tokens = pages * slice_raw.PDF_PAGE_TOKENS + slice_raw.BASE_OVERHEAD_TOKENS
        return tokens >= slice_raw.MASSIVE_TOTAL_TOKEN_THRESHOLD

    assert calc_is_massive(34) is False, "34页临界点断言失败：应处于 STANDARD 轨道"
    assert calc_is_massive(35) is True, "35页临界点断言失败：应处于 MASSIVE_DUAL_TRACK 轨道"
    assert calc_is_massive(50) is True, "50页超长断言失败"

    return {
        "test": "test_slice_raw_page_threshold_boundary",
        "status": "PASS",
        "detail": "34页与35页超长临界点 Token 准入断言全部通过"
    }


def run_all_script_tests() -> list[dict]:
    tests = [
        test_gatekeeper_diff_state_machine,
        test_gatekeeper_cluster_quota_enforcement,
        test_gatekeeper_log_append_and_anchor,
        test_scan_ghosts_composite_scoring,
        test_slice_raw_page_threshold_boundary,
    ]
    results = []
    for t in tests:
        start_t = time.perf_counter()
        try:
            res = t()
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            res["elapsed_ms"] = elapsed_ms
            results.append(res)
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            results.append({
                "test": t.__name__,
                "status": "FAIL",
                "error": str(e),
                "elapsed_ms": elapsed_ms
            })
    return results


if __name__ == "__main__":
    res_list = run_all_script_tests()
    all_pass = all(r["status"] == "PASS" for r in res_list)
    print("=" * 60)
    print("🛡️  防线 2：无头管家脚本状态机与边界拦截断言测试")
    print("=" * 60)
    for r in res_list:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{status_icon} [{r['status']}] {r['test']} ({r['elapsed_ms']} ms) - {r.get('detail', r.get('error'))}")
    print("=" * 60)
    sys.exit(0 if all_pass else 1)

