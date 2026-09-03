"""Discover candidates schema (spec §20.4).

Minimal placeholder for M1 (schema export freshness from week 1); the full model
arrives with M7 ``reprollm discover``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .manifest import SchemaVersion


class DiscoverCandidates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    reprollm_version: str
