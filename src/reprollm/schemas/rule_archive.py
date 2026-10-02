"""Immutable recovery copies, independent of the project-rules v1 schema (UX2-T06)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from reprollm.schemas.manifest import SchemaVersion
from reprollm.schemas.project_rules import ProjectRule

ArchiveId = Annotated[str, StringConstraints(pattern=r"^ra-[0-9a-f]{16}$")]


class RuleArchive(BaseModel):
    """A saved rule, not proof that deactivation completed successfully."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    archive_id: ArchiveId
    archived_at: datetime
    reason: str = Field(min_length=1)
    rule: ProjectRule

    @field_validator("reason")
    @classmethod
    def _nonempty_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("archive reason must be non-empty")
        return value

    @field_validator("archived_at")
    @classmethod
    def _aware_timestamp(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("archived_at must include a timezone")
        return value

    def content_id(self) -> str:
        """Detect mismatched names or edited recovery content before restoring it."""
        payload = self.model_dump(mode="json", exclude={"archive_id"})
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "ra-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
