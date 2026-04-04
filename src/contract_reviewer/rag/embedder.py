"""Embedding abstraction supporting cloud and local models."""

import asyncio
import logging
import random

import litellm

from contract_reviewer.models.config import Settings

logger = logging.getLogger(__name__)

# Maximum texts per embedding API call
MAX_BATCH_SIZE = 96
# Timeout for embedding calls (seconds)
EMBED_TIMEOUT = 60
# Retry defaults for embedding calls
_MAX_RETRIES = 2
_RETRY_BASE_DELAY = 1.0


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
        """Embed a single batch of texts with exponential backoff retry."""
        kwargs = {
            "model": self.model,
            "input": texts,
            "timeout": EMBED_TIMEOUT,
        }
        if self.api_base:
            kwargs["api_base"] = self.api_base

        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await litellm.aembedding(**kwargs)
                data = getattr(response, "data", None)
                if not data:
                    raise EmbeddingError("Embedding response has no data")
                return [item["embedding"] for item in data]
            except (litellm.APIConnectionError, litellm.Timeout, litellm.RateLimitError) as e:
                last_error = e
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.3)
                    logger.warning(
                        "Embedding retry %d/%d after %.1fs: %s",
                        attempt + 1, _MAX_RETRIES, wait, e,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise EmbeddingError(
                        f"Embedding API call failed after {_MAX_RETRIES} retries: {e}"
                    ) from e
            except litellm.APIError as e:
                raise EmbeddingError(f"Embedding API call failed: {e}") from e
            except Exception as e:
                raise EmbeddingError(f"Unexpected embedding error: {e}") from e

        raise EmbeddingError(f"Embedding failed: {last_error}") from last_error

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text."""
        results = await self.embed([text])
        return results[0]
