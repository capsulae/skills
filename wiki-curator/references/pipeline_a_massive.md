# 流水线 A (分支 2)：超长文献双轨分治执行剧本 (`MASSIVE_DUAL_TRACK`)

> **前置契约**：本剧本仅在 `ingestion_track == "MASSIVE_DUAL_TRACK"`（页数 $\ge 35$ 或预估消耗 $\ge 33,600$ Tokens / 纯文本 $\ge 40\text{k}$）时独立加载。所有证据定级（§2.1）、卡片模板与四类提炼法则（§2.2）、查词过滤（§2.3）与存量演进算法（§2.4）均直接调用 `SKILL.md` 第 2 节全局法典。

---

## 1. 确定性分治七步执行序列

🚫 **严禁调用 `view_file` 连续分段翻阅 `raw/` 原件试图单 Agent 硬吞并单卡提交！**

```python
# Step 1: 全景骨架探测 (提取目录树 TOC、前言与符号表)
inspect_res = run_command(CommandLine=f'python .scripts/slice_raw.py inspect --file "{item.file}" --json')

# Step 2: 自然章节语义分治契约规划 (三级自愈: 原生书签 > 印刷目录/字号跳变 > 15页+2~3页滑动重叠兜底 100% 覆盖)
plan_res = run_command(CommandLine=f'python .scripts/slice_raw.py plan-subagents --file "{item.file}" --json')

# Step 3: 滑动重叠切片提取、查词消歧与下游卡片集群锻造 (切片动态命名防竞争)
# - 对切片提炼术语时，严格执行 SKILL.md §2.3 (剔除五大负向类别 ①~⑤ + 调用 query-terms 查词消歧并归集 staging_terms)
# - 按 SKILL.md §2.2(2) 三态四段式模板锻造下游实操主题卡 (Layer 0 Callout <= 5行; Layer 1 决策矩阵 <= 60行; Layer 2 指针)，暂存至 .scratch/shadow_drafts/
for task in plan_res.subagents:
    slice_out = f".scratch/slice_{task.pages.replace('-', '_')}.txt"
    run_command(CommandLine=f'python .scripts/slice_raw.py extract-slice --file "{item.file}" --pages "{task.pages}" --overlap 2 --out "{slice_out}"')

# Step 4: 架构 Master Hub 主卡与草稿转正
# - 按 SKILL.md §2.2(1) 文献卡规范落盘 Master Hub 主卡 (路径锁定为 item.target_wiki_hint，承载全书规范全貌、章节目录树与页码映射)
# - 过滤并转正合格下游主题卡 (cluster_wikis 数量须满足 1 <= len(cluster_wikis) <= 5)
run_command(CommandLine="python .scripts/gatekeeper.py promote-drafts")

# Step 5: 存量主题对齐演进与双向织网
# 检索关联存量主题卡，调用 view_file(EndLine=手记标题前) 读取，严格执行 SKILL.md §2.4 (童子军嗅探升级、流变探针、收敛三级阀与时序表折叠)

# Step 6: 保真度强制审计 (核验章节全貌与拓扑深度，不达标一票否决)
run_command(CommandLine=f'python .scripts/slice_raw.py audit --wiki "{item.target_wiki_hint}"')

# Step 7: 集群原子提交闭环
assert cluster_wikis and 1 <= len(cluster_wikis) <= 5, "超长文献必须以 Master Hub + 分治卡片集群提交 (--cluster-wikis)，严禁单篇薄卡退化提交！"

log_text = f"""## [{date}] 摄取 | {doc.title}
- **新增资料出处 (1篇)**: [[{doc.wiki_title}]]
- **全新孵化主题 ({len(cluster_wikis)}个)**: {cluster_links}
- **主题对齐演进 (M个)**: [[{aligned_topic}]]"""
write_to_file(TargetFile=".scratch/log_entry.md", CodeContent=log_text, Description="生成超长文献分治摄取日志", Overwrite=True)

cmd = f'python .scripts/gatekeeper.py commit --file "{item.file}" --wiki "{item.target_wiki_hint}" --date "{date}" --log-file ".scratch/log_entry.md" --cluster-wikis ' + ' '.join(f'"{w}"' for w in cluster_wikis)

if staging_terms:
    write_to_file(TargetFile=".scratch/terms.json", CodeContent=json.dumps(staging_terms, ensure_ascii=False, indent=2), Description="暂存新词表", Overwrite=True)
    cmd += ' --terms-file ".scratch/terms.json"'

run_command(CommandLine=cmd)

if staging_terms:
    run_command(CommandLine="python .scripts/gatekeeper.py flush-terms")

run_command(CommandLine="python .scripts/scan_ghosts.py")
# 注: 全局队列归零核验 (assert diff == "IDLE") 由 SKILL.md 路由器外层循环统一执行
```

---

## 2. 超长文档漏斗切片工具字典 (`.scripts/slice_raw.py`)

| 操作目标 | 标准确定性命令模板 | 关键约束与前置条件 |
| :--- | :--- | :--- |
| **全景目录探测** | `python .scripts/slice_raw.py inspect --file "<file>" --json` | 必填 `--file`；提取目录与前言；常规文献严禁调用。 |
| **领域热力雷达** | `python .scripts/slice_raw.py radar --file "<file>" --json` | 必填 `--file`；可选 `--mode {normative,heuristic,descriptive}`。 |
| **前置锚点提取** | `python .scripts/slice_raw.py extract-anchor --file "<file>" --out ".scratch/anchor.md"` | 必填 `--file`；提取前 5 页核心定义。 |
| **分段切片提取** | `python .scripts/slice_raw.py extract-slice --file "<file>" --pages "10-25" --overlap 2 --out ".scratch/slice.txt"` | 强制滑动重叠提取。 |
| **子任务计划** | `python .scripts/slice_raw.py plan-subagents --file "<file>" --json` | 输出结构化子任务契约。 |
| **保真度审计** | `python .scripts/slice_raw.py audit --wiki "<wiki>"` | 剔除注释后核验完整性与拓扑深度。 |
