---
name: wiki-curator
description: Ingest raw literature, incubate ghost topics in batch, cultivate wiki topic cards, forge bilingual wikilinks, align three-mode epistemological standards, and maintain the Second Brain knowledge network. Use when the user asks to ingest raw documents, incubate pending topics, process files in raw/, update wiki topics, or run gatekeeper workflows.
---

# 第二大脑知识摄取与维基维护工序 (Wiki Curator)

本工序为“利刃的第二大脑”核心知识流水线，负责三大知识飞轮与维护闭环：
1. **输入飞轮（文献摄取）**：将 `raw/` 原始资料转化为高信度、双链化、三态对齐的 `wiki/` 来源卡片；
2. **演进飞轮（概念孵化）**：通过幽灵雷达扫描将高共识待孵化实体批量锻造为正式 `wiki/` 主题卡片；
3. **假说飞轮（洞察沙箱）**：在 `wiki/insights/` 隔离沉淀跨文献横向对比与综合推演；
4. **审计与合流**：保持时间序列 `log.md`、受控词表 `glossary.md` 与状态账本 `raw_manifest.json` 的原子单调一致性。

> 详细规范参考文档：
> - 六级证据权威度梯队与机器约束：[`evidence_levels.md`](references/evidence_levels.md)
> - 三态认识论决策模型与主题视口模板：[`three_mode_epistemology.md`](references/three_mode_epistemology.md)

---

## 意图路由与执行场景决策

收到用户指令后，首先进行意图场景判定，直接进入对应流水线，**严禁跨场景混淆执行**：

| 用户指令/意图特征 | 匹配场景 | 核心工具链入口 |
| :--- | :--- | :--- |
| “执行摄入流程”、“摄取 raw/ 新资料”、“处理新文献” | **流水线 A：原始文献摄取** | `gatekeeper.py diff` $\to$ `view_file` $\to$ `gatekeeper.py commit` |
| “批量孵化待孵化的主题/topics”、“扫描幽灵雷达”、“孵化主题” | **流水线 B：待孵化主题批量孵化** | `scan_ghosts.py --json` $\to$ 锻造卡片 $\to$ `gatekeeper.py append-log` |
| “合流词表”、“整理受控词”、“日志归档”、“指标回填” | **流水线 C：系统维护与词表合流** | `gatekeeper.py flush-terms` / `archive-log` / `backfill-metrics` |
| “合成高阶洞察”、“跨学科映射”、“全景方案推演” | **流水线 D：合成洞察与沙箱隔离** | 写入 `wiki/insights/` $\to$ 标记 `status: draft` 隔离 |

---

## 流水线 A：原始文献摄取工序 (Raw Ingestion Pipeline)

### Step A1: 门禁差分与工具路由
1. **执行差分**：运行门禁差分命令：
   ```bash
   python .scripts/gatekeeper.py diff
   ```
   *(或兼容路径：`python .agents/skills/wiki-curator/scripts/gatekeeper.py diff`)*
2. **状态流转决策**：
   - 若返回 `{"status": "IDLE"}` 或 `diff_queue` 为空：
     - **终止工序**：输出“当前无新资料待摄取”，立即停止执行。
   - 若返回 `{"status": "PROCEED"}`：
     - 依次遍历 `diff_queue` 中的项目（`NEW`、`UPDATE`、`COLLISION_NEW`）。
     - **物理范围断言**：严格仅处理 `raw/` 根目录下的直接物理文件，任何子目录（如 `raw/fixtures/`）一律忽略。
3. **工具路由轨道断言**：
   - 若 `ingestion_track == "STANDARD"`（常规单篇轨道）：
     - 唯一合法读取工具：调用 `view_file` 读取原件。
     - 🚫 **绝对严禁调用 `slice_raw.py` 或终端脚本读文件**。
   - 若 `ingestion_track == "MASSIVE_DUAL_TRACK"`（超长分治轨道）：
     - 触达条件：物理页数 $\ge 35$ 页或端到端预估总消耗 $\ge 33,600$ Tokens。纯扫描件（字符/页 $< 30$）熔断。
     - 严格查阅文末【速查字典】，运行 `slice_raw.py inspect` $\to$ `plan-subagents` $\to$ `promote-drafts` $\to$ `audit`。

### Step A2: 提取核心要点与双时钟元数据定级
0. **强制前置参考审阅 (Mandatory Pre-flight Reference Ingestion)**：
   每次执行文献摄取，必须显式调用 `view_file` 审阅 [`references/evidence_levels.md`](references/evidence_levels.md) 与 [`references/three_mode_epistemology.md`](references/three_mode_epistemology.md)，严禁凭先验经验单方面跳过！
1. **核心要素提炼**：
   - **论文/专利 (paper)**：提炼背景问题、突破机制、量化参数与边界局限。
   - **标准/指南 (standard/guideline)**：提取核心条款、适用范围、强制分级与指标截断值。
   - **专著/报告 (book/report)**：提炼高阶架构模型、推导逻辑与方法论框架。
   - **行业分析/访谈 (general/transcript)**：提取核心论点与工程实践，过滤口语闲聊。
2. **构建文献卡片 (`wiki/资料中文标题.md`)**：
   顶部必须包含双时钟 YAML Frontmatter：
   ```yaml
   ---
   title: "文献中文完整标题"
   type: paper # paper | standard | guideline | book | report | general | transcript
   pages: 18 # 真实物理页数 (非 PDF 填 null)
   evidence_level: L3_empirical_peer_reviewed # 查阅 references/evidence_levels.md
   epistemic_status: valid # valid | disputed | superseded | retracted
   source_file: "raw/原始文件名.pdf"
   date: "YYYY-MM-DD" # [处理时钟] 业务摄取当日日期
   year: 2023 # [事件时钟] 客观公开发表年份 (4位整数，无则填 null)
   epistemic_era: 2023 # [理论发源年代] 选填，现代文章转述古典理论时标注
   tags: [顶级领域, 核心主题]
   ---
   ```
3. **写入正文**：写入文献卡片核心要点，正文中适度穿透核心概念并留下待铸模双链。

### Step A3: 靶向查词与双链铸模
1. **术语圈定**：提炼 3~5 个特异性高阶核心术语。通用耗材（移液枪、室温、离心机等）严禁打链。
2. **三级穿透检索（杜绝全量读词表）**：
   - **一级查词表**：强制目录级检索配合文件包含过滤：
     ```python
     grep_search(SearchPath=".", Includes=["glossary.md"], Query=rf"\|\s*{re.escape(术语)}\b", IsRegex=True)
     ```
   - **二级查别名**：
     ```python
     grep_search(SearchPath="wiki", Query=rf"aliases:.*\b{re.escape(术语)}\b", IsRegex=True)
     ```
   - **三级查中文基底**：剥离末尾非白名单括号后检索正文标题：
     ```python
     grep_search(SearchPath="wiki", Query=rf"^#\s*{re.escape(中文基底)}\b", IsRegex=True)
     ```
3. **双链铸模决策**：
   - 若三级检索命中任何规范文档：双链写作 `[[权威规范名称]]`。
   - 若未命中：按中英双语规范铸模为 `[[中文名称 (英文全称或缩写)]]`，并暂存至 `.scratch/terms.json` 供门禁挂账合流。

### Step A4: 存量主题对齐演进与双向拓扑织网
1. **正向安全演进区与神圣禁区划分**：
   - **神圣禁区**：`## 4. 个人思考与实战手记` 属于人类专属领域，Agent **绝对禁读、禁写、禁改、禁删**；模式 C 主题卡片的 Frontmatter 标准字段强制为 `null`，严禁虚标。
   - **合法演进区**：`## 2. 理论流变与共识演进时序表` 与 `## 5. 衍生研讨与前沿反常` 属于合法知识织网责任区，Agent 必须且应当在符合认识论规则时执行精准综合。
2. **认识论优先级与收敛决策（消解规则冲突）**：
   - **优先级公理**：**认识论模式优先级高于通用收敛阀**。若属于【模式 C 客观机理】，核心量化动力学指标直接享有入表/入正文特权。
   - **Tier 1 (范式迭代 / 跨代突破)**：重大奠基突破或最高法定标准，刷新 Frontmatter 规程字段、更新置顶视口并插入流变表。
   - **Tier 2 (重磅突破 / 关键实证 / 填补断层)**：
     - 填补了该主题流变时序表中的重大年代空白（历史跨度 $\ge 3\sim 5$ 年）；
     - 或系行业/跨国级大规模权威实证调研（大样本队列、关键工具实务断层揭示、重大反常）；
     - **必须作为 Tier 2 插入流变时序表对应年份槽位**，严禁简单粗暴作为 Tier 3 忽略！
   - **Tier 3 (常规同行实证 / 局部微小验证)**：
     - 仅当文献确属常规微小应用或重复性验证时归入此项。
     - **Tier 3 举证责任倒置反思链**：主张归入 Tier 3 前，Agent 必须在推理链中证明：“本文献既无重大时序填空，亦无量化机制突破，亦无前沿反常争议，故安全归入 Tier 3”。
     - 仅在 `## 3. 关联出处与网络` 末尾追加 `[[新增文献]]`。
3. **时序表 8 行溢出折叠算法 (Timeline Compaction Protocol)**：
   - 时序表按年份严格单调升序，基准上限为 $8\sim 9$ 行。
   - 当插入新文献导致时序表超过 8 行时，**严禁放弃记录新文献，亦严禁删除首行奠基与末行现行标准**。
   - **执行折叠合并**：找到中间年代相邻、结论相似的 2~3 个同行微小实证行，合并为单一行：
     `| YYYY-YYYY | [[文献A]] / [[文献B]] | L3_empirical_peer_reviewed | valid | validation | 多中心队列/同行复现验证与参数标定 |`
4. **双向拓扑织网 (Two-Way Topological Weaving)**：
   - 严禁仅向母主题单一方向连线！必须在新文献讨论领域内，检索关联的存量文献卡片与概念卡片，建立双向互链。
5. **衍生次要概念收敛为幽灵双链**：
   - 非核心突破的新名词，在正文中打为 `[[规范名称 (Abbr)]]` 幽灵双链，留待流水线 B 批量孵化。
   - 集群特权例外：仅限 `L1_standard` 或 `L4_industry_framework`，允许当次直接建页核心子条款（硬性限定 $\le 3$ 张，且单卡 $\ge 30$ 行实操深度）。

### Step A5: 单篇提交原子闭环与账本合流
1. **生成日志条目**：将本次提取的变更写入 `.scratch/log_entry.md`（无 BOM UTF-8）：
   ```markdown
   ## [YYYY-MM-DD] 摄取 | 资料中文标题
   - **新增资料出处 (1篇)**: [[文档卡片]]
   - **全新孵化主题 (0个)**: 无
   - **主题对齐演进 (N个)**: [[已有主题]]
   ```
2. **暂存词表导出**：若提炼出新术语，写入 `.scratch/terms.json`（UTF-8 无 BOM）：
   ```json
   [
     {"zh": "中文术语名称", "en": "English Term", "abbr": "ET"}
   ]
   ```
3. **构建确定性提交命令并执行**：
   - **常规文献命令（绝大多数场景）**：
     ```bash
     python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"]
     ```
   - **L1/L4 集群子卡特权命令（仅限 L1/L4，子卡 $\le 3$ 张且已落盘）**：
     ```bash
     python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"] --cluster-wikis "wiki/子卡1.md" "wiki/子卡2.md"
     ```
4. **挂账阈值合流**：若回执提示 `"flush_recommended": true`，立即执行 `python .scripts/gatekeeper.py flush-terms`。
5. **回归复核**：运行 `python .scripts/gatekeeper.py diff`，确认状态回归 `{"status": "IDLE"}`。

### Step A6: 能效消耗与认知交付看板
向用户汇报最终成果，并附带能耗审计看板。

---

## 流水线 B：待孵化主题雷达扫描与批量孵化工序 (Batch Topic Incubation Pipeline)

当用户发出“批量孵化待孵化的主题”、“批量孵化 topics”、“扫描幽灵雷达”等指令时执行。物理上无 `raw/` 文件参与，专注于收割高共识幽灵双链转正为正式概念卡片。

### Step B1: 幽灵雷达扫描
运行幽灵扫描命令获取全库待孵化候选列表（JSON 流解析）：
```bash
python .scripts/scan_ghosts.py --json
```

### Step B2: 准入门槛过滤与候选确认
1. **复合准入门槛模型**：
   - 核心门槛：综合得分 $\text{Score} \ge 2.0$ 且 $\text{Sources} \ge 1$；
   - 高语境门槛：$\text{Score} \ge 1.8$ 且包含 $\ge 2$ 个不同上下文出处；
2. **规范查词与消歧核验**：
   - 通过 `grep_search` 包含检索 `glossary.md` 核对其规范中英双语名称与别名；
   - 自然机理严格对齐【模式 C】，工程规范对齐【模式 B】，法定法规对齐【模式 A】。
3. **孵化计划呈现**：
   向用户清晰列出本次达标候选清单、得分、关联文献与模式。涉及批量（$\ge 3$ 个）卡片时，生成或更新 `implementation_plan.md` 供用户确认。

### Step B3: 批量锻造高质量主题卡片 (`wiki/主题名称.md`)
依据三态认识论规范撰写主题卡片。卡片物理行数严控在 50~80 行，绝对不得突破 180 行；`## 4. 个人思考与实战手记` 预留为空，**绝对禁写**。

### Step B4: 幽灵雷达重扫验证收敛
卡片全部落盘后，再次运行 `python .scripts/scan_ghosts.py --json`，验证本次孵化主题已从候选池出库，物化视图缓存同步刷新。

### Step B5: 确定性日志原子追加 (Append-Log)
批量孵化不涉及 `raw/` 物理文件，**绝不能使用 `gatekeeper commit`**，必须且仅能使用 `append-log`：
1. 将本次孵化成果写入 `.scratch/log_entry.md`（无 BOM UTF-8）；
2. 运行原子追加命令：
   ```bash
   python .scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"
   ```

### Step B6: 成果汇报与能效看板
输出批量孵化清单、收敛审计报告与能耗看板。

---

## 流水线 C：系统维护与词表合流工序 (Maintenance Pipeline)

用于第二大脑的周期性系统运维：
1. **受控词表挂账合流 (`flush-terms`)**：
   ```bash
   python .scripts/gatekeeper.py flush-terms
   ```
2. **日志周期性归档 (`archive-log`)**：
   当日志条目较多且提示 `archive_recommended: true` 时执行：
   ```bash
   python .scripts/gatekeeper.py archive-log
   ```
3. **物理指标全量回填 (`backfill-metrics`)**：
   ```bash
   python .scripts/gatekeeper.py backfill-metrics
   ```

---

## 流水线 D：合成洞察与沙箱隔离工序 (Speculative Synthesis Pipeline)

用于跨文献横向对比、跨学科映射、前沿假说推演或全景方案设计：
1. **落盘路径**：`wiki/insights/主题_YYYYMMDD.md`
2. **Frontmatter 契约**：
   ```yaml
   ---
   title: "合成洞察中文标题"
   type: speculative_synthesis
   status: draft # 初始必须为 draft；经人类确认后方可转为 verified
   tags: [顶级领域, 核心领域]
   date: YYYY-MM-DD
   sources: ["[[文献A]]", "[[文献B]]"]
   ---
   ```
3. **草稿沙箱硬隔离**：
   - 初始强制为 `status: draft`；
   - 检索工具 (`grep_search`)、幽灵扫描 (`scan_ghosts.py`) 与驾驶舱 (`index.md`) **必须过滤排除 draft 草稿**，严禁未验证假说污染底层知识网络；
   - 经人类审阅确认为 `status: verified` 后，方可作为有效高阶洞察被下游主题卡片引用。

---

## 机器脚本执行速查全景字典 (CLI Reference)

全库无头脚本标准确定性调用签名固化如下（`<file>` 与 `<wiki>` 直接代入门禁属性值；`[...]` 为可选参数；🚫 **绝对严禁调用 `--help` 探测**）：

### 1. 门禁与账本管家 (`.scripts/gatekeeper.py`)
| 操作目标 | 标准确定性命令模板 | 关键约束与前置条件 |
| :--- | :--- | :--- |
| **门禁差分** | `python .scripts/gatekeeper.py diff` | `IDLE` 立即终止；`PROCEED` 继续流转。 |
| **单篇提交 (常规)** | `python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"]` | 适用常规文献 (L2/L3/L5/L6)；严禁携带 `--cluster-wikis`；严禁翻看源码或探测帮助。 |
| **单篇提交 (法典集群)** | `python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"] --cluster-wikis "wiki/子卡1.md" "wiki/子卡2.md"` | 仅限 L1/L4 规程；子卡 $\le 3$ 张且 $\ge 30$ 行实操深度；子卡物理文件必须先落盘。 |
| **独立日志追加** | `python .scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"` | 用于流水线 B 纯主题孵化；条目必须以 `## [YYYY-MM-DD]` 开头。 |
| **挂账术语合流** | `python .scripts/gatekeeper.py flush-terms` | 提交回执提示 `"flush_recommended": true` 时执行。 |
| **切片草稿转正** | `python .scripts/gatekeeper.py promote-drafts` | 将 `.scratch/shadow_drafts/` 中合格卡片转正至 `wiki/`。 |
| **物理指标补齐** | `python .scripts/gatekeeper.py backfill-metrics` | 差分回执提示 `"backfill_recommended": true` 时执行。 |
| **日志周期归档** | `python .scripts/gatekeeper.py archive-log` | 差分回执提示 `"log_archive_recommended": true` 时执行。 |

### 2. 超长文档漏斗切片 (`.scripts/slice_raw.py`，专用于 MASSIVE_DUAL_TRACK)
| 操作目标 | 标准确定性命令模板 | 关键约束与前置条件 |
| :--- | :--- | :--- |
| **全景目录探测** | `python .scripts/slice_raw.py inspect --file "<file>" --json` | 必填 `--file`；提取 TOC、前言与符号表；常规文献严禁调用。 |
| **领域热力雷达** | `python .scripts/slice_raw.py radar --file "<file>" --json` | 必填 `--file`；可选 `--mode {normative,heuristic,descriptive}`。 |
| **前置锚点提取** | `python .scripts/slice_raw.py extract-anchor --file "<file>" --out ".scratch/anchor.md"` | 必填 `--file`；提取前 5 页定义与符号表。 |
| **分段切片提取** | `python .scripts/slice_raw.py extract-slice --file "<file>" --pages "10-25" --overlap 2 --out ".scratch/slice.txt"` | 必填 `--file` 与 `--pages`；强制滑动重叠。 |
| **子任务派发计划** | `python .scripts/slice_raw.py plan-subagents --file "<file>" --json` | 必填 `--file`；输出结构化子任务契约。 |
| **保真度审计** | `python .scripts/slice_raw.py audit --wiki "<wiki>"` | 必填 `--wiki`；剔除注释后核验完整性与拓扑深度。 |

### 3. 幽灵双链雷达 (`.scripts/scan_ghosts.py`)
| 操作目标 | 标准确定性命令模板 | 关键约束与前置条件 |
| :--- | :--- | :--- |
| **被动巡检与雷达生成** | `python .scripts/scan_ghosts.py --json` | 后台被动园艺，生成物化视图缓存；输出认知评分 $\ge 2.0$ 候选；🚫 **严禁在摄取流程中作为前置门禁调用**。 |

### 4. 自动化回归测试套件 (`.scripts/tests/`)
| 操作目标 | 标准确定性命令模板 | 关键约束与前置条件 |
| :--- | :--- | :--- |
| **全库回归测试** | `python .scripts/tests/run_tests.py` | 仅限系统架构/代码迭代验收；12项断言全绿 $\le 500$ms；🚫 **日常单篇摄取主流程严禁调用！** |

---

## 交付看板模板 (Token Consumption Dashboard)

```markdown
### 📊 任务执行完成
- **执行工序**: [文献单篇摄取 | 批量主题孵化 | 系统运维 | 合成洞察]
- **涉及卡片**: [[卡片名称列表]]
- **状态同步**: 账本 / 日志确定性落盘，闭环完成。

#### ⏱️ 能效消耗看板
| 认知推演维度 | 消耗 Token 测算 | 备注 |
| :--- | :--- | :--- |
| **原件输入 (Input)** | ~ N | 摄入原件或雷达 JSON 流 |
| **词表检索 (Grep)** | ~ N | glossary.md 正则过滤检索 |
| **存量读取 (Read)** | ~ N | 存量卡片流变与关联核验 |
| **知识写盘 (Write)** | ~ N | 新建/更新卡片与日志条目 |
| **净总能效 (Total)** | ~ N | 处于高效绿区 |
```

---

## 宪法级底线与机器边界禁令

1. **四元立柱禁令**：
   - 🚫 严禁调用 `view_file` 或编辑工具读写 `index.md`。
   - 🚫 严禁直接文本编辑或全量读取 `log.md`（必须且仅由 `gatekeeper.py` 之 `commit` 或 `append-log` 原子追加并锁守锚点）。
   - 🚫 严禁直接文本修改 `raw_manifest.json`（必须且仅由 `gatekeeper.py` 事务落盘）。
   - 🚫 严禁全量阅读 `glossary.md`，仅允许用 `grep_search` 包含过滤检索。
2. **严禁探测命令**：🚫 **绝对禁止调用任何 `--help` 命令探测脚本！所有合法命令均已在速查字典完整定义。**
3. **人类手记专属保护**：任何卡片中的 `## 4. 个人思考与实战手记` **绝对禁读、禁写、禁改、禁删**。
4. **权威标准一票否决**：`L6_informal` 绝对禁止作为事实标准出处；机理类主题 Frontmatter 强制填 `null`。
5. **合规测试场景隔离**：`run_tests.py` 仅限用于脚本底层迭代时的验收，日常摄取与孵化主流程中绝对严禁调用。
6. **脚本源码绝对禁窥（Zero Source Inspection）**：🚫 **绝对严禁调用 `view_file` 或检索工具阅读/翻看任何底层脚本源码（包括 `gatekeeper.py`、`slice_raw.py`、`scan_ghosts.py` 等）！所有无头脚本必须严格作为“确定性黑盒 CLI 接口”直接传参调用。**
7. **工作区写盘约束**：向工作区（`wiki/`、`.scratch/` 等）创建非 Artifact 文件时，🚫 **绝对严禁携带 `ArtifactMetadata` 参数**。
