"""Pre-child input baselines and bounded post-child change checks (§5.1 R-13/R-14)."""

from __future__ import annotations

import stat
from collections.abc import Mapping, Sequence
from functools import partial
from pathlib import Path
from typing import Literal

from reprollm.core.bindings import observe
from reprollm.core.configread import MAX_CONFIG_BYTES
from reprollm.core.hashing import sha256_bytes
from reprollm.core.paths import LOCK, MANIFEST, is_relative_project_path, resolve_project_file
from reprollm.core.redaction import is_forbidden_file
from reprollm.run.capture import (
    FileRef,
    _read_file,
    declared_files,
    hash_and_snapshot,
    resolve_argv_files,
)
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import (
    DocumentRef,
    InputCapture,
    InputCheck,
    InputFingerprint,
    RunFileOrigin,
    RunFileRef,
    RunRecord,
)

_Origin = Literal["manifest", "lock", "argv", "declared", "binding"]


def _locate(root: Path, relative: str) -> tuple[Path | None, InputFingerprint]:
    """Distinguish absent inputs from targets that cannot safely be inspected."""
    unavailable = InputFingerprint(availability="unavailable")
    if not is_relative_project_path(relative):
        return None, unavailable
    try:
        base = root.resolve()
        alias = base / relative
        target = alias.resolve()
        target.relative_to(base)
        try:
            info = target.stat()
        except FileNotFoundError:
            if alias.is_symlink():
                return None, unavailable
            return None, InputFingerprint(availability="missing")
        if not stat.S_ISREG(info.st_mode):
            return None, unavailable
    except (OSError, RuntimeError, ValueError):
        return None, unavailable
    return target, unavailable


def _fingerprint(root: Path, relative: str) -> InputFingerprint:
    path, unavailable = _locate(root, relative)
    if path is None:
        return unavailable
    try:
        digest, size, _ = _read_file(path, -1)
    except OSError:
        return unavailable
    return InputFingerprint(availability="present", sha256=digest, size_bytes=size)


def _check(path: str, origin: _Origin, before: InputFingerprint) -> InputCheck:
    return InputCheck(
        path=path,
        origin=origin,
        before=before,
        after=InputFingerprint(availability="unavailable"),
        change="unknown",
    )


def _copy_document(name: str, data: bytes, run_dir: Path, privacy: RunPrivacy) -> DocumentRef:
    snapshot = "manifest.yaml" if name == MANIFEST else "lock.yaml"
    destination = run_dir / snapshot
    if destination.is_symlink() or not destination.resolve().is_relative_to(run_dir.resolve()):
        raise OSError("unsafe document snapshot destination")
    text = privacy.text(data.decode("utf-8"), manifest=name == MANIFEST)[0]
    destination.write_text(text, encoding="utf-8", newline="")
    return DocumentRef(path=name, sha256=sha256_bytes(data), snapshot=snapshot)


def capture_inputs(
    record: RunRecord,
    *,
    root: Path,
    cwd: Path,
    run_dir: Path,
    argv: Sequence[str],
    env: Mapping[str, str],
    privacy: RunPrivacy,
    manifest: Manifest | None,
    project_rules: ProjectRules | None,
    snapshot: bool,
    max_bytes: int,
    document_data: Mapping[str, bytes | None],
) -> None:
    """Freeze documents, input files and binding observations before executing a child."""
    checks: dict[str, InputCheck] = {}
    original_documents = dict(document_data)
    documents: tuple[tuple[str, _Origin], ...] = ((MANIFEST, "manifest"), (LOCK, "lock"))
    for name, origin in documents:
        path, before = _locate(root, name)
        data = document_data.get(name)
        original_documents[name] = data
        try:
            if name not in document_data and path is not None:
                data = path.read_bytes()
            original_documents[name] = data
            if data is not None:
                before = InputFingerprint(
                    availability="present", sha256=sha256_bytes(data), size_bytes=len(data)
                )
                setattr(record, origin, _copy_document(name, data, run_dir, privacy))
        except Exception:
            record.warnings.append(f"{origin} input snapshot unavailable")
        checks[name] = _check(name, origin, before)

    rank = {RunFileOrigin.DECLARED: 0, RunFileOrigin.BINDING: 1, RunFileOrigin.ARGV: 2}
    refs = declared_files(manifest, project_rules) + resolve_argv_files(argv, root, cwd)
    unique: dict[str, FileRef] = {}
    for ref in sorted(refs, key=lambda item: (rank[item.origin], item.path, item.optional)):
        if is_relative_project_path(ref.path):
            unique.setdefault(ref.path, ref)
        else:
            record.warnings.append("input path unavailable or outside repository")
    config_paths = {
        binding.config.partition(":")[0]
        for binding in (manifest.bindings.values() if manifest else [])
        if binding.config and is_relative_project_path(binding.config.partition(":")[0])
    }
    if project_rules is not None:
        config_paths.update(
            rule.bindings.config.partition(":")[0]
            for rule in project_rules.rules
            if rule.bindings is not None
            and rule.bindings.config
            and is_relative_project_path(rule.bindings.config.partition(":")[0])
        )
    config_data: dict[str, bytes | None] = dict.fromkeys(sorted(config_paths))
    capture_limits = dict.fromkeys(config_paths, MAX_CONFIG_BYTES)
    if (
        snapshot
        and sum(resolve_project_file(root, ref.path) is not None for ref in unique.values()) > 200
    ):
        snapshot = False
        record.warnings.append("more than 200 files: hashes recorded, file snapshots disabled")
    files: list[RunFileRef] = []
    for ref in sorted(unique.values(), key=lambda item: item.path):
        path, before = _locate(root, ref.path)

        def retain(source: FileRef, digest: str, size: int, data: bytes | None) -> None:
            nonlocal before
            before = InputFingerprint(availability="present", sha256=digest, size_bytes=size)
            if source.path in config_data:
                config_data[source.path] = data

        try:
            files.extend(
                hash_and_snapshot(
                    [ref],
                    run_dir,
                    root=root,
                    snapshot=snapshot,
                    max_bytes=max_bytes,
                    warnings=record.warnings,
                    sanitize=(
                        partial(privacy.text, python_source=True)
                        if ref.path.endswith(".py")
                        else privacy.text
                    ),
                    on_read=retain,
                    capture_limit=capture_limits,
                    original_data=original_documents,
                )
            )
        except Exception:
            record.warnings.append("input file snapshot unavailable")
            if before.availability == "present":
                assert before.sha256 is not None and before.size_bytes is not None
                files.append(
                    RunFileRef(
                        path=ref.path,
                        origin=ref.origin,
                        sha256=before.sha256,
                        size_bytes=before.size_bytes,
                        redacted=is_forbidden_file(ref.path)
                        or (path is not None and is_forbidden_file(path.name)),
                    )
                )
        if ref.path not in checks:
            checks[ref.path] = _check(ref.path, ref.origin.value, before)
    record.files = files
    record.input_capture = InputCapture(checks=[checks[path] for path in sorted(checks)])
    try:
        record.bindings_observed = observe(
            manifest.bindings if manifest else {},
            argv,
            env,
            root,
            project_rules=project_rules,
            warnings=record.warnings,
            config_data=config_data,
        )
    except Exception:
        record.warnings.append("input binding observation unavailable")


def recheck_inputs(record: RunRecord, *, root: Path) -> None:
    """Recheck only frozen paths; leave pre-child hashes, copies and observations intact."""
    if record.input_capture is None:
        return
    checks = []
    for check in record.input_capture.checks:
        after = _fingerprint(root, check.path)
        if after.availability == "unavailable":
            record.warnings.append("input recheck unavailable")
        before = check.before
        if "unavailable" in (before.availability, after.availability):
            change: Literal["unchanged", "changed", "removed", "created", "unknown"] = "unknown"
        elif before.availability == "missing" and after.availability == "present":
            change = "created"
        elif before.availability == "present" and after.availability == "missing":
            change = "removed"
        elif before.sha256 == after.sha256 and before.size_bytes == after.size_bytes:
            change = "unchanged"
        else:
            change = "changed"
        checks.append(
            InputCheck(
                path=check.path,
                origin=check.origin,
                before=before,
                after=after,
                change=change,
            )
        )
    record.input_capture = InputCapture(checks=checks)
