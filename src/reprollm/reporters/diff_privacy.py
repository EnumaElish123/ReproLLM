"""Sanitize report values after comparison, preserving change status and counts."""

from __future__ import annotations

from typing import Any

from reprollm.core.redaction import is_secret_env_name
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.diff_report import DiffReport


def _value(value: Any, privacy: RunPrivacy, key: str = "") -> Any:
    if value is not None and is_secret_env_name(key.replace("-", "_")):
        return "<REDACTED:generic_kv>"
    if isinstance(value, dict):
        return {
            privacy.text(str(name))[0]: _value(item, privacy, str(name))
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [_value(item, privacy) for item in value]
    return privacy.value(value)


def sanitize_report(report: DiffReport, privacy: RunPrivacy) -> DiffReport:
    safe = report.model_copy(deep=True)
    for change in safe.changes:
        key = change.path.rsplit(".", 1)[-1]
        change.a, change.b = _value(change.a, privacy, key), _value(change.b, privacy, key)
    return DiffReport.model_validate(privacy.value(safe))
