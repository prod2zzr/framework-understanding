# DESIGN.md 格式规范

本文档描述 DESIGN.md 的标准格式，以及如何将其转化为实际的 CSS / 视觉系统。

**格式来源**：Google Stitch 推出的设计系统 Markdown 标准。
**特点**：纯文本 Markdown，LLM 天然理解，无需特殊解析工具。

---

## 标准 9 Section 结构

每个 DESIGN.md 包含以下 9 个 Section，顺序固定：

### Section 1: Visual Theme & Atmosphere

**作用**：用自然语言描述品牌的整体视觉气质。

**典型内容**：
- 品牌视觉哲学（如 Notion 的"像纸一样温暖"、Vercel 的"阴影替代边框"）
- 关键设计特征（如字体压缩、暖灰色调、超薄边框）
- 自定义字体信息
- Key Characteristics 要点列表

**提取用法**：理解品牌调性，指导后续所有设计决策。

### Section 2: Color Palette & Roles

**作用**：完整的色彩系统定义，包含 hex 值和使用场景。

**典型子项**：
- **Primary**：主色（背景、文字、CTA）
- **Brand Secondary**：品牌辅助色
- **Neutral Scale**：灰度色阶（通常 4-6 级）
- **Semantic**：语义色（success/warning/error/info）
- **Interactive**：交互色（link/focus/hover/badge）
- **Shadows & Depth**：阴影色值（通常 rgba 格式，多层叠加）

**提取为 CSS 变量的示例**：

```css
/* 从 Notion 的 DESIGN.md 提取 */
:root {
  --color-bg: #ffffff;
  --color-surface: #f6f5f4;          /* Warm White */
  --color-text: rgba(0,0,0,0.95);    /* Near-Black */
  --color-text-secondary: #615d59;   /* Warm Gray 500 */
  --color-text-muted: #a39e98;       /* Warm Gray 300 */
  --color-accent: #0075de;           /* Notion Blue */
  --color-accent-hover: #005bab;     /* Active Blue */
  --color-border: rgba(0,0,0,0.1);   /* Whisper Border */
}
```

### Section 3: Typography Rules

**作用**：完整的字体层级系统。

**典型内容**：
- **Font Family**：字体族 + fallback chain
- **Hierarchy Table**：层级表，通常包含 10-16 个角色（Role/Size/Weight/LineHeight/LetterSpacing）
- **Principles**：排版原则（如压缩比例、字重体系、行高递减规则）

**提取为 CSS 变量的示例**：

```css
/* 从 Notion 的 Typography Rules 提取 */
:root {
  --font-display: 'NotionInter', 'Inter', system-ui, sans-serif;
  --font-body: 'NotionInter', 'Inter', system-ui, sans-serif;
  --font-size-hero: 64px;     /* weight 700, line-height 1.00, letter-spacing -2.125px */
  --font-size-h1: 48px;       /* weight 700, line-height 1.00, letter-spacing -1.5px */
  --font-size-h2: 26px;       /* weight 700, line-height 1.23, letter-spacing -0.625px */
  --font-size-body: 16px;     /* weight 400, line-height 1.50, letter-spacing normal */
  --font-size-caption: 14px;  /* weight 500, line-height 1.43 */
  --font-size-badge: 12px;    /* weight 600, line-height 1.33, letter-spacing 0.125px */
}
```

### Section 4: Component Stylings

**作用**：常用 UI 组件的完整样式规范。

**典型组件**：
- Buttons（Primary/Secondary/Ghost/Pill Badge）
- Cards & Containers
- Inputs & Forms
- Navigation
- Image Treatment
- Distinctive Components（品牌特色组件）

**用法**：直接参照开发组件，或作为 ppt-as-code 的组件样式参考。

### Section 5: Layout Principles

**作用**：间距、栅格和布局规则。

**典型内容**：
- Base spacing unit（通常 4px 或 8px）
- Spacing scale
- Grid & Container width
- Whitespace philosophy
- Border radius scale

### Section 6: Depth & Elevation

**作用**：阴影和层次系统。

**典型结构**：Level 表（通常 4-5 层）

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat | 无阴影 | 背景、文字块 |
| Whisper | 1px border | 卡片边框 |
| Card | 多层阴影 | 内容卡片 |
| Deep | 深层阴影 | 弹窗、浮层 |
| Focus | outline | 键盘焦点 |

### Section 7: Do's and Don'ts

**作用**：设计规范和禁忌，防止"像但不对"的情况。

### Section 8: Responsive Behavior

**作用**：响应式断点和折叠策略。

**典型内容**：
- Breakpoints table（通常 5-7 个断点）
- Touch targets
- Collapsing strategy（各组件在不同断点的表现）

### Section 9: Agent Prompt Guide

**作用**：AI 快速上手指南——最实用的部分。

**典型内容**：
- **Quick Color Reference**：快速色彩速查表
- **Example Component Prompts**：可直接复制的组件生成 prompt
- **Iteration Guide**：迭代时的注意事项要点

> **快捷用法**：如果只需要快速参考，直接跳到 Section 9。

---

## 与 ppt-as-code 的集成

### 场景：用户说"用 Notion 风格做 PPT"

**在 Phase 1**：
1. 识别品牌名 → 从 awesome-design-md 索引查找路径
2. 记录到内容大纲中：`风格参考：Notion (brands/design/notion.md)`

**在 Phase 3（Agent A — 视觉母板设计）**：
1. Read 对应的 DESIGN.md
2. 从 Section 2 提取 Color Palette → CSS 变量
3. 从 Section 3 提取 Typography → 字体系统
4. 从 Section 5 提取 Layout → 间距系统
5. 从 Section 6 提取 Depth → 阴影系统
6. 从 Section 9 参考 Agent Prompt Guide 微调

**跳过"3 套风格方向"流程**——品牌风格已经确定，无需再选。

### 示例：从 Notion DESIGN.md 生成 CSS 变量

```css
/* 自动从 DESIGN.md 提取并转化 */
:root {
  /* Color Palette (Section 2) */
  --color-bg: #ffffff;
  --color-surface: #f6f5f4;
  --color-text: rgba(0,0,0,0.95);
  --color-text-secondary: #615d59;
  --color-accent: #0075de;
  --color-border: rgba(0,0,0,0.1);

  /* Typography (Section 3) */
  --font-display: 'NotionInter', 'Inter', system-ui, sans-serif;
  --font-body: 'NotionInter', 'Inter', system-ui, sans-serif;
  --font-size-title: clamp(2rem, 5vw, 4rem);
  --font-size-body: 16px;

  /* Spacing (Section 5) */
  --space-unit: 8px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 32px;
  --space-xl: 64px;

  /* Depth (Section 6) */
  --shadow-card: rgba(0,0,0,0.04) 0px 4px 18px,
                 rgba(0,0,0,0.027) 0px 2.025px 7.85px,
                 rgba(0,0,0,0.02) 0px 0.8px 2.93px;
  --radius-sm: 4px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-pill: 9999px;
}
```
