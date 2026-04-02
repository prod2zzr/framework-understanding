"""Embedding abstraction supporting cloud and local models."""

import litellm

from contract_reviewer.models.config import Settings


class Embedder:
    """Generate embeddings via LiteLLM (supports OpenAI, Ollama, etc.)."""

    def __init__(self, settings: Settings):
        self.model = settings.embedding_model
        self.api_base = settings.embedding_api_base

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        kwargs = {"model": self.model, "input": texts}
        if self.api_base:
            kwargs["api_base"] = self.api_base

        response = await litellm.aembedding(**kwargs)
        return [item["embedding"] for item in response.data]

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text."""
        results = await self.embed([text])
        return results[0]
