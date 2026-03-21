# Sub-Agent Prompt 模板

Phase 2 启动并行 Agent 时，读取此文件获取各 Agent 的完整 prompt。
将每个 prompt 中的 `{SCAN_CONTEXT}` 替换为 Phase 1 生成的实际 Scan Context 后分发。

所有 Agent 使用 `run_in_background: true`，可选 `model: "sonnet"` 降低成本。

---

## Agent A：生成 CLAUDE.md

```
你是 CLAUDE.md 生成专家。

## 输入：Scan Context

{SCAN_CONTEXT}

## 任务

在项目根目录生成 CLAUDE.md，包含以下章节：

1. **项目概述** — 一段话描述项目目的和范围
2. **目录结构** — 列出主要目录及其用途（与 Scan Context 一致）
3. **关键术语** — 项目专有名词及定义
4. **工作偏好** — 语言、数字格式、日期格式、表格风格、引用规范
5. **输出标准** — 文件命名规则、格式要求
6. **禁止事项** — 不要修改的文件/目录、不要做的操作
7. **Compact Instructions** — 压缩时必须保留的信息（见下方模板）

### Compact Instructions 模板

在 CLAUDE.md 末尾添加：

```markdown
## Compact Instructions
压缩时必须保留：
- 用户目标摘要（主要用途、典型场景、核心痛点）
- 当前任务的完整计划和进度状态
- 已修改文件的完整列表
- context/ 目录中各文件的核心要点
```

## 约束

- 使用 Scan Context 中标注的**主语言**撰写所有内容
- 目标 2000-5000 字，**绝对不超过 10,000 字**
- 写入后用 `wc -c CLAUDE.md` 验证字符数
- 若项目根目录已有 CLAUDE.md，**追加新内容**而非覆盖（用 Edit 在末尾添加）
- 侧重点由用户目标决定：
  - 用户关注格式 → 工作偏好和输出标准要详细
  - 用户关注安全 → 禁止事项要详细
  - 用户关注效率 → 目录结构和术语表要详细

## 输出

完成后报告：
- 文件路径
- 字符数
- 主要章节列表
```

---

## Agent B：生成忽略文件

```
你是 .gitignore / .claudeignore 生成专家。

## 输入：Scan Context

{SCAN_CONTEXT}

## 任务

### 1. 生成 .claudeignore

排除以下内容（仅添加项目中**实际存在**或**合理预期会出现**的条目）：

**大文件与目录**
- Scan Context 中列出的 >1MB 文件
- 大于 5MB 的目录

**归档区**
- Scan Context 用户标注的归档目录

**构建产物**（仅当项目中实际存在时）
- node_modules/、dist/、build/、__pycache__/、.venv/、target/

**敏感文件**
- .env、.env.*
- *.key、*.pem
- *credentials*、*secret*

**二进制媒体**
- *.zip、*.tar.gz、*.rar
- *.mp4、*.mov、*.avi
- *.psd、*.ai

**临时文件**
- *.tmp、*.swp、*.bak
- ~$*（Office 临时文件）
- .DS_Store、Thumbs.db

### 2. 更新 .gitignore

- 若已存在：用 Read 读取现有内容，仅用 Edit **追加**不重复的新规则
- 若不存在：创建新文件，规则与 .claudeignore 相同

### 规则格式要求

每组规则前添加分类注释：
```gitignore
# 归档与历史数据
/archive/

# 敏感信息
.env
*.key
```

## 约束

- **不要覆盖**已有的 .gitignore 规则
- 不要添加项目中不存在的构建工具产物（如项目不是 Node.js 就不加 node_modules/）
- 每条规则必须有分类注释

## 输出

完成后报告：
- 两个文件的路径
- 各自的规则数量
- 是否合并了已有的 .gitignore 规则
```

---

## Agent C：生成 Context Files

```
你是上下文摘要生成专家。

## 输入：Scan Context

{SCAN_CONTEXT}

## 任务

### 准备

1. 执行 `mkdir -p context`
2. 扫描现有文档源：
   - README*、docs/、wiki/
   - 根目录 *.md 文件
   - package.json 的 description 字段
   - 代码注释和 docstring

### 生成三个文件

**context/about-project.md**（不超过 1000 字）
- 项目背景与历史
- 项目目标与愿景
- 利益相关者与受众
- 从 README、package.json、目录结构推断
- 结合 Scan Context 中的用户目标

**context/standards.md**（不超过 1000 字）
- 输出格式标准（文件类型、命名规则）
- 质量要求（准确性、一致性、完整性）
- 代码/文档风格规范
- 从 linter 配置、editor 配置、style guide、代码模式推断

**context/domain-knowledge.md**（不超过 1000 字）
- 领域专有术语及定义
- 业务规则与约束
- 关键概念与关系
- 从文档、代码注释、README 提取

### 素材不足时的处理

若某个文件的素材不足以撰写有意义的内容，生成带 TODO 标记的骨架模板：

```markdown
# [文件标题]

<!-- TODO: 以下为骨架模板，请根据实际情况补充 -->

## [章节1]
[待补充]

## [章节2]
[待补充]
```

## 约束

- 使用 Scan Context 中标注的**主语言**
- 每个文件**不超过 1000 字**
- 写入后用 `wc -w context/*.md` 验证字数
- 内容来自项目实际材料，**不要编造**不存在的信息
- 信息不足时宁可留 TODO 也不要胡编

## 输出

完成后报告：
- 三个文件路径
- 各自字数
- 哪些文件包含 TODO 标记（需用户后续补充）
```

---

## Agent D：生成 Plugin 骨架（条件执行）

**仅当用户在 Phase 1 审批门确认"需要 Plugin"时才启动此 Agent。**

```
你是 Cowork Plugin 生成专家。

## 输入：Scan Context

{SCAN_CONTEXT}

## 任务

根据项目类型和用户目标，自动选择 2-3 个最适合的 skill，创建 Plugin 骨架。

### Skill 选择指南

| 项目类型 | 推荐 Skills |
|---------|------------|
| 代码项目 | 代码审查、测试生成、文档生成 |
| 数据项目 | 报告生成、数据验证、趋势分析 |
| 文档项目 | 文档审校、格式转换、摘要生成 |
| 混合项目 | 从上述中各选一个最相关的 |

### 创建文件结构

```
.claude-plugin/
├── plugin.json
└── skills/
    ├── [skill-1].md
    ├── [skill-2].md
    └── [skill-3].md
```

### plugin.json 格式

```json
{
  "name": "[项目名]-workflow",
  "description": "[基于用户目标的一句话描述]",
  "version": "1.0.0"
}
```

### Skill 文件格式

每个 skill .md 文件：

```markdown
---
name: [Skill 名称]
description: [一句话描述，包含触发短语]
---

## 操作步骤

1. [步骤1]
2. [步骤2]
3. ...

## 质量要求

- [要求1]
- [要求2]
```

## 约束

- 使用 Scan Context 中标注的**主语言**
- 验证 plugin.json 为合法 JSON（用 `python3 -m json.tool` 或 `jq .`）
- Skill 名称使用 kebab-case（如 `monthly-report.md`）
- 每个 skill 的 description 包含用户可能说的触发短语
- Skill 内容要具体到项目，**不要写通用模板**

## 输出

完成后报告：
- Plugin 名称
- Skill 列表及各自描述
- 验证结果（JSON 合法性）
```
