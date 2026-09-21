---
name: wiki-curator
description: Ingest raw literature, cultivate wiki topic cards, forge bilingual wikilinks, align three-mode epistemological standards, and maintain the Second Brain knowledge network. Use when the user asks to ingest raw documents, process files in raw/, update wiki topics, or run gatekeeper workflows.
---

# 第二大脑知识摄取与维基维护工序 (Wiki Curator)

本工序为“利刃的第二大脑”核心知识流水线，负责将 `raw/` 原始资料转化为高信度、双链化、三态对齐的 `wiki/` 知识网络，并保持时间序列 `log.md` 与状态账本 `raw_manifest.json` 的原子单调一致性。

> 详细规范参考文档：
> - 六级证据权威度梯队与机器约束：[`evidence_levels.md`](references/evidence_levels.md)
> - 三态认识论决策模型与主题视口模板：[`three_mode_epistemology.md`](references/three_mode_epistemology.md)

---

## 工序执行链 (Ordered Steps & Completion Criteria)

### Step 1: 门禁差分与工具路由
1. **执行差分**：运行门禁差分命令：
   ```bash
   python .agents/skills/wiki-curator/scripts/gatekeeper.py diff
   ```
   *(或兼容旧命令：`python .scripts/gatekeeper.py diff`)*
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
     - 进入超长漏斗分治流程（见下文 Step 3）。

- **完成标志 (Completion Criterion)**：门禁差分明确完成，拿到有效任务队列，并准确锁定读取工具路由。

---

### Step 2: 自适应提取与双时钟元数据定级
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

---

### Step 3: 超长分治漏斗执行 (仅当触达 MASSIVE 轨道时)
1. **Pass 1 全景骨架探测**：
   ```bash
   python .agents/skills/wiki-curator/scripts/slice_raw.py inspect --file "<file>" --json
   ```
   提取目录树 (TOC)、前言与符号表，圈定概念骨架广播给后续子任务。
2. **Pass 2 自然章节分治契约**：
   运行派发契约：
   ```bash
   python .agents/skills/wiki-curator/scripts/slice_raw.py plan-subagents --file "<file>" --json
   ```
   按规划分块提取虚拟切片（内嵌真实物理页码标记），子 Agent 在 `.scratch/shadow_drafts/` 暂存中间切片。
3. **图拓扑解耦与沙箱转正**：
   - Master Hub (`wiki/主书名.md`) 承载规范全貌与页码映射。
   - 运行转正命令：
     ```bash
     python .agents/skills/wiki-curator/scripts/gatekeeper.py promote-drafts
     ```
   - 运行审计核验：
     ```bash
     python .agents/skills/wiki-curator/scripts/slice_raw.py audit --wiki "<wiki>"
     ```

- **完成标志 (Completion Criterion)**：超长文档实现无损分治映射，所有转正卡片单卡 $\le 180$ 行且通过完整性审计。

---

### Step 4: 靶向查词与双链铸模
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

---

### Step 5: 主题孵化与三态认识论对齐
1. **孵化准入判定**：
   - **L1/L4 集群孵化特权 (Mode A/B)**：对于 `L1_standard` 或 `L4_industry_framework`，允许当次直接建页关键子条款（**硬性限定 $\le 3$ 张**，且单卡正文需 $\ge 30$ 行实操深度）。
   - **L2/L3 单篇突破直通**：单篇重大独立理论突破允许直接孵化 1 张核心主题卡。
   - **被动汇聚**：其余次要概念保持幽灵双链，禁止主观随意建空卡。
2. **三态认识论模式选择 (查阅 `references/three_mode_epistemology.md`)**：
   - **模式 A（法定标准）**：填 `standard_year`, `standard_source`, `standard_summary`，置顶视口为 `[!CURRENT-STANDARD]`。
   - **模式 B（实务范式）**：填推荐基准出处与法则，置顶视口为 `[!CURRENT-GUIDELINE]`。
   - **模式 C（客观机理）**：`standard_*` 字段**强制全填 `null`**，置顶视口为 `[!NOTE]`。
3. **理论流变表维护与三级收敛阀**：
   - 按公开发表年份严格升序排列（上限 8 行）。
   - Tier 1（跨代突破）/ Tier 2（重磅补充）：插入流变表并更新视口。
   - Tier 3（常规实证）：严禁改动正文与表格！仅在 `## 3. 关联出处与网络` 末尾追加 `[[文献]]`。
   - 保护人类专属领地：`## 4. 个人思考与实战手记` 严禁读取与修改。

- **完成标志 (Completion Criterion)**：主题卡片三态对齐准确，流变表严格按年份单调升序，未越界触碰人类手记。

---

### Step 6: 单篇提交原子闭环与账本合流
1. **生成日志条目**：将本次提取的变更写入 `.scratch/log_entry.md`（无 BOM UTF-8）：
   ```markdown
   ## [YYYY-MM-DD] 摄取 | 资料中文标题
   - **新增资料出处 (1篇)**: [[文档卡片]]
   - **全新孵化主题 (N个)**: [[主题名]]
   - **主题对齐演进 (N个)**: [[已有主题]]
   ```
2. **暂存词表导出**：若提炼出新术语，必须写入 `.scratch/terms.json`（严格 UTF-8 无 BOM），字段契约固定如下（无需查阅任何脚本）：
   ```json
   [
     {"zh": "中文术语名称", "en": "English Term", "abbr": "ET"}
   ]
   ```
   *(注：若无英文缩写，abbr 填空字符串 `""` 即可)*
3. **构建确定性提交命令并执行**：
   - **常规文献命令（绝大多数场景）**：
     ```bash
     python .agents/skills/wiki-curator/scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"]
     ```
     > [!IMPORTANT]
     > **集群参数严格限定**：对于常规 L2/L3 论文、报告或网络文章，**绝对严禁传入 `--cluster-wikis`**！次要概念一律打幽灵双链等待自然孵化。
   - **L1/L4 集群子卡特权命令（仅限 L1 法定标准或 L4 行业专著，且子卡 $\le 3$ 张）**：
     ```bash
     python .agents/skills/wiki-curator/scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"] --cluster-wikis "wiki/子卡1.md" "wiki/子卡2.md"
     ```
4. **挂账阈值合流**：
   若 commit 回执提示 `"flush_recommended": true`，立即执行：
   ```bash
   python .agents/skills/wiki-curator/scripts/gatekeeper.py flush-terms
   ```

- **完成标志 (Completion Criterion)**：`gatekeeper commit` 成功执行，物理哈希入账，`log.md` 尾部锚点锁守，无脏文件残留。

---

### Step 7: 能效消耗与认知交付看板
向用户汇报最终成果，并附带能耗审计看板：
```markdown
### 📊 知识网络摄取完成
- **资料入账**: [[资料名称]] (权威等级: L3_empirical_peer_reviewed)
- **主题卡片**: [[主题名称]] (认识论对齐: 模式 C 客观机理)
- **物理账本**: 状态已同步入 `raw_manifest.json`，原子事务闭环。

#### ⏱️ 能效消耗看板
| 认知推演维度 | 消耗 Token 测算 | 备注 |
| :--- | :--- | :--- |
| **原件输入 (Input)** | ~ 8,500 | PDF 物理页数 18 页 |
| **词表检索 (Grep)** | ~ 450 | 3 次靶向包含过滤检索 |
| **存量读取 (Read)** | ~ 1,200 | 存量主题卡片流变核验 |
| **知识写盘 (Write)** | ~ 1,600 | 1 篇文献卡 + 1 篇主题对齐 |
| **净总能效 (Total)** | ~ 11,750 | 严格处于单篇高效绿区 |
```

- **完成标志 (Completion Criterion)**：用户清晰看到新卡片双链、账本更新状态以及端到端 Token 效能指标。

---

## 硬性底线与机器边界禁令

1. **四元立柱禁令**：
   - 🚫 严禁调用 `view_file` 或编辑工具读写 `index.md`。
   - 🚫 严禁直接文本编辑或全量读取 `log.md`（必须且仅由 `gatekeeper.py` 原子追加并锁守锚点）。
   - 🚫 严禁直接文本修改 `raw_manifest.json`（必须且仅由 `gatekeeper.py` 事务落盘）。
   - 🚫 严禁全量阅读 `glossary.md`，仅允许用 `grep_search` 包含过滤检索。
2. **严禁探测命令**：🚫 **绝对禁止调用任何 `--help` 命令探测脚本！**
3. **人类手记专属保护**：任何卡片中的 `## 4. 个人思考与实战手记` **绝对禁读、禁写、禁改、禁删**。
4. **权威标准一票否决**：`L6_informal` 绝对禁止作为事实标准出处；机理类主题 Frontmatter 强制填 `null`。
5. **合规测试场景隔离**：`run_tests.py` 仅限用于脚本迭代与系统级架构验收，日常单篇资料摄取主流程中绝对严禁调用。
6. **脚本源码绝对禁窥（Zero Source Inspection）**：🚫 **绝对严禁调用 `view_file` 或检索工具阅读/翻看任何底层脚本源码（包括 `gatekeeper.py`、`slice_raw.py`、`scan_ghosts.py` 等）！所有无头脚本必须严格作为“确定性黑盒 CLI 接口”直接传参调用，工序已提供全部参数范式。**
