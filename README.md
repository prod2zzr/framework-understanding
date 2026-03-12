# HR花名册智能匹配系统

从任意格式的HR花名册中，用自然语言查找和匹配合适人选。以大语言模型（通过OpenRouter）作为"大脑"，自动调用工具完成解析、分析、筛选、评分全流程。

**所有数据均在本地处理，不会上传到任何服务器。**

## 架构

```
Streamlit UI → LLM Orchestrator (OpenRouter) → Tools
                                                 ├── parse_excel     解析任意格式花名册
                                                 ├── analyze_schema  语义化列名映射
                                                 ├── search_roster   结构化条件筛选
                                                 └── score_matches   候选人评分排名
```

## Windows 一键部署

### 首次配置（只需一次）

1. 双击 `setup.bat`，自动完成 Python 安装和依赖配置
   - 如果系统未安装 Python，会优先使用 `tools/` 下的内置安装包
   - 如果 `tools/` 下没有安装包，请从以下地址下载后放入：
     - 国内镜像：https://mirrors.huaweicloud.com/python/3.11.9/python-3.11.9-amd64.exe
     - 官方地址：https://www.python.org/downloads/
2. 将花名册文件放入 `data/` 文件夹（支持 .xlsx、.xls、.et、.csv）

### 每次使用

1. 双击 `start.bat`
2. 浏览器自动打开，从下拉框选择花名册文件
3. 用自然语言提问，例如：
   - "帮我找技术部3年以上经验的本科生"
   - "谁擅长Python和机器学习？"
   - "列出月薪2万以上的在职员工"
4. 首次使用需在侧边栏输入 OpenRouter API Key（自动保存，之后无需重复输入）

## 项目结构

```
├── setup.bat               # 一键环境配置
├── start.bat               # 一键启动应用
├── data/                   # 放置花名册文件（.xlsx/.xls/.et/.csv）
├── tools/                  # 放置 Python 安装包（可选）
├── hr_matching/
│   ├── app.py              # Streamlit 入口
│   ├── config.py           # 配置
│   ├── llm/
│   │   ├── orchestrator.py # LLM tool-use 循环
│   │   └── tool_registry.py# 工具注册与调度
│   └── tools/
│       ├── parse_excel.py  # 解析花名册（xlsx/xls/et/csv）
│       ├── analyze_schema.py # 分析列名语义
│       ├── search_roster.py  # 筛选候选人
│       └── score_matches.py  # 评分排名
├── sample_data/            # 示例数据生成器
└── requirements.txt
```

## 核心设计

- **格式无关**: 支持 .xlsx/.xls/.et(WPS)/.csv，`analyze_schema` 工具自动识别任意列名含义
- **数据安全**: 所有数据在本地处理，花名册文件不会离开你的电脑
- **LLM驱动**: 大模型自主决定调用哪些工具、以什么顺序，灵活应对各种查询
- **零门槛部署**: 双击 bat 文件即可，无需命令行操作
- **国内友好**: pip 使用清华镜像源，Python 安装包可内置或从华为镜像下载
