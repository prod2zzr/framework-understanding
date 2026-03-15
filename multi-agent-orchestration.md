# 从"交给 AI"到"编排多个 AI"：协作与竞争的多智能体范式

---

## 1. 从二元到网络：范式升级

### 上一篇的结论

[收敛即能力](convergence-as-capability.md)确立了一个框架：

> 人类负责收敛（what + why），AI 负责执行（how）。

这是一个**二元模型**——一个人类，一个 AI。

### 进化

但实际使用中，一个更有力的模式浮现了：

> **发散的最终要收敛。收敛之后，交给多个 AI——让它们协作，甚至竞争。**

这不是量的增加，而是范式的升级：

```
二元模型（上一篇）：              网络模型（本篇）：

  人类 ─收敛→ AI ─执行→ 结果      人类 ─收敛→ ┌ AI-1 ─协作─ AI-2 ┐
                                            │ AI-3 ─竞争─ AI-4 │ → 结果
                                            └ AI-5 ─审查─ AI-6 ┘
                                                 ↑
                                           人类裁判最终输出
```

人类的角色从**收敛者**升级为**编排者**：收敛 + 调度 + 裁判。

---

## 2. 协作模式：四种已验证的架构

### 模式总览

| 模式 | 结构 | 代表产品/框架 | 适用场景 |
|------|------|-------------|---------|
| **Orchestrator-Worker** | 主智能体协调专业子智能体 | Claude Agent Teams, LangGraph | 复杂多步任务 |
| **Peer Collaboration** | 对等智能体共享并精炼成果 | CrewAI Collaborative Peer Group | 创意、研究 |
| **Pipeline** | 线性链式传递，每步专精 | CrewAI Sequential, Cursor Agents | 文档生产流 |
| **Debate/Competition** | 多智能体生成竞争方案 | A-HMAD, MAD 架构 | 高价值决策 |

### 模式一：Orchestrator-Worker（编排者-工人）

最常见的模式。一个"指挥"智能体负责分解任务和协调，多个专业智能体各司其职。

**实例：Claude Agent Teams**
```
                  ┌──── Code Agent (重构模块 A)
                  │
Orchestrator ─────┼──── Code Agent (写测试覆盖)
(Opus 4.6)        │
                  ├──── Code Agent (修复 lint 错误)
                  │
                  └──── Code Agent (更新文档)
```

Claude 的实现细节：
- 每个子智能体拥有独立的上下文窗口和系统提示
- Opus 4.6 做编排者，Sonnet 4.6 做执行者
- 子智能体之间可以直接通信（不必经过编排者）
- 相比单智能体，研究评估中性能提升 90.2%
- 45 分钟的串行任务压缩到 10 分钟以内

**适用场景**：任务可以清晰分解为独立子任务、各子任务所需技能不同。

### 模式二：Peer Collaboration（对等协作）

没有明确的"老板"，智能体之间平等交流、互相精炼。

**实例：CrewAI Collaborative Peer Group**
```
Agent-1 (研究员) ──→ 初步发现 ──→ Agent-2 (分析师) ──→ 深入分析
      ↑                                                    │
      └──────────── Agent-3 (整合者) ←─── 综合结论 ←────────┘
```

工作方式：
- 每个智能体输出自己的成果
- 其他智能体可以看到所有人的成果并精炼
- 多轮迭代直到收敛
- CrewAI 中设置 `allow_delegation=True` 即可启用

**适用场景**：探索性任务，没有预定义的"正确答案"，需要多视角碰撞。

### 模式三：Pipeline（流水线）

最简单的多智能体模式——每个智能体完成一个阶段，传递给下一个。

**实例：研究→写作→审查 流水线**
```
Researcher Agent ──→ Writer Agent ──→ Reviewer Agent ──→ 最终输出
(搜索和整理素材)     (撰写初稿)       (检查事实和质量)
```

Cursor 2.0 的并行变体：
- 8 个后台智能体同时操作同一代码库
- 每个智能体通过 Git worktrees 获得隔离的代码副本
- 一个重构、一个修测试、一个打磨 UI——真正的并行
- 互不干扰，最后合并

**适用场景**：有明确阶段划分的工作流，每阶段需要不同专业技能。

### 模式四：Debate/Competition（辩论/竞争）

最有趣也最激进的模式——让智能体互相挑战。详见下一节。

---

## 3. 竞争模式：为什么让 AI 互相挑战

### 核心洞察

> **协作产出效率，竞争产出质量。**

协作模式解决的是"如何更快完成"，竞争模式解决的是"如何做得更好"。

### Multi-Agent Debate（MAD）

```
Round 1:
  Agent-A: "我的答案是 X，理由是..."
  Agent-B: "我的答案是 Y，理由是..."
  Agent-C: "我的答案是 Z，理由是..."

Round 2:
  Agent-A: "看了 B 和 C 的论证，我修正为 X'，因为..."
  Agent-B: "A 的某个推理有漏洞，但 C 的数据支持我的结论..."
  Agent-C: "综合考虑后，我认为 Y 更准确，但需要补充..."

Round 3:
  → 收敛到最佳答案
```

**实测数据**（Adaptive Heterogeneous MAD, A-HMAD）：
- 在数学推理（GSM8K）、常识问答（MMLU）、传记生成等任务上，比单智能体准确率提升 4-6%
- 关键设计：给每个智能体分配**不同角色和专长**，而非简单复制
- 动态辩论路由：每轮自动选择最应参与的智能体，避免无效争论

### Adversarial Review（对抗审查）

```
Creator Agent ──→ 生成方案 ──→ Critic Agent ──→ 找出漏洞
      ↑                                           │
      └──── 修订后重新提交 ←─── 详细反驳报告 ←─────┘
```

一个智能体专门负责"找茬"——这比让同一个智能体"请检查你的工作"有效得多，因为独立的审查者没有"沉没成本偏差"。

### 代价与权衡

竞争模式并非免费的午餐：

| 模式 | Token 消耗（相对单智能体） | 适用条件 |
|------|:-------------------------:|---------|
| 单次对话 | 1x | 日常任务 |
| 单智能体执行 | 4x | 多步任务 |
| 多智能体协作 | 8-10x | 复杂项目 |
| 多智能体竞争/辩论 | 15x+ | 高价值决策 |

**决策规则**：竞争模式只在**错误的代价很高**时才值得——财务分析、法律文书、架构决策、安全审计。日常文档生成用协作模式即可。

---

## 4. 真实案例：这已经在发生

### Claude Agent Teams（2026.02，Opus 4.6）

最能体现"多智能体协作与竞争"理念的产品实现：

- **规模**：16 个智能体并行工作
- **真实成果**：一个团队生成了 100,000 行的 Rust C 编译器（~2,000 个会话，$20,000 API 成本）
- **人类角色**：通过 tmux 界面实时观察所有智能体，可在任意时刻介入重定向
- **智能体间通信**：不需要全部经过编排者，teammate 之间可直接对话
- **互相挑战**：智能体可以质疑其他智能体的输出

启用方式：
```bash
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### Cursor 2.0 Background Agents

```
┌─────────────────────────────────────────┐
│ 同一代码库，8 个智能体并行               │
│                                         │
│  Agent-1: 重构 auth 模块                │
│  Agent-2: 修复失败的测试                 │
│  Agent-3: 优化数据库查询                 │
│  Agent-4: 更新 API 文档                 │
│  Agent-5: 迁移到新的依赖版本             │
│  Agent-6: 添加错误处理                   │
│  Agent-7: 清理技术债                    │
│  Agent-8: 打磨 UI 组件                  │
│                                         │
│  隔离机制：Git worktrees / 远程机器      │
│  合并策略：各自提交 PR，人类审查合并      │
└─────────────────────────────────────────┘
```

### 企业多智能体案例

| 领域 | 智能体数 | 效果 |
|------|:-------:|------|
| **保险理赔** | 7 | 处理时间从数天缩短到数小时（-80%） |
| | | 智能体：规划、网络调查、保障范围、天气核实、欺诈检测、赔付计算、审计 |
| **物流供应链** | 多个 | 交付速度 +34%，人工干预 -70%，准时率 82%→96% |
| **亚马逊 MaRGen** | 4 | Researcher + Reviewer + Writer + Retriever 协作的数据分析 |

### 开源替代：Eigent（CAMEL-AI）

- 本地部署的多智能体协作框架
- 支持 Ollama + 本地模型，零外传
- 多个专业智能体（浏览、文档处理、邮件起草）+ 编排者监督
- 对于预算有限或数据敏感的场景，是 Agent Teams 的替代选择

---

## 5. "人类作为编排者"的具体工作

### 角色进化路径

研究者追踪了一条清晰的角色演变：

```
2020: 程序员     — 亲手写每一行代码
2023: 管理者     — 指导 AI 写代码，审查结果
2025: 指挥家     — 协调一个 AI 完成复杂任务
2026: 编排者     — 协调多个 AI 协作和竞争，裁判最终输出
```

### 编排者的三项核心能力

| 能力 | 对应前文概念 | 具体工作 |
|------|------------|---------|
| **上下文收敛** | 已有（见第 7 篇） | 决定喂给智能体群什么信息——CLAUDE.md、context files |
| **任务编排** | 新增 | 选择协作模式（pipeline? debate?），分配角色，设定约束 |
| **结果裁判** | 新增 | 当多个智能体给出不同方案，做最终的价值判断 |

### 编排 = 更高阶的收敛

为什么说编排本质上还是"收敛"？

```
上下文收敛:  从无限信息中选出相关子集      → 减少输入空间
任务编排:    从无限可能的分工方式中选出最优  → 减少执行空间
结果裁判:    从多个竞争输出中选出最好的      → 减少输出空间
```

**每一步都是从发散到收敛。** 编排者的工作，本质上就是在更多维度上做收敛。

---

## 6. 41-87% 失败率的教训：编排比执行更难

### 残酷的数据

多智能体系统在生产环境中的失败率惊人：

```
多智能体系统生产失败率: 41-87%

失败原因分布:
├── 协调/规范问题    79%  ← 不是智能体太弱，是编排太差
├── 技术集成问题     12%
└── 其他            9%
```

**79% 的失败与模型能力无关**——完全是协调问题。这是对"模型能力不是唯一决定因素"的最有力证据。

### 生产中实际使用的协调机制

| 机制 | 采用率 | 原理 |
|------|:------:|------|
| **合同网协议** | 47% | 任务发布 → 智能体竞标 → 选择最佳执行者 |
| **市场化方法** | 29% | 智能体根据资源和能力进行交易/协商 |
| **分布式约束优化** | 18% | 多智能体在约束条件下寻找全局最优解 |
| **其他** | 6% | 混合策略 |

### 核心教训

> **多智能体系统的瓶颈不是智能体太弱，而是编排太差。**

这再次印证了本系列的统一论点：**人类的收敛/编排角色是整个系统的瓶颈和杠杆点。** 投入在提升编排能力上的每一分钟，都比等待模型变强更有价值。

---

## 7. 协议层：让多智能体协作成为可能的基础设施

### 双协议体系

```
                    人类（编排者）
                        │
              ┌─────────┴─────────┐
              ↓                   ↓
         A2A 协议              MCP 协议
    (智能体 ↔ 智能体)      (智能体 ↔ 工具)
              │                   │
    ┌─────────┼─────────┐   ┌────┼────┐
    ↓         ↓         ↓   ↓    ↓    ↓
  Agent-1  Agent-2  Agent-3  DB  API  Files
```

**MCP（Model Context Protocol）**
- 状态：事实标准，已进入 Linux Foundation
- 作用：标准化智能体与外部工具/数据源的连接
- 2026 路线图：传输可扩展性、企业审计、SSO 认证

**A2A（Agent-to-Agent Protocol）**
- 状态：Google 2025 年 4 月发起，150+ 组织支持，已进入 Linux Foundation
- 作用：标准化智能体之间的通信——能力广播（Agent Cards）、安全信息交换、多模态支持
- 与 MCP 互补：MCP 解决"智能体如何使用工具"，A2A 解决"智能体如何对话"

### 共享记忆架构

多智能体协作的关键基础设施——不是每个智能体都从零开始：

```
记忆层级：

短期记忆（会话内）
├── 单个智能体的工作上下文
└── 通过 A2A 共享给其他智能体的中间结果

长期记忆（跨会话）
├── 项目知识库（CLAUDE.md, context files）
├── 向量数据库（语义搜索历史经验）
└── 结构化记录（决策日志、质量指标）

访问控制
├── 私有记忆（仅该智能体可见）
└── 共享记忆（按需分发给特定智能体，支持非对称、时变的访问权限）
```

---

## 8. 更新后的完整图景

整合本系列所有发现，更新统一模型：

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│                    人类：编排者（收敛者）                         │
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│   │ 信息收敛      │  │ 任务编排      │  │ 结果裁判      │         │
│   │ "什么重要？"  │  │ "怎么分工？"  │  │ "哪个更好？"  │         │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│          │                 │                  ↑                 │
│          ↓                 ↓                  │                 │
│   ┌──────────────────────────────────────────────────┐         │
│   │              共享配置层 / 协议层                    │         │
│   │  CLAUDE.md · context/ · .mcp.json · A2A · MCP    │         │
│   └──────────────────────┬───────────────────────────┘         │
│                          │                                     │
│          ┌───────────────┼───────────────┐                     │
│          ↓               ↓               ↓                     │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│   │ 协作智能体群 │  │ 并行执行    │  │ 竞争智能体群 │              │
│   │            │  │            │  │            │              │
│   │ Code       │  │ Agent-1    │  │ 方案 A     │              │
│   │ Cowork     │  │ Agent-2    │  │ 方案 B     │              │
│   │ Cursor     │  │ Agent-3    │  │ 方案 C     │              │
│   │ 专业Agents  │  │ ...        │  │ (互相挑战)  │              │
│   └────────────┘  └────────────┘  └─────┬──────┘              │
│                                         │                     │
│                                    竞争输出                    │
│                                    → 返回人类裁判               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**人类始终是起点和终点** —— 定义方向（收敛输入），裁判结果（收敛输出）。中间的一切——协作、竞争、并行执行——交给多个 AI。

### 与上一篇的递进关系

| 维度 | 第 7 篇（收敛即能力） | 第 8 篇（多智能体编排） |
|------|---------------------|----------------------|
| 人-AI 关系 | 一对一 | 一对多 |
| 人类角色 | 收敛者 | 编排者（收敛 + 调度 + 裁判） |
| AI 角色 | 单一执行者 | 协作群 + 竞争群 |
| 上下文流向 | 人→AI→结果 | 人→AI群⇄AI群→人→最终结果 |
| 核心瓶颈 | 收敛速度 × 收敛质量 | 编排策略的质量（含协调失败风险） |

---

## 9. 对"发散→收敛→多 AI"工作流的实操建议

### 日常工作中的应用

```
Step 1: 发散（用 AI 辅助，不做判断）
        "搜索所有相关资料"
        "列出所有可能的方案"
        "分析所有潜在风险"
        → 用一个 AI 做发散性搜索和生成

Step 2: 收敛（人类核心工作）
        "这 50 条中，这 5 条最相关"
        "这 10 个方案中，深入探索这 3 个"
        "这些风险中，这 2 个最关键"
        → 人类做判断，砍掉噪音

Step 3: 编排（分配给多个 AI）
        方案 A → Agent-1 深入展开
        方案 B → Agent-2 深入展开
        方案 C → Agent-3 深入展开
        → 并行执行，互不干扰

Step 4: 竞争（可选，高价值场景）
        Agent-4 审查 Agent-1 的方案
        Agent-5 审查 Agent-2 的方案
        → 对抗式审查，暴露盲点

Step 5: 裁判（人类最终收敛）
        "综合所有输出和审查意见，方案 B 最优，但需要采纳 Agent-4 对方案 A 的一个改进建议"
        → 人类做最终的价值判断
```

### 工具选择建议

| 阶段 | 推荐工具 | 原因 |
|------|---------|------|
| 发散 | 任意单个 AI | 发散阶段不需要精确控制 |
| 收敛 | 人类 + Claude Code | Code 的白盒透明度帮助审查和筛选 |
| 编排（协作） | Claude Agent Teams / Cursor | 并行执行，共享配置 |
| 编排（竞争） | CrewAI / LangGraph | 辩论架构支持更成熟 |
| 裁判 | 人类 | 不可替代的价值判断 |

---

## 系列文档索引

| # | 文档 | 核心问题 |
|---|------|---------|
| 1 | [claude-code-deep-dive.md](claude-code-deep-dive.md) | Code 的技术架构如何工作？ |
| 2 | [cli-vs-ide-comparison.md](cli-vs-ide-comparison.md) | CLI 和 IDE 模式的本质差异是什么？ |
| 3 | [workspace-file-handling.md](workspace-file-handling.md) | 不同工具如何处理项目文件？ |
| 4 | [cowork-controllability-paradox.md](cowork-controllability-paradox.md) | 为什么 Cowork 给越精确的指令效果越差？ |
| 5 | [code-as-cowork-setup-tool.md](code-as-cowork-setup-tool.md) | 如何用 Code 为 Cowork 构建上下文架构？ |
| 6 | [post-model-competition-landscape.md](post-model-competition-landscape.md) | 模型能力趋同后，什么决定竞争胜负？ |
| 7 | [convergence-as-capability.md](convergence-as-capability.md) | 人类在 AI 时代的不可替代角色是什么？ |
| 8 | [multi-agent-orchestration.md](multi-agent-orchestration.md)（本文） | 如何编排多个 AI 协作与竞争？ |
| 9 | [nezha-mode.md](nezha-mode.md) | 如何实现"一键发送"的端到端工作流？ |

**系列统一论点**：从单个工具的架构 → 工具间对比 → 竞争格局 → 人类角色 → 多智能体编排 → 端到端实操。所有分析收敛到一个结论：**人类的收敛判断——无论是为单个 AI 准备上下文，还是为多个 AI 编排协作与竞争——是整个系统的瓶颈和杠杆点。**

---

## 参考资料

### 多智能体框架
- [LangGraph 多智能体编排：框架完整指南（2025）](https://latenode.com/blog/ai-frameworks-technical-infrastructure/langgraph-multi-agent-orchestration/)
- [LangChain：何时以及如何构建多智能体系统](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/)
- [CrewAI 协作文档](https://docs.crewai.com/en/concepts/collaboration)
- [CrewAI 指南：构建多智能体 AI 团队](https://mem0.ai/blog/crewai-guide-multi-agent-ai-teams)
- [Microsoft AutoGen → Agent Framework 演进](https://visualstudiomagazine.com/articles/2025/10/01/semantic-kernel-autogen--open-source-microsoft-agent-framework.aspx)
- [Claude Code 子智能体文档](https://code.claude.com/docs/en/sub-agents)

### 智能体协作与竞争
- [Anthropic：我们如何构建多智能体研究系统](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Claude Agent Teams 详解（2026 指南）](https://www.turingcollege.com/blog/claude-agent-teams-explained)
- [Multi-LLM-Agents Debate——性能、效率与扩展挑战](https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/)
- [自适应异质多智能体辩论（A-HMAD）](https://link.springer.com/article/10.1007/s44443-025-00353-3)
- [民主式多智能体 AI 的辩论共识模式](https://medium.com/@edoardo.schepis/patterns-for-democratic-multi-agent-ai-debate-based-consensus-part-1-8ef80557ff8a)
- [多智能体强化学习的做市竞争](https://arxiv.org/html/2510.25929v1)

### 人类作为编排者
- [编排人机团队：管理者智能体作为统一研究挑战（ACM 2025）](https://dl.acm.org/doi/10.1145/3772429.3772439)
- [从指挥家到编排者：Agentic Coding 的未来](https://addyo.substack.com/p/conductors-to-orchestrators-the-future)
- [从编码者到编排者：AI 时代的软件工程未来](https://humanwhocodes.com/blog/2026/01/coder-orchestrator-future-software-engineering/)
- [Deloitte：通过 AI 智能体编排释放指数级价值](https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/ai-agent-orchestration.html)

### 协议与标准
- [A2A 协议：智能体间通信新时代（Google）](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [Linux Foundation 启动 A2A 协议项目](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents)
- [MCP 2026 路线图](http://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- [MCP 对 2025 年的影响（ThoughtWorks）](https://www.thoughtworks.com/en-us/insights/blog/generative-ai/model-context-protocol-mcp-impact-2025)

### 共享记忆与上下文
- [AI 智能体的记忆：上下文工程的新范式（The New Stack）](https://thenewstack.io/memory-for-ai-agents-a-new-paradigm-of-context-engineering/)
- [LangGraph + MongoDB 驱动智能体长期记忆](https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph)
- [协作记忆：LLM 智能体的多用户动态访问控制](https://arxiv.org/html/2505.18279v1)
- [从计算机架构视角看多智能体记忆](https://arxiv.org/html/2603.10062)

### 真实案例与实现
- [Claude Opus 4.6 Agent Teams：并行 AI 编码智能体教程（2026）](https://www.nxcode.io/resources/news/claude-agent-teams-parallel-ai-development-guide-2026)
- [Anthropic 发布 Opus 4.6 及 Agent Teams——TechCrunch](https://techcrunch.com/2026/02/05/anthropic-releases-opus-4-6-with-new-agent-teams/)
- [Cursor 2.0：更快的 AI 编码和多智能体工作流](https://devops.com/cursor-2-0-brings-faster-ai-coding-and-multi-agent-workflows/)
- [10 个 AI 智能体实际应用案例（2025）](https://www.xcubelabs.com/blog/10-real-world-examples-of-ai-agents-in-2025/)
- [Eigent：开源桌面多智能体框架](https://github.com/eigent-ai/eigent)
- [Gartner：到 2026 年 40% 的企业应用将内置任务级 AI 智能体](https://www.gartner.com/en/newsroom/press-releases/2025-08-26-gartner-predicts-40-percent-of-enterprise-apps-will-feature-task-specific-ai-agents-by-2026-up-from-less-than-5-percent-in-2025)

### 评估与基准
- [MultiAgentBench：LLM 智能体协作与竞争评估（ACL 2025）](https://aclanthology.org/2025.acl-long.421/)
- [AAAI 2026 Workshop：推进基于 LLM 的多智能体协作](https://multiagents.org/2026/)
