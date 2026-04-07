---
name: awesome-design-md
version: 1.0.0
source: https://github.com/VoltAgent/awesome-design-md
description: >
  58 个知名品牌的 DESIGN.md 设计系统参考库——AI 可读的视觉规范，覆盖色彩、字体、组件、布局。
  当用户说"用 XX 风格"、"参考 XX 的设计"、"Notion 风格"、"Stripe 风格"、
  "design system"、"DESIGN.md"、"品牌风格参考"时触发。
  被 ppt-as-code、diagram 等其他技能调用时，提供品牌级视觉规范参考。
argument-hint: "[品牌名称] 或 [风格描述]"
allowed-tools: Read, Glob, Grep
effort: low
---

# Awesome DESIGN.md — 品牌设计系统参考库

> 58 个知名品牌的完整视觉设计规范，以 AI 可读的 Markdown 格式呈现。
> 把 DESIGN.md 丢给 AI Agent，说"照这个风格做"，就能得到像素级还原的 UI。

**格式来源**：Google Stitch 推出的 DESIGN.md 标准，用纯文本描述完整的视觉设计系统。
**数据来源**：[VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md)

---

## 使用方式

本 skill 是**参考库**，不是 action workflow。有四种使用模式：

### 模式 1：直接查询品牌风格

用户说"用 Notion 风格"或"参考 Stripe 的设计"：
1. 从下方品牌索引找到品牌名和文件路径
2. `Read ${CLAUDE_SKILL_DIR}/references/brands/{category}/{brand}.md`
3. 提取需要的规范（色彩、字体、组件等）

### 模式 2：风格推荐

用户描述风格但没指定品牌（如"极简温暖"、"科技感暗色"）：
1. 参考下方索引的**风格关键词**列
2. 推荐 2-3 个匹配的品牌
3. 让用户选择后读取对应 DESIGN.md

### 模式 3：跨 Skill 调用（ppt-as-code 集成）

当 `ppt-as-code` Phase 3 需要视觉系统时：
1. 如果用户指定了品牌风格 → 读取对应 DESIGN.md
2. 将 `Color Palette & Roles` + `Typography Rules` + `Component Stylings` 提取为 CSS 变量
3. 作为 Agent A（视觉母板设计）的输入，替代从零生成 3 套方向

### 模式 4：风格混搭

用户说"Stripe 的配色 + Notion 的字体"：
1. 分别读取两个品牌的 DESIGN.md
2. 从各自提取对应部分
3. 合并为统一的视觉系统

---

## 品牌索引

### AI & Machine Learning（12 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| Claude | `brands/ai/claude.md` | 暖色调、学术感、橙棕 accent |
| Cohere | `brands/ai/cohere.md` | 绿色渐变、科技感、暗色 |
| ElevenLabs | `brands/ai/elevenlabs.md` | 深色背景、紫色 accent、未来感 |
| Minimax | `brands/ai/minimax.md` | 蓝色科技、极简 |
| Mistral AI | `brands/ai/mistral-ai.md` | 橙色 accent、暗色、欧洲极简 |
| Ollama | `brands/ai/ollama.md` | 亲切极简、白色背景 |
| OpenCode AI | `brands/ai/opencode-ai.md` | 深色终端感、代码优先 |
| Replicate | `brands/ai/replicate.md` | 极简白、功能导向 |
| RunwayML | `brands/ai/runwayml.md` | 创意视觉、暗色、视频感 |
| Together AI | `brands/ai/together-ai.md` | 渐变色、云服务感 |
| VoltAgent | `brands/ai/voltagent.md` | 紫色 accent、开发者工具 |
| xAI | `brands/ai/x-ai.md` | 极简暗色、高对比 |

### Developer Tools & Platforms（14 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| Cursor | `brands/devtools/cursor.md` | 暗色 IDE、紫蓝渐变 |
| Expo | `brands/devtools/expo.md` | 蓝色专业、React Native |
| Linear | `brands/devtools/linear-app.md` | 紫色、暗色、精致极简 |
| Lovable | `brands/devtools/lovable.md` | 温暖粉紫、亲切 |
| Mintlify | `brands/devtools/mintlify.md` | 绿色、文档优先 |
| PostHog | `brands/devtools/posthog.md` | 蓝色品牌、数据驱动 |
| Raycast | `brands/devtools/raycast.md` | 暗色、彩虹渐变、生产力 |
| Resend | `brands/devtools/resend.md` | 极简白、开发者友好 |
| Sentry | `brands/devtools/sentry.md` | 紫色暗色、错误监控 |
| Supabase | `brands/devtools/supabase.md` | 绿色、暗色背景、数据库 |
| Superhuman | `brands/devtools/superhuman.md` | 暗色、金色 accent、高端 |
| Vercel | `brands/devtools/vercel.md` | 纯黑白、Geist 字体、极简 |
| Warp | `brands/devtools/warp.md` | 暗色终端、渐变色 |
| Zapier | `brands/devtools/zapier.md` | 橙色品牌、自动化感 |

### Infrastructure & Cloud（6 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| ClickHouse | `brands/infra/clickhouse.md` | 黄色 accent、数据库 |
| Composio | `brands/infra/composio.md` | 蓝紫渐变、集成平台 |
| HashiCorp | `brands/infra/hashicorp.md` | 黑白极简、基础设施 |
| MongoDB | `brands/infra/mongodb.md` | 绿色品牌、数据库 |
| Sanity | `brands/infra/sanity.md` | 红色 accent、内容平台 |
| Stripe | `brands/infra/stripe.md` | 紫蓝渐变、精致细节、信任感 |

### Design & Productivity（10 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| Airtable | `brands/design/airtable.md` | 彩色、友好、表格工具 |
| Cal.com | `brands/design/cal.md` | 极简白、日历工具 |
| Clay | `brands/design/clay.md` | 渐变背景、数据工具 |
| Figma | `brands/design/figma.md` | 多彩、创意、设计工具 |
| Framer | `brands/design/framer.md` | 暗色、蓝色 accent、高端 |
| Intercom | `brands/design/intercom.md` | 蓝色品牌、客服工具 |
| Miro | `brands/design/miro.md` | 黄色品牌、协作白板 |
| Notion | `brands/design/notion.md` | 暖灰色、温暖极简、内容优先 |
| Pinterest | `brands/design/pinterest.md` | 红色品牌、瀑布流 |
| Webflow | `brands/design/webflow.md` | 蓝色、专业、无代码 |

### Fintech & Crypto（4 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| Coinbase | `brands/fintech/coinbase.md` | 蓝色、安全感、加密货币 |
| Kraken | `brands/fintech/kraken.md` | 紫色暗色、交易平台 |
| Revolut | `brands/fintech/revolut.md` | 暗色、现代金融 |
| Wise | `brands/fintech/wise.md` | 绿色、友好、跨境支付 |

### Enterprise & Consumer（7 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| Airbnb | `brands/enterprise/airbnb.md` | 珊瑚粉、温暖、旅行 |
| Apple | `brands/enterprise/apple.md` | 极简白、高端、SF Pro |
| IBM | `brands/enterprise/ibm.md` | 蓝色、企业级、专业 |
| NVIDIA | `brands/enterprise/nvidia.md` | 绿色、科技、算力 |
| SpaceX | `brands/enterprise/spacex.md` | 暗色、太空感、未来 |
| Spotify | `brands/enterprise/spotify.md` | 绿色品牌、音乐、活力 |
| Uber | `brands/enterprise/uber.md` | 黑白极简、出行 |

### Automotive（5 个）

| 品牌 | 文件路径 | 风格关键词 |
|------|---------|-----------|
| BMW | `brands/automotive/bmw.md` | 蓝白品牌、德系精致 |
| Ferrari | `brands/automotive/ferrari.md` | 红色、奢华、速度感 |
| Lamborghini | `brands/automotive/lamborghini.md` | 金色暗色、超跑、力量 |
| Renault | `brands/automotive/renault.md` | 黄色品牌、法式设计 |
| Tesla | `brands/automotive/tesla.md` | 极简白、科技、未来感 |

---

## 每个 DESIGN.md 的标准结构

所有品牌的 DESIGN.md 遵循统一的 9 section 结构（Google Stitch 标准）：

| # | Section | 提供什么 | 典型用途 |
|---|---------|---------|---------|
| 1 | Visual Theme & Atmosphere | 整体气质描述、关键视觉特征 | 理解品牌调性 |
| 2 | Color Palette & Roles | hex 色值 + 使用场景（Primary/Semantic/Interactive） | 提取 CSS 变量 |
| 3 | Typography Rules | 字体族 + 层级表（Size/Weight/LineHeight/LetterSpacing） | 字体系统定义 |
| 4 | Component Stylings | 按钮/卡片/输入框/导航等完整样式规范 | 组件开发参考 |
| 5 | Layout Principles | 间距系统、栅格、容器宽度、留白哲学 | 布局规范 |
| 6 | Depth & Elevation | 阴影层级表（flat → card → deep → focus） | 阴影系统 |
| 7 | Do's and Don'ts | 设计规范和禁忌清单 | 质量保证 |
| 8 | Responsive Behavior | 断点表 + 折叠策略 + 触控目标 | 响应式开发 |
| 9 | Agent Prompt Guide | Quick Color Reference + 示例组件 prompt | 快速上手 |

> **最快速的用法**：直接跳到 Section 9（Agent Prompt Guide），里面有 Quick Color Reference 和可复制的组件 prompt。

---

## 格式规范详情

详见 `references/design-md-format.md`。

---

## 风格推荐速查

| 用户说… | 推荐品牌 | 理由 |
|---------|---------|------|
| "极简白" | Vercel, Apple, Cal.com | 黑白为主，留白大方 |
| "暗色科技感" | Linear, SpaceX, Supabase | 深色背景，accent 点缀 |
| "温暖亲切" | Notion, Airbnb, Lovable | 暖灰色调，圆角，友好 |
| "高端精致" | Stripe, Superhuman, Framer | 细节打磨，渐变，阴影层次 |
| "活泼多彩" | Figma, Airtable, Miro | 多色系，友好，协作感 |
| "商务专业" | IBM, HashiCorp, Sentry | 蓝色系，企业级，信任感 |
| "力量速度" | Ferrari, Lamborghini, NVIDIA | 红/金/绿，强烈对比，冲击力 |
