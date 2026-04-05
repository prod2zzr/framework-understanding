"""Shared JSON Lines writing utility."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def append_jsonl(path: Path, entries: list[dict] | dict) -> None:
    """Append one or more dicts as JSON Lines to *path*.

    Creates parent directories if needed.  Flushes after writing to
    reduce the risk of partial writes on interruption.
    """
    if isinstance(entries, dict):
        entries = [entries]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()
