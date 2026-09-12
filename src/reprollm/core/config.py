"""Load tool configuration with concise diagnostics (spec §8, M3-T07)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.paths import CONFIG
from reprollm.core.yaml_io import load_yaml
from reprollm.schemas.config import Config


def load_config(root: Path) -> Config:
    """Return defaults when absent; invalid configuration is a usage error."""
    path = root / CONFIG
    if not path.exists() and not path.is_symlink():
        return Config()
    try:
        data = load_yaml(path)
    except UnicodeError:
        raise UserError(f"{CONFIG} must contain UTF-8 YAML text; save it as UTF-8.") from None
    except UserError as exc:
        cause = exc.__cause__
        if isinstance(cause, yaml.YAMLError):
            # PyYAML exception strings include source lines, which may contain secrets.
            mark = getattr(cause, "problem_mark", None)
            position = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
            message = f"invalid YAML in {CONFIG}{position}; correct the YAML syntax."
        elif isinstance(cause, OSError):
            message = f"cannot read {CONFIG}; check that it is a readable regular file."
        else:
            message = f"{CONFIG} must contain a YAML mapping."
        raise UserError(message) from None

    try:
        return Config.model_validate(data)
    except ValidationError as exc:
        lines: list[str] = []
        for error in exc.errors(include_url=False, include_context=False, include_input=False):
            location = error["loc"]
            field = ".".join(str(part) for part in location) or "<root>"
            rule = _ignore_rule(data, location)
            label = f"{field} (rule {rule})" if rule is not None else field
            lines.append(f"  {label}: {error['msg']}")
        raise UserError(f"invalid config {CONFIG}:\n" + "\n".join(lines)) from None


def _ignore_rule(data: dict[str, Any], location: tuple[str | int, ...]) -> str | None:
    """Identify an invalid suppression without echoing its enclosing config data."""
    if len(location) < 3 or location[:2] != ("audit", "ignore"):
        return None
    audit = data.get("audit")
    if not isinstance(audit, dict):
        return None
    entries = audit.get("ignore")
    index = location[2]
    if not isinstance(entries, list) or not isinstance(index, int) or index >= len(entries):
        return None
    entry = entries[index]
    if not isinstance(entry, dict):
        return None
    rule = entry.get("rule")
    return rule if isinstance(rule, str) else None
