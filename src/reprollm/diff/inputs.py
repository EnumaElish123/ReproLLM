"""Read-only input resolution at the diff filesystem boundary (§18)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reprollm.core.errors import UserError
from reprollm.core.paths import RUNS_DIR, resolve_project_file
from reprollm.core.yaml_io import load_lock, load_manifest
from reprollm.run.reader import read_run
from reprollm.schemas.diff_report import DiffSource
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import State


@dataclass(frozen=True)
class DiffInput:
    state: State
    source: DiffSource


def _reference(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        # Explicit external inputs are supported, but host paths never persist.
        return path.name


def load_input(value: str, root: Path) -> DiffInput:
    path = Path(value)
    if not path.exists():
        if "/" in value or "\\" in value or "." in value:
            raise UserError("diff input is missing; supply a run.json, run directory or lock file")
        record, _ = read_run(root, value)
        folder = root / RUNS_DIR / record.run_id
        return DiffInput(
            State.from_run(record, run_dir=folder), DiffSource(kind="run", ref=record.run_id)
        )
    try:
        path = path.resolve()
        if path.is_dir():
            contained = resolve_project_file(path, "run.json")
            if contained is None:
                raise UserError("run directory must contain run.json inside that directory")
            path = contained
        if path.suffix == ".json":
            record = RunRecord.model_validate_json(path.read_text(encoding="utf-8"))
            return DiffInput(
                State.from_run(record, run_dir=path.parent),
                DiffSource(kind="run", ref=_reference(path, root)),
            )
        lock = load_lock(path)
        manifest_path = path.parent / "reprollm.yaml"
        manifest = None
        if manifest_path.exists():
            contained = resolve_project_file(path.parent, "reprollm.yaml")
            if contained is None:
                raise UserError("reprollm.yaml must be inside the lock directory")
            manifest = load_manifest(contained)
        return DiffInput(
            State.merge(manifest, lock), DiffSource(kind="lock", ref=_reference(path, root))
        )
    except (OSError, ValueError, UserError):
        raise UserError(
            "cannot load diff input or its snapshots; inspect run.json/reprollm.lock "
            "and adjacent documents (schema_version 1)"
        ) from None
