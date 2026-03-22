---
name: quick-framework
description: >
  quickstart 之后的深度配置——跳过重复收集，合并 CLAUDE.md，生成上下文文件和 Plugin。
  当用户说"quick-framework"、"深度配置"、"quickstart 深度配置"、"quickstart 后深度配置"、
  "enhance project"、"深度初始化"、"enhance setup"时触发。
argument-hint: "[可选：补充的工作目标或痛点]"
---

# Quick Framework — quickstart 后的深度配置器

在 `/quickstart` 创建的基础配置上，进一步生成完整的 Cowork 上下文（合并 CLAUDE.md、忽略文件、上下文文件、Plugin 骨架）。

**与 framework-understanding 的区别**：
- 自动检测 quickstart 产出，跳过重复的目标收集
- CLAUDE.md 采用**按章节合并**策略（不重复），而非盲目追加
- 审批门从 5 个问题精简为 2 个

**架构**：哪吒模式三段式（适配 quickstart 版）
- **千里眼**（Phase 1）：检测 quickstart 产出 + 扫描项目 + 生成共享上下文
- **三头六臂**（Phase 2）：4 个 Sub-Agent 并行生成/合并配置文件
- **收敛**（Phase 3）：验证所有输出，生成交接清单

**Compact 防护**：
- Phase 1 完成后、启动 Sub-Agent 之前，主动执行 `/compact`，焦点为："保留完整的 Scan Context（含从 CLAUDE.md 提取的目标摘要和用户标注）、已有 CLAUDE.md 原文、以及待执行的 Phase 2 并行任务清单"
- Sub-Agent 天然拥有独立上下文窗口，不受主 Agent compact 影响
- 每个 Sub-Agent 的 prompt 中包含完整 Scan Context 副本

---

## Phase 1/3：千里眼 — quickstart 检测 + 项目扫描 + 共享上下文生成

这是唯一的串行阶段。分为四步：先检测 quickstart 产出，再自动提取目标，然后扫描项目，最后简化审批。

### Step 1：检测 quickstart 产出

在**同一轮**工具调用中并行执行以下检测：

```
[Bash] git log --oneline -5                    ← 查找 "via /quickstart" 提交记录
[Read] CLAUDE.md                                ← 检查是否包含 quickstart 风格章节（项目概述/目录结构/关键术语/工作偏好/参考资料/禁止事项/Compact Instructions）
[Glob] references/_index.md                     ← 检查资料索引是否存在
```

**判断逻辑**：
- **检测到 quickstart 产出**（满足以下任一条件）：
  - git log 中包含 "via /quickstart"
  - CLAUDE.md 中同时包含 "项目概述" 和 "工作偏好" 和 "Compact Instructions" 章节
  - references/_index.md 存在
  → 进入**衔接模式**，继续 Step 2

- **未检测到 quickstart 产出**：
  → 提示用户："未检测到 quickstart 的产出。建议先运行 `/quickstart` 创建基础配置，或改用 `/framework-understanding` 从头配置。"
  → **终止流程**

### Step 2：从已有 CLAUDE.md 自动提取目标摘要

**不问用户 3 个目标收敛问题。** 直接从 CLAUDE.md 提取：

1. 从 `## 项目概述` 章节提取 → USER_PURPOSE（主要用途）
2. 从 `## 工作偏好` 章节提取 → USER_SCENARIO（工作场景偏好）
3. 从 `## 禁止事项` 章节提取 → USER_PAIN_POINT（核心约束/痛点）
4. 从 `## 关键术语` 章节提取 → 领域上下文

若用户通过 `$ARGUMENTS` 提供了补充信息（如额外的痛点或目标），合并到目标摘要中。

将以上整理为**目标摘要**，嵌入后续的 Scan Context 中。

### Step 3：项目扫描

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
   **特别标注**：在 `已有配置` 字段中注明 "CLAUDE.md (来自 quickstart, N 字符)"。

4. **简化审批门**：展示 Scan Context（含自动提取的目标摘要 + 扫描结果），请用户确认。

> "检测到 quickstart 已创建基础配置，将在此基础上进行深度配置。
>
> 以下是项目扫描结果和从 CLAUDE.md 提取的目标理解：
>
> [展示 Scan Context]
>
> 请确认以下两点：
> 1. **核心工作区和归档区分别是哪些？**（用于配置忽略文件和上下文文件）
> 2. **是否需要生成 Plugin 骨架？**（自定义 skill 快捷命令）
>
> 确认后我将启动并行 Agent 生成深度配置。"

**等待用户回复。** 将用户标注合并到 Scan Context 中。

---

## Phase 2/3：三头六臂 — 4 个 Sub-Agent 并行

用户确认后，在**同一轮响应**中同时启动所有 Agent（使用 `run_in_background: true`）。

### 启动流程

1. 读取 `references/agent-prompts.md` 获取 Agent A/B/C/D 的完整 prompt 模板
2. 读取 `references/scan-context-template.md` 确认 Scan Context 格式完整
3. 将每个 Agent prompt 模板中的 `{SCAN_CONTEXT}` 占位符替换为实际的 Scan Context
4. **Agent A 额外替换**：将 `{EXISTING_CLAUDE_MD}` 占位符替换为当前 CLAUDE.md 的完整原文
5. 在**同一轮响应**中启动所有 Agent：

| Agent | 职责 | 输出 |
|-------|------|------|
| Agent A | **合并** CLAUDE.md（按章节 ENRICH/REPLACE/PRESERVE） | 项目根目录/CLAUDE.md |
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
- **特别检查**：CLAUDE.md 中是否每个章节只出现一次（无重复章节）
- 若发现冲突，直接用 Edit 修正（不需要重新启动 Agent）

### 3.3 输出 Cowork 启动清单

```markdown
## Cowork 深度配置完成（基于 quickstart）

### 执行摘要
- 基础配置来源：quickstart
- 并行 Agent 数量：[3 或 4]
- 总耗时：~[X] 分钟（串行预计 ~[Y] 分钟，加速 [Z]x）

### 自动生效（打开项目即可）
- [x] CLAUDE.md — [X] 字符（merged from quickstart: N enriched, M preserved, K added）
- [x] .gitignore — [X] 条规则（在 quickstart 基础上追加）
- [x] .claudeignore — [X] 条规则（在 quickstart 基础上追加）
- [x] context/ — 3 个文件，共 [X] 字（新增）
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

### 3.4 Git 提交

```bash
git add -A
git commit -m "深度配置 via /quick-framework (session: ${CLAUDE_SESSION_ID})"
```

---

## 错误处理

- 若某个 Agent 失败或超时，报告哪个 Agent 失败，然后串行重试该 Agent 的任务
- 若项目为空目录（<5 个文件），提示用户先运行 `/quickstart`
- 若 Scan Context 超过 5000 字，精简后再分发给 Agent
- 若 CLAUDE.md 合并后发现重复章节，用 Edit 手动去重

---

## 与 framework-understanding 的区别

| 维度 | framework-understanding | quick-framework |
|------|:----------------------:|:--------------:|
| 前置条件 | 无 | 需先运行 quickstart |
| 目标收集 | 问 3 个问题 | 从 CLAUDE.md 自动提取 |
| 审批门问题数 | 5 个 | 2 个 |
| CLAUDE.md 策略 | 已有则追加 | 按章节合并（ENRICH/REPLACE/PRESERVE/ADD） |
| 交互轮次 | 至少 3 轮 | 至少 2 轮 |
| 适用场景 | 从零开始配置 | quickstart 后深度增强 |
