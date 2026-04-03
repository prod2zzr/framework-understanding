"""Precomputed query vectors for zero-model RAG retrieval.

Instead of loading a 0.3B embedding model at runtime to embed query text,
use precomputed vectors for common legal query concepts. This eliminates
the embedding model from the runtime memory footprint entirely.

Flow:
1. Offline: `scripts/precompute_queries.py` generates vectors using the
   embedding model, saves to JSON.
2. Runtime: Load JSON vectors, find the closest precomputed query to the
   actual query text (by keyword matching), use that vector to search ChromaDB.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Predefined query templates per review dimension.
# Each template has keywords (for matching) and a query text (for embedding).
QUERY_TEMPLATES: dict[str, list[dict]] = {
    "risk_analysis": [
        {"id": "liability_unlimited", "keywords": ["责任", "赔偿", "损失", "liability", "damages"], "query": "无限责任赔偿条款风险"},
        {"id": "penalty_excessive", "keywords": ["违约金", "罚款", "penalty", "liquidated"], "query": "违约金过高风险"},
        {"id": "termination_unilateral", "keywords": ["解除", "终止", "单方", "termination", "unilateral"], "query": "单方解除权风险"},
        {"id": "ip_broad", "keywords": ["知识产权", "著作权", "专利", "IP", "intellectual"], "query": "知识产权归属过宽风险"},
        {"id": "confidentiality_perpetual", "keywords": ["保密", "秘密", "confidential", "NDA"], "query": "保密条款期限和范围"},
        {"id": "indemnity", "keywords": ["补偿", "赔偿", "indemnif", "hold harmless"], "query": "补偿赔偿条款分析"},
        {"id": "auto_renewal", "keywords": ["自动续期", "续约", "auto", "renewal"], "query": "自动续期条款风险"},
    ],
    "compliance": [
        {"id": "contract_term", "keywords": ["期限", "有效期", "term", "duration"], "query": "合同期限合规要求"},
        {"id": "dispute_resolution", "keywords": ["争议", "仲裁", "诉讼", "管辖", "dispute", "arbitration"], "query": "争议解决条款合规"},
        {"id": "payment_terms", "keywords": ["付款", "支付", "价款", "payment"], "query": "付款条件合规要求"},
        {"id": "force_majeure", "keywords": ["不可抗力", "force majeure"], "query": "不可抗力条款合规"},
        {"id": "governing_law", "keywords": ["适用法律", "准据法", "governing law"], "query": "适用法律条款要求"},
        {"id": "format_clauses", "keywords": ["格式条款", "标准条款", "standard terms", "boilerplate"], "query": "格式条款合规性民法典第四百九十六条"},
    ],
    "completeness": [
        {"id": "standard_clauses", "keywords": ["完整", "必备", "缺失", "standard", "missing"], "query": "合同完整性必备条款检查"},
        {"id": "parties_info", "keywords": ["甲方", "乙方", "主体", "parties"], "query": "合同主体信息完整性"},
        {"id": "subject_matter", "keywords": ["标的", "内容", "服务", "subject"], "query": "合同标的描述完整性"},
    ],
    "term_fairness": [
        {"id": "reciprocal_rights", "keywords": ["对等", "公平", "均衡", "reciprocal", "fair"], "query": "条款对等性公平性分析"},
        {"id": "one_sided", "keywords": ["单方", "仅", "exclusively", "solely"], "query": "单方权利义务条款公平性"},
        {"id": "interpretation_right", "keywords": ["解释权", "最终解释", "interpretation"], "query": "最终解释权条款效力"},
    ],
}


class PrecomputedQueries:
    """Load and match precomputed query vectors for zero-model retrieval."""

    def __init__(self, vectors_path: str | None = None):
        self._vectors: dict[str, list[float]] = {}
        self._templates = QUERY_TEMPLATES

        if vectors_path:
            self._load_vectors(vectors_path)

    def _load_vectors(self, path: str) -> None:
        """Load precomputed vectors from JSON file."""
        p = Path(path)
        if not p.exists():
            logger.warning("Precomputed vectors not found at %s", path)
            return

        with open(p, encoding="utf-8") as f:
            data = json.load(f)

        self._vectors = data.get("vectors", {})
        logger.info("Loaded %d precomputed query vectors", len(self._vectors))

    @property
    def is_available(self) -> bool:
        """Whether precomputed vectors are loaded and ready."""
        return len(self._vectors) > 0

    def find_best_vector(self, query_text: str, dimension: str | None = None) -> list[float] | None:
        """Find the best matching precomputed vector for a query.

        Matches by keyword overlap between query text and template keywords.
        Returns None if no good match is found.
        """
        best_id = None
        best_score = 0

        templates = {}
        if dimension and dimension in self._templates:
            templates = {dimension: self._templates[dimension]}
        else:
            templates = self._templates

        for dim_name, dim_templates in templates.items():
            for template in dim_templates:
                score = sum(1 for kw in template["keywords"] if kw in query_text)
                if score > best_score:
                    best_score = score
                    best_id = template["id"]

        if best_id and best_id in self._vectors:
            return self._vectors[best_id]

        return None

    def get_all_template_queries(self) -> list[dict]:
        """Get all template queries for precomputation. Used by scripts/precompute_queries.py."""
        result = []
        for dim_name, templates in self._templates.items():
            for t in templates:
                result.append({
                    "id": t["id"],
                    "dimension": dim_name,
                    "query": t["query"],
                })
        return result

    @staticmethod
    def save_vectors(vectors: dict[str, list[float]], output_path: str) -> None:
        """Save precomputed vectors to JSON."""
        data = {"vectors": vectors, "version": "1.0"}
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
