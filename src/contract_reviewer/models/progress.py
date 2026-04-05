"""Progress tracking models."""

from pydantic import BaseModel


class ProgressEvent(BaseModel):
    """Event emitted during review to track progress."""

    dimension: str
    status: str  # "started", "chunk_complete", "completed", "error"
    chunk_index: int | None = None
    total_chunks: int | None = None
    message: str = ""
