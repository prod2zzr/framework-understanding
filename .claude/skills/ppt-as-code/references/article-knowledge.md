# PPT as Code — 领域知识库

本文件是从「PPT as Code」方法论中提炼的核心知识，供 Agent 在生成演示文稿时参考。

---

## 一、五层模型

任何网页演示系统，本质上由五层组成：

| 层 | 名称 | 职责 | 技术实现 |
|----|------|------|---------|
| 1 | container | 演示容器/舞台 | `<div class="presentation">` 全屏容器 |
| 2 | slides | 每一页内容 | `<section class="slide">` 多个页面 |
| 3 | index | 当前页索引 | `let currentIndex = 0` 状态变量 |
| 4 | controls | 控制方式 | 按钮、键盘、分页器、URL、触摸 |
| 5 | motion | 切换动效 | CSS transition / WAAPI / View Transition |

**关键认知**：动画只是最后一层。真正的底层是**状态切换**。
不要把它理解成"轮播图"。传统 jQuery slideshow 思路是做 banner，不是做演示系统。

---

## 二、基础五能力

在最小版本跑通后，补齐这五个能力才算一套能讲的演示系统：

### 1. 进度条和分页圆点

- 作用：让观众知道"讲到哪了"
- 进度条：顶部横条，宽度 = `currentIndex / totalSlides * 100%`
- 分页圆点：底部圆点列表，当前页高亮，点击可跳转

### 2. URL 同步

- 作用：刷新后回到当前页，可单独分享某一页
- 技术：`history.pushState` + `popstate` 事件
- URL 格式：`?slide=5` 或 `#/5`

### 3. Fragment（页内逐步显现）

- 作用：控制叙述节奏，观众跟着讲者的节拍走
- 技术：给元素加 `.fragment` 类，按键时依次添加 `.visible`
- 逻辑：同一页内，先推进所有 fragment，再翻到下一页

### 4. 媒体预加载

- 作用：防止大图/视频造成切页卡顿
- 技术：`<link rel="preload" as="image" href="...">` 预加载相邻页资源
- 策略：预加载当前页 ±1 页的媒体资源

### 5. 移动端适配

- 桌面端：保持 16:9 宽高比
- 手机端：9:16 或允许内容重排
- 必须项：`<meta name="viewport">` + 触摸滑动支持 + 响应式字体

---

## 三、进阶四技术

### 1. CSS Scroll Snap

- **适合**：一屏一屏往下滚的叙事型长页面、观众自己浏览的链接
- **不适合**：需要精准按键控制、需要 fragment 推进、页面高度差异大
- 实现：容器 `scroll-snap-type: y mandatory`，子元素 `scroll-snap-align: start`

### 2. WAAPI（Web Animations API）

- **适合**：需要 JS 精准控场——动态改时长、等动画完再推进、多元素同步
- 优势：比 CSS transition 更可控，原生 API 无需库
- 用法：`element.animate(keyframes, options)` 返回 Animation 对象

### 3. View Transition API

- **适合**：旧视图→新视图的"镜头感"过渡
- **注意**：不是替代整套 slide 系统的，状态逻辑没理顺先不要上
- 用法：`document.startViewTransition(() => { /* 更新DOM */ })`

### 4. reveal.js

- **适合**：不想自己造轮子，需要完整演示框架
- 核心能力：
  - Fragments：页内逐步显现
  - Auto-Animate：相邻两页自动补间动画
  - Markdown：直接用 Markdown 写 slide
  - Speaker Notes：演讲者备注
  - 主题系统：内置多套主题 + 自定义
  - 插件生态：代码高亮、数学公式、搜索等

---

## 四、视觉系统四件事

做网页 PPT 显得丑，通常不是因为不会写 CSS，而是没有先定死一套视觉系统。

### 1. 字体系统

- 标题：用有 personality 的 display font（如 Playfair Display、Noto Serif SC）
- 正文：用耐读的 text font（如 Inter、Noto Sans SC）
- 数字/页码：保持统一字宽或统一气质
- 推荐：Google Fonts CSS2 API 的 variable fonts，一套字体拉开层级
- **反模式**：默认系统字体、随手套 display font、标题正文互相打架

### 2. 颜色系统

用 CSS 变量定义：
```css
:root {
  --color-bg: #0a0a0a;
  --color-surface: #1a1a1a;
  --color-text: #f5f5f5;
  --color-text-secondary: #a0a0a0;
  --color-accent: #4f9cf7;
  --color-accent-hover: #3a8ae5;
}
```

### 3. 间距系统

```css
:root {
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 2rem;
  --space-xl: 4rem;
  --space-2xl: 8rem;
}
```

### 4. 组件系统

统一定义常用组件样式：
- slide 容器（padding、max-width）
- 标题层级（h1/h2/h3 的大小、间距、颜色）
- 列表样式（bullet、间距、动画延迟）
- 代码块样式（背景、圆角、字体）
- 图片容器（圆角、阴影、最大宽度）

---

## 五、动效节奏原则

### 核心规则

- 换页时做**一个大动作**（整页滑入/淡入/缩放）
- 页内只让 **1-2 个关键元素**有节奏动作
- 其他元素**保持克制**
- 风格化 ≠ 满屏动画

### 典型节奏编排

```
[换页] → 整页从右滑入（0.5s ease-out）
  → 标题先压进来（delay: 0.1s）
  → 数字/统计值后接（delay: 0.3s）
  → 图片最后补上（delay: 0.5s）
```

### CSS 够用的场景

- 简单翻页动画
- hover 效果
- 单元素的 fadeIn/slideIn

### 需要 GSAP/WAAPI 的场景

- 多元素按时间线编排
- 动态改变动画时长
- 等一个动画完成再触发下一个
- 数字滚动效果

---

## 六、配图四步法

### Step 1：内容→视觉概念

同一句话可以配很多种图。先拆出方向：
- 具象：浏览器舞台、代码编辑器界面
- 系统图：多张 slide 切换的流程图
- 对照：传统 PPT vs 网页演示的对比
- 隐喻：文件→系统的抽象视觉

### Step 2：视觉概念→搜图包

不要只给一个大词（如"technology presentation"）。一次产出完整搜图包：
- **英文主关键词**：精确描述画面内容
- **替代关键词**：2-3 个同义/近义搜索词
- **应避开的词**：会导致搜到廉价图片的词
- **图片方向**：横版 / 竖版 / 方形
- **色彩倾向**：与演示主色调一致

### Step 3：搜图与筛选

- 优先用免费图库（Unsplash、Pexels）
- AI 帮筛掉不合适的（分辨率太低、风格不搭、有水印）
- 留 2-3 个候选方向

### Step 4：搜不到→出图 prompt

只有在前三步都试过之后，才把最终方向翻译为出图 prompt。
不要一上来就让出图模型直接生成。

---

## 七、反模式警告

| 反模式 | 正确做法 |
|--------|---------|
| 一页一页临场发挥设计 | 先定视觉母板（字体+颜色+间距+组件） |
| 全靠"都动起来" | 只在换页和关键元素下重手 |
| 直接让 AI 写最终版 | 先出 3 套风格方向，选一套再深化 |
| 让 AI 同时改结构+样式+内容 | 只让 AI 重写样式层，不碰结构 |
| 一上来就丢"配图需求"给出图模型 | 先拆概念→搜图包→筛图→最后才出图 |
| 把网页 PPT 当轮播图做 | 理解为状态切换系统，不是 jQuery slideshow |
| 用 `technology presentation` 搜图 | 用完整搜图包（主词+替代+避开+方向+色彩） |
