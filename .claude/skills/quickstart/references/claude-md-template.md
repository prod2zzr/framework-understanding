# CLAUDE.md 生成模板

此文件供 quickstart skill 在 Phase 3 读取并填充。用 `{placeholder}` 标记需要动态替换的内容。

---

```markdown
# {project_name}

## 项目概述

{project_description}

## 目录结构

{directory_structure}

## 关键术语

{key_terms}

## 工作偏好

- 语言：{language}
- 输出格式：Markdown
- 文件命名：kebab-case（小写 + 连字符）

## 参考资料

references/ 目录下包含以下资料：

{references_list}

## 禁止事项

- 不要修改 references/ 中的原始资料文件
- 不要生成超过 5000 字的单个文件（拆分为多个文件）

## Compact Instructions

压缩时必须保留：
- 项目目标：{project_description_short}
- 当前任务的完整计划和进度状态
- 已修改文件的完整列表
- references/ 目录中各资料的核心要点
```

---

## 填充说明

| 占位符 | 数据来源 | 示例 |
|--------|---------|------|
| `{project_name}` | Phase 1 用户输入 | `ai-landscape` |
| `{project_description}` | Phase 1 用户描述 + 资料摘要 | "调研 2026 年 AI 开发工具格局，对比主流 Agent 框架" |
| `{project_description_short}` | 上述描述的一句话精简版 | "AI 开发工具调研" |
| `{directory_structure}` | 根据所选模板，从 templates/*.md 提取 | 见模板文件 |
| `{key_terms}` | 从 references/ 中收集的资料提取 5-10 个 | `- **Agent**: 自主执行任务的 AI 系统` |
| `{language}` | 自动检测用户语言 | `中文` 或 `English` |
| `{references_list}` | Phase 2 生成的 _index.md 内容 | 见资料索引 |

## 字数约束

- 目标：500-1500 字
- 硬上限：3000 字
- 若资料丰富导致 references_list 过长，只列前 10 条并加"更多见 references/_index.md"
