"""Profile loading (spec §6).

Minimal M1 version: load built-in profiles from the packaged YAML, resolve the
implicit ``core`` plus the declared names, and validate rule IDs against the
registry. Inheritance (``extends``), user overrides, and merge semantics arrive
in M2-T05.
"""

from __future__ import annotations

from importlib.resources import files

import yaml
from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.registry import known_rule_ids
from reprollm.schemas.profile import AuditSeverity, Profile


class ResolvedProfiles:
    """The effective rule selection after resolving the profile list."""

    def __init__(
        self,
        names: list[str],
        rules: list[str],
        severity_overrides: dict[str, AuditSeverity],
        required_fields: list[str],
    ) -> None:
        self.names = names
        self.rules = rules
        self.severity_overrides = severity_overrides
        self.required_fields = required_fields


def builtin_profile_names() -> list[str]:
    root = files("reprollm.profiles")
    return sorted(
        entry.name[: -len(".yaml")]
        for entry in root.iterdir()
        if entry.is_file() and entry.name.endswith(".yaml")
    )


def load_builtin(name: str) -> Profile:
    resource = files("reprollm.profiles") / f"{name}.yaml"
    if not resource.is_file():
        known = ", ".join(builtin_profile_names())
        raise UserError(f"unknown profile {name!r} (known profiles: {known})")
    try:
        data = yaml.safe_load(resource.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise UserError(f"invalid profile YAML for {name!r}: {exc}") from exc
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        raise UserError(f"invalid profile {name!r}:\n{exc}") from exc


def resolve(names: list[str]) -> ResolvedProfiles:
    """Resolve ``core`` + declared profiles into the effective rule selection."""
    if "core" in names:
        raise UserError(
            "profile 'core' is always included implicitly; "
            "remove it from experiment.profiles / --profiles"
        )
    ordered: list[str] = ["core"]
    profiles: list[Profile] = [load_builtin("core")]
    seen: set[str] = {"core"}
    for name in names:
        if name in seen:
            continue
        profile = load_builtin(name)
        seen.add(name)
        ordered.append(name)
        profiles.append(profile)

    rules: list[str] = []
    severity_overrides: dict[str, AuditSeverity] = {}
    required_fields: list[str] = []
    for profile in profiles:
        for rule_id in profile.rules:
            if rule_id not in rules:
                rules.append(rule_id)
        # Child (later, more derived) profiles win.
        severity_overrides.update(profile.severity_overrides)
        for field_path in profile.required_fields:
            if field_path not in required_fields:
                required_fields.append(field_path)

    unknown = sorted(set(rules) - known_rule_ids())
    if unknown:
        raise UserError(
            f"profile references unknown rule IDs: {', '.join(unknown)}; "
            "run `reprollm rules list` to see registered rules"
        )
    return ResolvedProfiles(ordered, sorted(rules), severity_overrides, required_fields)
