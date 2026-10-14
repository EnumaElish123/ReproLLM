"""Read explicitly declared YAML/JSON/TOML binding locations (§15.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from reprollm.core._toml import tomllib

MAX_CONFIG_BYTES = 2 * 1024 * 1024


def read_config_value(path: Path, dotted_key: str) -> Any:
    with path.open("rb") as handle:
        data = handle.read(MAX_CONFIG_BYTES + 1)
    return read_config_bytes(data, path.suffix, dotted_key)


def read_config_bytes(data: bytes, suffix: str, dotted_key: str) -> Any:
    """Parse original bounded bytes; a redacted copy is never a config source."""
    if len(data) > MAX_CONFIG_BYTES:
        raise ValueError("binding config exceeds 2 MiB")
    suffix = suffix.lower()
    if suffix not in {".yaml", ".yml", ".json", ".toml"}:
        raise ValueError("binding config must use YAML, JSON or TOML")
    text = data.decode("utf-8")
    if suffix == ".json":
        value = json.loads(text)
    elif suffix == ".toml":
        value = tomllib.loads(text)
    else:
        value = yaml.safe_load(text)
    if not dotted_key:
        raise KeyError(dotted_key)
    try:
        for segment in dotted_key.split("."):
            if isinstance(value, dict):
                value = value[segment]
            elif isinstance(value, list):
                value = value[int(segment)]
            else:
                raise KeyError(dotted_key)
    except (KeyError, IndexError, ValueError):
        raise KeyError(dotted_key) from None
    return value
