"""Diff report schema (spec §18.3).

Minimal placeholder for M1 (schema export freshness from week 1); the full report
model arrives with M6 ``reprollm diff``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .manifest import SchemaVersion


class DiffReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    reprollm_version: str
