# 流水线 B：主题批量孵化执行剧本

> **前置契约**：本剧本仅定义幽灵主题批量孵化的有序执行动作流；所有证据定级（§2.1）、三态四段式主题卡模板（§2.2(2)）与存量织网演进（§2.4）均直接调用 `SKILL.md` 第 2 节全局法典。

---

## 执行工步序列

```python
# Step 1: 扫描幽灵雷达
candidates = run_command(CommandLine="python .scripts/scan_ghosts.py --json")

# Step 2: 准入阈值过滤与批量确认
qualified = [c for c in candidates if (c.score >= 2.0 and c.sources >= 1) or (c.score >= 1.8 and c.contexts >= 2)]
if len(qualified) >= 3:
    update_plan("implementation_plan.md", qualified)  # 批量呈现供确认

# Step 3: 批量锻造三态主题卡与双向织网
# - 查阅关联来源卡片时，调用 view_file(EndLine=手记标题前) 截断读取；
# - 严格按 SKILL.md §2.2(2) 模板生成四段式主题卡片，单卡行数严控在 50~80 行 (绝对 <= 180 行)，"## 4. 个人思考与实战手记" 留空严禁代写；
# - 若关联织网中触达非三态或残缺历史卡片，按 SKILL.md §2.4 触发童子军法则就地升级。

# Step 4: 雷达收敛重扫核验 (确认当批已批准孵化的主题已从幽灵雷达消除；若全量孵化则 candidates_above_2 == 0)
rescan_res = run_command(CommandLine="python .scripts/scan_ghosts.py --json")
assert not any(t in rescan_res for t in approved_targets)

# Step 5: 原子追加独立日志 (纯主题批量孵化严禁调用 commit，必须且仅能使用 append-log)
incubation_cnt = len(approved_targets)
incubation_log = f"""## [{date}] 批量孵化 | 待孵化概念与实体池批量孵化 ({incubation_cnt}项)
- **全新孵化主题 ({incubation_cnt}个)**:
""" + "\n".join(f"  - [[{t}]]" for t in approved_targets)
write_to_file(TargetFile=".scratch/log_entry.md", CodeContent=incubation_log, Description="记录批量主题孵化日志", Overwrite=True)
run_command(CommandLine='python .scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"')
```
