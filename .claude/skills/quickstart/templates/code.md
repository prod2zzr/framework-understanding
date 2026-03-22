# 代码型项目模板

## 目录结构

```
{project_name}/
├── src/                 # 源代码
├── tests/               # 测试文件
├── docs/                # 项目文档
│   └── references/      # 参考资料（框架文档、API 文档等）
├── CLAUDE.md
├── .claudeignore
└── .gitignore
```

创建命令：
```bash
mkdir -p src tests docs/references
```

## .claudeignore 规则

```
# 依赖目录
node_modules/
vendor/
.venv/
venv/
__pycache__/
*.pyc

# 构建产物
dist/
build/
out/
*.min.js
*.min.css
*.map

# 大文件和二进制
*.zip
*.tar.gz
*.mp4
*.mov
*.psd

# 临时文件
*.tmp
*.swp
*.log
.DS_Store
Thumbs.db

# IDE 配置（按需）
# .idea/
# .vscode/

# 锁文件（体积大但有用，按需排除）
# package-lock.json
# yarn.lock
# pnpm-lock.yaml
```

## .gitignore 规则

```
# 依赖
node_modules/
vendor/
.venv/
venv/
__pycache__/

# 构建产物
dist/
build/
out/

# 环境变量
.env
.env.local
.env.*.local

# 系统文件
.DS_Store
Thumbs.db
*.swp
*~

# IDE
.idea/
.vscode/
*.code-workspace

# 日志
*.log
npm-debug.log*
```

## 推荐工作流

代码型项目的典型 Claude 协作模式：

1. **架构阶段**：让 Claude 帮你设计项目结构，记录决策到 `docs/`
2. **开发阶段**：在 `src/` 中编写代码，Claude 辅助实现
3. **测试阶段**：让 Claude 生成测试到 `tests/`
4. **文档阶段**：基于代码自动生成文档到 `docs/`

建议在 CLAUDE.md 中明确技术栈、代码风格和测试要求。
