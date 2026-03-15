---
name: setup-cowork-teams
description: 用 Agent Teams 并行生成完整的 Cowork 上下文架构（CLAUDE.md、忽略文件、上下文文件、Plugin 骨架）
---

# Cowork Setup Architect — Agent Teams 并行版

你是一个 Cowork 项目配置编排者。此 skill 将当前项目的配置生成任务拆分为并行子任务，通过多个 Sub-Agent 同时执行，大幅缩短配置时间。

**架构**：哪吒模式三段式
- **千里眼**（Phase 1）：扫描项目，生成共享上下文
- **三头六臂**（Phase 2）：4 个 Sub-Agent 并行生成配置文件
- **收敛**（Phase 3）：验证所有输出，生成交接清单

---

## Phase 1/3：千里眼 — 项目扫描与共享上下文生成

这是唯一的串行阶段。扫描结果将作为所有并行 Agent 的共享输入。

### 执行步骤

1. 用 Bash 并行执行以下扫描（在**同一轮**工具调用中发起所有命令）：

```
[Bash] find . -type d -not -path './.git/*' | head -50
[Bash] find . -type f -not -path './.git/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
[Bash] find . -type f -size +1M -not -path './.git/*' -exec ls -lh {} \; | head -20
[Grep] pattern="password|secret|key|credential|token" （排除 .git）
[Glob] 检查已有配置：CLAUDE.md, .gitignore, .claudeignore, .mcp.json, .claude/, .claude-plugin/
```

2. 检测项目主语言（从文件内容和 README 判断是中文还是英文项目）

3. 将扫描结果整合为**结构化上下文摘要**（scan context），格式如下：

```markdown
## Scan Context（共享给所有 Sub-Agent）

### 项目类型
[代码项目 / 数据项目 / 文档项目 / 混合项目]

### 主语言
[中文 / 英文]

### 目录结构
[目录树，标注用途]

### 文件类型分布
[扩展名: 数量]

### 大文件（>1MB）
[列表]

### 敏感文件
[列表]

### 已有配置
[列表]

### 用户标注
- 核心工作区：[用户指定]
- 归档区：[用户指定]
- 敏感区：[用户指定]
```

4. **审批门**：展示 Scan Context，请用户确认并标注核心区/归档区/敏感区。

> "以上是项目扫描结果。请确认：
> 1. 哪些是核心工作区？
> 2. 哪些是归档区？
> 3. 有没有敏感区域？
> 4. 是否需要生成 Plugin 骨架？（Phase 2 会并行处理）
> 确认后我将同时启动 4 个 Agent 并行生成配置。"

**等待用户回复。** 将用户标注合并到 Scan Context 中。

---

## Phase 2/3：三头六臂 — 4 个 Sub-Agent 并行

用户确认后，在**同一轮响应**中同时启动以下 4 个 Agent（使用 `run_in_background: true`）：

### Agent A：生成 CLAUDE.md

```
Agent(
  description="Generate CLAUDE.md",
  run_in_background=true,
  prompt="""
  你是 CLAUDE.md 生成专家。

  ## 输入：Scan Context
  {粘贴完整的 Scan Context}

  ## 任务
  在项目根目录生成 CLAUDE.md，包含：
  - 项目概述（一段话）
  - 目录结构说明
  - 关键术语表
  - 工作偏好（语言、格式、引用规范）
  - 输出标准（命名规则、格式要求）
  - 禁止事项

  ## 约束
  - 使用 Scan Context 中标注的主语言
  - 目标 2000-5000 字，绝对不超过 10,000 字
  - 写入后用 wc -c CLAUDE.md 验证
  - 若已有 CLAUDE.md，追加而非覆盖（在末尾添加新内容）

  ## 输出
  完成后报告：文件路径、字符数、主要章节列表。
  """
)
```

### Agent B：生成忽略文件

```
Agent(
  description="Generate ignore files",
  run_in_background=true,
  prompt="""
  你是 .gitignore / .claudeignore 生成专家。

  ## 输入：Scan Context
  {粘贴完整的 Scan Context}

  ## 任务
  1. 生成 .claudeignore，排除：
     - 大于 5MB 的文件/目录
     - Scan Context 中标注的归档区
     - 构建产物（仅添加项目中实际存在的）
     - 敏感文件（.env, *.key, *credentials*, *secret*）
     - 二进制媒体（*.zip, *.tar.gz, *.mp4, *.mov, *.psd）
     - 临时文件（*.tmp, *.swp, ~$*, .DS_Store）

  2. 更新 .gitignore：
     - 若已存在，Read 现有内容，仅追加不重复的新规则
     - 若不存在，创建新文件（与 .claudeignore 相同规则）

  ## 约束
  - 不要覆盖已有的 .gitignore 规则
  - 每条规则添加分类注释

  ## 输出
  完成后报告：两个文件的路径、规则数量、是否合并了已有规则。
  """
)
```

### Agent C：生成 Context Files

```
Agent(
  description="Generate context files",
  run_in_background=true,
  prompt="""
  你是上下文摘要生成专家。

  ## 输入：Scan Context
  {粘贴完整的 Scan Context}

  ## 任务
  1. mkdir -p context
  2. 扫描现有文档源：README*, docs/, wiki/, 根目录 *.md, package.json description 等
  3. 生成三个文件：

  **context/about-project.md**（<1000 字）
  - 项目背景、目标、利益相关者
  - 从 README、package.json 或目录结构推断

  **context/standards.md**（<1000 字）
  - 输出标准、质量要求、格式规范
  - 从 linter/editor 配置或代码模式推断

  **context/domain-knowledge.md**（<1000 字）
  - 领域术语、业务规则、关键概念
  - 从文档和代码注释提取

  ## 约束
  - 使用 Scan Context 中标注的主语言
  - 每个文件不超过 1000 字
  - 素材不足时生成带 <!-- TODO: --> 标记的骨架
  - 写入后用 wc -w context/*.md 验证

  ## 输出
  完成后报告：三个文件路径、各自字数、哪些有 TODO 标记。
  """
)
```

### Agent D：生成 Plugin 骨架（条件执行）

**仅当用户在 Phase 1 审批门确认"需要 Plugin"时才启动此 Agent。** 否则跳过。

```
Agent(
  description="Generate plugin skeleton",
  run_in_background=true,
  prompt="""
  你是 Cowork Plugin 生成专家。

  ## 输入：Scan Context
  {粘贴完整的 Scan Context}

  ## 任务
  根据项目类型自动选择 2-3 个最适合的 skill，创建：

  .claude-plugin/
  ├── plugin.json
  └── skills/
      ├── [skill-1].md
      ├── [skill-2].md
      └── [skill-3].md

  Skill 选择指南：
  - 代码项目 → 代码审查、测试生成、文档生成
  - 数据项目 → 报告生成、数据验证、趋势分析
  - 文档项目 → 文档审校、格式转换、摘要生成
  - 混合项目 → 从上述中各选一个最相关的

  ## 格式要求

  plugin.json:
  {
    "name": "[项目名]-workflow",
    "description": "[描述]",
    "version": "1.0.0"
  }

  每个 skill .md:
  ---
  name: [名称]
  description: [一句话]
  ---
  ## 操作步骤
  [编号步骤]
  ## 质量要求
  [标准]

  ## 约束
  - 使用 Scan Context 中标注的主语言
  - 验证 plugin.json 为合法 JSON

  ## 输出
  完成后报告：plugin 名称、skill 列表及各自描述。
  """
)
```

### 并行执行要点

- **必须在同一轮响应中**发起所有 Agent 调用（不要等一个完成再启动下一个）
- 所有 Agent 使用 `run_in_background: true`
- 每个 Agent 的 prompt 中都包含完整的 Scan Context（因为 Sub-Agent 上下文隔离，无法共享状态）
- 可用 `model: "sonnet"` 为执行 Agent 降低成本（编排者用 Opus，执行者用 Sonnet）

---

## Phase 3/3：收敛 — 验证与交接

所有 Sub-Agent 返回后，主 Agent 执行收敛：

### 3.1 交叉验证

逐项检查每个 Agent 的输出：

| 检查项 | 验证方法 | 通过条件 |
|--------|---------|---------|
| CLAUDE.md 存在且合规 | `wc -c CLAUDE.md` | < 10,000 字符 |
| .claudeignore 存在 | `cat .claudeignore` | 语法无误 |
| .gitignore 包含新规则 | `cat .gitignore` | 含排除规则 |
| context/ 三文件就绪 | `wc -w context/*.md` | 每个 < 1,000 字 |
| plugin.json 合法（若有）| `python3 -m json.tool` 或 `jq .` | 合法 JSON |
| skill 文件有 frontmatter（若有）| 检查 `---` 包裹的 YAML | 含 name + description |

### 3.2 一致性检查

- CLAUDE.md 中提到的目录结构是否与 Scan Context 一致
- .claudeignore 排除的路径是否与 CLAUDE.md "禁止事项" 一致
- context files 中的术语是否与 CLAUDE.md "关键术语" 一致
- 若发现冲突，直接用 Edit 修正（不需要重新启动 Agent）

### 3.3 输出 Cowork 启动清单

```markdown
## Cowork 启动清单

### 执行摘要
- 并行 Agent 数量：[3 或 4]
- 总耗时：~[X] 分钟（串行预计 ~[Y] 分钟，加速 [Z]x）

### 自动生效（打开项目即可）
- [x] CLAUDE.md — [X] 字符（预算 [Y]%）
- [x] .gitignore — [X] 条规则
- [x] .claudeignore — [X] 条规则
- [x] context/ — 3 个文件，共 [X] 字
- [x/跳过] .claude-plugin/ — [已生成 N 个 skills / 已跳过]

### 需手动操作
- [ ] Claude Desktop → Settings → Cowork → Global Instructions
- [ ] 粘贴以下文本：
      [根据项目生成的全局指令，3-5 句话]
- [ ] 在 Cowork 中选择此项目文件夹
- [ ] 测试 prompt："[根据项目生成的测试指令]"

### 上下文预算估算（200K token 窗口）
- CLAUDE.md:      ~[X]K tokens  ([Y]%)
- Context Files:  ~[X]K tokens  ([Y]%)
- 系统占用合计:   ~[X]K tokens  ([Y]%)
- 可用于工作:     ~[X]K tokens  ([Y]%) ← [健康/需优化/危险]
```

---

## 错误处理

- 若某个 Agent 失败或超时，报告哪个 Agent 失败，然后串行重试该 Agent 的任务（不影响其他已完成的 Agent 输出）
- 若项目为空目录（<5 个文件），降级为串行模式（不值得启动并行 Agent）
- 若 Scan Context 超过 5000 字，精简后再分发给 Agent（避免 Sub-Agent 上下文浪费）

---

## 与串行版 setup-cowork 的区别

| 维度 | setup-cowork（串行） | setup-cowork-teams（并行） |
|------|:-------------------:|:------------------------:|
| 执行模式 | 6 阶段逐步串行 | 1 扫描 + 4 并行 + 1 收敛 |
| 审批门 | 2 个（Phase 1, 2） | 1 个（Phase 1，含所有决策） |
| 预计耗时 | ~8-12 分钟 | ~3-5 分钟 |
| Token 成本 | 1x | ~3-4x（4 个独立上下文窗口） |
| 适用场景 | 小项目、需逐步审查 | 大项目、追求速度 |
| 一致性保证 | 天然一致（串行） | 需 Phase 3 交叉验证 |
