"""Archive before deactivation; restore complete accepted declarations (UX2-T06)."""

from __future__ import annotations

import getpass
import json
import os
import re
import socket
import tempfile
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import ValidationError

from reprollm.core.errors import UserError
from reprollm.core.paths import PROJECT_RULES
from reprollm.core.yaml_io import dump_yaml
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.project_rules import ProjectRule, ProjectRules
from reprollm.schemas.rule_archive import RuleArchive

ARCHIVE_DIR = ".reprollm/rule-archives"
_ARCHIVE_ID = re.compile(r"ra-[0-9a-f]{16}")
ArchiveState = Literal["active-identical", "inactive", "conflict"]


def display_value(root: Path, value: Any) -> Any:
    """Redact variable text without changing fixed schema keys or generated IDs."""
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    fixed = {
        "severity": {"CRITICAL", "WARNING", "INFO"},
        "suggested_severity": {"CRITICAL", "WARNING", "INFO"},
        "source": {"manual", "discover", PROJECT_RULES},
        "kind": {
            "rule",
            "candidate",
            "archive",
            "parameter",
            "dependency",
            "artifact",
            "profile",
            "file",
            "field",
            "config",
            "code",
        },
        "status": {"accepted", "ignored", "pending"},
        "state": {"active-identical", "inactive", "conflict"},
        "confidence": {"high", "medium", "low"},
    }

    def sanitize(item: Any, key: str | None = None) -> Any:
        if isinstance(item, dict):
            return {name: sanitize(child, name) for name, child in item.items()}
        if isinstance(item, list):
            return [sanitize(child) for child in item]
        if isinstance(item, str):
            if item in fixed.get(key or "", set()):
                return item
            if key == "archive_id" and _ARCHIVE_ID.fullmatch(item):
                return item
            if key == "source" and re.fullmatch(
                r"\.reprollm/rule-archives/ra-[0-9a-f]{16}\.json", item
            ):
                return item
            if key == "source" and item.startswith(".reprollm/discover/"):
                return (
                    ".reprollm/discover/"
                    + privacy.text(item.removeprefix(".reprollm/discover/"))[0]
                )
            return privacy.text(item)[0]
        return item

    return sanitize(value)


def _safe_copy(root: Path, value: Any) -> None:
    if display_value(root, value) != value:
        raise UserError(
            "cannot archive or restore unsafe rule content; remove secrets and machine-specific "
            "text from the rule or --reason before retrying (no original fields were changed)"
        )


def _owned_path(root: Path, relative: str) -> Path:
    """Never follow an artifact symlink, including an in-repository secret target."""
    current = root
    for component in Path(relative).parts:
        current = current / component
        if current.is_symlink():
            raise UserError(f"{relative} must not contain symlinks")
    return current


def _read_rules_bytes(root: Path) -> bytes | None:
    path = _owned_path(root, PROJECT_RULES)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise UserError(
            f"cannot read {PROJECT_RULES} ({type(exc).__name__}); fix this file"
        ) from None


def _rules_snapshot(root: Path) -> tuple[ProjectRules, bytes | None]:
    content = _read_rules_bytes(root)
    if content is None:
        return ProjectRules(), None
    try:
        data = yaml.safe_load(content.decode("utf-8"))
        return ProjectRules.model_validate({} if data is None else data), content
    except (ValueError, UnicodeError, yaml.YAMLError) as exc:
        raise UserError(
            f"cannot read {PROJECT_RULES} ({type(exc).__name__}); fix this file"
        ) from None


def read_rules(root: Path) -> ProjectRules:
    return _rules_snapshot(root)[0]


def _archive_path(root: Path, archive_id: str) -> Path:
    if not _ARCHIVE_ID.fullmatch(archive_id):
        raise UserError("archive id must match ra- followed by 16 lowercase hexadecimal characters")
    return _owned_path(root, f"{ARCHIVE_DIR}/{archive_id}.json")


def _atomic_text(
    path: Path, text: str, *, exclusive: bool, before_replace: Callable[[], None] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".rule-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            # link publishes a fully written file and refuses to replace any
            # existing name, unlike replace. The temporary link is then removed.
            os.link(temporary, path)
        else:
            if before_replace is not None:
                before_replace()
            temporary.replace(path)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def write_rules(root: Path, document: ProjectRules, *, expected: bytes | None) -> None:
    _safe_copy(root, document.model_dump(mode="json"))
    target = _owned_path(root, PROJECT_RULES)

    def unchanged() -> None:
        if _read_rules_bytes(root) != expected:
            raise UserError(
                f"{PROJECT_RULES} changed during this command; review it before retrying"
            )

    try:
        _atomic_text(
            target,
            dump_yaml(document.model_dump(mode="json")),
            exclusive=False,
            before_replace=unchanged,
        )
    except OSError as exc:
        raise UserError(
            f"cannot write {PROJECT_RULES} ({type(exc).__name__}); fix this file"
        ) from None


def save_archive(root: Path, document: RuleArchive) -> None:
    _safe_copy(root, document.model_dump(mode="json"))
    target = _archive_path(root, document.archive_id)
    text = (
        json.dumps(document.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    try:
        _atomic_text(target, text, exclusive=True)
    except FileExistsError:
        # Repeating the same request in the same second reuses its identical
        # immutable recovery copy; an edited or colliding archive is an error.
        if load_archive(root, document.archive_id) != document:
            raise UserError(
                f"archive {document.archive_id} already exists with different content"
            ) from None
    except OSError as exc:
        raise UserError(
            f"cannot save {ARCHIVE_DIR} recovery copy ({type(exc).__name__}); rule not removed"
        ) from None


def load_archive(root: Path, archive_id: str) -> RuleArchive:
    path = _archive_path(root, archive_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            isinstance(data, dict)
            and isinstance(data.get("schema_version"), int)
            and data["schema_version"] > 1
        ):
            raise UserError(f"archive {archive_id} uses a newer schema_version; upgrade ReproLLM")
        document = RuleArchive.model_validate(data)
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        raise UserError(
            f"cannot read archive {archive_id} ({type(exc).__name__}); fix {ARCHIVE_DIR}"
        ) from None
    if document.archive_id != archive_id or document.content_id() != archive_id:
        raise UserError(
            f"archive {archive_id} content does not match its id; recover the original archive"
        )
    _safe_copy(root, document.model_dump(mode="json"))
    return document


def archive_state(document: ProjectRules, archive: RuleArchive) -> ArchiveState:
    original = archive.rule
    active = False
    for rule in document.rules:
        if rule.id == original.id:
            if rule != original:
                return "conflict"
            active = True
        elif original.candidate_id is not None and rule.candidate_id == original.candidate_id:
            return "conflict"
    return "active-identical" if active else "inactive"


def remove_rule(root: Path, rule_id: str, reason: str) -> RuleArchive:
    if not reason.strip():
        raise UserError("--reason is required and must be non-empty")
    current, before = _rules_snapshot(root)
    original = next((rule for rule in current.rules if rule.id == rule_id), None)
    if original is None:
        raise UserError("unknown active rule id; inspect `reprollm rules list`")
    archive = RuleArchive(
        archive_id="ra-" + "0" * 16,
        archived_at=datetime.now(timezone.utc).replace(microsecond=0),
        reason=reason.strip(),
        rule=original,
    )
    archive = archive.model_copy(update={"archive_id": archive.content_id()})
    save_archive(root, archive)
    current.rules = [rule for rule in current.rules if rule.id != rule_id]
    try:
        write_rules(root, current, expected=before)
    except (UserError, OSError):
        raise UserError(
            f"Recovery copy {archive.archive_id} saved; rule {rule_id} "
            "was not removed by this command. "
            f"Inspect {PROJECT_RULES}, then retry removal; `rules show {archive.archive_id}` "
            "derives the current rule state."
        ) from None
    return archive


def restore_rule(root: Path, archive_id: str) -> ProjectRule:
    archive = load_archive(root, archive_id)
    current, before = _rules_snapshot(root)
    if archive_state(current, archive) != "inactive":
        raise UserError(
            f"cannot restore {archive_id}: its rule id or candidate id is already active; "
            "inspect `reprollm rules list` before changing it"
        )
    current.rules.append(archive.rule)
    write_rules(root, current, expected=before)
    return archive.rule
