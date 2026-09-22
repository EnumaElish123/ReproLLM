"""Project current declarations and working files for Level 2 consistency checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from reprollm.core.hashing import sha256_file
from reprollm.diff.state import observed_state
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import Leaf, State


def _working_file(root: Path, relative: str) -> Path | None:
    if (
        not relative
        or relative.startswith(("/", "\\"))
        or "\\" in relative
        or re.match(r"^[A-Za-z]:", relative)
        or ".." in relative.split("/")
    ):
        return None
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _bound_manifest(manifest: Manifest | None, observed: State) -> State | None:
    if manifest is None:
        return None
    declared = State.from_manifest(manifest)
    values = declared.flatten()
    raw = manifest.model_dump(mode="json")
    for field, leaf in observed.flatten().items():
        if leaf.detail is None or leaf.detail.split(":", 1)[0] not in {"cli", "config", "env"}:
            continue
        value: Any = raw
        for part in field.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        # A binding may observe a complete object, including an empty object.
        # Keep that declaration atomic so it compares like the captured value.
        if isinstance(value, dict):
            values = {key: item for key, item in values.items() if not key.startswith(field + ".")}
            values[field] = Leaf(value=value, source="manifest", confidence="declared")
    return State.from_flat(values, profiles=declared.profiles)


def audit_state(
    root: Path, manifest: Manifest | None, lock: Lock | None, run: RunRecord | None
) -> State:
    # Audit compares current intent with observations. Historical snapshots are
    # needed for standalone diff, but must not impersonate current declarations.
    locked = State.from_lock(lock) if lock is not None else State()
    files = locked.flatten()
    working: dict[str, Leaf] = {}
    if lock is not None:
        entries: dict[str, tuple[str, str]] = {}
        for role, prompt in sorted(lock.prompts.items()):
            if prompt.path is not None and prompt.sha256 is not None:
                entries.setdefault(prompt.path, (prompt.sha256, f"prompts.{role}.path"))
        for index, entry in enumerate(lock.files):
            entries.setdefault(entry.path, (entry.sha256, f"files[{index}].path"))
        for relative, (digest, field) in sorted(entries.items()):
            key = f"files.{relative}.sha256"
            files[key] = Leaf(value=digest, source="lock", detail=field, confidence="declared")
            path = _working_file(root, relative)
            value = None
            detail = "invalid" if path is None else "missing"
            if path is not None and path.is_file():
                try:
                    value = sha256_file(path)
                    detail = "working tree hash differs"
                except OSError as exc:
                    detail = f"unreadable:{exc.strerror or type(exc).__name__}"
            working[key] = Leaf(
                value=value, source="working_tree", detail=detail, confidence="observed"
            )
    observed = observed_state(run) if run is not None else State()
    state = State.merge(_bound_manifest(manifest, observed), State.from_flat(files), observed)
    return State.merge(state, State.from_flat(working))
