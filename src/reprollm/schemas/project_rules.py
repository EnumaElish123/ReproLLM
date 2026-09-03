"""Project rules schema (spec §7): user-accepted repository-specific rules."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from .manifest import SchemaVersion, validate_field_path

ProjectRuleId = Annotated[str, StringConstraints(pattern=r"^project\.[a-z][a-z0-9_]{0,47}$")]


class ProjectRuleBindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cli: str | None = None
    config: str | None = None
    env: str | None = None


class ProjectRule(BaseModel):
    """One accepted rule; FAIL when ``field`` is absent/null in the manifest."""

    model_config = ConfigDict(extra="forbid")

    id: ProjectRuleId
    field: str
    severity: Literal["CRITICAL", "WARNING", "INFO"]
    reason: str = Field(min_length=1)
    source: Literal["manual", "discover"]
    candidate_id: str | None = None
    accepted_at: datetime
    bindings: ProjectRuleBindings | None = None

    @model_validator(mode="after")
    def _check_field_path(self) -> ProjectRule:
        if self.field == "custom" or self.field.startswith("custom."):
            return self
        try:
            validate_field_path(self.field)
        except ValueError as exc:
            raise ValueError(f"rule {self.id}: field {self.field!r}: {exc}") from exc
        return self

    @model_validator(mode="after")
    def _check_candidate(self) -> ProjectRule:
        if self.source == "discover" and not self.candidate_id:
            raise ValueError(
                f"rule {self.id}: source 'discover' requires a candidate_id "
                "(accepted via `reprollm rules accept`)"
            )
        return self


class IgnoredCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    ignored_at: datetime
    reason: str | None = None


class ProjectRules(BaseModel):
    """``.reprollm/project-rules.yaml``."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    rules: list[ProjectRule] = Field(default_factory=list)
    ignored_candidates: list[IgnoredCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_unique_ids(self) -> ProjectRules:
        seen: set[str] = set()
        for rule in self.rules:
            if rule.id in seen:
                raise ValueError(f"duplicate project rule id {rule.id!r}")
            seen.add(rule.id)
        return self
