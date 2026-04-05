# PPT as Code — Prompt 模板集

供各阶段使用的 AI prompt 模板。每个模板独立可用，也可组合使用。

---

## 1. 最小版本生成

```
生成一个最小可运行的 HTML 分页演示：

要求：
- 纯单文件 HTML，内联 CSS + JS，零外部依赖
- 每一页是一个 <section class="slide">
- 用 currentIndex 状态变量控制当前页
- 切页用 CSS transform: translateX() + transition 实现
- 支持键盘左右箭头切页
- 支持上一页/下一页按钮
- 全屏容器，页面居中，16:9 比例
- 显示当前页/总页数

内容（共 {N} 页）：
{SLIDE_OUTLINE}

风格：{STYLE_DIRECTION}
```

---

## 2. 进度条 + 分页圆点

```
在已有的 HTML 分页演示上，补充进度指示器：

1. 顶部进度条：
   - 固定在视口顶部
   - 宽度 = currentIndex / (totalSlides - 1) * 100%
   - 高度 3px，颜色用 --color-accent
   - transition: width 0.3s ease

2. 底部分页圆点：
   - 固定在视口底部居中
   - 每页一个圆点（8px 圆形）
   - 当前页圆点高亮（--color-accent）
   - 点击圆点可跳转到对应页
   - 圆点间距 12px

不要改动已有的 slide 内容和切页逻辑，只新增 UI 元素。
```

---

## 3. URL 同步

```
为已有的 HTML 分页演示添加 URL 同步功能：

1. 切页时更新 URL：
   - 使用 history.pushState
   - URL 格式：?slide={index}（从 0 开始）
   - 不要触发页面刷新

2. 页面加载时读取 URL：
   - 解析 URLSearchParams 获取 slide 参数
   - 跳转到对应页（无动画，直接定位）
   - 参数无效时默认第 0 页

3. 浏览器前进/后退：
   - 监听 popstate 事件
   - 根据 URL 参数切换到对应页

不要改动已有的 slide 内容和样式。
```

---

## 4. Fragment 逐步显现

```
为已有的 HTML 分页演示添加 Fragment 功能：

1. 标记方式：
   - 给需要逐步显现的元素加 class="fragment"
   - 默认隐藏（opacity: 0; transform: translateY(20px)）
   - 显现时添加 class="visible"（opacity: 1; transform: none; transition: 0.4s ease）

2. 按键逻辑修改：
   - 按 → 或 Space：
     a. 如果当前页还有未显现的 fragment → 显现下一个 fragment
     b. 如果所有 fragment 都已显现 → 翻到下一页
   - 按 ←：
     a. 如果当前页有已显现的 fragment → 隐藏最后一个 fragment
     b. 如果没有已显现的 fragment → 翻到上一页

3. 翻页时重置：
   - 向前翻页：新页的所有 fragment 初始隐藏
   - 向后翻页：前一页的所有 fragment 初始全部显现

不要改动 slide 的整体布局和切页动画。
```

---

## 5. 媒体预加载

```
为已有的 HTML 分页演示添加媒体预加载：

1. 预加载策略：
   - 当切换到第 N 页时，预加载第 N+1 页和第 N-1 页的图片
   - 使用 <link rel="preload" as="image"> 动态插入 <head>
   - 避免重复预加载已加载的资源

2. 实现方式：
   - 在切页回调中触发
   - 扫描相邻 slide 中的 <img> src 和 CSS background-image
   - 用 Set 记录已预加载的 URL

3. 懒加载配合：
   - 非相邻页的图片使用 loading="lazy"
   - 当前页和相邻页的图片移除 lazy 属性

不要改动已有的切页逻辑和样式。
```

---

## 6. 移动端适配

```
为已有的 HTML 分页演示添加移动端适配：

1. Viewport：
   - <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

2. 触摸支持：
   - 监听 touchstart / touchend 事件
   - 左滑 → 下一页，右滑 → 上一页
   - 滑动距离阈值：50px
   - 防止触摸时的页面滚动（preventDefault）

3. 响应式布局：
   - 桌面端：slide 保持 16:9 比例，居中显示
   - 移动端（max-width: 768px）：
     - slide 铺满整个视口
     - 字体缩小（标题 clamp(1.5rem, 5vw, 3rem)）
     - 间距缩小
     - 隐藏上一页/下一页按钮（触摸替代）
     - 分页圆点缩小

不要改动已有的 slide 内容结构。
```

---

## 7. 视觉母板生成（3 套方向）

```
为以下演示主题生成 3 套差异明显的视觉方向：

主题：{TOPIC}
场景：{SCENE}
受众：{AUDIENCE}

每套方向包含：
1. 风格名称（2-3个词概括）
2. 色彩方案（背景色 + 文字色 + 强调色，给出 hex 值）
3. 字体搭配（标题字体 + 正文字体，从 Google Fonts 选）
4. 整体气质描述（一句话）
5. 适合场景说明

要求：
- 三套方向之间差异要大（不是同一风格的三种变体）
- 每套都要实际可用（不是概念性的）
- 给出具体的 CSS 变量值，不要只说"深色系"

输出格式（每套）：
---
### 方向 A：{风格名称}

气质：{一句话描述}
适合：{场景}

```css
:root {
  --color-bg: #...;
  --color-surface: #...;
  --color-text: #...;
  --color-text-secondary: #...;
  --color-accent: #...;
  --font-display: '...', serif;
  --font-body: '...', sans-serif;
  --font-size-title: clamp(...);
  --font-size-body: clamp(...);
}
```
---
```

---

## 8. 样式重写（只改样式，不碰结构）

```
重写以下 HTML 演示文稿的样式层：

当前 HTML 结构：
{CURRENT_HTML}

选定的视觉方向：
{SELECTED_STYLE}

要求：
1. 只修改 CSS / <style> 部分
2. 不要修改 HTML 结构（不增删标签、不改类名）
3. 不要修改 JavaScript 逻辑
4. 不要修改文案内容
5. 应用视觉方向中定义的所有 CSS 变量
6. 确保字体从 Google Fonts 正确引入
7. 所有颜色都通过 CSS 变量引用，不要硬编码

输出完整的 CSS（可以覆盖原有样式）。
```

---

## 9. 配图概念拆解

```
为以下演示的每一页，拆解配图方向：

演示主题：{TOPIC}
页面列表：
{SLIDE_LIST}

对每一页，输出：
1. 页面核心信息（一句话）
2. 视觉概念方向（2-3个可选方向）
   - 每个方向用一句话描述画面
3. 推荐方向（选一个最合适的）
4. 推荐原因

格式：
---
### 第 N 页：{页标题}

核心信息：{一句话}

视觉方向：
- A：{画面描述}
- B：{画面描述}
- C：{画面描述}

推荐：方向 {X}
原因：{理由}
---
```

---

## 10. 搜图包生成

```
为以下配图需求生成完整的搜图包：

页面：{PAGE_TITLE}
视觉概念：{VISUAL_CONCEPT}
演示整体色调：{COLOR_SCHEME}

输出搜图包：

1. 英文主关键词：{精确描述画面内容的搜索词}
2. 替代关键词：{2-3个同义/近义搜索词}
3. 应避开的词：{会导致搜到廉价/不相关图片的词}
4. 图片方向：横版 16:9 / 竖版 / 方形
5. 色彩倾向：{与演示主色调协调的色彩方向}
6. 建议图库：Unsplash / Pexels / 其他
7. 搜索 URL（直接可点击）：
   - Unsplash: https://unsplash.com/s/photos/{主关键词}
   - Pexels: https://www.pexels.com/search/{主关键词}/
```
