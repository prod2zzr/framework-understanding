"""Retrieve relevant legal knowledge for contract review.

Supports two modes:
- "precomputed": Uses precomputed query vectors (no embedding model at runtime)
- "runtime_embed": Embeds query text at runtime (requires embedding model)
"""

import logging
from dataclasses import dataclass

from contract_reviewer.rag.embedder import Embedder
from contract_reviewer.rag.precomputed_queries import PrecomputedQueries
from contract_reviewer.rag.vectorstore import SearchResult, VectorStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievedContext:
    """A piece of legal context retrieved for prompt augmentation."""

    text: str
    source: str
    article_number: str
    relevance_score: float


class Retriever:
    """Retrieve relevant legal context from the knowledge base.

    In precomputed mode, no embedding model is loaded at runtime.
    Query text is matched to precomputed vectors by keyword overlap.
    """

    def __init__(
        self,
        vectorstore: VectorStore,
        top_k: int = 5,
        embedder: Embedder | None = None,
        precomputed: PrecomputedQueries | None = None,
        mode: str = "precomputed",
    ):
        self.vectorstore = vectorstore
        self.top_k = top_k
        self.embedder = embedder
        self.precomputed = precomputed
        self.mode = mode

    async def retrieve(
        self,
        query: str,
        topic_filter: str | None = None,
        dimension: str | None = None,
    ) -> list[RetrievedContext]:
        """Retrieve relevant legal context for a query.

        Args:
            query: The contract text or question to find context for.
            topic_filter: Optional topic tag to narrow results.
            dimension: Review dimension name (for precomputed query matching).
        """
        embedding = await self._get_embedding(query, dimension)
        if embedding is None:
            logger.debug("No embedding available for query, skipping retrieval")
            return []

        where = None
        if topic_filter:
            where = {"topic_tags": {"$contains": topic_filter}}

        results: list[SearchResult] = self.vectorstore.query(
            embedding=embedding,
            n_results=self.top_k,
            where=where,
        )

        return [
            RetrievedContext(
                text=r.text,
                source=r.metadata.get("document_name", ""),
                article_number=r.metadata.get("article_number", ""),
                relevance_score=1.0 - r.distance,
            )
            for r in results
        ]

    async def _get_embedding(self, query: str, dimension: str | None) -> list[float] | None:
        """Get query embedding using configured mode."""
        if self.mode == "precomputed" and self.precomputed and self.precomputed.is_available:
            vector = self.precomputed.find_best_vector(query, dimension)
            if vector is not None:
                return vector
            logger.debug("No precomputed match for query, falling back")

        # Fallback to runtime embedding if available
        if self.embedder:
            try:
                return await self.embedder.embed_single(query)
            except Exception as e:
                logger.warning("Runtime embedding failed: %s", e)
                return None

        return None
