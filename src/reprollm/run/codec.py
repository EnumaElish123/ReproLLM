"""Decode saved run records without exposing their payload in diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.schemas.run_record import RunRecord


class RunRecordError(UserError):
    """A safe run-decoding error that input loaders must retain."""


def parse_run_record(raw: str) -> RunRecord:
    """Reject newer versions before validating fields unknown to this reader."""
    try:
        data = json.loads(raw)
    except ValueError:
        raise RunRecordError("cannot read run.json (invalid JSON); inspect run.json") from None
    if isinstance(data, dict):
        version = data.get("schema_version")
        if "schema_version" in data and type(version) is not int:
            raise RunRecordError("run.json schema_version must be an integer; inspect run.json")
        if type(version) is int and version > 1:
            raise RunRecordError(
                f"run.json uses newer schema_version {version}; upgrade ReproLLM before reading it"
            )
    try:
        return RunRecord.model_validate(data)
    except ValidationError:
        raise RunRecordError("cannot read run.json (ValidationError); inspect run.json") from None


def read_run_record(path: Path) -> tuple[RunRecord, str]:
    """Read an already selected path; callers own containment and run-ID checks."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RunRecordError(
            f"cannot read run.json ({type(exc).__name__}); inspect run.json"
        ) from None
    return parse_run_record(raw), raw
