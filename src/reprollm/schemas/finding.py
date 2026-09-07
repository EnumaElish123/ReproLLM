"""Finding, audit report, and detection result schemas (spec §9, §10, §13)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .manifest import SchemaVersion


class Severity(str, Enum):
    """Audit severities, ordered CRITICAL > WARNING > INFO > PASS (D-09)."""

    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"
    PASS = "PASS"


#: Rank for deterministic sorting; higher = more severe.
SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 3,
    Severity.WARNING: 2,
    Severity.INFO: 1,
    Severity.PASS: 0,
}


class FindingStatus(str, Enum):
    FAIL = "fail"
    PASS = "pass"
    SUPPRESSED = "suppressed"
    SKIPPED = "skipped"


class EvidenceKind(str, Enum):
    FIELD = "field"
    FILE = "file"
    GIT = "git"
    ENV = "env"
    LOCK = "lock"
    RUN = "run"
    DETECTION = "detection"
    HTTP = "http"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: EvidenceKind
    path: str | None = None
    field: str | None = None
    line: int | None = None
    value: Any = None
    expected: Any = None
    note: str | None = None


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    aliases: list[str] = Field(default_factory=list)
    category: str
    severity: Severity
    status: FindingStatus
    level: int = Field(ge=0, le=2)
    message: str
    evidence: list[Evidence] = Field(default_factory=list)
    fix_hint: str
    profile_origin: list[str] = Field(default_factory=list)
    severity_origin: str = "default"
    suppressed_reason: str | None = None


class ProfileDetection(BaseModel):
    """One detected profile; ``shipped=False`` marks report-only profiles
    (rag/agent per spec §13) that cannot be declared in the Beta."""

    model_config = ConfigDict(extra="forbid")

    profile: str
    confidence: Literal["high", "medium", "low"]
    evidence: list[Evidence] = Field(default_factory=list)
    shipped: bool = True


class ProfilesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    declared: list[str] = Field(default_factory=list)
    resolved: list[str] = Field(default_factory=list)
    detected: list[ProfileDetection] = Field(default_factory=list)


class DocumentsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: str | None = None
    lock: str | None = None
    runs: int = 0


class Summary(BaseModel):
    """``pass`` is a Python keyword; the field is ``pass_`` with a ``pass`` alias."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    critical: int = 0
    warning: int = 0
    info: int = 0
    pass_: int = Field(default=0, alias="pass")
    suppressed: int = 0
    skipped: int = 0


class AuditReport(BaseModel):
    """The ``audit --format json`` document (spec §10)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: SchemaVersion = 1
    reprollm_version: str
    generated_at: datetime
    target: str
    level: int = Field(ge=0, le=2)
    profiles: ProfilesSection
    documents: DocumentsSection
    summary: Summary
    findings: list[Finding] = Field(default_factory=list)


# --- Detection result (spec §13) -------------------------------------------


class HfIdHint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    path: str
    line: int


class DetectionHints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: list[str] = Field(default_factory=list)
    backends: list[str] = Field(default_factory=list)
    datasets: bool = False
    adapter: bool = False
    trust_remote_code: bool = False
    hf_ids: list[HfIdHint] = Field(default_factory=list)


class DetectionResult(BaseModel):
    """Output of deterministic profile detection; feeds AuditReport.profiles.detected."""

    model_config = ConfigDict(extra="forbid")

    profiles: list[ProfileDetection] = Field(default_factory=list)
    hints: DetectionHints = Field(default_factory=DetectionHints)
