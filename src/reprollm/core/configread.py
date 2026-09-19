"""Read explicitly declared YAML/JSON/TOML binding locations (§15.1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from reprollm.core._toml import tomllib


def read_config_value(path: Path, dotted_key: str) -> Any:
    suffix = path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json", ".toml"}:
        raise ValueError("binding config must use YAML, JSON or TOML")
    text = path.read_text(encoding="utf-8")
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
