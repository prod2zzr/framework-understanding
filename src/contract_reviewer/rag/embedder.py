"""Embedding abstraction supporting cloud and local models."""

import asyncio
import logging

import litellm

from contract_reviewer.llm.retry import retry_with_backoff
from contract_reviewer.models.config import Settings

logger = logging.getLogger(__name__)

# Maximum texts per embedding API call
MAX_BATCH_SIZE = 96
# Timeout for embedding calls (seconds)
EMBED_TIMEOUT = 60

# Maximum concurrent sub-batch API calls
_MAX_CONCURRENT_BATCHES = 3

# Transient exceptions worth retrying
_RETRYABLE = (litellm.APIConnectionError, litellm.Timeout, litellm.RateLimitError)


class EmbeddingError(Exception):
    """Raised when embedding fails."""


class Embedder:
    """Generate embeddings via LiteLLM (supports OpenAI, Ollama, etc.)."""

    def __init__(self, settings: Settings):
        self.model = settings.embedding_model
        self.api_base = settings.embedding_api_base

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, splitting into concurrent sub-batches."""
        batches = [
            texts[i : i + MAX_BATCH_SIZE]
            for i in range(0, len(texts), MAX_BATCH_SIZE)
        ]
        if len(batches) <= 1:
            # Single batch — skip concurrency overhead
            return await self._embed_batch(batches[0]) if batches else []

        sem = asyncio.Semaphore(_MAX_CONCURRENT_BATCHES)

        async def _guarded(batch: list[str]) -> list[list[float]]:
            async with sem:
                return await self._embed_batch(batch)

        results = await asyncio.gather(*[_guarded(b) for b in batches])
        return [emb for batch_result in results for emb in batch_result]

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch of texts with exponential backoff retry."""
        kwargs = {
            "model": self.model,
            "input": texts,
            "timeout": EMBED_TIMEOUT,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base

        try:
            response = await retry_with_backoff(
                lambda: litellm.aembedding(**kwargs),
                retryable_exceptions=_RETRYABLE,
                max_retries=2,
                base_delay=1.0,
                jitter=0.3,
                description="Embedding",
            )
        except _RETRYABLE as e:
            raise EmbeddingError(f"Embedding API call failed after retries: {e}") from e
        except litellm.APIError as e:
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
