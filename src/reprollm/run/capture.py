"""File, artifact, and binding capture for run records."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from reprollm.core.errors import UserError
from reprollm.core.hashing import CHUNK_SIZE, sha256_file
from reprollm.core.paths import is_relative_project_path, resolve_project_file
from reprollm.core.redaction import is_forbidden_file, redact_text
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import ArtifactRef, RunFileOrigin, RunFileRef


@dataclass(frozen=True)
class FileRef:
    path: str
    origin: RunFileOrigin
    optional: bool = False


def resolve_argv_files(argv: Sequence[str], root: Path, cwd: Path) -> list[FileRef]:
    found: dict[str, FileRef] = {}
    root = root.resolve()
    for token in argv:
        candidates = [token]
        if token.startswith("--") and "=" in token:
            candidates.append(token.split("=", 1)[1])
        for candidate in candidates:
            try:
                relative = Path(os.path.abspath(cwd / candidate)).relative_to(root).as_posix()
            except (OSError, ValueError):
                continue
            if resolve_project_file(root, relative) is not None:
                found[relative] = FileRef(relative, RunFileOrigin.ARGV)
    return [found[path] for path in sorted(found)]


def declared_files(
    manifest: Manifest | None, project_rules: ProjectRules | None = None
) -> list[FileRef]:
    """Manifest binding paths are declared files under normative R-04."""
    found: dict[str, FileRef] = {}

    def add(
        path: str, *, optional: bool = False, origin: RunFileOrigin = RunFileOrigin.DECLARED
    ) -> None:
        if path not in found or found[path].optional:
            found[path] = FileRef(path, origin, optional)

    if manifest is not None:
        if manifest.execution is not None:
            for path in manifest.execution.config_files or []:
                add(path)
        for binding in manifest.bindings.values():
            if binding.config:
                add(binding.config.partition(":")[0])
        for prompt in manifest.prompts.values():
            if prompt.path:
                add(prompt.path)
        if manifest.training is not None and manifest.training.deepspeed is not None:
            add(manifest.training.deepspeed.config)
        for model in manifest.models.values():
            if model.chat_template is not None:
                add(model.chat_template.path)
        if manifest.evaluation is not None:
            for value in (manifest.evaluation.definitions or {}).values():
                add(value, optional=True)
        if manifest.privacy is not None and manifest.privacy.threat_model:
            add(manifest.privacy.threat_model, optional=True)
    if project_rules is not None:
        for rule in project_rules.rules:
            if rule.bindings is not None and rule.bindings.config:
                add(rule.bindings.config.partition(":")[0], origin=RunFileOrigin.BINDING)
    return [found[path] for path in sorted(found)]


def _read_file(path: Path, limit: int) -> tuple[str, int, bytes | None]:
    digest = hashlib.sha256()
    size = 0
    buffer = bytearray()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
            size += len(chunk)
            if size <= limit:
                buffer.extend(chunk)
            else:
                buffer.clear()
    return f"sha256:{digest.hexdigest()}", size, bytes(buffer) if size <= limit else None


def hash_and_snapshot(
    refs: Sequence[FileRef],
    run_dir: Path,
    *,
    root: Path,
    snapshot: bool,
    max_bytes: int,
    warnings: list[str] | None = None,
) -> list[RunFileRef]:
    """Hash original bytes; snapshot only bounded, redacted UTF-8 text (§5.1 R-03)."""
    warnings = warnings if warnings is not None else []
    if max_bytes < 1:
        raise ValueError("snapshot_max_bytes must be positive")
    rank = {RunFileOrigin.DECLARED: 0, RunFileOrigin.BINDING: 1, RunFileOrigin.ARGV: 2}
    unique: dict[str, FileRef] = {}
    for ref in sorted(refs, key=lambda item: (rank[item.origin], item.path, item.optional)):
        unique.setdefault(ref.path, ref)
    valid: list[tuple[FileRef, Path]] = []
    for ref in unique.values():
        path = resolve_project_file(root, ref.path)
        if path is not None:
            valid.append((ref, path))
        elif not ref.optional:
            warnings.append("declared/argv file unavailable or outside repository")
    if snapshot and len(valid) > 200:
        snapshot = False
        warnings.append("more than 200 files: hashes recorded, file snapshots disabled")
    records = []
    for ref, path in sorted(valid, key=lambda item: item[0].path):
        forbidden = is_forbidden_file(ref.path) or is_forbidden_file(path.name)
        try:
            digest, size, data = _read_file(path, max_bytes if snapshot and not forbidden else -1)
        except OSError as exc:
            warnings.append(f"file {ref.path}: cannot read ({type(exc).__name__})")
            continue
        record = RunFileRef(
            path=ref.path, sha256=digest, size_bytes=size, origin=ref.origin, redacted=forbidden
        )
        if data is not None and b"\0" not in data:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                records.append(record)
                continue
            redacted, count = redact_text(text)
            destination = run_dir / "files" / digest.removeprefix("sha256:")
            if destination.is_symlink() or not destination.resolve().is_relative_to(
                run_dir.resolve()
            ):
                raise UserError(
                    "run files/ snapshot destination must remain inside the run directory"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(redacted, encoding="utf-8", newline="")
            record.snapshot = destination.relative_to(run_dir).as_posix()
            record.redacted = count > 0
        records.append(record)
    return records


def collect_outputs(root: Path, patterns: Sequence[str]) -> list[ArtifactRef]:
    paths: set[str] = set()
    for pattern in patterns:
        if not is_relative_project_path(pattern):
            continue
        for path in root.glob(pattern):
            relative = path.relative_to(root).as_posix()
            if resolve_project_file(root, relative) is not None:
                paths.add(relative)
    records = []
    for relative in sorted(paths):
        resolved = resolve_project_file(root, relative)
        if resolved is not None:
            records.append(
                ArtifactRef(
                    path=relative, sha256=sha256_file(resolved), size_bytes=resolved.stat().st_size
                )
            )
    return records
