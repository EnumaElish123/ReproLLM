"""Verified read-only CLI execution and bounded private result delivery for the Skill."""

from __future__ import annotations

import argparse
import contextlib
import copy
import dataclasses
import getpass
import hashlib
import importlib
import io
import json
import os
import re
import socket
import stat
import subprocess
import sys
import time
import unicodedata
import uuid
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_request import (  # noqa: E402
    BASE_ACTIONS,
    LOCAL_WRITE_ACTIONS,
    MAX_REPLY_BYTES,
    MAX_REQUEST_BYTES,
    OPERATION_ACTIONS,
    WRITE_ACTIONS,
    Reply,
    Request,
    RequestError,
    blocked,
    encode_reply,
    error_reply,
    parse_request,
    publication_summary,
)

READONLY_ACTIONS = frozenset(
    {
        "audit",
        "doctor",
        "profiles.list",
        "profiles.show",
        "init.tasks",
        "runs.list",
        "runs.show",
        "diff",
        "run.preview",
    }
)
LOCAL_READ_ACTIONS = frozenset({"rules.list", "rules.show", "rules.candidates"})
LOCAL_ACTIONS = LOCAL_READ_ACTIONS | LOCAL_WRITE_ACTIONS
AVAILABLE_ACTIONS = (
    BASE_ACTIONS | READONLY_ACTIONS | WRITE_ACTIONS | LOCAL_ACTIONS | OPERATION_ACTIONS
)
REQUIRED_CAPABILITIES = frozenset({"contextual_word_scan"})
MAX_CAPTURE_BYTES = 64 * 1024 * 1024
MAX_INPUT_ENTRIES = 50_000
MAX_CONTENT_BYTES = 16 * 1024 * 1024
SNAPSHOT_TTL_SECONDS = 3600
_CURSOR = re.compile(r"([0-9a-f]{64}):(items|fragment):([0-9]{1,12})\Z")
_CACHE_OWNER = {"schema_version": 1, "owner": "reprollm-skill-responses"}
_SNAPSHOT_PRODUCER = "reprollm-skill-readonly"
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "node_modules",
    }
)
_TEXT_SUFFIXES = frozenset({".py", ".yaml", ".yml", ".json", ".toml", ".txt", ".md", ".lock"})
CliRunner = Callable[[list[str], Path], "CliResult"]


@dataclass(frozen=True)
class CliResult:
    exit_code: int
    stdout: str
    stderr: str


class ScopeError(ValueError):
    """Fixed safe diagnostic; never include source paths or raw exception text."""


def _json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def helper_code_identity(directory: Path | None = None) -> str:
    """Bind snapshots to every trusted executable sibling, including display policy."""
    scripts = directory or Path(__file__).resolve().parent
    files = []
    for path in sorted(scripts.glob("*.py")):
        if path.is_symlink():
            raise ScopeError("trusted_helper_symlink_refused")
        if not path.is_file():
            raise ScopeError("trusted_helper_file_required")
        files.append([path.name, _sha(path.read_bytes())])
    return _sha(_json(files))


def _authorized(path: Path, request: Request) -> bool:
    return any(Path(item).resolve() == path for item in request.grants.external_paths)


def project_root(request: Request) -> Path:
    if request.project is None:
        raise ScopeError("project_required")
    try:
        root = Path(request.project).resolve(strict=True)
    except (OSError, RuntimeError):
        raise ScopeError("project_directory_required") from None
    if not root.is_dir():
        raise ScopeError("project_directory_required")
    # Native root discovery must not broaden a caller-selected subdirectory.
    for ancestor in (root, *root.parents):
        if (ancestor / "reprollm.yaml").exists() or (ancestor / ".git").exists():
            if ancestor != root and not _authorized(ancestor, request):
                raise ScopeError("ancestor_project_scope_required")
            return ancestor
    return root


def _resolve_path(value: str, root: Path) -> Path:
    item = Path(value)
    return (item if item.is_absolute() else root / item).resolve()


def _diff_read_files(path: Path) -> list[Path]:
    from reprollm.core.paths import is_relative_project_path, resolve_project_file
    from reprollm.run.codec import RunRecordError, read_run_record

    primary = path / "run.json" if path.is_dir() else path
    result = [primary]
    if primary.suffix != ".json":
        sidecar = primary.parent / "reprollm.yaml"
        result.append(sidecar)
        resolved = resolve_project_file(primary.parent, "reprollm.yaml")
        if resolved is not None and resolved != sidecar:
            result.append(resolved)
        return result
    try:
        record, _ = read_run_record(primary)
    except (RunRecordError, OSError, ValueError):
        return result
    for reference in (record.manifest, record.lock):
        if reference is None or not is_relative_project_path(reference.snapshot):
            continue
        declared = primary.parent / reference.snapshot
        result.append(declared)
        resolved = resolve_project_file(primary.parent, reference.snapshot)
        if resolved is not None and resolved != declared:
            result.append(resolved)
    return result


def _external_inputs(request: Request, root: Path) -> list[Path]:
    inputs: list[Path] = []
    if request.action == "export":
        from skill_writes import WriteError, query_input_files

        from reprollm.core.errors import UserError

        try:
            inputs.extend(query_input_files(request, root))
        except WriteError as error:
            raise ScopeError(str(error)) from None
        except UserError:
            if request.response.cursor:
                raise ScopeError("response_snapshot_stale") from None
            # Let the native producer return its actionable selection error.
    if request.action == "diff":
        from reprollm.core.errors import UserError
        from reprollm.core.paths import RUNS_DIR
        from reprollm.run.reader import filter_runs, list_runs, read_run

        for key in ("a", "b"):
            value = request.options.get(key)
            if not isinstance(value, str):
                continue
            candidate = _resolve_path(value, root)
            if candidate.exists() or Path(value).is_absolute() or "/" in value or "\\" in value:
                if not candidate.is_relative_to(root) and not _authorized(candidate, request):
                    raise ScopeError("external_input_scope_required")
                inputs.extend(_diff_read_files(candidate))
            else:
                try:
                    record, _ = read_run(root, value)
                except UserError:
                    continue
                inputs.extend(_diff_read_files(root / RUNS_DIR / record.run_id / "run.json"))
        if request.options.get("latest_successful"):
            try:
                records, _ = list_runs(root)
                selected = filter_runs(
                    records, name=request.options.get("name"), outcome="success", limit=2
                )
            except UserError:
                selected = []
            for record in selected:
                inputs.extend(_diff_read_files(root / RUNS_DIR / record.run_id / "run.json"))
    if request.action == "run.preview" and isinstance(request.options.get("cwd"), str):
        cwd = _resolve_path(request.options["cwd"], root)
        if not cwd.is_relative_to(root) and not _authorized(cwd, request):
            raise ScopeError("external_working_directory_scope_required")
        for ancestor in (cwd, *cwd.parents):
            if (ancestor / "reprollm.yaml").exists():
                if not ancestor.is_relative_to(root) and not _authorized(ancestor, request):
                    raise ScopeError("ancestor_project_scope_required")
                break
        if not cwd.is_relative_to(root):
            inputs.append(cwd)
    return list(dict.fromkeys(inputs))


def input_signature(root: Path, external: list[Path], cache_home: Path) -> str:
    """Hash the finite file view, with bounded content hashing plus file metadata."""
    digest = hashlib.sha256()
    budget = MAX_CONTENT_BYTES
    entries = 0
    cache = cache_home.resolve()

    def add(path: Path, label: str, *, critical: bool = False) -> None:
        nonlocal budget, entries
        entries += 1
        if entries > MAX_INPUT_ENTRIES:
            raise ScopeError("input_signature_entry_limit")
        if not path.exists() and not path.is_symlink():
            digest.update(
                _json(
                    [
                        label,
                        "missing",
                        _sha(str(path.resolve()).encode("utf-8")) if critical else None,
                    ]
                )
            )
            return
        info = path.lstat()
        row: list[Any] = [label, stat.S_IFMT(info.st_mode), info.st_size, info.st_mtime_ns]
        if critical:
            row.append(_sha(str(path.resolve()).encode("utf-8")))
        if stat.S_ISLNK(info.st_mode):
            row.append(_sha(os.readlink(path).encode("utf-8")))
        elif critical and stat.S_ISREG(info.st_mode):
            if info.st_size > MAX_CAPTURE_BYTES:
                raise ScopeError("input_signature_content_limit")
            content = hashlib.sha256()
            total = 0
            with path.open("rb") as stream:
                while block := stream.read(65536):
                    total += len(block)
                    if total > MAX_CAPTURE_BYTES:
                        raise ScopeError("input_signature_content_limit")
                    content.update(block)
            after = path.stat()
            if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ScopeError("input_source_changed")
            row.append(content.hexdigest())
        elif (
            stat.S_ISREG(info.st_mode)
            and info.st_size <= min(2 * 1024 * 1024, budget)
            and (path.suffix.lower() in _TEXT_SUFFIXES or label.startswith("git:"))
        ):
            raw = path.read_bytes()
            budget -= len(raw)
            row.append(_sha(raw))
        digest.update(_json(row))

    def walk(base: Path, prefix: str) -> None:
        if base.is_file():
            add(base, prefix)
            return
        for folder, directories, files in os.walk(base, followlinks=False):
            parent = Path(folder)
            directories[:] = sorted(
                name
                for name in directories
                if name not in _SKIP_DIRS and (parent / name).resolve() != cache
            )
            for name in sorted([*directories, *files]):
                path = parent / name
                if path.resolve() == cache:
                    continue
                add(path, prefix + path.relative_to(base).as_posix())

    git = root / ".git"
    if git.is_file():
        add(git, "git:worktree")
        directive = git.read_bytes()[:8192].decode("utf-8").strip()
        if directive.startswith("gitdir: "):
            git = _resolve_path(directive[8:], root)
    metadata_roots = [git] if git.is_dir() else []
    if git.is_dir() and (git / "commondir").is_file():
        add(git / "commondir", "git:commondir")
        common = (git / "commondir").read_bytes()[:8192].decode("utf-8").strip()
        metadata_roots.append(_resolve_path(common, git))
    for index, metadata in enumerate(metadata_roots):
        for name in ("HEAD", "index", "config", "packed-refs"):
            path = metadata / name
            if path.is_file():
                add(path, f"git:{index}:" + name)
        if (metadata / "refs").is_dir():
            walk(metadata / "refs", f"git:{index}:refs/")
    for index, path in enumerate(external):
        if path.is_dir():
            walk(path, f"consumed:{index}:")
        else:
            add(path, f"consumed:{index}:", critical=True)
    walk(root, "project:")
    return digest.hexdigest()


def _request_identity(request: Request) -> str:
    value = dataclasses.asdict(request)
    value.pop("response")
    return _sha(_json(value))


@dataclass(frozen=True)
class _ReportTarget:
    target: Path
    expected: str | None
    path_bindings: tuple[Path, ...]


def _output_target(request: Request, root: Path) -> _ReportTarget | None:
    value = request.options.get("output") if request.action == "audit" else None
    if value is None:
        return None
    if request.options.get("format", "json") != "json":
        raise ScopeError("audit_output_requires_json")
    if not request.grants.write:
        raise ScopeError("report_write_authorization_required")
    declared = Path(value)
    declared = declared if declared.is_absolute() else root / declared
    if declared.is_symlink():
        raise ScopeError("report_target_symlink_refused")
    target = declared.resolve()
    external_bindings = tuple(
        Path(item).absolute()
        for item in request.grants.external_paths
        if Path(item).resolve() == target
    )
    if not target.is_relative_to(root) and not external_bindings:
        raise ScopeError("external_output_scope_required")
    matches = [
        (Path(path) if Path(path).is_absolute() else root / path, expected)
        for path, expected in request.grants.expected_hashes.items()
        if _resolve_path(path, root) == target
    ]
    if len(matches) != 1:
        raise ScopeError("report_target_approval_required")
    approved, expected = matches[0]
    current = _sha(target.read_bytes()) if target.exists() else None
    if current != expected:
        raise ScopeError("report_target_changed")
    if not target.parent.is_dir():
        raise ScopeError("report_parent_directory_required")
    return _ReportTarget(
        target,
        expected,
        (declared, approved, *(external_bindings if not target.is_relative_to(root) else ())),
    )


def _check_report_mapping(approval: _ReportTarget) -> None:
    try:
        if any(path.resolve() != approval.target for path in approval.path_bindings):
            raise ScopeError("report_target_mapping_changed")
    except (OSError, RuntimeError):
        raise ScopeError("report_target_mapping_changed") from None


def _write_report(approval: _ReportTarget, raw: bytes) -> None:
    target, expected = approval.target, approval.expected
    _check_report_mapping(approval)
    if target.parent.resolve() != target.parent or target.resolve() != target:
        raise ScopeError("report_parent_changed")
    temporary = target.with_name("." + target.name + "." + uuid.uuid4().hex)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if target.parent.resolve() != target.parent:
            raise ScopeError("report_parent_changed")
        if (
            target.is_symlink()
            or (_sha(target.read_bytes()) if target.exists() else None) != expected
        ):
            raise ScopeError("report_target_changed")
        _check_report_mapping(approval)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def command_args(request: Request, root: Path) -> tuple[list[str], bool]:
    options = request.options
    prefix = [
        "--" + key.replace("_", "-") for key in ("no_color", "verbose", "quiet") if options.get(key)
    ]
    action = request.action
    if action == "audit":
        argv = ["audit", str(root), "--format", options.get("format", "json")]
        for key in ("fail_on", "level"):
            if key in options:
                argv += ["--" + key.replace("_", "-"), options[key]]
        if "profiles" in options:
            argv += ["--profiles", ",".join(options["profiles"])]
        if options.get("show_passed") is not None:
            argv += ["--show-passed" if options["show_passed"] else "--no-show-passed"]
        for key in ("show_skipped", "details"):
            if options.get(key):
                argv.append("--" + key.replace("_", "-"))
        return prefix + argv, options.get("format", "json") == "json"
    if action == "doctor":
        argv = ["doctor", *(["--json"] if options.get("json", True) else [])]
        if options.get("no_color"):
            argv.append("--no-color")
        return prefix + argv, options.get("json", True)
    if action == "profiles.show":
        return prefix + ["profiles", "show", "--", options["name"]], False
    if action == "init.tasks":
        return prefix + ["init", str(root), "--list-tasks"], False
    if action == "profiles.list":
        return prefix + [
            "profiles",
            "list",
            *(["--json"] if options.get("json", True) else []),
        ], options.get("json", True)
    if action in {"runs.list", "runs.show"}:
        argv = ["runs", "list" if action.endswith("list") else "show"]
        if action.endswith("list"):
            for key in ("name", "status", "outcome", "limit"):
                if key in options:
                    argv += ["--" + key, str(options[key])]
        if options.get("json", True):
            argv.append("--json")
        if action.endswith("show"):
            argv += ["--", options["run_id"]]
        return prefix + argv, options.get("json", True)
    if action == "diff":
        argv = ["diff"]
        positionals = [options[key] for key in ("a", "b") if key in options]
        argv += ["--format", options.get("format", "json")]
        if options.get("latest_successful"):
            argv.append("--latest-successful")
        for key in ("name", "min_severity", "fail_on"):
            if key in options:
                argv += ["--" + key.replace("_", "-"), options[key]]
        if positionals:
            argv += ["--", *positionals]
        return prefix + argv, options.get("format", "json") == "json"
    raise ScopeError("action_unavailable")


class _Capture(io.StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.bytes = 0

    def write(self, text: str) -> int:
        self.bytes += len(text.encode("utf-8"))
        if self.bytes > MAX_CAPTURE_BYTES:
            raise ScopeError("readonly_output_limit")
        return super().write(text)


def invoke_cli(argv: list[str], root: Path) -> CliResult:
    from reprollm.cli.main import cli

    previous, previous_cwd = sys.argv, Path.cwd()
    stdout, stderr = _Capture(), _Capture()
    code = 0
    try:
        os.chdir(root)
        sys.argv = ["reprollm", *argv]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                cli()
            except SystemExit as error:
                code = error.code if type(error.code) is int else (0 if error.code is None else 3)
    finally:
        sys.argv = previous
        os.chdir(previous_cwd)
    return CliResult(code, stdout.getvalue(), stderr.getvalue())


def _preview(request: Request, root: Path) -> CliResult:
    from reprollm.core.errors import UserError
    from reprollm.run.preflight import preview
    from reprollm.run.saved import load_saved_invocation

    options = request.options
    cwd = _resolve_path(options["cwd"], root) if "cwd" in options else root
    argv = options.get("argv")
    try:
        if not argv:
            selected = load_saved_invocation(cwd)
            argv, cwd = selected.argv, selected.cwd
        text = preview(
            argv,
            cwd=cwd,
            capture_output=options.get("capture_output"),
            env_capture=options.get("env_capture"),
            snapshot=not options.get("no_snapshot", False),
        )
        return CliResult(0, text + "\n", "")
    except UserError as error:
        return CliResult(2, "", "error: " + str(error) + "\n")


def _presentation_schema(action: str | None, value: Any) -> dict[str, Any]:
    from pydantic import BaseModel

    from reprollm.schemas.diff_report import DiffReport
    from reprollm.schemas.finding import AuditReport
    from reprollm.schemas.run_record import RunRecord

    if action in WRITE_ACTIONS | LOCAL_WRITE_ACTIONS:
        properties: dict[str, Any] = {
            name: {}
            for name in (
                "profiles",
                "task_candidates",
                "selected_tasks",
                "guidance",
                "accepted_answers",
                "invalid_field",
                "manifest_text",
                "missing_required_fields",
                "plan_hash",
                "artifacts_written",
                "preserved_changed_targets",
                "artifact_publication_attempted",
                "selected_run_id",
                "selected_run_locator",
                "document",
                "schema_files",
                "schema_count",
                "lock",
                "project_rules",
                "summary",
                "stdout",
                "reasons",
                "archive_id",
                "archive_state",
                "archive_available",
            )
        }
        properties["phase"] = {"enum": ["prepared", "applied", "partial", "preparation_failed"]}
        properties["template"] = {"enum": ["default", "neurips", "acl", "acm"]}
        properties["artifacts"] = {
            "type": "array",
            "items": {
                "properties": {
                    name: {}
                    for name in (
                        "role",
                        "path",
                        "expected_old_sha256",
                        "new_sha256",
                        "approval_required",
                    )
                }
            },
        }
        shape: dict[str, Any] = {"properties": properties}
        if action == "lock":
            from reprollm.schemas.lock import Lock

            schema = Lock.model_json_schema()
            shape["$defs"] = schema.get("$defs", {})
            properties["lock"] = schema
        elif action in LOCAL_WRITE_ACTIONS:
            from reprollm.schemas.project_rules import ProjectRules

            schema = ProjectRules.model_json_schema()
            shape["$defs"] = schema.get("$defs", {})
            properties["project_rules"] = schema
        return shape
    models: dict[str, type[BaseModel]] = {
        "audit": AuditReport,
        "diff": DiffReport,
        "runs.show": RunRecord,
    }
    if action in models:
        schema = models[action].model_json_schema()
        if action == "audit" and isinstance(value, dict) and "report" in value:
            return {
                "$defs": schema.get("$defs", {}),
                "properties": {
                    "report": schema,
                    "stdout": {"type": "string"},
                    "artifact": {"type": "string"},
                },
            }
        return schema
    if action == "runs.list":
        return {
            "type": "array",
            "items": {
                "properties": {
                    key: {}
                    for key in (
                        "run_id",
                        "started_at",
                        "status",
                        "exit_code",
                        "duration_seconds",
                        "name",
                        "dirty",
                    )
                }
            },
        }
    if action == "profiles.list":
        return {
            "type": "array",
            "items": {
                "properties": {
                    "name": {},
                    "source": {"enum": ["built-in", "user"]},
                    "description": {},
                }
            },
        }
    if action == "doctor":
        return {
            "properties": {
                "reprollm_version": {},
                "checks": {
                    "type": "array",
                    "items": {
                        "properties": {
                            "name": {},
                            "status": {"enum": ["ok", "warn", "missing"]},
                            "detail": {},
                        }
                    },
                },
            }
        }
    return {}


def _sanitize(
    value: Any,
    root: Path,
    *,
    action: str | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
    context: tuple[str, ...] = (),
) -> Any:
    from skill_run_display import mask_command_argv, mask_secret_env_observation

    from reprollm.core.registry import get_rule
    from reprollm.run.privacy import RunPrivacy
    from reprollm.schemas.run_record import Observation, ObservationSource

    importlib.import_module("reprollm.rules")
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    schema = _presentation_schema(action, value)
    definitions = schema.get("$defs", {})
    transformed_keys = 0
    transformed_values = 0
    collisions = 0

    def controls(text: str) -> str:
        return "".join(
            f"\\u{ord(c):04x}"
            if c not in {"\n", "\t"}
            and (unicodedata.category(c).startswith("C") or c in {"\u2028", "\u2029"})
            else c
            for c in text
        )

    def resolved(shape: dict[str, Any], item: Any) -> dict[str, Any]:
        reference = shape.get("$ref", "")
        if reference.startswith("#/$defs/"):
            return resolved(cast(dict[str, Any], definitions.get(reference[8:], {})), item)
        alternatives = [branch for branch in shape.get("anyOf", ()) if branch.get("type") != "null"]
        if len(alternatives) == 1:
            return resolved(alternatives[0], item)
        for branch in alternatives:
            candidate = resolved(branch, item)
            if isinstance(item, dict) and candidate.get("type") == "object":
                return candidate
            if isinstance(item, list) and candidate.get("type") == "array":
                return candidate
        return shape

    def walk(item: Any, keys: tuple[str, ...], shape: dict[str, Any]) -> Any:
        nonlocal transformed_keys, transformed_values, collisions
        if action == "runs.show" and shape.get("$ref") == "#/$defs/Observation":
            return observation_privacy.value(Observation.model_validate(item), keys)
        shape = resolved(shape, item)
        if isinstance(item, dict):
            properties = shape.get("properties", {})
            additional = shape.get("additionalProperties", {})
            prepared = []
            counts: dict[str, int] = {}
            for key, child in item.items():
                raw_key = str(key)
                safe_key = raw_key if raw_key in properties else controls(privacy.text(raw_key)[0])
                transformed_keys += safe_key != raw_key
                counts[safe_key] = counts.get(safe_key, 0) + 1
                child_schema = properties.get(raw_key, additional)
                prepared.append(
                    (
                        raw_key,
                        safe_key,
                        child,
                        child_schema if isinstance(child_schema, dict) else {},
                    )
                )
            result: dict[str, Any] = {}
            for raw_key, safe_key, child, child_schema in prepared:
                if counts[safe_key] > 1:
                    safe_key += "<KEY:" + _sha(raw_key.encode("utf-8")) + ">"
                    collisions += 1
                while safe_key in result:
                    safe_key += "<KEY:" + _sha((raw_key + safe_key).encode("utf-8")) + ">"
                    collisions += 1
                result[safe_key] = walk(child, (*keys, raw_key), child_schema)
            return result
        if isinstance(item, list):
            if action == "runs.show" and keys == ("command", "argv"):
                item, changed = mask_command_argv(item)
                transformed_values += changed
            child_schema = shape.get("items", {})
            return [
                walk(child, keys, child_schema if isinstance(child_schema, dict) else {})
                for child in item
            ]
        if isinstance(item, str):
            if action == "runs.show" and len(keys) == 3 and keys[:2] == ("environment", "env"):
                item, changed = mask_secret_env_observation(item, "env", keys[2])
                transformed_values += changed
            if item in shape.get("enum", ()) or ("const" in shape and item == shape["const"]):
                return item
            if keys and keys[-1] in {"rule_id", "aliases"} and get_rule(item) is not None:
                return item
            safe_text = controls(str(privacy.value(item, keys)))
            transformed_values += safe_text != item
            return safe_text
        safe_scalar = privacy.value(item, keys)
        transformed_values += safe_scalar != item
        return safe_scalar

    class ObservationPrivacy(RunPrivacy):
        def value(self, item: Any, keys: tuple[str, ...] = ()) -> Any:
            nonlocal transformed_values
            if isinstance(item, Observation):
                masked, changed = mask_secret_env_observation(
                    item.value, item.source.type, item.source.key
                )
                if changed:
                    item = item.model_copy(update={"value": masked})
                    transformed_values += changed
                # Preserve native source.key/config-key context and source reset.
                return super().value(item, keys)
            if isinstance(item, ObservationSource):
                source_shape = (
                    definitions.get("Observation", {}).get("properties", {}).get("source", {})
                )
                return walk(item.model_dump(mode="json", exclude_unset=True), (), source_shape)
            return walk(item, keys, {})

    observation_privacy = ObservationPrivacy(
        root, hostname=socket.gethostname(), username=getpass.getuser()
    )
    safe = walk(value, context, schema)
    if diagnostics is not None:
        if transformed_keys:
            diagnostics.append({"code": "display_key_transformation", "count": transformed_keys})
        if transformed_values:
            diagnostics.append(
                {"code": "display_value_transformation", "count": transformed_values}
            )
        if collisions:
            diagnostics.append({"code": "display_keys_disambiguated", "count": collisions})
    return safe


def _cache_directory(home: Path) -> None:
    if home.is_symlink():
        raise ScopeError("response_cache_symlink_refused")
    marker = home / "owner.json"
    if home.exists() and any(home.iterdir()):
        if marker.is_symlink() or not marker.is_file():
            raise ScopeError("response_cache_ownership_required")
        owner = json.loads(marker.read_bytes())
        if owner != _CACHE_OWNER or type(owner.get("schema_version")) is not int:
            raise ScopeError("response_cache_ownership_required")
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not marker.exists():
        descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_json(_CACHE_OWNER))
    _clean_expired_snapshots(home)


def _clean_expired_snapshots(home: Path) -> None:
    for path in home.glob("*.json"):
        if not re.fullmatch(r"[0-9a-f]{64}", path.stem) or path.is_symlink():
            continue
        try:
            info = path.stat()
            if (
                time.time() - info.st_mtime <= SNAPSHOT_TTL_SECONDS
                or info.st_size > 2 * MAX_CAPTURE_BYTES
            ):
                continue
            raw = path.read_bytes()
            document = json.loads(raw)
            if (
                isinstance(document, dict)
                and _sha(raw) == path.stem
                and type(document.get("schema_version")) is int
                and document["schema_version"] == 1
                and document.get("producer") == _SNAPSHOT_PRODUCER
                and isinstance(document.get("created_at"), (int, float))
                and time.time() - document["created_at"] > SNAPSHOT_TTL_SECONDS
            ):
                path.unlink()
        except (OSError, ValueError, TypeError):
            continue


def _atomic_snapshot(target: Path, raw: bytes) -> None:
    if target.exists():
        if target.is_symlink() or target.read_bytes() != raw:
            raise ScopeError("response_snapshot_target_occupied")
        return
    temporary = target.with_name("." + target.name + "." + uuid.uuid4().hex)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _save(
    reply: Reply, request: Request, root: Path, external: list[Path], home: Path, identity: str
) -> tuple[str, dict[str, Any]]:
    _cache_directory(home)
    document = {
        "schema_version": 1,
        "producer": _SNAPSHOT_PRODUCER,
        "created_at": time.time(),
        "identity": identity,
        "request": _request_identity(request),
        "project_sha256": _sha(str(root).encode("utf-8")),
        "inputs": input_signature(root, external, home),
        "reply": reply.as_dict(),
    }
    raw = _json(document)
    if len(raw) > 2 * MAX_CAPTURE_BYTES:
        raise ScopeError("sanitized_result_limit")
    snapshot = _sha(raw)
    target = home / (snapshot + ".json")
    _atomic_snapshot(target, raw)
    return snapshot, document


def _load(
    cursor: str, request: Request, root: Path, external: list[Path], home: Path, identity: str
) -> tuple[str, dict[str, Any], str, int]:
    match = _CURSOR.fullmatch(cursor)
    if match is None:
        raise ScopeError("invalid_response_cursor")
    snapshot, kind, offset = match.groups()
    target = home / (snapshot + ".json")
    if home.is_symlink() or target.is_symlink() or not target.is_file():
        raise ScopeError("response_snapshot_unavailable")
    raw = target.read_bytes()
    if len(raw) > 2 * MAX_CAPTURE_BYTES or _sha(raw) != snapshot:
        raise ScopeError("response_snapshot_changed")
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ScopeError("response_snapshot_changed")
    if (
        type(document.get("schema_version")) is not int
        or document["schema_version"] != 1
        or document.get("producer") != _SNAPSHOT_PRODUCER
        or document.get("identity") != identity
        or document.get("request") != _request_identity(request)
        or document.get("project_sha256") != _sha(str(root).encode("utf-8"))
        or document.get("inputs") != input_signature(root, external, home)
        or not isinstance(document.get("created_at"), (int, float))
        or not 0 <= time.time() - document["created_at"] <= SNAPSHOT_TTL_SECONDS
    ):
        raise ScopeError("response_snapshot_stale")
    return snapshot, document, kind, int(offset)


def _page(
    snapshot: str, document: dict[str, Any], size: int, *, kind: str = "items", offset: int = 0
) -> Reply:
    full = Reply(**document["reply"])
    data = full.data
    collection = None
    metadata: dict[str, Any] = {}
    if isinstance(data, list):
        collection = data
    elif isinstance(data, dict):
        for key in ("findings", "changes", "checks"):
            if isinstance(data.get(key), list):
                collection = data[key]
                metadata = {name: value for name, value in data.items() if name != key}
                metadata["collection"] = key
                break
    if kind == "items" and collection is not None:
        empty = dataclasses.replace(
            full,
            data={
                **metadata,
                "scope": "partial_collection",
                "items": [],
                "offset": offset,
                "total_items": len(collection),
            },
            complete=False,
            snapshot=snapshot,
            next_cursor=f"{snapshot}:items:{len(collection)}",
        )
        overhead = len(_json(empty.as_dict()))
        # Select one view for the whole immutable result, including a large
        # record that would otherwise become unreachable after smaller pages.
        if overhead > MAX_REPLY_BYTES - 1 or any(
            overhead + len(_json(item)) > MAX_REPLY_BYTES - 1 for item in collection
        ):
            collection = None
    if kind == "items" and collection is not None:
        stop = min(len(collection), offset + size)
        while stop > offset:
            page_data = {
                **metadata,
                "scope": "partial_collection",
                "items": collection[offset:stop],
                "offset": offset,
                "total_items": len(collection),
            }
            candidate = dataclasses.replace(
                full,
                data=page_data,
                complete=False,
                snapshot=snapshot,
                next_cursor=f"{snapshot}:items:{stop}" if stop < len(collection) else None,
            )
            if len(_json(candidate.as_dict())) <= MAX_REPLY_BYTES - 1:
                return candidate
            stop -= 1
        if offset:
            raise ScopeError("response_page_requires_fragment_view")
    text = _json({"data": full.data, "diagnostics": full.diagnostics}).decode("utf-8")
    if kind != "fragment":
        offset = 0
    stop = min(len(text), offset + 64 * 1024)
    while stop > offset:
        fragment = {
            "scope": "partial_document",
            "encoding": "json-text",
            "text": text[offset:stop],
            "offset": offset,
            "total_characters": len(text),
            "source_sha256": _sha(text.encode("utf-8")),
            "source_bytes": len(text.encode("utf-8")),
        }
        candidate = dataclasses.replace(
            full,
            data=fragment,
            diagnostics=[{"code": "diagnostics_in_full_snapshot"}],
            complete=False,
            snapshot=snapshot,
            next_cursor=f"{snapshot}:fragment:{stop}" if stop < len(text) else None,
        )
        if len(_json(candidate.as_dict())) <= MAX_REPLY_BYTES - 1:
            return candidate
        stop = offset + (stop - offset) // 2
    raise ScopeError("response_budget_unavailable")


def sanitize_reply(reply: Reply, root: Path) -> Reply:
    """Return a full display-safe copy before a durable operation saves it."""
    safe = dataclasses.replace(
        reply, diagnostics=copy.deepcopy(reply.diagnostics), questions=list(reply.questions)
    )
    safe.data = _sanitize(safe.data, root, action=safe.action, diagnostics=safe.diagnostics)
    for diagnostic in safe.diagnostics:
        for name, value in list(diagnostic.items()):
            if name == "code" or (
                name.endswith("sha256")
                and isinstance(value, str)
                and re.fullmatch(r"[0-9a-f]{64}", value)
            ):
                continue
            diagnostic[name] = _sanitize(value, root, context=(name,))
    safe.questions = cast(list[str], _sanitize(safe.questions, root))
    return safe


def finish_reply(
    reply: Reply,
    request: Request,
    *,
    root: Path,
    external: list[Path],
    cache_home: Path,
    identity: str,
    sanitized: bool = False,
) -> Reply:
    """Deliver the same complete safe result or a hash-bound view of it."""
    reply = reply if sanitized else sanitize_reply(reply, root)
    raw = _json(reply.as_dict())
    collection = (
        reply.data
        if isinstance(reply.data, list)
        else next(
            (
                reply.data[key]
                for key in ("findings", "changes", "checks")
                if isinstance(reply.data, dict) and isinstance(reply.data.get(key), list)
            ),
            None,
        )
    )
    needs_paging = len(raw) > MAX_REPLY_BYTES - 1 or (
        isinstance(collection, list) and len(collection) > request.response.page_size
    )
    if not needs_paging:
        return reply
    snapshot, saved = _save(reply, request, root, external, cache_home, identity)
    return _page(snapshot, saved, request.response.page_size)


def long_operation(request: Request) -> bool:
    return (
        request.action == "lock"
        and request.options.get("hash_large_files") is True
        and not request.options.get("check", False)
    )


def operation_identity() -> str:
    catalog = Path(__file__).resolve().parents[1] / "assets/install-catalog.json"
    return _sha(catalog.read_bytes() + helper_code_identity().encode("ascii"))


def operation_worker_entry(request: Request, context: Any) -> Reply:
    """Run one fixed native adapter, then return a full safe result to its owner."""
    from skill_local import execute_lock
    from skill_request import required_grants

    try:
        root = project_root(request)
    except ScopeError as error:
        return blocked(request.action, str(error))
    if root != context.root or not long_operation(request):
        return blocked(request.action, "operation_request_conflict")
    if any(not getattr(request.grants, name) for name in required_grants(request)):
        return blocked(request.action, "authorization_required", needs_authorization=True)
    if not request.options.get("offline", False):
        return blocked(request.action, "online_lock_unavailable")
    context.check_cancel()
    reply = execute_lock(
        request,
        root=root,
        state_home=context.home / "writes",
        identity=context.identity,
        cancellation=context,
    )
    return sanitize_reply(reply, root)


def execute(
    request: Request,
    *,
    cache_home: Path,
    identity: str = "test-runtime",
    cli_runner: CliRunner | None = None,
) -> Reply:
    reply: Reply | None = None
    artifact_written = False
    try:
        if (
            request.action
            not in READONLY_ACTIONS | WRITE_ACTIONS | LOCAL_ACTIONS | OPERATION_ACTIONS
        ):
            return blocked(request.action, "action_unavailable")
        if request.action == "doctor" and request.options.get("check_network"):
            return blocked(
                request.action,
                "network_diagnostics_unavailable",
                needs_authorization=not request.grants.network,
            )
        root = project_root(request)
        external = _external_inputs(request, root)
        if request.response.cursor:
            snapshot, saved, kind, offset = _load(
                request.response.cursor, request, root, external, cache_home, identity
            )
            return _page(snapshot, saved, request.response.page_size, kind=kind, offset=offset)
        if request.action in OPERATION_ACTIONS or long_operation(request):
            return blocked(request.action, "long_operation_requires_controller")
        if request.action == "lock" and not (
            request.options.get("offline", False) or request.options.get("check", False)
        ):
            return blocked(request.action, "online_lock_unavailable")
        if request.action in LOCAL_ACTIONS:
            from skill_local import execute_lock, execute_rules

            producer = execute_lock if request.action == "lock" else execute_rules
            reply = producer(
                request, root=root, state_home=cache_home.parent / "writes", identity=identity
            )
        elif request.action in WRITE_ACTIONS:
            from skill_writes import execute_write

            reply = execute_write(
                request,
                root=root,
                state_home=cache_home.parent / "writes",
                identity=identity,
                cli_runner=cli_runner or invoke_cli,
                source_signature=input_signature,
                display_sanitizer=lambda value, notes: _sanitize(
                    value, root, action="runs.show", diagnostics=notes
                ),
            )
        else:
            output = _output_target(request, root)
            display_diagnostics: list[dict[str, Any]] = []
            if request.action == "run.preview":
                result, as_json = _preview(request, root), False
            else:
                argv, as_json = command_args(request, root)
                if request.action == "audit":
                    from skill_audit_display import invoke_private_audit

                    result, display_diagnostics = invoke_private_audit(
                        argv,
                        root,
                        invoke_cli=cli_runner or invoke_cli,
                        sanitize=lambda value, notes: _sanitize(
                            value, root, action="runs.show", diagnostics=notes
                        ),
                    )
                elif request.action == "diff":
                    from skill_diff_display import invoke_private_diff

                    result, display_diagnostics = invoke_private_diff(
                        argv,
                        root,
                        invoke_cli=cli_runner or invoke_cli,
                        sanitize=lambda value, notes: _sanitize(
                            value, root, action="runs.show", diagnostics=notes
                        ),
                    )
                elif request.action == "runs.show" and not as_json:
                    from skill_run_display import invoke_private_show

                    result, display_diagnostics = invoke_private_show(
                        argv,
                        root,
                        invoke_cli=cli_runner or invoke_cli,
                        sanitize=lambda value, notes: _sanitize(
                            value, root, action="runs.show", diagnostics=notes
                        ),
                    )
                else:
                    result = (cli_runner or invoke_cli)(argv, root)
            diagnostics = [*display_diagnostics]
            if result.stderr:
                diagnostics.append({"code": "cli_stderr", "text": result.stderr})
            reply = Reply(
                request.action,
                cli_exit_code=result.exit_code,
                complete=False,
                diagnostics=diagnostics,
            )
            if result.exit_code in {2, 3} or result.exit_code not in {0, 1}:
                reply.invocation = "user_error" if result.exit_code == 2 else "internal_error"
            else:
                try:
                    data = json.loads(result.stdout) if as_json else result.stdout
                except (ValueError, RecursionError):
                    reply.invocation = "internal_error"
                    reply.diagnostics.append({"code": "invalid_cli_json"})
                else:
                    reply.gate_failed = (
                        result.exit_code == 1 if request.action in {"audit", "diff"} else None
                    )
                    if output is not None:
                        if not isinstance(data, dict):
                            raise ScopeError("invalid_cli_json")
                        target = output.target
                        _write_report(output, result.stdout.encode("utf-8"))
                        artifact_written = True
                        counts = data.get("summary", {})
                        message = f"Wrote audit report to {target} "
                        message += f"({counts.get('critical', 0)} critical, "
                        message += f"{counts.get('warning', 0)} warning)\n"
                        data = {
                            "report": data,
                            "stdout": message,
                            "artifact": target.relative_to(root).as_posix()
                            if target.is_relative_to(root)
                            else target.name,
                        }
                    reply.data, reply.complete = data, True
        return finish_reply(
            reply, request, root=root, external=external, cache_home=cache_home, identity=identity
        )
    except ScopeError as error:
        code = str(error)
        failure = blocked(
            request.action,
            code,
            needs_authorization=(
                code.endswith("scope_required")
                or code.endswith("approval_required")
                or code
                in {
                    "report_write_authorization_required",
                    "report_target_changed",
                    "report_target_mapping_changed",
                }
            ),
        )
        if reply is not None:
            failure.cli_exit_code, failure.gate_failed = reply.cli_exit_code, reply.gate_failed
            failure.data = publication_summary(reply)
        if artifact_written:
            failure.data = {"scope": "incomplete_delivery", "artifact_written": True}
        return failure
    except (OSError, ValueError, RecursionError):
        return Reply(
            request.action,
            invocation="user_error",
            complete=False,
            cli_exit_code=reply.cli_exit_code if reply else None,
            gate_failed=reply.gate_failed if reply else None,
            data={"scope": "incomplete_delivery", "artifact_written": True}
            if artifact_written
            else publication_summary(reply)
            if reply is not None
            else None,
            diagnostics=[{"code": "readonly_input_unavailable"}],
        )


@dataclass
class _WorkerLease:
    status: dict[str, Any]
    environment: Path
    claim: dict[str, Any]
    cleanup_failed: bool = False
    release_on_exit: bool = True

    def transfer(self) -> None:
        """Keep the durable lease when a broker returns or launch becomes unknown."""
        self.release_on_exit = False

    def reclaim(self) -> None:
        """Use only after proving that a launch did not start a worker."""
        self.release_on_exit = True


def release_owned_lease(manager: Any, claim: dict[str, Any]) -> bool:
    """Release the exact original marker; preserve foreign or ambiguous ownership."""
    from bootstrap import BootstrapError

    try:
        if set(claim) != {"schema_version", "environment", "lease_id"}:
            return False
        name, lease_id = claim["environment"], claim["lease_id"]
        if (
            type(claim["schema_version"]) is not int
            or claim["schema_version"] != 1
            or not isinstance(name, str)
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", name) is None
            or not isinstance(lease_id, str)
            or re.fullmatch(r"[0-9a-f]{32}", lease_id) is None
        ):
            return False
        raw = _json({"schema_version": 1, "owner": "reprollm-skill-worker", "lease_id": lease_id})
        with manager._lock():
            environment = manager.environment_path(name)
            leases = environment / "leases"
            path = leases / (lease_id + ".json")
            if (
                environment.is_symlink()
                or leases.is_symlink()
                or path.is_symlink()
                or not path.is_file()
                or path.stat().st_size != len(raw)
                or path.read_bytes() != raw
            ):
                return False
            path.unlink()
            if not any(leases.iterdir()):
                leases.rmdir()
        return True
    except (BootstrapError, OSError, ValueError, TypeError, KeyError):
        return False


def release_operation_lease(home: Path, claim: dict[str, Any]) -> bool:
    from bootstrap import Bootstrap
    from install_catalog import load_catalog

    catalog = load_catalog(Path(__file__).resolve().parents[1] / "assets/install-catalog.json")
    return release_owned_lease(Bootstrap(home, catalog), claim)


@contextlib.contextmanager
def _worker_lease(manager: Any, name: str) -> Iterator[_WorkerLease]:
    # Verification and the lease claim share the installer's mutation lock so
    # uninstall cannot remove an environment between its check and worker start.
    lease_id = uuid.uuid4().hex
    raw = _json({"schema_version": 1, "owner": "reprollm-skill-worker", "lease_id": lease_id})
    with manager._lock():
        status = manager._verify(name)
        if not _compatible_installation(status):
            raise ScopeError("compatible_tool_preparation_failed")
        environment = manager.environment_path(name)
        leases = environment / "leases"
        if leases.is_symlink() or (leases.exists() and not leases.is_dir()):
            raise ScopeError("runtime_lease_directory_invalid")
        leases.mkdir(mode=0o700, exist_ok=True)
        path = leases / (lease_id + ".json")
        _atomic_snapshot(path, raw)
    lease = _WorkerLease(
        status, environment, {"schema_version": 1, "environment": name, "lease_id": lease_id}
    )
    try:
        yield lease
    finally:
        if lease.release_on_exit and not release_owned_lease(manager, lease.claim):
            lease.cleanup_failed = True


class RuntimeExecutor:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home

    def __call__(self, request: Request) -> Reply:
        from bootstrap import Bootstrap, BootstrapError, default_home, environment_python
        from install_catalog import CatalogError, load_catalog
        from skill_runtime_frame import FrameError, validate_frame

        worker_started = False
        try:
            if request.action not in AVAILABLE_ACTIONS - BASE_ACTIONS:
                return blocked(request.action, "action_unavailable")
            root = project_root(request)
            home = self.home or default_home()
            catalog_path = Path(__file__).resolve().parents[1] / "assets/install-catalog.json"
            if request.action in OPERATION_ACTIONS or (
                long_operation(request) and request.options.get("operation_id")
            ):
                from skill_operations import control

                if request.response.cursor:
                    return execute(
                        request, cache_home=home / "responses", identity=operation_identity()
                    )
                controlled = control(request, home=home, root=root)
                if controlled is not None:
                    return finish_reply(
                        controlled,
                        request,
                        root=root,
                        external=[],
                        cache_home=home / "responses",
                        identity=operation_identity(),
                        sanitized=True,
                    )
            catalog = load_catalog(catalog_path)
            manager = Bootstrap(home, catalog)
            try:
                status = manager.status()
            except (BootstrapError, CatalogError, OSError):
                status = {"state": "INVALID"}
            if not _compatible_installation(status):
                if not request.grants.install:
                    return blocked(
                        request.action,
                        "compatible_tool_preparation_required",
                        needs_authorization=True,
                    )
                preferred = catalog.get_candidate()
                candidates = (preferred, *catalog.candidates)
                selected = next(
                    (
                        candidate
                        for candidate in candidates
                        if REQUIRED_CAPABILITIES.issubset(candidate.capabilities)
                    ),
                    None,
                )
                if selected is None:
                    return blocked(request.action, "compatible_tool_candidate_unavailable")
                status = manager.update(selected.id)
                if not _compatible_installation(status):
                    return blocked(request.action, "compatible_tool_preparation_failed")
            if long_operation(request):
                from skill_operations import start

                identity = _sha(
                    catalog_path.read_bytes()
                    + helper_code_identity().encode("ascii")
                    + _json(status)
                )
                return finish_reply(
                    start(
                        request,
                        home=home,
                        root=root,
                        identity=identity,
                        manager=manager,
                        environment_name=status["environment"],
                        lease_factory=_worker_lease,
                    ),
                    request,
                    root=root,
                    external=[],
                    cache_home=home / "responses",
                    identity=operation_identity(),
                    sanitized=True,
                )
            with _worker_lease(manager, status["environment"]) as lease:
                identity = _sha(
                    catalog_path.read_bytes()
                    + helper_code_identity().encode("ascii")
                    + _json(lease.status)
                )
                environment = lease.environment
                worker_started = True
                result = subprocess.run(
                    [
                        str(environment_python(environment)),
                        "-I",
                        "-B",
                        str(Path(__file__).resolve()),
                        "--worker",
                        "--cache-home",
                        str(home / "responses"),
                        "--identity",
                        identity,
                    ],
                    input=_json(dataclasses.asdict(request)),
                    capture_output=True,
                    timeout=120,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    check=False,
                )
            if len(result.stdout) > MAX_REPLY_BYTES:
                failure = blocked(request.action, "runtime_protocol_failed")
                _unknown_write_effects(request, failure)
                return failure
            try:
                reply = validate_frame(result.stdout, expected_action=request.action)
            except FrameError:
                failure = Reply(
                    request.action,
                    invocation="internal_error",
                    complete=False,
                    diagnostics=[
                        {"code": "runtime_protocol_failed", "worker_exit_code": result.returncode}
                    ],
                )
                _unknown_write_effects(request, failure)
                return failure
            if result.returncode != 0 or result.stderr or lease.cleanup_failed:
                reply.invocation = "internal_error"
                reply.complete = False
                reply.next_cursor = None
                if result.returncode != 0 or result.stderr:
                    reply.diagnostics.append(
                        {
                            "code": "runtime_worker_exit"
                            if result.returncode
                            else "runtime_worker_stderr",
                            "worker_exit_code": result.returncode,
                        }
                    )
            if lease.cleanup_failed:
                reply.diagnostics.append({"code": "runtime_lease_cleanup_failed"})
            return reply
        except ScopeError as error:
            return blocked(
                request.action,
                str(error),
                needs_authorization=str(error).endswith("scope_required"),
                needs_input=str(error) in {"project_required", "project_directory_required"},
            )
        except (
            BootstrapError,
            CatalogError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            subprocess.SubprocessError,
        ):
            failure = blocked(request.action, "tool_or_runtime_unavailable")
            if worker_started:
                _unknown_write_effects(request, failure)
            return failure


def _unknown_write_effects(request: Request, reply: Reply) -> None:
    if (
        request.action in WRITE_ACTIONS | LOCAL_WRITE_ACTIONS
        and not request.options.get("preview", False)
        and not (request.action == "lock" and request.options.get("check", False))
    ):
        reply.data = {
            "scope": "unknown_completion",
            "artifact_publication_unknown": True,
            "safe_to_repeat": False,
        }


def _compatible_installation(status: dict[str, Any]) -> bool:
    capabilities = status.get("capabilities")
    return (
        status.get("state") == "READY"
        and isinstance(capabilities, (list, tuple))
        and REQUIRED_CAPABILITIES.issubset(capabilities)
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--cache-home", type=Path, required=True)
    parser.add_argument("--identity", required=True)
    args = parser.parse_args(argv)
    try:
        request = parse_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
        reply = execute(request, cache_home=args.cache_home, identity=args.identity)
    except RequestError as error:
        reply = error_reply(error)
    except Exception:
        reply = Reply(
            None,
            invocation="internal_error",
            complete=False,
            diagnostics=[{"code": "readonly_runtime_failed"}],
        )
    sys.stdout.buffer.write(encode_reply(reply) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
