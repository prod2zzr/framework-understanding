#!/usr/bin/env bash
# Cowork 配置文件验证脚本
# Phase 3 收敛阶段使用：检查所有生成文件是否合规
# 用法：bash scripts/verify.sh [项目根目录]

set -euo pipefail

ROOT="${1:-.}"
PASS=0
FAIL=0
WARN=0

pass() { echo "  PASS  $1"; ((PASS++)); }
fail() { echo "  FAIL  $1"; ((FAIL++)); }
warn() { echo "  WARN  $1"; ((WARN++)); }

echo "=========================================="
echo " Cowork 配置验证"
echo "=========================================="
echo ""

# ── 1. CLAUDE.md ──────────────────────────────
echo "── CLAUDE.md ──"
if [ -f "$ROOT/CLAUDE.md" ]; then
  chars=$(wc -c < "$ROOT/CLAUDE.md")
  if [ "$chars" -lt 10000 ]; then
    pass "存在且大小合规 (${chars} 字符, 上限 10,000)"
  else
    fail "文件过大 (${chars} 字符, 超过 10,000 上限)"
  fi
  if [ "$chars" -lt 2000 ]; then
    warn "内容偏少 (${chars} 字符, 建议 2,000-5,000)"
  fi
else
  fail "CLAUDE.md 不存在"
fi
echo ""

# ── 2. .claudeignore ─────────────────────────
echo "── .claudeignore ──"
if [ -f "$ROOT/.claudeignore" ]; then
  rules=$(grep -cve '^\s*$' -e '^\s*#' "$ROOT/.claudeignore" || true)
  pass "存在 (${rules} 条有效规则)"
  # 检查是否有语法问题（空行开头的空格等）
  if grep -qP '^\s+[^#\s]' "$ROOT/.claudeignore" 2>/dev/null; then
    warn "部分规则行首有空格，可能导致匹配失败"
  fi
else
  fail ".claudeignore 不存在"
fi
echo ""

# ── 3. .gitignore ────────────────────────────
echo "── .gitignore ──"
if [ -f "$ROOT/.gitignore" ]; then
  rules=$(grep -cve '^\s*$' -e '^\s*#' "$ROOT/.gitignore" || true)
  pass "存在 (${rules} 条有效规则)"
else
  fail ".gitignore 不存在"
fi
echo ""

# ── 4. context/ 文件 ─────────────────────────
echo "── context/ ──"
expected_files=("about-project.md" "standards.md" "domain-knowledge.md")
context_ok=true

for f in "${expected_files[@]}"; do
  filepath="$ROOT/context/$f"
  if [ -f "$filepath" ]; then
    words=$(wc -w < "$filepath")
    if [ "$words" -le 1000 ]; then
      pass "$f (${words} 字)"
    else
      fail "$f 超过字数限制 (${words} 字, 上限 1,000)"
      context_ok=false
    fi
    # 检查是否有 TODO 标记
    if grep -q 'TODO' "$filepath" 2>/dev/null; then
      warn "$f 包含 TODO 标记，需用户后续补充"
    fi
  else
    fail "$f 不存在"
    context_ok=false
  fi
done
echo ""

# ── 5. plugin.json（条件检查）────────────────
echo "── Plugin（可选）──"
if [ -f "$ROOT/.claude-plugin/plugin.json" ]; then
  if python3 -m json.tool "$ROOT/.claude-plugin/plugin.json" > /dev/null 2>&1; then
    pass "plugin.json 为合法 JSON"
  elif command -v jq > /dev/null 2>&1 && jq . "$ROOT/.claude-plugin/plugin.json" > /dev/null 2>&1; then
    pass "plugin.json 为合法 JSON (jq 验证)"
  else
    fail "plugin.json 不是合法 JSON"
  fi
else
  echo "  SKIP  未生成 Plugin（用户选择跳过或未要求）"
fi
echo ""

# ── 6. Skill 文件 frontmatter（条件检查）─────
echo "── Skills（可选）──"
if [ -d "$ROOT/.claude-plugin/skills" ]; then
  for skill in "$ROOT/.claude-plugin/skills"/*.md; do
    [ -f "$skill" ] || continue
    name=$(basename "$skill")
    # 检查是否有 YAML frontmatter（以 --- 开头和结尾）
    if head -1 "$skill" | grep -q '^---$'; then
      # 检查 frontmatter 中是否包含 name 和 description
      frontmatter=$(sed -n '1,/^---$/p' "$skill" | tail -n +2)
      has_name=$(echo "$frontmatter" | grep -c '^name:' || true)
      has_desc=$(echo "$frontmatter" | grep -c '^description:' || true)
      if [ "$has_name" -ge 1 ] && [ "$has_desc" -ge 1 ]; then
        pass "$name — frontmatter 包含 name + description"
      else
        fail "$name — frontmatter 缺少 name 或 description"
      fi
    else
      fail "$name — 缺少 YAML frontmatter"
    fi
  done
else
  echo "  SKIP  未生成 Skills"
fi
echo ""

# ── 汇总 ─────────────────────────────────────
echo "=========================================="
echo " 结果：${PASS} PASS / ${FAIL} FAIL / ${WARN} WARN"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "存在 ${FAIL} 项失败，请检查上方 FAIL 条目并修正。"
  exit 1
else
  echo ""
  echo "所有必选项通过验证。"
  exit 0
fi
