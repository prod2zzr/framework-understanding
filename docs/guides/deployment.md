# 部署指南：AI 合同审核系统

> 适用于 macOS (Apple Silicon) / Linux / Docker 部署
> 最后更新: 2026-04-05

---

## 一、硬件选购建议

### 你需要多少内存？

系统运行时的内存占用 = **模型权重** + **KV Cache（随上下文长度增长）** + **Embedding 模型** + **系统开销**。

Qwen3.5-9B 使用 GDN 混合架构（32 层中只有 8 层需要 KV Cache），长上下文内存开销是传统 Transformer 的 **1/4**。

**单用户总内存估算（Qwen3.5-9B Q4 + Qwen3-Embedding-0.6B）：**

| 上下文长度 | 模型权重 | KV Cache | Embedding | 系统+开销 | **总计** |
|-----------|----------|----------|-----------|----------|---------|
| 8K tokens | 5.2 GB | 0.26 GB | 0.5 GB | ~4 GB | **~10 GB** |
| 32K tokens | 5.2 GB | 1.0 GB | 0.5 GB | ~4 GB | **~11 GB** |
| 64K tokens | 5.2 GB | 2.0 GB | 0.5 GB | ~4 GB | **~12 GB** |
| 128K tokens | 5.2 GB | 4.0 GB | 0.5 GB | ~4 GB | **~14 GB** |

> 上下文长度参考：10 页中文合同 ≈ 3000-5000 字 ≈ 2000-3500 tokens。
> 8K 上下文足够处理单个分块 + 系统提示 + RAG 上下文。

**多用户并发（每用户独立 KV Cache）：**

| 并发人数 | 上下文/人 | KV Cache 总计 | 总占用 | 16GB 可行？ | 32GB 可行？ |
|---------|----------|---------------|--------|------------|------------|
| 1 | 32K | 1.0 GB | 11 GB | ✅ | ✅ |
| 2 | 16K | 1.0 GB | 11 GB | ✅ | ✅ |
| 3 | 16K | 1.5 GB | 11.5 GB | ✅ | ✅ |
| 3 | 32K | 3.0 GB | 13 GB | ⚠️ 偏紧 | ✅ |
| 5 | 32K | 5.0 GB | 15 GB | ❌ | ✅ |

> 启用 KV Cache 量化（`OLLAMA_KV_CACHE_TYPE=q8_0`）可将 KV Cache 减半。

### 选购建议

| 场景 | 推荐硬件 | 预算参考 |
|------|---------|---------|
| 个人试用 | Mac Mini M4 **16GB** / 256GB | ~¥4,000 |
| 1-3 人小团队 | Mac Mini M4 **32GB** / 512GB | ~¥7,000 |
| 5+ 人团队 | Mac Studio M4 Max **64GB** 或 Linux + GPU | ~¥15,000+ |

> **为什么选 Mac？** Apple Silicon 的统一内存架构让 CPU 和 GPU 共享内存，不需要独立显卡。M4 的内存带宽 (~120 GB/s) 足够支撑 9B 模型的推理。

---

## 二、推理速度预期

以 Mac Mini M4 16GB + Qwen3.5-9B Q4_K_M 实测数据为参考：

| 指标 | 数值 | 说明 |
|------|------|------|
| Prompt 处理速度 | 80-120 tok/s | 读取输入文本 |
| 生成速度 | 12-15 tok/s | 输出审查结果 |
| 首 token 延迟 (2K prompt) | ~0.5-1 秒 | 短文本 |
| 首 token 延迟 (8K prompt) | ~3-5 秒 | 含 RAG 上下文 |

**审查一份合同需要多久？**

以 10 页合同为例（~3000 字）：
- 4 个维度（风险/合规/完整性/公平性）排队处理
- 每个维度: prompt 处理 ~2-3 秒 + 生成 ~40-60 秒
- **总计约 3-4 分钟**（单用户，包含 RAG 检索和验证）

> 多用户时排队等待，但不会显著增加单次审查时间。

---

## 三、方案 A：Mac Mini 本地部署（推荐）

合同不出本机，零费用，适合对数据安全有要求的场景。

### 步骤 1：安装 Ollama

```bash
# macOS 一键安装
curl -fsSL https://ollama.ai/install.sh | sh

# 或从 https://ollama.ai 下载安装包
```

### 步骤 2：下载模型

```bash
# LLM 模型（~5.2 GB，首次下载约 5-10 分钟）
ollama pull qwen3.5:9b

# Embedding 模型（~0.5 GB）
ollama pull qwen3-embedding:0.6b
```

### 步骤 3：安装项目

```bash
# 克隆代码
git clone https://github.com/prod2zzr/framework-understanding.git
cd framework-understanding

# 安装 Python 依赖
pip install -e .
```

### 步骤 4：配置

```bash
cp .env.example .env
```

编辑 `.env`，修改以下关键项：

```bash
# LLM — 本地模型
CR_LLM_MODEL=ollama/qwen3.5:9b
CR_LLM_API_BASE=http://localhost:11434
CR_LLM_API_KEY=                          # 留空，本地不需要

# Embedding — 本地向量模型
CR_EMBEDDING_MODEL=ollama/qwen3-embedding:0.6b
CR_EMBEDDING_API_BASE=http://localhost:11434

# RAG — 暂时关闭（首次体验可跳过知识库）
CR_RAG_MODE=disabled
```

### 步骤 5：审查合同

```bash
# 审查单份合同
contract-review review 你的合同.pdf

# 输出为 JSON（方便程序处理）
contract-review review 你的合同.pdf --format json --output report.json

# 批量审查整个目录
contract-review batch ./合同目录/ --output ./reports/
```

### 步骤 6（可选）：启用 API 服务

```bash
# 启动 API 服务，供前端或其他系统调用
uvicorn contract_reviewer.app:app --host 0.0.0.0 --port 8000

# 访问 http://localhost:8000/docs 查看 API 文档
```

---

## 四、方案 B：云端 API（最快上手）

不需要下载模型，10 分钟跑通，但合同内容会发送到云端。

### 步骤

```bash
git clone https://github.com/prod2zzr/framework-understanding.git
cd framework-understanding
pip install -e .
cp .env.example .env
```

编辑 `.env`：

```bash
CR_LLM_MODEL=anthropic/claude-sonnet-4-20250514
CR_LLM_API_KEY=sk-ant-你的API密钥      # 从 console.anthropic.com 获取
CR_RAG_MODE=disabled

# 不需要 Embedding 配置（RAG 已关闭）
```

```bash
contract-review review 你的合同.pdf
```

**费用**：Claude API 按 token 计费，审查一份 10 页合同约 $0.05-0.15。

---

## 五、方案 C：Docker 部署

适合服务器部署或团队共享。

```bash
# 构建基础镜像
docker build -t contract-reviewer .

# 运行（配合外部 Ollama）
docker run -d \
  -p 8000:8000 \
  -e CR_LLM_MODEL=ollama/qwen3.5:9b \
  -e CR_LLM_API_BASE=http://host.docker.internal:11434 \
  -e CR_RAG_MODE=disabled \
  contract-reviewer

# 或使用云端 API
docker run -d \
  -p 8000:8000 \
  -e CR_LLM_MODEL=anthropic/claude-sonnet-4-20250514 \
  -e CR_LLM_API_KEY=sk-ant-你的key \
  -e CR_RAG_MODE=disabled \
  contract-reviewer
```

---

## 六、多用户并发配置

当多人通过 API 同时使用时，需要配置 Ollama 的并发参数。

### 设置 Ollama 环境变量

```bash
# macOS: 编辑 Ollama 配置
launchctl setenv OLLAMA_NUM_PARALLEL 3           # 最大并发请求数
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0       # KV Cache 量化（内存减半）
launchctl setenv OLLAMA_FLASH_ATTENTION 1        # Flash Attention（KV 量化前提）

# 重启 Ollama 生效
killall ollama && ollama serve
```

### 并发数推荐

| 内存 | 推荐 `OLLAMA_NUM_PARALLEL` | 上下文/人 | 说明 |
|------|--------------------------|----------|------|
| 16 GB | 2 | 16K | 保守稳定 |
| 16 GB + q8_0 | 3 | 16K | KV 量化后可多一人 |
| 32 GB | 4 | 32K | 舒适 |
| 32 GB + q8_0 | 5-6 | 32K | 充裕 |

> 超过并发上限的请求会自动排队，不会报错。

---

## 七、模型选择依据

### LLM 模型

| 模型 | 适用场景 | 内存 | 审查质量 |
|------|---------|------|---------|
| **Qwen3.5-9B** | ★ 16GB 首选 | ~5.2 GB | 优秀 — GPQA 81.7 |
| Qwen3.5-4B | 极端内存受限 | ~3 GB | 良好 — 简单合同够用 |
| Qwen3.5-27B | 32GB+ 设备 | ~16 GB | 更佳 — 复杂合同 |
| Claude Sonnet 4 | 云端 API | 0 (云端) | 优秀 — 需联网 |

### Embedding 模型

| 模型 | MMTEB 分 | 内存 | 说明 |
|------|---------|------|------|
| **Qwen3-Embedding-0.6B** | 64.34 | ~0.5 GB | ★ 性价比首选 |
| Qwen3-Embedding-8B | 70.58 | ~5 GB | 精度最高，32GB 设备用 |
| BGE-large-zh-v1.5 | ~60 | ~0.6 GB | 老牌稳定，项目默认 |

> Qwen3-Embedding-0.6B（0.6B 参数）在 MMTEB 上打赢了 OpenAI text-embedding-3-large。

---

## 八、OCR 配置（扫描件合同）

**只有扫描件才需要 OCR**。判断方法：PDF 里的文字能用鼠标选中 → 不需要。

```bash
# 安装 OCR 依赖
pip install -e ".[ocr]"

# .env 配置
CR_OCR_ENABLED=true
CR_OCR_PROVIDER=paddleocr

# 审查时加 --ocr 参数
contract-review review 扫描件.pdf --ocr
```

> PaddleOCR 模型约 1 GB，首次运行自动下载。
> **注意**：OCR 模块代码已写但尚未完整验证，可能需要调试。

---

## 九、常见问题

### Q: 内存不足（OOM）怎么办？

1. 减小上下文长度: 在 Ollama API 调用时设置 `num_ctx=8192`
2. 换更小的模型: `ollama pull qwen3.5:4b`
3. 启用 KV Cache 量化: `OLLAMA_KV_CACHE_TYPE=q4_0`（最激进，内存减 3/4）

### Q: 如何监控内存使用？

```bash
# macOS
# 打开 Activity Monitor → Memory 标签页
# 或命令行
sudo memory_pressure

# 查看 Ollama 进程内存
ps aux | grep ollama
```

### Q: 如何验证模型已正确加载？

```bash
# 测试 LLM
ollama run qwen3.5:9b "你好，请用一句话介绍自己"

# 测试 Embedding
curl http://localhost:11434/api/embeddings -d '{
  "model": "qwen3-embedding:0.6b",
  "prompt": "合同违约责任"
}'
```

### Q: 合同内容安全吗？

- **本地部署（方案 A/C）**：合同全程在你的设备上处理，不发送到任何外部服务
- **云端 API（方案 B）**：合同内容会发送到 Anthropic/OpenAI 服务器。如果合同涉密，请使用本地部署

### Q: 262K 上下文能把整份合同一次输入吗？

理论上可以（262K tokens ≈ 40-50 万中文字），但 **不建议**：
1. 128K+ 上下文在 16GB 设备上内存偏紧
2. 研究表明长上下文模型在 >4K tokens 时检索质量下降（NoLiMa 基准）
3. 项目的条款感知分块 + RAG 检索方案在实践中更可靠

### Q: 16GB 和 32GB Mac Mini 该选哪个？

- **只有你一个人用** → 16GB 足够
- **2-3 人团队共用** → 16GB 勉强，32GB 更舒适
- **想用更大模型（27B）或更多并发** → 32GB
- **价差约 ¥3,000**，如果预算允许，直接上 32GB
