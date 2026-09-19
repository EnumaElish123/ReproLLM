"""Deterministic observations of declared CLI/config/env locations (§15)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from reprollm.core.configread import read_config_value
from reprollm.core.paths import resolve_project_file
from reprollm.core.redaction import is_forbidden_file, is_secret_env_name, redact_text
from reprollm.schemas.manifest import BindingSpec
from reprollm.schemas.project_rules import ProjectRuleBindings, ProjectRules
from reprollm.schemas.run_record import Observation, ObservationSource


def normalize(value: Any) -> Any:
    if isinstance(value, str):
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            try:
                number = float(value)
                return number if math.isfinite(number) else value
            except ValueError:
                return value
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def values_equal(a: Any, b: Any) -> bool:
    a, b = normalize(a), normalize(b)
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, int) and isinstance(b, int):
            return a == b
        return math.isclose(a, b, rel_tol=1e-9)
    return bool(a == b)


def _safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)[0]
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _safe_value(item) for key, item in value.items()}
    return value


def observe(
    bindings: Mapping[str, BindingSpec],
    argv: Sequence[str],
    env: Mapping[str, str],
    root: Path,
    *,
    project_rules: ProjectRules | None = None,
    warnings: list[str] | None = None,
) -> dict[str, list[Observation]]:
    """Keep CLI occurrences in order; add every distinct declared config/env location."""
    warnings = warnings if warnings is not None else []
    combined: dict[str, list[BindingSpec | ProjectRuleBindings]] = {
        field: [binding] for field, binding in bindings.items()
    }
    if project_rules is not None:
        for rule in project_rules.rules:
            if rule.bindings is not None:
                combined.setdefault(rule.field, []).append(rule.bindings)
    observed: dict[str, list[Observation]] = {}
    for field, specs in sorted(combined.items()):
        observations: list[Observation] = []
        flags = sorted({spec.cli for spec in specs if spec.cli})
        for index, token in enumerate(argv):
            for flag in flags:
                value: Any
                if token == flag:
                    value = (
                        argv[index + 1]
                        if index + 1 < len(argv) and not argv[index + 1].startswith("-")
                        else True
                    )
                elif token.startswith(flag + "="):
                    value = token[len(flag) + 1 :]
                else:
                    continue
                observations.append(
                    Observation(
                        value=_safe_value(normalize(value)),
                        source=ObservationSource(type="cli", key=flag),
                    )
                )
        for location in sorted({spec.config for spec in specs if spec.config}):
            relative, separator, key = location.partition(":")
            path = resolve_project_file(root, relative)
            if not separator or not key or path is None:
                warnings.append(
                    f"binding {field}: config path/key unavailable or outside repository"
                )
                continue
            if is_forbidden_file(relative) or is_forbidden_file(path.name):
                warnings.append(f"binding {field}: forbidden config file was not observed")
                continue
            try:
                value = read_config_value(path, key)
            except KeyError:
                warnings.append(f"binding {field}: config key not found")
                continue
            except (OSError, ValueError, yaml.YAMLError) as exc:
                warnings.append(f"binding {field}: cannot read config ({type(exc).__name__})")
                continue
            observations.append(
                Observation(
                    value=_safe_value(normalize(value)),
                    source=ObservationSource(type="config", path=relative, key=key),
                )
            )
        for name in sorted({spec.env for spec in specs if spec.env}):
            if is_secret_env_name(name):
                warnings.append(f"binding {field}: secret environment binding refused")
            elif name in env:
                observations.append(
                    Observation(
                        value=_safe_value(normalize(env[name])),
                        source=ObservationSource(type="env", key=name),
                    )
                )
        if observations:
            observed[field] = observations
    return observed
