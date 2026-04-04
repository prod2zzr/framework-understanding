"""Shared exponential backoff retry utility for API calls."""

import asyncio
import logging
import random
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    coro_factory: Callable[[], Awaitable[Any]],
    retryable_exceptions: tuple[type[Exception], ...],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    jitter: float = 0.5,
    description: str = "API call",
) -> Any:
    """Execute *coro_factory()* with exponential backoff on transient errors.

    Args:
        coro_factory: Zero-arg callable returning an awaitable.
        retryable_exceptions: Tuple of exception types that trigger a retry.
        max_retries: Maximum number of retry attempts (0 = no retries).
        base_delay: Base delay in seconds (doubled each retry).
        jitter: Maximum random jitter added to delay.
        description: Label for log messages.

    Returns:
        The result of the coroutine.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except retryable_exceptions as exc:
            last_error = exc
            if attempt < max_retries:
                wait = base_delay * (2 ** attempt) + random.uniform(0, jitter)
                logger.warning(
                    "%s retry %d/%d after %.1fs: %s",
                    description, attempt + 1, max_retries, wait, exc,
                )
                await asyncio.sleep(wait)

    raise last_error  # type: ignore[misc]
