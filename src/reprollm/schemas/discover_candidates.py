"""Discover candidates schema (spec §20.4)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .manifest import SchemaVersion


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["file", "field", "config", "code"] = "file"
    path: str | None = None
    line: int | None = None
    snippet: str | None = None


class CandidateSuggestedBindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cli: str | None = None
    config: str | None = None
    env: str | None = None


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    kind: Literal["parameter", "dependency", "artifact", "profile"]
    name: str
    suggested_field: str
    suggested_severity: Literal["CRITICAL", "WARNING", "INFO"]
    confidence: Literal["high", "medium", "low"]
    rationale: str
    evidence: list[CandidateEvidence] = Field(default_factory=list)
    suggested_bindings: CandidateSuggestedBindings | None = None


class DiscoverCandidates(BaseModel):
    """``.reprollm/discover/<ts>.json`` (spec §20.4)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    reprollm_version: str
    generated_at: datetime
    model: str
    input_files: list[str] = Field(default_factory=list)
    dropped_files: list[str] = Field(default_factory=list)
    truncated_files: list[str] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)

    def by_id(self, candidate_id: str) -> Candidate | None:
        return next((c for c in self.candidates if c.id == candidate_id), None)


def candidate_id(kind: str, name: str, first_evidence_path: str | None) -> str:
    """``c-`` + first 6 hex of sha256(kind + name + first evidence path)."""
    import hashlib

    digest = hashlib.sha256(f"{kind}{name}{first_evidence_path or ''}".encode())
    return f"c-{digest.hexdigest()[:6]}"
