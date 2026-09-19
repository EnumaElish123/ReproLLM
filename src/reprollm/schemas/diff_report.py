"""Semantic drift report, replacing the unreleased M1 placeholder (spec §18.3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .manifest import SchemaVersion
from .profile import DriftSeverity


class DiffSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["run", "lock"]
    ref: str


class DiffChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    status: Literal["changed", "added", "removed"]
    a: Any
    b: Any
    severity: DriftSeverity
    note: str | None = None


class DiffSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    highest: DriftSeverity
    counts: dict[DriftSeverity, int]
    same: int = Field(ge=0)


class DiffReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    reprollm_version: str
    a: DiffSource
    b: DiffSource
    summary: DiffSummary
    changes: list[DiffChange]
    filtered_below: DriftSeverity | None = None
