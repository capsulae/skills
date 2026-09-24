# 三态认识论决策模型与主题视口模板

本文件为 `wiki-curator` Skill 的标准参考文档，定义维基主题卡片的三态分类、置顶视口规范与流变表管理。

---

## 1. 三态认识论本质分类

| 认识论维度 | 【模式 A：法定规程标准】 | 【模式 B：实务推荐范式】 | 【模式 C：客观描述机理】 |
| :--- | :--- | :--- | :--- |
| **本体本质** | 具有法定强制力、准入约束力或契约效力的标准 (ISO, RFC, FIGO, 国家标准) | 软件工程范式、管理方法论、工程经验法则 (OKR, DDD, 敏捷, 设计模式) | 自然物理化学规律、试剂原料、生化反应、数学算法推导 (EDTA, PCR, 贝叶斯滤波) |
| **Frontmatter 规则** | `standard_year: 2023`<br>`standard_source: "[[权威组织或规范]]"`<br>`standard_summary: "强制指标/截断值/合格准则"` | `standard_year: 2018`<br>`standard_source: "[[奠基专著或头部机构]]"`<br>`standard_summary: "核心推荐法则/黄金准则"` | `standard_year: null`<br>`standard_source: null`<br>`standard_summary: null`<br>*(模式 C 强制全填 null，严禁虚标！)* |
| **置顶视口类型** | `> [!CURRENT-STANDARD] 法定规程标准` | `> [!CURRENT-GUIDELINE] 推荐范式与实效基准` | `> [!NOTE] 核心机理与主流共识` |

---

## 2. 主题卡片完整合并模板

```markdown
---
type: topic
aliases: [英文全称, 英文缩写, 通俗别名]
tags: [一级领域, 二级分类]
epistemic_status: valid # valid | disputed | superseded
# 模式 A/B 填 4 位年份、规范出处与核心参数；模式 C (客观机理) 强制全部填 null:
standard_year: 2023 # 模式 C 填 null
standard_source: "[[权威组织或奠基专著]]" # 模式 C 填 null
standard_summary: "核心量化参数或黄金法则" # 模式 C 填 null
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
(人类专属领地，Agent 绝对禁读、禁写、禁改、禁删)
```

---

## 3. 认识论流变与收敛三级阀

### (1) 流变决策探针
```python
# 模式 A/B 流变决策（模式 C 统一收敛至下方的优先级收敛三级阀）:
if mode in ["模式A", "模式B"]:
    delta_T = new_doc.year - standard_year
    if abs(delta_T) <= 2:  # 优先捕获同代演化窗口 (<= 2年)
        if contradictory:
            mark("disputed")
        else:
            mark("corroborated")  # 独立同行复现，保持原标准，严禁误标为争议！
    elif delta_T > 2:  # 真正的前向跨代演进
        if new_doc.level >= standard_level:
            mark_old_as("superseded")
            refresh_standard_viewport()
        elif new_doc.level == "L2" and standard_level == "L1" and falsified:
            add_viewport_alert("CRITICAL-DISCREPANCY")  # 实证挑战法定标准
        else:
            add_to_anomaly_buffer()  # 低级证据冲突只入缓冲池
    else:  # delta_T < -2 (历史回溯)
        role = "historical"  # 严禁用早年旧设推翻晚年标准；数学/算法奠基永久保真
```

### (2) 收敛三级阀与折叠协议 (Convergence Valves)
```python
# 1. 权限边界
#    神圣禁区: "## 4. 个人思考与实战手记" 绝对禁读写改删; 模式 C 的 Frontmatter 强制为 null
#    安全演进区: "## 2. 理论流变与共识演进时序表（含反常缓冲池）" 与 "## 3. 关联出处与网络" 为法定综合区

# 2. 优先级与收敛判定
priority: "模式 C (客观机理参数/突破)" > "收敛三级阀"

if is_paradigm_shift:
    tier = "Tier 1"  # 任何模式的范式颠覆必属 Tier 1，刷新置顶视口与核心表
elif mode == "模式C" and (doc.has_quantitative_parameters or doc.has_mechanism_breakthrough):
    tier = "Tier 2"  # 模式 C 重大机理突破与关键量化参数正向入表与入正文
elif is_highest_legal_standard:
    tier = "Tier 1"  # 模式 A/B 最高法定标准刷新 Frontmatter 与置顶视口
elif (doc.year - timeline.latest_year >= 3) or doc.is_large_scale_benchmark:
    tier = "Tier 2"  # 填补 >=3~5 年历史断层或关键实证，强制升序插表
else:
    tier = "Tier 3"
    # 归入 Tier 3 必须在思考链显式断言: assert no_gap_fill and no_mechanism_breakthrough and no_paradigm_shift
    append_link("## 3. 关联出处与网络", doc.wikilink)

# 3. 时序表折叠算法: 严格单调升序，基准行数 <= 8~9
if len(timeline.rows) > 8:
    pinned = [timeline.rows[0], timeline.rows[-1]]  # 锁定奠基 (foundation) 与现行标准 (standard/SOTA)
    folded = fold_adjacent_peers(timeline.rows[1:-1])  # 中间行合并为: | YYYY-YYYY | [[A]] / [[B]] |
    timeline.rows = [pinned[0]] + folded + [pinned[1]]

# 4. 细胞分裂阈值: 单卡 > 180 行时主卡转为 Hub 导航卡，派生子卡进行细胞分裂
if card.lines > 180:
    split_card(master_as_hub=True, spawn_subcards=True)
```
