"""Config schema (spec §8): ``.reprollm/config.yaml``.

CLI flags override config; config overrides defaults. ``audit.ignore`` entries carry a
mandatory non-empty ``reason`` (D-10).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .manifest import SchemaVersion


class AuditIgnoreEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule: str
    reason: str = Field(min_length=1)


class AuditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fail_on: Literal["critical", "warning", "never"] = "critical"
    ignore: list[AuditIgnoreEntry] = Field(default_factory=list)
    show_passed: bool = False


class RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    env_capture: Literal["allowlist", "all"] = "allowlist"
    capture_output: bool = False
    snapshot_max_bytes: int = Field(default=1_048_576, ge=1)
    extra_env_allowlist: list[str] = Field(default_factory=list)


class DiscoverConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    base_url_env: str = "REPROLLM_LLM_BASE_URL"
    api_key_env: str = "REPROLLM_LLM_API_KEY"
    model_env: str = "REPROLLM_LLM_MODEL"
    max_chars: int = Field(default=60_000, ge=1)
    include: list[str] | None = None
    exclude: list[str] | None = None


class Config(BaseModel):
    """``.reprollm/config.yaml``."""

    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    audit: AuditConfig = Field(default_factory=AuditConfig)
    run: RunConfig = Field(default_factory=RunConfig)
    discover: DiscoverConfig = Field(default_factory=DiscoverConfig)
