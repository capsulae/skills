#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.scripts/tests/run_tests.py - 利刃的第二大脑·三道防线标准化回归测试调度器
一键串联并执行宿主工具链探针(防线1)、无头管家状态机(防线2)、Agent仿真审计(防线3)与黄金样本库
"""

import os
import sys
import time
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
TESTS_DIR = ROOT_DIR / ".scripts" / "tests"
TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(TESTS_DIR))

from generate_fixtures import generate_all_fixtures
from test_toolchain import run_all_toolchain_tests
from test_scripts import run_all_script_tests
from test_agent_audit import run_all_audit_tests


def main():
    total_start = time.perf_counter()
    print("=" * 70)
    print("🚀 利刃的第二大脑 · 三道防线标准化回归测试流水线")
    print("=" * 70)

    # 阶段 0：黄金样本库就绪检测
    f_start = time.perf_counter()
    fixtures = generate_all_fixtures()
    f_elapsed = round((time.perf_counter() - f_start) * 1000, 2)
    print(f"📦 [黄金样本库] L1~L6 六级微型样本已就绪 ({len(fixtures)} 篇, {f_elapsed} ms)")
    print("-" * 70)

    all_suites = [
        ("防线 1：宿主工具链与物理环境探针测试", run_all_toolchain_tests),
        ("防线 2：无头管家脚本状态机断言测试", run_all_script_tests),
        ("防线 3：Agent 摄取仿真与轨迹自动审计测试", run_all_audit_tests),
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    suite_summaries = []

    for suite_name, runner in all_suites:
        print(f"\n▶ 开始执行 {suite_name}:")
        suite_start = time.perf_counter()
        results = runner()
        suite_elapsed = round((time.perf_counter() - suite_start) * 1000, 2)

        s_pass = sum(1 for r in results if r["status"] == "PASS")
        s_fail = sum(1 for r in results if r["status"] != "PASS")
        total_tests += len(results)
        passed_tests += s_pass
        failed_tests += s_fail

        for r in results:
            status_mark = "✅ 通过" if r["status"] == "PASS" else "❌ 失败"
            detail = r.get("detail") or r.get("error", "")
            print(f"  [{status_mark}] {r['test']} ({r['elapsed_ms']} ms) - {detail}")

        suite_summaries.append({
            "name": suite_name,
            "pass": s_pass,
            "fail": s_fail,
            "total": len(results),
            "elapsed_ms": suite_elapsed
        })

    total_elapsed = round((time.perf_counter() - total_start) * 1000, 2)

    print("\n" + "=" * 70)
    print("📊 回归测试执行总结看板")
    print("=" * 70)
    for s in suite_summaries:
        status_icon = "🟢" if s["fail"] == 0 else "🔴"
        print(f"{status_icon} {s['name']}: {s['pass']}/{s['total']} 用例通过 ({s['elapsed_ms']} ms)")

    print("-" * 70)
    overall_status = "ALL PASS (全绿通过)" if failed_tests == 0 else "FAILED (存在拦截失败)"
    print(f"🏁 最终结论: {overall_status}")
    print(f"📈 统计总览: 共执行 {total_tests} 项断言，通过 {passed_tests} 项，失败 {failed_tests} 项")
    print(f"⏱️ 净总耗时: {total_elapsed} ms (端到端实测)")
    print("=" * 70)

    sys.exit(0 if failed_tests == 0 else 1)


if __name__ == "__main__":
    main()

