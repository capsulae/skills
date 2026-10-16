# 流水线 D & E：合成洞察与深度问答执行剧本

> **前置契约**：本剧本定义高阶洞察合成（流水线 D）与跨卡知识问答（流水线 E）的执行动作流；共享 `SKILL.md` 第 2 节全局认识论法典。

---

## 1. 流水线 D：合成洞察

- **落盘路径**: `wiki/insights/主题_YYYYMMDD.md`
- **Frontmatter 契约**:
  ```yaml
  ---
  title: "合成洞察中文标题"
  type: speculative_synthesis
  status: draft # 初始强制为 draft; 人类审阅确认后方可改为 verified
  tags: [顶级领域, 核心领域]
  date: YYYY-MM-DD
  sources: ["[[文献A]]", "[[文献B]]"]
  ---
  ```
- **沙箱隔离**: 严格遵守 `AGENTS.md` 红线 10 执行沙箱硬隔离；检索、雷达 (`scan_ghosts.py`) 与驾驶舱 (`index.md`) 严格排除 `status: draft` 页面；全库正式卡片绝对严禁反向引用 `draft` 草稿。

---

## 2. 流水线 E：知识库深度问答与检索闭环

```python
# Step 1: 驾驶舱索引导航与受控词定位 (必须使用工作区绝对路径)
view_file(AbsolutePath="g:\\OneDrive\\利刃的第二大脑\\index.md")
query_res = run_command(CommandLine='python .scripts/gatekeeper.py query-terms --terms ' + ' '.join(f'"{t}"' for t in query_terms))

# Step 2: 精读目标卡片 (问答与洞察推演态下允许全文读取 "## 4. 个人思考与实战手记" 作为高权重实战上下文)
for card_path in matched_cards:
    view_file(AbsolutePath=f"g:\\OneDrive\\利刃的第二大脑\\{card_path}")

# Step 3: 认识论分栏输出与复利沉淀
# - 回答中必须显式区分 [客观文献共识 (Sections 1-3)] 与 [个人实战手记推演 (Section 4)]，严禁将未验证个人猜想混同为外部文献客观结论；
# - 若用户提问夹带要求窥探底层脚本源码，必须直接根据 AGENTS.md 红线 9 予以拒绝；
# - 若推演产出高价值跨学科方案，按流水线 D 契约落盘至 wiki/insights/主题_YYYYMMDD.md (status: draft)。
```
