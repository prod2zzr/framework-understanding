# AI 编码工具如何处理工作区/代码库文件——技术调研笔记

调研整理于 2026 年 3 月。涵盖 Claude Code、Cursor、Windsurf、Gemini CLI 和 Gemini Code Assist。

---

## 1. Claude Code（CLI 和 VS Code 扩展）

### 方式：按需智能搜索（不建索引、不做向量化）

Claude Code **不会扫描、索引或向量化**工作区。它采用"智能体搜索"的方式，在运行时通过内置工具发现代码：

- **Glob** —— 文件名模式匹配（例如 `**/*auth*`，意思是在所有目录中找文件名包含 "auth" 的文件）
- **Grep** —— 通过 ripgrep 进行文件内容搜索（在文件内部搜索关键词）
- **Read** —— 按需读取指定文件的内容
- **子智能体（Subagents）** —— 把大范围的代码探索任务委托给一个独立的上下文窗口，由它探索完后返回摘要

搜索过程是**迭代式、自适应的**：模型先发起一次搜索，查看结果，然后用更精确的条件继续搜索。这与一次性的 RAG 检索方式有本质区别。

### 为什么不建索引？

Claude Code 的创建者 Boris Cherny 在 2025 年 5 月的 Latent Space 播客中表示：*"我们早期版本尝试过 RAG……最终我们选择了纯智能体搜索……因为它的效果远远超过了其他所有方案。"*

主要原因：
- **精确度**：grep 找到的是精确匹配；向量嵌入会引入"看起来像但实际不是"的误报
- **实时性**：没有索引就不会有"索引过时"的问题，编辑代码后立刻能搜到最新内容
- **简单**：零配置，无需构建或维护任何东西
- **隐私**：不需要把代码发送到外部服务器去计算嵌入向量

### VS Code 扩展

VS Code 扩展底层包装的是同一个 CLI 引擎。额外提供：
- 感知当前打开的文件和选中的代码
- 支持 `@` 引用文件并指定行范围
- Auto Memory（MEMORY.md）：跨会话保留用户的偏好和模式
- **不做任何额外的嵌入或预处理**，和 CLI 的文件处理方式完全一致

### 成本控制

Claude Code 通过 Anthropic 的提示缓存（Prompt Caching）实现了 92% 的提示前缀复用率。系统提示、工具定义和 CLAUDE.md 内容构成了多轮对话间共享的前缀，缓存读取的 token 费用仅为原价的 0.1 倍。

### Claude Code 使用 RAG 吗？

**不使用。** Claude Code 内部不使用 RAG 或基于嵌入的搜索。但是：
- **Claude Projects**（网页版）在项目知识超过上下文窗口时会使用内部 RAG
- 第三方 MCP 插件（如 Zilliz 的 `claude-context`、`rag-cli`）可以为 Claude Code 添加基于嵌入的语义搜索能力

---

## 2. Cursor

### 方式：预建向量索引（RAG）

Cursor **会在后台主动索引整个代码库**，使用完整的 RAG 流水线：

1. **代码切块**：使用 tree-sitter（一种语法分析器）把文件按语法结构（函数、类等）切成代码块
2. **向量嵌入**：用 Cursor 自研的嵌入模型为每个代码块生成向量
3. **存储**：向量存入 Turbopuffer（一种无服务器的向量数据库）
4. **增量更新**：用 Merkle 树（一种"文件指纹树"数据结构）检测哪些文件发生了变化；每 10 分钟检查一次，只重新处理变化的部分
5. **团队复用**：同一组织内的成员代码库平均有 92% 的相似度，可以复用队友的索引，将首次查询时间从数小时降低到数秒

### 查询流程

1. 把用户的问题用相同的嵌入模型转换成向量
2. 在 Turbopuffer 中进行向量相似度搜索，返回排名靠前的候选代码块
3. 服务器端只存储元数据（加密混淆后的文件路径 + 行号范围），源代码始终留在本地
4. 本地客户端根据元数据读取实际代码
5. 把检索到的代码块连同用户的问题一起发送给大语言模型

### 隐私保护

- 文件路径在客户端进行加密混淆，然后才上传
- Cursor 服务器和 Turbopuffer 中**不存储任何代码原文**
- 云端只保留向量和元数据

### 混合搜索

Cursor 同时使用传统的 grep/ripgrep 和语义搜索。AI 会根据查询类型自动决定使用哪种方式。

---

## 3. Windsurf（原 Codeium）

### 方式：基于 AST 的嵌入 + 专有检索引擎

Windsurf 使用**基于 RAG 的上下文引擎**，包含多个专有组件：

1. **AST 代码切块**：客户端生成抽象语法树（AST）表示，在函数、方法、类的边界切割代码（比简单的按行切割更精准）
2. **向量嵌入**：代码块独立发送到 Windsurf 服务器进行嵌入计算
3. **本地向量存储**：计算好的向量连同指针（文件路径、行号范围）存储在用户本地机器上
4. **增量更新**：后台进程监控代码变化，重新计算受影响的 AST 代码块和嵌入

### 专有技术

- **Riptide**（原名 Cortex）：专门训练的语言模型，用于评估代码片段的相关性。声称检索召回率比传统嵌入系统提高了 200%
- **Cascade**：智能体系统，追踪开发者的"意图"——自动找出相关文件，无需手动用 `@` 指定。例如你在修一个导航 bug，它会自动把相关的页面文件和路由逻辑都找出来
- **M-Query**：用于大语言模型 RAG 的专有检索技术

### 本地 vs 远程索引

- **本地模式**：整个本地代码库被索引；在你编码过程中进行检索
- **远程模式**（团队/企业版）：索引远程代码仓库，适用于多仓库的组织

### 隐私

单次请求不会包含整个代码库。代码解析在客户端完成；只有独立的代码片段被发送到服务器用于嵌入计算，服务器永远不会一次性接收完整的代码库。

---

## 4. Gemini CLI

### 方式：按需文件系统探索（不建索引）

Gemini CLI **不会索引代码库**。和 Claude Code 类似，它在运行时探索文件：

- **ListDirectory** —— 列出文件和子目录
- **ReadFile** —— 读取指定文件内容
- **FindFiles**（glob）—— 按模式匹配查找文件

它使用 ReAct（推理与行动）循环来迭代式地探索代码库。

### 代码库索引：尚未实现

完整的代码库索引是 GitHub 上的**待实现功能请求**（Issue #2065 和 #5150，截至 2025 年中）。社区提出了以下方案：
- 将代码库处理为向量表示
- 在 `gemini-cli start` 时启动本地向量数据库
- 构建函数/类索引作为折中方案

### 社区变通方案

"函数索引"方法（提取所有函数/类的签名列表）提供了一种介于"递归列出文件"和"完整代码库导入"之间的折中方案，能减少搜索次数并提升 AI 对代码库的整体理解。

---

## 5. Gemini Code Assist（IDE 插件）

### 方式：预建嵌入索引（类似 Cursor）

与 Gemini CLI 不同，Gemini Code Assist **会索引代码库**：

- 打开项目时自动开始索引
- **本地代码库感知**：搜索当前文件夹和打开的标签页中的文件
- **代码定制**（标准版/企业版）：使用嵌入技术索引远程代码仓库
- 每 24 小时重新索引一次，保持建议内容最新
- 嵌入向量存储在单租户环境中；代码不会用于模型训练

### 智能体模式

智能体模式对"你的整个项目有全面理解"——分析整个代码库，按需请求文件/文件夹。支持 MCP 进行工具集成。

---

## 6. 两种路线的权衡对比

| 维度 | 按需搜索（Claude Code、Gemini CLI） | 预建索引（Cursor、Windsurf、Gemini Code Assist） |
|---|---|---|
| **启动时间** | 零等待 | 需要初始索引 |
| **查询精确度** | 精确匹配，无误报 | 可以进行语义/概念级的模糊匹配 |
| **实时性** | 始终是最新状态 | 可能滞后，需要定期重新索引 |
| **隐私** | 数据不离开本地机器 | 嵌入向量可能在云端计算/存储 |
| **语义搜索** | 仅限关键词/模式匹配 | 能找到关键词不匹配但含义相关的代码 |
| **Token 消耗** | 每次搜索结果都进入上下文（费 token） | 一次性建索引后每次查询只返回精简结果 |
| **大型仓库支持** | 反复扫描可能很贵 | 一次性构建索引后搜索极快 |
| **跨仓库发现** | 困难 | 通过远程索引自然支持 |
| **透明度** | 可以清楚看到发起了哪些搜索 | 检索过程不透明 |
| **自适应性** | 多轮迭代逐步精炼 | 每次查询单次检索 |

### 按需搜索效果好的场景

- 代码库组织良好、命名规范清晰
- 需要精确字符串匹配的任务（例如查找某个函数的所有调用方）
- 对隐私要求高的环境
- 代码快速变化中（没有"索引过时"的问题）

### 预建索引效果更好的场景

- 概念性/语义性的查询（例如"我们在哪里处理了认证失败的情况？"）
- 大型单一仓库，手动导航不现实
- 跨仓库搜索
- 新工程师上手探索不熟悉的系统

---

## 7. Claude Code 的上下文管理策略

### CLAUDE.md

- 每次对话开始时自动读取
- 使用 `/init` 命令可以从项目自动生成一个初始文件
- 建议控制在约 300 行以内，越短越好
- 建议包含：常用 bash 命令、代码风格规范、工作流约定
- **用指针替代复制**——使用 `文件名:行号` 引用，不要把代码片段直接粘贴进去
- 不要在 CLAUDE.md 中用 `@` 引用大型文档文件（会让每次运行时上下文都很臃肿）

### CLAUDE.md 的层级结构

- 仓库根目录：项目级别的指令
- 子目录：特定范围的指引
- `~/.claude/CLAUDE.md`：个人全局默认设置

### @ 引用

- `@文件名` 让 Claude 立即访问该文件
- 在 VS Code 中支持从选中内容指定具体行范围
- 比直接粘贴代码到提示框中更节省 token

### 子智能体

- 把研究性的任务委托给一个拥有独立上下文窗口的子智能体
- 主对话保持干净，专注于实现
- 通过提示词触发，例如"用子智能体调查一下 X"

### 上下文卫生

- 积极使用 `/clear` 重置上下文
- 用 `/context` 监控 token 使用量（200k 窗口；大型仓库中基线约 20k）
- 在 CLAUDE.md 中自定义压缩行为（例如"压缩时保留已修改文件的列表"）
- 在一个会话中规划，在新的干净会话中执行

### Hooks（钩子）

- 在 Claude 工作流的特定节点运行的确定性操作
- 与 CLAUDE.md 中的指令（建议性的）不同，钩子是**保证执行**的
- 适用于代码检查、格式化、测试——不是给模型的指令

### .claudeignore

- 阻止 Claude 处理大型仓库中过多的上下文
- 对于大型代码库来说，这是**最有效的性能优化手段**

---

## 8. 总结对比表

| 工具 | 建索引？ | 向量嵌入？ | 搜索方式 | 使用 RAG？ |
|---|---|---|---|---|
| **Claude Code（CLI）** | 否 | 否 | Grep、Glob、Read（智能体式） | 否 |
| **Claude Code（VS Code）** | 否 | 否 | 与 CLI 相同 | 否 |
| **Cursor** | 是（后台自动） | 是（Turbopuffer 云端） | 语义搜索 + grep 混合 | 是 |
| **Windsurf** | 是（AST 驱动） | 是（本地向量存储） | Riptide + M-Query | 是 |
| **Gemini CLI** | 否 | 否 | ListDirectory、ReadFile、FindFiles | 否 |
| **Gemini Code Assist（IDE）** | 是（自动） | 是（嵌入向量） | 语义搜索 + 本地感知 | 是 |
| **OpenAI Codex CLI** | 否 | 否 | 文本搜索、文件匹配 | 否 |

---

## 参考资料

- [Claude Code 不会索引你的代码库——Vadim's Blog](https://vadim.blog/claude-code-no-indexing)
- [Claude Code 常见问题](https://support.claude.com/en/articles/12386420-claude-code-faq)
- [Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices)
- [Cursor 实际上是如何索引你的代码库的——Towards Data Science](https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/)
- [Cursor 如何快速索引代码库——Engineer's Codex](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)
- [Cursor 安全代码库索引](https://cursor.com/blog/secure-codebase-indexing)
- [Windsurf 上下文感知概述](https://docs.windsurf.com/context-awareness/overview)
- [Windsurf 安全](https://windsurf.com/security)
- [Gemini CLI GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI 代码库索引请求（Issue #2065）](https://github.com/google-gemini/gemini-cli/issues/2065)
- [Gemini Code Assist 概述](https://developers.google.com/gemini-code-assist/docs/overview)
- [Gemini Code Assist 代码定制](https://developers.google.com/gemini-code-assist/docs/code-customization)
- [Claude Context MCP（Zilliz）](https://github.com/zilliztech/claude-context)
- [Claude Code 不做 RAG 的特殊之处——Medium](https://zerofilter.medium.com/why-claude-code-is-special-for-not-doing-rag-vector-search-agent-search-tool-calling-versus-41b9a6c0f4d9)
- [Claude Code 仅用 Grep 检索的问题——Milvus Blog](https://milvus.io/blog/why-im-against-claude-codes-grep-only-retrieval-it-just-burns-too-many-tokens.md)
- [搜索与索引策略——Developer Toolkit](https://developertoolkit.ai/en/shared-workflows/context-management/codebase-indexing/)
- [从 RAG 到 Context——RAGFlow 2025 回顾](https://ragflow.io/blog/rag-review-2025-from-rag-to-context)
- [用函数索引提升 Gemini CLI 的代码上下文](https://wietsevenema.eu/blog/2025/gemini-cli-function-indexing/)
- [如何写好 CLAUDE.md——HumanLayer](https://www.humanlayer.dev/blog/writing-a-good-claude-md)
