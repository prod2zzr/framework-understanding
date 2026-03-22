# Scan Context 模板

以下为 Phase 1 扫描结果的标准输出格式。主 Agent 填写后，完整嵌入每个 Sub-Agent 的 prompt。

---

## Scan Context（共享给所有 Sub-Agent）

### 用户目标
- 主要用途：{USER_PURPOSE}
- 典型场景：{USER_SCENARIO}
- 核心痛点：{USER_PAIN_POINT}

### 项目类型
{PROJECT_TYPE}
<!-- 代码项目 / 数据项目 / 文档项目 / 混合项目 -->

### 主语言
{PRIMARY_LANGUAGE}
<!-- 中文 / 英文 — 所有生成内容必须匹配此语言 -->

### 目录结构
```
{DIRECTORY_TREE}
```
<!-- find . -type d -not -path './.git/*' | head -50 的输出，标注各目录用途 -->

### 文件类型分布
```
{FILE_TYPE_DISTRIBUTION}
```
<!-- find . -type f ... | sed | sort | uniq -c 的输出 -->

### 大文件（>1MB）
{LARGE_FILES}
<!-- 无大文件时填写"无" -->

### 敏感文件
{SENSITIVE_FILES}
<!-- Grep password|secret|key|credential|token 的命中结果；无则填"未检测到" -->

### 已有配置
{EXISTING_CONFIG}
<!-- 列出已存在的：CLAUDE.md / .gitignore / .claudeignore / .mcp.json / .claude/ / .claude-plugin/ -->
<!-- 不存在的不列出 -->

### 用户标注
- 核心工作区：{CORE_AREAS}
- 归档区：{ARCHIVE_AREAS}
- 敏感区：{SENSITIVE_AREAS}
- 是否需要 Plugin：{NEED_PLUGIN}
<!-- 以上来自 Phase 1 审批门的用户回复 -->
