"""Deterministic YAML I/O for persisted documents (spec §0).

Dump rules: 2-space indentation, keys in model-field order (never sorted), unicode
allowed, long lines never folded. Models are dumped in JSON mode so datetimes render
as ISO-8601 UTC ``Z`` timestamps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from reprollm.core.errors import UserError
from reprollm.schemas.manifest import Manifest

#: Very large width so PyYAML never folds long lines (reviewable diffs).
_MAX_WIDTH = 1_000_000


def load_yaml(path: Path) -> dict[str, Any]:
    """Safely load a YAML mapping; an empty file yields ``{}``."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UserError(f"cannot read {path}: {exc.strerror}") from exc
    if not text.strip():
        return {}
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise UserError(f"invalid YAML in {path}: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise UserError(f"{path} must contain a YAML mapping, got {type(data).__name__}")
    return data


def dump_yaml(obj: BaseModel | dict[str, Any]) -> str:
    """Dump a model or mapping deterministically (field order preserved)."""
    data = obj.model_dump(mode="json") if isinstance(obj, BaseModel) else obj
    return yaml.safe_dump(
        data,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=_MAX_WIDTH,
    )


def load_manifest(path: Path) -> Manifest:
    """Load and validate ``reprollm.yaml``; validation errors become UserError (exit 2)."""
    data = load_yaml(path)
    try:
        return Manifest.model_validate(data)
    except ValidationError as exc:
        raise UserError(f"invalid manifest {path}:\n{_format_validation_error(exc)}") from exc


def _format_validation_error(exc: ValidationError) -> str:
    lines: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        message = error["msg"]
        lines.append(f"  {location}: {message}")
    return "\n".join(lines) or "  (no details)"
