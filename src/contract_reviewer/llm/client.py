"""LLM client wrapping LiteLLM for unified cloud/local model access."""

import asyncio
import json
import logging
import random
from typing import Any, AsyncIterator

import litellm
from pydantic import BaseModel, ValidationError

from contract_reviewer.llm.cache import ResponseCache
from contract_reviewer.llm.circuit_breaker import CircuitBreaker, CircuitOpenError
from contract_reviewer.llm.retry import retry_with_backoff
from contract_reviewer.utils.hashing import content_sha256
from contract_reviewer.llm.token_budget import TokenBudget
from contract_reviewer.models.config import Settings

logger = logging.getLogger(__name__)

# Default timeout for LLM API calls (seconds)
DEFAULT_TIMEOUT = 120

# Exceptions worth retrying (transient failures)
_RETRYABLE = (litellm.RateLimitError, litellm.APIConnectionError, litellm.Timeout)


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

        # Resilience
        self._max_retries = settings.llm_max_retries
        self._retry_base_delay = settings.llm_retry_base_delay
        self._breaker = CircuitBreaker(
            failure_threshold=settings.llm_circuit_breaker_threshold,
            recovery_timeout=settings.llm_circuit_breaker_recovery,
            name="llm",
        )

        if settings.llm_api_key:
            litellm.api_key = settings.llm_api_key

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    async def _call_with_retry(
        self,
        coro_factory,
        *,
        max_retries: int | None = None,
        base_delay: float | None = None,
    ):
        """Execute *coro_factory()* with exponential back-off on transient errors."""
        retries = max_retries if max_retries is not None else self._max_retries
        delay = base_delay if base_delay is not None else self._retry_base_delay

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                return await self._breaker.call(coro_factory)
            except CircuitOpenError:
                raise  # Don't retry when the breaker is open
            except _RETRYABLE as exc:
                last_error = exc
                if attempt < retries:
                    wait = delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Retry %d/%d after %.1fs: %s",
                        attempt + 1, retries, wait, exc,
                    )
                    await asyncio.sleep(wait)
            except litellm.APIError as exc:
                # Only retry 5xx server errors, not 4xx client errors
                status = getattr(exc, "status_code", None)
                if status and 500 <= status < 600 and attempt < retries:
                    last_error = exc
                    wait = delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Retry %d/%d after %.1fs (server error %s): %s",
                        attempt + 1, retries, wait, status, exc,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise LLMError(f"API error: {exc}") from exc

        raise LLMError(f"Failed after {retries} retries: {last_error}") from last_error

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        # Call LLM with retry, circuit breaker, and token budget tracking
        async with self.token_budget.track(self.max_output_tokens) as recorder:
            try:
                response = await self._call_with_retry(
                    lambda: litellm.acompletion(**call_kwargs)
                )
            except CircuitOpenError as e:
                raise LLMError(f"Circuit breaker open: {e}") from e
            except LLMError:
                raise
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
                response = await self._call_with_retry(
                    lambda: litellm.acompletion(**call_kwargs)
                )
            except CircuitOpenError as e:
                raise LLMError(f"Circuit breaker open: {e}") from e
            except LLMError:
                raise
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

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

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
        return content_sha256(data)
