#!/usr/bin/env bash
# Cross-platform configuration file verification script
# Phase 3 convergence: checks all generated files for compliance
# Usage: bash scripts/verify.sh [project-root]

set -euo pipefail

ROOT="${1:-.}"
PASS=0
FAIL=0
WARN=0

pass() { echo "  PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "  FAIL  $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  WARN  $1"; WARN=$((WARN + 1)); }

echo "=========================================="
echo " Cross-Platform Configuration Verification"
echo "=========================================="
echo ""

# -- 1. CLAUDE.md --------------------------------
echo "-- CLAUDE.md --"
if [ -f "$ROOT/CLAUDE.md" ]; then
  chars=$(wc -c < "$ROOT/CLAUDE.md")
  if [ "$chars" -lt 10000 ]; then
    pass "Exists and within size limit (${chars} chars, max 10,000)"
  else
    fail "File too large (${chars} chars, exceeds 10,000 max)"
  fi
  if [ "$chars" -lt 2000 ]; then
    warn "Content is thin (${chars} chars, recommend 2,000-5,000)"
  fi
  if grep -q '## Compact Instructions' "$ROOT/CLAUDE.md" 2>/dev/null; then
    pass "Contains Compact Instructions section"
  else
    warn "Missing Compact Instructions section"
  fi
  if grep -q '## Agent Guidelines' "$ROOT/CLAUDE.md" 2>/dev/null; then
    warn "CLAUDE.md contains Agent Guidelines (should only be in AGENTS.md)"
  fi
else
  fail "CLAUDE.md does not exist"
fi
echo ""

# -- 2. AGENTS.md --------------------------------
echo "-- AGENTS.md --"
if [ -f "$ROOT/AGENTS.md" ]; then
  chars=$(wc -c < "$ROOT/AGENTS.md")
  if [ "$chars" -lt 10000 ]; then
    pass "Exists and within size limit (${chars} chars, max 10,000)"
  else
    fail "File too large (${chars} chars, exceeds 10,000 max)"
  fi
  if [ "$chars" -lt 2000 ]; then
    warn "Content is thin (${chars} chars, recommend 2,000-5,000)"
  fi
  if grep -q '## Agent Guidelines' "$ROOT/AGENTS.md" 2>/dev/null; then
    pass "Contains Agent Guidelines section"
  else
    warn "Missing Agent Guidelines section"
  fi
  if grep -q '## Compact Instructions' "$ROOT/AGENTS.md" 2>/dev/null; then
    warn "AGENTS.md contains Compact Instructions (should only be in CLAUDE.md)"
  fi
else
  fail "AGENTS.md does not exist"
fi
echo ""

# -- 3. Cross-file consistency ------------------
echo "-- Cross-file Consistency --"
if [ -f "$ROOT/CLAUDE.md" ] && [ -f "$ROOT/AGENTS.md" ]; then
  shared_sections=("Project Overview" "Directory Structure" "Key Terms" "Work Preferences" "Output Standards" "Prohibited Actions")
  for section in "${shared_sections[@]}"; do
    in_claude=$(grep -c "## ${section}" "$ROOT/CLAUDE.md" 2>/dev/null || true)
    in_agents=$(grep -c "## ${section}" "$ROOT/AGENTS.md" 2>/dev/null || true)
    if [ "$in_claude" -ge 1 ] && [ "$in_agents" -ge 1 ]; then
      pass "${section} present in both files"
    elif [ "$in_claude" -ge 1 ] || [ "$in_agents" -ge 1 ]; then
      warn "${section} missing from one file"
    else
      fail "${section} missing from both files"
    fi
  done
else
  warn "Cannot check cross-file consistency (need both CLAUDE.md and AGENTS.md)"
fi
echo ""

# -- 4. .claudeignore ----------------------------
echo "-- .claudeignore --"
if [ -f "$ROOT/.claudeignore" ]; then
  rules=$(grep -cve '^\s*$' -e '^\s*#' "$ROOT/.claudeignore" || true)
  pass "Exists (${rules} effective rules)"
  if grep -qP '^\s+[^#\s]' "$ROOT/.claudeignore" 2>/dev/null; then
    warn "Some rules have leading whitespace that may cause matching issues"
  fi
else
  fail ".claudeignore does not exist"
fi
echo ""

# -- 5. .gitignore -------------------------------
echo "-- .gitignore --"
if [ -f "$ROOT/.gitignore" ]; then
  rules=$(grep -cve '^\s*$' -e '^\s*#' "$ROOT/.gitignore" || true)
  pass "Exists (${rules} effective rules)"
else
  fail ".gitignore does not exist"
fi
echo ""

# -- 6. context/ files --------------------------
echo "-- context/ --"
expected_files=("about-project.md" "standards.md" "domain-knowledge.md")

for f in "${expected_files[@]}"; do
  filepath="$ROOT/context/$f"
  if [ -f "$filepath" ]; then
    words=$(wc -w < "$filepath")
    if [ "$words" -le 1000 ]; then
      pass "$f (${words} words)"
    else
      fail "$f exceeds word limit (${words} words, max 1,000)"
    fi
    if grep -q 'TODO' "$filepath" 2>/dev/null; then
      warn "$f contains TODO markers — needs user follow-up"
    fi
  else
    fail "$f does not exist"
  fi
done
echo ""

# -- 7. Plugin (optional) -----------------------
echo "-- Plugin (optional) --"
if [ -f "$ROOT/.claude-plugin/plugin.json" ]; then
  if python3 -m json.tool "$ROOT/.claude-plugin/plugin.json" > /dev/null 2>&1; then
    pass "plugin.json is valid JSON"
  elif command -v jq > /dev/null 2>&1 && jq . "$ROOT/.claude-plugin/plugin.json" > /dev/null 2>&1; then
    pass "plugin.json is valid JSON (jq verified)"
  else
    fail "plugin.json is not valid JSON"
  fi
else
  echo "  SKIP  No Plugin generated (user chose to skip or did not request)"
fi
echo ""

# -- 8. Skills (optional) -----------------------
echo "-- Skills (optional) --"
skill_checked=false

# Check Claude Code plugin skills
if [ -d "$ROOT/.claude-plugin/skills" ]; then
  for skill in "$ROOT/.claude-plugin/skills"/*.md; do
    [ -f "$skill" ] || continue
    skill_checked=true
    name=$(basename "$skill")
    if head -1 "$skill" | grep -q '^---$'; then
      frontmatter=$(sed -n '1,/^---$/p' "$skill" | tail -n +2)
      has_name=$(echo "$frontmatter" | grep -c '^name:' || true)
      has_desc=$(echo "$frontmatter" | grep -c '^description:' || true)
      if [ "$has_name" -ge 1 ] && [ "$has_desc" -ge 1 ]; then
        pass "$name — frontmatter has name + description"
      else
        fail "$name — frontmatter missing name or description"
      fi
    else
      fail "$name — missing YAML frontmatter"
    fi
  done
fi

# Check Codex CLI skills
if [ -d "$ROOT/.codex/skills" ]; then
  for skill_dir in "$ROOT/.codex/skills"/*/; do
    [ -d "$skill_dir" ] || continue
    skill_checked=true
    name=$(basename "$skill_dir")
    skill_file="$skill_dir/SKILL.md"
    if [ -f "$skill_file" ]; then
      if head -1 "$skill_file" | grep -q '^---$'; then
        pass "$name (Codex) — SKILL.md has frontmatter"
      else
        fail "$name (Codex) — SKILL.md missing frontmatter"
      fi
    else
      fail "$name (Codex) — missing SKILL.md"
    fi
  done
fi

if [ "$skill_checked" = false ]; then
  echo "  SKIP  No Skills generated"
fi
echo ""

# -- Summary ------------------------------------
echo "=========================================="
echo " Result: ${PASS} PASS / ${FAIL} FAIL / ${WARN} WARN"
echo "=========================================="

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "${FAIL} item(s) failed — check FAIL entries above and fix."
  exit 1
else
  echo ""
  echo "All required items passed verification."
  exit 0
fi
