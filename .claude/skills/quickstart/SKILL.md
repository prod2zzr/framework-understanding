---
name: quickstart
description: >
  一键启动新项目——选模板、收集资料、建目录、整理上下文，消除启动摩擦。
  当用户说"开个新项目"、"quickstart"、"新建项目"、"我要开始一个新项目"、
  "帮我启动项目"、"start new project"时触发。
argument-hint: "[描述你要做什么，可附 URL]"
allowed-tools: Bash(mkdir *), Bash(tree *), Bash(git init), Bash(wc *), Read, Write, WebFetch, WebSearch, Glob
effort: high
---

# Quickstart — 项目快速启动器

把 6 步 30 分钟的手动启动流程压缩为一次对话。

## 当前环境

- 工作目录：!`pwd`
- 目录内容：!`ls -la 2>/dev/null || echo "(空目录)"`

---

## Phase 1/4：项目定义

### 解析 `$ARGUMENTS`

用户输入的参数：`$ARGUMENTS`

**解析规则**（按优先级）：

1. `--research` / `--code` / `--document` → 明确指定模板（兼容桌面端习惯）
2. 自然语言关键词自动推断模板：
   - 含"研究/调研/分析/对比/论文/survey/compare" → 研究型
   - 含"代码/app/应用/工具/api/web/开发/build/dev" → 代码型
   - 含"报告/文档/方案/提案/手册/写作/write/report" → 文档型
3. 以 `http://` 或 `https://` 开头的词 → URL 资料（自动抓取）
4. 以 `/` 或 `~/` 开头的词 → 本地文件路径
5. 其余文本 → 项目名称和描述（取前 3 个非关键词作项目名，用连字符连接）

**示例**：
- `/quickstart 调研 AI Agent 框架` → 项目名=ai-agent-frameworks, 模板=研究型, 零交互
- `/quickstart myapp --code https://docs.example.com` → 项目名=myapp, 模板=代码型, 附带 URL
- `/quickstart 写一份技术方案` → 项目名=tech-proposal, 模板=文档型, 零交互
- `/quickstart` → 无参数，进入交互模式（最多 1 轮）

### 快速模式（$ARGUMENTS 已含项目名 + 可推断模板时）

**跳过所有交互**，直接进入 Phase 2。

### 交互模式（$ARGUMENTS 为空或无法推断模板时）

用 AskUserQuestion 问**一个**问题：

**问题**：选择项目模板

| 选项 | 适用场景 |
|------|---------|
| 研究型 | 调研、分析、对比、读论文 |
| 代码型 | 写代码、建应用、做工具 |
| 文档型 | 写报告、方案、提案、手册 |
| 自定义 | 以上都不合适，自己指定 |

若项目名也缺失，从用户的回复中提取关键词作为项目名。

**等待用户回复后继续。**

---

## Phase 2/4：资料收集与整理

### Step 1：创建项目目录

项目路径默认为 `../[项目名称]/`（当前目录的同级）。若用户指定了路径，用指定路径。

```bash
mkdir -p [项目路径]
cd [项目路径]
git init
```

根据模板类型，读取对应模板文件获取目录结构：
- 研究型 → 用 Read 读取 `${CLAUDE_SKILL_DIR}/templates/research.md`
- 代码型 → 用 Read 读取 `${CLAUDE_SKILL_DIR}/templates/code.md`
- 文档型 → 用 Read 读取 `${CLAUDE_SKILL_DIR}/templates/document.md`
- 自定义 → 按用户指定的结构创建

按模板创建子目录。

### Step 2：处理网页链接

若用户提供了 URL，对每个 URL：

1. 用 WebFetch 抓取（多个 URL **并行**抓取，不要串行等待）
2. 提取核心信息（去掉导航栏、广告等噪音）
3. 保存为 `references/[简短描述].md`

文件格式：
```markdown
---
source: [原始 URL]
fetched: [日期]
type: [article|repo|docs|other]
---

# [标题]

[提取的核心内容]
```

若 URL 指向 GitHub 仓库，额外提取：README 全文、目录结构、关键配置。

### Step 3：处理本地文件

若用户提供了本地文件路径：

1. 用 Read 读取（支持 PDF、文本、Markdown）
2. Word/PPT 若 Read 失败，提示用户导出为 PDF
3. 整理为 markdown 保存到 `references/`

### Step 4：处理关键词搜索

若用户提供了关键词/主题：

1. 用 WebSearch 搜索，取 3-5 个最相关结果
2. 对每个结果用 WebFetch 抓取
3. 保存为 `references/search-[关键词].md`

### Step 5：生成资料索引

在 `references/_index.md` 中创建索引表：

```markdown
# 资料索引

| 文件 | 来源 | 类型 | 摘要 |
|------|------|------|------|
| [文件名] | [URL/路径] | [类型] | [一句话摘要] |
```

完成后**自动继续** Phase 3（不等待确认，减少交互轮次）。

---

## Phase 3/4：项目配置

### 生成 CLAUDE.md

用 Read 读取 `${CLAUDE_SKILL_DIR}/references/claude-md-template.md` 获取模板。

基于以下信息填充模板：
- 项目名称和描述（Phase 1）
- 目录结构（来自模板文件）
- 关键术语（从 references/ 中的资料提取 5-10 个）
- 资料列表（Phase 2 的索引）

**约束**：500-1500 字，硬上限 3000 字。写入后用 `wc -c CLAUDE.md` 验证。

### 生成 .claudeignore 和 .gitignore

从模板文件（templates/*.md）中提取对应的忽略规则，用 Write 生成。

### 初始化 Git

若尚未 git init，执行：
```bash
git init
git add -A
git commit -m "Initial project setup via /quickstart (session: ${CLAUDE_SESSION_ID})"
```

---

## Phase 4/4：启动确认

输出紧凑摘要（手机一屏可读）：

```markdown
## [项目名] 已就绪

[模板类型] | [N] 份资料 | `[项目路径]`

目录：references/ analysis/ notes/ （根据实际模板列出）
配置：CLAUDE.md .claudeignore .gitignore

下一步：打开此文件夹开始工作，或 `/framework-understanding` 深度配置
```

**不要**执行 `tree` 命令输出完整目录树——用一行列出主要子目录名即可。

---

## 错误处理

- **WebFetch 失败**：跳过，在索引中标注"抓取失败"，最后统一告知
- **本地文件不存在**：提示检查路径，不阻塞流程
- **目录已存在**：问用户是追加资料还是新建目录
- **无任何资料**：正常创建目录和配置，`references/` 下放 `_placeholder.md`
- **若项目较复杂**（已有大量代码），建议改用 `/framework-understanding`
