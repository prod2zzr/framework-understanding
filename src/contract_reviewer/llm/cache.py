"""Disk-backed response cache for LLM calls."""

from pathlib import Path
from typing import Any

import diskcache


class ResponseCache:
    """Simple disk cache for LLM responses to avoid redundant API calls."""

    def __init__(self, cache_dir: str, expire: int = 86400):
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(cache_dir)
        self._expire = expire  # Default 24 hours

    def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._cache.set(key, value, expire=self._expire)

    def clear(self) -> None:
        self._cache.clear()
