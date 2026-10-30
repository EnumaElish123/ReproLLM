"""Offline lock and native rule operations with guarded artifact publication."""

from __future__ import annotations

import contextlib
import dataclasses
import importlib
import io
import json
import math
import os
import stat
import tempfile
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, Protocol, cast

import skill_writes as writes
from skill_request import Reply, Request, blocked

RULE_READS = frozenset({"rules.list", "rules.candidates", "rules.show"})
RULE_WRITES = frozenset(
    {"rules.add", "rules.accept", "rules.ignore", "rules.remove", "rules.restore"}
)
LOCAL_ACTIONS = RULE_READS | RULE_WRITES | {"lock"}
SMALL_INPUT_BYTES = 2 * 1024 * 1024
PLAN_TTL_SECONDS = 3600
MAX_PLAN_BYTES = 16 * 1024
MAX_PLANS = 128
_PLAN_OWNER = "reprollm-skill-local-plan"


def _plan_request(request: Request, root: Path, identity: str) -> str:
    return writes._sha(
        writes._json(
            {
                "action": request.action,
                "project": writes._sha(str(root).encode()),
                "options": {
                    key: value
                    for key, value in request.options.items()
                    if key not in {"preview", "operation_id"}
                },
                "identity": writes._sha(identity.encode()),
                "module": writes._sha(Path(__file__).read_bytes()),
            }
        )
    )


def _plans(state: Path) -> Path:
    return writes._owned_state(state / "plans")


def _load_plan(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise LocalError("local_plan_unavailable", review=True)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_PLAN_BYTES + 1)
        document = json.loads(raw)
    except (OSError, ValueError):
        raise LocalError("local_plan_state_invalid", review=True) from None
    if (
        len(raw) > MAX_PLAN_BYTES
        or not isinstance(document, dict)
        or set(document)
        != {
            "schema_version",
            "owner",
            "created_at",
            "prepared_at",
            "request_sha256",
            "plan_hash",
            "metadata_sha256",
        }
        or type(document.get("schema_version")) is not int
        or document["schema_version"] != 1
        or document["owner"] != _PLAN_OWNER
        or document["plan_hash"] != path.stem
        or type(document["created_at"]) not in {int, float}
        or not math.isfinite(document["created_at"])
        or document["metadata_sha256"]
        != writes._sha(
            writes._json(
                {key: value for key, value in document.items() if key != "metadata_sha256"}
            )
        )
    ):
        raise LocalError("local_plan_state_invalid", review=True)
    return document


def _prepared_time(request: Request, root: Path, state: Path, identity: str) -> datetime | None:
    token = request.grants.plan_hash
    if token is None:
        return (
            datetime.now(timezone.utc).replace(microsecond=0)
            if request.options.get("preview")
            else None
        )
    if len(token) != 64 or any(char not in "0123456789abcdef" for char in token):
        raise LocalError("local_plan_unavailable", review=True)
    document = _load_plan(_plans(state) / (token + ".json"))
    age = time.time() - document["created_at"]
    if not 0 <= age <= PLAN_TTL_SECONDS:
        raise LocalError("local_plan_expired", review=True)
    if document["request_sha256"] != _plan_request(request, root, identity):
        raise LocalError("local_plan_changed", review=True)
    try:
        prepared = datetime.fromisoformat(document["prepared_at"])
    except (TypeError, ValueError):
        raise LocalError("local_plan_state_invalid", review=True) from None
    if prepared.tzinfo is None or prepared.utcoffset() != timezone.utc.utcoffset(None):
        raise LocalError("local_plan_state_invalid", review=True)
    return prepared


def _save_plan(
    request: Request, root: Path, state: Path, identity: str, plan: str, prepared: datetime
) -> None:
    directory = _plans(state)
    count = 0
    for path in directory.glob("*.json"):
        if len(path.stem) != 64 or any(char not in "0123456789abcdef" for char in path.stem):
            continue
        before = path.lstat()
        record = _load_plan(path)
        if time.time() - record["created_at"] > PLAN_TTL_SECONDS:
            current = path.lstat()
            if (before.st_dev, before.st_ino) == (current.st_dev, current.st_ino):
                path.unlink()
        else:
            count += 1
    target = directory / (plan + ".json")
    if target.exists() or target.is_symlink():
        record = _load_plan(target)
        if (
            record["request_sha256"] != _plan_request(request, root, identity)
            or record["prepared_at"] != prepared.isoformat()
        ):
            raise LocalError("local_plan_state_invalid", review=True)
        return
    if count >= MAX_PLANS:
        raise LocalError("local_plan_capacity_reached", review=True)
    record = {
        "schema_version": 1,
        "owner": _PLAN_OWNER,
        "created_at": time.time(),
        "prepared_at": prepared.isoformat(),
        "request_sha256": _plan_request(request, root, identity),
        "plan_hash": plan,
    }
    record["metadata_sha256"] = writes._sha(writes._json(record))
    raw = writes._json(record)
    descriptor, name = tempfile.mkstemp(prefix=".plan-", suffix=".tmp", dir=directory)
    temporary = Path(name)
    owned = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            record = _load_plan(target)
            if (
                record["request_sha256"] != _plan_request(request, root, identity)
                or record["prepared_at"] != prepared.isoformat()
            ):
                raise LocalError("local_plan_state_invalid", review=True) from None
    finally:
        with contextlib.suppress(FileNotFoundError):
            current = temporary.lstat()
            if (owned.st_dev, owned.st_ino) == (current.st_dev, current.st_ino):
                temporary.unlink()


class Cancellation(Protocol):
    def check_cancel(self) -> None: ...
    def publication(self) -> contextlib.AbstractContextManager[Any]: ...


class LocalError(ValueError):
    def __init__(self, code: str, *, authorization: bool = False, review: bool = False) -> None:
        super().__init__(code)
        self.authorization = authorization
        self.review = review


class NativeFailure(Exception):
    """The original command would fail internally; its exception text stays private."""


class PreparationFailure(LocalError):
    pass


@dataclass(frozen=True)
class FileView:
    declared: Path
    target: Path
    identity: tuple[int, int, int, int, int] | None
    sha256: str | None
    small: bool


class Inputs:
    """Actual native inputs; weights use metadata, never a second content hash."""

    def __init__(self, request: Request, root: Path) -> None:
        self.request, self.root = request, root
        self.files: dict[Path, FileView] = {}
        self.directories: dict[Path, tuple[Path, tuple[str, ...] | None]] = {}

    def authorized(self, target: Path) -> None:
        if target.is_relative_to(self.root):
            return
        if any(
            writes._path(item, self.root).resolve() == target
            for item in self.request.grants.external_paths
        ):
            return
        raise LocalError("external_input_scope_required", authorization=True)

    @staticmethod
    def identity(path: Path) -> tuple[int, int, int, int, int] | None:
        try:
            metadata = path.stat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(metadata.st_mode):
            raise LocalError("local_input_regular_file_required")
        return (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )

    def file(self, declared: Path, *, small: bool = True) -> None:
        target = declared.resolve()
        self.authorized(target)
        identity = self.identity(target)
        previous = self.files.get(declared)
        if previous is not None:
            small = small and previous.small
        digest = (
            writes._hash_file(target)
            if small and identity is not None and identity[2] <= SMALL_INPUT_BYTES
            else previous.sha256
            if previous is not None
            else None
        )
        current = FileView(declared, target, identity, digest, small)
        if previous is not None and (
            previous.target != current.target
            or previous.identity != current.identity
            or previous.sha256 is not None
            and previous.sha256 != current.sha256
        ):
            raise LocalError("local_inputs_changed")
        self.files[declared] = current

    def directory(self, path: Path, members: list[str]) -> None:
        target = path.resolve()
        self.authorized(target)
        value = (target, tuple(sorted(members)) if path.exists() else None)
        previous = self.directories.get(path)
        if previous is not None and previous != value:
            raise LocalError("local_input_membership_changed")
        self.directories[path] = value

    def check(self) -> None:
        for item in tuple(self.files.values()):
            if item.declared.resolve() != item.target:
                raise LocalError("local_input_mapping_changed", authorization=True)
            self.authorized(item.target)
            if self.identity(item.target) != item.identity:
                raise LocalError("local_inputs_changed")
            if item.sha256 is not None and writes._hash_file(item.target) != item.sha256:
                raise LocalError("local_inputs_changed")
        for declared, (target, _) in self.directories.items():
            if declared.resolve() != target:
                raise LocalError("local_input_mapping_changed", authorization=True)

    def fingerprint(self) -> str:
        return writes._sha(
            writes._json(
                {
                    "module": writes._sha(Path(__file__).read_bytes()),
                    "files": [
                        [
                            writes._sha(str(p).encode()),
                            writes._sha(str(v.target).encode()),
                            v.identity,
                            v.sha256,
                        ]
                        for p, v in sorted(self.files.items())
                    ],
                    "directories": [
                        [writes._sha(str(p).encode()), writes._sha(str(v[0]).encode()), v[1]]
                        for p, v in sorted(self.directories.items())
                    ],
                }
            )
        )


def _cancel(cancellation: Cancellation | None) -> None:
    if cancellation is not None:
        cancellation.check_cancel()


def _error(request: Request, error: Exception) -> Reply:
    from reprollm.core.errors import UserError

    if isinstance(error, PreparationFailure):
        return Reply(
            request.action,
            invocation="user_error",
            cli_exit_code=2,
            complete=False,
            data={"phase": "preparation_failed", "artifacts_written": []},
            diagnostics=[
                {
                    "code": "local_preparation_failed",
                    "text": "Private removal preparation failed before publication; "
                    "check helper directory permissions and retry rules.remove "
                    "with the same rule_id and reason.",
                }
            ],
        )
    if isinstance(error, LocalError):
        return blocked(
            request.action,
            str(error),
            needs_authorization=error.authorization,
            needs_input=error.review,
        )
    if isinstance(error, writes.WriteError):
        return blocked(request.action, str(error), needs_authorization=error.authorization)
    if isinstance(error, NativeFailure):
        return Reply(
            request.action,
            invocation="internal_error",
            cli_exit_code=3,
            complete=False,
            diagnostics=[{"code": "native_internal_error"}],
        )
    return Reply(
        request.action,
        invocation="user_error" if isinstance(error, UserError) else "blocked",
        cli_exit_code=2 if isinstance(error, UserError) else None,
        complete=False,
        diagnostics=[{"code": "native_usage_error", "text": str(error)}]
        if isinstance(error, UserError)
        else [{"code": "local_input_or_publication_failed"}],
    )


def _expected(
    request: Request, root: Path, path: Path, actual: str | None, *, required: bool = False
) -> None:
    matches = [
        digest
        for value, digest in request.grants.expected_hashes.items()
        if writes._path(value, root).resolve() == path.resolve()
    ]
    if len(matches) > 1:
        raise LocalError("local_expected_hash_ambiguous", authorization=True)
    if not matches:
        if required:
            if path.parent == root / ".reprollm/discover" and any(
                writes._path(value, root).parent == path.parent
                for value in request.grants.expected_hashes
            ):
                raise LocalError("reviewed_source_changed", review=True)
            raise LocalError("candidate_review_required", review=True)
        return
    if matches[0] != actual:
        raise LocalError("reviewed_source_changed", review=True)


def _artifact(request: Request, root: Path, relative: str, content: bytes) -> writes.Artifact:
    from reprollm.core.rule_lifecycle import _owned_path

    target = _owned_path(root, relative)
    immutable = relative.startswith(".reprollm/rule-archives/")
    artifact = writes._artifact(
        request, root, target, content, role=relative, mode=0o600, implicit_replace=not immutable
    )
    if immutable and artifact.expected is not None:
        raise LocalError("rule_archive_appeared")
    return artifact


def _publish(
    request: Request,
    root: Path,
    state: Path,
    identity: str,
    guard: Inputs,
    artifacts: list[writes.Artifact],
    data: dict[str, Any],
    *,
    check: Callable[[], None],
    cancellation: Cancellation | None = None,
    published: list[writes.Published] | None = None,
    prepared_at: datetime | None = None,
) -> Reply:
    effects = published if published is not None else []
    signature = guard.fingerprint()
    native_intent = dataclasses.replace(
        request,
        options={key: value for key, value in request.options.items() if key != "operation_id"},
    )
    plan = writes._plan(native_intent, root, artifacts, signature, identity)
    prepared = writes.PreparedWrite(request.action, root, artifacts, signature, plan, data)
    data.update(
        {
            "phase": "prepared",
            "plan_hash": plan,
            "artifacts": writes._descriptions(prepared),
            "artifacts_written": [],
        }
    )
    if request.options.get("preview"):
        assert prepared_at is not None
        _save_plan(request, root, state, identity, plan, prepared_at)
        data["stdout"] = (
            "Private preparation output; project artifacts remain unchanged.\n"
            + data.get("stdout", "")
        )
        return Reply(request.action, cli_exit_code=0, data=data)
    if request.grants.plan_hash is not None and request.grants.plan_hash != plan:
        raise LocalError("local_plan_changed", review=True)
    _cancel(cancellation)
    publication = (
        cancellation.publication() if cancellation is not None else contextlib.nullcontext()
    )
    with publication, writes._project_lock(state, root):
        check()
        guard.check()
        for artifact in artifacts:
            writes._check_artifact(artifact)
        directories: list[writes.DirectoryIdentity] = []
        for artifact in artifacts:
            check()
            guard.check()
            ready = writes._make_directories(artifact, directories)
            writes.publish_artifact(ready, effects)
    data.update({"phase": "applied", "artifacts_written": writes._remaining(effects, root)})
    return Reply(request.action, cli_exit_code=0, data=data)


def _local_inventory(root: Path, manifest: Any, guard: Inputs) -> None:
    from reprollm.lock import local_resolver as local
    from reprollm.lock.resolver import _safe_project_file

    for role, model in sorted(manifest.models.items()):
        if model.provider == "local":
            target = local._safe_existing_path(root, model.id or "", f"models.{role}.id")
            declared = root / (model.id or "")
            if target.is_dir():
                members = [
                    path.relative_to(target).as_posix()
                    for path in target.rglob("*")
                    if path.is_file() and path.suffix.lower() in local._WEIGHT_SUFFIXES
                ]
                members.extend(
                    name for name in local._MODEL_METADATA_FILES if (target / name).is_file()
                )
                guard.directory(declared, members)
                for name in members:
                    path = declared / name
                    guard.file(path, small=path.suffix.lower() not in local._WEIGHT_SUFFIXES)
            else:
                guard.file(declared, small=False)
        if (
            model.provider == "huggingface"
            and model.adapter is not None
            and model.adapter.provider == "peft"
            and local.is_local_path(root, model.adapter.id)
        ):
            target = local._safe_existing_path(root, model.adapter.id, f"models.{role}.adapter.id")
            declared = root / model.adapter.id
            guard.file(declared / "adapter_config.json" if target.is_dir() else declared)
    optional = [prompt.path for prompt in manifest.prompts.values() if prompt.path]
    optional.extend(
        model.chat_template.path
        for model in manifest.models.values()
        if model.chat_template is not None
    )
    for dataset in manifest.datasets.values():
        if dataset.provider == "local":
            optional.extend(dataset.files or [])
    if manifest.execution is not None:
        optional.extend(manifest.execution.config_files or [])
    optional.extend(
        binding.config.partition(":")[0] for binding in manifest.bindings.values() if binding.config
    )
    if manifest.training is not None and manifest.training.deepspeed is not None:
        optional.append(manifest.training.deepspeed.config)
    if manifest.evaluation is not None:
        optional.extend((manifest.evaluation.definitions or {}).values())
        optional.extend(
            metric.implementation for metric in manifest.evaluation.metrics if metric.implementation
        )
    if manifest.privacy is not None and manifest.privacy.threat_model:
        optional.append(manifest.privacy.threat_model)
    for relative in sorted(set(optional)):
        if _safe_project_file(root, relative) is not None:
            guard.file(root / relative, small=False)


@contextlib.contextmanager
def _guard_native_reads(guard: Inputs, cancellation: Cancellation | None) -> Iterator[None]:
    modules: list[Any] = [
        importlib.import_module(name)
        for name in (
            "reprollm.lock.writer",
            "reprollm.lock.resolver",
            "reprollm.lock.local_resolver",
            "reprollm.lock.hf_resolver",
        )
    ]
    originals: list[tuple[Any, Any]] = []
    for module in modules:
        original = module.sha256_file
        originals.append((module, original))

        def read(path: Path, original: Any = original) -> str:
            _cancel(cancellation)
            known = next(
                (item for item in guard.files.values() if item.target == path.resolve()), None
            )
            guard.file(path, small=known.small if known is not None else False)
            return str(original(path))

        module.sha256_file = read
    local = modules[2]
    aggregate = local._aggregate_hash
    chat_template = local._local_chat_template

    def guarded_aggregate(paths: list[Path], base: Path) -> str:
        _cancel(cancellation)
        for path in paths:
            known = next(
                (item for item in guard.files.values() if item.target == path.resolve()), None
            )
            guard.file(
                path,
                small=known.small
                if known is not None
                else path.suffix.lower() not in local._WEIGHT_SUFFIXES,
            )
        return str(aggregate(paths, base))

    def guarded_template(*args: Any, **kwargs: Any) -> Any:
        guard.check()
        return chat_template(*args, **kwargs)

    local._aggregate_hash, local._local_chat_template = guarded_aggregate, guarded_template
    try:
        yield
    finally:
        local._aggregate_hash, local._local_chat_template = aggregate, chat_template
        for module, original in originals:
            module.sha256_file = original


def execute_lock(
    request: Request,
    *,
    root: Path,
    state_home: Path,
    identity: str,
    cancellation: Cancellation | None = None,
) -> Reply:
    import getpass
    import socket

    from reprollm.core.errors import UserError
    from reprollm.core.paths import MANIFEST, PROJECT_RULES
    from reprollm.core.yaml_io import load_manifest
    from reprollm.lock import writer
    from reprollm.run.privacy import RunPrivacy

    effects: list[writes.Published] = []
    try:
        if request.action != "lock":
            return blocked(request.action, "action_unavailable")
        if request.response.cursor:
            return blocked(request.action, "local_cursor_requires_runtime_snapshot")
        guard = Inputs(request, root)
        for name in (MANIFEST, PROJECT_RULES):
            guard.file(root / name)
        if not (root / MANIFEST).is_file():
            raise UserError("reprollm.yaml is missing; run `reprollm init` first")
        manifest = load_manifest(root / MANIFEST)
        if request.options.get("check"):
            guard.file(root / "reprollm.lock")
            reasons = writer.check_lock(root)
            guard.check()
            text = (
                "Lock check failed:\n" + "".join(f"  - {reason}\n" for reason in reasons)
                if reasons
                else "reprollm.lock is up to date\n"
            )
            return Reply(
                request.action,
                cli_exit_code=int(bool(reasons)),
                data={"reasons": reasons, "stdout": text},
            )
        if not request.options.get("offline", False):
            return blocked(
                request.action,
                "online_lock_unavailable_use_offline",
                needs_authorization=not request.grants.network,
            )
        if not request.options.get("preview") and not request.grants.write:
            return blocked(request.action, "write_authorization_required", needs_authorization=True)
        for name in (MANIFEST, PROJECT_RULES):
            _expected(request, root, root / name, writes._hash_file(root / name))
        target = _artifact(request, root, "reprollm.lock", b"")
        guard.file(root / "reprollm.lock")
        state = writes._owned_state(state_home)
        prepared_at = _prepared_time(request, root, state, identity)
        _local_inventory(root, manifest, guard)
        _cancel(cancellation)
        with tempfile.TemporaryDirectory(prefix="local-lock-", dir=state / "staging") as name:
            stage = Path(name)
            with _guard_native_reads(guard, cancellation):
                document = writer.build_lock(
                    root,
                    manifest,
                    # The native offline branch also passes None without constructing a client.
                    http=cast(Any, None),
                    offline=True,
                    verify_api=request.options.get("verify_api", False),
                    hash_large_files=request.options.get("hash_large_files", False),
                    now=prepared_at,
                )
            writer.write_lock(stage / "reprollm.lock", document)
            privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
            if privacy.value(document.model_dump(mode="json")) != document.model_dump(mode="json"):
                raise UserError(
                    "cannot write reprollm.lock: remove secrets and machine identity "
                    "from reprollm.yaml"
                )
            artifact = dataclasses.replace(target, content=(stage / "reprollm.lock").read_bytes())
        summary = writer.summarize_lock(document)
        data = {
            "lock": document.model_dump(mode="json"),
            "summary": json.loads(writes._json(dataclasses.asdict(summary))),
            "stdout": "Wrote reprollm.lock\n" + summary.render() + "\n",
        }
        return _publish(
            request,
            root,
            state,
            identity,
            guard,
            [artifact],
            data,
            check=lambda: _local_inventory(root, manifest, guard),
            cancellation=cancellation,
            published=effects,
            prepared_at=prepared_at,
        )
    except (LocalError, writes.WriteError, UserError, OSError, ValueError, RecursionError) as error:
        reply = _error(request, error)
        if effects:
            reply.data = {
                "phase": "partial",
                "artifacts_written": writes._remaining(effects, root),
                "artifact_publication_attempted": True,
            }
        return reply


def _native_call(function: Callable[[], Any], cwd: Path) -> str:
    from reprollm.core.errors import UserError

    output, previous = io.StringIO(), Path.cwd()
    try:
        os.chdir(cwd)
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                function()
            except (UserError, LocalError, writes.WriteError):
                raise
            except Exception:
                raise NativeFailure from None
    finally:
        os.chdir(previous)
    return output.getvalue()


def _rule_snapshot(root: Path, guard: Inputs, source: Path | None = None) -> dict[str, Any]:
    from reprollm.core.paths import PROJECT_RULES
    from reprollm.core.rule_lifecycle import _owned_path, display_value

    active = _owned_path(root, PROJECT_RULES)
    guard.file(active)
    metadata: dict[str, Any] = {
        "code": "rule_source_snapshot",
        "active_source": PROJECT_RULES,
        "active_sha256": writes._hash_file(active),
    }
    if source is not None:
        directory = source.parent
        members = sorted(path.name for path in directory.glob("*.json"))
        guard.directory(directory, members)
        guard.file(source)
        metadata.update(
            {
                "source": source.relative_to(root).as_posix(),
                "sha256": writes._hash_file(source),
                "membership_sha256": writes._sha(writes._json(members)),
            }
        )
    return cast(dict[str, Any], display_value(root, metadata))


def _archive_available(root: Path, identifier: str) -> bool | None:
    from reprollm.core.errors import UserError
    from reprollm.core.rule_lifecycle import _archive_path, load_archive

    try:
        if not _archive_path(root, identifier).exists():
            return False
        load_archive(root, identifier)
        return True
    except (UserError, OSError, ValueError):
        return None


def execute_rules(
    request: Request,
    *,
    root: Path,
    state_home: Path,
    identity: str,
    cancellation: Cancellation | None = None,
) -> Reply:
    native: Any = importlib.import_module("reprollm.cli.rules")
    from reprollm.core import rule_lifecycle as lifecycle
    from reprollm.core.errors import UserError
    from reprollm.core.paths import PROJECT_RULES

    effects: list[writes.Published] = []
    archive: Any = None
    try:
        if request.action not in RULE_READS | RULE_WRITES:
            return blocked(request.action, "action_unavailable")
        if request.response.cursor:
            return blocked(request.action, "local_cursor_requires_runtime_snapshot")
        options = request.options
        if request.action in RULE_READS:
            guard = Inputs(request, root)
            diagnostics = [_rule_snapshot(root, guard)]
            original_latest = native._latest_discovery

            def inspected(project: Path) -> Any:
                from reprollm.core.rule_lifecycle import _owned_path

                directory = _owned_path(root, ".reprollm/discover")
                names = sorted(path.name for path in directory.glob("*.json"))
                if names:
                    source = _owned_path(root, ".reprollm/discover/" + names[-1])
                    diagnostics.append(_rule_snapshot(root, guard, source))
                result = original_latest(project)
                if names and result[0] != source:
                    raise LocalError("reviewed_source_changed", review=True)
                guard.directory(directory, sorted(path.name for path in directory.glob("*.json")))
                guard.check()
                return result

            as_json = request.action == "rules.show" or options.get("json", True)
            function = (
                (lambda: native.show(identifier=options["id"]))
                if request.action == "rules.show"
                else (
                    lambda: native.list_rules(
                        json_output=as_json,
                        candidates=request.action == "rules.candidates"
                        or options.get("candidates", False),
                    )
                )
            )
            native._latest_discovery = inspected
            try:
                stdout = _native_call(function, root)
            finally:
                native._latest_discovery = original_latest
            guard.check()
            return Reply(
                request.action,
                cli_exit_code=0,
                data=json.loads(stdout) if as_json else stdout,
                diagnostics=diagnostics,
            )
        if not options.get("preview") and not request.grants.write:
            return blocked(request.action, "write_authorization_required", needs_authorization=True)
        state = writes._owned_state(state_home)
        prepared_at = _prepared_time(request, root, state, identity)
        original_document = lifecycle.read_rules(root)
        guard = Inputs(request, root)
        guard.file(root / PROJECT_RULES)
        before = writes._hash_file(root / PROJECT_RULES)
        _expected(request, root, root / PROJECT_RULES, before)
        target = _artifact(request, root, PROJECT_RULES, b"")
        with tempfile.TemporaryDirectory(prefix="local-rules-", dir=state / "staging") as name:
            stage = Path(name)
            (stage / "reprollm.yaml").write_text("# Private native root sentinel\n")
            (stage / ".reprollm").mkdir()
            if before is not None:
                (stage / PROJECT_RULES).write_bytes((root / PROJECT_RULES).read_bytes())
            original_latest = native._latest_discovery

            def latest(_stage: Path) -> Any:
                directory = root / ".reprollm/discover"
                names = (
                    sorted(p.name for p in directory.glob("*.json")) if directory.is_dir() else []
                )
                if not names:
                    return original_latest(root)
                source = lifecycle._owned_path(root, ".reprollm/discover/" + names[-1])
                guard.directory(directory, names)
                guard.file(source)
                path, document = original_latest(root)
                if path != source:
                    raise LocalError("reviewed_source_changed", review=True)
                _expected(request, root, source, writes._hash_file(source), required=True)
                _expected(request, root, root / PROJECT_RULES, before, required=True)
                _expected(request, root, directory, writes._sha(writes._json(names)))
                guard.check()
                destination = stage / ".reprollm/discover" / source.name
                destination.parent.mkdir(exist_ok=True)
                destination.write_bytes(source.read_bytes())
                return original_latest(stage)

            native._latest_discovery = latest
            try:
                if request.action == "rules.add":
                    function = partial(
                        native.add,
                        field=options["field"],
                        severity=options["severity"],
                        reason=options["reason"],
                        rule_id=options.get("id"),
                        cli=options.get("cli"),
                        config=options.get("config"),
                        env=options.get("env"),
                    )
                elif request.action == "rules.accept":
                    function = partial(
                        native.accept,
                        candidate_id=options["candidate_id"],
                        severity=options.get("severity"),
                        field=options.get("field"),
                    )
                elif request.action == "rules.ignore":
                    function = partial(
                        native.ignore,
                        candidate_id=options["candidate_id"],
                        reason=options.get("reason"),
                    )
                elif request.action == "rules.remove":
                    function = partial(
                        native.remove, rule_id=options["rule_id"], reason=options["reason"]
                    )
                else:
                    source = lifecycle._archive_path(root, options["archive_id"])
                    lifecycle.load_archive(root, options["archive_id"])
                    guard.file(source)
                    _expected(request, root, source, writes._hash_file(source))
                    destination = stage / lifecycle.ARCHIVE_DIR / source.name
                    destination.parent.mkdir(parents=True)
                    destination.write_bytes(source.read_bytes())
                    function = partial(native.restore, archive_id=options["archive_id"])
                stdout = _native_call(function, stage).replace(str(stage), str(root))
            except UserError:
                if request.action == "rules.remove" and any(
                    (stage / lifecycle.ARCHIVE_DIR).glob("*.json")
                ):
                    raise PreparationFailure("local_preparation_failed") from None
                raise
            finally:
                native._latest_discovery = original_latest
            document = lifecycle.read_rules(stage)
            if prepared_at is not None:
                previous_ids = {rule.id for rule in original_document.rules}
                ignored_ids = {entry.candidate_id for entry in original_document.ignored_candidates}
                if request.action in {"rules.add", "rules.accept"}:
                    for rule in document.rules:
                        if rule.id not in previous_ids:
                            rule.accepted_at = prepared_at
                if request.action == "rules.ignore":
                    for entry in document.ignored_candidates:
                        if entry.candidate_id not in ignored_ids:
                            entry.ignored_at = prepared_at
                document = type(document).model_validate(document.model_dump(mode="json"))
                native._write_rules(stage, document)
            lifecycle._safe_copy(root, document.model_dump(mode="json"))
            artifacts = [dataclasses.replace(target, content=(stage / PROJECT_RULES).read_bytes())]
            archives = sorted((stage / lifecycle.ARCHIVE_DIR).glob("*.json"))
            if request.action == "rules.remove" and archives:
                archive = lifecycle.load_archive(stage, archives[0].stem)
                if prepared_at is not None:
                    original_id = archive.archive_id
                    payload = archive.model_dump(mode="python")
                    payload["archived_at"] = prepared_at
                    rebuilt = type(archive).model_validate(payload)
                    archive = rebuilt.model_copy(update={"archive_id": rebuilt.content_id()})
                    lifecycle.save_archive(stage, archive)
                    stdout = stdout.replace(original_id, archive.archive_id)
                    archives = [stage / lifecycle.ARCHIVE_DIR / (archive.archive_id + ".json")]
                lifecycle._safe_copy(root, archive.model_dump(mode="json"))
                relative = lifecycle.ARCHIVE_DIR + "/" + archives[0].name
                actual = lifecycle._archive_path(root, archive.archive_id)
                if actual.exists():
                    if lifecycle.load_archive(root, archive.archive_id) != archive:
                        raise UserError(
                            f"archive {archive.archive_id} already exists with different content"
                        )
                    guard.file(actual)
                else:
                    artifacts.insert(
                        0, _artifact(request, root, relative, archives[0].read_bytes())
                    )

        def unchanged() -> None:
            directory = root / ".reprollm/discover"
            if directory in guard.directories:
                guard.directory(directory, sorted(p.name for p in directory.glob("*.json")))

        data = {"project_rules": document.model_dump(mode="json"), "stdout": stdout}
        if archive is not None:
            data["archive_id"] = archive.archive_id
        reply = _publish(
            request,
            root,
            state,
            identity,
            guard,
            artifacts,
            data,
            check=unchanged,
            cancellation=cancellation,
            published=effects,
            prepared_at=prepared_at,
        )
        if archive is not None:
            reply.data["archive_available"] = _archive_available(root, archive.archive_id)
            reply.data["archive_state"] = lifecycle.archive_state(
                lifecycle.read_rules(root), archive
            )
        return reply
    except (
        LocalError,
        writes.WriteError,
        UserError,
        NativeFailure,
        OSError,
        ValueError,
        RecursionError,
    ) as error:
        reply = _error(request, error)
        if archive is not None or effects:
            reply.invocation = "user_error"
            reply.cli_exit_code = 2
            current: Any = None
            state_name = "unknown"
            with contextlib.suppress(UserError, OSError, ValueError):
                current = lifecycle.read_rules(root)
                if archive is not None:
                    state_name = lifecycle.archive_state(current, archive)
            reply.data = {
                "phase": "partial",
                "artifacts_written": writes._remaining(effects, root),
                "artifact_publication_attempted": bool(effects),
                "archive_id": archive.archive_id if archive else None,
                "archive_available": _archive_available(root, archive.archive_id)
                if archive is not None
                else None,
                "archive_state": state_name,
                "project_rules": current.model_dump(mode="json") if current is not None else None,
            }
        return reply
