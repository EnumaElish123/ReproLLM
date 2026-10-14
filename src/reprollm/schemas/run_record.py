"""Run record schema (spec §5): ``.reprollm/runs/<run_id>/run.json`` — runtime truth.

Written by ``reprollm run``; a minimal record with ``status: running`` is written
before the child starts (R-02) and the full record atomically after it exits.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reprollm.core.paths import is_relative_project_path


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


class InputFingerprint(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"availability": {"const": "present"}},
                        "required": ["availability"],
                    },
                    "then": {
                        "required": ["sha256", "size_bytes"],
                        "properties": {
                            "sha256": {"not": {"type": "null"}},
                            "size_bytes": {"not": {"type": "null"}},
                        },
                    },
                    "else": {
                        "properties": {"sha256": {"type": "null"}, "size_bytes": {"type": "null"}}
                    },
                }
            ]
        },
    )

    availability: Literal["present", "missing", "unavailable"]
    sha256: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    size_bytes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def fingerprint_matches_availability(self) -> InputFingerprint:
        if self.availability == "present":
            if self.sha256 is None or self.size_bytes is None:
                raise ValueError("present input requires sha256 and size_bytes")
        elif self.sha256 is not None or self.size_bytes is not None:
            raise ValueError("missing/unavailable input cannot carry a fingerprint")
        return self


class InputCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", regex_engine="python-re")

    path: str = Field(
        pattern=r"^(?![/\\])(?![A-Za-z]:)(?![\s\S]*\\)(?![\s\S]*(?:^|/)\.\.(?:/|$))(?=[\s\S]*\S)[\s\S]+$"
    )
    origin: Literal["manifest", "lock", "argv", "declared", "binding"]
    before: InputFingerprint
    after: InputFingerprint
    change: Literal["unchanged", "changed", "removed", "created", "unknown"]

    @model_validator(mode="after")
    def change_matches_fingerprints(self) -> InputCheck:
        if not is_relative_project_path(self.path):
            raise ValueError("input check path must stay relative to the repository")
        before, after = self.before.availability, self.after.availability
        if "unavailable" in (before, after):
            expected = "unknown"
        elif before == "missing" and after == "present":
            expected = "created"
        elif before == "present" and after == "missing":
            expected = "removed"
        elif (
            self.before.sha256 == self.after.sha256
            and self.before.size_bytes == self.after.size_bytes
        ):
            expected = "unchanged"
        else:
            expected = "changed"
        if self.change != expected:
            raise ValueError("input change must agree with before/after fingerprints")
        return self


class InputCapture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_phase: Literal["pre_child"] = "pre_child"
    check_phase: Literal["post_child"] = "post_child"
    consumption: Literal["unverified"] = "unverified"
    checks: list[InputCheck] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_sorted_checks(self) -> InputCapture:
        if len({check.path for check in self.checks}) != len(self.checks):
            raise ValueError("input check paths must be unique")
        self.checks.sort(key=lambda check: check.path)
        return self


class RunRecord(BaseModel):
    """``.reprollm/runs/<run_id>/run.json`` (spec §5)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "allOf": [
                {
                    "if": {
                        "properties": {"schema_version": {"const": 2}},
                        "required": ["schema_version"],
                    },
                    "then": {
                        "required": ["input_capture"],
                        "properties": {"input_capture": {"not": {"type": "null"}}},
                    },
                    "else": {"properties": {"input_capture": {"type": "null"}}},
                }
            ]
        },
    )

    schema_version: Literal[1, 2] = 1
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
    input_capture: InputCapture | None = None

    @model_validator(mode="before")
    @classmethod
    def schema_version_is_integer(cls, value: Any) -> Any:
        if (
            isinstance(value, dict)
            and "schema_version" in value
            and type(value["schema_version"]) is not int
        ):
            raise ValueError("run schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def input_capture_matches_version(self) -> RunRecord:
        if self.schema_version == 2 and self.input_capture is None:
            raise ValueError("schema 2 requires input_capture")
        if self.schema_version == 1 and self.input_capture is not None:
            raise ValueError("schema 1 cannot carry input_capture")
        if self.input_capture is not None:
            checks = {item.path: item.before for item in self.input_capture.checks}
            for reference in [self.manifest, self.lock, *self.files]:
                if reference is None:
                    continue
                baseline = checks.get(reference.path)
                if (
                    baseline is None
                    or baseline.availability != "present"
                    or baseline.sha256 != reference.sha256
                    or (
                        isinstance(reference, RunFileRef)
                        and baseline.size_bytes != reference.size_bytes
                    )
                ):
                    raise ValueError("input reference must match its recorded baseline fingerprint")
        return self
