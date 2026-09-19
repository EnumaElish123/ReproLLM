"""Ordered drift policy and version-component semantics (spec §18.1–18.2)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files

import yaml
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field

from reprollm.schemas.manifest import SchemaVersion
from reprollm.schemas.profile import DriftSeverity

SEVERITIES: tuple[DriftSeverity, ...] = ("NONE", "LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH")


class DriftRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    severity: DriftSeverity


class SeverityTable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: SchemaVersion = 1
    default: DriftSeverity = "MEDIUM"
    rules: list[DriftRule] = Field(default_factory=list)


@dataclass(frozen=True)
class Resolution:
    severity: DriftSeverity
    note: str | None = None


def matches(pattern: str, path: str) -> bool:
    """A file path is one atomic segment even when it contains dots/slashes."""
    if pattern == "files.*.sha256":
        return path.startswith("files.") and path.endswith(".sha256") and len(path) > 13
    expression = re.escape(pattern).replace(r"\*", r"[^.]+")
    return re.fullmatch(expression, path) is not None


class SeverityResolver:
    def __init__(
        self,
        table: SeverityTable | None = None,
        profile_overrides: Mapping[str, DriftSeverity] | None = None,
    ) -> None:
        if table is None:
            content = files("reprollm.diff").joinpath("drift_severity.yaml").read_text("utf-8")
            table = SeverityTable.model_validate(yaml.safe_load(content))
        self.table = table
        self.rules = [
            DriftRule(path=path, severity=severity)
            for path, severity in (profile_overrides or {}).items()
        ] + table.rules

    def resolve(
        self, path: str, a: object, b: object, *, dirty_a: bool = False, dirty_b: bool = False
    ) -> Resolution:
        severity = next(
            (rule.severity for rule in self.rules if matches(rule.path, path)), self.table.default
        )
        note = None
        if path == "code.commit":
            note = "code changed"
            if dirty_a or dirty_b:
                side = "both" if dirty_a and dirty_b else "a" if dirty_a else "b"
                return Resolution("HIGH", f"working tree was dirty on {side}")
        if (path.startswith("environment.packages.") or path == "inference.version") and (
            isinstance(a, str) and isinstance(b, str)
        ):
            try:
                before, after = Version(a), Version(b)
            except InvalidVersion:
                return Resolution(severity, note)
            if (
                (before.epoch, before.major, before.minor)
                == (after.epoch, after.major, after.minor)
                and before != after
                and severity != "NONE"
            ):
                severity = SEVERITIES[max(1, SEVERITIES.index(severity) - 1)]
        return Resolution(severity, note)
