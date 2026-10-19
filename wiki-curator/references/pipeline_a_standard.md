# 流水线 A (分支 1)：常规单篇文献摄取执行剧本 (`STANDARD`)

> **前置契约**：本剧本仅定义 `ingestion_track == "STANDARD"` 单篇文献的有序执行动作流；所有证据定级（§2.1）、卡片模板与四类提炼法则（§2.2）、查词过滤（§2.3）与存量演进算法（§2.4）均直接调用 `SKILL.md` 第 2 节全局法典。

---

## 执行工步序列 (Step A2 ~ Step A5)

```python
# Step A2: 原文精读与核心要素提炼
view_file(AbsolutePath=item.file)
# 严格按照 SKILL.md §2.2(1) 定义的四类文献提炼法则提取背景、突破、参数与边界，并对照 §2.1 & §2.2 裁决 L1~L6 等级与模式 A/B/C

# Step A3: 术语圈定与拓扑查词
# 严格执行 SKILL.md §2.3：剔除五大负向类别 ①~⑤，提炼 3~5 个正向核心术语，调用 query-terms 获取成品 wikilink 并归集 NEW 词条至 staging_terms

# Step A4: 文献卡落盘、直通子卡锻造与存量主题双向织网
# 1. 文献卡落盘: 按 SKILL.md §2.2(1) 模板将文献卡写入 item.target_wiki_hint
# 2. 直通子卡锻造: 若符合 §2.4 直通建页特权 (L1/L4 <= 3张, L2/L3突破 <= 1张)，锻造下游实操卡写入 wiki/ 并记入 direct_spawns
# 3. 存量主题演进: 检索讨论领域内的存量主题卡（wiki/<规范中文名>.md），调用 view_file(EndLine=手记标题前) 读取，严格按 SKILL.md §2.4 执行童子军嗅探、流变探针、收敛三级阀、时序表折叠与双向互链

# Step A5: 单篇提交原子闭环
spawned_cnt = len(direct_spawns) if direct_spawns else 0
spawned_desc = ", ".join(f"[[{w}]]" for w in direct_spawns) if spawned_cnt > 0 else "无"

aligned_cnt = len(aligned_topics) if aligned_topics else 0
aligned_desc = ", ".join(f"[[{w}]]" for w in aligned_topics) if aligned_cnt > 0 else "无"

log_text = f"""## [{date}] 摄取 | {doc.title}
- **新增资料出处 (1篇)**: [[{doc.wiki_title}]]
- **全新孵化主题 ({spawned_cnt}个)**: {spawned_desc}
- **主题对齐演进 ({aligned_cnt}个)**: {aligned_desc}"""
write_to_file(TargetFile=".scratch/log_entry.md", CodeContent=log_text, Description="生成摄取日志", Overwrite=True)

cmd = f'python .scripts/gatekeeper.py commit --file "{item.file}" --wiki "{item.target_wiki_hint}" --date "{date}" --log-file ".scratch/log_entry.md"'

if staging_terms:
    write_to_file(TargetFile=".scratch/terms.json", CodeContent=json.dumps(staging_terms, ensure_ascii=False, indent=2), Description="暂存新词表", Overwrite=True)
    cmd += ' --terms-file ".scratch/terms.json"'

if direct_spawns:  # 符合 SKILL.md §2.4 直通建页特权 (L1/L4 <= 3张, L2/L3突破 <= 1张)
    cmd += ' --cluster-wikis ' + ' '.join(f'"{w}"' for w in direct_spawns)

run_command(CommandLine=cmd)

if staging_terms:
    run_command(CommandLine="python .scripts/gatekeeper.py flush-terms")

run_command(CommandLine="python .scripts/scan_ghosts.py")
# 注: 全局队列归零核验 (assert diff == "IDLE") 由 SKILL.md 路由器外层循环统一执行
```
