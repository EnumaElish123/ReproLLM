"""SHA-256 helpers (spec §0): lowercase hex, ``sha256:`` prefixed."""

from __future__ import annotations

import hashlib
from pathlib import Path

#: Default read chunk for file hashing (1 MiB).
CHUNK_SIZE = 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path, chunk_size: int = CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def is_text_file(path: Path, max_bytes: int) -> bool:
    """Heuristic: UTF-8 decodable within ``max_bytes`` and free of NUL bytes."""
    try:
        with path.open("rb") as handle:
            head = handle.read(max_bytes)
    except OSError:
        return False
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
