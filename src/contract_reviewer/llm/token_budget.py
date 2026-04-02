"""Token budget tracker for managing LLM usage across concurrent calls."""

import asyncio


class BudgetExhausted(Exception):
    """Raised when the token budget is exhausted."""


class TokenBudget:
    """Thread-safe token budget tracker."""

    def __init__(self, max_tokens: int):
        self._used = 0
        self._max = max_tokens
        self._lock = asyncio.Lock()

    async def reserve(self, estimated_tokens: int) -> int:
        """Reserve tokens for an upcoming call. Returns actual tokens allowed."""
        async with self._lock:
            remaining = self._max - self._used
            if remaining <= 0:
                raise BudgetExhausted(
                    f"Token budget exhausted: {self._used}/{self._max} tokens used"
                )
            allowed = min(estimated_tokens, remaining)
            return allowed

    async def record_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Record actual token usage from an API response."""
        async with self._lock:
            self._used += prompt_tokens + completion_tokens

    @property
    def used(self) -> int:
        return self._used

    @property
    def remaining(self) -> int:
        return max(0, self._max - self._used)
