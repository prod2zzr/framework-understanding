# 多阶段构建：base / ocr / dev
# 用法:
#   docker build -t contract-reviewer .                    # 基础版（无 OCR）
#   docker build --target ocr -t contract-reviewer:ocr .   # 含 OCR
#   docker build --target dev -t contract-reviewer:dev .    # 含测试依赖

# ── 阶段 1: 构建依赖 ─────────────────────────────────

FROM python:3.11-slim AS builder

WORKDIR /build

# 系统依赖（PDF 解析需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src/ src/

RUN pip install --no-cache-dir --prefix=/install .

# ── 阶段 2: 基础运行时 ───────────────────────────────

FROM python:3.11-slim AS base

LABEL maintainer="contract-reviewer"
LABEL description="AI 合同审核系统"

WORKDIR /app

# 从 builder 复制已安装的包
COPY --from=builder /install /usr/local

# 复制应用代码和配置
COPY src/ src/
COPY config/ config/
COPY pyproject.toml README.md ./

# 安装项目本身（editable 模式，利用已安装的依赖）
RUN pip install --no-cache-dir --no-deps -e .

# 创建数据目录
RUN mkdir -p data/chroma data/cache

# 非 root 用户运行
RUN useradd -m -r reviewer && chown -R reviewer:reviewer /app
USER reviewer

# 环境变量默认值
ENV CR_PROMPTS_DIR=/app/config/prompts \
    CR_RULES_PATH=/app/config/rules/default_rules.yaml \
    CR_VECTORSTORE_PATH=/app/data/chroma \
    CR_CACHE_DIR=/app/data/cache

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD contract-review --help > /dev/null 2>&1 || exit 1

# 默认启动 API 服务
CMD ["uvicorn", "contract_reviewer.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ── 阶段 3: OCR 版本 ─────────────────────────────────

FROM base AS ocr

USER root

# OCR 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "contract-reviewer[ocr]" 2>/dev/null \
    || pip install --no-cache-dir paddleocr pdf2image

USER reviewer

ENV CR_OCR_ENABLED=true \
    CR_OCR_PROVIDER=paddle

# ── 阶段 4: 开发版本 ──────────────────────────────────

FROM base AS dev

USER root

RUN pip install --no-cache-dir pytest pytest-asyncio respx python-multipart ruff

USER reviewer

# 开发版覆盖: 运行测试
CMD ["pytest", "tests/", "-v"]
