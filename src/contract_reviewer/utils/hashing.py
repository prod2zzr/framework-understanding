"""Unified SHA-256 hashing utilities for files and content."""

import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    """Stream-hash a file in 8 KiB chunks to keep memory bounded."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def content_sha256(data: str | bytes) -> str:
    """Hash a string or bytes blob."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()
