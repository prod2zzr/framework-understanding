#!/usr/bin/env bash
# ============================================================
# install-skills.sh — 一键安装 framework-understanding skills
# 用法:
#   curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash
#   curl -sL ... | bash -s -- quickstart               # 只安装指定 skill
#   curl -sL ... | bash -s -- quickstart quick-framework # 安装多个
#   curl -sL ... | bash -s -- --branch <branch-name>   # 指定分支
#   curl -sL ... | bash -s -- --codex                   # 安装到 Codex CLI
#   curl -sL ... | bash -s -- --both                    # 同时安装到 Claude Code 和 Codex CLI
#   curl -sL ... | bash -s -- --list                    # 列出可用 skills
#   curl -sL ... | bash -s -- --status                  # 查看已安装状态
#   curl -sL ... | bash -s -- --update                  # 更新全部已安装 skills
#   curl -sL ... | bash -s -- --update quickstart       # 更新指定 skill
#   curl -sL ... | bash -s -- --uninstall               # 卸载全部 skills
#   curl -sL ... | bash -s -- --uninstall quickstart    # 卸载指定 skill
#   curl -sL ... | bash -s -- --help                    # 显示帮助
#   INSTALL_SKILLS_BRANCH=dev curl -sL ... | bash       # 环境变量指定分支
#   INSTALL_SKILLS_TARGET=both curl -sL ... | bash      # 环境变量指定目标平台
# ============================================================

set -euo pipefail

REPO_URL="https://github.com/prod2zzr/framework-understanding.git"
BRANCH="${INSTALL_SKILLS_BRANCH:-main}"
CLAUDE_SKILLS_DIR="${HOME}/.claude/skills"
CODEX_SKILLS_DIR="${HOME}/.codex/skills"
TARGET="${INSTALL_SKILLS_TARGET:-claude}"
TMP_DIR=""

# 可安装的 skills（目录形式）— Claude Code 和 Codex CLI 均支持
AVAILABLE_DIR_SKILLS=(quickstart quick-framework framework-understanding fw-universal)
# 可安装的 skills（单文件形式）— 仅 Claude Code 支持
AVAILABLE_FILE_SKILLS=(setup-cowork setup-cowork-teams)

cleanup() {
  [[ -n "${TMP_DIR}" && -d "${TMP_DIR}" ]] && rm -rf "${TMP_DIR}" || true
}
trap cleanup EXIT

info()  { printf "\033[1;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[1;32m[OK]\033[0m    %s\n" "$*"; }
warn()  { printf "\033[1;33m[WARN]\033[0m  %s\n" "$*"; }
error() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*"; exit 1; }

# ---- 目标平台辅助函数 ----

targets_claude() { [[ "$TARGET" == "claude" || "$TARGET" == "both" ]]; }
targets_codex()  { [[ "$TARGET" == "codex"  || "$TARGET" == "both" ]]; }

target_label() {
  case "$TARGET" in
    claude) echo "Claude Code" ;;
    codex)  echo "Codex CLI" ;;
    both)   echo "Claude Code + Codex CLI" ;;
  esac
}

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

  目标平台:
    (默认)                         安装到 Claude Code (~/.claude/skills/)
    --codex                        安装到 Codex CLI (~/.codex/skills/)
    --both                         同时安装到 Claude Code 和 Codex CLI

  选项:
    --branch <name>                指定仓库分支（默认 main）

  环境变量:
    INSTALL_SKILLS_BRANCH          等同于 --branch
    INSTALL_SKILLS_TARGET          等同于 --codex/--both (值: claude|codex|both)

  注意:
    单文件 skills (setup-cowork 等) 仅支持 Claude Code，Codex CLI 不支持单文件格式。
    使用 --codex 时，单文件 skills 会自动跳过。

  示例:
    bash install-skills.sh                              # 安装全部到 Claude Code
    bash install-skills.sh --codex fw-universal         # 安装 fw-universal 到 Codex CLI
    bash install-skills.sh --both                       # 安装全部到两个平台
    bash install-skills.sh --codex --status             # 查看 Codex CLI 安装状态
    bash install-skills.sh --update                     # 更新全部
    bash install-skills.sh --uninstall quickstart       # 卸载 quickstart
    bash install-skills.sh --branch dev quickstart      # 从 dev 分支安装

HELP
}

list_skills() {
  echo ""
  info "可用的 Skills (目标: $(target_label)):"
  echo ""
  for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
    local marker=" "
    is_installed "$s" && marker="*"
    printf "  [%s] %-30s (目录)\n" "$marker" "$s"
  done
  if targets_claude; then
    for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
      local marker=" "
      is_installed "$s" && marker="*"
      printf "  [%s] %-30s (单文件, 仅 Claude Code)\n" "$marker" "$s"
    done
  else
    for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
      printf "  \033[90m[ ] %-30s (单文件, 仅 Claude Code — 当前目标不支持)\033[0m\n" "$s"
    done
  fi
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
    if targets_claude && [[ -d "${CLAUDE_SKILLS_DIR}/${name}" ]]; then
      return 0
    fi
    if targets_codex && [[ -d "${CODEX_SKILLS_DIR}/${name}" ]]; then
      return 0
    fi
    return 1
  elif is_file_skill "$name"; then
    if targets_claude && [[ -f "${CLAUDE_SKILLS_DIR}/${name}.md" ]]; then
      return 0
    fi
    return 1
  else
    return 1
  fi
}

show_status() {
  echo ""
  info "Skills 安装状态 (目标: $(target_label)):"

  # Claude Code 状态
  if targets_claude; then
    echo ""
    info "── Claude Code (${CLAUDE_SKILLS_DIR}) ──"
    echo ""
    local c_installed=0 c_total=0

    for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
      c_total=$((c_total + 1))
      if [[ -d "${CLAUDE_SKILLS_DIR}/${s}" ]]; then
        c_installed=$((c_installed + 1))
        local file_count
        file_count=$(find "${CLAUDE_SKILLS_DIR}/${s}" -type f 2>/dev/null | wc -l)
        ok "$(printf "%-28s %d 个文件" "$s" "$file_count")"
      else
        printf "  \033[90m%-32s 未安装\033[0m\n" "$s"
      fi
    done

    for s in "${AVAILABLE_FILE_SKILLS[@]}"; do
      c_total=$((c_total + 1))
      if [[ -f "${CLAUDE_SKILLS_DIR}/${s}.md" ]]; then
        c_installed=$((c_installed + 1))
        local size
        size=$(wc -c < "${CLAUDE_SKILLS_DIR}/${s}.md" 2>/dev/null || echo 0)
        ok "$(printf "%-28s %s bytes" "${s}.md" "$size")"
      else
        printf "  \033[90m%-32s 未安装\033[0m\n" "${s}.md"
      fi
    done

    echo ""
    info "Claude Code: ${c_installed}/${c_total}"

    local settings="${HOME}/.claude/settings.json"
    if [[ -f "$settings" ]] && grep -q '"Skill"' "$settings"; then
      ok "Skill 权限: 已配置"
    else
      warn "Skill 权限: 未配置（运行安装命令可自动添加）"
    fi
  fi

  # Codex CLI 状态
  if targets_codex; then
    echo ""
    info "── Codex CLI (${CODEX_SKILLS_DIR}) ──"
    echo ""
    local x_installed=0 x_total=0

    for s in "${AVAILABLE_DIR_SKILLS[@]}"; do
      x_total=$((x_total + 1))
      if [[ -d "${CODEX_SKILLS_DIR}/${s}" ]]; then
        x_installed=$((x_installed + 1))
        local file_count
        file_count=$(find "${CODEX_SKILLS_DIR}/${s}" -type f 2>/dev/null | wc -l)
        ok "$(printf "%-28s %d 个文件" "$s" "$file_count")"
      else
        printf "  \033[90m%-32s 未安装\033[0m\n" "$s"
      fi
    done

    echo ""
    info "Codex CLI: ${x_installed}/${x_total} (仅目录 skills，Codex 不支持单文件)"
    ok "Codex CLI 无需额外权限配置（自动发现 skills）"
  fi

  echo ""
}

ensure_skill_permission() {
  if ! targets_claude; then
    return
  fi

  local settings="${HOME}/.claude/settings.json"

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

  if grep -q '"Skill"' "$settings"; then
    info "Skill 权限已存在"
    return
  fi

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
  local ok_count=0

  if [[ ! -d "$src" ]]; then
    warn "目录 skill '${name}' 在仓库中未找到，跳过"
    return 1
  fi

  if targets_claude; then
    local dst="${CLAUDE_SKILLS_DIR}/${name}"
    mkdir -p "${dst}"
    cp -r "${src}/." "${dst}/"
    ok "已安装: ${name} → ${dst}"
    ok_count=$((ok_count + 1))
  fi

  if targets_codex; then
    local dst="${CODEX_SKILLS_DIR}/${name}"
    mkdir -p "${dst}"
    cp -r "${src}/." "${dst}/"
    ok "已安装: ${name} → ${dst}"
    ok_count=$((ok_count + 1))
  fi

  [[ $ok_count -gt 0 ]]
}

install_file_skill() {
  local name="$1"
  local src="${TMP_DIR}/.claude/skills/${name}.md"

  if [[ ! -f "$src" ]]; then
    warn "文件 skill '${name}' 在仓库中未找到，跳过"
    return 1
  fi

  if targets_claude; then
    local dst="${CLAUDE_SKILLS_DIR}/${name}.md"
    cp "${src}" "${dst}"
    ok "已安装: ${name}.md → ${dst}"
  fi

  if targets_codex; then
    warn "'${name}' 是单文件 skill，Codex CLI 不支持此格式，跳过 Codex 安装"
  fi

  targets_claude
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
  local removed=false

  if ! is_dir_skill "$name" && ! is_file_skill "$name"; then
    warn "未知的 skill: '${name}'"
    return 1
  fi

  if is_dir_skill "$name"; then
    if targets_claude && [[ -d "${CLAUDE_SKILLS_DIR}/${name}" ]]; then
      rm -rf "${CLAUDE_SKILLS_DIR}/${name}"
      ok "已卸载: ${name} (Claude Code)"
      removed=true
    fi
    if targets_codex && [[ -d "${CODEX_SKILLS_DIR}/${name}" ]]; then
      rm -rf "${CODEX_SKILLS_DIR}/${name}"
      ok "已卸载: ${name} (Codex CLI)"
      removed=true
    fi
  elif is_file_skill "$name"; then
    if targets_claude && [[ -f "${CLAUDE_SKILLS_DIR}/${name}.md" ]]; then
      rm -f "${CLAUDE_SKILLS_DIR}/${name}.md"
      ok "已卸载: ${name}.md (Claude Code)"
      removed=true
    fi
  fi

  if [[ "$removed" == false ]]; then
    warn "'${name}' 未安装，跳过"
    return 1
  fi
}

do_install() {
  local skills=("$@")
  clone_repo

  if targets_claude; then
    mkdir -p "${CLAUDE_SKILLS_DIR}"
  fi
  if targets_codex; then
    mkdir -p "${CODEX_SKILLS_DIR}"
  fi

  local installed=0 failed=0
  for skill in "${skills[@]}"; do
    if install_skill "$skill"; then
      installed=$((installed + 1))
    else
      failed=$((failed + 1))
    fi
  done

  if [[ $installed -gt 0 ]]; then
    ensure_skill_permission
  fi

  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  ok "安装完成: ${installed} 个成功, ${failed} 个跳过 ($(target_label))"
  if targets_claude; then
    info "Claude Code Skills: ${CLAUDE_SKILLS_DIR}"
  fi
  if targets_codex; then
    info "Codex CLI Skills:   ${CODEX_SKILLS_DIR}"
  fi
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  if targets_claude; then
    info "Claude Code: 在任意项目中启动即可使用 skills"
  fi
  if targets_codex; then
    info "Codex CLI:   重启 codex 即可自动发现新 skills"
  fi
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
  if [[ $removed -gt 0 ]] && targets_claude; then
    info "如需移除 Skill 权限，请编辑 ~/.claude/settings.json"
  fi
  echo ""
}

do_update() {
  local skills=("$@")

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

  info "更新 ${#to_update[@]} 个 skills ($(target_label))..."

  for skill in "${to_update[@]}"; do
    uninstall_skill "$skill" >/dev/null 2>&1 || true
  done

  clone_repo

  if targets_claude; then
    mkdir -p "${CLAUDE_SKILLS_DIR}"
  fi
  if targets_codex; then
    mkdir -p "${CODEX_SKILLS_DIR}"
  fi

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

# 处理 --branch / --codex / --both 参数（可以出现在任何位置）
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      [[ -z "${2:-}" ]] && error "用法: --branch <branch-name>"
      BRANCH="$2"
      shift 2
      ;;
    --codex)
      TARGET="codex"
      shift
      ;;
    --both)
      TARGET="both"
      shift
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"

info "目标平台: $(target_label)"

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
    if [[ $# -gt 0 ]]; then
      SELECTED=("$@")
    else
      if targets_codex && ! targets_claude; then
        SELECTED=("${AVAILABLE_DIR_SKILLS[@]}")
      else
        SELECTED=("${AVAILABLE_DIR_SKILLS[@]}" "${AVAILABLE_FILE_SKILLS[@]}")
      fi
    fi
    info "开始安装 skills..."
    echo ""
    do_install "${SELECTED[@]}"
    ;;
esac
