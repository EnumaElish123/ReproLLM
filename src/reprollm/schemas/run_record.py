"""Run record schema (spec §5): ``.reprollm/runs/<run_id>/run.json`` — runtime truth.

Written by ``reprollm run``; a minimal record with ``status: running`` is written
before the child starts (R-02) and the full record atomically after it exits.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .manifest import SchemaVersion


class RunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class CommandInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argv: list[str]
    cwd: str
    redactions: int = 0


class CodeInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit: str | None = None
    branch: str | None = None
    dirty: bool = False
    modified_count: int = 0
    untracked_count: int = 0
    remote: str | None = None
    patch_sha256: str | None = None
    patch_file: str | None = None


class SecretPresent(BaseModel):
    """Recorded instead of a secret environment variable's value (D-20)."""

    model_config = ConfigDict(extra="forbid")

    present: bool = True


class RunEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    os: str
    platform: Literal["linux", "darwin", "windows"]
    python: str
    hostname_sha256: str
    packages: dict[str, str] = Field(default_factory=dict)
    env: dict[str, str | SecretPresent] = Field(default_factory=dict)
    env_capture: Literal["allowlist", "all"] = "allowlist"


class GpuInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int
    name: str
    memory_mib: int
    uuid_sha256: str


class HardwareInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_count: int
    gpus: list[GpuInfo] = Field(default_factory=list)
    driver: str | None = None
    cuda_driver_max: str | None = None
    source: Literal["nvidia_smi", "unavailable"] = "unavailable"


class SchedulerInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slurm: dict[str, str] | None = None
    pbs: dict[str, str] | None = None
    lsf: dict[str, str] | None = None


class DocumentRef(BaseModel):
    """Reference + snapshot of a persisted document at run time."""

    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    snapshot: str


class RunFileOrigin(str, Enum):
    ARGV = "argv"
    DECLARED = "declared"
    BINDING = "binding"


class RunFileRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size_bytes: int
    origin: RunFileOrigin
    snapshot: str | None = None
    redacted: bool = False


class ObservationSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["cli", "config", "env"]
    key: str
    path: str | None = None


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    source: ObservationSource


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size_bytes: int


class RunRecord(BaseModel):
    """``.reprollm/runs/<run_id>/run.json`` (spec §5)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    reprollm_version: str
    run_id: str
    name: str | None = None
    status: RunStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    exit_code: int | None = None
    command: CommandInfo
    code: CodeInfo = Field(default_factory=CodeInfo)
    environment: RunEnvironment | None = None
    hardware: HardwareInfo | None = None
    scheduler: SchedulerInfo | None = None
    manifest: DocumentRef | None = None
    lock: DocumentRef | None = None
    files: list[RunFileRef] = Field(default_factory=list)
    bindings_observed: dict[str, list[Observation]] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
