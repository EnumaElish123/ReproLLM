"""Native initialization and staged report/schema publication for the Skill.

Research declarations are rendered by ReproLLM. This boundary only guards the
owned destinations and preserves ordinary-failure effects; it is not a
filesystem transaction against arbitrary concurrent editors or power loss.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import importlib
import json
import os
import stat
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skill_request import WRITE_ACTIONS, Reply, Request, blocked

_OWNER = {"schema_version": 1, "owner": "reprollm-skill-writes"}
SourceSignature = Callable[[Path, list[Path], Path], str]
CliRunner = Callable[[list[str], Path], Any]
DisplaySanitizer = Callable[[Any, list[dict[str, Any]]], Any]


class WriteError(ValueError):
    """A fixed boundary diagnostic with no user values or machine paths."""

    def __init__(self, code: str, *, authorization: bool = False) -> None:
        super().__init__(code)
        self.authorization = authorization


@dataclass(frozen=True)
class DirectoryIdentity:
    path: Path
    identity: tuple[int, int]


@dataclass(frozen=True)
class Artifact:
    role: str
    target: Path
    content: bytes
    expected: str | None
    mode: int
    bindings: tuple[Path, ...]
    approval_required: bool = False
    parents: tuple[DirectoryIdentity, ...] = ()
    missing_parents: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Published:
    artifact: Artifact
    created: bool
    identity: tuple[int, int]


@dataclass
class PreparedWrite:
    action: str
    root: Path
    artifacts: list[Artifact]
    source_fingerprint: str
    plan_hash: str
    data: dict[str, Any]
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    cli_exit_code: int = 0


@dataclass(frozen=True)
class ReadFile:
    declared: Path
    target: Path
    digest: str | None
    bindings: tuple[tuple[Path, Path], ...]


@dataclass(frozen=True)
class ReadDirectory:
    declared: Path
    target: Path
    inventory: str | None
    bindings: tuple[tuple[Path, Path], ...]


class ReadGuard:
    """The actual native export record/snapshot read set, kept transiently."""

    def __init__(self, request: Request, root: Path) -> None:
        self.request = request
        self.root = root
        self.files: dict[Path, ReadFile] = {}
        self.directories: dict[Path, ReadDirectory] = {}

    def _bindings(self, target: Path, bundle: Path | None = None) -> tuple[tuple[Path, Path], ...]:
        if target.is_relative_to(self.root):
            return ()
        bindings = []
        for item in self.request.grants.external_paths:
            declared = _path(item, self.root)
            actual = declared.resolve()
            if actual == target:
                bindings.append((declared, target))
            elif (
                bundle is not None and actual == bundle.resolve() and target.is_relative_to(actual)
            ):
                bindings.append((declared, actual))
        if not bindings:
            raise WriteError("external_input_scope_required", authorization=True)
        return tuple(bindings)

    def file(self, declared: Path, *, bundle: Path | None = None) -> None:
        target = declared.resolve()
        bindings = self._bindings(target, bundle)
        if target.is_file() and target.stat().st_size > 64 * 1024 * 1024:
            raise WriteError("write_input_fingerprint_limit")
        item = ReadFile(declared, target, _hash_file(target), bindings)
        previous = self.files.get(declared)
        if previous is not None and previous != item:
            raise WriteError("write_native_input_changed")
        self.files[declared] = item

    @staticmethod
    def _inventory(path: Path) -> str | None:
        if not path.exists():
            return None
        names = []
        for child in path.iterdir():
            names.append(child.name)
            if len(names) > 50_000:
                raise WriteError("write_input_inventory_limit")
        return _sha(_json(sorted(names)))

    def directory(self, declared: Path) -> None:
        target = declared.resolve()
        bindings = self._bindings(target)
        self.directories[declared] = ReadDirectory(
            declared, target, self._inventory(target), bindings
        )

    def check(self) -> None:
        observed: tuple[ReadDirectory | ReadFile, ...] = (
            *self.directories.values(),
            *self.files.values(),
        )
        for item in observed:
            if item.declared.resolve() != item.target or any(
                declared.resolve() != expected for declared, expected in item.bindings
            ):
                raise WriteError("write_native_input_mapping_changed", authorization=True)
            current = (
                self._inventory(item.target)
                if isinstance(item, ReadDirectory)
                else _hash_file(item.target)
            )
            expected = item.inventory if isinstance(item, ReadDirectory) else item.digest
            if current != expected:
                raise WriteError("write_native_input_changed")

    def fingerprint(self) -> str:
        return _sha(
            _json(
                {
                    "files": [
                        [
                            _sha(str(item.declared).encode("utf-8")),
                            _sha(str(item.target).encode("utf-8")),
                            item.digest,
                        ]
                        for _, item in sorted(self.files.items())
                    ],
                    "directories": [
                        [
                            _sha(str(item.declared).encode("utf-8")),
                            _sha(str(item.target).encode("utf-8")),
                            item.inventory,
                        ]
                        for _, item in sorted(self.directories.items())
                    ],
                }
            )
        )


def _json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hash_file(path: Path) -> str | None:
    if path.is_symlink():
        raise WriteError("write_target_symlink_refused")
    try:
        before = path.stat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(before.st_mode):
        raise WriteError("write_target_regular_file_required")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while raw := stream.read(1024 * 1024):
            digest.update(raw)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise WriteError("write_target_changed")
    return digest.hexdigest()


def _path(value: str | Path, root: Path) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _check_owner_marker(marker: Path) -> None:
    if marker.is_symlink() or not marker.is_file():
        raise WriteError("write_state_ownership_required")
    try:
        value = json.loads(marker.read_bytes())
    except (OSError, ValueError):
        raise WriteError("write_state_ownership_required") from None
    if value != _OWNER or type(value.get("schema_version")) is not int:
        raise WriteError("write_state_ownership_required")


def _publish_owner_marker(path: Path) -> None:
    descriptor, name = tempfile.mkstemp(prefix=".owner-", suffix=".tmp", dir=path)
    temporary = Path(name)
    identity = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(_json(_OWNER) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        # A concurrent complete marker may win; never replace its bytes.
        with contextlib.suppress(FileExistsError):
            os.link(temporary, path / "owner.json")
        _check_owner_marker(path / "owner.json")
    finally:
        with contextlib.suppress(FileNotFoundError):
            current = temporary.lstat()
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                temporary.unlink()


def _owned_state(path: Path) -> Path:
    if path.is_symlink():
        raise WriteError("write_state_symlink_refused")
    marker = path / "owner.json"
    if path.exists() and any(path.iterdir()):
        _check_owner_marker(marker)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if marker.exists() or marker.is_symlink():
        _check_owner_marker(marker)
    else:
        _publish_owner_marker(path)
    for name in ("staging", "locks"):
        child = path / name
        if child.is_symlink():
            raise WriteError("write_state_symlink_refused")
        child.mkdir(mode=0o700, exist_ok=True)
    return path.resolve()


def _label(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else path.name


def _artifact(
    request: Request,
    root: Path,
    declared: Path,
    content: bytes,
    *,
    role: str,
    mode: int,
    implicit_replace: bool = False,
    external_directory: Path | None = None,
) -> Artifact:
    if declared.is_symlink():
        raise WriteError("write_target_symlink_refused")
    target = declared.resolve()
    bindings = [declared]
    if not target.is_relative_to(root):
        matches = []
        for item in request.grants.external_paths:
            candidate = _path(item, root)
            if candidate.resolve() == target:
                matches.append(candidate)
            elif (
                external_directory is not None
                and candidate.resolve() == external_directory.resolve()
            ):
                matches.append(candidate / target.name)
        if not matches:
            raise WriteError("external_output_scope_required", authorization=True)
        bindings.extend(matches)
    expected = _hash_file(target)
    approvals = [
        (_path(path, root), digest)
        for path, digest in request.grants.expected_hashes.items()
        if _path(path, root).resolve() == target
    ]
    if len(approvals) > 1:
        raise WriteError("write_target_approval_ambiguous", authorization=True)
    if approvals:
        approved, reviewed = approvals[0]
        bindings.append(approved)
        if reviewed != expected:
            raise WriteError("write_target_changed", authorization=True)
    approved_existing = expected is None or implicit_replace or bool(approvals)
    if expected is not None:
        mode = stat.S_IMODE(target.stat().st_mode)
    parents = []
    missing = []
    for parent in (target.parent, *target.parent.parents):
        try:
            info = parent.lstat()
        except FileNotFoundError:
            missing.append(parent)
            continue
        if not stat.S_ISDIR(info.st_mode):
            raise WriteError("write_parent_changed")
        parents.append(DirectoryIdentity(parent, (info.st_dev, info.st_ino)))
    return Artifact(
        role,
        target,
        content,
        expected,
        mode,
        tuple(bindings),
        not approved_existing,
        tuple(parents),
        tuple(missing),
    )


def _check_mapping(artifact: Artifact) -> None:
    try:
        if any(path.resolve() != artifact.target for path in artifact.bindings):
            raise WriteError("write_target_mapping_changed", authorization=True)
        for parent in artifact.parents:
            info = parent.path.lstat()
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != parent.identity:
                raise WriteError("write_parent_changed")
    except (OSError, RuntimeError):
        raise WriteError("write_target_mapping_changed", authorization=True) from None


def _check_artifact(artifact: Artifact) -> None:
    _check_mapping(artifact)
    if _hash_file(artifact.target) != artifact.expected:
        raise WriteError("write_target_changed", authorization=True)


def _make_directories(artifact: Artifact, created: list[DirectoryIdentity]) -> Artifact:
    for path in reversed(artifact.missing_parents):
        own = next((item for item in created if item.path == path), None)
        if own is not None:
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != own.identity:
                raise WriteError("write_parent_changed")
            continue
        # An appearing foreign directory is not adopted as our prepared parent.
        path.mkdir()
        info = path.lstat()
        created.append(DirectoryIdentity(path, (info.st_dev, info.st_ino)))
    return dataclasses.replace(
        artifact,
        parents=(
            *artifact.parents,
            *(item for item in created if item.path in artifact.missing_parents),
        ),
    )


def publish_artifact(artifact: Artifact, published: list[Published]) -> None:
    """Commit one already approved artifact, tracking effects before cleanup."""
    _check_artifact(artifact)
    target = artifact.target
    if target.parent.resolve() != target.parent:
        raise WriteError("write_parent_changed")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".reprollm-skill-", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(artifact.content)
            os.chmod(temporary, artifact.mode)
            stream.flush()
            os.fsync(stream.fileno())
        identity = temporary.stat()
        _check_artifact(artifact)
        if target.parent.resolve() != target.parent:
            raise WriteError("write_parent_changed")
        if artifact.expected is None:
            # Same-directory hard-link publication is exclusive. An unsupported
            # filesystem fails safely instead of falling back to replacement.
            os.link(temporary, target)
        else:
            os.replace(temporary, target)
        published.append(
            Published(artifact, artifact.expected is None, (identity.st_dev, identity.st_ino))
        )
    finally:
        temporary.unlink(missing_ok=True)


def _rollback_created(published: list[Published], directories: list[DirectoryIdentity]) -> None:
    for item in reversed(published):
        if not item.created:
            continue
        target = item.artifact.target
        try:
            info = target.lstat()
            if (
                stat.S_ISREG(info.st_mode)
                and (info.st_dev, info.st_ino) == item.identity
                and _hash_file(target) == _sha(item.artifact.content)
            ):
                target.unlink()
        except (OSError, ValueError):
            pass
    for directory in reversed(directories):
        with contextlib.suppress(OSError):
            info = directory.path.lstat()
            if stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == directory.identity:
                directory.path.rmdir()


@contextlib.contextmanager
def _project_lock(state: Path, root: Path) -> Iterator[None]:
    lock = state / "locks" / _sha(str(root).encode("utf-8"))
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError:
        raise WriteError("write_operation_lock_held") from None
    try:
        yield
    finally:
        try:
            lock.rmdir()
        except OSError:
            raise WriteError("write_operation_lock_cleanup_failed") from None


def _native_error(request: Request, text: str, *, data: dict[str, Any] | None = None) -> Reply:
    return Reply(
        request.action,
        invocation="user_error",
        cli_exit_code=2,
        complete=False,
        data=data,
        diagnostics=[{"code": "native_usage_error", "text": text}],
    )


def _prepare_init(
    request: Request, root: Path, stage: Path
) -> tuple[dict[str, Any], list[Artifact], list[dict[str, Any]]] | Reply:
    from reprollm.core.errors import UserError
    from reprollm.core.init_guidance import (
        MANUAL_FIELDS,
        answer_privacy,
        check_interactive_plan,
        field_guidance,
        missing_required_fields,
        validate_answer,
    )
    from reprollm.core.manifest_scaffold import (
        check_scaffold_paths,
        plan_init,
        render_manifest,
        select_tasks,
        validate_init_command,
        write_scaffold,
    )

    options = request.options
    # Native CLI imports register the built-in rules before resolving profiles;
    # equivalent core initialization in a fresh worker needs the same registry.
    importlib.import_module("reprollm.rules")
    force = options.get("force", False)
    check_scaffold_paths(root, force=force)
    command = options.get("command")
    values: dict[str, Any] = {}
    accepted_answers: dict[str, str] = {}
    if command is not None:
        values["execution.command"] = validate_init_command(root, command)
    plan = plan_init(root, profiles_override=options.get("profiles"))
    selected = select_tasks(plan, options.get("tasks", []))
    data: dict[str, Any] = {
        "profiles": plan.profiles,
        "task_candidates": plan.task_names,
        "selected_tasks": selected,
        "guidance": {name: field_guidance(name) for name in plan.required_fields},
    }
    diagnostics = [{"code": "cli_stderr", "text": f"scan: {text}\n"} for text in plan.diagnostics]
    if plan.project_name_defaulted:
        diagnostics.append(
            {
                "code": "project_name_defaulted",
                "text": "Set project.name in reprollm.yaml; "
                "init used the safe default 'experiment'.",
            }
        )
    if (
        len(plan.task_names) > 1
        and "evaluation.metrics" in plan.required_fields
        and "tasks" not in options
    ):
        reply = blocked(
            request.action,
            "experiment_task_selection_required",
            needs_input=True,
            questions=["Select the task names for this experiment from task_candidates."],
        )
        reply.data = {**data, "phase": "prepared", "artifacts_written": []}
        reply.diagnostics.extend(diagnostics)
        return reply
    answers = options.get("answers", {})
    allowed = set(plan.required_fields) - MANUAL_FIELDS - {"project.name"}
    if set(answers) - allowed:
        return _native_error(request, "init.answers must name supported required scalar fields.")
    privacy = answer_privacy(root)
    check_interactive_plan(plan, values, selected, command, privacy)
    for field_path in plan.required_fields:
        if field_path not in answers or not answers[field_path].strip():
            continue
        answer = answers[field_path]
        try:
            if field_path == "execution.command":
                answer = validate_init_command(root, answer)
                if command is not None and command != answer:
                    raise UserError(
                        "execution.command conflicts with the explicitly provided command."
                    )
            value = validate_answer(
                plan,
                values,
                field_path,
                answer,
                selected_tasks=selected,
                saved_command=command,
                privacy=privacy,
            )
        except UserError as error:
            reply = _native_error(
                request,
                str(error),
                data={
                    **data,
                    "accepted_answers": accepted_answers,
                    "invalid_field": field_path,
                    "artifacts_written": [],
                },
            )
            reply.needs_input = True
            reply.diagnostics.extend(diagnostics)
            return reply
        values[field_path] = value
        accepted_answers[field_path] = answer
    text = render_manifest(plan, values, selected_tasks=selected, saved_command=command)
    remaining = missing_required_fields(plan, text)
    write_scaffold(stage, text, force=False)
    check_scaffold_paths(root, force=force)
    artifacts = []
    for role in (".reprollm/config.yaml", ".reprollm/project-rules.yaml", "reprollm.yaml"):
        declared = root / role
        if role != "reprollm.yaml" and declared.exists():
            continue
        source = stage / role
        artifacts.append(
            _artifact(
                request,
                root,
                declared,
                source.read_bytes(),
                role=role,
                mode=stat.S_IMODE(source.stat().st_mode),
                implicit_replace=force and role == "reprollm.yaml",
            )
        )
    data.update(
        {
            "manifest_text": text,
            "missing_required_fields": remaining,
            "accepted_answers": accepted_answers,
        }
    )
    return data, artifacts, diagnostics


def _export_input_target(root: Path, target: Path, selected: Any = None) -> bool:
    from reprollm.core.context import AuditContext
    from reprollm.core.deps import _FORMAT_LOCK_NAMES, _is_requirements_name
    from reprollm.core.errors import UserError
    from reprollm.core.project_rules import load_project_rules
    from reprollm.core.saved_command import parse_saved_command
    from reprollm.core.yaml_io import load_manifest
    from reprollm.run.capture import declared_files

    for directory in (".git", ".reprollm", ".venv", "venv"):
        if target.is_relative_to((root / directory).resolve()):
            return True
    if target in {(root / name).resolve() for name in ("reprollm.yaml", "reprollm.lock")}:
        return True
    if target.exists() and target.suffix.lower() in {".py", ".sh"}:
        return True
    manifest = load_manifest(root / "reprollm.yaml")
    project_rules = load_project_rules(root)

    def associated(value: str, base: Path = root) -> bool:
        try:
            candidate = _path(value, base).resolve()
            return target == candidate or (candidate.is_dir() and target.is_relative_to(candidate))
        except (OSError, RuntimeError, ValueError):
            return False

    def argv_input(argv: list[str], cwd: Path) -> bool:
        return any(
            associated(candidate, cwd)
            for token in argv
            for candidate in (
                [token, token.split("=", 1)[1]]
                if token.startswith("--") and "=" in token
                else [token]
            )
        )

    if any(associated(item.path) for item in declared_files(manifest, project_rules)):
        return True
    if manifest.execution is not None and manifest.execution.command:
        try:
            argv = parse_saved_command(manifest.execution.command)
        except UserError:
            argv = []
        if argv_input(argv, root / (manifest.execution.cwd or ".")):
            return True
    if selected is not None:
        if any(associated(item.path) for item in [*selected.files, *selected.artifacts]):
            return True
        if argv_input(selected.command.argv, root / selected.command.cwd):
            return True
        if selected.input_capture is not None and any(
            associated(item.path) for item in selected.input_capture.checks
        ):
            return True
    native_export: Any = importlib.import_module("reprollm.cli.export")
    lock = native_export._load_lock(root)
    if lock is not None and any(associated(item.path) for item in lock.files):
        return True

    def contains(value: Any, key: str = "") -> bool:
        if isinstance(value, dict):
            if (
                value.get("provider") == "local"
                and isinstance(value.get("id"), str)
                and associated(value["id"])
            ):
                return True
            return any(contains(child, name) for name, child in value.items())
        if isinstance(value, list):
            return any(contains(child, key) for child in value)
        path_fields = {
            "path",
            "config_files",
            "implementation",
            "chat_template",
            "threat_model",
            "refusal",
            "asr",
        }
        if (
            key in path_fields
            and isinstance(value, str)
            and value
            and not Path(value).is_absolute()
        ):
            return associated(value)
        return False

    if contains(manifest.model_dump(mode="json")):
        return True
    ctx = AuditContext(root, manifest=manifest, project_rules=project_rules)
    files = ctx.fs.analysis_files()
    # Source ownership does not expire at a static size or AST budget boundary.
    source_paths = [path for path in ctx.fs._walk() if path.lower().endswith((".py", ".sh"))]
    dependency_paths = [
        path
        for path in files
        if Path(path).name
        in {*_FORMAT_LOCK_NAMES, "pyproject.toml", "Pipfile", "environment.yml", "environment.yaml"}
        or _is_requirements_name(path)
    ]
    if any(associated(path) for path in [*source_paths, *dependency_paths]):
        return True
    if _generated_export_artifact(target):
        return False
    detected_paths = [
        evidence.path
        for profile in ctx.detection.profiles
        for evidence in profile.evidence
        if evidence.path
    ]
    detected_paths.extend(hint.path for hint in ctx.detection.hints.hf_ids)
    return any(associated(path) for path in detected_paths)


def _generated_export_artifact(target: Path) -> bool:
    if not target.is_file() or target.stat().st_size > 2 * 1024 * 1024:
        return False
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    lines = text.splitlines()
    if (
        len(lines) >= 3
        and lines[0].startswith("# Reproducibility statement — ")
        and lines[2].startswith(
            "Generated by [ReproLLM](https://github.com/EnumaElish123/ReproLLM) "
        )
    ):
        return True
    try:
        document = json.loads(text)
    except (ValueError, RecursionError):
        return False
    # An instance may declare $schema while retaining actual experiment values.
    # Only a definition-shaped object with schema keywords can override keyword
    # detection; explicit manifest/run/lock associations were checked first.
    schema_keywords = {
        "$schema",
        "$id",
        "$ref",
        "$defs",
        "definitions",
        "$comment",
        "$anchor",
        "$dynamicAnchor",
        "$dynamicRef",
        "$vocabulary",
        "title",
        "description",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "patternProperties",
        "dependentRequired",
        "dependentSchemas",
        "unevaluatedProperties",
        "propertyNames",
        "minProperties",
        "maxProperties",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "if",
        "then",
        "else",
        "examples",
        "default",
        "deprecated",
        "readOnly",
        "writeOnly",
        "enum",
        "const",
        "format",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "items",
        "prefixItems",
        "additionalItems",
        "unevaluatedItems",
        "minItems",
        "maxItems",
        "uniqueItems",
        "contains",
        "minContains",
        "maxContains",
        "contentEncoding",
        "contentMediaType",
        "contentSchema",
        "dependencies",
        "$recursiveRef",
        "$recursiveAnchor",
    }
    if not (
        isinstance(document, dict)
        and document.get("type") == "object"
        and isinstance(document.get("properties"), dict)
    ):
        return False
    pending: list[Any] = [document]
    while pending:
        definition = pending.pop()
        if isinstance(definition, bool):
            continue
        if not isinstance(definition, dict) or not set(definition).issubset(schema_keywords):
            return False
        for key in (
            "$schema",
            "$id",
            "$ref",
            "$comment",
            "$anchor",
            "$dynamicAnchor",
            "$dynamicRef",
            "$recursiveRef",
            "title",
            "description",
            "format",
            "pattern",
            "contentEncoding",
            "contentMediaType",
        ):
            if key in definition and not isinstance(definition[key], str):
                return False
        for key in ("readOnly", "writeOnly", "deprecated", "uniqueItems", "$recursiveAnchor"):
            if key in definition and type(definition[key]) is not bool:
                return False
        for key in (
            "minLength",
            "maxLength",
            "minProperties",
            "maxProperties",
            "minItems",
            "maxItems",
            "minContains",
            "maxContains",
        ):
            if key in definition and (type(definition[key]) is not int or definition[key] < 0):
                return False
        for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"):
            if key in definition and type(definition[key]) not in {int, float}:
                return False
        if "type" in definition:
            types = definition["type"]
            types = types if isinstance(types, list) else [types]
            if not types or any(
                not isinstance(kind, str)
                or kind not in {"object", "array", "string", "number", "integer", "boolean", "null"}
                for kind in types
            ):
                return False
        if "required" in definition and (
            not isinstance(definition["required"], list)
            or not all(isinstance(name, str) for name in definition["required"])
        ):
            return False
        if "dependentRequired" in definition:
            required = definition["dependentRequired"]
            if not isinstance(required, dict) or any(
                not isinstance(names, list) or not all(isinstance(name, str) for name in names)
                for names in required.values()
            ):
                return False
        if "$vocabulary" in definition:
            vocabulary = definition["$vocabulary"]
            if not isinstance(vocabulary, dict) or any(
                type(flag) is not bool for flag in vocabulary.values()
            ):
                return False
        for key in ("enum", "examples"):
            if key in definition and not isinstance(definition[key], list):
                return False
        for key in ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas"):
            if key in definition:
                mapping = definition[key]
                if not isinstance(mapping, dict):
                    return False
                pending.extend(mapping.values())
        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            if key in definition:
                alternatives = definition[key]
                if not isinstance(alternatives, list):
                    return False
                pending.extend(alternatives)
        for key in (
            "items",
            "additionalItems",
            "additionalProperties",
            "unevaluatedProperties",
            "unevaluatedItems",
            "propertyNames",
            "contains",
            "not",
            "if",
            "then",
            "else",
            "contentSchema",
        ):
            if key in definition:
                child = definition[key]
                if key == "items" and isinstance(child, list):
                    pending.extend(child)
                else:
                    pending.append(child)
        if "dependencies" in definition:
            dependencies = definition["dependencies"]
            if not isinstance(dependencies, dict):
                return False
            for child in dependencies.values():
                if isinstance(child, list):
                    if not all(isinstance(item, str) for item in child):
                        return False
                else:
                    pending.append(child)
    return True


@contextlib.contextmanager
def _guard_export_reader(reads: ReadGuard) -> Iterator[None]:
    native_export: Any = importlib.import_module("reprollm.cli.export")
    original_reader = native_export.read_run_record

    def guarded_reader(path: Path) -> Any:
        reads.file(path, bundle=path.parent)
        return original_reader(path)

    # Selection and parsing remain native. This isolated worker supplies the
    # authorization check before the selector can open an external record.
    native_export.read_run_record = guarded_reader
    try:
        yield
    finally:
        native_export.read_run_record = original_reader


def _export_sources(request: Request, root: Path, reads: ReadGuard) -> tuple[Any, Path | None]:
    from reprollm.core.paths import resolve_project_file

    native_export: Any = importlib.import_module("reprollm.cli.export")
    for name in (
        "reprollm.yaml",
        "reprollm.lock",
        ".reprollm/config.yaml",
        ".reprollm/project-rules.yaml",
    ):
        reads.file(root / name)
    reads.directory(root / ".reprollm/runs")
    with _guard_export_reader(reads):
        selected, directory = native_export._select_run(root, request.options.get("run"))
    if selected is not None and directory is not None:
        for reference in (selected.manifest, selected.lock):
            if reference is not None:
                contained = resolve_project_file(directory, reference.snapshot)
                if contained is not None:
                    reads.file(directory / reference.snapshot, bundle=directory)
    return selected, directory


def query_input_files(request: Request, root: Path) -> list[Path]:
    """Re-read only the authorized native export closure for cursor binding."""
    if request.action != "export":
        return []
    reads = ReadGuard(request, root)
    _export_sources(request, root, reads)
    reads.check()
    return list(
        dict.fromkeys(
            path for item in reads.files.values() for path in (item.declared, item.target)
        )
    )


@contextlib.contextmanager
def _private_export(sanitize: DisplaySanitizer) -> Iterator[list[dict[str, Any]]]:
    from skill_audit_display import _field_value, private_binding_reports
    from skill_diff_display import project_leaf_value
    from skill_run_display import mask_command_argv

    exporter: Any = importlib.import_module("reprollm.export.exporter")
    original = exporter.build_input
    diagnostics: list[dict[str, Any]] = []
    total = 0

    def private_input(
        manifest: Any,
        lock: Any,
        run: Any,
        state: Any,
        *,
        reprollm_version: str,
        audit_report: Any = None,
    ) -> Any:
        nonlocal total
        # Selection, merge and every audit comparison have already used raw values.
        # Only this native renderer receives an isolated private display view.
        private_state = state.model_copy(deep=True)

        def project(leaf: Any, path: str) -> None:
            nonlocal total
            value, changed = project_leaf_value(
                leaf.value, path, leaf, (run,) if run is not None else (), sanitize
            )
            leaf.value = _field_value(value, path, sanitize)
            if leaf.value != value:
                changed += 1
            total += changed
            for alternative in leaf.alternatives:
                project(alternative, path)

        for path, leaf in private_state.flatten().items():
            project(leaf, path)
        private_run = run
        if run is not None:
            argv, changed = mask_command_argv(run.command.argv)
            total += changed
            private_run = run.model_copy(
                update={"command": run.command.model_copy(update={"argv": argv}, deep=True)},
                deep=True,
            )
        return original(
            manifest,
            lock,
            private_run,
            private_state,
            reprollm_version=reprollm_version,
            audit_report=audit_report,
        )

    exporter.build_input = private_input
    try:
        with private_binding_reports(sanitize) as audit_diagnostics:
            yield diagnostics
        diagnostics.extend(audit_diagnostics)
    finally:
        exporter.build_input = original
        if total:
            diagnostics.append({"code": "display_value_transformation", "count": total})


def _prepare_export(
    request: Request,
    root: Path,
    stage: Path,
    runner: CliRunner,
    reads: ReadGuard,
    sanitize: DisplaySanitizer,
) -> tuple[dict[str, Any], list[Artifact], list[dict[str, Any]]] | Reply:
    selected, directory = _export_sources(request, root, reads)
    declared = _path(request.options.get("output", "REPRODUCIBILITY.md"), root)
    destination = _artifact(request, root, declared, b"", role="report", mode=0o600)
    if _export_input_target(root, destination.target, selected):
        raise WriteError("report_target_is_research_input")
    target = stage / "report.md"
    argv = [
        "export",
        str(root),
        "--output",
        str(target),
        "--template",
        request.options.get("template", "default"),
    ]
    if directory is not None:
        # The CLI selects directory names; a legacy content ID need not match it.
        argv += ["--run", directory.name]
    reads.check()
    with _guard_export_reader(reads), _private_export(sanitize) as display_diagnostics:
        result = runner(_global_flags(request) + argv, root)
    reads.check()
    if result.exit_code:
        return Reply(
            request.action,
            invocation="user_error" if result.exit_code == 2 else "internal_error",
            cli_exit_code=result.exit_code,
            complete=False,
            diagnostics=display_diagnostics
            + ([{"code": "cli_stderr", "text": result.stderr}] if result.stderr else []),
        )
    artifacts = [
        dataclasses.replace(
            destination,
            content=target.read_bytes(),
            mode=destination.mode
            if destination.expected is not None
            else stat.S_IMODE(target.stat().st_mode),
        )
    ]
    return (
        {
            "template": request.options.get("template", "default"),
            "selected_run_id": selected.run_id if selected else None,
            "selected_run_locator": directory.name if directory else None,
            "document": target.read_text(encoding="utf-8"),
        },
        artifacts,
        display_diagnostics
        + ([{"code": "cli_stderr", "text": result.stderr}] if result.stderr else []),
    )


def _global_flags(request: Request) -> list[str]:
    return [
        "--" + name.replace("_", "-")
        for name in ("no_color", "verbose", "quiet")
        if request.options.get(name)
    ]


def _prepare_schema(
    request: Request, root: Path, stage: Path, runner: CliRunner
) -> tuple[dict[str, Any], list[Artifact], list[dict[str, Any]]] | Reply:
    from reprollm.cli.schema import SCHEMA_MODELS

    names = sorted(name + ".schema.json" for name in SCHEMA_MODELS)
    declared = _path(request.options.get("out", "schemas"), root)
    if declared.is_symlink():
        raise WriteError("schema_output_symlink_refused")
    if (
        declared.resolve() == root
        or declared.resolve().is_relative_to(root / ".git")
        or declared.resolve().is_relative_to(root / ".reprollm")
    ):
        raise WriteError("schema_output_is_research_input")
    destinations = [
        _artifact(
            request,
            root,
            declared / name,
            b"",
            role="schema:" + name,
            mode=0o600,
            external_directory=declared,
        )
        for name in names
    ]
    generated = stage / "schemas"
    result = runner(_global_flags(request) + ["schema", "export", "--out", str(generated)], root)
    if result.exit_code:
        return Reply(
            request.action,
            invocation="user_error" if result.exit_code == 2 else "internal_error",
            cli_exit_code=result.exit_code,
            complete=False,
            diagnostics=[{"code": "cli_stderr", "text": result.stderr}] if result.stderr else [],
        )
    if sorted(path.name for path in generated.iterdir()) != names or len(names) != 10:
        raise WriteError("native_schema_inventory_mismatch")
    artifacts = [
        dataclasses.replace(
            destination,
            content=(generated / name).read_bytes(),
            mode=destination.mode
            if destination.expected is not None
            else stat.S_IMODE((generated / name).stat().st_mode),
        )
        for name, destination in zip(names, destinations, strict=True)
    ]
    return (
        {"schema_files": names, "schema_count": 10},
        artifacts,
        [{"code": "cli_stderr", "text": result.stderr}] if result.stderr else [],
    )


def _plan(
    request: Request, root: Path, artifacts: list[Artifact], signature: str, identity: str
) -> str:
    options = {name: value for name, value in request.options.items() if name != "preview"}
    return _sha(
        _json(
            {
                "schema_version": 1,
                "action": request.action,
                "root": _sha(str(root).encode("utf-8")),
                "options": options,
                "source": signature,
                "tool": identity,
                "helper": _sha(Path(__file__).read_bytes()),
                "artifacts": [
                    {
                        "role": item.role,
                        "target": _sha(str(item.target).encode("utf-8")),
                        "old": item.expected,
                        "new": _sha(item.content),
                        "mode": item.mode,
                        "parents": [
                            [_sha(str(parent.path).encode("utf-8")), list(parent.identity)]
                            for parent in item.parents
                        ],
                        "missing_parents": [
                            _sha(str(path).encode("utf-8")) for path in item.missing_parents
                        ],
                    }
                    for item in artifacts
                ],
            }
        )
    )


def _descriptions(prepared: PreparedWrite) -> list[dict[str, Any]]:
    return [
        {
            "role": item.role,
            "path": _label(item.target, prepared.root),
            "expected_old_sha256": item.expected,
            "new_sha256": _sha(item.content),
            "approval_required": item.approval_required,
        }
        for item in prepared.artifacts
    ]


def _remaining(published: list[Published], root: Path) -> list[str]:
    result = []
    for item in published:
        try:
            if _hash_file(item.artifact.target) == _sha(item.artifact.content):
                result.append(_label(item.artifact.target, root))
        except (OSError, ValueError):
            continue
    return result


def _preserved_changes(published: list[Published], root: Path) -> list[str]:
    result = []
    for item in published:
        try:
            info = item.artifact.target.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or (info.st_dev, info.st_ino) != item.identity
                or _hash_file(item.artifact.target) != _sha(item.artifact.content)
            ):
                result.append(_label(item.artifact.target, root))
        except (OSError, ValueError):
            continue
    return result


def execute_write(
    request: Request,
    *,
    root: Path,
    state_home: Path,
    identity: str,
    cli_runner: CliRunner | None = None,
    source_signature: SourceSignature | None = None,
    display_sanitizer: DisplaySanitizer | None = None,
) -> Reply:
    """Prepare native artifact bytes and publish only the explicitly owned set."""
    from reprollm.core.errors import UserError

    if request.action not in WRITE_ACTIONS:
        return blocked(request.action, "action_unavailable")
    if request.response.cursor:
        return blocked(request.action, "write_cursor_requires_runtime_snapshot")
    if not request.options.get("preview", False) and not request.grants.write:
        return blocked(request.action, "write_authorization_required", needs_authorization=True)
    if cli_runner is None or source_signature is None:
        # The worker passes its already loaded runtime functions explicitly.
        from skill_runtime import input_signature, invoke_cli

        cli_runner = cli_runner or invoke_cli
        source_signature = source_signature or input_signature
    published: list[Published] = []
    directories: list[DirectoryIdentity] = []
    prepared: PreparedWrite | None = None
    try:
        root = root.resolve(strict=True)
        state = _owned_state(state_home)
        reads = ReadGuard(request, root)
        before = source_signature(root, [], state)
        with tempfile.TemporaryDirectory(prefix="prepare-", dir=state / "staging") as name:
            stage = Path(name)
            if request.action == "init":
                result = _prepare_init(request, root, stage)
            elif request.action == "export":
                if display_sanitizer is None:
                    from skill_runtime import _sanitize

                    def display_sanitizer(value: Any, notes: list[dict[str, Any]]) -> Any:
                        return _sanitize(value, root, action="runs.show", diagnostics=notes)

                result = _prepare_export(request, root, stage, cli_runner, reads, display_sanitizer)
            else:
                result = _prepare_schema(request, root, stage, cli_runner)
            if isinstance(result, Reply):
                return result
            data, artifacts, diagnostics = result
        if source_signature(root, [], state) != before:
            raise WriteError("write_inputs_changed_during_prepare")
        reads.check()
        if len({item.target for item in artifacts}) != len(artifacts):
            raise WriteError("write_target_alias_collision")
        prepared = PreparedWrite(
            request.action,
            root,
            artifacts,
            _sha((before + reads.fingerprint()).encode("utf-8")),
            _plan(
                request,
                root,
                artifacts,
                _sha((before + reads.fingerprint()).encode("utf-8")),
                identity,
            ),
            data,
            diagnostics,
        )
        data.update(
            {
                "phase": "prepared",
                "plan_hash": prepared.plan_hash,
                "artifacts": _descriptions(prepared),
                "artifacts_written": [],
            }
        )
        if request.options.get("preview", False):
            return Reply(request.action, cli_exit_code=0, data=data, diagnostics=diagnostics)
        expected_plan = getattr(request.grants, "plan_hash", None)
        if expected_plan is not None and expected_plan != prepared.plan_hash:
            raise WriteError("write_plan_changed")
        if any(item.approval_required for item in artifacts):
            raise WriteError("write_target_approval_required", authorization=True)
        with _project_lock(state, root):
            if source_signature(root, [], state) != before:
                raise WriteError("write_inputs_changed_before_publish")
            reads.check()
            for artifact in artifacts:
                _check_artifact(artifact)
            for artifact in artifacts:
                ready = _make_directories(artifact, directories)
                publish_artifact(ready, published)
        data.update({"phase": "applied", "artifacts_written": _remaining(published, root)})
        return Reply(request.action, cli_exit_code=0, data=data, diagnostics=diagnostics)
    except UserError as error:
        return _native_error(request, str(error))
    except (WriteError, OSError, ValueError, RecursionError) as error:
        if request.action == "init":
            _rollback_created(published, directories)
        code = str(error) if isinstance(error, WriteError) else "write_input_or_publication_failed"
        reply = blocked(
            request.action,
            code,
            needs_authorization=isinstance(error, WriteError) and error.authorization,
        )
        if prepared is not None:
            reply.cli_exit_code = prepared.cli_exit_code
            reply.data = {
                **prepared.data,
                "phase": "partial" if published else "prepared",
                "artifacts_written": _remaining(published, root),
                "preserved_changed_targets": _preserved_changes(published, root),
                "artifact_publication_attempted": bool(published),
            }
            reply.diagnostics.extend(prepared.diagnostics)
        return reply
