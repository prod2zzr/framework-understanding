# 用 Claude Code 为 Cowork 构建上下文架构：SOP 指南

---

## 1. 核心理念：用 Code 的"白盒"为 Cowork 消除"黑箱"

### 问题回顾

在[上一篇分析](cowork-controllability-paradox.md)中，我们确认了一个系统性现象：Cowork 的"黑箱感"并非来自其能力不足，而是来自**缺少显式配置的上下文架构**。Code 用户天然需要编写 CLAUDE.md、安装 skills、配置 hooks，这些行为本身就是在与 AI 建立"合作契约"。Cowork 用户可以跳过这一步直接开始工作，结果就是 Claude 按自己的理解行事——有时出色，有时让人困惑。

### 解决思路

一个自然的想法浮现：

> 能否用 Claude Code 的透明交互流程，系统性地为 Cowork 项目生成所有需要的上下文配置文件？

答案是：**完全可行，而且比预想的更好。**

### 关键发现：配置层是共享的

研究揭示了一个重要事实——Code 和 Cowork 的核心配置文件**格式完全一致，可以互相读取**：

| 配置文件 | Code 读取 | Cowork 读取 | 格式 | Code 可生成 |
|----------|:---------:|:-----------:|------|:-----------:|
| `CLAUDE.md` | ✅ | ✅ | Markdown | ✅ |
| `.claudeignore` | ✅ | ⚠️ 部分 | gitignore 语法 | ✅ |
| `.gitignore` | ✅ | ✅ | gitignore 语法 | ✅ |
| `.mcp.json` | ✅ | ✅ | JSON | ✅ |
| `.claude/settings.json` | ✅ | ✅ | JSON | ✅ |
| `plugins/` 目录 | ✅ (skills) | ✅ (plugins) | Markdown + JSON | ✅ |
| 全局指令 | N/A | ✅ (桌面UI) | 纯文本 | ✅ 可生成草稿 |

这意味着：**用 Code 生成的配置文件，Cowork 可以直接读取，不需要任何格式转换。** Code 是 Cowork 的理想配置工具。

---

## 2. SOP 工作流：六阶段交互式配置

以下是用 Claude Code 为任意 Cowork 项目构建完整上下文架构的标准操作流程。每个阶段都利用 Code 的透明性让用户审查和参与。

### Phase 1：项目扫描与诊断

**目标**：理解项目全貌，为后续配置提供数据基础。

在项目根目录启动 Claude Code，让它执行以下操作（每步都可见）：

```
你: "扫描这个项目的结构，告诉我：
     1. 目录树概览
     2. 文件类型分布（多少 .docx, .xlsx, .py, .md 等）
     3. 大文件列表（>1MB）
     4. 潜在敏感文件（.env, credentials, keys）
     5. 已有的配置文件（CLAUDE.md, .gitignore 等）"
```

Code 会使用 Glob、Grep、Bash 工具逐步扫描，你能看到每一步：
```
[Tool: Glob] pattern="**/*" → 列出所有文件
[Tool: Bash] command="du -sh *" → 查看目录大小
[Tool: Grep] pattern="password|secret|key" → 搜索敏感内容
```

**用户参与**：审查扫描结果，标注哪些是核心工作区、哪些是归档区、哪些是敏感区域。

### Phase 2：生成 CLAUDE.md

**目标**：创建项目级的指令文件——Code 和 Cowork 共同的"合作契约"。

```
你: "基于刚才的扫描结果，为这个项目生成一份 CLAUDE.md。
     包含以下部分：
     - 项目概述（一段话）
     - 目录结构说明（哪个文件夹放什么）
     - 关键术语表（项目中的专有名词）
     - 工作偏好（中文输出、表格格式、引用规范等）
     - 输出标准（文件命名规则、格式要求）
     - 禁止事项（不要修改的文件/目录）
     总字数控制在 3000 字以内。"
```

**关键约束**：CLAUDE.md **必须控制在 10K 字以内**。研究表明，过大的系统上下文会消耗 86.5% 的 token 窗口，引发"压缩死亡螺旋"。理想长度是 2000-5000 字。

Code 会生成初稿并显示完整内容。你可以逐段审查、逐行修改——这就是"白盒"的优势。

**CLAUDE.md 模板结构**：

```markdown
# 项目名称

## 项目概述
[一段话描述项目目的和范围]

## 目录结构
- `/reports/` — 月度分析报告（.docx）
- `/data/` — 原始数据文件（.xlsx, .csv）
- `/templates/` — 文档模板
- `/archive/` — 历史存档（请勿修改）

## 关键术语
- [术语1]: [定义]
- [术语2]: [定义]

## 工作偏好
- 语言：中文
- 数字格式：千分位分隔符
- 日期格式：YYYY-MM-DD
- 表格：使用 Markdown 表格
- 引用：标注来源和页码

## 输出标准
- 文件命名：`[日期]-[主题]-[版本].扩展名`
- Word 文档：使用 `/templates/` 中的模板
- Excel 文件：第一行为表头，冻结首行

## 禁止事项
- 不要修改 `/archive/` 中的任何文件
- 不要删除原始数据文件
- 不要在报告中使用未经验证的数据
```

### Phase 3：生成 .claudeignore / .gitignore

**目标**：精确排除不应被 Claude 读取的文件，减少上下文噪音。

```
你: "基于扫描结果，生成 .claudeignore 文件。排除：
     1. 所有 >5MB 的文件
     2. /archive/ 目录
     3. /node_modules/ 和构建产物
     4. .env 和凭证文件
     5. 图片和视频文件（除非特别需要）
     6. 临时文件和缓存"
```

**注意**：由于 Cowork 对 .claudeignore 的支持有限，建议**同时更新 .gitignore**——Cowork 完全尊重 .gitignore 规则。Code 可以一次生成两个文件。

示例输出：

```gitignore
# .claudeignore / .gitignore (Cowork 项目)

# 归档与历史数据（太大，且不需要 Claude 读取）
/archive/
/backup/

# 敏感信息
.env
*.key
*credentials*
*secret*

# 大型二进制文件
*.zip
*.tar.gz
*.mp4
*.mov
*.psd

# 构建产物和缓存
/node_modules/
/__pycache__/
/dist/
/build/
*.pyc

# 临时文件
*.tmp
*.swp
~$*
.DS_Store
```

**用户参与**：逐项确认排除列表，确保没有误排重要文件。

### Phase 4：生成 Context Files

**目标**：不是把原始文档堆进项目目录，而是生成**结构化摘要**作为 Claude 的参考。

核心原则：**摘要优于原文**。把 50 页的产品文档浓缩为 2 页结构化摘要，比把原文扔给 Claude 更有效。

```
你: "阅读以下文件 [列出核心参考文档]，
     为每个生成一份结构化摘要（500字以内），
     放入 /context/ 目录。
     摘要应包含：关键概念、核心数据、决策依据。"
```

**推荐的 Context Files 结构**（社区最佳实践）：

```
/context/
├── about-project.md      ← 项目背景、目标、利益相关者
├── standards.md           ← 输出标准、质量要求、格式规范
└── domain-knowledge.md    ← 领域术语、业务规则、关键数据点
```

每个文件控制在 1000 字以内。总计 3000 字的精练上下文，远好于 30000 字的原始文档堆砌。

### Phase 5：生成 Plugin 骨架（可选）

**目标**：如果项目有重复性任务模式，创建自定义 Plugin 让 Claude 自动遵循。

Plugin 的本质就是 markdown 指令文件 + JSON 清单——Code 完全可以生成。

```
你: "为这个项目创建一个 Cowork Plugin，包含以下 skills：
     1. 月度报告生成（使用指定模板和数据格式）
     2. 数据清洗检查（验证必填字段、格式一致性）
     3. 会议纪要整理（按标准格式提取要点和行动项）"
```

Code 会生成以下结构：

```
.claude-plugin/
├── plugin.json                 ← Plugin 清单
└── skills/
    ├── monthly-report.md       ← Skill: 月度报告生成
    ├── data-validation.md      ← Skill: 数据清洗检查
    └── meeting-notes.md        ← Skill: 会议纪要整理
```

**plugin.json 示例**：
```json
{
  "name": "项目工作流",
  "description": "项目标准操作流程和质量规范",
  "version": "1.0.0"
}
```

**Skill 文件示例**（monthly-report.md）：
```markdown
---
name: 月度报告生成
description: 按照项目模板生成标准月度分析报告
---

## 操作步骤

1. 读取 `/data/` 目录中当月的数据文件
2. 按照 `/templates/monthly-report-template.docx` 的格式生成报告
3. 包含以下部分：
   - 执行摘要（200字以内）
   - 关键指标表格（同比/环比）
   - 趋势分析（配图表描述）
   - 风险与建议

## 质量要求

- 所有数字必须与源数据一致，计算过程可追溯
- 使用千分位分隔符
- 日期格式：YYYY年MM月
- 引用数据时标注来源文件名和工作表名
```

**用户参与**：审查每个 skill 的触发条件和指令内容，确保符合实际工作需求。

### Phase 6：验证与交接

**目标**：确认所有文件格式正确，并生成 Cowork 启动指南。

```
你: "验证刚才生成的所有配置文件：
     1. CLAUDE.md 语法和字数检查
     2. .claudeignore 规则有效性
     3. plugin.json 格式合规性
     4. 所有 skill 文件的 YAML frontmatter 格式
     然后生成一份 Cowork 启动清单。"
```

Code 会执行验证并生成一份清单：

```markdown
## Cowork 启动清单

### 自动生效（打开项目即可）
- [x] CLAUDE.md — 已放置在项目根目录
- [x] .gitignore — 已更新排除规则
- [x] /context/ — 3 个结构化摘要文件
- [x] .claude-plugin/ — Plugin 和 3 个 Skills

### 需手动操作
- [ ] 打开 Claude Desktop → Settings → Cowork → Global Instructions
- [ ] 粘贴以下全局指令：

      [Code 生成的全局指令建议文本]

- [ ] 在 Cowork 中选择此项目文件夹
- [ ] 测试：输入"按模板生成本月报告"验证 skill 是否生效
```

---

## 3. 一个完整的 Cowork 项目目录（经 Code 预处理后）

```
my-project/
│
├── CLAUDE.md                      ← 合作契约（Code 和 Cowork 共读）
├── .gitignore                     ← 排除规则（Cowork 完全尊重）
├── .claudeignore                  ← 额外排除（Code 完全尊重，Cowork 部分）
├── .mcp.json                      ← MCP 服务器配置（共享）
│
├── .claude-plugin/                ← Plugin（Code 生成，Cowork 使用）
│   ├── plugin.json
│   └── skills/
│       ├── monthly-report.md
│       ├── data-validation.md
│       └── meeting-notes.md
│
├── context/                       ← 结构化上下文（替代原始文档堆砌）
│   ├── about-project.md           ← 项目背景摘要
│   ├── standards.md               ← 输出标准和规范
│   └── domain-knowledge.md        ← 领域知识精要
│
├── templates/                     ← 文档模板
│   ├── monthly-report-template.docx
│   └── meeting-notes-template.docx
│
├── data/                          ← 工作数据
│   ├── 2026-01-sales.xlsx
│   └── 2026-02-sales.xlsx
│
├── reports/                       ← 输出目录
│   └── (Cowork 生成的报告放这里)
│
└── archive/                       ← 归档（已被 .gitignore 排除）
    └── (历史数据，Claude 看不到)
```

---

## 4. 局限与注意事项

### 无法通过 Code 自动化的部分

| 限制 | 原因 | 绕过方式 |
|------|------|----------|
| **全局指令** | 只能通过 Cowork 桌面 UI 设置 | Code 生成建议文本，用户手动粘贴 |
| **Cowork 不支持 Hooks** | 架构差异——Cowork 的 VM 环境不暴露 hook 接口 | 将 hook 逻辑转化为 skill 中的"检查步骤" |
| **会话间无记忆** | Cowork 每次对话从零开始 | 在 CLAUDE.md 和 context files 中包含所有关键信息 |

### 上下文预算管理

基于实测数据的建议：

```
上下文预算分配（200K token 窗口）：

理想状态：
  CLAUDE.md:        ~5K tokens   (2.5%)
  Context Files:    ~10K tokens  (5%)
  MCP 工具定义:      ~15K tokens  (7.5%)
  系统提示:          ~20K tokens  (10%)
  ─────────────────────────────────────
  系统占用合计:      ~50K tokens  (25%)
  可用于实际工作:    ~150K tokens (75%)  ← 健康

危险状态（要避免）：
  过大的 CLAUDE.md:  ~40K tokens  (20%)
  过多的 Context:    ~50K tokens  (25%)
  MCP 工具定义:      ~30K tokens  (15%)
  系统提示:          ~53K tokens  (26.5%)
  ─────────────────────────────────────
  系统占用合计:      ~173K tokens (86.5%)
  可用于实际工作:    ~27K tokens  (13.5%) ← 压缩死亡螺旋
```

### .claudeignore 的 Cowork 兼容性

- Cowork 对 .claudeignore 的支持**不完整**——某些情况下 Claude 仍可能读取被排除的文件
- **更可靠的替代**：使用 .gitignore，Cowork 完全尊重 .gitignore 规则
- **最安全的做法**：不要把敏感文件放在挂载给 Cowork 的目录中。VM 的安全边界是目录级的——未挂载的路径在 VM 中根本不存在

---

## 5. 更大的图景：Code + Cowork 协作模式

用 Code 为 Cowork 做配置不是一次性操作，而是一种持续的协作模式：

```
┌─────────────────────────────────────────────────────────┐
│                   项目生命周期                            │
│                                                         │
│   ┌──────────┐    共享配置层     ┌──────────┐           │
│   │          │  ← CLAUDE.md →   │          │           │
│   │  Claude  │  ← .mcp.json →  │  Claude  │           │
│   │  Code    │  ← plugins/  →  │  Cowork  │           │
│   │          │  ← context/  →  │          │           │
│   └────┬─────┘                  └─────┬────┘           │
│        │                              │                 │
│   负责：                          负责：                │
│   · 配置生成与维护               · 文档生成（Word/PPT）  │
│   · 技术任务（代码/脚本）         · 数据分析（Excel）     │
│   · Skills 编写与调试            · 研究与整理            │
│   · 精确控制的操作               · 委托型知识工作         │
│   · 定期更新 context files       · 日常重复性任务         │
│                                                         │
│   工作流示例：                                           │
│   1. Code 扫描新数据 → 更新 context/domain-knowledge.md │
│   2. Cowork 读取更新后的上下文 → 生成本月分析报告        │
│   3. Code 审查报告中的数据引用 → 验证准确性              │
│   4. Cowork 根据反馈修订 → 输出最终版本                  │
└─────────────────────────────────────────────────────────┘
```

这种模式的本质是：**Code 是架构师和质检员，Cowork 是执行者。** 两者通过共享配置层保持对项目的一致理解，各自发挥架构优势。

---

## 参考资料

- [Claude Cowork 设置指南：Context Files、Instructions、Plugins（2026）](https://www.the-ai-corner.com/p/claude-cowork-setup-guide)
- [使用 CLAUDE.md 文件：为你的代码库定制 Claude](https://claude.com/blog/using-claude-md-files)
- [创建 Plugins——Claude Code 文档](https://code.claude.com/docs/en/plugins)
- [在 Cowork 中使用 Plugins——Claude 帮助中心](https://support.claude.com/en/articles/13837440-use-plugins-in-cowork)
- [Cowork 入门指南——Claude 帮助中心](https://support.claude.com/en/articles/13345190-get-started-with-cowork)
- [Anthropic 官方知识工作 Plugins 仓库](https://github.com/anthropics/knowledge-work-plugins)
- [Claude Cowork 架构深度解析——claudecn.com](https://claudecn.com/en/blog/claude-cowork-architecture/)
- [扩展 Claude 能力：Skills 与 MCP 服务器](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)
- [Claude Skills vs MCP 技术对比——Intuition Labs](https://intuitionlabs.ai/articles/claude-skills-vs-mcp)
- [上下文过载导致压缩死亡螺旋——GitHub Issue #24677](https://github.com/anthropics/claude-code/issues/24677)
- [Cowork 上下文管理策略——DataLakehouse Hub](https://datalakehousehub.com/blog/2026-03-context-management-claude-cowork/)
- [Claude Code 设置指南：MCP、Hooks、Skills（2026）](https://okhlopkov.com/claude-code-setup-mcp-hooks-skills-2026/)
- [用 Code 和 Cowork 协作——Ryan McDonald](https://ryancmcdonald.com/blog/claude-cowork-and-claude-code-together/)
- [Claude Code 的秘密武器：CLAUDE.md、SKILL.md 完全指南](https://sidsaladi.substack.com/p/claude-codes-secret-weapon-the-complete)
- [为 Claude Cowork 构建自定义 Connector——Rebecca De Prey](https://rebeccamdeprey.com/blog/build-custom-connector-claude-cowork)
- [Claude Cowork Plugins 构建指南——aiblewmymind](https://aiblewmymind.substack.com/p/claude-cowork-plugins-guide)
- [Cowork 安全使用指南——Claude 帮助中心](https://support.claude.com/en/articles/13364135-use-cowork-safely)
