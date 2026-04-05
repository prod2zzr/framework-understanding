#!/usr/bin/env bash
# PPT as Code 演示文稿验证脚本
# Phase 5 验证阶段使用：检查生成的演示文稿是否合规
# 用法：bash verify.sh [项目目录] [预期页数]

set -euo pipefail

ROOT="${1:-.}"
EXPECTED_SLIDES="${2:-0}"
PASS=0
FAIL=0
WARN=0

pass() { echo "  PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL  $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  WARN  $1"; WARN=$((WARN + 1)); }

echo "=========================================="
echo " PPT as Code 演示文稿验证"
echo "=========================================="
echo ""

# ── 1. index.html 存在性 ────────────────────────
echo "── index.html ──"
INDEX="$ROOT/index.html"
if [ -f "$INDEX" ]; then
  chars=$(wc -c < "$INDEX")
  pass "存在 (${chars} 字节)"
else
  fail "index.html 不存在"
  echo ""
  echo "=========================================="
  echo " 结果：${PASS} PASS / ${FAIL} FAIL / ${WARN} WARN"
  echo "=========================================="
  echo ""
  echo "index.html 缺失，无法继续验证。"
  exit 1
fi
echo ""

# ── 2. Slide 数量 ───────────────────────────────
echo "── Slide 数量 ──"

# 检测是否为 reveal.js 版本
IS_REVEAL=false
if grep -q 'reveal\.js\|class="reveal"' "$INDEX" 2>/dev/null; then
  IS_REVEAL=true
fi

if [ "$IS_REVEAL" = true ]; then
  # reveal.js：统计 .slides 下的直接 <section> 子元素
  # 简化统计：计算所有 <section> 标签数（含嵌套）
  slide_count=$(grep -co '<section' "$INDEX" || true)
  # 去掉嵌套的垂直 slide 父容器（粗略估计）
  pass "reveal.js 模式，检测到约 ${slide_count} 个 section 标签"
else
  # 原生模式：统计 class="slide" 的 section
  # 匹配 class="slide" 或 class="slide ..."（含修饰类名）
  slide_count=$(grep -c 'class="slide[ "]' "$INDEX" || true)
  if [ "$slide_count" -eq 0 ]; then
    # 尝试匹配 <section> 标签
    slide_count=$(grep -co '<section' "$INDEX" || true)
  fi
  pass "原生模式，检测到 ${slide_count} 个 slide"
fi

if [ "$EXPECTED_SLIDES" -gt 0 ]; then
  if [ "$slide_count" -ge "$EXPECTED_SLIDES" ]; then
    pass "页数满足预期 (${slide_count} >= ${EXPECTED_SLIDES})"
  else
    warn "页数不足 (${slide_count} < ${EXPECTED_SLIDES})"
  fi
fi
echo ""

# ── 3. CSS 视觉系统变量 ─────────────────────────
echo "── 视觉系统 ──"

# 检查内联或外部 CSS 中的变量
has_color_vars=false
has_font_vars=false
has_space_vars=false

# 检查 index.html 内联样式
if grep -q '\-\-color-' "$INDEX" 2>/dev/null; then has_color_vars=true; fi
if grep -q '\-\-font-' "$INDEX" 2>/dev/null; then has_font_vars=true; fi
if grep -q '\-\-space-\|--r-' "$INDEX" 2>/dev/null; then has_space_vars=true; fi

# 检查外部 style.css
STYLE="$ROOT/style.css"
if [ -f "$STYLE" ]; then
  if grep -q '\-\-color-' "$STYLE" 2>/dev/null; then has_color_vars=true; fi
  if grep -q '\-\-font-' "$STYLE" 2>/dev/null; then has_font_vars=true; fi
  if grep -q '\-\-space-' "$STYLE" 2>/dev/null; then has_space_vars=true; fi
fi

if [ "$has_color_vars" = true ]; then
  pass "颜色变量 (--color-*) 已定义"
else
  warn "未检测到颜色变量 (--color-*)"
fi

if [ "$has_font_vars" = true ]; then
  pass "字体变量 (--font-*) 已定义"
else
  warn "未检测到字体变量 (--font-*)"
fi

if [ "$has_space_vars" = true ]; then
  pass "间距变量 (--space-* 或 --r-*) 已定义"
else
  warn "未检测到间距变量"
fi
echo ""

# ── 4. 交互功能 ─────────────────────────────────
echo "── 交互功能 ──"

if [ "$IS_REVEAL" = true ]; then
  # reveal.js 自带交互，只检查初始化
  if grep -q 'Reveal.initialize' "$INDEX" 2>/dev/null; then
    pass "reveal.js 已初始化"
  else
    fail "reveal.js 未初始化（缺少 Reveal.initialize）"
  fi
else
  # 原生版本：检查键盘事件
  has_keyboard=false
  has_controls=false

  # 检查 index.html 和 script.js
  for file in "$INDEX" "$ROOT/script.js"; do
    [ -f "$file" ] || continue
    if grep -q 'keydown\|keyup\|ArrowRight\|ArrowLeft' "$file" 2>/dev/null; then
      has_keyboard=true
    fi
    if grep -q 'nextSlide\|prevSlide\|goToSlide' "$file" 2>/dev/null; then
      has_controls=true
    fi
  done

  if [ "$has_keyboard" = true ]; then
    pass "键盘事件监听存在"
  else
    fail "未检测到键盘事件监听"
  fi

  if [ "$has_controls" = true ]; then
    pass "切页函数存在"
  else
    fail "未检测到切页函数"
  fi
fi
echo ""

# ── 5. Fragment 支持 ─────────────────────────────
echo "── Fragment ──"
if grep -q 'fragment' "$INDEX" 2>/dev/null; then
  frag_count=$(grep -c 'class="fragment\|class=.*fragment' "$INDEX" || true)
  pass "Fragment 已配置 (${frag_count} 个元素)"
else
  echo "  SKIP  未使用 Fragment（最小版本可不需要）"
fi
echo ""

# ── 6. 资源引用检查 ──────────────────────────────
echo "── 资源引用 ──"

# 检查本地图片引用
local_images=$(grep -oP 'src="(?!https?://)[^"]*\.(png|jpg|jpeg|gif|svg|webp)"' "$INDEX" 2>/dev/null || true)
if [ -n "$local_images" ]; then
  broken=0
  while IFS= read -r match; do
    # 提取路径
    img_path=$(echo "$match" | sed 's/src="//;s/"//')
    full_path="$ROOT/$img_path"
    if [ ! -f "$full_path" ]; then
      warn "本地图片缺失：$img_path"
      ((broken++))
    fi
  done <<< "$local_images"

  if [ "$broken" -eq 0 ]; then
    pass "所有本地图片引用有效"
  fi
else
  echo "  SKIP  无本地图片引用"
fi

# 检查 CDN 引用格式（仅格式检查，不验证可达性）
if [ "$IS_REVEAL" = true ]; then
  if grep -q 'cdn.jsdelivr.net/npm/reveal.js' "$INDEX" 2>/dev/null; then
    pass "reveal.js CDN 引用格式正确"
  else
    warn "reveal.js CDN 引用格式可能有误"
  fi
fi
echo ""

# ── 7. 响应式支持 ────────────────────────────────
echo "── 响应式 ──"
if grep -q 'viewport' "$INDEX" 2>/dev/null; then
  pass "viewport meta 已设置"
else
  warn "缺少 viewport meta（移动端可能显示异常）"
fi

if grep -q '@media\|max-width\|min-width' "$INDEX" 2>/dev/null || \
   ([ -f "$STYLE" ] && grep -q '@media' "$STYLE" 2>/dev/null); then
  pass "响应式媒体查询已配置"
else
  warn "未检测到响应式媒体查询"
fi
echo ""

# ── 8. assets 目录 ──────────────────────────────
echo "── 资源目录 ──"
if [ -d "$ROOT/assets" ]; then
  asset_count=$(find "$ROOT/assets" -type f 2>/dev/null | wc -l)
  pass "assets/ 目录存在 (${asset_count} 个文件)"
else
  echo "  SKIP  无 assets/ 目录（单文件版本不需要）"
fi
echo ""

# ── 汇总 ─────────────────────────────────────────
echo "=========================================="
echo " 结果：${PASS} PASS / ${FAIL} FAIL / ${WARN} WARN"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "存在 ${FAIL} 项失败，请检查上方 FAIL 条目并修正。"
  exit 1
elif [ "$WARN" -gt 0 ]; then
  echo ""
  echo "所有必选项通过，但有 ${WARN} 项建议优化。"
  exit 0
else
  echo ""
  echo "所有检查项通过！"
  exit 0
fi
