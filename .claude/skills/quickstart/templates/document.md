# 文档型项目模板

## 目录结构

```
{project_name}/
├── drafts/              # 草稿和迭代版本
├── references/          # 参考资料
│   └── _index.md        # 资料索引
├── assets/              # 图片、图表、附件
├── CLAUDE.md
├── .claudeignore
└── .gitignore
```

创建命令：
```bash
mkdir -p drafts references assets
```

## .claudeignore 规则

```
# 大文件和二进制
*.zip
*.tar.gz
*.mp4
*.mov
*.psd
*.ai

# 图片（Claude 可读但占 token）
# *.png
# *.jpg
# *.jpeg

# 临时文件
*.tmp
*.swp
*.bak
~$*
.DS_Store
Thumbs.db

# Office 临时文件
~$*.docx
~$*.xlsx
~$*.pptx
```

## .gitignore 规则

```
# 系统文件
.DS_Store
Thumbs.db
*.swp
*~

# Office 临时文件
~$*

# 大型资产（按需取消注释）
# *.pdf
# assets/*.png
```

## 推荐工作流

文档型项目的典型 Claude 协作模式：

1. **准备阶段**：收集参考资料到 `references/`，建立资料索引
2. **大纲阶段**：让 Claude 基于参考资料生成文档大纲到 `drafts/`
3. **撰写阶段**：逐节扩写，Claude 保持风格一致性
4. **审阅阶段**：让 Claude 检查逻辑、格式、引用的完整性
5. **定稿阶段**：将最终版本从 `drafts/` 移到根目录或指定位置

建议在 CLAUDE.md 中明确文档风格（正式/非正式）、目标读者和格式要求。
