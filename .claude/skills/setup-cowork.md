---
name: setup-cowork
description: 扫描项目并生成完整的 Cowork 上下文架构（CLAUDE.md、忽略文件、上下文文件、可选 Plugin 骨架）
---

# Cowork Setup Architect

你是一个 Cowork 项目配置架构师。用户调用此 skill 时，你将对当前项目目录执行六阶段配置流程，为 Claude Cowork 生成完整的上下文架构。

**核心原则**：
- 每个阶段开始时打印阶段标题（如 "## Phase 1/6：项目扫描与诊断"）
- 自动检测项目中已有文件的主语言（中文/英文/其他），所有生成内容匹配该语言
- 严格遵守 token 预算约束
- 遇到已有配置文件时，先询问用户再操作

---

## Phase 1/6：项目扫描与诊断

执行以下扫描并汇总结果：

1. **目录树概览**：用 Bash 执行 `find . -type d -not -path './.git/*' | head -50` 获取目录结构
2. **文件类型分布**：用 Bash 执行 `find . -type f -not -path './.git/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20` 统计各扩展名数量
3. **大文件列表**：用 Bash 执行 `find . -type f -size +1M -not -path './.git/*' -exec ls -lh {} \; | head -20` 找出大于 1MB 的文件
4. **敏感文件检测**：用 Grep 搜索 `password|secret|key|credential|token` 模式，以及用 Glob 查找 `.env*` 文件
5. **已有配置检测**：用 Glob 检查 `CLAUDE.md`、`.gitignore`、`.claudeignore`、`.mcp.json`、`.claude/`、`.claude-plugin/` 是否存在

将五项结果整理为结构化摘要，然后 **停下来请用户确认**：
> "以上是项目扫描结果。请确认：
> 1. 哪些是核心工作区？
> 2. 哪些是归档区（不需要 Claude 读取）？
> 3. 有没有敏感区域需要特别排除？
> 确认后我将进入 Phase 2。"

**等待用户回复后再继续。**

---

## Phase 2/6：生成 CLAUDE.md

1. 先检查项目根目录是否已有 `CLAUDE.md`。若存在，问用户："已有 CLAUDE.md，是覆盖还是合并？"
2. 基于 Phase 1 扫描结果和用户标注，用 Write 工具生成 `CLAUDE.md`，包含以下部分：

```
# [项目名称]

## 项目概述
[一段话描述项目目的和范围]

## 目录结构
[列出主要目录及其用途]

## 关键术语
[项目专有名词及定义]

## 工作偏好
[语言、数字格式、日期格式、表格风格、引用规范]

## 输出标准
[文件命名规则、格式要求]

## 禁止事项
[不要修改的文件/目录、不要做的操作]
```

3. **硬约束**：目标 2000-5000 字，绝对不超过 10,000 字。写入后用 Bash 执行 `wc -c CLAUDE.md` 验证。
4. **停下来展示完整内容，请用户确认或要求修改。** 用户确认后再继续。

---

## Phase 3/6：生成 .claudeignore / .gitignore

1. 基于 Phase 1 扫描结果，确定排除规则：
   - 大于 5MB 的文件和目录
   - 用户标注的归档目录
   - 构建产物（`node_modules/`、`dist/`、`build/`、`__pycache__/`——仅当项目中实际存在时才添加）
   - 敏感文件（`.env`、`*.key`、`*credentials*`、`*secret*`）
   - 二进制媒体文件（`*.zip`、`*.tar.gz`、`*.mp4`、`*.mov`、`*.psd`）
   - 临时文件（`*.tmp`、`*.swp`、`~$*`、`.DS_Store`）

2. **处理已有 .gitignore**：若存在，用 Read 读取现有内容，仅追加新规则（不重复、不覆盖）。用 Edit 工具合并。
3. 用 Write 生成 `.claudeignore`（规则与 .gitignore 相同或更严格）。
4. 简要展示生成的规则列表，继续下一阶段（无需等待审批，除非用户主动干预）。

---

## Phase 4/6：生成 Context Files

1. 用 Bash 执行 `mkdir -p context`
2. 扫描现有文档源：README*、docs/、wiki/、*.md（根目录）、package.json 的 description 字段等
3. 生成三个文件，每个 **不超过 1000 字**：

**context/about-project.md**：
- 项目背景、目标、利益相关者
- 从 README、package.json 或项目结构推断

**context/standards.md**：
- 输出标准、质量要求、格式规范
- 从 linter 配置、editor 配置、style guide 或代码模式推断

**context/domain-knowledge.md**：
- 领域术语、业务规则、关键概念
- 从文档和代码注释提取

4. 若某个文件的素材不足，生成带 `<!-- TODO: -->` 标记的骨架模板，供用户后续补充。
5. 写入后用 Bash 执行 `wc -w context/*.md` 验证字数约束。

---

## Phase 5/6：生成 Plugin 骨架（条件执行）

**先问用户**：
> "是否需要为此项目生成 Cowork Plugin 骨架（包含自定义 Skills）？这一步是可选的。"

### 如果用户选择"是"：

1. 根据项目类型自动建议 2-3 个常用 skill（例如：代码项目 → 代码审查/测试生成/文档生成；数据项目 → 报告生成/数据验证/趋势分析）
2. 请用户确认或自定义 skill 列表
3. 创建以下结构：

```
.claude-plugin/
├── plugin.json
└── skills/
    ├── [skill-1].md
    ├── [skill-2].md
    └── [skill-3].md
```

**plugin.json** 格式：
```json
{
  "name": "[项目名]-workflow",
  "description": "[项目名]标准操作流程和质量规范",
  "version": "1.0.0"
}
```

**每个 skill .md 文件** 格式：
```markdown
---
name: [Skill 名称]
description: [一句话描述]
---

## 操作步骤
[编号列表，描述 Claude 执行此 skill 时应遵循的步骤]

## 质量要求
[此 skill 输出的质量标准]
```

### 如果用户选择"否"：

跳过此阶段，直接进入 Phase 6。

---

## Phase 6/6：验证与交接

### 验证清单

逐项验证并报告结果：

1. **CLAUDE.md**：确认存在，用 `wc -c` 检查字符数 < 10,000
2. **.claudeignore**：确认存在，语法无明显错误
3. **.gitignore**：确认存在且包含新增规则
4. **context/ 文件**：确认三个文件都存在，用 `wc -w` 检查每个 < 1,000 字
5. **Plugin（若 Phase 5 执行了）**：用 Bash 执行 `python3 -m json.tool .claude-plugin/plugin.json` 或 `cat .claude-plugin/plugin.json | jq .` 验证 JSON 格式；检查每个 skill 文件的 YAML frontmatter

### 输出 Cowork 启动清单

在对话中输出以下清单（不写入文件）：

```markdown
## ✅ Cowork 启动清单

### 自动生效（打开项目即可）
- [x] CLAUDE.md — 已放置在项目根目录
- [x] .gitignore — 排除规则已更新
- [x] .claudeignore — 额外排除规则已生成
- [x] context/ — 结构化上下文文件已就绪
- [x/跳过] .claude-plugin/ — Plugin 和 Skills [已生成/已跳过]

### 需手动操作
- [ ] 打开 Claude Desktop → Settings → Cowork → Global Instructions
- [ ] 粘贴以下全局指令建议：

    [根据项目生成的全局指令建议文本，3-5 句话]

- [ ] 在 Cowork 中选择此项目文件夹
- [ ] 测试：输入以下 prompt 验证配置是否生效：

    "[根据项目生成的测试 prompt]"

### 上下文预算估算
- CLAUDE.md: ~[X]K tokens ([Y]%)
- Context Files: ~[X]K tokens ([Y]%)
- 系统占用合计: ~[X]K tokens ([Y]%)
- 可用于实际工作: ~[X]K tokens ([Y]%) ← [健康/需优化/危险]
```

---

## 错误处理

- 若任何阶段因文件权限或目录不存在而失败，报告具体错误并尝试替代方案
- 若扫描发现项目为空目录或极小项目（<5 个文件），简化流程：跳过 Phase 4 的深度提取，直接生成 TODO 模板
- 若 `jq` 和 `python3` 都不可用于 JSON 验证，用 Bash 的 `cat` 展示内容供用户人工检查
