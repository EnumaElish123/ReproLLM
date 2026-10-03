"""Bounded, read-only preview of declared capture locations (spec §5.2)."""

from __future__ import annotations

import getpass
import json
import os
import re
import socket
import stat
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, TypeVar

import yaml
from pydantic import BaseModel

from reprollm.core._toml import tomllib
from reprollm.core.errors import UserError
from reprollm.core.hashing import sha256_bytes
from reprollm.core.paths import CONFIG, LOCK, MANIFEST, PROJECT_RULES, resolve_project_file
from reprollm.core.redaction import is_forbidden_file, is_secret_env_name
from reprollm.run.capture import FileRef, declared_files, resolve_argv_files
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.config import Config
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import BindingSpec, Manifest
from reprollm.schemas.project_rules import ProjectRuleBindings, ProjectRules
from reprollm.schemas.run_record import RunFileOrigin

MAX_BYTES = 2 * 1024 * 1024
Document = TypeVar("Document", bound=BaseModel)
_ADVISORY_ROOTS = (
    "generation",
    "evaluation.judge.params",
    "inference.params",
    "training.params",
    "privacy.mechanism.params",
    "privacy.attack.params",
    "custom",
)


def _root(cwd: Path) -> Path:
    for parent in (cwd, *cwd.parents):
        candidate = parent / MANIFEST
        if candidate.exists() or candidate.is_symlink():
            return parent
    raise UserError("run --dry-run requires reprollm.yaml; run `reprollm init` first")


def _read(path: Path) -> bytes | None:
    """Read bounded regular files without assuming the earlier stat stays valid."""
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("not a regular file")
        if before.st_size > MAX_BYTES:
            return None
        data = handle.read(MAX_BYTES)
        if os.fstat(handle.fileno()).st_size > MAX_BYTES:
            return None
        return data


def _document(
    root: Path, name: str, model: type[Document], read: Callable[[Path], bytes | None]
) -> tuple[Document | None, bytes | None]:
    candidate = root / name
    if not candidate.exists() and not candidate.is_symlink():
        return None, None
    path = resolve_project_file(root, name)
    if path is None or is_forbidden_file(name) or is_forbidden_file(path.name):
        raise UserError(
            f"{name} must be a permitted regular file inside the repository; fix this file"
        )
    try:
        data = read(path)
        if data is None:
            raise UserError(f"{name} exceeds the 2 MiB preflight limit; reduce this file")
        loaded = yaml.safe_load(data.decode("utf-8"))
        parsed = model.model_validate({} if loaded is None else loaded)
    except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
        raise UserError(
            f"cannot read {name} ({type(exc).__name__}); repair this file or upgrade "
            "ReproLLM for a newer schema_version"
        ) from None
    return parsed, data


def _safe(privacy: RunPrivacy, value: str) -> str:
    text = privacy.text(value)[0]
    # Field labels may concatenate a dotted schema prefix with a user-supplied
    # absolute path; the general privacy layer treats that dot as a path prefix.
    text = re.sub(
        r"(?<=\.)/[^\s\"'<>;,\)\]}>]*",
        lambda match: privacy.text(match[0])[0],
        text,
    )
    escaped = []
    for char in text:
        if char == "\n":
            escaped.append(r"\n")
        elif char == "\r":
            escaped.append(r"\r")
        elif char == "\t":
            escaped.append(r"\t")
        elif unicodedata.category(char).startswith("C") or char in {"\u2028", "\u2029"}:
            code = ord(char)
            escaped.append(f"\\x{code:02x}" if code <= 255 else f"\\u{code:04x}")
        else:
            escaped.append(char)
    return "".join(escaped)


def _file_status(
    ref: FileRef,
    path: Path | None,
    read: Callable[[Path], bytes | None],
    *,
    snapshot: bool,
    max_bytes: int,
    too_many: bool,
) -> str:
    if path is None:
        return "not a file (optional declaration)" if ref.optional else "unavailable"
    if is_forbidden_file(ref.path) or is_forbidden_file(path.name):
        return "hash-only (forbidden name)"
    try:
        size = path.stat().st_size
        if size > MAX_BYTES:
            suffix = "; hash-only" if size > max_bytes or not snapshot or too_many else ""
            return f"not inspected (over 2 MiB{suffix})"
        if not snapshot:
            return "hash-only (snapshots disabled)"
        if too_many:
            return "hash-only (200-file limit)"
        if size > max_bytes:
            return "hash-only (size)"
        data = read(path)
        if data is None:
            return "not inspected (over 2 MiB)"
        if len(data) > max_bytes:
            return "hash-only (size)"
        if b"\0" in data:
            return "hash-only (binary)"
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return "hash-only (binary)"
    except (OSError, ValueError):
        return "unavailable (cannot read file)"
    return "snapshot eligible"


def _file_lines(
    refs: Sequence[FileRef],
    root: Path,
    privacy: RunPrivacy,
    read: Callable[[Path], bytes | None],
    *,
    snapshot: bool,
    max_bytes: int,
) -> list[str]:
    rank = {RunFileOrigin.DECLARED: 0, RunFileOrigin.BINDING: 1, RunFileOrigin.ARGV: 2}
    unique: dict[str, FileRef] = {}
    for ref in sorted(refs, key=lambda item: (rank[item.origin], item.path, item.optional)):
        unique.setdefault(ref.path, ref)
    resolved = {name: resolve_project_file(root, name) for name in unique}
    too_many = sum(path is not None for path in resolved.values()) > 200
    lines = []
    for name, ref in sorted(unique.items()):
        status = _file_status(
            ref, resolved[name], read, snapshot=snapshot, max_bytes=max_bytes, too_many=too_many
        )
        lines.append(f"  {_safe(privacy, name)} [{ref.origin.value}]: {status}")
    return lines


def _config_status(root: Path, location: str, read: Callable[[Path], bytes | None]) -> str:
    relative, separator, key = location.partition(":")
    path = resolve_project_file(root, relative)
    if not separator or not key or path is None:
        return "path/key unavailable or outside repository"
    if is_forbidden_file(relative) or is_forbidden_file(path.name):
        return "refused (forbidden config file)"
    suffix = path.suffix.lower()
    if suffix not in {".yaml", ".yml", ".json", ".toml"}:
        return "unsupported config format"
    try:
        data = read(path)
        if data is None:
            return "not inspected (over 2 MiB)"
        text = data.decode("utf-8")
        if suffix == ".json":
            value = json.loads(text)
        elif suffix == ".toml":
            value = tomllib.loads(text)
        else:
            value = yaml.safe_load(text)
        for segment in key.split("."):
            if isinstance(value, dict):
                value = value[segment]
            elif isinstance(value, list):
                try:
                    index = int(segment)
                except ValueError:
                    return "key not found"
                value = value[index]
            else:
                return "key not found"
    except (KeyError, IndexError):
        return "key not found"
    except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
        return f"cannot read config ({type(exc).__name__})"
    return "located"


def _bindings(
    manifest: Manifest, rules: ProjectRules | None
) -> dict[str, list[BindingSpec | ProjectRuleBindings]]:
    combined: dict[str, list[BindingSpec | ProjectRuleBindings]] = {
        field: [binding] for field, binding in manifest.bindings.items()
    }
    if rules:
        for rule in rules.rules:
            if rule.bindings:
                combined.setdefault(rule.field, []).append(rule.bindings)
    return combined


def _binding_lines(
    combined: Mapping[str, Sequence[BindingSpec | ProjectRuleBindings]],
    argv: Sequence[str],
    env: Mapping[str, str],
    root: Path,
    privacy: RunPrivacy,
    read: Callable[[Path], bytes | None],
) -> list[str]:
    lines = []
    for field, specs in sorted(combined.items()):
        locations = []
        for flag in sorted({spec.cli for spec in specs if spec.cli}):
            count = sum(token == flag or token.startswith(flag + "=") for token in argv)
            status = f"located ({count} occurrences)" if count else "missing"
            locations.append(f"    cli {_safe(privacy, flag)}: {status}")
        for config in sorted({spec.config for spec in specs if spec.config}):
            locations.append(
                f"    config {_safe(privacy, config)}: {_config_status(root, config, read)}"
            )
        for name in sorted({spec.env for spec in specs if spec.env}):
            if is_secret_env_name(name):
                status = "refused (secret environment binding)"
            else:
                status = "present" if name in env else "missing"
            locations.append(f"    env {_safe(privacy, name)}: {status}")
        if locations:
            lines.append(f"  {_safe(privacy, field)}")
            lines.extend(locations)
    return lines


def _lookup(value: Any, path: str) -> Any:
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _leaves(value: Any, path: str) -> set[str]:
    if isinstance(value, dict):
        found: set[str] = set()
        for key, item in value.items():
            found.update(_leaves(item, f"{path}.{key}"))
        return found
    return {path} if value is not None else set()


def _unbound(
    manifest: Manifest,
    rules: ProjectRules | None,
    combined: Mapping[str, Sequence[BindingSpec | ProjectRuleBindings]],
) -> list[str]:
    try:
        data = manifest.model_dump(mode="python")
        fields: set[str] = set()
        for path in _ADVISORY_ROOTS:
            fields.update(_leaves(_lookup(data, path), path))
        for role, model in manifest.models.items():
            for name in ("id", "revision"):
                if getattr(model, name) is not None:
                    fields.add(f"models.{role}.{name}")
        if rules:
            fields.update(rule.field for rule in rules.rules)
    except (ValueError, RecursionError):
        raise UserError(
            "cannot inspect reprollm.yaml declarations; remove recursive values"
        ) from None
    bound = {
        field
        for field, specs in combined.items()
        if any(spec.cli or spec.config or spec.env for spec in specs)
    }
    return sorted(fields - bound)


def preview(
    argv: Sequence[str],
    *,
    cwd: Path,
    capture_output: bool | None = None,
    env_capture: Literal["allowlist", "all"] | None = None,
    snapshot: bool = True,
) -> str:
    """Describe potential capture without running commands or changing the repository."""
    if not argv:
        raise UserError("run --dry-run requires a command after --")
    read = lru_cache(maxsize=None)(_read)
    try:
        cwd = cwd.resolve()
        if not cwd.is_dir():
            raise UserError("--cwd must name an existing directory")
        root = _root(cwd)
        manifest, manifest_bytes = _document(root, MANIFEST, Manifest, read)
        rules, rules_bytes = _document(root, PROJECT_RULES, ProjectRules, read)
        config, _ = _document(root, CONFIG, Config, read)
        lock, _ = _document(root, LOCK, Lock, read)
    except (OSError, RuntimeError):
        raise UserError(
            "cannot inspect --cwd or ReproLLM documents; check paths and permissions"
        ) from None
    if manifest is None or manifest_bytes is None:
        raise UserError("run --dry-run requires reprollm.yaml; run `reprollm init` first")
    settings = (config or Config()).run
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    env = os.environ
    output = settings.capture_output if capture_output is None else capture_output
    lines = [
        "Run preflight (command not executed)",
        f"Working directory: {_safe(privacy, cwd.relative_to(root).as_posix())}",
        f"Snapshots: {'enabled' if snapshot else 'disabled'}",
        f"Output capture: {'enabled' if output else 'disabled'}",
        f"Environment policy: {env_capture or settings.env_capture}",
    ]

    def section(title: str, rows: Sequence[str]) -> None:
        lines.append(title + ":")
        lines.extend(rows or ["  none"])

    section(
        "Files",
        _file_lines(
            resolve_argv_files(argv, root, cwd) + declared_files(manifest, rules),
            root,
            privacy,
            read,
            snapshot=snapshot,
            max_bytes=settings.snapshot_max_bytes,
        ),
    )
    combined = _bindings(manifest, rules)
    section("Bindings", _binding_lines(combined, argv, env, root, privacy, read))
    required = manifest.execution.env_requirements if manifest.execution else None
    section(
        "Required environment",
        [
            f"  {_safe(privacy, name)}: {'present' if name in env else 'missing'}"
            for name in sorted(set(required or []))
        ],
    )
    section(
        "Unbound declarations",
        [f"  {_safe(privacy, field)}" for field in _unbound(manifest, rules, combined)],
    )
    reasons = []
    if lock is None:
        status = "missing"
    else:
        if lock.manifest_sha256 != sha256_bytes(manifest_bytes):
            reasons.append("reprollm.yaml changed")
        if lock.project_rules_sha256 != (
            sha256_bytes(rules_bytes) if rules_bytes is not None else None
        ):
            reasons.append(".reprollm/project-rules.yaml changed")
        status = "stale" if reasons else "fresh"
    lines.append(f"Lock: {status}")
    lines.extend(f"  {reason}" for reason in reasons)
    if status != "fresh":
        lines.append("  Run `reprollm lock` to refresh local lock identity.")
    lines.extend(
        [
            "Advisory only: no bound values are displayed; unbound declarations use a fixed scope.",
            "Remote revisions, artifact hashes, dependencies, hardware and provider access "
            "are not revalidated.",
            "Environment presence does not verify credentials or guarantee command success.",
            "Files and bindings can change after this preview; actual evidence is collected "
            "by `reprollm run`.",
            "No run ID, directory or files created; no subprocess or network calls made.",
        ]
    )
    return "\n".join(lines)
