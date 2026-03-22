# 手机远程安装 Skills 指南

通过手机端 Claude App 的 dispatch/cowork，用自然语言一句话安装 skills 到本地。

---

## 方法 1：一句话指令（推荐）

在手机 Claude App 中对 dispatch 说：

> **"运行这个命令安装 skills：`curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash`"**

### 只安装特定 skill

> "运行：`curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash -s -- quickstart`"

### 指定分支安装（代码未合并到 main 时使用）

> "运行：`curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/<branch>/install-skills.sh | bash -s -- --branch <branch>`"

### 查看可用 skills

> "运行：`curl -sL https://raw.githubusercontent.com/prod2zzr/framework-understanding/main/install-skills.sh | bash -s -- --list`"

---

## 方法 2：自然语言描述

如果不想记命令，直接用自然语言：

> "从 GitHub 仓库 prod2zzr/framework-understanding 克隆代码，把 .claude/skills/ 下所有内容复制到 ~/.claude/skills/ 作为全局 skill 安装，然后清理临时文件。"

---

## 方法 3：Claude Code --remote

```bash
# 电脑端启动
claude --remote

# 手机浏览器打开输出的 URL，然后输入：
/quickstart   # 直接使用已安装的 skill
```

---

## 权限链路

```
📱 手机 Claude App
    ↓  自然语言指令
☁️  Dispatch 路由
    ↓
💻 本地 Cowork Agent
    ↓  bash: curl | bash 或 git clone + cp
📂 ~/.claude/skills/   ← 全局 skill 目录
```

关键点：
- Dispatch 通过 cowork 连接到**本地机器**，拥有本地文件系统权限
- 不需要提前指定目录，agent 可以操作任意路径
- 安装完成后，在任意项目中启动 Claude Code 都能使用这些 skills

---

## 安装后验证

在任意项目中启动 Claude Code，输入：

```
/quickstart 我要做一个新项目
```

如果 skill 正确识别并执行，说明安装成功。
