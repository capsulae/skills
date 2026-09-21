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
if mode == "模式C":
    insert_timeline_asc(new_doc.year)  # 客观机理豁免 ΔT，直接按公开发表年份升序插桩
else:  # 模式 A/B
    delta_T = new_doc.year - standard_year
    if delta_T > 0:  # 前向演进
        if new_doc.level >= standard_level:
            mark_old_as("superseded")
            refresh_standard_viewport()
        elif new_doc.level == "L2" and standard_level == "L1" and falsified:
            add_viewport_alert("CRITICAL-DISCREPANCY")  # 实证挑战法定标准
        else:
            add_to_anomaly_buffer()  # 低级证据冲突只入缓冲池
    elif delta_T < 0:  # 逆向历史回溯
        role = "historical"  # 严禁用早年旧设推翻晚年标准；数学/算法奠基永久保真
    elif delta_T == 0:  # 同代演化 (<= 2年)
        if contradictory:
            mark("disputed")
        else:
            mark("corroborated")  # 独立复现，严禁误标为争议
```

### (2) 认识论优先级与防膨胀收敛三级阀 (Convergence Valves)
- **认识论优先级公理**：**认识论模式优先级高于通用收敛阀**。若属于【模式 C：客观机理】，文献中确证的核心量化动力学指标、反应条件与边界常数，直接享有更新参数表格与插入流变时序表的正向特权。
- **正向安全演进区划分**：
  - **神圣禁区**：`## 4. 个人思考与实战手记` 属于人类领地，Agent **绝对禁读、禁写、禁改、禁删**；模式 C 的 Frontmatter 标准字段强制全为 `null`。
  - **安全演进区**：`## 2. 理论流变与共识演进时序表` 与 `## 5. 衍生研讨与前沿反常` 属于合法知识演进区，Agent 必须在符合认识论时序时执行综合。
- **Tier 1 (范式迭代 / 跨代突破)**：刷新 Frontmatter + 刷新置顶视口 + 插入流变表对应年份槽位。
- **Tier 2 (重磅突破 / 关键实证 / 填补断层)**：
  - 填补了该主题流变时序表中的重大年代空白（历史跨度 $\ge 3\sim 5$ 年）；
  - 或系行业/跨国级大规模权威实证调研（大样本队列、关键工具断层、重要实务反常）；
  - **必须作为 Tier 2 插入流变时序表对应年份槽位**，严禁以 Tier 3 忽略！
- **Tier 3 (常规同行实证 / 局部微小验证)**：
  - 仅当文献确属常规微小验证且无时序填补价值时方可归入。
  - **举证责任倒置反思链**：主张归入 Tier 3 前，Agent 必须在推理链中证明：“本文献既无重大年代断层填补，亦无量化机制突破，亦无前沿反常争议，故安全归入 Tier 3”。
  - 仅在 `## 3. 关联出处与网络` 末尾追加 `[[文献名]]`。
- **时序表 8 行溢出折叠算法 (Timeline Compaction Protocol)**：
  - 时序表按年份严格单调升序，基准上限为 $8\sim 9$ 行。
  - 当插入新文献导致时序表超过 8 行时，**严禁放弃记录新文献，亦严禁删除首行奠基 (`foundation`) 与末行现行标准 (`standard`)**。
  - **执行折叠合并**：找到中间年代相邻、结论相似的 2~3 个同行微小实证行，合并为单一行：
    `| YYYY-YYYY | [[文献A]] / [[文献B]] | L3_empirical_peer_reviewed | valid | validation | 多中心队列/同行复现验证与参数标定 |`
- **单卡行数限制**：单张卡片正文超过 180 行时，触发细胞分裂，主卡退化为 Hub 导航卡，关键子领域派生独立子卡。
