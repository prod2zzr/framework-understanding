# AI 合同审核系统 (Contract Reviewer)

基于大语言模型的智能合同审查工具，支持云端 API（Claude）和本地模型（Ollama/vLLM）部署。

## 功能特性

- **多维度审查**: 风险识别、合规检查、完整性检测、条款公平性分析
- **双模式部署**: 云端 Claude API 或本地 Ollama/vLLM，通过环境变量一键切换
- **RAG 知识库**: 向量化法律知识检索（民法典、司法解释等），让 AI 具备专业法律知识
- **并发处理**: 多维度并行审查 + 批量合同处理
- **插件扩展**: 自定义审查维度和规则
- **可配置规则**: YAML 格式合规规则，法务人员可直接编辑
- **多格式支持**: PDF、DOCX、TXT 合同文件
- **双输出模式**: JSON（机器可读）+ Markdown（人类可读）

## 快速开始

```bash
# 安装
pip install -e .

# 设置 API Key（云端模式）
export ANTHROPIC_API_KEY=your_key_here

# 审查单份合同
contract-review ./合同.pdf

# 使用本地模型
export CR_LLM_MODEL="ollama/qwen2.5:72b"
export CR_LLM_MAX_CONCURRENT=1
contract-review ./合同.pdf

# JSON 输出
contract-review ./合同.pdf --format json --output report.json

# 仅运行指定维度
contract-review ./合同.pdf -d risk_analysis -d compliance

# 批量审查
contract-review batch ./contracts/ --output ./reports/
```

## 知识库灌入

```bash
# 将法律文本灌入向量数据库
contract-review ingest ./knowledge_base/civil_code --type civil_code
contract-review ingest ./knowledge_base/judicial_interpretations --type judicial_interpretation
```

## API 服务

```bash
uvicorn contract_reviewer.app:app --host 0.0.0.0 --port 8000

# 审查合同
curl -X POST http://localhost:8000/api/review \
  -F "file=@合同.pdf"

# 流式审查（SSE）
curl -X POST http://localhost:8000/api/review/stream \
  -F "file=@合同.pdf"
```

## 配置

通过环境变量（`CR_` 前缀）或 `config/settings.yaml` 配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `CR_LLM_MODEL` | LLM 模型 | `anthropic/claude-sonnet-4-20250514` |
| `CR_LLM_API_BASE` | 本地模型 API 地址 | - |
| `CR_LLM_MAX_CONCURRENT` | 最大并发 LLM 调用 | `5` |
| `CR_EMBEDDING_MODEL` | 嵌入模型 | `ollama/bge-large-zh` |
| `CR_VECTORSTORE_PATH` | 向量库路径 | `./data/chroma` |

## 项目结构

```
src/contract_reviewer/
├── cli.py              # CLI 入口
├── app.py              # FastAPI API
├── models/             # Pydantic 数据模型
├── llm/                # LLM 抽象层（LiteLLM）
├── rag/                # RAG 管线（ChromaDB + 嵌入）
├── chunking/           # 条款感知文档分块
├── review/             # 审核引擎 + 维度定义
├── plugins/            # 插件系统
└── streaming/          # SSE 流式输出

config/
├── prompts/            # Jinja2 提示词模板
├── rules/              # 合规规则（YAML）
└── settings.yaml       # 默认配置
```

## 技术栈

- **LLM**: LiteLLM（统一 Claude/Ollama/vLLM 接口）
- **向量库**: ChromaDB
- **嵌入**: bge-large-zh（本地）/ text-embedding-3-small（云端）
- **Web**: FastAPI + SSE
- **CLI**: Typer + Rich
