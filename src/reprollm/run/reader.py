"""Contained, validated run-record reads for the inspection commands."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.paths import RUNS_DIR, resolve_project_file
from reprollm.schemas.run_record import RunRecord

_RUN_ID = re.compile(r"[0-9]{8}T[0-9]{6}Z-[a-f0-9]{6}\Z")
_PREFIX = re.compile(r"[0-9TZa-f-]+\Z")


def _folders(root: Path) -> list[Path]:
    base = root / RUNS_DIR
    if not base.exists():
        return []
    if not base.is_dir() or not base.resolve().is_relative_to(root.resolve()):
        raise UserError(".reprollm/runs must be a directory inside the repository")
    try:
        return sorted(
            path for path in base.iterdir() if _RUN_ID.fullmatch(path.name) and path.is_dir()
        )
    except OSError as exc:
        raise UserError(f"cannot list .reprollm/runs ({type(exc).__name__})") from None


def _read(root: Path, folder: Path) -> tuple[RunRecord, str]:
    relative = f"{RUNS_DIR}/{folder.name}/run.json"
    path = resolve_project_file(root, relative)
    if path is None:
        raise UserError(f"{relative} is missing or outside the repository")
    try:
        raw = path.read_text(encoding="utf-8")
        record = RunRecord.model_validate_json(raw)
    except (OSError, ValueError, ValidationError) as exc:
        raise UserError(
            f"cannot read {relative} ({type(exc).__name__}); inspect run.json"
        ) from None
    if record.run_id != folder.name:
        raise UserError(f"{relative}: run_id must match its directory name")
    return record, raw


def run_sort_key(record: RunRecord) -> tuple[datetime, str]:
    started = record.started_at or datetime.min.replace(tzinfo=timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return started.astimezone(timezone.utc), record.run_id


def list_runs(root: Path) -> tuple[list[RunRecord], list[str]]:
    records, warnings = [], []
    for folder in _folders(root):
        try:
            record, _ = _read(root, folder)
            records.append(record)
        except UserError as exc:
            warnings.append(str(exc))
    records.sort(key=run_sort_key, reverse=True)
    return records, warnings


def read_run(root: Path, prefix: str) -> tuple[RunRecord, str]:
    if not _PREFIX.fullmatch(prefix):
        raise UserError("RUN_ID must be a run ID or its unique prefix; use `reprollm runs list`")
    matches = [path for path in _folders(root) if path.name.startswith(prefix)]
    if not matches:
        raise UserError("RUN_ID not found; use `reprollm runs list`")
    if len(matches) > 1:
        raise UserError("RUN_ID is ambiguous; supply a longer prefix from `reprollm runs list`")
    return _read(root, matches[0])
