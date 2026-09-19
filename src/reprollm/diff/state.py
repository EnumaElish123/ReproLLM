"""Project declared, resolved and observed values without losing their sources."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from reprollm.core.errors import UserError
from reprollm.core.paths import resolve_project_file
from reprollm.core.yaml_io import load_lock, load_manifest
from reprollm.schemas.lock import Lock, Provenance
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import Leaf, State

_SECTIONS = (
    "models",
    "datasets",
    "prompts",
    "generation",
    "inference",
    "training",
    "evaluation",
    "privacy",
    "execution",
    "custom",
)


def _plain(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Provenance):
        return _plain(value.value)
    if isinstance(value, BaseModel):
        return {
            key: _plain(getattr(value, key))
            for key in type(value).model_fields
            if getattr(value, key) is not None
        }
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _project(value: Any, path: str, source: Any, result: dict[str, Leaf]) -> None:
    if isinstance(value, Provenance):
        result[path] = Leaf(
            value=value.value, source="lock", detail=value.source, confidence=value.confidence.value
        )
    elif isinstance(value, BaseModel):
        for key in sorted(type(value).model_fields):
            if source == "lock" and key == "observed_at":
                continue
            _project(getattr(value, key), f"{path}.{key}", source, result)
    elif isinstance(value, dict):
        for key, child in sorted(value.items()):
            _project(child, f"{path}.{key}", source, result)
    elif value is not None:
        result[path] = Leaf(
            value=_plain(value),
            source=source,
            confidence="observed" if source == "run" else "declared",
        )


def from_flat(values: dict[str, Leaf], *, profiles: list[str] | None = None) -> State:
    tree: dict[str, Any] = {}
    for path, leaf in sorted(values.items()):
        if path.startswith("files.") and path.endswith(".sha256"):
            parts = ["files", path[len("files.") : -len(".sha256")], "sha256"]
        else:
            parts = path.split(".")
        if parts[0] not in State.model_fields or parts[0] == "profiles" or not all(parts):
            raise UserError("invalid experiment field path; inspect bindings_observed in run.json")
        branch = tree
        for part in parts[:-1]:
            node = branch.setdefault(part, {})
            if not isinstance(node, dict):
                raise UserError("conflicting experiment field paths; inspect bindings_observed")
            branch = node
        if parts[-1] in branch:
            raise UserError("conflicting experiment field paths; inspect bindings_observed")
        branch[parts[-1]] = leaf.model_copy(deep=True)
    return State.model_validate({**tree, "profiles": list(profiles or [])})


def from_manifest(manifest: Manifest) -> State:
    values: dict[str, Leaf] = {}
    for section in _SECTIONS:
        _project(getattr(manifest, section), section, "manifest", values)
    return from_flat(values, profiles=manifest.experiment.profiles)


def from_lock(lock: Lock) -> State:
    values: dict[str, Leaf] = {}
    for section in _SECTIONS:
        _project(getattr(lock, section, None), section, "lock", values)
    if lock.environment is not None:
        for field in ("python", "platform", "packages"):
            _project(getattr(lock.environment, field), f"environment.{field}", "lock", values)
        # Driver expectations and observed hardware must share the same paths.
        _project(lock.environment.gpu, "hardware", "lock", values)
    for file in sorted(lock.files, key=lambda entry: entry.path):
        values[f"files.{file.path}.sha256"] = Leaf(
            value=file.sha256, source="lock", confidence="declared"
        )
    return from_flat(values)


def _snapshots(run: RunRecord, run_dir: Path | None) -> tuple[Manifest | None, Lock | None]:
    documents: dict[str, Any] = {}
    for name, reference, loader in (
        ("manifest", run.manifest, load_manifest),
        ("lock", run.lock, load_lock),
    ):
        if reference is None:
            continue
        if run_dir is None:
            raise UserError(f"{name} snapshot requires the run directory; supply its run.json path")
        path = resolve_project_file(run_dir, reference.snapshot)
        if path is None:
            raise UserError(f"{name} snapshot is missing or outside the run directory; restore it")
        try:
            documents[name] = loader(path)
        except (UserError, ValueError, OSError):
            # Parser errors can echo source secrets and absolute paths.
            raise UserError(f"invalid {name} snapshot; inspect the run directory") from None
    return documents.get("manifest"), documents.get("lock")


def from_run(run: RunRecord, *, run_dir: Path | None = None) -> State:
    manifest, lock = _snapshots(run, run_dir)
    values: dict[str, Leaf] = {}
    raw = run.model_dump(mode="json")
    for section in (
        "code",
        "environment",
        "command",
        "run_id",
        "started_at",
        "ended_at",
        "duration_seconds",
    ):
        _project(raw[section], section, "run", values)
    if run.hardware is not None:
        hardware = run.hardware.model_dump(mode="json", exclude={"gpus"})
        hardware["gpus"] = {
            str(gpu.index): gpu.model_dump(mode="json") for gpu in run.hardware.gpus
        }
        _project(hardware, "hardware", "run", values)
    for file in sorted(run.files, key=lambda entry: entry.path):
        values[f"files.{file.path}.sha256"] = Leaf(
            value=file.sha256, source="run", confidence="observed"
        )
    observations: dict[str, list[Leaf]] = defaultdict(list)
    for field, items in sorted(run.bindings_observed.items()):
        for item in items:
            source = item.source
            location = f"{source.path}:" if source.path else ""
            observations[field].append(
                Leaf(
                    value=item.value,
                    source="run",
                    confidence="observed",
                    detail=f"{source.type}:{location}{source.key}",
                )
            )
    for field, leaves in observations.items():
        if field in values:
            leaves.append(values[field])
        values[field] = _choose(leaves)
    return merge(manifest, lock, from_flat(values))


def _rank(leaf: Leaf) -> int:
    if leaf.source == "run":
        kind = (leaf.detail or "").split(":", 1)[0]
        return {"cli": 9, "config": 8, "env": 7}.get(kind, 6)
    return {"working_tree": 5, "lock": 4, "manifest": 3, "default": 1}[leaf.source]


def _evidence(leaf: Leaf) -> list[Leaf]:
    return [
        leaf.model_copy(update={"alternatives": []}, deep=True),
        *(item for alternative in leaf.alternatives for item in _evidence(alternative)),
    ]


def _choose(leaves: list[Leaf]) -> Leaf:
    candidates = [item for leaf in leaves for item in _evidence(leaf)]
    # Same-rank observations have no specified winner; make their selection
    # independent of mapping/observation order and retain every observation.
    candidates.sort(
        key=lambda leaf: (
            -_rank(leaf),
            leaf.detail or "",
            json.dumps(leaf.value, sort_keys=True, ensure_ascii=False),
        )
    )
    return candidates[0].model_copy(update={"alternatives": candidates[1:]}, deep=True)


def merge(
    manifest: Manifest | State | None = None,
    lock: Lock | State | None = None,
    run: RunRecord | State | None = None,
    *,
    run_dir: Path | None = None,
) -> State:
    states: list[State] = []
    for document in (manifest, lock, run):
        if isinstance(document, State):
            states.append(document)
        elif isinstance(document, Manifest):
            states.append(from_manifest(document))
        elif isinstance(document, Lock):
            states.append(from_lock(document))
        elif isinstance(document, RunRecord):
            states.append(from_run(document, run_dir=run_dir))
    values: dict[str, list[Leaf]] = defaultdict(list)
    profiles: list[str] = []
    for state in states:
        profiles.extend(name for name in state.profiles if name not in profiles)
        for path, leaf in state.flatten().items():
            values[path].append(leaf)
    return from_flat({path: _choose(leaves) for path, leaves in values.items()}, profiles=profiles)
