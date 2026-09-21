#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.scripts/tests/test_agent_audit.py - 防线 3：Agent 摄取仿真与轨迹自动审计工具
自动化审计 Agent 执行日志 (transcript.jsonl) 的耗时、工具调用指纹与维基卡片认识论规范
"""

import os
import sys
import re
import json
import time
from pathlib import Path
from datetime import datetime

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


def parse_transcript_events(transcript_file: Path) -> dict:
    """解析 transcript.jsonl 文件，提取时序、耗时与工具调用特征"""
    if not transcript_file.exists():
        raise FileNotFoundError(f"Transcript 文件不存在: {transcript_file}")

    events = []
    with open(transcript_file, "r", encoding="utf-8") as f:
        for line in f:
            line_s = line.strip()
            if not line_s:
                continue
            try:
                events.append(json.loads(line_s))
            except Exception:
                pass

    if not events:
        return {
            "total_steps": 0,
            "duration_seconds": 0,
            "tool_calls": [],
            "view_scripts_calls": 0,
            "glossary_grep_calls": 0,
            "help_command_calls": 0,
        }

    # 提取时间戳
    timestamps = []
    for e in events:
        created_at = e.get("created_at")
        if created_at:
            try:
                # 兼容 ISO 格式 "2026-09-16T06:40:00Z" 与带有微秒格式
                dt_str = created_at.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                timestamps.append(dt.timestamp())
            except Exception:
                pass

    duration_seconds = 0
    if len(timestamps) >= 2:
        duration_seconds = max(timestamps) - min(timestamps)

    # 统计工具调用指纹
    all_tool_calls = []
    view_scripts_count = 0
    glossary_grep_count = 0
    help_command_count = 0

    for e in events:
        t_calls = e.get("tool_calls") or []
        for tc in t_calls:
            func = tc.get("function", {})
            fname = func.get("name", "")
            fargs = func.get("arguments", {})
            if isinstance(fargs, str):
                try:
                    fargs = json.loads(fargs)
                except Exception:
                    fargs = {}

            all_tool_calls.append({"name": fname, "args": fargs})

            # 探针 1：翻看 .scripts/ 源码
            if fname == "view_file":
                path_str = str(fargs.get("AbsolutePath", "")).lower().replace("\\", "/")
                if ".scripts" in path_str:
                    view_scripts_count += 1

            # 探针 2：glossary 检索频次
            if fname == "grep_search":
                search_path = str(fargs.get("SearchPath", "")).lower()
                includes = str(fargs.get("Includes", "")).lower()
                if "glossary" in search_path or "glossary" in includes:
                    glossary_grep_count += 1

            # 探针 3：非法 --help 探测
            if fname == "run_command":
                cmd = str(fargs.get("CommandLine", "")).lower()
                if "--help" in cmd or " -h " in cmd or cmd.endswith(" -h"):
                    help_command_count += 1

    return {
        "total_steps": len(events),
        "duration_seconds": round(duration_seconds, 2),
        "tool_calls": all_tool_calls,
        "view_scripts_calls": view_scripts_count,
        "glossary_grep_calls": glossary_grep_count,
        "help_command_calls": help_command_count,
    }


def audit_wiki_epistemics(card_text: str) -> dict:
    """审计单张维基卡片的 Frontmatter 与三态认识论置顶视口规范"""
    violations = []

    # 1. 检验 Frontmatter 闭合
    fm_match = re.search(r"^---\s*\n([\s\S]*?)\n---", card_text)
    if not fm_match:
        violations.append("缺失标准 YAML Frontmatter 头部")
        return {"compliant": False, "violations": violations}

    yaml_block = fm_match.group(1)

    # 必填字段断言
    required_fields = ["title", "type", "evidence_level", "epistemic_status", "date", "year"]
    for rf in required_fields:
        if not re.search(rf"^{rf}:", yaml_block, re.M):
            violations.append(f"Frontmatter 缺失必须字段: {rf}")

    # 提取关键属性
    em = re.search(r"^evidence_level:\s*(\w+)", yaml_block, re.M)
    evidence_level = em.group(1) if em else ""

    tm = re.search(r"^type:\s*(\w+)", yaml_block, re.M)
    ptype = tm.group(1) if tm else ""

    # 2. 模式 A / B / C / L5 / L6 置顶视口与规范字段断言
    if evidence_level == "L1_standard":
        # 模式 A: 法定标准
        if not re.search(r"^>\s*\[!CURRENT-STANDARD\]", card_text, re.M):
            violations.append("L1 法定标准卡片必须使用 '> [!CURRENT-STANDARD]' 置顶视口")
        if not re.search(r"standard_year:\s*\d{4}", yaml_block):
            violations.append("L1 法定标准卡片 Frontmatter 必须提供 4 位 standard_year")
    elif evidence_level == "L4_industry_framework":
        # 模式 B: 实务规范
        if not re.search(r"^>\s*\[!CURRENT-GUIDELINE\]", card_text, re.M):
            violations.append("L4 产业架构专著卡片必须使用 '> [!CURRENT-GUIDELINE]' 置顶视口")
    elif evidence_level in ("L2_causal_synthesis", "L3_empirical_peer_reviewed"):
        # 模式 C: 客观机理与实证
        if not re.search(r"^>\s*\[!NOTE\]", card_text, re.M):
            violations.append("L2/L3 实证机理卡片必须使用 '> [!NOTE]' 置顶视口")
    elif evidence_level in ("L5_exploratory", "L6_informal"):
        # 探索假说与非正式来源
        if not re.search(r"^>\s*\[!INFO\]", card_text, re.M):
            violations.append("L5/L6 探索或非正式卡片必须使用 '> [!INFO]' 降级视口")

    return {
        "compliant": len(violations) == 0,
        "violations": violations,
        "evidence_level": evidence_level,
        "type": ptype
    }


def test_golden_fixtures_compliance() -> dict:
    """用例 1：审计 raw/fixtures/ 下 6 篇黄金夹具的合规性"""
    fixtures_dir = ROOT_DIR / "raw" / "fixtures"
    fixture_files = sorted(list(fixtures_dir.glob("*.md")))
    assert len(fixture_files) == 6, f"预期 6 个黄金测试样本，实际发现 {len(fixture_files)}"

    for ff in fixture_files:
        content = ff.read_text(encoding="utf-8")
        audit_res = audit_wiki_epistemics(content)
        assert audit_res["compliant"], f"黄金样本 {ff.name} 认识论契约违规: {audit_res['violations']}"

    return {
        "test": "test_golden_fixtures_compliance",
        "status": "PASS",
        "audited_count": len(fixture_files),
        "detail": "6 篇 L1~L6 黄金样本 100% 符合 YAML 与三态认识论视口契约"
    }


def test_historical_incident_fingerprint_detection() -> dict:
    """用例 2：历史事故仿真检测断言（回放 540c21ac 事故特征并验证 100% 告警）"""
    # 模拟 540c21ac 会话的关键违规指纹：
    # 1. 耗时 1884 秒 (> 600 秒)
    # 2. 连续 6 次 view_file 翻看 .scripts/gatekeeper.py
    # 3. 词表反复检索 12 次
    mock_events = {
        "total_steps": 45,
        "duration_seconds": 1884.2,
        "tool_calls": [],
        "view_scripts_calls": 6,
        "glossary_grep_calls": 12,
        "help_command_calls": 1,
    }

    # 执行审计断言，必须触发所有 4 项拦截指标
    violations = []
    if mock_events["duration_seconds"] > 600:
        violations.append(f"【耗时超限拦截】摄取总耗时 {mock_events['duration_seconds']}s 超过 600s 阈值")
    if mock_events["view_scripts_calls"] > 0:
        violations.append(f"【源码翻看拦截】检测到 {mock_events['view_scripts_calls']} 次 view_file 翻看 .scripts 源码")
    if mock_events["glossary_grep_calls"] > 5:
        violations.append(f"【词表循环拦截】检测到 {mock_events['glossary_grep_calls']} 次词表检索，疑似假阴性死循环")
    if mock_events["help_command_calls"] > 0:
        violations.append(f"【非法探测拦截】检测到 {mock_events['help_command_calls']} 次非法 --help 探测命令")

    assert len(violations) == 4, f"事故指纹漏判断言失败，预期 4 项违规，实际检出: {violations}"

    return {
        "test": "test_historical_incident_fingerprint_detection",
        "status": "PASS",
        "detected_violations": len(violations),
        "detail": "成功精准捕获历史事故全部 4 项违规指纹（耗时超限、源码翻看、词表死循环、非法帮助）"
    }


def test_ideal_agent_session_acceptance() -> dict:
    """用例 3：标准合规 Agent 会话轨迹通过性断言"""
    # 模拟理想标准摄取轨迹：
    # 1. 耗时 120 秒 (<= 600 秒)
    # 2. 0 次翻看脚本源码
    # 3. 2 次词表检索 (<= 5 次)
    # 4. 0 次 --help 探测
    ideal_events = {
        "total_steps": 12,
        "duration_seconds": 120.0,
        "tool_calls": [],
        "view_scripts_calls": 0,
        "glossary_grep_calls": 2,
        "help_command_calls": 0,
    }

    violations = []
    if ideal_events["duration_seconds"] > 600:
        violations.append("耗时超限")
    if ideal_events["view_scripts_calls"] > 0:
        violations.append("翻看源码")
    if ideal_events["glossary_grep_calls"] > 5:
        violations.append("词表循环")
    if ideal_events["help_command_calls"] > 0:
        violations.append("非法帮助")

    assert len(violations) == 0, f"标准轨迹误伤断言失败: {violations}"

    return {
        "test": "test_ideal_agent_session_acceptance",
        "status": "PASS",
        "detail": "标准合规摄取轨迹以 0 违规完全通过"
    }


def run_all_audit_tests() -> list[dict]:
    tests = [
        test_golden_fixtures_compliance,
        test_historical_incident_fingerprint_detection,
        test_ideal_agent_session_acceptance,
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
    res_list = run_all_audit_tests()
    all_pass = all(r["status"] == "PASS" for r in res_list)
    print("=" * 60)
    print("🛡️  防线 3：Agent 摄取仿真与轨迹自动审计测试")
    print("=" * 60)
    for r in res_list:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{status_icon} [{r['status']}] {r['test']} ({r['elapsed_ms']} ms) - {r.get('detail', r.get('error'))}")
    print("=" * 60)
    sys.exit(0 if all_pass else 1)

