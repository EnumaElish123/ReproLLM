"""Internal experiment tree with per-leaf evidence (spec §17, D-27)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunRecord


class Leaf(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    source: Literal["manifest", "lock", "run", "working_tree", "default"]
    detail: str | None = None
    confidence: Literal["exact", "declared", "unresolved", "observed"]
    alternatives: list[Leaf] = Field(default_factory=list)


class Branch(RootModel[dict[str, "Leaf | Branch"]]):
    root: dict[str, Leaf | Branch] = Field(default_factory=dict)


class State(BaseModel):
    """Only experimental values participate in flattening; profiles select policy."""

    model_config = ConfigDict(extra="forbid")

    code: Branch = Field(default_factory=Branch)
    environment: Branch = Field(default_factory=Branch)
    hardware: Branch = Field(default_factory=Branch)
    models: Branch = Field(default_factory=Branch)
    datasets: Branch = Field(default_factory=Branch)
    prompts: Branch = Field(default_factory=Branch)
    files: Branch = Field(default_factory=Branch)
    generation: Branch = Field(default_factory=Branch)
    inference: Branch = Field(default_factory=Branch)
    training: Branch = Field(default_factory=Branch)
    evaluation: Branch = Field(default_factory=Branch)
    privacy: Branch = Field(default_factory=Branch)
    execution: Branch = Field(default_factory=Branch)
    custom: Branch = Field(default_factory=Branch)
    command: Branch = Field(default_factory=Branch)
    run_id: Leaf | None = None
    started_at: Leaf | None = None
    ended_at: Leaf | None = None
    duration_seconds: Leaf | None = None
    profiles: list[str] = Field(default_factory=list)

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> State:
        from reprollm.diff.state import from_manifest

        return from_manifest(manifest)

    @classmethod
    def from_lock(cls, lock: Lock) -> State:
        from reprollm.diff.state import from_lock

        return from_lock(lock)

    @classmethod
    def from_run(cls, run: RunRecord, *, run_dir: Path | None = None) -> State:
        from reprollm.diff.state import from_run

        return from_run(run, run_dir=run_dir)

    @classmethod
    def merge(
        cls,
        manifest: Manifest | State | None = None,
        lock: Lock | State | None = None,
        run: RunRecord | State | None = None,
        *,
        run_dir: Path | None = None,
    ) -> State:
        from reprollm.diff.state import merge

        return merge(manifest, lock, run, run_dir=run_dir)

    @classmethod
    def from_flat(cls, values: dict[str, Leaf], *, profiles: list[str] | None = None) -> State:
        from reprollm.diff.state import from_flat

        return from_flat(values, profiles=profiles)

    def flatten(self) -> dict[str, Leaf]:
        result: dict[str, Leaf] = {}

        def walk(node: Branch | Leaf, path: str) -> None:
            if isinstance(node, Leaf):
                result[path] = node
            else:
                for key, child in sorted(node.root.items()):
                    walk(child, f"{path}.{key}")

        for key in sorted(type(self).model_fields):
            node = getattr(self, key)
            if isinstance(node, (Branch, Leaf)):
                walk(node, key)
        return dict(sorted(result.items()))
