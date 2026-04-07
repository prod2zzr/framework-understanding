#!/usr/bin/env bash
# Awesome DESIGN.md 验证脚本
# 检查所有品牌 DESIGN.md 文件的完整性和格式一致性
# 用法：bash verify.sh [skill根目录]

set -euo pipefail

ROOT="${1:-.}"
BRANDS_DIR="$ROOT/references/brands"
PASS=0
FAIL=0
WARN=0

pass() { echo "  PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL  $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  WARN  $1"; WARN=$((WARN + 1)); }

echo "=========================================="
echo " Awesome DESIGN.md 验证"
echo "=========================================="
echo ""

# ── 1. SKILL.md ──────────────────────────────────
echo "── SKILL.md ──"
if [ -f "$ROOT/SKILL.md" ]; then
  if head -1 "$ROOT/SKILL.md" | grep -q '^---$'; then
    frontmatter=$(sed -n '1,/^---$/p' "$ROOT/SKILL.md" | tail -n +2)
    has_name=$(echo "$frontmatter" | grep -c '^name:' || true)
    has_desc=$(echo "$frontmatter" | grep -c '^description:' || true)
    if [ "$has_name" -ge 1 ] && [ "$has_desc" -ge 1 ]; then
      pass "SKILL.md frontmatter 包含 name + description"
    else
      fail "SKILL.md frontmatter 缺少 name 或 description"
    fi
  else
    fail "SKILL.md 缺少 YAML frontmatter"
  fi
else
  fail "SKILL.md 不存在"
fi
echo ""

# ── 2. 品牌目录结构 ──────────────────────────────
echo "── 品牌目录 ──"
expected_categories=("ai" "devtools" "infra" "design" "fintech" "enterprise" "automotive")
for cat in "${expected_categories[@]}"; do
  catdir="$BRANDS_DIR/$cat"
  if [ -d "$catdir" ]; then
    count=$(find "$catdir" -name "*.md" -type f | wc -l)
    if [ "$count" -gt 0 ]; then
      pass "$cat/ — ${count} 个品牌文件"
    else
      fail "$cat/ 目录存在但无 .md 文件"
    fi
  else
    fail "$cat/ 目录不存在"
  fi
done
echo ""

# ── 3. 品牌总数 ──────────────────────────────────
echo "── 品牌总数 ──"
total=$(find "$BRANDS_DIR" -name "*.md" -type f 2>/dev/null | wc -l)
if [ "$total" -ge 50 ]; then
  pass "共 ${total} 个品牌文件（目标 58）"
elif [ "$total" -ge 40 ]; then
  warn "共 ${total} 个品牌文件（目标 58，部分缺失）"
else
  fail "仅 ${total} 个品牌文件（目标 58）"
fi
echo ""

# ── 4. 格式一致性抽查 ────────────────────────────
echo "── 格式一致性（抽查） ──"

# 标准 section 标题（检查前 7 个关键 section）
required_sections=(
  "Color Palette"
  "Typography"
  "Component"
  "Layout"
  "Depth"
)

sample_count=0
format_ok=0
format_fail=0

while IFS= read -r file; do
  brand=$(basename "$file" .md)
  missing=""

  for section in "${required_sections[@]}"; do
    if ! grep -qi "$section" "$file" 2>/dev/null; then
      missing="$missing [$section]"
    fi
  done

  if [ -z "$missing" ]; then
    format_ok=$((format_ok + 1))
  else
    warn "$brand — 缺少 section:$missing"
    format_fail=$((format_fail + 1))
  fi
  sample_count=$((sample_count + 1))
done < <(find "$BRANDS_DIR" -name "*.md" -type f 2>/dev/null)

if [ "$sample_count" -gt 0 ]; then
  pass "检查了 ${sample_count} 个文件：${format_ok} 个格式完整，${format_fail} 个有缺失"
fi
echo ""

# ── 5. 色值检查 ──────────────────────────────────
echo "── 色值检查 ──"
has_colors=0
no_colors=0

while IFS= read -r file; do
  if grep -qP '#[0-9a-fA-F]{3,8}' "$file" 2>/dev/null; then
    has_colors=$((has_colors + 1))
  else
    brand=$(basename "$file" .md)
    warn "$brand — 未检测到 hex 色值"
    no_colors=$((no_colors + 1))
  fi
done < <(find "$BRANDS_DIR" -name "*.md" -type f 2>/dev/null)

if [ "$has_colors" -gt 0 ]; then
  pass "${has_colors} 个文件包含 hex 色值"
fi
if [ "$no_colors" -gt 0 ]; then
  warn "${no_colors} 个文件未检测到 hex 色值"
fi
echo ""

# ── 6. 字体层级表检查 ────────────────────────────
echo "── 字体层级表 ──"
has_table=0
no_table=0

while IFS= read -r file; do
  # 检查 Typography 附近是否有 markdown 表格（|）
  if grep -A 30 -i "Typography" "$file" 2>/dev/null | grep -q '|.*|.*|'; then
    has_table=$((has_table + 1))
  else
    brand=$(basename "$file" .md)
    no_table=$((no_table + 1))
  fi
done < <(find "$BRANDS_DIR" -name "*.md" -type f 2>/dev/null)

if [ "$has_table" -gt 0 ]; then
  pass "${has_table} 个文件包含字体层级表"
fi
if [ "$no_table" -gt 0 ]; then
  warn "${no_table} 个文件未检测到字体层级表"
fi
echo ""

# ── 7. design-md-format.md ───────────────────────
echo "── 格式规范文档 ──"
if [ -f "$ROOT/references/design-md-format.md" ]; then
  pass "design-md-format.md 存在"
else
  warn "design-md-format.md 不存在"
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
