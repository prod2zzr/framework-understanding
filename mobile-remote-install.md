# 远程控制 Claude Code：三种方式实测对比

> **结论**：OpenClaw 是目前唯一能完成"安装 skill → 新建项目 → 交互式启动"全流程的远程控制方式。

---

## 一、实测对比总览

| 能力 | Dispatch | Code --remote | OpenClaw |
|------|----------|---------------|----------|
| curl 安装 skill | ❌ 无法执行 | ✅ 全局安装可行 | ✅ |
| 搜索已安装 skills | ❌ 搜不到 | ✅ | ✅ |
| 项目目录外创建文件夹 | ❌ | ❌ 受限于项目目录 | ✅ |
| 启动 skill（如 /quickstart） | ❌ 无法启动 | ✅ 可启动 | ✅ |
| 看到交互选项并选择 | ❌ | ❌ 看不到弹出选项 | ✅ |
| 完整流程（安装→建目录→启动→交互） | ❌ | ❌ | ✅ |

### 各方式详细说明

**Dispatch**：无法远程通过 curl 安装 skill，无法启动 skill，甚至无法搜索到已安装的 skills。目前基本不可用于 skill 相关操作。

**Code --remote**：可以通过 curl 全局安装 skill，但无法在项目目录外创建文件夹。可以启动 skill（如 /quickstart），但看不到弹出的交互选项，无法进行下去。适合**仅需安装 skill** 的场景。

**OpenClaw**：完整流程可行——安装 skill、新建文件夹、进入文件夹、打开终端、启动 Claude Code、确认工作区安全、启动 /quickstart、看到交互选项、传递参数、开展项目。

---

## 二、推荐方式

### 方法 1：OpenClaw（推荐，完整流程）

OpenClaw 可以完成所有操作，包括：

1. 安装 skills
2. 在任意位置新建项目文件夹
3. 进入文件夹并打开终端
4. 启动 Claude Code 并确认工作区安全
5. 运行 `/quickstart` 并完成交互选项选择

### 方法 2：Code --remote（有限能力）

```bash
# 电脑端启动
claude --remote

# 手机浏览器打开输出的 URL
```

可以做的事：
- 通过 curl 全局安装 skills
- 在当前项目目录内操作

做不到的事：
- 在项目目录外创建新文件夹
- 看到 skill 的交互式选项（如 AskUserQuestion 弹窗）

#### 安装命令示例

```
# 安装所有 skills
curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash

# 只安装特定 skill
curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash -s -- quickstart

# 指定分支安装
curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/<branch>/install-skills.sh | bash -s -- --branch <branch>

# 查看可用 skills
curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash -s -- --list
```

### 方法 3：Dispatch（目前不可用）

> ⚠️ 实测发现 Dispatch 无法执行 curl 安装、无法启动 skill、甚至无法搜索到已安装的 skills。以下为理论链路，仅供参考。

```
📱 手机 Claude App
    ↓  自然语言指令
☁️  Dispatch 路由
    ↓
💻 本地 Cowork Agent
    ↓  bash: curl | bash 或 git clone + cp
📂 ~/.claude/skills/   ← 全局 skill 目录
```

---

## 三、安装后验证

在任意项目中启动 Claude Code，输入：

```
/quickstart 我要做一个新项目
```

如果 skill 正确识别并执行，说明安装成功。
