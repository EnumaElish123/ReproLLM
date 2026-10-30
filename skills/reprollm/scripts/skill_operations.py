"""Owned local workers for long lock hashing; no scheduler or raw-output store."""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import json
import math
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from typing import Protocol

    class _OperationOS(Protocol):
        O_NOFOLLOW: int
        O_NONBLOCK: int

        def geteuid(self) -> int: ...
        def pidfd_open(self, pid: int, /) -> int: ...
        def set_blocking(self, descriptor: int, blocking: bool, /) -> None: ...

    class _OperationSignal(Protocol):
        SIGKILL: int

        def pidfd_send_signal(self, descriptor: int, number: int, /) -> None: ...

    class _OperationFileLock(Protocol):
        LOCK_EX: int
        LOCK_NB: int

        def flock(self, descriptor: int, operation: int, /) -> None: ...


sys.path.insert(0, str(Path(__file__).resolve().parent))
from skill_request import MAX_REQUEST_BYTES, Reply, Request, blocked, parse_request  # noqa: E402
from skill_runtime_frame import FrameError, validate_frame  # noqa: E402

PREPARED_TTL_SECONDS = 3600
RESULT_TTL_SECONDS = 24 * 3600
TERMINAL_TTL_SECONDS = 7 * 24 * 3600
CANCEL_GRACE_SECONDS = 5
IPC_SEND_TIMEOUT_SECONDS = 5.0
MAX_OPERATIONS = 256
MAX_BUNDLES = 64
MAX_STATE_BYTES = 65536
MAX_RESULT_BYTES = 128 * 1024 * 1024
MAX_BUNDLE_BYTES = 16 * 1024 * 1024
_OWNER = {"schema_version": 1, "owner": "reprollm-skill-operations"}
_ID = re.compile(r"[0-9a-f]{32}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TERMINAL = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
_STATES = _TERMINAL | {"PREPARED", "STARTING", "RUNNING", "FINALIZING", "UNKNOWN"}
_CONTROL = frozenset({"operation.status", "operation.result", "operation.cancel"})


def _operation_os() -> _OperationOS:
    # Platform checks stay authoritative; importing this module must not resolve Linux features.
    return cast("_OperationOS", os)


def _operation_signal() -> _OperationSignal:
    return cast("_OperationSignal", signal)


class OperationError(ValueError):
    """Fixed diagnostic without source paths, options or exception messages."""


class OperationCancelled(BaseException):
    """Escape native broad Exception recovery before any publication."""


def _json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _utc(value: float | None = None) -> str:
    return (
        datetime.fromtimestamp(time.time() if value is None else value, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _epoch(value: Any) -> float:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OperationError("operation_state_invalid")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise OperationError("operation_state_invalid")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise OperationError("operation_state_invalid")


def _private(path: Path, *, directory: bool = False) -> None:
    info = path.lstat()
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected(info.st_mode) or info.st_mode & 0o077:
        raise OperationError("operation_private_state_required")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise OperationError("operation_private_state_required")


def _directory(path: Path) -> None:
    if path.is_symlink():
        raise OperationError("operation_state_symlink_refused")
    path.mkdir(mode=0o700, exist_ok=True)
    _private(path, directory=True)


def _raw(path: Path, limit: int) -> bytes:
    native = _operation_os()
    descriptor = os.open(path, os.O_RDONLY | native.O_NOFOLLOW | native.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_mode & 0o077
            or info.st_uid != native.geteuid()
        ):
            raise OperationError("operation_private_state_required")
        if info.st_size > limit:
            raise OperationError("operation_state_limit")
        raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise OperationError("operation_state_limit")
        return raw


def _decode(raw: bytes) -> dict[str, Any]:
    value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    if (
        not isinstance(value, dict)
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != 1
    ):
        raise OperationError("operation_state_invalid")
    return value


def _finite(value: Any, depth: int = 0) -> None:
    if depth > 128 or isinstance(value, float) and not math.isfinite(value):
        raise OperationError("operation_result_invalid")
    if isinstance(value, dict):
        for child in value.values():
            _finite(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _finite(child, depth + 1)


def _claim(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "environment", "lease_id"}:
        raise OperationError("operation_lease_invalid")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or any(
            not isinstance(value[key], str) or not _ID.fullmatch(value[key])
            for key in ("environment", "lease_id")
        )
    ):
        raise OperationError("operation_lease_invalid")
    return value


def _read(path: Path, limit: int = MAX_STATE_BYTES) -> dict[str, Any]:
    return _decode(_raw(path, limit))


def _atomic(path: Path, raw: bytes, *, exclusive: bool = False) -> None:
    if path.is_symlink():
        raise OperationError("operation_state_symlink_refused")
    descriptor, name = tempfile.mkstemp(prefix=".operation-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _save(path: Path, record: dict[str, Any]) -> None:
    raw = _json(record)
    if len(raw) > MAX_STATE_BYTES:
        raise OperationError("operation_state_limit")
    _atomic(path, raw)


def _store(home: Path, *, create: bool) -> Path:
    if home.is_symlink():
        raise OperationError("operation_state_symlink_refused")
    store = home / "operations"
    if not store.exists() and not create:
        raise OperationError("operation_unknown")
    if create:
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        _directory(store)
    else:
        _private(store, directory=True)
    marker = store / "owner.json"
    if not marker.exists() and create:
        if any(store.iterdir()):
            raise OperationError("operation_ownership_required")
        with contextlib.suppress(FileExistsError):
            _atomic(marker, _json(_OWNER), exclusive=True)
    if _read(marker) != _OWNER:
        raise OperationError("operation_ownership_required")
    for name in ("claims", "bundles"):
        child = store / name
        if create:
            _directory(child)
        else:
            _private(child, directory=True)
    return store


@contextlib.contextmanager
def _lock(path: Path) -> Iterator[None]:
    import fcntl

    locking = cast("_OperationFileLock", fcntl)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | _operation_os().O_NOFOLLOW, 0o600)
    try:
        _private(path)
        deadline = time.monotonic() + 5
        while True:
            try:
                locking.flock(descriptor, locking.LOCK_EX | locking.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise OperationError("operation_busy") from None
                time.sleep(0.01)
        yield
    finally:
        os.close(descriptor)


def _platform() -> bool:
    supported = (
        sys.platform.startswith("linux")
        and hasattr(os, "pidfd_open")
        and hasattr(signal, "pidfd_send_signal")
    )
    if not supported:
        return False
    try:
        descriptor = _operation_os().pidfd_open(os.getpid())
        os.close(descriptor)
        return _process_identity(os.getpid()) is not None
    except OSError:
        return False


def _process_identity(pid: int) -> str | None:
    try:
        value = Path(f"/proc/{pid}/stat").read_text()
        fields = value[value.rfind(")") + 2 :].split()
        if fields[0] == "Z":
            return None
        boot = Path("/proc/sys/kernel/random/boot_id").read_bytes().strip()
        return _sha(boot + b":" + str(pid).encode() + b":" + fields[19].encode())
    except (OSError, ValueError, IndexError):
        return None


def _signal_owned(record: dict[str, Any], number: int = signal.SIGTERM) -> bool:
    pid = record.get("worker_pid")
    expected = record.get("worker_identity")
    if type(pid) is not int or not isinstance(expected, str) or not _platform():
        return False
    descriptor: int | None = None
    try:
        descriptor = _operation_os().pidfd_open(pid)
        if _process_identity(pid) != expected:
            return False
        _operation_signal().pidfd_send_signal(descriptor, number)
        return True
    except OSError:
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _project(root: Path) -> str:
    return _sha(os.fsencode(str(root.resolve(strict=True))))


def _intent(request: Request, root: Path) -> str:
    value = dataclasses.asdict(request)
    value.pop("response")
    value["project"] = _project(root)
    value["options"].pop("operation_id", None)
    value["grants"].pop("install", None)
    return _sha(_json(value))


def _token(request: Request) -> str:
    value = request.options.get("operation_id")
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise OperationError("operation_id_required")
    return value


def _record(store: Path, token: str, root: Path) -> tuple[Path, dict[str, Any]]:
    folder = store / "claims" / token
    _private(folder, directory=True)
    path = folder / "status.json"
    record = _read(path)
    if (
        record.get("operation_id") != token
        or record.get("kind") != "lock"
        or record.get("state") not in _STATES
    ):
        raise OperationError("operation_state_invalid")
    if record.get("project_identity") != _project(root):
        raise OperationError("operation_project_mismatch")
    for key in ("intent_identity", "policy_identity", "nonce_hash", "bundle_id"):
        if not isinstance(record.get(key), str) or not _HASH.fullmatch(record[key]):
            raise OperationError("operation_state_invalid")
    _epoch(record.get("created_at"))
    _epoch(record.get("updated_at"))
    if (
        record.get("state") == "PREPARED"
        and time.time() - _epoch(record["created_at"]) > PREPARED_TTL_SECONDS
    ):
        raise OperationError("operation_preparation_expired")
    if type(record.get("cancel_requested")) is not bool:
        raise OperationError("operation_state_invalid")
    return path, record


def _public(record: dict[str, Any]) -> dict[str, Any]:
    state = record["state"]
    return {
        "operation_id": record["operation_id"],
        "kind": record["kind"],
        "state": state,
        "execution_started": False if state == "PREPARED" else record.get("execution_started"),
        "result_available": bool(record.get("result_sha256"))
        and time.time() - _epoch(record.get("ended_at")) <= RESULT_TTL_SECONDS,
        "artifact_publication": record.get("artifact_publication", "none"),
        "cancel_requested": bool(record.get("cancel_requested")),
        "cancel_delivered": bool(record.get("cancel_delivered")),
        "cancel_escalated": bool(record.get("cancel_escalated")),
        "safe_to_repeat": False,
    }


def _status(request: Request, record: dict[str, Any]) -> Reply:
    diagnostics = [{"code": "operation_completion_unknown"}] if record["state"] == "UNKNOWN" else []
    if record.get("failure_code") == "operation_launch_failed":
        diagnostics.append({"code": "operation_launch_failed"})
    if record.get("lease_cleanup_failed") is True:
        diagnostics.append({"code": "operation_lease_cleanup_failed"})
    return Reply(
        request.action,
        complete=record["state"] != "UNKNOWN",
        data={"operation": _public(record)},
        diagnostics=diagnostics,
    )


def _worker_proof(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        **{
            key: record[key]
            for key in (
                "operation_id",
                "kind",
                "project_identity",
                "intent_identity",
                "policy_identity",
                "bundle_id",
                "nonce_hash",
                "worker_pid",
                "worker_identity",
                "lease",
            )
        },
    }


def _acknowledged(path: Path, record: dict[str, Any]) -> bool:
    target = path.parent / "worker.json"
    if not target.exists() and not target.is_symlink():
        if record["state"] == "STARTING":
            return False
        raise OperationError("operation_worker_ack_missing")
    if _read(target) != _worker_proof(record):
        raise OperationError("operation_worker_ownership_changed")
    return True


def _refresh(path: Path, record: dict[str, Any]) -> None:
    if record["state"] not in {"STARTING", "RUNNING", "FINALIZING"}:
        return
    _acknowledged(path, record)
    pid = record.get("worker_pid")
    expected = record.get("worker_identity")
    if (
        type(pid) is not int
        or not isinstance(expected, str)
        or not _HASH.fullmatch(expected)
        or _process_identity(pid) != expected
    ):
        record.update(state="UNKNOWN", updated_at=_utc(), artifact_publication="unknown")
        _save(path, record)


def _safe_reply(value: dict[str, Any]) -> Reply:
    _finite(value)
    diagnostics = value.get("diagnostics")
    if not isinstance(diagnostics, list) or not all(isinstance(item, dict) for item in diagnostics):
        raise OperationError("operation_result_invalid")
    header = {**value, "data": None, "diagnostics": []}
    validate_frame(_json(header), expected_action="lock")
    if value.get("next_cursor") is not None or value.get("snapshot") is not None:
        raise OperationError("operation_result_invalid")
    return Reply(**value)


def _result(request: Request, path: Path, record: dict[str, Any]) -> Reply:
    reply = _status(request, record)
    if not record.get("result_sha256"):
        reply.diagnostics.append({"code": "operation_result_not_available"})
        return reply
    if time.time() - _epoch(record.get("ended_at")) > RESULT_TTL_SECONDS:
        reply.data["result_expired"] = True
        reply.diagnostics.append({"code": "operation_result_expired"})
        return reply
    target = path.parent / "result.json"
    raw = _raw(target, MAX_RESULT_BYTES)
    data = _decode(raw)
    if _sha(raw) != record["result_sha256"]:
        raise OperationError("operation_result_changed")
    native = _safe_reply(data)
    reply.cli_exit_code, reply.gate_failed, reply.child_exit_code = (
        native.cli_exit_code,
        native.gate_failed,
        native.child_exit_code,
    )
    reply.data["result"] = native.as_dict()
    return reply


def control(request: Request, *, home: Path, root: Path) -> Reply | None:
    """Query/replay existing ownership before any active-install preparation."""
    is_replay = (
        request.action == "lock"
        and "operation_id" in request.options
        and not request.options.get("check", False)
    )
    if request.action not in _CONTROL and not is_replay:
        return None
    if request.action == "operation.cancel" and not request.grants.write:
        return blocked(request.action, "write_authorization_required", needs_authorization=True)
    try:
        if not _platform():
            raise OperationError("operation_platform_unavailable")
        token = _token(request)
        store = _store(home, create=False)
        path, record = _record(store, token, root)
        with _lock(path.parent / "lock"):
            path, record = _record(store, token, root)
            if is_replay and record["intent_identity"] != _intent(request, root):
                raise OperationError("operation_intent_changed")
            if is_replay and record["state"] == "PREPARED":
                return None
            _refresh(path, record)
            if request.action == "operation.cancel":
                if record["state"] == "PREPARED":
                    record.update(state="CANCELLED", execution_started=False, ended_at=_utc())
                elif record["state"] in {"STARTING", "RUNNING", "FINALIZING"}:
                    record["cancel_requested"] = True
                    record.setdefault("cancel_requested_at", _utc())
                    if record["state"] != "FINALIZING" and _acknowledged(path, record):
                        escalate = (
                            record.get("cancel_delivered")
                            and time.time() - _epoch(record["cancel_requested_at"])
                            >= CANCEL_GRACE_SECONDS
                        )
                        number = _operation_signal().SIGKILL if escalate else signal.SIGTERM
                        record["cancel_delivered"] = _signal_owned(record, number)
                        record["cancel_escalated"] = bool(escalate)
                        if not record["cancel_delivered"]:
                            record.update(state="UNKNOWN", artifact_publication="unknown")
                record["updated_at"] = _utc()
                _save(path, record)
            return (
                _result(request, path, record)
                if request.action == "operation.result"
                else _status(request, record)
            )
    except (OSError, ValueError, TypeError, KeyError, RecursionError, FrameError) as error:
        return blocked(
            request.action,
            str(error) if isinstance(error, OperationError) else "operation_state_unavailable",
        )


def _bundle(store: Path) -> str:
    scripts = Path(__file__).resolve().parent
    source = {"scripts/" + p.name: p for p in sorted(scripts.glob("*.py"))}
    source["assets/install-catalog.json"] = scripts.parent / "assets/install-catalog.json"
    if len(source) > 128:
        raise OperationError("operation_bundle_limit")
    content: dict[str, bytes] = {}
    total = 0
    for role, path in source.items():
        if path.is_symlink() or not path.is_file():
            raise OperationError("operation_helper_source_invalid")
        total += path.stat().st_size
        if total > MAX_BUNDLE_BYTES:
            raise OperationError("operation_bundle_limit")
        content[role] = path.read_bytes()
    manifest = {"schema_version": 1, "files": {role: _sha(raw) for role, raw in content.items()}}
    token = _sha(_json(manifest))
    target = store / "bundles" / token
    if target.exists():
        _verify_bundle(target, token)
        return token
    if len(list((store / "bundles").iterdir())) >= MAX_BUNDLES:
        raise OperationError("operation_bundle_limit")
    with tempfile.TemporaryDirectory(prefix=".bundle-", dir=store / "bundles") as name:
        temporary = Path(name)
        for role, raw in content.items():
            dest = temporary / role
            dest.parent.mkdir(mode=0o700, exist_ok=True)
            _atomic(dest, raw)
        _save(temporary / "manifest.json", manifest)
        if any(path.read_bytes() != content[role] for role, path in source.items()):
            raise OperationError("operation_helper_source_changed")
        try:
            os.rename(temporary, target)
        except FileExistsError:
            _verify_bundle(target, token)
    return token


def _verify_bundle(target: Path, token: str) -> None:
    _private(target, directory=True)
    manifest = _read(target / "manifest.json")
    if _sha(_json(manifest)) != token or not isinstance(manifest.get("files"), dict):
        raise OperationError("operation_helper_bundle_changed")
    expected = {"manifest.json", *manifest["files"]}
    actual = set()
    total = 0
    for path in target.rglob("*"):
        if path.is_symlink():
            raise OperationError("operation_helper_bundle_changed")
        if path.is_dir():
            _private(path, directory=True)
        else:
            _private(path)
            role = path.relative_to(target).as_posix()
            actual.add(role)
            total += path.stat().st_size
            if total > MAX_BUNDLE_BYTES + MAX_STATE_BYTES:
                raise OperationError("operation_bundle_limit")
            if role != "manifest.json" and _sha(path.read_bytes()) != manifest["files"].get(role):
                raise OperationError("operation_helper_bundle_changed")
    if actual != expected:
        raise OperationError("operation_helper_bundle_changed")


def _cleanup(store: Path) -> None:
    now = time.time()
    references = set()
    for folder in (store / "claims").iterdir():
        if folder.is_symlink() or not folder.is_dir() or not _ID.fullmatch(folder.name):
            raise OperationError("operation_ownership_required")
        with _lock(folder / "lock"):
            record = _read(folder / "status.json")
            if (
                record.get("operation_id") != folder.name
                or record.get("kind") != "lock"
                or record.get("state") not in _STATES
            ):
                raise OperationError("operation_ownership_required")
            state = record.get("state")
            expired = (
                state == "PREPARED"
                and now - _epoch(record.get("created_at")) > PREPARED_TTL_SECONDS
            )
            expired = (
                expired
                or state in _TERMINAL
                and now - _epoch(record.get("ended_at")) > TERMINAL_TTL_SECONDS
            )
            if expired and record.get("lease") is None:
                if set(p.name for p in folder.iterdir()) - {
                    "lock",
                    "status.json",
                    "result.json",
                    "worker.json",
                }:
                    raise OperationError("operation_ownership_required")
                for file in folder.iterdir():
                    _private(file)
                    file.unlink()
                folder.rmdir()
            else:
                references.add(record.get("bundle_id"))
                if state in _TERMINAL and now - _epoch(record.get("ended_at")) > RESULT_TTL_SECONDS:
                    (folder / "result.json").unlink(missing_ok=True)
    for folder in (store / "bundles").iterdir():
        if folder.name not in references and _HASH.fullmatch(folder.name):
            _verify_bundle(folder, folder.name)
            shutil.rmtree(folder)


def _send_input(stream: IO[bytes], raw: bytes) -> None:
    """Send one complete frame with bounded waiting, without buffering raw input."""
    descriptor = stream.fileno()
    remaining = memoryview(len(raw).to_bytes(4, "big") + raw)
    deadline = time.monotonic() + IPC_SEND_TIMEOUT_SECONDS
    try:
        _operation_os().set_blocking(descriptor, False)
        with selectors.DefaultSelector() as ready:
            ready.register(descriptor, selectors.EVENT_WRITE)
            while remaining:
                timeout = deadline - time.monotonic()
                if timeout <= 0 or not ready.select(timeout):
                    raise OperationError("operation_start_input_timeout")
                try:
                    sent = os.write(descriptor, remaining[:65536])
                except BlockingIOError:
                    continue
                if sent <= 0:
                    raise OperationError("operation_start_input_failed")
                remaining = remaining[sent:]
    finally:
        # os.write bypasses BufferedWriter, so close has no pending buffer to flush.
        with contextlib.suppress(OSError, ValueError):
            stream.close()


def start(
    request: Request,
    *,
    home: Path,
    root: Path,
    identity: str,
    manager: Any,
    environment_name: str,
    lease_factory: Callable[..., Any],
) -> Reply:
    """Prepare without work; start only a matching existing claim exactly once."""
    try:
        record: dict[str, Any]
        if not _platform():
            raise OperationError("operation_platform_unavailable")
        if (
            request.action != "lock"
            or request.options.get("check", False)
            or not request.options.get("hash_large_files", False)
        ):
            raise OperationError("operation_kind_unavailable")
        if not request.options.get("preview", False) and not request.grants.write:
            return blocked(request.action, "write_authorization_required", needs_authorization=True)
        if not request.options.get("offline", False) and not request.grants.network:
            return blocked(
                request.action, "network_authorization_required", needs_authorization=True
            )
        if "operation_id" in request.options:
            existing = control(request, home=home, root=root)
            if existing is not None:
                return existing
            store = _store(home, create=False)
            token = _token(request)
        else:
            store = _store(home, create=True)
            with _lock(store / "registry-lock"):
                _cleanup(store)
                if len(list((store / "claims").iterdir())) >= MAX_OPERATIONS:
                    raise OperationError("operation_store_limit")
                bundle_id = _bundle(store)
                token = uuid.uuid4().hex
                folder = store / "claims" / token
                _directory(folder)
                record = {
                    "schema_version": 1,
                    "operation_id": token,
                    "kind": "lock",
                    "state": "PREPARED",
                    "created_at": _utc(),
                    "updated_at": _utc(),
                    "ended_at": None,
                    "project_identity": _project(root),
                    "intent_identity": _intent(request, root),
                    "policy_identity": identity,
                    "bundle_id": bundle_id,
                    "nonce_hash": _sha(os.urandom(32)),
                    "worker_pid": None,
                    "worker_identity": None,
                    "lease": None,
                    "cancel_requested": False,
                    "cancel_delivered": False,
                    "execution_started": False,
                    "artifact_publication": "none",
                    "result_sha256": None,
                }
                _save(folder / "status.json", record)
                return _status(request, record)
        path, record = _record(store, token, root)
        with _lock(path.parent / "lock"):
            path, record = _record(store, token, root)
            if record["state"] != "PREPARED":
                return _status(request, record)
            if (
                record["intent_identity"] != _intent(request, root)
                or record["policy_identity"] != identity
            ):
                raise OperationError("operation_intent_changed")
            bundle = store / "bundles" / record["bundle_id"]
            _verify_bundle(bundle, record["bundle_id"])
            with lease_factory(manager, environment_name) as lease:
                claim = _claim(lease.claim)
                nonce = uuid.uuid4().hex
                record.update(
                    state="STARTING",
                    updated_at=_utc(),
                    nonce_hash=_sha(nonce.encode()),
                    lease=claim,
                    execution_started=None,
                )
                _save(path, record)
                # The durable claim precedes launch. Any ambiguous exit retains
                # its environment; only a proven Popen failure reclaims it.
                lease.transfer()
                executable = lease.environment / (
                    "Scripts/python.exe" if os.name == "nt" else "bin/python"
                )
                process: subprocess.Popen[bytes] | None = None
                try:
                    process = subprocess.Popen(
                        [
                            str(executable),
                            "-I",
                            "-B",
                            str(bundle / "scripts/skill_operations.py"),
                            "--worker",
                            "--home",
                            str(home),
                            "--operation-id",
                            token,
                        ],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except OSError:
                    lease.reclaim()
                    record.update(
                        state="FAILED",
                        ended_at=_utc(),
                        updated_at=_utc(),
                        execution_started=False,
                        failure_code="operation_launch_failed",
                    )
                    _save(path, record)
                    process = None
                if process is not None:
                    record.update(
                        worker_pid=process.pid,
                        worker_identity=_process_identity(process.pid),
                        updated_at=_utc(),
                    )
                    _save(path, record)
                    transient = {
                        "schema_version": 1,
                        "request": dataclasses.asdict(request),
                        "root": str(root),
                        "identity": identity,
                        "nonce": nonce,
                        "lease": claim,
                    }
                    raw = _json(transient)
                    if len(raw) > MAX_REQUEST_BYTES + MAX_STATE_BYTES:
                        raise OperationError("operation_request_limit")
                    assert process.stdin is not None
                    try:
                        _send_input(process.stdin, raw)
                    except (OSError, ValueError) as error:
                        record.update(
                            state="UNKNOWN",
                            artifact_publication="unknown",
                            updated_at=_utc(),
                            failure_code=str(error)
                            if isinstance(error, OperationError)
                            else "operation_start_input_failed",
                        )
                        _save(path, record)
                    return _status(request, record)
            cleanup_failed = getattr(lease, "cleanup_failed", True) is not False
            if not cleanup_failed:
                record["lease"] = None
            record["lease_cleanup_failed"] = cleanup_failed
            _save(path, record)
            return _status(request, record)
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        return blocked(
            request.action,
            str(error) if isinstance(error, OperationError) else "operation_unavailable",
        )


@dataclass
class WorkerContext:
    home: Path
    root: Path
    identity: str
    operation_id: str
    claim: dict[str, Any]
    store: Path
    nonce: str
    publishing: bool = False
    publication_started: bool = False

    def _owned(self) -> tuple[Path, dict[str, Any]]:
        path, record = _record(self.store, self.operation_id, self.root)
        if record["nonce_hash"] != _sha(self.nonce.encode()) or record.get("lease") != self.claim:
            raise OperationError("operation_worker_ownership_changed")
        if record.get("worker_pid") != os.getpid() or record.get(
            "worker_identity"
        ) != _process_identity(os.getpid()):
            raise OperationError("operation_worker_ownership_changed")
        if (path.parent / "worker.json").exists() or (path.parent / "worker.json").is_symlink():
            _acknowledged(path, record)
        return path, record

    def check_cancel(self) -> None:
        path, record = self._owned()
        with _lock(path.parent / "lock"):
            _, record = self._owned()
            if record["cancel_requested"]:
                raise OperationCancelled

    @contextlib.contextmanager
    def publication(self) -> Iterator[None]:
        path, record = self._owned()
        with _lock(path.parent / "lock"):
            _, record = self._owned()
            if record["cancel_requested"]:
                raise OperationCancelled
            record.update(state="FINALIZING", updated_at=_utc())
            _save(path, record)
        self.publishing = True
        self.publication_started = True
        try:
            yield
        finally:
            self.publishing = False


def _read_exact(stream: Any, count: int) -> bytes:
    data = bytearray()
    while len(data) < count:
        part = stream.read(count - len(data))
        if not part:
            raise OperationError("operation_request_incomplete")
        data.extend(part)
    return bytes(data)


def worker_main(home: Path, operation_id: str, request_pipe: int = 0) -> int:
    """One fixed trusted worker entry. Raw streams are already DEVNULL."""
    context: WorkerContext | None = None
    record: dict[str, Any] | None = None
    reply: Reply | None = None
    lease: dict[str, Any] | None = None
    previous_signals: dict[int, Any] = {}
    try:
        with os.fdopen(os.dup(request_pipe), "rb") as stream:
            size = int.from_bytes(_read_exact(stream, 4), "big")
            if not 0 < size <= MAX_REQUEST_BYTES + MAX_STATE_BYTES:
                raise OperationError("operation_request_limit")
            transient = json.loads(
                _read_exact(stream, size), object_pairs_hook=_pairs, parse_constant=_constant
            )
        if request_pipe == 0:
            descriptor = os.open(os.devnull, os.O_RDONLY)
            try:
                os.dup2(descriptor, 0)
            finally:
                os.close(descriptor)
        if (
            set(transient) != {"schema_version", "request", "root", "identity", "nonce", "lease"}
            or transient["schema_version"] != 1
        ):
            raise OperationError("operation_request_invalid")
        request = parse_request(transient["request"])
        root = Path(transient["root"]).resolve(strict=True)
        if _token(request) != operation_id or request.action != "lock":
            raise OperationError("operation_request_invalid")
        store = _store(home, create=False)
        context = WorkerContext(
            home,
            root,
            transient["identity"],
            operation_id,
            _claim(transient["lease"]),
            store,
            transient["nonce"],
        )
        path, record = context._owned()
        with _lock(path.parent / "lock"):
            path, record = context._owned()
            if (
                record["intent_identity"] != _intent(request, root)
                or record["policy_identity"] != context.identity
            ):
                raise OperationError("operation_intent_changed")
            _verify_bundle(store / "bundles" / record["bundle_id"], record["bundle_id"])
            ack = path.parent / "worker.json"
            try:
                _atomic(ack, _json(_worker_proof(record)), exclusive=True)
            except FileExistsError:
                _acknowledged(path, record)
            record.update(state="RUNNING", execution_started=True, updated_at=_utc())
            _save(path, record)
            lease = context.claim

        def cancel(number: int, frame: Any) -> None:
            if context is not None and not context.publication_started:
                raise OperationCancelled

        previous_signals = {
            number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)
        }
        signal.signal(signal.SIGTERM, cancel)
        signal.signal(signal.SIGINT, cancel)
        context.check_cancel()
        from skill_runtime import operation_worker_entry

        reply = operation_worker_entry(request, context)
        if not isinstance(reply, Reply):
            raise OperationError("operation_result_invalid")
        native_invocation = reply.invocation
        try:
            _safe_reply(reply.as_dict())
            raw = _json(reply.as_dict())
            if len(raw) > MAX_RESULT_BYTES:
                raise OperationError("operation_result_limit")
        except (OSError, ValueError, TypeError, RecursionError):
            # Delivery is distinct from native completion. Preserve every known
            # exit fact without keeping the invalid/oversized original value.
            reply = Reply(
                "lock",
                invocation="internal_error",
                complete=False,
                cli_exit_code=reply.cli_exit_code if type(reply.cli_exit_code) is int else None,
                gate_failed=reply.gate_failed if type(reply.gate_failed) is bool else None,
                child_exit_code=reply.child_exit_code
                if type(reply.child_exit_code) is int
                else None,
                data={
                    "scope": "incomplete_delivery",
                    "safe_to_repeat": False,
                    "artifact_publication_unknown": context.publication_started,
                },
                diagnostics=[{"code": "operation_result_delivery_failed"}],
            )
            raw = _json(reply.as_dict())
        path, record = context._owned()
        with _lock(path.parent / "lock"):
            path, record = context._owned()
            _atomic(path.parent / "result.json", raw)
            record.update(
                state="COMPLETED" if native_invocation == "handled_result" else "FAILED",
                result_sha256=_sha(raw),
                ended_at=_utc(),
                updated_at=_utc(),
                artifact_publication="known" if context.publication_started else "none",
            )
            _save(path, record)
    except OperationCancelled:
        if context is not None:
            path, record = context._owned()
            with _lock(path.parent / "lock"):
                record.update(
                    state="CANCELLED",
                    ended_at=_utc(),
                    updated_at=_utc(),
                    artifact_publication="none",
                )
                _save(path, record)
    except BaseException:
        if context is not None:
            with contextlib.suppress(OSError, ValueError):
                path, record = context._owned()
                with _lock(path.parent / "lock"):
                    record.update(
                        state="UNKNOWN", updated_at=_utc(), artifact_publication="unknown"
                    )
                    _save(path, record)
        return 1
    finally:
        for number, handler in previous_signals.items():
            signal.signal(number, handler)
        if lease is not None and context is not None:
            with contextlib.suppress(Exception):
                from skill_runtime import release_operation_lease

                if record is not None and record["state"] in _TERMINAL:
                    released = release_operation_lease(home, lease)
                    path, current = context._owned()
                    with _lock(path.parent / "lock"):
                        if released:
                            current["lease"] = None
                        current["lease_cleanup_failed"] = not released
                        _save(path, current)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--operation-id", required=True)
    args = parser.parse_args(argv)
    if not _ID.fullmatch(args.operation_id) or not _platform():
        return 2
    return worker_main(args.home, args.operation_id)


if __name__ == "__main__":
    raise SystemExit(main())
