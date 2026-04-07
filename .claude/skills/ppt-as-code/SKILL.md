---
name: ppt-as-code
description: >
  用网页技术生成比 PPT 还惊艳的演示文稿——AI 帮你搭骨架、定风格、找配图。
  当用户说"做个演示"、"做PPT"、"ppt as code"、"网页PPT"、"做个slides"、
  "create presentation"、"make slides"、"web presentation"时触发。
argument-hint: "[演示主题/内容描述，可附 URL 或文件路径]"
allowed-tools: Bash(mkdir *), Bash(tree *), Bash(npx *), Bash(wc *), Bash(open *), Bash(python3 -m http.server*), Read, Write, Edit, Glob, WebFetch, WebSearch
effort: high
---

# PPT as Code — 网页演示文稿生成器

把传统 PPT 的制作流程，变成一套可复用、可迭代、可版本管理的网页演示资产。

**核心理念**：演示文稿 = container + slides + index + controls + motion。
先把状态切换做对，再去管动画。

**Compact 防护**：
- Phase 1 完成后、启动 Sub-Agent 之前，主动执行 `/compact`，焦点为："保留完整的内容大纲、用户风格偏好、复杂度选择，以及待执行的 Phase 3 并行任务清单"
- Sub-Agent 天然拥有独立上下文窗口，不受主 Agent compact 影响

---

## Phase 1/5：需求理解 + 内容规划

### 解析 `$ARGUMENTS`

用户输入的参数：`$ARGUMENTS`

**解析规则**（按优先级）：

1. `--minimal` / `--basic` / `--advanced` → 明确指定复杂度
2. `--reveal` → 使用 reveal.js 框架
3. 以 `http://` 或 `https://` 开头的词 → URL 资料（自动抓取内容）
4. 以 `/` 或 `~/` 开头的词 → 本地文件路径（Read 读取）
5. 自然语言关键词推断场景：
   - 含"会议/汇报/投屏/present" → 投屏场景
   - 含"链接/分享/share/link" → 发链接场景
   - 含"录屏/record/demo" → 录屏场景
6. 其余文本 → 演示主题和描述

**示例**：
- `/ppt-as-code AI Agent 技术架构分享` → 主题=AI Agent, 场景=推断, 零交互
- `/ppt-as-code --reveal --advanced https://docs.example.com` → reveal.js 进阶版, 附带 URL
- `/ppt-as-code 季度业绩汇报 --basic` → 基础版, 投屏场景
- `/ppt-as-code 用 Notion 风格做产品介绍` → 自动从 awesome-design-md 读取 Notion 的 DESIGN.md 作为视觉参考
- `/ppt-as-code` → 无参数，进入交互模式

### 品牌风格引用（与 awesome-design-md 集成）

如果用户指定了品牌风格（如"Notion 风格"、"Stripe 风格"、"Apple 风格"），在 Phase 1 中：
1. 从 `awesome-design-md` skill 的品牌索引中查找对应文件
2. `Read` 对应的 DESIGN.md（如 `.claude/skills/awesome-design-md/references/brands/design/notion.md`）
3. 记录到内容大纲中：`视觉参考：{品牌名} ({文件路径})`
4. 在 Phase 3 中，将 DESIGN.md 的 Color Palette + Typography + Layout 直接作为 Agent A 的输入
5. **跳过"3 套风格方向"流程**——品牌风格已确定，无需再选

### 快速模式（$ARGUMENTS 已含主题 + 可推断配置时）

**跳过交互**，使用默认值：场景=发链接，页数=10页，复杂度=基础版，风格=极简专业。
直接进入 Phase 2。

### 交互模式（$ARGUMENTS 为空或信息不足时）

用 AskUserQuestion 问**一个**综合问题：

> "在开始制作之前，我需要了解几件事：
>
> 1. **演示主题和核心内容**是什么？（简单描述即可）
> 2. **使用场景**？投屏讲解 / 发链接浏览 / 录屏分享
> 3. **页数预期**？5页精简 / 10-15页标准 / 20+页详细
> 4. **技术复杂度**？
>    - 最小版：纯 HTML 单文件，零依赖，适合快速出活
>    - 基础版：含进度条、URL同步、逐步显现，适合正式分享
>    - 进阶版：reveal.js 或原生高级API，适合技术演讲
> 5. **风格偏好**？极简黑白 / 商务专业 / 科技感 / 学术严谨 / 活泼明快
>
> 简单说几句就行，未指定的我会用合理默认值。"

**等待用户回复后继续。**

### 内容提取（若有 URL 或文件）

1. URL → 用 WebFetch 抓取，提取核心内容
2. 本地文件 → 用 Read 读取
3. 将内容整理为演示大纲

### 输出：内容大纲

整理为结构化大纲，格式：

```markdown
## 演示大纲

- 主题：[主题名]
- 场景：[投屏/链接/录屏]
- 页数：[N]
- 复杂度：[最小/基础/进阶]
- 风格：[风格方向]

### 页面规划

1. **封面** — 标题 + 副标题 + 作者
2. **[页标题]** — [2-3个要点]
3. **[页标题]** — [2-3个要点]
...
N. **结尾页** — 总结 / CTA / 联系方式
```

展示大纲请用户确认后继续。

---

## Phase 2/5：架构选择 + 骨架生成

### Step 1：读取模板

根据 Phase 1 确定的复杂度，读取对应模板：
- 最小版 → `Read ${CLAUDE_SKILL_DIR}/templates/minimal.html`
- 基础版 → `Read ${CLAUDE_SKILL_DIR}/templates/basic.html`
- 进阶版 → `Read ${CLAUDE_SKILL_DIR}/templates/advanced.html`

同时读取领域知识：
- `Read ${CLAUDE_SKILL_DIR}/references/article-knowledge.md`
- `Read ${CLAUDE_SKILL_DIR}/references/prompt-templates.md`

### Step 2：创建项目目录

```bash
mkdir -p [project-name]/{assets/images}
```

项目结构（根据复杂度调整）：

**最小版**：
```
[project-name]/
└── index.html          # 单文件，内联 CSS + JS
```

**基础版/进阶版**：
```
[project-name]/
├── index.html          # 主 HTML
├── style.css           # 样式（含视觉系统变量）
├── script.js           # 交互逻辑
└── assets/
    └── images/         # 图片资源
```

### Step 3：填充内容

将 Phase 1 的内容大纲填入模板的 `<section>` 结构中：
- 每页一个 `<section class="slide">`
- 标题用 `<h1>` 或 `<h2>`
- 要点用 `<ul>` 或 `<p>`
- 需要逐步显现的元素加 `class="fragment"`（基础版+）

用 Write 生成 index.html。

**完成后自动继续 Phase 3。**

---

## Phase 3/5：视觉系统设计（并行 Sub-Agent）

> 仅基础版和进阶版执行此阶段。最小版跳过，直接进入 Phase 4。

### 准备工作

1. 读取 `${CLAUDE_SKILL_DIR}/references/agent-prompts.md` 获取 Agent 模板
2. 构建共享上下文（Shared Context）：
   - 演示主题和内容大纲
   - 用户风格偏好
   - 当前页数和内容结构
   - 目标文件路径

### 启动并行 Agent

在**同一轮响应**中同时启动两个 Agent（使用 `run_in_background: true`）：

| Agent | 职责 | 输出 |
|-------|------|------|
| Agent A | 视觉母板设计 | CSS 变量 + 组件样式 |
| Agent B | 配图研究 | 每页配图建议 + 搜图关键词 |

### 收敛

两个 Agent 返回后：
1. 将 Agent A 的 CSS 视觉系统写入 `style.css`（或内联到 HTML）
2. 将 Agent B 的配图建议整理为注释嵌入 HTML 对应位置
3. 如果 Agent B 找到了可用的免费图片 URL，直接插入

---

## Phase 4/5：动效与交互打磨

根据复杂度等级，读取 `references/prompt-templates.md` 中对应的 prompt 模板，逐项补充能力。

### 最小版清单

- [x] CSS `transform: translateX()` + `transition` 分页动画
- [x] 键盘左右箭头切页
- [x] 上一页/下一页按钮
- [x] 基础的 slide 计数器（当前页/总页数）

### 基础版清单（在最小版基础上）

- [ ] 顶部进度条（宽度 = currentIndex / totalSlides * 100%）
- [ ] 底部分页圆点（点击可跳转）
- [ ] URL 同步（`history.pushState` + `popstate` 监听）
- [ ] Fragment 逐步显现（`.fragment` 类 + 按键控制）
- [ ] 媒体预加载（相邻页的图片 `<link rel="preload">`）
- [ ] 移动端适配（viewport meta + 触摸滑动 + 响应式字体）

### 进阶版清单（在基础版基础上）

选择以下**一种**路线：

**路线 A：reveal.js**
- [ ] CDN 引入 reveal.js + 插件
- [ ] Markdown slide 支持
- [ ] Auto-Animate 相邻页补间
- [ ] Speaker Notes 配置
- [ ] 主题定制（覆盖 reveal.js 默认主题）

**路线 B：原生高级 API**
- [ ] scroll-snap 滚动吸附（适合叙事型）
- [ ] WAAPI 精准动画编排
- [ ] View Transition API 镜头切换感
- [ ] GSAP 时间线编排（可选）

### 动效节奏原则

参考 `references/article-knowledge.md` 中的节奏规则：
- 换页时做**一个大动作**（整页滑入/淡入）
- 页内只让**1-2个关键元素**有节奏动作（标题先压进来→数字后接→图片最后补上）
- 其他元素**保持克制**，不要全部都动

用 Edit 逐步修改 index.html / style.css / script.js。

---

## Phase 5/5：验证 + 交付

### 自动验证

运行 `bash ${CLAUDE_SKILL_DIR}/scripts/verify.sh [project-path]`

脚本检查：
- index.html 存在且包含 `<section>` 标签
- slide 数量与规划页数一致
- CSS 中定义了 `--color-*` / `--font-*` / `--space-*` 变量（基础版+）
- 键盘事件监听存在
- 若为 reveal.js，CDN 引用格式正确
- 无 broken 的本地资源引用

### 本地预览

```bash
cd [project-path] && python3 -m http.server 8080
```

告知用户在浏览器打开 `http://localhost:8080` 预览。

### 输出交付清单

```markdown
## [主题名] 演示文稿已就绪

[复杂度] | [N] 页 | `[project-path]/`

### 文件清单
- index.html — 主演示文件
- style.css — 视觉系统（基础版+）
- script.js — 交互逻辑（基础版+）
- assets/images/ — 图片资源

### 使用方式
- 本地预览：`python3 -m http.server 8080`，打开 http://localhost:8080
- 键盘操作：← → 翻页，Space 推进 fragment
- 直接分享：部署到任意静态托管（GitHub Pages、Vercel、Netlify）

### 后续优化建议
- [ ] 替换占位图片为实际配图
- [ ] 调整动效节奏和时长
- [ ] 添加 speaker notes（进阶版）
- [ ] 部署到线上获取分享链接
```

---

## 错误处理

- **WebFetch 失败**：跳过 URL 内容，在大纲中标注"待补充"
- **模板文件读取失败**：降级为内联生成，不依赖模板
- **Agent 超时**：报告哪个 Agent 失败，串行执行该 Agent 的任务
- **reveal.js CDN 不可用**：降级为原生实现（basic 模板）
- **用户无参数且不回复**：使用全默认值（10页基础版，极简专业风格）

---

## 与传统方案的区别

| 维度 | 传统 PPT | PPT as Code |
|------|:-------:|:-----------:|
| 格式 | .pptx 二进制 | HTML/CSS/JS 纯文本 |
| 版本管理 | 手动存副本 | Git 追踪每次修改 |
| 分享方式 | 发文件/上传平台 | 发链接 |
| 主题切换 | 模板绑定 | CSS 变量一键换 |
| 动画能力 | 预设列表 | CSS/JS 无限制 |
| 协作编辑 | 专用软件 | 任意文本编辑器 |
| AI 辅助 | 受格式限制 | 代码生成，精确可控 |
