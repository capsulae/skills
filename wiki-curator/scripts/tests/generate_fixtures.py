#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.scripts/tests/generate_fixtures.py - 黄金测试样本库自动化生成器
生成 L1~L6 六级代表性微型标准测试资料于 raw/fixtures/
"""

import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def find_workspace_root() -> Path:
    """智能嗅探工作区根目录（优先检测 cwd，再从当前文件向上回溯寻找 raw/ 与 wiki/）"""
    try:
        cwd = Path.cwd().resolve()
        if (cwd / "raw").is_dir() and (cwd / "wiki").is_dir():
            return cwd
    except Exception:
        pass

    cur = Path(__file__).resolve().parent
    for p in [cur, *cur.parents]:
        if (p / "raw").is_dir() and (p / "wiki").is_dir():
            return p

    if cur.name == "scripts":
        if len(cur.parents) >= 3 and cur.parent.parent.name == "skills":
            return cur.parent.parent.parent.parent
        return cur.parent

    return Path.cwd().resolve()


ROOT_DIR = find_workspace_root()
FIXTURES_DIR = ROOT_DIR / "raw" / "fixtures"

FIXTURES_DATA = {
    "L1_fixture_standard.md": """---
title: "医疗器械质量管理体系与设计控制规程标准"
type: standard
pages: 18
evidence_level: L1_standard
epistemic_status: valid
source_file: "raw/fixtures/L1_fixture_standard.md"
date: "2026-09-17"
year: 2023
standard_year: 2023
standard_source: "[[ISO 13485:2016]]"
standard_summary: "设计转换关键工序过程能力指数 C_pk >= 1.33；无菌屏障完整性泄漏率 < 1e-6 mbar*L/s"
tags: [监管科学, 质量体系]
---

# 医疗器械质量管理体系与设计控制规程标准

> [!CURRENT-STANDARD] 法定规程标准
> - **权威出处/理论基石**：[[ISO 13485:2016]] 与 [[21 CFR Part 820]]
> - **核心强制参数/截断值**：设计转换关键工序过程能力指数 C_pk >= 1.33；无菌屏障完整性泄漏率 < 1e-6 mbar*L/s。
> - **适用边界与强制范畴**：全生命周期医疗器械研发与生产，严禁跳过验证阶段直接量产。

## 1. 核心法定条款与架构
依据 Clause 7.3.7 与 Clause 7.3.8：
- [[设计转换 (Design Transfer)]]：确保研发输入正确转化为量产技术规范，建立 DMR 档案。
- [[无菌屏障系统 (Sterile Barrier System)]]：满足 ISO 11607-1 强制包装密封性测试。

## 2. 演进与流变
| 年份 | 代表出处 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2016** | [[ISO 13485:2016]] | L1_standard | valid | standard | 确立基于风险的全生命周期质量体系 |
| **2023** | [[FDA QMSR Final Rule]] | L1_standard | valid | standard | 全面与 ISO 13485 标准对齐融合 |
""",

    "L2_fixture_causal_synthesis.md": """---
title: "基于前瞻性多中心双盲RCT的抗疟靶向抑制剂临床疗效Meta分析"
type: paper
pages: 24
evidence_level: L2_causal_synthesis
epistemic_status: valid
source_file: "raw/fixtures/L2_fixture_causal_synthesis.md"
date: "2026-09-17"
year: 2024
standard_year: null
standard_source: null
standard_summary: null
tags: [热带医学, 药理学]
---

# 基于前瞻性多中心双盲RCT的抗疟靶向抑制剂临床疗效Meta分析

> [!NOTE] 核心机理与主流共识
> - **理论基石**：[[抗疟疗效Meta综合]] (2024, Cochrane Review)
> - **反应机理与量化指标**：靶向抑制 PfATP6 钙离子泵；相对危险度 RR = 0.42 (95% CI: 0.35-0.51), p < 0.0001。
> - **适用边界与禁忌**：仅限恶性疟原虫感染；对三日疟原虫突变体效果受限。

## 1. 核心生物物理机理
通过结合疟原虫跨膜通道阻断离子转运。核心机制涵盖 [[疟疾]] 感染期裂殖子释放抑制。

## 2. 演进与流变
| 年份 | 代表出处 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2015** | [[RCT试验早期报告]] | L3_empirical_peer_reviewed | valid | foundation | 单中心双盲初探证实生化有效性 |
| **2024** | [[抗疟疗效Meta综合]] | L2_causal_synthesis | valid | synthesis | 多中心 RCT 严格合成，确立最高实证 |
""",

    "L3_fixture_empirical_paper.md": """---
title: "低共熔溶剂用于木质素催化解聚的反应动力学校准与原位表征"
type: paper
pages: 14
evidence_level: L3_empirical_peer_reviewed
epistemic_status: valid
source_file: "raw/fixtures/L3_fixture_empirical_paper.md"
date: "2026-09-17"
year: 2023
standard_year: null
standard_source: null
standard_summary: null
tags: [绿色化学, 生物质催化]
---

# 低共熔溶剂用于木质素催化解聚的反应动力学校准与原位表征

> [!NOTE] 核心机理与主流共识
> - **理论基石**：[[木质素催化解聚]] (2023, JACS)
> - **反应机理与量化参数**：活化能 Ea = 58.4 kJ/mol；在 120 摄氏度下反应速率常数 k = 0.042 min^-1。
> - **工程局限性**：高粘度限制传质效率；水含量超过 5% 时体系相分离。

## 1. 核心化学机理
氢键供体与受体形成稳定网络结构。引入 [[低共熔溶剂 (DES)]] 作为反应介质促进醚键断裂。

## 2. 演进与流变
| 年份 | 代表出处 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2019** | [[DES基础表征]] | L3_empirical_peer_reviewed | valid | foundation | 首次测定热力学共晶点 |
| **2023** | [[木质素催化解聚]] | L3_empirical_peer_reviewed | valid | corroboration | 原位红外验证氢键断键路径 |
""",

    "L4_fixture_industry_framework.md": """---
title: "分布式高并发微服务架构设计准则与领域驱动设计范式"
type: book
pages: 32
evidence_level: L4_industry_framework
epistemic_status: valid
source_file: "raw/fixtures/L4_fixture_industry_framework.md"
date: "2026-09-17"
year: 2020
standard_year: 2020
standard_source: "[[Building Microservices 2nd Ed]]"
standard_summary: "服务间异步事件解耦，跨服务链路跳数 <= 3，P99 延迟 <= 150ms"
tags: [软件工程, 分布式系统]
---

# 分布式高并发微服务架构设计准则与领域驱动设计范式

> [!CURRENT-GUIDELINE] 推荐范式与实效基准
> - **权威出处/奠基专著**：[[Building Microservices 2nd Ed]] (2020, Newman)
> - **黄金法则与量化阈值**：服务间通过异步事件驱动解耦；单次请求链路跨服务跳数 <= 3；P99 延迟 <= 150ms。
> - **适用边界与禁忌**：单体阶段严禁盲目拆分；必须具备分布式调用链追踪与监控基础设施。

## 1. 架构本质与领域建模
基于 [[领域驱动设计 (DDD)]] 划分限界上下文。

## 2. 演进与流变
| 年份 | 代表出处 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2003** | [[Domain-Driven Design]] | L4_industry_framework | valid | foundation | Eric Evans 确立限界上下文与聚合根范式 |
| **2020** | [[Building Microservices 2nd Ed]] | L4_industry_framework | valid | standard | 工业界确立微服务网状拓扑治理准则 |
""",

    "L5_fixture_exploratory_preprint.md": """---
title: "基于量子退火算法的染色体空间三维构象拓扑重构初探"
type: paper
pages: 12
evidence_level: L5_exploratory
epistemic_status: valid
source_file: "raw/fixtures/L5_fixture_exploratory_preprint.md"
date: "2026-09-17"
year: 2025
standard_year: null
standard_source: null
standard_summary: null
tags: [计算生物学, 量子计算]
---

# 基于量子退火算法的染色体空间三维构象拓扑重构初探

> [!INFO] 现行工程经验与探索假说
> - **出处**：arXiv 预印本 (2025)
> - **探索机理与参数**：利用 D-Wave 拓扑拟合 Hi-C 接触矩阵；样本量 N=8。
> - **适用边界与局限**：硬件量子比特噪声显著，仅验证小规模玩具拓扑，未经验证临床样本。

## 1. 探索假说与模型推导
量子退火映射伊辛自旋玻璃模型。

## 2. 演进与流变
| 年份 | 代表出处 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2025** | [[量子退火重构初探]] | L5_exploratory | valid | exploratory | 预印本初探，提出构象拓扑映射假说 |

### ⚠️ 前沿反常与争议缓冲池
- 在高分辨率局域 TAD 边界预测上，与经典 Hi-C 算法预测结果偏差 23%，机理尚待实验复现。
""",

    "L6_fixture_informal_blog.md": """---
title: "深度拆解：2026年AI制药十大前沿趋势与商业化展望"
type: general
pages: null
evidence_level: L6_informal
epistemic_status: valid
source_file: "raw/fixtures/L6_fixture_informal_blog.md"
date: "2026-09-17"
year: 2026
standard_year: null
standard_source: null
standard_summary: null
tags: [行业分析, AI制药]
---

# 深度拆解：2026年AI制药十大前沿趋势与商业化展望

> [!INFO] 现行工程经验与探索假说
> - **出处**：行业微信公众号综述 (2026)
> - **核心观点**：生成式扩散模型正在加速苗头化合物筛选周期。
> - **局限性**：非同行评议实证，缺乏湿法实验量化数据支撑。

## 1. 核心观点综述
梳理 2026 年行业投资热点与初创管线进展。

## 2. 演进与流变
| 年份 | 代表出处 / 提案 | 证据等级 | 科学自洽度 | 认识论角色 | 演进关系与证据边界 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2026** | [[2026年AI制药前沿展望]] | L6_informal | valid | informal | 行业媒体快讯与宏观趋势综述 |
"""
}


def generate_all_fixtures() -> list[Path]:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    created = []
    for filename, text in FIXTURES_DATA.items():
        fp = FIXTURES_DIR / filename
        fp.write_text(text.strip() + "\n", encoding="utf-8")
        created.append(fp)
    return created


if __name__ == "__main__":
    files = generate_all_fixtures()
    print(f"SUCCESS: 生成 {len(files)} 篇黄金样本于 {FIXTURES_DIR}")

