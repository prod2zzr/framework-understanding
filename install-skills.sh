#!/usr/bin/env bash
# ============================================================
# install-skills.sh — 一键安装 framework-understanding skills
# 用法:
#   curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash
#   curl -sL ... | bash -s -- quickstart               # 只安装指定 skill
#   curl -sL ... | bash -s -- quickstart quick-framework # 安装多个
#   curl -sL ... | bash -s -- --branch <branch-name>   # 指定分支
#   curl -sL ... | bash -s -- --list                    # 列出可用 skills
#   INSTALL_SKILLS_BRANCH=dev curl -sL ... | bash       # 环境变量指定分支
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/prod2zzr/framework-understanding.git"
BRANCH="${INSTALL_SKILLS_BRANCH:-main}"
GLOBAL_SKILLS_DIR="${HOME}/.claude/skills"
TMP_DIR=""

# 可安装的 skills（目录形式）
AVAILABLE_DIR_SKILLS=(quickstart quick-framework framework-understanding)
# 可安装的 skills（单文件形式）
AVAILABLE_FILE_SKILLS=(setup-cowork setup-cowork-teams)

cleanup() {
  [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]] && rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

info()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[1;32m[OK]\033[0m    %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m  %s\n" "$*"; }
error() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; exit 1; }

list_skills() {
  echo ""
  info "可用的 Skills:"
  echo ""
  for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
    printf "  📦 %-30s (目录)\n" "$s"
  done
  for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
    printf "  📄 %-30s (单文件)\n" "$s"
  done
  echo ""
  info "用法: bash install-skills.sh <skill-name> [<skill-name> ...]"
  info "不带参数则安装全部 skills"
  echo ""
}

install_dir_skill() {
  local name="$1"
  local src="${TMP_DIR}/.claude/skills/${name}"
  local dst="${GLOBAL_SKILLS_DIR}/${name}"

  if [[ ! -d "$src" ]]; then
    warn "目录 skill '${name}' 在仓库中未找到，跳过"
    return 1
  fi

  mkdir -p "${dst}"
  cp -r "${src}/." "${dst}/"
  ok "已安装: ${name} → ${dst}"
}

install_file_skill() {
  local name="$1"
  local src="${TMP_DIR}/.claude/skills/${name}.md"
  local dst="${GLOBAL_SKILLS_DIR}/${name}.md"

  if [[ ! -f "$src" ]]; then
    warn "文件 skill '${name}' 在仓库中未找到，跳过"
    return 1
  fi

  cp "${src}" "${dst}"
  ok "已安装: ${name}.md → ${dst}"
}

install_skill() {
  local name="$1"
  # 检查是目录 skill 还是文件 skill
  for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
    [[ "$s" == "$name" ]] && { install_dir_skill "$name"; return; }
  done
  for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
    [[ "$s" == "$name" ]] && { install_file_skill "$name"; return; }
  done
  warn "未知的 skill: '${name}'"
  return 1
}

# ---- main ----

# 处理 --branch 参数
if [[ "${1:-}" == "--branch" ]]; then
  [[ -z "${2:-}" ]] && error "用法: --branch <branch-name>"
  BRANCH="$2"
  shift 2
fi

# 处理 --list
if [[ "${1:-}" == "--list" ]]; then
  list_skills
  exit 0
fi

# 确定要安装的 skills
if [[ $# -gt 0 ]]; then
  SELECTED=("$@")
else
  SELECTED=("${AVAILABLE_DIR_SKILLS[@]}" "${AVAILABLE_FILE_SKILLS[@]}")
fi

info "开始安装 skills..."
echo ""

# 克隆仓库到临时目录
TMP_DIR="$(mktemp -d)"
info "克隆仓库到临时目录 (分支: ${BRANCH})..."
git clone --depth 1 --single-branch --branch "${BRANCH}" "${REPO_URL}" "${TMP_DIR}" 2>/dev/null \
  || error "克隆仓库失败，请检查网络连接或分支名是否正确: ${BRANCH}"

# 创建全局 skills 目录
mkdir -p "${GLOBAL_SKILLS_DIR}"

# 安装
INSTALLED=0
FAILED=0
for skill in "${SELECTED[@]}"; do
  if install_skill "$skill"; then
    ((INSTALLED++))
  else
    ((FAILED++))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "安装完成: ${INSTALLED} 个成功, ${FAILED} 个跳过"
info "Skills 目录: ${GLOBAL_SKILLS_DIR}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
info "在任意项目中启动 Claude Code 即可使用已安装的 skills"
info "试试: claude → 输入 /quickstart"
echo ""
