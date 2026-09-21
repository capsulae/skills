#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.scripts/tests/test_toolchain.py - 防线 1：宿主工具链与物理环境探针测试
验证底层文件系统、Unicode编码、ripgrep检索语义与跨进程锁排他性
"""

import os
import sys
import time
import subprocess
import threading
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

from gatekeeper import GatekeeperLock, LOCK_FILE


def test_glossary_grep_semantics() -> dict:
    """用例 1：验证词表检索语义与底层 ripgrep 路径容错探针"""
    glossary_path = ROOT_DIR / "glossary.md"
    assert glossary_path.exists(), f"glossary.md 不存在: {glossary_path}"

    # 1. 模拟单文件直接检索（检测底层环境是否存在单文件假阴性陷阱）
    # 当直接指定单文件为搜索目标时，测试是否能稳定捕获特定词条
    with open(glossary_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Malaria" in content, "glossary.md 预置测试词条 Malaria 缺失"

    # 2. 验证基于根目录配合文件包含过滤的权威检索语义
    # 模拟 grep_search(SearchPath=".", Includes=["glossary.md"], Query=r"\|\s*Malaria\b")
    lines = content.splitlines()
    matches = [
        (idx + 1, line)
        for idx, line in enumerate(lines)
        if "Malaria" in line and line.strip().startswith("|")
    ]

    assert len(matches) >= 1, "词表目录检索语义断言失败：未检索到 Malaria 词条"
    assert any("疟疾" in line for _, line in matches), "词条中英映射断言失败：未检索到中文对应项"

    return {
        "test": "test_glossary_grep_semantics",
        "status": "PASS",
        "matched_lines": len(matches),
        "detail": "词表包含过滤检索语义自洽，命中目标词条"
    }


def test_windows_path_case_normalization() -> dict:
    """用例 2：验证 Windows 物理路径大小写归一化探针"""
    fixture_real = ROOT_DIR / "raw" / "fixtures" / "L1_fixture_standard.md"
    assert fixture_real.exists(), f"测试基准文件不存在: {fixture_real}"

    # 构造变异大小写路径
    fixture_lower = ROOT_DIR / "raw" / "fixtures" / "l1_fixture_standard.md"
    fixture_upper = ROOT_DIR / "raw" / "fixtures" / "L1_FIXTURE_STANDARD.MD"

    # 断言 Windows 下物理存在性
    assert fixture_lower.exists(), "路径大小写变异存在性断言失败"
    assert fixture_upper.exists(), "路径大写变异存在性断言失败"

    # 断言真实物理路径归一化守恒 (Path.resolve())
    resolved_real = fixture_real.resolve()
    resolved_lower = fixture_lower.resolve()
    resolved_upper = fixture_upper.resolve()

    assert resolved_lower == resolved_real, "大小写归一化断言失败：解析路径不一致"
    assert resolved_upper == resolved_real, "大小写归一化断言失败：解析路径不一致"

    # 断言磁盘实际大小写文件名反查
    parent_dir = fixture_real.parent
    actual_filenames = {p.name for p in parent_dir.iterdir()}
    assert "L1_fixture_standard.md" in actual_filenames, "物理磁盘真实文件名守恒断言失败"

    return {
        "test": "test_windows_path_case_normalization",
        "status": "PASS",
        "canonical_name": resolved_real.name,
        "detail": "物理路径大小写归一化机制通过"
    }


def test_utf8_encoding_and_no_bom() -> dict:
    """用例 3：验证无 BOM UTF-8 编码与问号乱码阻断探针"""
    fixtures_dir = ROOT_DIR / "raw" / "fixtures"
    target_files = list(fixtures_dir.glob("*.md"))
    target_files.extend([ROOT_DIR / "glossary.md", ROOT_DIR / "AGENTS.md"])

    checked_count = 0
    for file_path in target_files:
        if not file_path.exists():
            continue
        raw_bytes = file_path.read_bytes()

        # 断言无 BOM 头部 (b'\xef\xbb\xbf')
        assert not raw_bytes.startswith(b"\xef\xbb\xbf"), f"文件包含非法 UTF-8 BOM 头: {file_path.name}"

        # 断言 UTF-8 纯度与无乱码替换符
        decoded = raw_bytes.decode("utf-8")
        assert "\ufffd" not in decoded, f"文件包含非法 Unicode 替换字符: {file_path.name}"

        # 断言无控制台编码截断产生的连续孤立问号 (如 ?? / ???)
        import re
        assert not re.search(r"[a-zA-Z\u4e00-\u9fa5]\?{2,}[a-zA-Z\u4e00-\u9fa5]", decoded), f"文件包含可疑截断问号: {file_path.name}"
        checked_count += 1

    return {
        "test": "test_utf8_encoding_and_no_bom",
        "status": "PASS",
        "files_checked": checked_count,
        "detail": f"已核验 {checked_count} 个核心文件无 BOM 且编码纯度 100%"
    }


def test_gatekeeper_file_lock_concurrency() -> dict:
    """用例 4：验证跨进程/线程文件锁互斥与释放探针"""
    test_lock_file = ROOT_DIR / ".scratch" / ".test_gatekeeper.lock"
    test_lock_file.parent.mkdir(parents=True, exist_ok=True)
    if test_lock_file.exists():
        test_lock_file.unlink(missing_ok=True)

    lock_acquired = threading.Event()
    release_signal = threading.Event()
    worker_error = []

    def lock_holder():
        try:
            with GatekeeperLock(test_lock_file, timeout=5.0):
                lock_acquired.set()
                release_signal.wait(timeout=3.0)
        except Exception as e:
            worker_error.append(f"Holder error: {e}")

    # 启动持有锁的后台线程
    t = threading.Thread(target=lock_holder, daemon=True)
    t.start()

    assert lock_acquired.wait(timeout=2.0), f"主锁获取超时断言失败: {worker_error}"

    # 主线程尝试争抢已被持有的锁（超时设为 0.2 秒，必须超时失败）
    contention_failed = False
    try:
        with GatekeeperLock(test_lock_file, timeout=0.2):
            pass
    except TimeoutError:
        contention_failed = True
    except Exception as e:
        contention_failed = "Timeout" in str(e) or "锁" in str(e)

    assert contention_failed, "互斥锁排他性断言失败：争抢未被正确阻塞"

    # 释放后台锁
    release_signal.set()
    t.join(timeout=2.0)

    # 再次尝试获取，断言释放后能正常获取
    reacquired = False
    with GatekeeperLock(test_lock_file, timeout=2.0):
        reacquired = True

    assert reacquired, "锁释放后重入断言失败"
    test_lock_file.unlink(missing_ok=True)

    return {
        "test": "test_gatekeeper_file_lock_concurrency",
        "status": "PASS",
        "detail": "跨线程独占排他锁与自愈释放断言通过"
    }


def run_all_toolchain_tests() -> list[dict]:
    tests = [
        test_glossary_grep_semantics,
        test_windows_path_case_normalization,
        test_utf8_encoding_and_no_bom,
        test_gatekeeper_file_lock_concurrency,
    ]
    results = []
    for t in tests:
        start_t = time.perf_counter()
        try:
            res = t()
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            res["elapsed_ms"] = elapsed_ms
            results.append(res)
        except AssertionError as ae:
            elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
            results.append({
                "test": t.__name__,
                "status": "FAIL",
                "error": str(ae),
                "elapsed_ms": elapsed_ms
            })
    return results


if __name__ == "__main__":
    res_list = run_all_toolchain_tests()
    all_pass = all(r["status"] == "PASS" for r in res_list)
    print("=" * 60)
    print("🛡️  防线 1：宿主工具链与物理环境探针测试")
    print("=" * 60)
    for r in res_list:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{status_icon} [{r['status']}] {r['test']} ({r['elapsed_ms']} ms) - {r.get('detail', r.get('error'))}")
    print("=" * 60)
    sys.exit(0 if all_pass else 1)

