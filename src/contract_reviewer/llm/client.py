"""LLM client wrapping LiteLLM for unified cloud/local model access."""

import hashlib
import json
from typing import Any, AsyncIterator

import litellm
from pydantic import BaseModel

from contract_reviewer.llm.cache import ResponseCache
from contract_reviewer.llm.token_budget import TokenBudget
from contract_reviewer.models.config import Settings


class LLMClient:
    """Unified LLM client supporting Claude, Ollama, vLLM via LiteLLM."""

    def __init__(self, settings: Settings):
        self.model = settings.llm_model
        self.api_base = settings.llm_api_base
        self.temperature = settings.llm_temperature
        self.max_output_tokens = settings.llm_max_output_tokens
        self.token_budget = TokenBudget(settings.llm_max_total_tokens)
        self.cache = ResponseCache(settings.cache_dir) if settings.cache_enabled else None

        if settings.llm_api_key:
            litellm.api_key = settings.llm_api_key

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel] | None = None,
        **kwargs: Any,
    ) -> str | dict:
        """Send a completion request and return the response.

        If response_model is provided, uses tool_use to get structured output.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Check cache
        if self.cache:
            cache_key = self._cache_key(messages, response_model)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Check token budget
        await self.token_budget.reserve(self.max_output_tokens)

        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            **kwargs,
        }
        if self.api_base:
            call_kwargs["api_base"] = self.api_base

        # Use tool_use for structured output
        if response_model is not None:
            tool_schema = self._pydantic_to_tool(response_model)
            call_kwargs["tools"] = [tool_schema]
            call_kwargs["tool_choice"] = {"type": "function", "function": {"name": tool_schema["function"]["name"]}}

        response = await litellm.acompletion(**call_kwargs)

        # Record token usage
        usage = response.usage
        if usage:
            await self.token_budget.record_usage(
                usage.prompt_tokens or 0, usage.completion_tokens or 0
            )

        # Extract result
        if response_model is not None:
            result = self._extract_tool_result(response)
        else:
            result = response.choices[0].message.content or ""

        # Store in cache
        if self.cache:
            self.cache.set(cache_key, result)

        return result

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream completion tokens."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        await self.token_budget.reserve(self.max_output_tokens)

        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "stream": True,
            **kwargs,
        }
        if self.api_base:
            call_kwargs["api_base"] = self.api_base

        response = await litellm.acompletion(**call_kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    @staticmethod
    def _pydantic_to_tool(model: type[BaseModel]) -> dict:
        """Convert a Pydantic model to an OpenAI-compatible tool schema."""
        schema = model.model_json_schema()
        # Remove $defs and title from top level for cleaner tool schema
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": f"submit_{model.__name__.lower()}",
                "description": f"Submit structured {model.__name__} result",
                "parameters": schema,
            },
        }

    @staticmethod
    def _extract_tool_result(response: Any) -> dict:
        """Extract structured result from a tool_use response."""
        message = response.choices[0].message
        if message.tool_calls:
            args = message.tool_calls[0].function.arguments
            return json.loads(args) if isinstance(args, str) else args
        # Fallback: try to parse content as JSON
        content = message.content or ""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"raw_response": content}

    @staticmethod
    def _cache_key(messages: list[dict], response_model: type | None) -> str:
        """Generate a cache key from messages and model type."""
        data = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        if response_model:
            data += response_model.__name__
        return hashlib.sha256(data.encode()).hexdigest()
