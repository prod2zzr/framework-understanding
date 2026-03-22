#!/usr/bin/env bash
# ============================================================
# install-skills.sh — 一键安装 framework-understanding skills
# 用法:
#   curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash
#   curl -sL ... | bash -s -- quickstart               # 只安装指定 skill
#   curl -sL ... | bash -s -- quickstart quick-framework # 安装多个
#   curl -sL ... | bash -s -- --branch <branch-name>   # 指定分支
#   curl -sL ... | bash -s -- --list                    # 列出可用 skills
#   curl -sL ... | bash -s -- --status                  # 查看已安装状态
#   curl -sL ... | bash -s -- --update                  # 更新全部已安装 skills
#   curl -sL ... | bash -s -- --update quickstart       # 更新指定 skill
#   curl -sL ... | bash -s -- --uninstall               # 卸载全部 skills
#   curl -sL ... | bash -s -- --uninstall quickstart    # 卸载指定 skill
#   curl -sL ... | bash -s -- --help                    # 显示帮助
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
  [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]] && rm -rf "${TMP_DIR}" || true
}
trap cleanup EXIT

info()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[1;32m[OK]\033[0m    %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m  %s\n" "$*"; }
error() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; exit 1; }

# ---- 功能函数 ----

show_help() {
  cat <<'HELP'

  install-skills.sh — framework-understanding skills 管理工具

  命令:
    (无参数)                       安装全部 skills
    <skill> [<skill> ...]          安装指定 skills
    --list                         列出可用 skills
    --status                       查看已安装 skills 的状态
    --update [<skill> ...]         更新已安装的 skills（默认全部）
    --uninstall [<skill> ...]      卸载已安装的 skills（默认全部）
    --help                         显示此帮助信息

  选项:
    --branch <name>                指定仓库分支（默认 main）

  环境变量:
    INSTALL_SKILLS_BRANCH          等同于 --branch

  示例:
    bash install-skills.sh                              # 安装全部
    bash install-skills.sh quickstart                   # 只安装 quickstart
    bash install-skills.sh --update                     # 更新全部
    bash install-skills.sh --uninstall quickstart       # 卸载 quickstart
    bash install-skills.sh --status                     # 查看状态
    bash install-skills.sh --branch dev quickstart      # 从 dev 分支安装

HELP
}

list_skills() {
  echo ""
  info "可用的 Skills:"
  echo ""
  for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
    local marker=" "
    is_installed "$s" && marker="*"
    printf "  [%s] %-30s (目录)\n" "$marker" "$s"
  done
  for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
    local marker=" "
    is_installed "$s" && marker="*"
    printf "  [%s] %-30s (单文件)\n" "$marker" "$s"
  done
  echo ""
  info "[*] = 已安装"
  echo ""
}

is_dir_skill() {
  local name="$1"
  for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
    [[ "$s" == "$name" ]] && return 0
  done
  return 1
}

is_file_skill() {
  local name="$1"
  for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
    [[ "$s" == "$name" ]] && return 0
  done
  return 1
}

is_installed() {
  local name="$1"
  if is_dir_skill "$name"; then
    [[ -d "${GLOBAL_SKILLS_DIR}/${name}" ]]
  elif is_file_skill "$name"; then
    [[ -f "${GLOBAL_SKILLS_DIR}/${name}.md" ]]
  else
    return 1
  fi
}

show_status() {
  echo ""
  info "Skills 安装状态 (${GLOBAL_SKILLS_DIR}):"
  echo ""

  local installed=0 total=0

  for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
    total=$((total + 1))
    if is_installed "$s"; then
      installed=$((installed + 1))
      local file_count
      file_count=$(find "${GLOBAL_SKILLS_DIR}/${s}" -type f 2>/dev/null | wc -l)
      ok "$(printf "%-28s %d 个文件" "$s" "$file_count")"
    else
      printf "  \033[90m%-32s 未安装\033[0m\n" "$s"
    fi
  done

  for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
    total=$((total + 1))
    if is_installed "$s"; then
      installed=$((installed + 1))
      local size
      size=$(wc -c < "${GLOBAL_SKILLS_DIR}/${s}.md" 2>/dev/null || echo 0)
      ok "$(printf "%-28s %s bytes" "${s}.md" "$size")"
    else
      printf "  \033[90m%-32s 未安装\033[0m\n" "${s}.md"
    fi
  done

  echo ""
  info "已安装: ${installed}/${total}"

  # 检查权限
  local settings="${HOME}/.claude/settings.json"
  if [[ -f "$settings" ]] && grep -q '"Skill"' "$settings"; then
    ok "Skill 权限: 已配置"
  else
    warn "Skill 权限: 未配置（运行安装命令可自动添加）"
  fi
  echo ""
}

ensure_skill_permission() {
  local settings="${HOME}/.claude/settings.json"

  # 不存在 → 创建
  if [[ ! -f "$settings" ]]; then
    mkdir -p "$(dirname "$settings")"
    cat > "$settings" <<'JSON'
{
    "permissions": {
        "allow": ["Skill"]
    }
}
JSON
    ok "已创建 settings.json 并添加 Skill 权限"
    return
  fi

  # 已有 Skill 权限 → 跳过
  if grep -q '"Skill"' "$settings"; then
    info "Skill 权限已存在"
    return
  fi

  # 存在但没 Skill → 用 python3 安全修改 JSON
  if command -v python3 &>/dev/null; then
    python3 -c "
import json
path = '$settings'
with open(path) as f:
    data = json.load(f)
data.setdefault('permissions', {}).setdefault('allow', [])
if 'Skill' not in data['permissions']['allow']:
    data['permissions']['allow'].append('Skill')
with open(path, 'w') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
    f.write('\n')
"
    ok "已在 settings.json 中添加 Skill 权限"
  elif command -v jq &>/dev/null; then
    local tmp
    tmp=$(mktemp)
    jq '.permissions.allow += ["Skill"] | .permissions.allow |= unique' "$settings" > "$tmp" \
      && mv "$tmp" "$settings"
    ok "已在 settings.json 中添加 Skill 权限"
  else
    warn "无法自动修改 settings.json（需要 python3 或 jq）"
    info "请手动添加 \"Skill\" 到 ${settings} 的 permissions.allow 数组"
  fi
}

clone_repo() {
  TMP_DIR="$(mktemp -d)"
  info "克隆仓库到临时目录 (分支: ${BRANCH})..."
  git clone --depth 1 --single-branch --branch "${BRANCH}" "${REPO_URL}" "${TMP_DIR}" 2>/dev/null \
    || error "克隆仓库失败，请检查网络连接或分支名是否正确: ${BRANCH}"
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
  if is_dir_skill "$name"; then
    install_dir_skill "$name"
  elif is_file_skill "$name"; then
    install_file_skill "$name"
  else
    warn "未知的 skill: '${name}'"
    return 1
  fi
}

uninstall_skill() {
  local name="$1"

  if ! is_dir_skill "$name" && ! is_file_skill "$name"; then
    warn "未知的 skill: '${name}'"
    return 1
  fi

  if ! is_installed "$name"; then
    warn "'${name}' 未安装，跳过"
    return 1
  fi

  if is_dir_skill "$name"; then
    rm -rf "${GLOBAL_SKILLS_DIR}/${name}"
    ok "已卸载: ${name}"
  elif is_file_skill "$name"; then
    rm -f "${GLOBAL_SKILLS_DIR}/${name}.md"
    ok "已卸载: ${name}.md"
  fi
}

do_install() {
  local skills=("$@")
  clone_repo
  mkdir -p "${GLOBAL_SKILLS_DIR}"

  local installed=0 failed=0
  for skill in "${skills[@]}"; do
    if install_skill "$skill"; then
      installed=$((installed + 1))
    else
      failed=$((failed + 1))
    fi
  done

  # 配置 Skill 权限
  if [[ $installed -gt 0 ]]; then
    ensure_skill_permission
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  ok "安装完成: ${installed} 个成功, ${failed} 个跳过"
  info "Skills 目录: ${GLOBAL_SKILLS_DIR}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  info "在任意项目中启动 Claude Code 即可使用已安装的 skills"
  info "试试: claude → 输入 /quickstart"
  echo ""
}

do_uninstall() {
  local skills=("$@")
  local removed=0 failed=0

  echo ""
  for skill in "${skills[@]}"; do
    if uninstall_skill "$skill"; then
      removed=$((removed + 1))
    else
      failed=$((failed + 1))
    fi
  done

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  ok "卸载完成: ${removed} 个已移除, ${failed} 个跳过"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  if [[ $removed -gt 0 ]]; then
    info "如需移除 Skill 权限，请编辑 ~/.claude/settings.json"
  fi
  echo ""
}

do_update() {
  local skills=("$@")

  # 过滤出已安装的 skills
  local to_update=()
  for skill in "${skills[@]}"; do
    if is_installed "$skill"; then
      to_update+=("$skill")
    else
      warn "'${skill}' 未安装，跳过更新"
    fi
  done

  if [[ ${#to_update[@]} -eq 0 ]]; then
    warn "没有可更新的 skills"
    echo ""
    info "使用 --status 查看已安装的 skills"
    info "使用不带参数的命令安装全部 skills"
    return
  fi

  info "更新 ${#to_update[@]} 个 skills..."

  # 先卸载再重装
  for skill in "${to_update[@]}"; do
    uninstall_skill "$skill" >/dev/null 2>&1 || true
  done

  clone_repo
  mkdir -p "${GLOBAL_SKILLS_DIR}"

  local updated=0 failed=0
  for skill in "${to_update[@]}"; do
    if install_skill "$skill"; then
      updated=$((updated + 1))
    else
      failed=$((failed + 1))
    fi
  done

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  ok "更新完成: ${updated} 个成功, ${failed} 个失败"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
}

# ---- main ----

# 处理 --branch 参数（可以出现在任何位置之前）
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      [[ -z "${2:-}" ]] && error "用法: --branch <branch-name>"
      BRANCH="$2"
      shift 2
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

# 分发命令
case "${1:-}" in
  --help|-h)
    show_help
    exit 0
    ;;
  --list)
    list_skills
    ;;
  --status)
    show_status
    ;;
  --uninstall)
    shift
    if [[ $# -gt 0 ]]; then
      do_uninstall "$@"
    else
      ALL_SKILLS=("${AVAILABLE_DIR_SKILLS[@]}" "${AVAILABLE_FILE_SKILLS[@]}")
      do_uninstall "${ALL_SKILLS[@]}"
    fi
    ;;
  --update)
    shift
    if [[ $# -gt 0 ]]; then
      do_update "$@"
    else
      ALL_SKILLS=("${AVAILABLE_DIR_SKILLS[@]}" "${AVAILABLE_FILE_SKILLS[@]}")
      do_update "${ALL_SKILLS[@]}"
    fi
    ;;
  *)
    # 默认：安装
    if [[ $# -gt 0 ]]; then
      SELECTED=("$@")
    else
      SELECTED=("${AVAILABLE_DIR_SKILLS[@]}" "${AVAILABLE_FILE_SKILLS[@]}")
    fi
    info "开始安装 skills..."
    echo ""
    do_install "${SELECTED[@]}"
    ;;
esac
