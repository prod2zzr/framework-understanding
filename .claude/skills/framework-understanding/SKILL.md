---
name: framework-understanding
description: >
  用多个并行 Agent 快速生成 Cowork 上下文配置（CLAUDE.md、忽略文件、上下文文件、Plugin 骨架）。
  当用户说"帮我配置 Cowork"、"快速初始化项目"、"并行生成配置"、"一键配置 Cowork"、
  "setup project for Cowork"、"generate all config files"、"framework understanding"时触发。
---

# Cowork Setup Architect — Agent Teams 并行版

你是一个 Cowork 项目配置编排者。通过并行 Sub-Agent 同时执行配置任务，大幅缩短配置时间。

**架构**：哪吒模式三段式
- **千里眼**（Phase 1）：扫描项目，生成共享上下文
- **三头六臂**（Phase 2）：4 个 Sub-Agent 并行生成配置文件
- **收敛**（Phase 3）：验证所有输出，生成交接清单

**Compact 防护**：
- Phase 1 完成后、启动 Sub-Agent 之前，主动执行 `/compact`，焦点为："保留完整的 Scan Context（含用户目标摘要和用户标注）以及待执行的 Phase 2 并行任务清单"
- Sub-Agent 天然拥有独立上下文窗口，不受主 Agent compact 影响
- 每个 Sub-Agent 的 prompt 中包含完整 Scan Context 副本

---

## Phase 1/3：千里眼 — 目标收敛 + 项目扫描 + 共享上下文生成

这是唯一的串行阶段。分为两步：先理解用户目标，再扫描项目。

### Step 1：目标收敛（扫描之前）

在做任何技术操作之前，先问用户：

> "在开始配置之前，我需要理解你的工作目标：
>
> 1. **你用 Cowork 主要做什么？**（例如：写分析报告、处理数据、管理文档、做研究、写代码……）
> 2. **典型的工作场景是什么？**（例如：每月生成销售报告、每周整理会议纪要、日常代码审查……）
> 3. **最大的痛点是什么？**（例如：格式不一致、总是忘记某个步骤、重复劳动太多……）
>
> 简单说几句就行，不需要很详细。"

**等待用户回复。**

将用户回答整理为**目标摘要**，嵌入后续的 Scan Context 中。

### Step 2：项目扫描

1. 用 Bash 并行执行以下扫描（在**同一轮**工具调用中发起所有命令）：

```
[Bash] find . -type d -not -path './.git/*' | head -50
[Bash] find . -type f -not -path './.git/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20
[Bash] find . -type f -size +1M -not -path './.git/*' -exec ls -lh {} \; | head -20
[Grep] pattern="password|secret|key|credential|token" （排除 .git）
[Glob] 检查已有配置：CLAUDE.md, .gitignore, .claudeignore, .mcp.json, .claude/, .claude-plugin/
```

2. 检测项目主语言（从文件内容和 README 判断是中文还是英文项目）

3. 将扫描结果整合为**结构化上下文摘要**（Scan Context）。
   **格式模板**：读取 `references/scan-context-template.md` 获取标准格式。

4. **审批门**：展示 Scan Context（含用户目标摘要 + 扫描结果），请用户确认。

> "以上是你的目标理解和项目扫描结果。请确认：
> 1. 我对你的工作目标理解是否准确？需要补充或修正吗？
> 2. 哪些是核心工作区？
> 3. 哪些是归档区？
> 4. 有没有敏感区域？
> 5. 是否需要生成 Plugin 骨架？（Phase 2 会并行处理）
> 确认后我将同时启动 4 个 Agent 并行生成配置。"

**等待用户回复。** 将用户标注和目标修正合并到 Scan Context 中。

---

## Phase 2/3：三头六臂 — 4 个 Sub-Agent 并行

用户确认后，在**同一轮响应**中同时启动所有 Agent（使用 `run_in_background: true`）。

### 启动流程

1. 读取 `references/agent-prompts.md` 获取 Agent A/B/C/D 的完整 prompt 模板
2. 读取 `references/scan-context-template.md` 确认 Scan Context 格式完整
3. 将每个 Agent prompt 模板中的 `{SCAN_CONTEXT}` 占位符替换为实际的 Scan Context
4. 在**同一轮响应**中启动所有 Agent：

| Agent | 职责 | 输出 |
|-------|------|------|
| Agent A | 生成 CLAUDE.md | 项目根目录/CLAUDE.md |
| Agent B | 生成忽略文件 | .claudeignore + .gitignore |
| Agent C | 生成 Context Files | context/*.md（3 个文件）|
| Agent D | 生成 Plugin 骨架 | .claude-plugin/（条件执行）|

### 并行执行要点

- **必须在同一轮响应中**发起所有 Agent 调用
- 所有 Agent 使用 `run_in_background: true`
- 每个 Agent 的 prompt 中都包含完整的 Scan Context（Sub-Agent 上下文隔离）
- 可用 `model: "sonnet"` 降低执行 Agent 成本
- Agent D 仅当用户在 Phase 1 审批门确认"需要 Plugin"时才启动

---

## Phase 3/3：收敛 — 验证与交接

所有 Sub-Agent 返回后，主 Agent 执行收敛。

### 3.1 自动验证

运行 `scripts/verify.sh`，根据输出判断各文件是否合规。

脚本会检查：
- CLAUDE.md 存在且 < 10,000 字符
- .claudeignore 存在且语法无误
- .gitignore 包含排除规则
- context/ 三文件就绪且各 < 1,000 字
- plugin.json 合法 JSON（若有）
- skill 文件有 frontmatter（若有）

### 3.2 一致性检查（人工判断）

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
- [ ] 粘贴以下文本：[根据项目生成的全局指令]
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

- 若某个 Agent 失败或超时，报告哪个 Agent 失败，然后串行重试该 Agent 的任务
- 若项目为空目录（<5 个文件），降级为串行模式
- 若 Scan Context 超过 5000 字，精简后再分发给 Agent

---

## 与串行版 setup-cowork 的区别

| 维度 | setup-cowork（串行） | framework-understanding（并行） |
|------|:-------------------:|:-----------------------------:|
| 执行模式 | 6 阶段逐步串行 | 1 扫描 + 4 并行 + 1 收敛 |
| 审批门 | 2 个（Phase 1, 2） | 1 个（Phase 1，含所有决策） |
| 预计耗时 | ~8-12 分钟 | ~3-5 分钟 |
| Token 成本 | 1x | ~3-4x（4 个独立上下文窗口） |
| 适用场景 | 小项目、需逐步审查 | 大项目、追求速度 |
| 一致性保证 | 天然一致（串行） | 需 Phase 3 交叉验证 |
