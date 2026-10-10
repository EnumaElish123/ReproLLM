"""Construction, atomic writing, and freshness checks for ``reprollm.lock``."""

from __future__ import annotations

import getpass
import json
import os
import re
import socket
import tempfile
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from yaml.tokens import ScalarToken, ValueToken

from reprollm import __version__
from reprollm.core.errors import UserError
from reprollm.core.hashing import sha256_file
from reprollm.core.paths import repo_paths
from reprollm.core.persistence import redact_keyed_values
from reprollm.core.yaml_io import dump_yaml, load_lock
from reprollm.lock.resolver import resolve_manifest
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.lock import Lock, ResolutionMode
from reprollm.schemas.manifest import Manifest


@dataclass(frozen=True)
class LockSummary:
    exact: int
    declared: int
    unresolved: tuple[tuple[str, str], ...]
    unpinnable: tuple[tuple[str, str], ...]

    def render(self) -> str:
        paths = ", ".join(path for path, _ in self.unpinnable)
        suffix = f" ({paths})" if paths else ""
        lines = [
            f"Resolved: {self.exact} exact · {self.declared} declared · "
            f"{len(self.unresolved)} unresolved · {len(self.unpinnable)} unpinnable{suffix}"
        ]
        if self.unresolved:
            lines.append("Unresolved:")
            lines.extend(f"  - {path}: {reason}" for path, reason in self.unresolved)
        if self.unpinnable:
            lines.append("Unpinnable:")
            lines.extend(f"  - {path}: {reason}" for path, reason in self.unpinnable)
        return "\n".join(lines)


def build_lock(
    root: Path,
    manifest: Manifest,
    *,
    http: httpx.Client,
    offline: bool,
    verify_api: bool,
    hash_large_files: bool,
    now: datetime | None = None,
) -> Lock:
    """Resolve ``manifest`` and attach document identity and source hashes."""
    timestamp = now or datetime.now(timezone.utc).replace(microsecond=0)
    paths = repo_paths(root)
    sections = resolve_manifest(
        root,
        manifest,
        http=http,
        offline=offline,
        verify_api=verify_api,
        hash_large_files=hash_large_files,
        now=timestamp,
    )
    return Lock(
        reprollm_version=__version__,
        generated_at=timestamp,
        manifest_sha256=sha256_file(paths.manifest),
        project_rules_sha256=(
            sha256_file(paths.project_rules) if paths.project_rules.is_file() else None
        ),
        resolution=ResolutionMode(mode="offline" if offline else "online"),
        models=sections.models,
        datasets=sections.datasets,
        prompts=sections.prompts,
        files=sections.files,
        generation=sections.generation,
        inference=sections.inference,
        training=sections.training,
        evaluation=sections.evaluation,
        privacy=sections.privacy,
        environment=sections.environment,
    )


def write_lock(target: Path, lock: Lock) -> None:
    """Replace ``target`` atomically, leaving any previous lock intact on failure."""
    text = dump_yaml(lock)
    data = lock.model_dump(mode="json")
    privacy = RunPrivacy(target.parent, hostname=socket.gethostname(), username=getpass.getuser())
    safe_values = False
    try:
        safe_values = redact_keyed_values(data) == data and privacy.value(data) == data
        serialized_data = yaml.safe_load(text)
        tokens = list(yaml.scan(text))
        check_text = list(text)
        for token, following in zip(tokens, tokens[1:], strict=False):
            if isinstance(token, ScalarToken) and isinstance(following, ValueToken):
                # Keys are checked structurally. A mapping key followed by another
                # mapping is not a generic_kv scalar, despite the regex's \s*.
                for index in range(token.start_mark.index, token.end_mark.index):
                    if check_text[index] not in "\r\n":
                        check_text[index] = " "
        same_data = json.dumps(serialized_data, sort_keys=True) == json.dumps(data, sort_keys=True)
        safe_serialization = same_data and not privacy.text("".join(check_text))[1]
    except (yaml.YAMLError, TypeError, ValueError):
        safe_serialization = False
    if not safe_values or re.search(r"(?i)\bfile:[/\\]{2}", text) or not safe_serialization:
        raise UserError(
            "cannot write reprollm.lock: remove secrets and machine identity from reprollm.yaml; "
            "let the child read credentials from environment variables or another secure source, "
            "and use project-relative paths"
        )
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
        raise UserError(
            "cannot write reprollm.lock; check the project directory permissions"
        ) from exc


def check_lock(root: Path) -> list[str]:
    """Return deterministic staleness reasons without performing resolution."""
    paths = repo_paths(root)
    if not paths.lock.is_file():
        return ["reprollm.lock is missing"]
    lock = load_lock(paths.lock)
    reasons: list[str] = []
    if lock.manifest_sha256 != sha256_file(paths.manifest):
        reasons.append("reprollm.yaml changed")
    current_rules_hash = sha256_file(paths.project_rules) if paths.project_rules.is_file() else None
    if lock.project_rules_sha256 != current_rules_hash:
        reasons.append(".reprollm/project-rules.yaml changed")
    return reasons


def summarize_lock(lock: Lock) -> LockSummary:
    """Count provenance states and list all unresolved and unpinnable paths."""
    exact = 0
    declared = 0
    unresolved: list[tuple[str, str]] = []
    data = lock.model_dump(mode="json")
    for path, provenance in _walk_provenance(data):
        confidence = provenance["confidence"]
        if confidence == "exact":
            exact += 1
        elif confidence == "declared":
            declared += 1
        elif confidence == "unresolved":
            reason = provenance.get("note") or provenance.get("source") or "unresolved"
            unresolved.append((path, str(reason)))
    unpinnable = [
        (
            f"models.{role}",
            f"{model.provider} does not expose an immutable model revision",
        )
        for role, model in sorted(lock.models.items())
        if model.pinnability == "unpinnable"
    ]
    return LockSummary(
        exact=exact,
        declared=declared,
        unresolved=tuple(sorted(unresolved)),
        unpinnable=tuple(unpinnable),
    )


def _walk_provenance(value: Any, path: str = "") -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        if {"value", "source", "confidence"} <= value.keys():
            yield path, value
            return
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            yield from _walk_provenance(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_provenance(item, f"{path}[{index}]")
