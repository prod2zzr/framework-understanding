"""Circuit breaker pattern for LLM and embedding API calls.

Four-state model:
- CLOSED: Normal operation, requests pass through.
- OPEN: Too many consecutive failures — fail fast without calling the API.
- HALF_OPEN: Recovery timeout expired — exactly one probe is allowed.
- PROBING: A probe request is in-flight; other callers are rejected.
"""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit breaker is OPEN."""


class CircuitBreaker:
    """Protect downstream services from cascading failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self._state: str = "CLOSED"
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    async def call(
        self,
        coro_factory: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Execute *coro_factory()* through the circuit breaker.

        *coro_factory* is a zero-arg callable that returns an awaitable so
        that the coroutine is only created when the breaker decides to let
        the request through.
        """
        is_probe = False
        async with self._lock:
            if self._state == "CLOSED":
                pass  # Allow through
            elif self._state == "OPEN":
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    # Transition to PROBING — only this coroutine gets through
                    self._state = "PROBING"
                    is_probe = True
                    logger.info("[%s] Circuit breaker PROBING — sending probe", self.name)
                else:
                    raise CircuitOpenError(
                        f"[{self.name}] Circuit breaker OPEN "
                        f"(failures={self._failure_count}, "
                        f"retry in {self.recovery_timeout - (time.monotonic() - self._last_failure_time):.0f}s)"
                    )
            elif self._state in ("HALF_OPEN", "PROBING"):
                # Another coroutine is already probing — reject
                raise CircuitOpenError(
                    f"[{self.name}] Circuit breaker {self._state} — probe in progress"
                )

        try:
            result = await coro_factory()
        except Exception:
            await self._on_failure(is_probe)
            raise
        else:
            await self._on_success(is_probe)
            return result

    async def _on_success(self, was_probe: bool = False) -> None:
        async with self._lock:
            self._failure_count = 0
            if was_probe or self._state == "PROBING":
                logger.info("[%s] Circuit breaker CLOSED — probe succeeded", self.name)
            self._state = "CLOSED"

    async def _on_failure(self, was_probe: bool = False) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if was_probe or self._state == "PROBING":
                self._state = "OPEN"
                logger.warning(
                    "[%s] Circuit breaker OPEN — probe failed", self.name
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning(
                    "[%s] Circuit breaker OPEN — %d consecutive failures",
                    self.name,
                    self._failure_count,
                )

    async def reset(self) -> None:
        """Manually reset the breaker to CLOSED."""
        async with self._lock:
            self._state = "CLOSED"
            self._failure_count = 0
