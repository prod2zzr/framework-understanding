"""LLM client wrapping LiteLLM for unified cloud/local model access."""

import hashlib
import json
import logging
from typing import Any, AsyncIterator

import litellm
from pydantic import BaseModel, ValidationError

from contract_reviewer.llm.cache import ResponseCache
from contract_reviewer.llm.token_budget import TokenBudget
from contract_reviewer.models.config import Settings

logger = logging.getLogger(__name__)

# Default timeout for LLM API calls (seconds)
DEFAULT_TIMEOUT = 120


class LLMError(Exception):
    """Raised when an LLM call fails after exhausting retries."""


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
        Raises LLMError on unrecoverable failures.
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

        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "timeout": DEFAULT_TIMEOUT,
            **kwargs,
        }
        if self.api_base:
            call_kwargs["api_base"] = self.api_base

        # Use tool_use for structured output
        if response_model is not None:
            tool_schema = self._pydantic_to_tool(response_model)
            call_kwargs["tools"] = [tool_schema]
            call_kwargs["tool_choice"] = {"type": "function", "function": {"name": tool_schema["function"]["name"]}}

        # Call LLM with token budget tracking
        async with self.token_budget.track(self.max_output_tokens) as recorder:
            try:
                response = await litellm.acompletion(**call_kwargs)
            except litellm.RateLimitError as e:
                raise LLMError(f"Rate limit exceeded: {e}") from e
            except litellm.APIConnectionError as e:
                raise LLMError(f"API connection failed: {e}") from e
            except litellm.Timeout as e:
                raise LLMError(f"API call timed out after {DEFAULT_TIMEOUT}s: {e}") from e
            except litellm.APIError as e:
                raise LLMError(f"API error: {e}") from e
            except Exception as e:
                raise LLMError(f"Unexpected LLM error: {e}") from e

            # Record token usage
            usage = getattr(response, "usage", None)
            if usage:
                recorder.prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                recorder.completion_tokens = getattr(usage, "completion_tokens", 0) or 0

        # Extract result safely
        result = self._extract_result(response, response_model)

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
        """Stream completion tokens. Raises LLMError on failure."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        call_kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "stream": True,
            "timeout": DEFAULT_TIMEOUT,
            **kwargs,
        }
        if self.api_base:
            call_kwargs["api_base"] = self.api_base

        async with self.token_budget.track(self.max_output_tokens) as recorder:
            try:
                response = await litellm.acompletion(**call_kwargs)
            except (litellm.RateLimitError, litellm.APIConnectionError,
                    litellm.Timeout, litellm.APIError) as e:
                raise LLMError(f"Streaming LLM call failed: {e}") from e
            except Exception as e:
                raise LLMError(f"Unexpected streaming error: {e}") from e

            async for chunk in response:
                choices = getattr(chunk, "choices", None)
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                if delta and getattr(delta, "content", None):
                    yield delta.content

                # Try to capture usage from final chunk
                usage = getattr(chunk, "usage", None)
                if usage:
                    recorder.prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                    recorder.completion_tokens = getattr(usage, "completion_tokens", 0) or 0

    def _extract_result(self, response: Any, response_model: type[BaseModel] | None) -> str | dict:
        """Safely extract result from an LLM response."""
        choices = getattr(response, "choices", None)
        if not choices:
            logger.warning("LLM response has no choices")
            return {"raw_response": ""} if response_model else ""

        message = choices[0].message

        if response_model is not None:
            return self._extract_tool_result(message)
        return getattr(message, "content", "") or ""

    @staticmethod
    def _pydantic_to_tool(model: type[BaseModel]) -> dict:
        """Convert a Pydantic model to an OpenAI-compatible tool schema."""
        schema = model.model_json_schema()
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
    def _extract_tool_result(message: Any) -> dict:
        """Extract structured result from a tool_use response with defensive checks."""
        # Try tool_calls first
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls and len(tool_calls) > 0:
            func = getattr(tool_calls[0], "function", None)
            if func:
                args = getattr(func, "arguments", None)
                if args:
                    try:
                        return json.loads(args) if isinstance(args, str) else args
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse tool_call arguments: %s", args[:200])

        # Fallback: try to parse content as JSON
        content = getattr(message, "content", "") or ""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("LLM returned non-JSON content, wrapping as raw_response")
            return {"raw_response": content}

    def _cache_key(self, messages: list[dict], response_model: type | None) -> str:
        """Generate a cache key from messages, model, and response type."""
        data = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        # Include model identifier so switching models invalidates cache
        data += f"|model={self.model}|temp={self.temperature}"
        if response_model:
            data += f"|schema={response_model.__name__}"
        return hashlib.sha256(data.encode()).hexdigest()
