# AI 合同审核系统 (Contract Reviewer)

基于大语言模型的智能合同审查工具，支持云端 API（Claude）和本地模型（Ollama/vLLM）部署。

## 功能特性

- **多维度审查**: 风险识别、合规检查、完整性检测、条款公平性分析
- **双模式部署**: 云端 Claude API 或本地 Ollama/vLLM，通过环境变量一键切换
- **RAG 知识库**: 向量化法律知识检索（民法典、司法解释等），支持运行时嵌入和预计算两种模式
- **韧性设计**: 熔断器、指数退避重试、Token 预算控制、响应缓存
- **并发处理**: 多维度并行审查 + 批量合同处理
- **证据验证**: 审查结果自动与原文交叉验证，输出可追溯审计日志
- **插件扩展**: 自定义审查维度和规则
- **规则学习**: 从审查结果中发现候选规则，一键纳入规则库
- **可配置规则**: YAML 格式合规规则，法务人员可直接编辑
- **多格式支持**: PDF、DOCX、TXT 合同文件（扫描件可启用 OCR）
- **双输出模式**: JSON（机器可读）+ Markdown（人类可读）
- **双接口**: CLI 命令行 + FastAPI REST API（含 SSE 流式推送）

## 快速开始

### 安装

```bash
# 基础安装
pip install -e .

# 含 OCR 支持（扫描件识别）
pip install -e ".[ocr]"

# 含开发依赖（测试）
pip install -e ".[dev]"
```

### 配置

所有配置通过 `CR_` 前缀的环境变量设置，也可编辑 `config/settings.yaml`。详见 `.env.example`。

```bash
# 云端模式 — 设置 API Key
export CR_LLM_API_KEY=your_key_here

# 本地模式 — 使用 Ollama
export CR_LLM_MODEL="ollama/qwen2.5:7b"
export CR_LLM_API_BASE="http://localhost:11434"
```

### CLI 使用

```bash
# 审查单份合同
contract-review ./合同.pdf

# 指定模型
contract-review ./合同.pdf --model "ollama/qwen2.5:7b"

# JSON 输出
contract-review ./合同.pdf --format json --output report.json

# 仅运行指定维度
contract-review ./合同.pdf -d risk_analysis -d compliance

# 启用 OCR（扫描件）
contract-review ./合同.pdf --ocr

# 输出审计日志
contract-review ./合同.pdf --audit-log audit.jsonl

# 批量审查
contract-review batch ./contracts/ --output ./reports/
```

### 知识库管理

```bash
# 将法律文本灌入向量数据库
contract-review ingest ./knowledge_base/civil_code --type civil_code
contract-review ingest ./knowledge_base/judicial_interpretations --type judicial_interpretation
```

### 规则管理

```bash
# 将审查报告中发现的候选规则纳入规则库
contract-review accept-rule report.json              # 交互式选择
contract-review accept-rule report.json --all        # 接受全部
contract-review accept-rule report.json --id RULE_01 # 指定规则 ID
```

### 审计日志查看

```bash
# 查看审计日志摘要（LLM 调用统计、维度结果、证据验证）
contract-review audit-summary audit.jsonl

# 按合同名称过滤
contract-review audit-summary audit.jsonl --contract "某某合同"
```

## API 服务

```bash
# 启动 API 服务
uvicorn contract_reviewer.app:app --host 0.0.0.0 --port 8000

# 审查合同（返回 JSON）
curl -X POST http://localhost:8000/api/review \
  -F "file=@合同.pdf"

# 流式审查（SSE，实时返回进度和结果）
curl -X POST http://localhost:8000/api/review/stream \
  -F "file=@合同.pdf"

# 健康检查（熔断器状态、Token 预算）
curl http://localhost:8000/api/health
```

如果设置了 `CR_API_KEY`，请求需携带 `X-API-Key` header：

```bash
curl -X POST http://localhost:8000/api/review \
  -H "X-API-Key: your_api_key" \
  -F "file=@合同.pdf"
```

## 配置

通过环境变量（`CR_` 前缀）或 `config/settings.yaml` 配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `CR_LLM_MODEL` | LLM 模型 | `anthropic/claude-sonnet-4-20250514` |
| `CR_LLM_API_BASE` | 本地模型 API 地址 | - |
| `CR_LLM_API_KEY` | API 密钥 | - |
| `CR_LLM_MAX_CONCURRENT` | 最大并发 LLM 调用 | `5` |
| `CR_LLM_MAX_TOTAL_TOKENS` | Token 总预算 | `1000000` |
| `CR_LLM_MAX_RETRIES` | LLM 调用最大重试次数 | `3` |
| `CR_LLM_CIRCUIT_BREAKER_THRESHOLD` | 熔断器触发阈值 | `5` |
| `CR_EMBEDDING_MODEL` | 嵌入模型 | `ollama/bge-large-zh` |
| `CR_EMBEDDING_API_BASE` | 嵌入模型 API 地址 | `http://localhost:11434` |
| `CR_VECTORSTORE_PATH` | 向量库路径 | `./data/chroma` |
| `CR_RAG_MODE` | RAG 模式 | `runtime_embed` |
| `CR_OCR_ENABLED` | 启用 OCR | `false` |
| `CR_OCR_PROVIDER` | OCR 引擎 | `paddleocr` |
| `CR_API_KEY` | API 鉴权密钥（设置后启用） | - |

完整配置项见 [`.env.example`](.env.example) 和 [`src/contract_reviewer/models/config.py`](src/contract_reviewer/models/config.py)。

## 项目结构

```
src/contract_reviewer/
├── cli.py              # CLI 入口（Typer + Rich）
├── app.py              # FastAPI API 入口
├── models/             # Pydantic 数据模型 + Settings
│   └── config.py       # CR_ 前缀环境变量配置
├── llm/                # LLM 抽象层（LiteLLM + 熔断器 + 重试 + Token 预算 + 缓存）
├── rag/                # RAG 管线（ChromaDB + 嵌入 + 预计算查询）
├── review/             # 审核引擎 + 维度定义 + 证据验证 + 审计追踪
├── chunking/           # 合同解析（PDF/DOCX/TXT）+ Token 感知分块
├── plugins/            # 插件系统（ReviewPlugin 基类 + 内置插件）
├── ocr/                # OCR 支持（PaddleOCR / GLM-OCR）
├── streaming/          # SSE 流式输出
└── utils/              # 共享工具（hashing, jsonl）

config/
├── prompts/            # Jinja2 提示词模板（风险分析、合规检查、完整性、公平性）
├── rules/              # 合规规则（YAML，法务可编辑）
└── settings.yaml       # 默认配置
```

## 部署

详细部署指南（硬件选购、容量规划、多用户并发配置）见 [docs/guides/deployment.md](docs/guides/deployment.md)。

支持三种部署方式：

### 本地部署

Mac Mini / Linux + Ollama — 合同不出本机，零 API 费用。

```bash
pip install -e .
export CR_LLM_MODEL="ollama/qwen2.5:7b"
export CR_LLM_API_BASE="http://localhost:11434"
contract-review ./合同.pdf
```

### 云端 API

Claude API — 10 分钟上手，按量付费。

```bash
pip install -e .
export CR_LLM_API_KEY=your_key_here
contract-review ./合同.pdf
```

### Docker

适合服务器部署或团队共享。

```bash
# 基础版（无 OCR）
docker build -t contract-reviewer .

# 含 OCR 支持
docker build --target ocr -t contract-reviewer:ocr .

# 启动 API 服务
docker run -p 8000:8000 \
  -e CR_LLM_API_KEY=your_key \
  -v ./data:/app/data \
  contract-reviewer

# 单次 CLI 审查
docker run --rm \
  -e CR_LLM_API_KEY=your_key \
  -v ./合同.pdf:/app/input.pdf \
  contract-reviewer contract-review /app/input.pdf
```

## 技术栈

| 组件 | 技术 |
|------|------|
| **LLM** | LiteLLM（统一 Claude / Ollama / vLLM 接口） |
| **向量库** | ChromaDB |
| **嵌入** | bge-large-zh（本地 Ollama）/ text-embedding-3-small（云端） |
| **Web** | FastAPI + SSE（sse-starlette） |
| **CLI** | Typer + Rich |
| **数据校验** | Pydantic v2 + pydantic-settings |
| **文档解析** | pdfplumber + python-docx |
| **OCR（可选）** | PaddleOCR / GLM-OCR |
| **模板** | Jinja2 |
| **测试** | pytest + pytest-asyncio |
| **Lint** | ruff |
| **容器** | Docker（多阶段构建） |

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码检查
ruff check src/ tests/
ruff format --check src/ tests/
```
