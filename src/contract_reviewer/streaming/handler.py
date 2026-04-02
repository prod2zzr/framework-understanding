"""Server-Sent Events handler for streaming review progress."""

import json
from collections.abc import AsyncIterator

from contract_reviewer.models.progress import ProgressEvent


async def progress_to_sse(events: AsyncIterator[ProgressEvent]) -> AsyncIterator[str]:
    """Convert progress events to SSE format."""
    async for event in events:
        data = json.dumps(event.model_dump(), ensure_ascii=False)
        yield f"event: {event.status}\ndata: {data}\n\n"
    yield "event: done\ndata: {}\n\n"
