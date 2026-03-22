# 研究型项目模板

## 目录结构

```
{project_name}/
├── references/          # 原始资料（抓取的网页、PDF、论文）
│   └── _index.md        # 资料索引
├── analysis/            # 分析产出（对比表、框架图、总结）
├── notes/               # 工作笔记、灵感、草稿片段
├── CLAUDE.md
├── .claudeignore
└── .gitignore
```

创建命令：
```bash
mkdir -p references analysis notes
```

## .claudeignore 规则

```
# 大文件和二进制
*.zip
*.tar.gz
*.rar
*.7z
*.mp4
*.mov
*.avi
*.psd
*.ai

# 临时文件
*.tmp
*.swp
*.bak
~$*
.DS_Store
Thumbs.db

# 原始数据（若体积大）
*.csv
*.xlsx
*.json.gz
```

## .gitignore 规则

```
# 系统文件
.DS_Store
Thumbs.db
*.swp
*~

# 大型原始文件（按需取消注释）
# *.pdf
# *.csv
# *.xlsx
```

## 推荐工作流

研究型项目的典型 Claude 协作模式：

1. **资料收集阶段**：将 URL、PDF 等丢给 Claude，自动整理到 `references/`
2. **分析阶段**：让 Claude 基于 `references/` 生成对比分析、提取关键发现，输出到 `analysis/`
3. **笔记阶段**：随时让 Claude 帮你记录想法到 `notes/`
4. **产出阶段**：基于 `analysis/` 生成最终报告或演示文稿

建议在 CLAUDE.md 中明确你的研究问题和分析框架。
