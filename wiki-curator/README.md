# Wiki Curator (利刃的第二大脑 · 认知策展引擎)

`wiki-curator` 是专为 Obsidian 与大语言模型（LLM）双链知识库量身定制的**自动化认知策展与文献摄取 Skill**。

它将文献摄入、双时钟权威定级、中英双链铸模、三态认识论流变追踪（法定标准 / 实务范式 / 客观机理）以及原子账本闭环，完整封装为确定性可执行工序。

---

## 🌟 核心特性

- **存算解耦架构**：将“执行引擎”（Skill 与脚本）与“个人笔记资产”（`wiki/`、`raw/`、`log.md`）彻底分离。笔记神圣不动，引擎随时平滑升级。
- **智能根目录嗅探 (Smart Root Discovery)**：脚本自动向上探测工作区根目录，无论安装在何种深层路径均能开箱即用。
- **三道防线质量护城河**：内嵌宿主工具链探针、无头管家状态机与 Agent 仿真审计 12 项断言测试，保证执行可靠度。
- **双时钟与三态认识论**：严格区分业务摄取时钟与文献发表时钟，自动对齐国际规程、行业范式与物理机理。

---

## 🚀 快速安装与配置

### 1. 克隆到知识库

在你的 Obsidian 第二大脑根目录下打开终端，执行以下命令：

```bash
# 将本仓库作为 Skill 安装到 .agents 目录中
git clone https://github.com/<你的用户名>/wiki-curator.git .agents/skills/wiki-curator
```

### 2. 安装 Python 运行时依赖

确保本机已安装 Python 3.10+，然后安装依赖库（主要是 PDF 拓扑解析引擎）：

```bash
pip install -r .agents/skills/wiki-curator/requirements.txt
```

### 3. 配置知识库全局守则 (`AGENTS.md`)

在你的知识库根目录下的 `AGENTS.md` 中，配置极简宪法级安全守则，并引入本 Skill：

```markdown
# 知识库核心机器守则
1. 四元立柱禁令：严禁直接读写 index.md；log.md 与 raw_manifest.json 必须且仅由脚本代理；glossary.md 仅限靶向正则检索。
2. 禁令与格式：严格无 BOM UTF-8；绝对禁止运行任何 --help 探测命令；人类专属手记绝对禁碰。
3. 摄取工序调用：所有文献摄取、维基卡片构建与主题对齐演进，必须严格遵循并执行 `wiki-curator` skill。
```

---

## 🛠️ 日常使用指南

当你（或通过 AI Agent）想要处理知识库时，直接输入自然语言即可触发：

- *“帮我把 raw/ 目录里的新论文摄取一下。”*
- *“检查一下当前账本状态，看看有没有未处理的新资料。”*
- *“将新摄取的文献与已有的主题卡片进行三态对齐。”*

Agent 将自动加载本 Skill，依照标准化步骤执行门禁差分、自适应提取、查词双链铸模、主题流变更新与原子提交。

---

## 🔄 如何获取最新升级？

当作者在 GitHub 上更新了提示词工序或优化了底层脚本时，你只需进入 Skill 目录拉取更新：

```bash
cd .agents/skills/wiki-curator
git pull
```

**0 秒平滑升级！** 你的笔记与历史数据 100% 不受影响。

---

## 🧪 自动化测试验证

在修改脚本或配置后，可运行三道防线回归测试流水线进行自测：

```bash
python .agents/skills/wiki-curator/scripts/tests/run_tests.py
```
全部 12 项断言应在 ~300ms 内全绿通过。
