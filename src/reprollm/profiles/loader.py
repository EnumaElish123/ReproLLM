"""Profile loading and resolution (spec §6, M2-T05).

Built-in profiles ship as packaged YAML under ``reprollm/profiles/``; a user
profile at ``.reprollm/profiles/<name>.yaml`` overrides the built-in of the
same name. ``resolve`` computes the inheritance closure (cycles are a
``UserError``), merges left-to-right with child-wins on overrides, and
validates every referenced rule ID against the registry.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import yaml
from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.registry import known_rule_ids
from reprollm.schemas.profile import AuditSeverity, DetectSignals, DriftSeverity, Profile


class ResolvedProfiles:
    """The effective rule selection after resolving the profile list."""

    def __init__(
        self,
        names: list[str],
        rules: list[str],
        severity_overrides: dict[str, AuditSeverity],
        drift_overrides: dict[str, DriftSeverity],
        required_fields: list[str],
        detect: DetectSignals,
    ) -> None:
        self.names = names
        self.rules = rules
        self.severity_overrides = severity_overrides
        self.drift_overrides = drift_overrides
        self.required_fields = required_fields
        self.detect = detect


def builtin_profile_names() -> list[str]:
    root = files("reprollm.profiles")
    return sorted(
        entry.name[: -len(".yaml")]
        for entry in root.iterdir()
        if entry.is_file() and entry.name.endswith(".yaml")
    )


def user_profile_path(root: Path, name: str) -> Path:
    return root / ".reprollm" / "profiles" / f"{name}.yaml"


def load_builtin(name: str) -> Profile:
    resource = files("reprollm.profiles") / f"{name}.yaml"
    if not resource.is_file():
        known = ", ".join(builtin_profile_names())
        raise UserError(f"unknown profile {name!r} (known profiles: {known})")
    return _parse_profile(str(resource.read_text(encoding="utf-8")), name)


def load_user(root: Path, name: str) -> Profile:
    path = user_profile_path(root, name)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise UserError(f"cannot read user profile {path}: {exc}") from exc
    return _parse_profile(text, name)


def _parse_profile(text: str, name: str) -> Profile:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise UserError(f"invalid profile YAML for {name!r}: {exc}") from exc
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        raise UserError(f"invalid profile {name!r}:\n{exc}") from exc


def load_profile(root: Path, name: str) -> Profile:
    """User profile at ``.reprollm/profiles/<name>.yaml`` overrides the built-in."""
    if user_profile_path(root, name).is_file():
        return load_user(root, name)
    return load_builtin(name)


def known_profile_names(root: Path) -> list[str]:
    """Built-in names plus user overrides, sorted."""
    names = set(builtin_profile_names())
    user_dir = root / ".reprollm" / "profiles"
    if user_dir.is_dir():
        for entry in user_dir.iterdir():
            if entry.is_file() and entry.suffix == ".yaml":
                names.add(entry.stem)
    return sorted(names)


def inheritance_chain(root: Path, name: str) -> list[str]:
    """``name`` followed by its ancestors, ending at ``core`` (cycle-safe)."""
    chain = _closure(root, name, [])
    return chain


def _closure(root: Path, name: str, stack: list[str]) -> list[str]:
    """DFS post-order closure (parents first); raises on cycles."""
    if name in stack:
        cycle = " -> ".join([*stack[stack.index(name) :], name])
        raise UserError(f"profile inheritance cycle: {cycle}")
    profile = load_profile(root, name)
    order: list[str] = []
    seen: set[str] = set()
    for parent in profile.extends:
        for ancestor in _closure(root, parent, [*stack, name]):
            if ancestor not in seen:
                seen.add(ancestor)
                order.append(ancestor)
    if name not in seen:
        order.append(name)
    return order


def resolve(names: list[str], root: Path | None = None) -> ResolvedProfiles:
    """Resolve ``core`` + declared profiles into the effective rule selection."""
    if "core" in names:
        raise UserError(
            "profile 'core' is always included implicitly; "
            "remove it from experiment.profiles / --profiles"
        )
    root = Path.cwd() if root is None else root

    ordered: list[str] = ["core"]
    seen: set[str] = {"core"}
    for name in names:
        for entry in _closure(root, name, []):
            if entry not in seen:
                seen.add(entry)
                ordered.append(entry)

    profiles = [load_profile(root, name) for name in ordered]

    rules: list[str] = []
    required_fields: list[str] = []
    severity_overrides: dict[str, AuditSeverity] = {}
    drift_overrides: dict[str, DriftSeverity] = {}
    detect = DetectSignals()
    for profile in profiles:  # parents first ⇒ child wins on overrides
        for rule_id in profile.rules:
            if rule_id not in rules:
                rules.append(rule_id)
        severity_overrides.update(profile.severity_overrides)
        drift_overrides.update(profile.drift_overrides)
        for field_path in profile.required_fields:
            if field_path not in required_fields:
                required_fields.append(field_path)
        detect.imports.extend(d for d in profile.detect.imports if d not in detect.imports)
        detect.dependencies.extend(
            d for d in profile.detect.dependencies if d not in detect.dependencies
        )
        detect.keywords.extend(k for k in profile.detect.keywords if k not in detect.keywords)
        detect.files.extend(f for f in profile.detect.files if f not in detect.files)

    unknown = sorted(set(rules) - known_rule_ids())
    if unknown:
        raise UserError(
            f"profile references unknown rule IDs: {', '.join(unknown)}; "
            "run `reprollm profiles list` and check the profile YAML"
        )
    return ResolvedProfiles(
        names=ordered,
        rules=sorted(rules),
        severity_overrides=severity_overrides,
        drift_overrides=drift_overrides,
        required_fields=required_fields,
        detect=detect,
    )
