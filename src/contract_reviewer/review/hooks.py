"""Review lifecycle hooks — extensibility points for the review pipeline.

Hooks are called at key stages of the review process. Each hook method
is optional (default implementations are no-ops). Exceptions in hooks
are logged but never propagate to the main pipeline.
"""

import logging
from typing import Any, Protocol, runtime_checkable

from contract_reviewer.models.contract import Contract
from contract_reviewer.models.review import DimensionResult, ReviewReport

logger = logging.getLogger(__name__)


@runtime_checkable
class ReviewHook(Protocol):
    """Protocol for review lifecycle hooks."""

    async def on_review_start(self, contract: Contract) -> None:
        """Called before any dimension processing begins."""
        ...

    async def on_dimension_complete(
        self, dimension: str, result: DimensionResult
    ) -> None:
        """Called after each dimension completes (success or failure)."""
        ...

    async def on_report_ready(self, report: ReviewReport) -> None:
        """Called after the final report is assembled, before returning."""
        ...


class BaseHook:
    """Convenience base class with no-op defaults."""

    async def on_review_start(self, contract: Contract) -> None:
        pass

    async def on_dimension_complete(
        self, dimension: str, result: DimensionResult
    ) -> None:
        pass

    async def on_report_ready(self, report: ReviewReport) -> None:
        pass


async def call_hooks(
    hooks: list[Any],
    method_name: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Call *method_name* on each hook, isolating exceptions."""
    for hook in hooks:
        fn = getattr(hook, method_name, None)
        if fn is None:
            continue
        try:
            await fn(*args, **kwargs)
        except Exception as exc:
            logger.warning(
                "Hook %s.%s raised %s: %s",
                type(hook).__name__,
                method_name,
                type(exc).__name__,
                exc,
            )
