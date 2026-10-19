#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Telemetry & Energy Dashboard Engine for Second Brain
Accurately calculates physical token consumption, prompt cache hit rates,
and tool usage metrics directly from Antigravity session transcripts.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_default_brain_dir() -> Path:
    """Return default Antigravity brain logs directory."""
    return Path.home() / ".gemini" / "antigravity" / "brain"


def find_latest_transcript() -> Path | None:
    """Find the most recently modified transcript.jsonl across all brain sessions."""
    brain_dir = get_default_brain_dir()
    if not brain_dir.exists():
        return None

    candidates = list(brain_dir.glob("*/.system_generated/logs/transcript.jsonl"))
    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def parse_transcript(transcript_path: Path | str) -> dict:
    """Parse transcript.jsonl and extract physical token metrics and step details."""
    path = Path(transcript_path)
    if not path.is_file():
        raise FileNotFoundError(f"Transcript not found: {path}")

    total_steps = 0
    planner_steps = 0
    user_steps = 0
    input_tokens = 0
    cache_read_tokens = 0
    output_tokens = 0
    tool_counts: dict[str, int] = {}
    step_records = []
    first_time = None
    last_time = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except Exception:
                continue

            total_steps += 1
            entry_type = entry.get("type")
            created_at = entry.get("created_at")
            if created_at:
                if first_time is None:
                    first_time = created_at
                last_time = created_at

            step_idx = entry.get("step_index", total_steps - 1)

            if entry_type == "USER_INPUT":
                user_steps += 1
            elif entry_type == "PLANNER_RESPONSE":
                planner_steps += 1
                inp = entry.get("input_tokens", 0)
                cache = entry.get("cache_read_tokens", 0)
                out = entry.get("output_tokens", 0)

                input_tokens += inp
                cache_read_tokens += cache
                output_tokens += out

                tools_in_step = []
                for tc in entry.get("tool_calls", []):
                    t_name = tc.get("name", "unknown")
                    tools_in_step.append(t_name)
                    tool_counts[t_name] = tool_counts.get(t_name, 0) + 1

                step_records.append({
                    "step": step_idx,
                    "input_tokens": inp,
                    "cache_read_tokens": cache,
                    "output_tokens": out,
                    "total_tokens": inp + cache + out,
                    "tools": tools_in_step,
                    "created_at": created_at or ""
                })

    total_prompt_tokens = input_tokens + cache_read_tokens
    gross_throughput = total_prompt_tokens + output_tokens
    cache_hit_rate = (cache_read_tokens / total_prompt_tokens * 100) if total_prompt_tokens > 0 else 0.0

    conv_id = "unknown"
    parts = path.resolve().parts
    try:
        idx = parts.index("brain")
        if idx + 1 < len(parts):
            conv_id = parts[idx + 1]
    except ValueError:
        pass

    return {
        "conversation_id": conv_id,
        "transcript_path": str(path.resolve()),
        "total_steps": total_steps,
        "planner_steps": planner_steps,
        "user_steps": user_steps,
        "input_tokens": input_tokens,
        "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "gross_throughput": gross_throughput,
        "cache_hit_rate_pct": round(cache_hit_rate, 2),
        "tool_usage": tool_counts,
        "step_records": step_records,
        "started_at": first_time or "",
        "finished_at": last_time or "",
    }


def render_progress_bar(pct: float, width: int = 15) -> str:
    """Render a text progress bar using safe ASCII characters."""
    filled = int(round(width * pct / 100))
    filled = max(0, min(width, filled))
    return "#" * filled + "-" * (width - filled)


def render_markdown_table(metrics: dict) -> str:
    """Generate delivery markdown table for Skill energy dashboard."""
    inp = metrics["input_tokens"]
    cache = metrics["cache_read_tokens"]
    out = metrics["output_tokens"]
    tot = metrics["gross_throughput"]
    hit = metrics["cache_hit_rate_pct"]
    p_steps = metrics["planner_steps"]

    inp_pct = (inp / tot * 100) if tot > 0 else 0.0
    out_pct = (out / tot * 100) if tot > 0 else 0.0

    lines = [
        "#### ⏱️ 能效消耗看板（物理真实遥测）",
        f"> **物理遥测基准**：共计 `{p_steps}` 轮推理，上下文缓存命中率达 **`{hit:.2f}%`**。",
        "",
        "| 认知推演维度 | 物理 Token 数 | 占比 / 命中率 | 备注 |",
        "| :--- | :--- | :--- | :--- |",
        f"| **未命中裸输入 (Prompt Delta)** | `{inp:,}` | {inp_pct:.1f}% | 原件文本增量与新指令输入 |",
        f"| **上下文缓存命中 (Cache Read)** | `{cache:,}` | **{hit:.1f}%** | 知识库与规则缓存命中（节省 ~{hit:.0f}% 计算开销） |",
        f"| **模型推理生成 (Output)** | `{out:,}` | {out_pct:.1f}% | 思维链思考 (CoT) 与工具调用参数 |",
        f"| **系统总吞吐规模 (Gross)** | `{tot:,}` | 100.0% | 本次会话物理吞吐总量 |"
    ]
    return "\n".join(lines)


def print_cli_report(metrics: dict, show_steps: bool = False) -> None:
    """Format and print an interactive console report."""
    conv_id = metrics.get("conversation_id", "unknown")
    t_path = metrics.get("transcript_path", "")
    t_steps = metrics.get("total_steps", 0)
    p_steps = metrics.get("planner_steps", 0)
    u_steps = metrics.get("user_steps", 0)
    inp = metrics.get("input_tokens", 0)
    cache = metrics.get("cache_read_tokens", 0)
    out = metrics.get("output_tokens", 0)
    prompt_tot = metrics.get("total_prompt_tokens", 0)
    gross = metrics.get("gross_throughput", 0)
    hit_rate = metrics.get("cache_hit_rate_pct", 0.0)
    tools = metrics.get("tool_usage", {})

    bar = render_progress_bar(hit_rate, width=15)

    print("\n" + "=" * 76)
    print("                     ANTIGRAVITY TOKEN TELEMETRY REPORT")
    print("=" * 76)
    print(f" Conversation ID : {conv_id}")
    print(f" Transcript Path : {t_path}")
    print(f" Execution Steps : {t_steps} Total ({p_steps} LLM Inferences, {u_steps} User Inputs)")
    print("-" * 76)
    print(" Token Breakdown:")
    print(f"   * Uncached Input (Prompt Delta) : {inp:>12,d} tokens")
    print(f"   * Cache Read (Prompt Hit)       : {cache:>12,d} tokens")
    print(f"   * Model Output (Generation)     : {out:>12,d} tokens")
    print("  " + "-" * 72)
    print(f"   * Total Prompt Context Seen     : {prompt_tot:>12,d} tokens")
    print(f"   * Gross System Throughput       : {gross:>12,d} tokens")
    print(f"   * Context Cache Hit Ratio       : {hit_rate:>11.2f} %  [{bar}]")
    print("-" * 76)

    if tools:
        print(" Tool Invocations:")
        sorted_tools = sorted(tools.items(), key=lambda x: x[1], reverse=True)
        for t, count in sorted_tools:
            print(f"   * {t:<28}: {count:>4d} calls")
        print("-" * 76)

    if show_steps and metrics.get("step_records"):
        print(" Step-by-Step Trajectory:")
        print(f" {'Step':<6} | {'Uncached In':<12} | {'Cache Read':<12} | {'Output':<10} | {'Total':<10} | {'Tools Used'}")
        print("-" * 76)
        for r in metrics["step_records"]:
            tools_str = ", ".join(r["tools"]) if r["tools"] else "(none)"
            print(f" {r['step']:<6} | {r['input_tokens']:>12,d} | {r['cache_read_tokens']:>12,d} | {r['output_tokens']:>10,d} | {r['total_tokens']:>10,d} | {tools_str}")
        print("=" * 76 + "\n")
    else:
        print("=" * 76 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Antigravity Real Token Tracker & Energy Dashboard")
    parser.add_argument("path", nargs="?", help="Path to transcript.jsonl (defaults to latest active session)")
    parser.add_argument("--conversation-id", "-c", help="Query specific conversation ID")
    parser.add_argument("--markdown", "-m", action="store_true", help="Output markdown table format for skill dashboard")
    parser.add_argument("--step-details", "-s", action="store_true", help="Display step-by-step breakdown table")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")

    args = parser.parse_args()

    target_path = None
    if args.path:
        target_path = Path(args.path)
    elif args.conversation_id:
        target_path = get_default_brain_dir() / args.conversation_id / ".system_generated" / "logs" / "transcript.jsonl"
    else:
        target_path = find_latest_transcript()

    if not target_path or not target_path.exists():
        print(f"Error: Could not locate a valid transcript.jsonl file.", file=sys.stderr)
        sys.exit(1)

    try:
        metrics = parse_transcript(target_path)
    except Exception as e:
        print(f"Error reading transcript: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(metrics, indent=2, ensure_ascii=False))
    elif args.markdown:
        print(render_markdown_table(metrics))
    else:
        print_cli_report(metrics, show_steps=args.step_details)


if __name__ == "__main__":
    main()
