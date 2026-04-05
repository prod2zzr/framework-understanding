# 代码质量审计报告

> 日期: 2026-04-04
> 范围: 全仓库 54 个 Python 文件，对照 CLAUDE.md 开发规范

## 审计结果总览

| # | 检查项 | 结果 | 说明 |
|---|--------|------|------|
| 1 | 静默异常吞没 | ✅ 通过 | 已修复 registry.py，所有异常均有日志或重抛 |
| 2 | 硬编码密钥/token | ✅ 通过 | 全部走 Settings/环境变量（CR_ 前缀） |
| 3 | Magic numbers | ⚠️ 6 处 | 见下方详细列表 |
| 4 | 死代码/注释代码 | ✅ 通过 | 无注释掉的废弃代码 |
| 5 | 异常缺少消息 | ✅ 通过 | 所有 raise 均含描述性消息 |
| 6 | 哈希算法统一 | ✅ 通过 | 已统一到 utils/hashing.py (SHA-256) |
| 7 | JSONL 写入重复 | ✅ 通过 | 已统一到 utils/jsonl.py |
| 8 | Import 组织 | ✅ 通过 | stdlib → third-party → local 一致 |
| 9 | 类型标注 | ✅ 通过 | 所有 public 函数已完整标注 |
| 10 | 未使用导入 | ✅ 通过 | 无冗余 import |

**总评**: 9/10 通过，代码质量优秀。唯一不通过项为 6 处轻微 magic number。

---

## 已修复项（commit c7e6cf4）

| # | 问题 | 严重性 | 修复方式 |
|---|------|--------|---------|
| 1 | `client.py` 缺失 `import random` | P0 | 补充导入 |
| 2 | `registry.py` 静默吞异常 (`except Exception: pass`) | P1 | 改为 `logger.debug()` |
| 3 | 魔法数字 `8000`（completeness 截断） | P1 | 提取到 `Settings.completeness_max_chars` |
| 4 | 魔法数字 `0.7`（cross-dimension 阈值） | P2 | 提取为 `_CROSS_DIM_THRESHOLD` 常量 |
| 5 | 重复哈希逻辑（3 个文件各自实现） | P2 | 统一到 `utils/hashing.py` |
| 6 | 重复 JSONL 写入逻辑（2 个文件） | P2 | 统一到 `utils/jsonl.py` |
| 7 | ingestor.py 使用 MD5（弱哈希） | P2 | 改为 SHA-256 |
| 8 | Embedding 串行批处理 | P2 | 改为 asyncio.gather + Semaphore 并发 |

---

## 未解决项（Outstanding）

### Magic Numbers（6 处，均为低严重性）

| 文件 | 行号 | 值 | 含义 | 建议 |
|------|------|----|------|------|
| `review/engine.py` | 339 | `8` | 合规 FAIL 权重 | 提取为常量 |
| `review/engine.py` | 341 | `3` | 合规 WARNING 权重 | 提取为常量 |
| `plugins/builtin/risk_clauses.py` | 50 | `100` | 上下文窗口字符数 | 提取为常量 |
| `plugins/builtin/term_fairness.py` | 48 | `100` | 上下文窗口字符数 | 提取为常量 |
| `rag/prompt_builder.py` | 88 | `200` | token 预留 overhead | 已有局部变量名，可提升为模块常量 |
| `utils/hashing.py` | 11 | `8192` | 文件读取 chunk 大小 | 可提取为 `_READ_CHUNK_SIZE` |

### 基础设施缺失

| 优先级 | 问题 | 影响 | 建议 |
|--------|------|------|------|
| **P0** | 零测试覆盖 | 无法验证行为，回归风险极高 | 添加 pytest 套件：models/chunking/plugins 单元测试 + engine 集成测试（mock LLM） |
| **P1** | 无 lint/格式化配置 | 代码风格无自动化保障 | pyproject.toml 添加 `[tool.ruff]`（本次已完成 ✅） |
| **P1** | 无 CI/CD 流水线 | 无自动化质量门禁 | 添加 GitHub Actions: lint → test → build |
| **P2** | 无 Dockerfile | 无法标准化部署 | 添加多阶段 Dockerfile |
| **P3** | Commit 缺 scope | 规范一致性 | 后续遵循，不改历史 |

---

## 经验总结

1. **工具统一早做**：哈希和 JSONL 的重复是渐进开发的自然产物，但应在第二次出现时就统一
2. **import 完整性**：`import random` 遗漏说明手动 review 不够，需要 lint 工具（ruff F401）自动检测
3. **审计驱动改进**：系统性审计比零散修复更有效，一次发现全部问题比多次小修补效率高
