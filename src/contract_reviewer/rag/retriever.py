"""Retrieve relevant legal knowledge for contract review."""

from dataclasses import dataclass

from contract_reviewer.rag.embedder import Embedder
from contract_reviewer.rag.vectorstore import SearchResult, VectorStore


@dataclass
class RetrievedContext:
    """A piece of legal context retrieved for prompt augmentation."""

    text: str
    source: str
    article_number: str
    relevance_score: float


class Retriever:
    """Retrieve relevant legal context from the knowledge base."""

    def __init__(self, embedder: Embedder, vectorstore: VectorStore, top_k: int = 5):
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.top_k = top_k

    async def retrieve(
        self,
        query: str,
        topic_filter: str | None = None,
    ) -> list[RetrievedContext]:
        """Retrieve relevant legal context for a query.

        Args:
            query: The contract text or question to find context for.
            topic_filter: Optional topic tag to narrow results (e.g., "liability").
        """
        embedding = await self.embedder.embed_single(query)

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
                relevance_score=1.0 - r.distance,  # cosine distance -> similarity
            )
            for r in results
        ]
