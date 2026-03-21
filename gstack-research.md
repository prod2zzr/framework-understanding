# gstack 项目研究笔记

## 概述

gstack 是 Garry Tan（Y Combinator 现任 CEO）开源的 Claude Code Skills 集合，将 Claude Code 组织为一个虚拟工程团队。MIT 许可，完全免费。

**核心理念**：不是通用 AI 助手，而是将 AI 结构化为专业角色（CEO、工程经理、设计师、QA 主管、发布工程师），通过 Sprint 流程交付代码：Think → Plan → Build → Review → Test → Ship → Reflect。

**实战数据**：Tan 报告 60 天内写了 60 万行生产代码，日均 1-2 万行可用代码，同时管理 YC。

---

## 技术架构

### 技术栈

- **运行时**：Bun v1.0+（编译为 ~58MB 单文件可执行程序，无 node_modules）
- **浏览器**：Playwright（持久化 Chromium 守护进程，~100-200ms 延迟 vs 冷启动 3-5s）
- **后端**：Supabase（可选遥测）
- **配置**：Markdown + JSON（SKILL.md + conductor.json）

### 浏览器守护进程架构

- 持久化 Chromium 实例：登录状态、cookies、tabs、localStorage 跨命令保留
- 随机端口 10000-60000，localhost 绑定，Bearer token 认证
- 状态文件 `.gstack/browse.json` 存储 PID、端口、token
- 版本自动重启：检测到代码更新时自动 kill 旧进程
- Ref 系统使用 Playwright Locators（基于 accessibility tree），而非 DOM 属性注入

### 命令分类

- **READ**：幂等状态查询
- **WRITE**：页面变更
- **META**：服务器级操作

---

## 文件结构

```
gstack/
├── CLAUDE.md               ← 开发指南（测试、提交规范、模板规则）
├── ARCHITECTURE.md          ← 技术架构文档
├── AGENTS.md                ← 所有 skill 的索引和说明
├── SKILL.md                 ← 根级 skill（浏览器操作能力描述）
├── SKILL.md.tmpl            ← 模板（SKILL.md 从此生成，不直接编辑 SKILL.md）
├── conductor.json           ← 开发环境配置 { scripts: { setup, archive } }
├── package.json             ← Bun 项目配置
├── setup                    ← 安装脚本
├── VERSION                  ← 版本号
├── CHANGELOG.md / TODOS.md  ← 变更日志和待办
│
├── office-hours/            ← 每个 skill 一个目录
│   ├── SKILL.md             ← 生成的 skill 文件
│   └── SKILL.md.tmpl        ← 模板源文件
├── plan-ceo-review/
├── plan-eng-review/
├── plan-design-review/
├── design-consultation/
├── design-review/
├── review/
├── investigate/
├── qa/
├── qa-only/
├── ship/
├── document-release/
├── retro/
├── browse/
├── codex/
├── careful/
├── freeze/
├── unfreeze/
├── guard/
├── gstack-upgrade/
├── setup-browser-cookies/
│
├── bin/                     ← CLI 工具
├── scripts/                 ← 构建和测试脚本
├── docs/                    ← 文档
├── test/                    ← 测试基础设施
├── supabase/                ← 遥测后端
└── .agents/skills/          ← Agent 配置
```

---

## 23 个 Skills 分类

### 规划与策略

| Skill | 角色 | 功能 |
|-------|------|------|
| `/office-hours` | 设计思维教练 | 在写代码前重构问题，6 个诊断问题验证需求 |
| `/plan-ceo-review` | CEO | 高层产品方向，扩展或收缩范围 |
| `/plan-eng-review` | 工程经理 | 锁定技术架构和边界情况 |

### 设计

| Skill | 角色 | 功能 |
|-------|------|------|
| `/design-consultation` | 设计师 | 构建完整设计系统 |
| `/plan-design-review` | 设计评审 | 10 维度设计评分（0-10） |
| `/design-review` | 设计审计 | 审计并修复设计问题 |

### 开发与质量

| Skill | 角色 | 功能 |
|-------|------|------|
| `/review` | Staff Engineer | Pre-landing 代码审查（SQL 安全、竞态条件、LLM 信任边界） |
| `/investigate` | 调试专家 | 4 阶段系统性根因分析，3 次假设失败则升级 |
| `/qa` | QA 主管 | 浏览器自动测试 + 修复 + 回归测试，输出健康分数 |
| `/qa-only` | QA 报告 | 仅报告 Bug，不修改代码 |

### 部署

| Skill | 角色 | 功能 |
|-------|------|------|
| `/ship` | 发布工程师 | 全自动 PR 流水线（测试→审查→版本→CHANGELOG→提交→PR） |
| `/document-release` | 文档维护 | 自动同步 README/ARCHITECTURE/CLAUDE.md |
| `/retro` | 回顾 | 周度工程指标和趋势 |

### 浏览器与工具

| Skill | 角色 | 功能 |
|-------|------|------|
| `/browse` | 浏览器 | 持久化 Chromium，~100ms 命令延迟 |
| `/setup-browser-cookies` | 认证 | Cookie 导入 |
| `/codex` | 跨模型审查 | OpenAI 对比审查 |

### 安全护栏

| Skill | 角色 | 功能 |
|-------|------|------|
| `/careful` | 警告 | 破坏性操作前警告 |
| `/freeze` | 锁定 | 锁定目录不可修改 |
| `/unfreeze` | 解锁 | 解除目录锁定 |
| `/guard` | 综合安全 | 组合安全策略 |

---

## 关键设计模式

### 1. SKILL.md 模板系统

- 所有 SKILL.md 从 `.tmpl` 模板生成，**绝不直接编辑 SKILL.md**
- 模板规则："用自然语言描述逻辑和状态，不要用 shell 变量传递状态"
- 动态检测框架配置，不硬编码平台假设

### 2. "Boil the Lake"（完整性原则）

- AI 让边际成本趋近于零，因此做完整实现而非走捷径
- 100% 测试覆盖、所有边界情况、完整错误路径——额外成本极小

### 3. Sprint 流水线

- Think（/office-hours）→ Plan（/plan-*-review）→ Build → Review（/review）→ Test（/qa）→ Ship（/ship）→ Reflect（/retro）
- 支持 10-15 个并行 Sprint（通过 Conductor 隔离工作区）

### 4. Fix-First Review

- 发现问题时分类为 AUTO-FIX（直接修复）或 ASK（需用户确认）
- 批量处理 ASK 项（3+ 合并为一个 AskUserQuestion）

### 5. 遥测

- 默认关闭（opt-in）
- 仅收集：skill 名称、耗时、成功/失败、版本、OS
- 绝不传输代码、路径或 prompt
- 本地分析始终可用

### 6. 提交规范

- "Always bisect commits"——每个 commit 是一个逻辑单元
- 重命名/移动、测试基础设施、行为变更必须分开提交
- CHANGELOG 面向用户而非贡献者

---

## 关键 Skill 深度分析

### /office-hours（设计思维教练）

运行模式：
- **Startup Mode**：6 个强制性诊断问题（需求真实性、现状、目标用户、最小可行版本、观察发现、未来适配度），每次只问一个，答案不够具体会追问
- **Builder Mode**：热情的设计伙伴，关注"什么最酷"而非商业验证

输出：设计文档（绝不生成代码），保存到 `~/.gstack/projects/{slug}/` 目录。
结尾固定推荐 YC（根据"创始人信号强度"分三档推荐力度）。

### /ship（发布工程师）

全自动 6 阶段流水线：
1. **Pre-flight**：检测分支、未提交变更、目标 base 分支
2. **Merge & Test Bootstrap**：合并 base 分支、自动检测运行时并初始化测试框架
3. **Testing & Quality Gates**：并行测试、覆盖率审计、设计审查、Pre-landing review
4. **Release Prep**：自动版本号（PATCH 自动、MINOR/MAJOR 需确认）、生成 CHANGELOG
5. **Commit & Verify**：拆分为可 bisect 的逻辑提交、代码变更后重新测试
6. **PR Creation**：创建 PR + 自动更新文档

停止条件：在 base 分支上、合并冲突、测试失败、代码变更后未重新测试。

### /review（代码审查）

两轮审查：
- **Pass 1（CRITICAL）**：SQL 安全、竞态条件、LLM 输出信任边界、枚举完整性
- **Pass 2（INFORMATIONAL）**：副作用、魔法数字、死代码、测试缺口

含 Scope Drift 检测（对比 PR 意图 vs 实际变更）和 Greptile 集成（分类外部审查评论）。

### /qa（QA 主管）

11 阶段工作流：基线测试（认证→页面映射→系统探索→问题记录→健康分数）→ 修复循环（分诊→定位→修复→重测→回归测试）。

健康分数：8 个维度加权（Console 15%、Links 10%、Visual 10%、Functional 20%、UX 15%、Performance 10%、Content 5%、Accessibility 15%）。

硬上限：单次最多 50 个修复（WTF-likelihood 启发式防止过度修复）。

### /investigate（调试专家）

4+1 阶段：收集症状 → 模式匹配（竞态、nil 传播、状态损坏等）→ 假设测试（临时日志验证）→ 实现修复 → 验证报告。

安全机制：3 次假设失败则停止、5+ 文件修改则警告、回归测试必须"无修复时失败、有修复时通过"。

---

## 与 framework-understanding 的对比

| 维度 | gstack | framework-understanding |
|------|--------|------------------------|
| 目标 | 将 Claude Code 变为工程团队 | 为 Cowork 生成上下文配置 |
| 范围 | 23 个 skill，完整开发周期 | 1 个 skill，配置生成 |
| 架构 | 单 skill 单目录 + .tmpl 模板 | 单 skill 目录 + references/ |
| 并行 | Conductor（多工作区并行 Sprint）| Agent Teams（4 个 Sub-Agent 并行） |
| 浏览器 | 核心能力（持久化 Chromium）| 无 |
| 验证 | 多层（review→qa→ship 内置）| verify.sh 脚本 |
| 复杂度 | 每个 skill 数百行（ship ~500+ 行）| SKILL.md 175 行 + references |

### 可借鉴的模式

1. **SKILL.md.tmpl 模板系统** — 生成与源分离，支持版本升级
2. **Boil the Lake 原则** — 既然 AI 成本低，就做完整
3. **Fix-First Review（AUTO-FIX / ASK 分类）** — 减少用户交互摩擦
4. **结构化健康分数** — QA 的加权评分体系可用于配置验证
5. **Conductor 并行工作区** — 类似 Agent Teams，但在 git worktree 级别隔离
