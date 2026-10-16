---
name: wiki-curator
description: Ingest raw literature, incubate ghost topics in batch, cultivate wiki topic cards, forge bilingual wikilinks, align three-mode epistemological standards, and maintain the Second Brain knowledge network. Use when the user asks to ingest raw documents, incubate pending topics, process files in raw/, update wiki topics, query the knowledge base, or run gatekeeper workflows.
---

# 第二大脑知识编译法典与主干路由器

> **架构正交原则**：
> - **`AGENTS.md`**：定义全局物理立柱访问边界与不可逾越之安全红线；
> - **`SKILL.md` (本文件)**：定义**顶层意图路由**与**所有流水线 100% 共享的通用认识论法典、卡片模板、查词准入与演进算法**；
> - **`references/pipeline_*.md`**：定义各分支互斥的**纯执行工步流**（每次仅按路由加载唯一对应的 1 个剧本文件）。

---

## 1. 顶层意图与轨道路由器 (动态消费闭环)

```python
if user_intent in ["执行摄入流程", "摄取新资料", "处理新文献", "摄取新文献", "推进门禁队列"]:
    # 动态消费循环: 逐篇消化，杜绝并发混读
    while True:
        diff_res = run_command(CommandLine="python .scripts/gatekeeper.py diff")
        if diff_res.status == "IDLE" or not diff_res.diff_queue:
            break
        item = diff_res.diff_queue[0]  # 每次锁定消费队首第一篇
        assert "/" not in item.file.removeprefix("raw/")
        
        if item.ingestion_track == "STANDARD":
            view_file(AbsolutePath="g:\\OneDrive\\利刃的第二大脑\\.agents\\skills\\wiki-curator\\references\\pipeline_a_standard.md")
        elif item.ingestion_track == "MASSIVE_DUAL_TRACK":
            view_file(AbsolutePath="g:\\OneDrive\\利刃的第二大脑\\.agents\\skills\\wiki-curator\\references\\pipeline_a_massive.md")
            
    # 全队列消费完毕总体验收
    assert run_command(CommandLine="python .scripts/gatekeeper.py diff")["status"] == "IDLE"

elif user_intent in ["批量孵化主题", "扫描幽灵雷达", "孵化topics", "扫描幽灵主题", "维护wiki卡片"]:
    view_file(AbsolutePath="g:\\OneDrive\\利刃的第二大脑\\.agents\\skills\\wiki-curator\\references\\pipeline_b_incubate.md")

elif user_intent in ["合流词表", "整理受控词", "日志归档", "指标回填"]:
    # 流水线 C：系统维护与合流
    run_command(CommandLine="python .scripts/gatekeeper.py flush-terms")
    # 提示 log_archive_recommended 时执行: python .scripts/gatekeeper.py archive-log
    # 提示 backfill_recommended 时执行: python .scripts/gatekeeper.py backfill-metrics

elif user_intent in ["合成高阶洞察", "跨学科映射", "全景方案推演", "合成洞察", "知识库问答", "检索知识库"]:
    view_file(AbsolutePath="g:\\OneDrive\\利刃的第二大脑\\.agents\\skills\\wiki-curator\\references\\pipeline_d_e_insight_query.md")

else:
    raise ValueError("意图未匹配，严禁越界执行")
```

---

## 2. 全局通用认识论与数据契约法典 (所有流水线强制共享)

### 2.1 六级证据权威度梯队与裁决铁律

| 等级标识符 | 定位与核心范畴 | 代表出处示例 | 认识论角色 | 机器约束 |
| :--- | :--- | :--- | :--- | :--- |
| **`L1_standard`** | 国际/国家法定规程标准、官方临床指南、强制法规、数学公理 | ISO/IEC 标准、GB/T、RFC、FDA 最终法规、FIGO/WHO 官方临床指南 | 法定标准、公理底座 | **最高规程**：直接裁决技术指标；享有 Mode A 直通建页特权（$\le 3$ 张子卡）。 |
| **`L2_causal_synthesis`** | 顶级同行评议 Meta 分析、多中心前瞻双盲 RCT、重大数学定理证明 | Cochrane 系统评价、Lancet/NEJM 大样本 RCT、重大数学猜想证明 | 最高因果实证 | **最高实证**：具有挑战或验证既有标准的能力；可直通建 1 张核心卡。 |
| **`L3_empirical_peer_reviewed`** | 常规期刊同行评议学术论文、高价值授权发明专利、单中心队列 | IEEE/ACM 会议论文、行业顶刊论文、授权发明专利说明书 | 主流同行实证 | **常规实证**：支撑具体参数、机制与工艺细节；可直通建 1 张核心卡。 |
| **`L4_industry_framework`** | 头部机构官方技术规范与架构文档、行业白皮书、经典奠基专著 | W3C 规范、大型开源基金会架构白皮书、GoF《设计模式》、DDD 奠基之作 | 架构实践与推荐范式 | **实务规范**：采用 Mode B（推荐基准）；享有集群孵化特权（$\le 3$ 张子卡）。 |
| **`L5_exploratory`** | 预印本、早期探索试错、单一案例报告、实验方案初稿 | arXiv/bioRxiv 预印本、单一临床病例报道、实验室内部初稿 | 探索性假说与异常捕获 | **探索假说**：严禁作为现行权威标准；若与 L1~L3 冲突只能进入反常缓冲池。 |
| **`L6_informal`** | 微信公众号、技术博客、行业快讯、媒体通稿、非正式网络文章 | 微信公众号技术贴、CSDN/掘金文章、科技媒体通稿、知乎回答 | 纯非正式参考 | 🚫 **一票否决**：**绝对严禁作为 L1/L2/L3 的事实依据或主题卡的 `standard_source`**！ |

1. **L6 一票否决与兜底降级**：任何 `L6_informal` 资料严禁在主题卡 Frontmatter 中被引用为 `standard_source`；出处含糊或仅有 L5/L6 支撑时，置顶视口强制降级为 `> [!INFO] 现行工程经验与探索假说`，且主题卡 `standard_year`、`standard_source`、`standard_summary` 强制全填 `null`。
2. **转引穿透资格门禁**：
   - 转引穿透特权**仅赋予 L2（Meta/RCT）及 L3/L4（同行评议顶刊/专著）**；
   - 🚫 **严禁 L5（预印本）与 L6 享有转引穿透特权**！L5 即使提及确切 L1 标准，其主题卡视口依然强制为 `[!INFO]` 或进入反常池，绝对严禁为存量权威标准加冕；
   - 符合资格且原始出处确切时，格式必须外层双引号包裹：`"[[权威组织或标准规范]] (转引自 [[次级转述文献卡片名称]])"`。
3. **数学奠基与物理公理永久保真**：基础数学公理、经严格检验的定理与基础物理定律（如 Shannon 信息熵定理、热力学定律）具备永久真值，严禁因年份古老被标为 `superseded`。

---

### 2.2 三态认识论本质分类与双卡标准 Schema

| 认识论维度 | 【模式 A：法定规程标准】 | 【模式 B：实务推荐范式】 | 【模式 C：客观描述机理】 |
| :--- | :--- | :--- | :--- |
| **本体本质** | 具有法定强制力、准入约束力或契约效力的标准 (ISO, RFC, FIGO, 国家标准) | 软件工程范式、管理方法论、工程经验法则 (OKR, DDD, 敏捷, 设计模式) | 自然物理化学规律、试剂原料、生化反应、数学算法推导 (EDTA, PCR, 贝叶斯滤波) |
| **主题卡 YAML** | `standard_year: 2023`<br>`standard_source: "[[权威组织或规范]]"`<br>`standard_summary: "强制指标/截断值/合格准则"` | `standard_year: 2018`<br>`standard_source: "[[奠基专著或头部机构]]"`<br>`standard_summary: "核心推荐法则/黄金准则"` | `standard_year: null`<br>`standard_source: null`<br>`standard_summary: null`<br>*(模式 C 强制全填 null，严禁虚标！)* |
| **置顶视口类型** | `> [!CURRENT-STANDARD] 法定规程标准` | `> [!CURRENT-GUIDELINE] 推荐范式与实效基准` | `> [!NOTE] 核心机理与主流共识` |

#### (1) 文献卡片标准 Frontmatter 模板 (`item.target_wiki_hint`)
```yaml
---
title: "文献中文完整标题"
type: paper # paper | standard | guideline | book | report | general | transcript
pages: 18 # 真实物理页数 (非 PDF 填 null)
evidence_level: L3_empirical_peer_reviewed
epistemic_status: valid # valid | disputed | superseded | retracted
source_file: "raw/原始文件名.pdf"
date: "YYYY-MM-DD" # [处理时钟] 业务摄取当日
year: 2023 # [事件时钟] 客观公开发表年份 (4位整数，无则填 null)
epistemic_era: 2023 # [理论发源年代] 选填，现代转述古典理论时标注
tags: [顶级领域, 核心主题]
---
```
> **四类文献核心要素提炼法则 (全局共享)**:
> - `paper`: 背景问题、突破机制、量化动力学参数、边界局限
> - `standard` / `guideline`: 核心条款、适用范围、强制分级、指标截断值
> - `book` / `report`: 架构模型、推导逻辑、方法论框架
> - `general` / `transcript`: 核心论点、工程实践，过滤口语闲聊

#### (2) 主题卡片完整四段式合并模板 (`wiki/<规范中文名>.md`)
```markdown
---
type: topic
aliases: [英文全称, 英文缩写, 通俗别名]
tags: [一级领域, 二级分类]
epistemic_status: valid # valid | disputed | superseded
standard_year: 2023 # 模式 C 强制填 null
standard_source: "[[权威组织或奠基专著]]" # 模式 C 强制填 null
standard_summary: "核心量化参数或黄金法则" # 模式 C 强制填 null
---

# 主题名称 (英文全称 / 缩写)

> [!CURRENT-STANDARD] 现行权威规范与实践基准
> (模式 B 使用 [!CURRENT-GUIDELINE]，模式 C 使用 [!NOTE]，降级使用 [!INFO])
> - **权威出处/理论基石**：[[代表性文献/组织]] (年份, 作者/机构)
> - **核心突破/量化基准/反应机理**：推荐参数、接口契约、数学模型或反应方程式。
> - **适用边界与禁忌**：应用前提、排他性禁忌与已知局限性。

## 1. 核心理论机制、数理推导与架构本质
(提炼底层科学原理、物理机制、推导逻辑或系统拓扑架构)

## 2. 理论流变与共识演进时序表
(按文献公开发表年份严格升序单调排列，上限 8 行；模式 C 豁免时间差，按发表年份直接插槽)
| 年份 | 代表出处 / 算法 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2017** | [[文献A]] | L2_causal_synthesis | valid | foundation | 确立现代范式奠基，严格因果证明 |
| **2023** | [[文献B]] | L1_standard | valid | standard | 国际组织正式确立现行法定规程 |

### ⚠️ 前沿反常与争议缓冲池
(记录与现行标准冲突但属于早期探索的反常证据；无反常时可略)

## 3. 关联出处与网络
- [[里程碑出处A]]
- [[常规验证出处B (Tier 3 仅挂链不入表)]]

## 4. 个人思考与实战手记
```

---

### 2.3 术语圈定准入标准与拓扑查词公理

1. **五大负向类别一票否决（严禁打双链或加入 `terms.json`）**：
   - ① 通用器皿耗材：枪头/吸头、离心管/EP管/PCR管、多孔板/酶标板、载玻片/盖玻片、培养皿/瓶、滤膜/滤纸等；
   - ② 基础溶剂试剂：水/超纯水/蒸馏水/ddH2O、生理盐水、PBS、乙醇、DMSO、常规缓冲液等；
   - ③ 通用仪器器具：移液器/移液枪、离心机、天平、水浴锅、摇床/振荡器、超净台、通风橱、冰箱等；
   - ④ 基础工步环境：室温/常温/冰浴/过夜、洗涤、孵育、离心条件等；
   - ⑤ 科研通用统计：对照组、空白组、阴性/阳性对照、p值、显著性、误差线、样本量等。
   - ✅ **正向准入标准**：每篇提炼 3~5 个特异性生物分子/靶点、新型独创技术/算法、专有疾病表型或法定标准规程。
2. **拓扑查词消歧逻辑 (`gatekeeper.py query-terms`)**：
```python
query_res = run_command('python .scripts/gatekeeper.py query-terms --terms ' + ' '.join(f'"{t}"' for t in terms))["results"]
staging_terms = []
for term, data in query_res.items():
    if data["status"] == "EXISTS":
        wikilink = data["wikilink"]  # 强制使用返回成品 wikilink，严禁别名分裂；存量路径严格等于 wiki/<规范中文名>.md
    elif data["status"] == "AMBIGUOUS":
        wikilink = select_candidate_by_tags(data["candidates"], doc.tags)
    else:  # NEW
        wikilink = f"[[{zh_name} ({en_or_abbr})]]"
        staging_terms.append({"zh": zh_name, "en": en_name, "abbr": abbr})
```

---

### 2.4 存量主题演进、收敛三级阀与拓扑扩张公理

```python
# 1. 格式世代嗅探 (童子军法则，触达存量卡时最高优先级前置执行):
# 检查是否缺失 standard_year/source/summary、三态置顶视口，或缺失 "## 1."、"## 2."、"## 4. 个人思考与实战手记"
is_legacy_format = missing_three_mode_yaml_or_viewport(card) or missing_four_sections(card)

# 2. 模式 A/B 跨代流变决策探针:
if mode in ["模式A", "模式B"]:
    delta_T = new_doc.year - standard_year
    if abs(delta_T) <= 2:  # 同代演化窗口 (<= 2年)
        mark("disputed" if contradictory else "corroborated")  # 一致则标为独立同行复现 corroborated，严禁误标为 disputed！
    elif delta_T > 2:  # 前向跨代演进
        if new_doc.level >= standard_level:
            mark_old_as("superseded")
            refresh_standard_viewport()
        elif new_doc.level == "L2" and standard_level == "L1" and falsified:
            add_viewport_alert("CRITICAL-DISCREPANCY")
        else:
            add_to_anomaly_buffer()
    else:  # delta_T < -2 (历史回溯)
        role = "historical"

# 3. 认识论优先级与收敛三级阀:
if is_legacy_format:
    upgrade_to_three_mode_standard(card)  # 强制豁免 Tier 3，就地升格为 2.2 标准三态四段式卡片（保留手记隔离领地）
elif is_paradigm_shift:
    tier = "Tier 1"  # 范式颠覆刷新置顶视口与核心表（模式 C 锁定 [!NOTE] 且严禁修改 standard_*）
elif doc.mode == "模式C" and (doc.has_quantitative_parameters or doc.has_mechanism_breakthrough):
    tier = "Tier 2"  # 模式 C 重大机理突破与关键量化参数正向入表与入正文
elif is_highest_legal_standard:
    tier = "Tier 1"  # 模式 A/B 最高法定标准刷新 Frontmatter 与置顶视口
elif (doc.year - timeline.latest_year >= 3) or doc.is_large_scale_benchmark:
    tier = "Tier 2"  # 填补 >=3~5 年历史断层或关键实证，强制升序插表
else:
    tier = "Tier 3"
    assert no_gap_fill and no_mechanism_breakthrough and no_paradigm_shift
    append_outgoing_link("## 3. 关联出处与网络", doc.wikilink)

# 4. 时序表折叠算法: 严格单调升序，上限 8~9 行 (锁定首行奠基与末行现行标准)
# 中间同行合并模板: | YYYY-YYYY | [[文献A]] / [[文献B]] | L3_empirical_peer_reviewed | valid | validation | 多中心队列/同行复现验证与参数标定 |
if len(timeline.rows) > 8:
    timeline.rows = [timeline.rows[0]] + fold_adjacent_peers(timeline.rows[1:-1]) + [timeline.rows[-1]]

# 5. 直通建页特权与细胞分裂:
if item.ingestion_track == "MASSIVE_DUAL_TRACK":
    assert 1 <= len(cluster_wikis) <= 5  # 超长分治必须派生 1~5 张下游实操主题卡
elif doc.level in ["L1_standard", "L4_industry_framework"]:
    max_direct_spawns = 3  # 法典集群特权: <= 3 张且 >= 30 行实操深度
elif doc.level in ["L2_causal_synthesis", "L3_empirical_peer_reviewed"] and is_paradigm_breakthrough:
    max_direct_spawns = 1  # 范式突破特权: 允许直通建 1 张核心卡
else:
    max_direct_spawns = 0  # 其余次要概念统一打为 [[规范名称 (Abbr)]] 幽灵双链

if card.lines > 180:
    split_card(master_as_hub=True, spawn_subcards=True)  # 单卡 > 180 行时主卡转为 Master Hub 并派生子卡细胞分裂
```

---

## 3. 门禁管家核心命令字典与熔断自愈协议 (`.scripts/gatekeeper.py`)

> ⚡ **脚本报错熔断自愈协议 (Max Retry = 1)**：
> 1. 若命令返回非零码，仅允许对照下表检查参数后执行 **最多 1 次修正重试**；
> 2. 🚫 **黑盒铁律**：即使 stderr 包含 `.scripts/*.py` 的 Traceback 报错堆栈，也**绝对严禁调用 `view_file` 或终端命令窥探源码**！
> 3. 若修正 1 次后仍报错，**立即熔断中断工序，向人类输出原始错误信息求助**。

| 操作目标 | 标准确定性命令模板 | 关键约束与前置条件 |
| :--- | :--- | :--- |
| **门禁差分** | `python .scripts/gatekeeper.py diff` | `IDLE` 终止；`PROCEED` 继续流转。 |
| **拓扑查词** | `python .scripts/gatekeeper.py query-terms --terms "<t1>" "<t2>"` | 唯一合法查词入口；支持 `--input-file "<file>"`。 |
| **单篇提交** | `python .scripts/gatekeeper.py commit --file "<file>" --wiki "<wiki>" --date "YYYY-MM-DD" --log-file ".scratch/log_entry.md" [--terms-file ".scratch/terms.json"] [--cluster-wikis "<w1>" "<w2>"]` | 物理文件须已落盘。 |
| **独立日志追加** | `python .scripts/gatekeeper.py append-log --entry-file ".scratch/log_entry.md"` | 用于流水线 B；条目须以 `## [YYYY-MM-DD]` 开头。 |
| **挂账术语合流** | `python .scripts/gatekeeper.py flush-terms` | 写入 `glossary.md`；提交含词表时即刻执行。 |
| **切片草稿转正** | `python .scripts/gatekeeper.py promote-drafts` | 将 `.scratch/shadow_drafts/` 转正至 `wiki/`。 |
| **物理指标补齐** | `python .scripts/gatekeeper.py backfill-metrics` | 差分提示 `backfill_recommended` 时执行。 |
| **日志周期归档** | `python .scripts/gatekeeper.py archive-log` | 差分提示 `log_archive_recommended` 时执行。 |
| **幽灵雷达巡检** | `python .scripts/scan_ghosts.py [--json]` | 刷新 `.scratch/ghost_radar_cache.json` 驱动 `index.md`。 |

---

## 4. 交付简报模板

```markdown
### 📊 任务执行完成
- **执行工序**: [文献单篇摄取 | 超长文献分治 | 批量主题孵化 | 系统运维 | 合成洞察与问答]
- **涉及卡片**: [[卡片名称列表]]
- **状态同步**: 账本 / 日志 / 雷达确定性落盘，闭环完成。

#### ⏱️ 能效消耗看板
| 认知推演维度 | 消耗 Token 测算 | 备注 |
| :--- | :--- | :--- |
| **原件输入 (Input)** | ~ N | 摄入原件或雷达 JSON 流 |
| **拓扑查词 (Query)** | ~ N | gatekeeper.py query-terms 原子检索与消歧 |
| **存量读取 (Read)** | ~ N | 存量卡片流变与关联核验 |
| **知识写盘 (Write)** | ~ N | 新建/更新卡片与日志条目 |
| **净总能效 (Total)** | ~ N | 处于高效绿区 |
```
