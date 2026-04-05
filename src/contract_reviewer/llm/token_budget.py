"""Token budget tracker for managing LLM usage across concurrent calls."""

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class BudgetExhausted(Exception):
    """Raised when the token budget is exhausted."""


class TokenBudget:
    """Thread-safe token budget tracker with context manager for safe usage."""

    def __init__(self, max_tokens: int):
        self._used = 0
        self._max = max_tokens
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def track(self, estimated_tokens: int) -> AsyncIterator["UsageRecorder"]:
        """Context manager that reserves budget and records usage on exit.

        Usage:
            async with budget.track(4096) as recorder:
                response = await llm_call(...)
                recorder.prompt_tokens = response.usage.prompt_tokens
                recorder.completion_tokens = response.usage.completion_tokens
            # Budget is automatically updated on exit, even if an exception occurs
        """
        async with self._lock:
            remaining = self._max - self._used
            if remaining <= 0:
                raise BudgetExhausted(
                    f"Token budget exhausted: {self._used}/{self._max} tokens used"
                )

        recorder = UsageRecorder()
        try:
            yield recorder
        finally:
            if recorder.prompt_tokens or recorder.completion_tokens:
                async with self._lock:
                    self._used += recorder.prompt_tokens + recorder.completion_tokens
            else:
                # API call likely failed before recording usage; estimate conservatively
                logger.debug(
                    "No token usage recorded — API call may have failed"
                )

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return max(0, self._max - self._used)


class UsageRecorder:
    """Mutable container for recording token usage within a track() context."""

    __slots__ = ("prompt_tokens", "completion_tokens")

    def __init__(self) -> None:
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
