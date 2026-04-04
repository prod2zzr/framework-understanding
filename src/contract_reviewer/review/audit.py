"""Immutable audit trail for contract review operations.

Records key events during the review pipeline for traceability.
Outputs as JSON Lines for easy ingestion into log analysis tools.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """A single audit event."""

    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event: str
    dimension: str | None = None
    chunk_index: int | None = None
    detail: dict = Field(default_factory=dict)


class AuditTrail:
    """Collect and persist audit entries for a single review session."""

    def __init__(self, contract_name: str):
        self.contract_name = contract_name
        self.entries: list[AuditEntry] = []

    def log(self, event: str, **kwargs) -> None:
        """Append an audit entry."""
        entry = AuditEntry(event=event, **kwargs)
        self.entries.append(entry)

    def summary(self) -> dict:
        """Return a compact summary suitable for ReviewReport.audit_summary."""
        event_counts: dict[str, int] = {}
        for entry in self.entries:
            event_counts[entry.event] = event_counts.get(entry.event, 0) + 1

        llm_calls = [e for e in self.entries if e.event == "llm_call"]
        total_prompt_tokens = sum(e.detail.get("prompt_tokens", 0) for e in llm_calls)
        total_completion_tokens = sum(e.detail.get("completion_tokens", 0) for e in llm_calls)
        cache_hits = sum(1 for e in llm_calls if e.detail.get("cached", False))

        return {
            "contract_name": self.contract_name,
            "total_events": len(self.entries),
            "event_counts": event_counts,
            "llm_calls": len(llm_calls),
            "cache_hits": cache_hits,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
        }

    def save(self, path: Path) -> None:
        """Write audit trail as JSON Lines file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for entry in self.entries:
                line = json.dumps(
                    {"contract": self.contract_name, **entry.model_dump()},
                    ensure_ascii=False,
                )
                f.write(line + "\n")
        logger.info("Audit trail written to %s (%d entries)", path, len(self.entries))

    def to_json(self) -> str:
        """Serialize all entries as a JSON array."""
        return json.dumps(
            [{"contract": self.contract_name, **e.model_dump()} for e in self.entries],
            ensure_ascii=False,
            indent=2,
        )
