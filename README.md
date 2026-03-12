# HR花名册智能匹配系统

从任意格式的HR Excel花名册中，用自然语言查找和匹配合适人选。以大语言模型（通过OpenRouter）作为"大脑"，自动调用工具完成解析、分析、筛选、评分全流程。

## 架构

```
Streamlit UI → LLM Orchestrator (OpenRouter) → Tools
                                                 ├── parse_excel     解析任意格式Excel
                                                 ├── analyze_schema  语义化列名映射
                                                 ├── search_roster   结构化条件筛选
                                                 └── score_matches   候选人评分排名
```

## 快速开始

```bash
pip install -r requirements.txt
export OPENROUTER_API_KEY="your-key-here"
streamlit run hr_matching/app.py
```

## 使用方法

1. 在侧边栏输入 OpenRouter API Key
2. 上传任意格式的 Excel 花名册
3. 用自然语言提问，例如：
   - "帮我找技术部3年以上经验的本科生"
   - "谁擅长Python和机器学习？"
   - "列出月薪2万以上的在职员工"

## 项目结构

```
hr_matching/
├── app.py                  # Streamlit 入口
├── config.py               # 配置（API地址、模型等）
├── llm/
│   ├── orchestrator.py     # LLM tool-use 循环
│   └── tool_registry.py    # 工具注册与调度
├── tools/
│   ├── parse_excel.py      # 解析Excel文件
│   ├── analyze_schema.py   # 分析列名语义
│   ├── search_roster.py    # 筛选候选人
│   └── score_matches.py    # 评分排名
├── requirements.txt
└── sample_data/
    ├── generate_sample.py  # 生成测试数据
    └── sample_roster.xlsx  # 80人示例花名册
```

## 核心设计

- **格式无关**: `analyze_schema` 工具将任意列名映射到标准语义字段，无需预设格式
- **LLM驱动**: 大模型自主决定调用哪些工具、以什么顺序，灵活应对各种查询
- **Tool-Use循环**: 基于OpenAI兼容的function calling协议，支持多轮工具调用
- **OpenRouter**: 支持多种模型（Claude、GPT-4o、Gemini等），一个API Key即可切换
