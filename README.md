# Antigravity & Agent Skills 集合库

本仓库为维护的 AI Agent 技能集合库（Skills Repository），适配 Google Antigravity、Claude Code 及遵循 Agent Skill 标准规范的知识库与开发环境。

---

## 📦 包含的技能清单 (Available Skills)

| 技能名称 | 目录路径 | 核心功能简介 |
| :--- | :--- | :--- |
| **wiki-curator** | [wiki-curator/](./wiki-curator) | **第二大脑认知策展与文献摄取引擎**：全自动文献摄取、双时钟权威定级、中英双链铸模、三态认识论对齐与原子账本锁守。 |

---

## 🚀 快速安装指引 (Quickstart)

### 方式一：整库克隆（最推荐）
如果你的知识库根目录下尚未创建 .agents/skills 目录，可直接执行：
`ash
git clone https://github.com/capsulae/skills.git .agents/skills
`
安装后，.agents/skills/wiki-curator/ 自动就绪，Agent 开箱即用。

### 方式二：单技能手动引入
如果你已有现存的 .agents/skills 目录，可将本仓库克隆至临时目录后，将 wiki-curator 文件夹拷贝至你的 .agents/skills/ 中。

---

## 🔄 升级与同步 (Update)
当本仓库发布更新时，直接进入目录执行：
`ash
cd .agents/skills
git pull
`
