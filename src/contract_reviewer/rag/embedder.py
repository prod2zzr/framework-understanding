"""Embedding abstraction supporting cloud and local models."""

import logging

import litellm

from contract_reviewer.models.config import Settings

logger = logging.getLogger(__name__)

# Maximum texts per embedding API call
MAX_BATCH_SIZE = 96
# Timeout for embedding calls (seconds)
EMBED_TIMEOUT = 60


class EmbeddingError(Exception):
    """Raised when embedding fails."""


class Embedder:
    """Generate embeddings via LiteLLM (supports OpenAI, Ollama, etc.)."""

    def __init__(self, settings: Settings):
        self.model = settings.embedding_model
        self.api_base = settings.embedding_api_base

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, automatically splitting into sub-batches."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), MAX_BATCH_SIZE):
            batch = texts[i : i + MAX_BATCH_SIZE]
            embeddings = await self._embed_batch(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch of texts."""
        kwargs = {
            "model": self.model,
            "input": texts,
            "timeout": EMBED_TIMEOUT,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base

        try:
            response = await litellm.aembedding(**kwargs)
        except (litellm.APIConnectionError, litellm.Timeout, litellm.APIError) as e:
            raise EmbeddingError(f"Embedding API call failed: {e}") from e
        except Exception as e:
            raise EmbeddingError(f"Unexpected embedding error: {e}") from e

        data = getattr(response, "data", None)
        if not data:
            raise EmbeddingError("Embedding response has no data")

        return [item["embedding"] for item in data]

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text."""
        results = await self.embed([text])
        return results[0]
