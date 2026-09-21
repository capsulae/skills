---
name: wiki-curator
description: Ingest raw literature, incubate ghost topics in batch, cultivate wiki topic cards, forge bilingual wikilinks, align three-mode epistemological standards, and maintain the Second Brain knowledge network. Use when the user asks to ingest raw documents, incubate pending topics, process files in raw/, update wiki topics, or run gatekeeper workflows.
---

# 第二大脑知识摄取与维基维护工序 (Wiki Curator)

本工序为“利刃的第二大脑”核心知识流水线，负责两大核心知识飞轮与维护闭环：
1. **输入飞轮（文献摄取）**：将 `raw/` 原始资料转化为高信度、双链化、三态对齐的 `wiki/` 来源卡片；
2. **演进飞轮（概念孵化）**：通过幽灵雷达扫描将高共识待孵化实体批量锻造为正式 `wiki/` 主题卡片；
3. **审计与合流**：保持时间序列 `log.md`、受控词表 `glossary.md` 与状态账本 `raw_manifest.json` 的原子单调一致性。

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
     - 触达条件：物理页数 $\ge 35$ 页或预估总消耗 $\ge 33,600$ Tokens。
     - 进入超长分治流程（运行 `slice_raw.py inspect` $\to$ `plan-subagents` $\to$ `promote-drafts` $\to$ `audit`）。

- **完成标志 (Completion Criterion)**：差分明确完成，拿到有效任务队列，并准确锁定读取工具路由。

### Step A2: 提取核心要点与双时钟元数据定级
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

- **完成标志 (Completion Criterion)**：文献来源卡片物理落盘，YAML 字段完整合规，六级证据定级确切无误。

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

- **完成标志 (Completion Criterion)**：核心术语 100% 判定完毕，双链格式规范，无重复或歧义幽灵词。

### Step A4: 存量主题对齐演进（收敛防扩散原则）
1. **Tier 3 关联追加**：
   - 若文献与已有存量主题相关，遵循 **Tier 3 收敛阀**：严禁随意改动正文与表格！仅在该主题卡片的 `## 3. 关联出处与网络` 末尾追加 `[[新增文献]]`。
2. **衍生概念收敛为幽灵双链（核心机制）**：
   - 摄取文献时遇到的新名词、新技术或次要实体，**一律仅在正文中打为 `[[规范名称 (Abbr)]]` 幽灵双链，绝对不就地新建空卡或衍生主题卡**！
   - 让新概念自然沉淀进入幽灵池，待未来多篇文献共同引用后由流水线 B 批量孵化。
   - **集群特权例外**：仅限 `L1_standard` 或 `L4_industry_framework`，允许当次直接建页核心子条款（硬性限定 $\le 3$ 张，且单卡 $\ge 30$ 行实操深度）。

- **完成标志 (Completion Criterion)**：存量网络正确关联，次要概念作为幽灵双链合规播种，无冗余空卡。

### Step A5: 单篇提交原子闭环与账本合流
1. **生成日志条目**：将本次提取的变更写入 `.scratch/log_entry.md`（无 BOM UTF-8）：
   ```markdown
   ## [YYYY-MM-DD] 摄取 | 资料中文标题
   - **新增资料出处 (1篇)**: [[文档卡片]]
   - **全新孵化主题 (0个)**: 无
   - **主题对齐演进 (N个)**: [[已有主题]]
   ```
2. **暂存词表导出**：若提炼出新术语，必须写入 `.scratch/terms.json`（严格 UTF-8 无 BOM），字段契约固定如下：
   ```json
   [
     {"zh": "中文术语名称", "en": "English Term", "abbr": "ET"}
   ]
   ```
   *(注：若无英文缩写，abbr 填空字符串 `""` 或 `null`)*
3. **构建确定性提交命令并执行**：
   - **常规文献命令（绝大多数场景）**：
     ```bash
     python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"]
     ```
   - **L1/L4 集群子卡特权命令（仅限 L1 法定标准或 L4 行业专著，且子卡 $\le 3$ 张）**：
     ```bash
     python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"] --cluster-wikis "wiki/子卡1.md" "wiki/子卡2.md"
     ```
4. **挂账阈值合流**：
   若 commit 回执提示 `"flush_recommended": true`，立即执行：
   ```bash
   python .scripts/gatekeeper.py flush-terms
   ```
5. **回归复核**：
   运行 `python .scripts/gatekeeper.py diff`，确认状态回归 `{"status": "IDLE"}`。

- **完成标志 (Completion Criterion)**：`gatekeeper commit` 成功执行，物理哈希入账，`log.md` 尾部锚点锁守，差分状态回归 IDLE。

### Step A6: 能效消耗与认知交付看板
向用户汇报最终成果，并附带能耗审计看板（详见看板模板）。

---

## 流水线 B：待孵化主题雷达扫描与批量孵化工序 (Batch Topic Incubation Pipeline)

当用户发出“批量孵化待孵化的主题”、“批量孵化 topics”、“扫描幽灵雷达”等指令时，**立即执行本工序**。物理上无 `raw/` 文件参与，完全专注于将高共识“幽灵双链”收割转正为正式概念卡片。

### Step B1: 幽灵雷达扫描
运行幽灵扫描命令获取全库待孵化候选列表（以 JSON 结构化流解析）：
```bash
python .scripts/scan_ghosts.py --json
```
*(或兼容路径：`python .agents/skills/wiki-curator/scripts/scan_ghosts.py --json`)*

### Step B2: 准入门槛过滤与候选确认
1. **复合准入门槛模型**：
   - **核心门槛**：综合得分 $\text{Score} \ge 2.0$ 且 $\text{Sources} \ge 1$；
   - **高语境补充门槛**：$\text{Score} \ge 1.8$ 且包含 $\ge 2$ 个不同上下文主题/出处（如被多篇已建卡主题交叉引用）；
   - 低于此门槛的偶发词条继续保留在幽灵池中沉淀。
2. **规范查词与消歧核验**：
   - 对筛选出的每个候选概念，通过 `grep_search` 包含检索 `glossary.md` 核对其规范中英双语名称与别名；
   - 绝大多数自然科学机理、生化反应、数学物理模型、分析技术严格对齐 **【模式 C：客观机理】**；工程规范对齐 **【模式 B：实务范式】**；公认法规对齐 **【模式 A：法定标准】**。
3. **孵化计划呈现**：
   向用户清晰列出本次达到门禁准入门槛的候选清单、综合得分、关联文献数与认识论模式。涉及批量（$\ge 3$ 个）卡片时，生成或更新 `implementation_plan.md` 供用户把关。

### Step B3: 批量锻造高质量主题卡片 (`wiki/主题名称.md`)
依据三态认识论规范撰写主题卡片。以最普遍的 **模式 C（客观描述机理）** 为例，卡片标准范式如下：

```markdown
---
type: topic
aliases: [英文全称, 常用缩写, 别名]
tags: [一级学科/领域, 二级技术/分类]
epistemic_status: valid
standard_year: null
standard_source: null
standard_summary: null
---

# 中文标准名称 (英文简称)

> [!NOTE] 核心机理与主流共识
> - **权威出处/理论基石**：[[核心奠基文献1]] / [[核心综述文献2]]
> - **核心突破/量化基准/反应机理**：精炼提炼该技术/实体的反应机理、关键动力学参数、工作温度/浓度/极限、技术指标。
> - **适用边界与禁忌**：明确反应的干扰因素、特异性限制、假阳性/假阴性风险、严苛环境依赖。

## 1. 核心理论机制、数理推导与架构本质

### 1.1 分子动力学/微观机制与反应循环
系统阐述生化动力学模型、数理公式推导（如介电模型、热力学自由能公式等）、酶系协同或工程逻辑。

### 1.2 工业化转化与核心试剂/耗材控制红线
阐明在实际工程、实验或商业化应用中的关键控制点与禁忌。

## 2. 认识论演进、范式迁移与前沿反常

### 历史流变演进表（单调升序）
| 年份 | 关键出处 | 证据梯队 | 状态 | 演进角色 | 核心贡献与范式跃迁 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **YYYY** | [[奠基文献]] | L3_empirical_peer_reviewed | valid | foundation | 首次提出机制与核心参数 |
| **YYYY** | [[突破文献]] | L3_empirical_peer_reviewed | valid | breakthrough | 实现性能跃迁或结构突破 |

### ⚠️ 前沿反常与争议缓冲池
- 记录学术争议、未解机理、反常观测或竞争技术路径之间的学术分歧。

## 3. 关联出处与网络
- [[相关文献卡片]]
- [[相关已有主题卡片]]
- [[相关技术卡片]]

## 4. 个人思考与实战手记

```

- **物理行数与边界约束**：
  - 单卡物理行数严控在 50~80 行，绝对不得突破 180 行；
  - `## 4. 个人思考与实战手记` 预留为空，**绝对禁止代写**。

### Step B4: 幽灵雷达重扫验证收敛
卡片全部落盘后，再次运行幽灵雷达命令：
```bash
python .scripts/scan_ghosts.py --json
```
验证：本次孵化的主题已从候选池中全部出库清除（$\text{Score} \ge 2.0$ 候选全量收敛），物化视图 `.scratch/ghost_radar_cache.json` 自动更新同步。

### Step B5: 确定性日志原子追加 (Append-Log)
纯主题批量孵化不涉及 `raw/` 物理文件，**绝不能使用 `gatekeeper commit`**，必须且仅能使用门禁的 `append-log` 命令：
1. **生成日志条目**：将本次孵化成果写入 `.scratch/log_entry.md`（无 BOM UTF-8）：
   ```markdown
   ## [YYYY-MM-DD] 园艺 | 批量孵化高共识待孵化主题卡片 (N篇)
   - **全新孵化主题 (N个)**:
     - [[主题1]]: 核心机制要点与领域定位摘要 (Mode C)
     - [[主题2]]: 核心机制要点与领域定位摘要 (Mode C)
   - **知识图谱收敛**: 幽灵雷达高分候选（Score >= 2.0）全量收敛清零，刷新物化视图缓存 (.scratch/ghost_radar_cache.json)。
   ```
2. **执行原子追加命令**：
   ```bash
   python .scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"
   ```
   *(或兼容路径：`python .agents/skills/wiki-curator/scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"`)*
   回执将返回 `{"status": "APPENDED", "entry_title": "...", "total_entries": ...}`，确保 `log.md` 尾部哨兵锚点 `<!-- %% LOG_TAIL_ANCHOR %% -->` 完好无损。

### Step B6: 成果汇报与能效看板
输出批量孵化清单、收敛审计报告与 Token 能效看板。

---

## 流水线 C：系统维护与词表合流工序 (Maintenance Pipeline)

用于第二大脑的周期性系统运维：

1. **受控词表挂账合流 (`flush-terms`)**：
   将已在门禁提交中挂账的术语真正合流至 `glossary.md`：
   ```bash
   python .scripts/gatekeeper.py flush-terms
   ```
2. **日志周期性归档 (`archive-log`)**：
   当日志条目数较多（通常 $\ge 50$ 条）且回执提示 `archive_recommended: true` 时，执行：
   ```bash
   python .scripts/gatekeeper.py archive-log
   ```
3. **物理指标全量回填 (`backfill-metrics`)**：
   若存在未计算 SHA-256 或页数的老文件，执行：
   ```bash
   python .scripts/gatekeeper.py backfill-metrics
   ```

---

## 交付看板模板 (Token Consumption Dashboard)

```markdown
### 📊 任务执行完成
- **执行工序**: [文献单篇摄取 | 批量主题孵化 | 系统运维]
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

## 硬性底线与机器边界禁令

1. **四元立柱禁令**：
   - 🚫 严禁调用 `view_file` 或编辑工具读写 `index.md`。
   - 🚫 严禁直接文本编辑或全量读取 `log.md`（必须且仅由 `gatekeeper.py` 之 `commit` 或 `append-log` 原子追加并锁守锚点）。
   - 🚫 严禁直接文本修改 `raw_manifest.json`（必须且仅由 `gatekeeper.py` 事务落盘）。
   - 🚫 严禁全量阅读 `glossary.md`，仅允许用 `grep_search` 包含过滤检索。
2. **严禁探测命令**：🚫 **绝对禁止调用任何 `--help` 命令探测脚本！所有合法命令均已在三大流水线完整定义。**
3. **人类手记专属保护**：任何卡片中的 `## 4. 个人思考与实战手记` **绝对禁读、禁写、禁改、禁删**。
4. **权威标准一票否决**：`L6_informal` 绝对禁止作为事实标准出处；机理类主题 Frontmatter 强制填 `null`。
5. **合规测试场景隔离**：`run_tests.py` 仅限用于脚本底层迭代时的验收，日常摄取与孵化主流程中绝对严禁调用。
6. **脚本源码绝对禁窥（Zero Source Inspection）**：🚫 **绝对严禁调用 `view_file` 或检索工具阅读/翻看任何底层脚本源码（包括 `gatekeeper.py`、`slice_raw.py`、`scan_ghosts.py` 等）！所有无头脚本必须严格作为“确定性黑盒 CLI 接口”直接传参调用，工序已提供全部参数范式。**
7. **工作区写盘约束**：向工作区（`wiki/`、`.scratch/` 等）创建非 Artifact 文件时，🚫 **绝对严禁携带 `ArtifactMetadata` 参数**。
