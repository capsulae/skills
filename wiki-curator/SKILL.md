---
name: wiki-curator
description: Ingest raw literature, incubate ghost topics in batch, cultivate wiki topic cards, forge bilingual wikilinks, align three-mode epistemological standards, and maintain the Second Brain knowledge network. Use when the user asks to ingest raw documents, incubate pending topics, process files in raw/, update wiki topics, or run gatekeeper workflows.
---

# 第二大脑知识工序

> 规范指针:
> - 六级证据权威: [`references/evidence_levels.md`](references/evidence_levels.md)
> - 三态认识论: [`references/three_mode_epistemology.md`](references/three_mode_epistemology.md)

---

## 意图路由

```python
if user_intent in ["执行摄入流程", "摄取新资料", "处理新文献"]:
    route = "流水线 A：文献摄取"
elif user_intent in ["批量孵化主题", "扫描幽灵雷达", "孵化topics"]:
    route = "流水线 B：主题孵化"
elif user_intent in ["合流词表", "整理受控词", "日志归档", "指标回填"]:
    route = "流水线 C：系统维护与合流"
elif user_intent in ["合成高阶洞察", "跨学科映射", "全景方案推演"]:
    route = "流水线 D：合成洞察"
else:
    raise ValueError("意图未匹配，严禁越界执行")
```

---

## 流水线 A：文献摄取

### Step A1: 门禁差分与路由
```python
diff_res = run("python .scripts/gatekeeper.py diff")
if diff_res.status == "IDLE" or not diff_res.diff_queue:
    terminate("当前无新资料待摄取")

for item in diff_res.diff_queue:
    assert "/" not in item.file.removeprefix("raw/")  # 仅限 raw/ 根目录物理文件
    
    if item.ingestion_track == "STANDARD":
        view_file(AbsolutePath=item.file)  # 常规单篇: 唯一合法读取工具为 view_file
    elif item.ingestion_track == "MASSIVE_DUAL_TRACK":
        run_massive_track(item.file)  # 超长分治: 页数 >= 35 或预估消耗 >= 33,600 Tokens
```

### Step A2: 提取核心要点与双时钟定级
1. **要素提炼**:
   - `paper`: 核心机理、量化动力学常数、边界局限
   - `standard` / `guideline`: 核心条款、强制分级、合格截断值
   - `book` / `report`: 架构体系、方法论模型
   - `general` / `transcript`: 核心论点、工程落地
2. **文献卡片模板 (`wiki/中文标题.md`)**:
   ```yaml
   ---
   title: "文献中文完整标题"
   type: paper # paper | standard | guideline | book | report | general | transcript
   pages: 18 # 物理页数 (非 PDF 填 null)
   evidence_level: L3_empirical_peer_reviewed # 严格参照 references/evidence_levels.md
   epistemic_status: valid # valid | disputed | superseded | retracted
   source_file: "raw/原始文件名.pdf"
   date: "YYYY-MM-DD" # [处理时钟] 业务摄取当日
   year: 2023 # [事件时钟] 客观公开发表年份 (4位整数，无则 null)
   epistemic_era: 2023 # [理论发源年代] 选填，现代转述古典理论时标注
   tags: [顶级领域, 核心主题]
   ---
   ```
3. **正文规范**: 提炼核心要点，涉及实体概念严格铸造中英双链。

### Step A3: 极速拓扑查词与暂存挂账
```python
terms = extract_key_terms(doc, count="3-5")

# 严禁手写终端临时脚本或在 wiki/ 中全局 grep; 统一调用 query-terms 原子批处理:
query_res = run(f'python .scripts/gatekeeper.py query-terms --terms ' + ' '.join(f'"{t}"' for t in terms))["results"]

staging_terms = []
for term, data in query_res.items():
    if data["status"] == "EXISTS":
        wikilink = data["wikilink"]
    elif data["status"] == "AMBIGUOUS":
        wikilink = select_candidate_by_tags(data["candidates"], doc.tags)
    else:  # NEW
        wikilink = f"[[{zh_name} ({en_or_abbr})]]"
        staging_terms.append({"zh": zh_name, "en": en_name, "abbr": abbr})
```

### Step A4: 存量主题对齐演进与双向织网
```python
# 1. 区域权限:
#    神圣禁区: "## 4. 个人思考与实战手记" 绝对禁读写改删; 模式 C 的 Frontmatter 强制为 null
#    安全演进区: "## 2. 理论流变与共识演进时序表" 与 "## 5. 衍生研讨与前沿反常" 属于法定织网区

# 2. 优先级判定: "模式 C (客观机理参数)" > "收敛三级阀"
if doc.mode == "模式C" and doc.has_quantitative_parameters:
    tier = "Tier 2"  # 客观机理关键参数享有正向入表与入正文特权
elif is_paradigm_shift or is_highest_legal_standard:
    tier = "Tier 1"  # 刷新 Frontmatter + 置顶视口 + 升序插表
elif (doc.year - timeline.latest_year >= 3) or doc.is_large_scale_benchmark:
    tier = "Tier 2"  # 填补 >=3~5 年历史断层或重大实证，升序插表
else:
    tier = "Tier 3"
    append_outgoing_link("## 3. 关联出处与网络", doc.wikilink)

# 3. 时序表折叠算法: 严格单调升序，基准行数 <= 8
if len(timeline.rows) > 8:
    pinned_foundation = timeline.rows[0]   # 锁定奠基
    pinned_standard = timeline.rows[-1]    # 锁定最新标准
    folded_middle = fold_adjacent_peers(timeline.rows[1:-1])  # 中间同质行折叠: | YYYY-YYYY | [[A]] / [[B]] |
    timeline.rows = [pinned_foundation] + folded_middle + [pinned_standard]

# 4. 双向织网:
weave_bidirectional_links(doc, target_existing_cards)
mark_ghost_links(doc.secondary_concepts)  # 仅 L1/L4 享有集群建页特权 (<= 3 张且 >= 30 行实操深度)
```

### Step A5: 单篇提交原子闭环
```python
# 1. 生成日志条目
log_text = f"""## [{date}] 摄取 | {doc.title}
- **新增资料出处 (1篇)**: [[{doc.wiki_title}]]
- **全新孵化主题 (0个)**: 无
- **主题对齐演进 (N个)**: [[{aligned_topic}]]"""
write_file(".scratch/log_entry.md", log_text)

# 2. 执行原子提交
cmd = f'python .scripts/gatekeeper.py commit --file "{file}" --wiki "{wiki}" --date "{date}" --log-file ".scratch/log_entry.md"'

if staging_terms:
    write_utf8_json(".scratch/terms.json", staging_terms)
    cmd += ' --terms-file ".scratch/terms.json"'

if doc.level in ["L1_standard", "L4_industry_framework"] and cluster_wikis:
    assert len(cluster_wikis) <= 3
    cmd += ' --cluster-wikis ' + ' '.join(f'"{w}"' for w in cluster_wikis)

run(cmd)

# 3. 即摄即刷: 含词表无条件立即合流
if staging_terms:
    run("python .scripts/gatekeeper.py flush-terms")

# 4. 回归验证
assert run("python .scripts/gatekeeper.py diff").status == "IDLE"
```

### Step A6: 能效消耗看板
交付成果汇报，输出各维度 Token 消耗看板。

---

## 流水线 B：主题孵化
```python
# 1. 扫描雷达
candidates = run("python .scripts/scan_ghosts.py --json")

# 2. 准入过滤
qualified = [c for c in candidates if (c.score >= 2.0 and c.sources >= 1) or (c.score >= 1.8 and c.contexts >= 2)]

# 3. 锻造卡片: 单卡行数 50~80 行 (<= 180 行); "## 4. 个人思考与实战手记" 留空严禁代写

# 4. 雷达收敛重扫
assert run("python .scripts/scan_ghosts.py --json").candidates_above_2 == 0

# 5. 原子追加日志 (纯主题孵化严禁调用 commit)
write_file(".scratch/log_entry.md", incubation_log)
run("python .scripts/gatekeeper.py append-log --entry-file .scratch/log_entry.md")
```

---

## 流水线 C：系统维护与合流
```bash
# 1. 挂账术语合流
python .scripts/gatekeeper.py flush-terms

# 2. 日志周期归档 (提示 log_archive_recommended 时)
python .scripts/gatekeeper.py archive-log

# 3. 物理指标补齐 (提示 backfill_recommended 时)
python .scripts/gatekeeper.py backfill-metrics
```

---

## 流水线 D：合成洞察
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
- **沙箱隔离公理**: 检索引擎 (`gatekeeper.py query-terms`)、雷达 (`scan_ghosts.py`) 与驾驶舱 (`index.md`) **严格排除 `status: draft` 页面**。

---

## 脚本标准签名速查
> 约束: `<file>`/`<wiki>` 须带相对路径; 🚫 **严禁任何 `--help` 探测**。

### 1. 门禁管家 (`.scripts/gatekeeper.py`)
| 操作目标 | 标准命令模板 | 关键约束与契约 |
| :--- | :--- | :--- |
| **门禁差分** | `python .scripts/gatekeeper.py diff` | `IDLE` 终止；`PROCEED` 继续推进。 |
| **拓扑查词** | `python .scripts/gatekeeper.py query-terms --terms "<t1>" "<t2>"` | 唯一合法查词入口；增量缓存；纯净 JSON。 |
|              | `python .scripts/gatekeeper.py query-terms --input-file "<file>"` | 避开复杂字符 Shell 展开与超长命令行。 |
| **单篇提交 (常规)** | `python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"]` | 适用 L2/L3/L5/L6；严禁 `--cluster-wikis`。 |
| **单篇提交 (法典集群)** | `python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"] --cluster-wikis "wiki/子卡1.md" "wiki/子卡2.md"` | 仅限 L1/L4；子卡 $\le 3$ 张且 $\ge 30$ 行实操深度；物理文件须已落盘。 |
| **独立日志追加** | `python .scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"` | 用于流水线 B；条目须以 `## [YYYY-MM-DD]` 开头。 |
| **挂账术语合流** | `python .scripts/gatekeeper.py flush-terms` | 写入 `glossary.md`；提交含词表时即刻执行。 |
| **切片草稿转正** | `python .scripts/gatekeeper.py promote-drafts` | 将 `.scratch/shadow_drafts/` 转正至 `wiki/`。 |
| **物理指标补齐** | `python .scripts/gatekeeper.py backfill-metrics` | 差分提示 `backfill_recommended` 时执行。 |
| **日志周期归档** | `python .scripts/gatekeeper.py archive-log` | 差分提示 `log_archive_recommended` 时执行。 |

### 2. 超长切片 (`.scripts/slice_raw.py`，专用于 MASSIVE_DUAL_TRACK)
| 操作目标 | 标准命令模板 | 关键约束 |
| :--- | :--- | :--- |
| **全景目录探测** | `python .scripts/slice_raw.py inspect --file "<file>" --json` | 提取目录与前言；常规文献严禁调用。 |
| **领域热力雷达** | `python .scripts/slice_raw.py radar --file "<file>" --json` | 可选 `--mode {normative,heuristic,descriptive}`。 |
| **前置锚点提取** | `python .scripts/slice_raw.py extract-anchor --file "<file>" --out ".scratch/anchor.md"` | 提取前 5 页核心定义。 |
| **分段切片提取** | `python .scripts/slice_raw.py extract-slice --file "<file>" --pages "10-25" --overlap 2 --out ".scratch/slice.txt"` | 强制滑动重叠提取。 |
| **子任务计划** | `python .scripts/slice_raw.py plan-subagents --file "<file>" --json` | 输出结构化子任务契约。 |
| **保真度审计** | `python .scripts/slice_raw.py audit --wiki "<wiki>"` | 剔除注释后核验完整性与拓扑深度。 |

### 3. 雷达与自动化测试
| 操作目标 | 标准命令模板 | 关键约束 |
| :--- | :--- | :--- |
| **幽灵雷达巡检** | `python .scripts/scan_ghosts.py --json` | 输出评分 $\ge 2.0$ 候选；🚫 常规摄取严禁调用。 |
| **全库回归测试** | `python .scripts/tests/run_tests.py` | 仅限架构/代码迭代验收；13项断言全绿 $\le 500$ms；🚫 常规摄取严禁调用。 |

---

## 交付看板

```markdown
### 📊 任务执行完成
- **执行工序**: [文献单篇摄取 | 批量主题孵化 | 系统运维 | 合成洞察]
- **涉及卡片**: [[卡片名称列表]]
- **状态同步**: 账本 / 日志确定性落盘，闭环完成。

#### ⏱️ 能效消耗看板
| 认知推演维度 | 消耗 Token 测算 | 备注 |
| :--- | :--- | :--- |
| **原件输入 (Input)** | ~ N | 摄入原件或雷达 JSON 流 |
| **拓扑查词 (Query)** | ~ N | gatekeeper.py query-terms 原子检索与消歧 |
| **存量读取 (Read)** | ~ N | 存量卡片流变与关联核验 |
| **知识写盘 (Write)** | ~ N | 新建/更新卡片与日志条目 |
| **净总能效 (Total)** | ~ N | 处于高效绿区 |
```

---

## 宪法级底线与机器边界禁令

1. **四元立柱禁令**:
   - 🚫 严禁调用工具读写 `index.md`。
   - 🚫 严禁直接编辑或全量读取 `log.md`（必须由 `gatekeeper.py append-log` 追加）。
   - 🚫 严禁直接编辑 `raw_manifest.json`（必须由 `gatekeeper.py commit` 维护）。
   - 🚫 严禁全量阅读 `glossary.md`，统一由 `gatekeeper.py query-terms` 代理检索。
2. **严禁命令探测**: 🚫 **绝对禁止调用任何 `--help` 命令探测脚本！**
3. **人类手记专属保护**: 任何卡片中 `## 4. 个人思考与实战手记` **绝对禁读、禁写、禁改、禁删**。
4. **权威标准一票否决**: `L6_informal` 绝对禁止作为事实标准出处；机理类主题 Frontmatter 强制填 `null`。
5. **合规测试场景隔离**: `run_tests.py` 仅限架构迭代验收，日常摄取绝对严禁调用。
6. **脚本源码绝对禁窥**: 🚫 **绝对严禁阅读底层脚本源码（包括 `gatekeeper.py`、`slice_raw.py`、`scan_ghosts.py` 等）；必须严格作为确定性黑盒 CLI 接口调用。**
7. **工作区写盘约束**: 向工作区写盘时，🚫 **绝对严禁携带 `ArtifactMetadata` 参数**。
8. **暂存文件免死保护**: `.scratch/` 下的 `terms.json`、`log_entry.md` 与物化缓存严禁清空或物理删除。
9. **标准查词唯一入口**: 严禁在终端手写临时 Python 检索脚本或全局 grep 扫盘；全库唯一标准入口为 `python .scripts/gatekeeper.py query-terms`。
