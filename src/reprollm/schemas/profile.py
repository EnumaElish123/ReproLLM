"""Profile schema (spec §6): a YAML bundle of rules, required fields, and overrides."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .manifest import SchemaVersion

#: Profile names share the identifier grammar of role keys (spec §6).
ProfileName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,31}$")]

#: Audit severities a profile may override (D-09).
AuditSeverity = Literal["CRITICAL", "WARNING", "INFO", "PASS"]

#: Drift severities a profile may override (spec §18).
DriftSeverity = Literal["HIGH", "MEDIUM_HIGH", "MEDIUM", "LOW", "NONE"]


class DetectSignals(BaseModel):
    """Deterministic detection signals (spec §13); all lists default to empty."""

    model_config = ConfigDict(extra="forbid")

    imports: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)


class Profile(BaseModel):
    """A profile: rules + required fields + overrides for an experiment type (D-06).

    Merge semantics when ``extends`` is resolved (spec §6): ``rules`` and
    ``required_fields`` union; ``severity_overrides`` / ``drift_overrides`` child wins;
    ``detect`` unions. ``core`` is implicit and MUST NOT be listed in
    ``experiment.profiles``.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    name: ProfileName
    description: str
    extends: list[str] = Field(default_factory=list)
    rules: list[str] = Field(default_factory=list)
    required_fields: list[str] = Field(default_factory=list)
    severity_overrides: dict[str, AuditSeverity] = Field(default_factory=dict)
    drift_overrides: dict[str, DriftSeverity] = Field(default_factory=dict)
    detect: DetectSignals = Field(default_factory=DetectSignals)
