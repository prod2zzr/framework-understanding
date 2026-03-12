# Cowork 的"黑箱悖论"：为什么更精确的指令反而得不到更好的结果？

---

## 1. 一个反直觉的发现

在使用 Claude Cowork 的过程中，有一种让人困惑的体验：

> 当你以为自己有了更多使用经验，给出更精准的指令时，结果反而不如让 Claude 自由发挥来得好。放太多背景资料到项目目录中也不会改善结果——有时还会更差。

与此同时，Claude Code 虽然需要手动安装 skills、编写 CLAUDE.md、配置 hooks，看起来更"麻烦"，但执行过程透明可控，结果可预期。

这是个例还是普遍现象？如果是普遍现象，Cowork 存在的意义是什么？它是否也需要 skills 体系的辅助？

**答案是：这些观察并非个例。它们是由架构差异和上下文管理机制决定的系统性现象。**

---

## 2. "精确指令反而更差"——Setup vs. Prompting 的根本区别

### 问题的真正根源

直觉告诉我们：更精确的 prompt → 更好的结果。但在 Cowork 中，这个等式经常失效。社区经验揭示了原因：

**Cowork 的成功不取决于单次 prompt 的精度，而取决于"上下文架构"的预配置。**

所谓"上下文架构"，是指在发出具体任务之前，就已经建立好的指导框架：
- **全局指令**（Global Instructions）：告诉 Claude 你的工作风格、偏好、输出标准
- **Context Files**：提供项目背景、命名规范、模板要求
- **Plugins**：扩展 Claude 的工具能力（MCP 服务器、自定义连接器）

社区中的成功案例显示：花 30 分钟搭建好上下文架构的用户，之后只用简单的一句话 prompt 就能持续产出专业级成果。反过来，跳过这一步而试图在每次 prompt 中塞入所有细节的用户，得到的结果反而不稳定。

### 为什么会这样？

原因在于模型处理信息的方式：

```
方式 A（逐次精确描述）：
  每个 prompt 都是 500 字的详细指令
  → 模型每次都在"重新理解"你的需求
  → 每次理解可能有偏差
  → 结果不一致

方式 B（预配置 + 简洁指令）：
  全局指令已经定义好风格、标准、偏好
  → 每个 prompt 只需说"做 X"
  → 模型在稳定的框架内工作
  → 结果一致
```

### Code 为什么天然避免了这个问题？

Claude Code 的工作流**天然要求用户做 setup**：

- 安装 skills → 你在定义工具能力的边界
- 编写 CLAUDE.md → 你在写合作规则
- 配置 hooks → 你在设定自动化检查点
- 设置权限模式 → 你在划定信任边界

这些配置行为本身就是在搭建"上下文架构"。Code 用户不会意识到自己在做这件事，因为这是使用 Code 的必要步骤。但 Cowork 用户可以**完全跳过配置直接开始工作**——这恰恰是"黑箱感"的起源。

**结论：Cowork 缺的不是指令精度，而是配置化的指导框架。**

---

## 3. "放太多文档反而更差"——上下文过载的技术原因

### 有实测数据支撑的问题

这个观察有确凿的技术解释。GitHub 上的 issue 记录了一个典型案例：

```
系统上下文配置：
  CLAUDE.md 文件大小：~32KB
  已连接 MCP 服务器：多个

上下文窗口消耗：
  总容量：200K tokens
  系统上下文占用：173K tokens（86.5%）
  剩余可用于实际工作：仅 27K tokens

结果：
  3.5 分钟内触发 6 次上下文压缩（compaction）
  → "压缩死亡螺旋"——系统忙于压缩旧内容，无暇处理新任务
```

### 三层原因

**第一层：上下文窗口是有限资源**

大语言模型的上下文窗口就像一块固定大小的白板。背景文档占据的空间越多，留给实际推理的空间就越少。当你放入大量"以防万一"的参考资料时，模型能用来理解你当前需求和生成回复的空间被严重压缩。

**第二层：注意力稀释效应**

即使上下文没有物理溢出，过多的信息也会分散模型的注意力。Transformer 架构的注意力机制需要在所有输入内容之间计算相关性——无关内容越多，对关键信息的注意力权重就越低。

这类似于你在一个堆满杂物的书桌上找一份特定文件：桌上的东西越多，找到目标文件所需的认知负担越大。

**第三层：VM 性能退化**

Cowork 运行在一个隔离的 Linux 虚拟机中。有用户报告，长期使用后 VM bundle 文件会膨胀至 10GB，导致整个 Claude 桌面应用启动缓慢、UI 卡顿、响应延迟。这意味着性能问题不仅来自 token 层面，还来自底层运行环境。

### 实用建议

- **少即是多**：只放与当前任务直接相关的文档
- **用 .claudeignore 排除干扰**：将无关的大文件、数据集、归档文档排除在 Claude 的视野之外
- **结构化而非堆砌**：与其放 10 个背景文档，不如写一个精练的摘要文件
- **定期清理**：移除不再需要的 context files，保持上下文"轻量"

---

## 4. 可控性的架构差异：为什么 Code "感觉"更可控？

这不是错觉，而是架构决定的。两者在六个关键维度上有本质区别：

| 维度 | Claude Code | Claude Cowork |
|------|------------|---------------|
| **执行可见性** | 终端中每步操作实时可见——你看到每个工具调用的名称、参数、结果 | VM 内部执行，部分细节被抽象——你看到的是"正在处理" |
| **中断能力** | 随时 Ctrl+C 停止，立即重新引导方向 | 多步任务可能需要运行完一个阶段才能干预 |
| **执行架构** | 单线程 `while(tool_use)` 循环——一步一步，可预测 | 异步 VM 执行 + 子智能体并行协调——高效但不透明 |
| **配置显式度** | CLAUDE.md / hooks / skills 都是你手写的文件，完全可审查 | 全局指令 + plugins 配置相对隐式，效果不易追踪 |
| **工具调用** | 每次调用显式展示：`Tool: Grep, Args: {pattern: "auth"}` | 工具调用在后台自动管理，用户看到的是高层摘要 |
| **安全边界** | 沙盒模式透明——你知道哪些操作被限制了 | VZVirtualMachine + bubblewrap + seccomp + 代理网络——安全但不透明 |

用一个类比来总结：

> **Code 像开手动挡车**：你控制每一次换挡，知道引擎在做什么。需要更多操作，但出了问题你能立刻诊断。
>
> **Cowork 像开自动挡车**：你只需踩油门和刹车，系统自动换挡。大多数时候更轻松，但当它做了你不想要的决策时，你很难理解为什么，也不容易干预。

---

## 5. Cowork 也需要 Skills 吗？

### 事实：已经需要，且已经支持

Cowork **已经支持** MCP 服务器和 Skills（通过 Plugins 系统）。技术上，Skills 在 Claude.ai、Claude Code 和 Cowork 之间是通用的。所以问题不是"能不能用"，而是"用不用，以及怎么用"。

### 差异在于"被迫配置"vs"可以跳过"

| | Claude Code | Claude Cowork |
|--|------------|---------------|
| 需要写 CLAUDE.md？ | 几乎必须——否则 Claude 不了解你的项目 | 可以不写——但效果下降 |
| 需要装 skills？ | 处理 Office 文件必须装 | Cowork 原生支持 Office 文件 |
| 需要配 hooks？ | 推荐——确保代码质量 | 不支持 hooks |
| 初始投入 | 30-60 分钟配置 | 0 分钟即可开始 |

Code 用户通过安装 skills 和编写 CLAUDE.md，实际上在做一件关键的事：**编写与 AI 的合作契约**。这个"契约"明确规定了：

- Claude 可以做什么、不能做什么
- 输出应该遵循什么标准
- 遇到不确定情况应该如何处理
- 哪些检查是强制执行的（hooks）

Cowork 用户跳过了这一步。他们直接与一个没有被"训练过合作规范"的 Claude 交互。结果就是——Claude 按自己的理解行事，有时好得出人意料，有时让人摸不着头脑。

### 核心洞察

**Skills 和配置不仅是"功能扩展"，更是用户与 AI 之间的契约机制。**

通过显式配置，用户实际上在做四件事：
1. **定义能力边界**：Claude 能用哪些工具、访问哪些资源
2. **设定质量标准**：输出的格式、风格、精度要求
3. **建立检查点**：哪些操作需要确认、哪些可以自动执行
4. **提供领域知识**：项目背景、术语表、最佳实践

没有这些"契约"，Claude 就只能靠猜测——即使它猜得很有水平，"猜测"本身就是不可控性的来源。

### 推荐做法

像对待 Code 一样认真配置 Cowork：

1. **写全局指令**：在 Cowork 设置中详细定义你的偏好和标准（这相当于 CLAUDE.md）
2. **配置 Plugins**：安装与你工作相关的 MCP 服务器和 Skills
3. **准备精练的 Context Files**：不是堆砌文档，而是准备结构化的项目摘要
4. **建立模板**：对于重复性任务，创建标准模板让 Claude 遵循

---

## 6. 结论：可控性是一个谱系

Cowork 和 Code 不是"好与坏"的关系，而是处于**自主性谱系**的不同位置：

```
          低自主性                                     高自主性
          高可见性                                     低可见性
          高可控性                                     低可控性
     ─────┬───────────────────┬──────────────────────┬────────
          │                   │                      │
      Claude Code          Cowork                Cowork
      (默认状态)           (精心配置后)           (零配置)
          │                   │                      │
     "你指挥，我执行"     "我理解你的框架，      "我按自己的
                           在其中自主工作"         理解来做"
```

**关键认知**：

1. **Cowork 的能力毋庸置疑**——它对 Office 文件的支持、子智能体协调、VM 隔离执行都是 Code 不具备的优势
2. **但能力 ≠ 可控性**——没有配置的 Cowork 就像一个能力很强但没有被交代清楚任务的新同事
3. **两者的最佳实践正在趋同**——都需要投入前期配置来获得可预测的结果
4. **"黑箱"不是 Cowork 的缺陷，而是 trade-off**——它用透明度换取了易用性，但你可以通过配置把部分透明度"赢回来"

最终建议：

- **简单任务**：Cowork 零配置即可胜任（生成文档、数据分析、信息整理）
- **关键任务**：投入 30 分钟配置 Cowork 的全局指令和 plugins，效果会大幅提升
- **需要完全可控**：使用 Code，接受配置成本，换取执行透明度
- **终极方案**：两者结合——Code 处理需要精确控制的技术任务，Cowork 处理委托型的知识工作

---

## 参考资料

- [Claude Cowork 设置指南：Context Files、Instructions、Plugins（2026）](https://www.the-ai-corner.com/p/claude-cowork-setup-guide)
- [Claude Cowork 教程——DataCamp](https://www.datacamp.com/tutorial/claude-cowork-tutorial)
- [Cowork 安全架构深度解析——claudecn.com](https://claudecn.com/en/blog/claude-cowork-security-architecture/)
- [Cowork 架构深度解析：VM 隔离、MCP 与智能体循环——claudecn.com](https://claudecn.com/en/blog/claude-cowork-architecture/)
- [Claude vs Claude Code vs Cowork 对比——Medium](https://medium.com/@yunusemresalcan/claude-vs-claude-code-vs-cowork-which-one-do-you-actually-need-66d3952a2eb4)
- [Claude Code 与 Cowork 的区别——Forte Labs](https://fortelabs.com/blog/the-difference-between-claude-code-and-cowork/)
- [上下文过载导致压缩死亡螺旋——GitHub Issue #24677](https://github.com/anthropics/claude-code/issues/24677)
- [Cowork 10GB VM bundle 性能退化——GitHub Issue #22543](https://github.com/anthropics/claude-code/issues/22543)
- [扩展 Claude 能力：Skills 与 MCP 服务器——claude.com](https://claude.com/blog/extending-claude-capabilities-with-skills-mcp-servers)
- [Claude Skills vs MCP 技术对比——Intuition Labs](https://intuitionlabs.ai/articles/claude-skills-vs-mcp)
- [Claude Cowork 安全使用指南——Claude 帮助中心](https://support.claude.com/en/articles/13364135-use-cowork-safely)
- [Claude Cowork 实际使用笔记——natesnewsletter](https://natesnewsletter.substack.com/p/claude-cowork-the-10-day-launch-that)
- [Claude Code 智能体循环幕后——PromptLayer](https://blog.promptlayer.com/claude-code-behind-the-scenes-of-the-master-agent-loop/)
- [Claude Code 设置指南：MCP、Hooks、Skills（2026）](https://okhlopkov.com/claude-code-setup-mcp-hooks-skills-2026/)
- [Hacker News: Claude Cowork 初印象讨论](https://news.ycombinator.com/item?id=46612919)
- [Claude Code, Cowork 与 Codex 分析——The Zvi](https://thezvi.substack.com/p/claude-code-claude-cowork-and-codex)
