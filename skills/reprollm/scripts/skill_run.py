"""Bind native run selection before the sole recorder call; never supervise a child."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import stat
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast

from skill_request import Reply, Request, blocked

if TYPE_CHECKING:
    from reprollm.schemas.run_record import RunRecord

MAX_CONTROL_BYTES = 2 * 1024 * 1024
_CONTROLS = (
    "reprollm.yaml",
    ".reprollm/project-rules.yaml",
    ".reprollm/config.yaml",
    "reprollm.lock",
)


class RunError(ValueError):
    """A fixed private diagnostic, never a native exception payload."""


class RunLifecycle(Protocol):
    def check_cancel(self) -> None: ...

    def bind_run(self, run_id: str) -> None:
        """Durably bind the actual native ID, or raise before recorder entry."""
        ...


@dataclass(frozen=True)
class _Selection:
    argv: tuple[str, ...]
    cwd: Path
    source: Literal["saved", "explicit"]
    capture: bool
    env_capture: Literal["allowlist", "all"]
    allowlist: tuple[str, ...]
    snapshot: bool
    max_bytes: int
    name: str | None
    controls: str
    cwd_identity: str
    cwd_path: Path
    cwd_mapping: str
    plan_hash: str


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _mapping(path: Path) -> tuple[Any, ...]:
    resolved = path.resolve(strict=False)
    if not path.exists() and not path.is_symlink():
        return ("missing", _sha(os.fsencode(str(resolved))))
    info = path.lstat()
    return (
        stat.S_IFMT(info.st_mode),
        info.st_dev,
        info.st_ino,
        _sha(os.fsencode(str(resolved))),
        _sha(os.fsencode(os.readlink(path))) if path.is_symlink() else None,
    )


def _control(root: Path, role: str) -> tuple[Any, ...]:
    candidate = root / role
    before = _mapping(candidate)
    if before[0] == "missing":
        return before
    target = candidate.resolve(strict=True)
    if not target.is_relative_to(root):
        raise RunError("run_control_scope_required")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(target, flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise RunError("run_control_regular_file_required")
        raw = stream.read(MAX_CONTROL_BYTES + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > MAX_CONTROL_BYTES or after.st_size > MAX_CONTROL_BYTES:
        raise RunError("run_control_limit")
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(info, name) != getattr(after, name) for name in fields):
        raise RunError("run_plan_changed")
    if _mapping(candidate) != before:
        raise RunError("run_plan_changed")
    return (*before, _sha(raw))


def _controls(root: Path) -> str:
    info = root.stat()
    return _sha(
        _canonical(
            {
                "root": [_sha(os.fsencode(str(root))), info.st_dev, info.st_ino],
                "roles": {role: _control(root, role) for role in _CONTROLS},
            }
        )
    )


def _cwd_identity(cwd: Path) -> str:
    info = cwd.stat()
    if not stat.S_ISDIR(info.st_mode) or cwd.resolve(strict=True) != cwd:
        raise RunError("run_plan_changed")
    return _sha(_canonical([_sha(os.fsencode(str(cwd))), info.st_dev, info.st_ino]))


def _cwd_mapping(path: Path) -> str:
    # Inspect only the selected lexical chain, preserving parent aliases too.
    chain = [*reversed(path.parents), path]
    return _sha(_canonical([_mapping(part) for part in chain]))


@contextlib.contextmanager
def _at(root: Path) -> Iterator[None]:
    previous = Path.cwd()
    try:
        os.chdir(root)
        yield
    finally:
        os.chdir(previous)


def _selection(request: Request, root: Path, identity: str) -> _Selection:
    from reprollm.core.config import load_config
    from reprollm.run import wrapper
    from reprollm.run.saved import load_saved_invocation

    controls = _controls(root)
    manifest, _, _ = wrapper._safe_load(root)
    options = request.options
    supplied_cwd = options.get("cwd")
    command = options.get("argv")
    cwd_path = root / supplied_cwd if supplied_cwd is not None else root
    if not command and supplied_cwd is None and manifest is not None and manifest.execution:
        cwd_path = root / (manifest.execution.cwd or ".")
    cwd_mapping = _cwd_mapping(cwd_path)
    cwd = cwd_path.resolve()
    if command:
        argv, source = tuple(command), "explicit"
    else:
        # None is semantically distinct: a root-valued override loses saved cwd.
        with _at(root):
            saved = load_saved_invocation(cwd if supplied_cwd is not None else None)
        argv, cwd, source = tuple(saved.argv), saved.cwd, "saved"
    if cwd_path.resolve() != cwd:
        raise RunError("run_plan_changed")
    if not cwd.is_dir() or not cwd.is_relative_to(root):
        raise RunError("run_working_directory_scope_required")
    config = load_config(root).run
    capture = options.get("capture_output")
    capture = config.capture_output if capture is None else capture
    mode = options.get("env_capture", config.env_capture)
    name = options.get("name")
    snapshot = not options.get("no_snapshot", False)
    if _controls(root) != controls or _cwd_mapping(cwd_path) != cwd_mapping:
        raise RunError("run_plan_changed")
    cwd_identity = _cwd_identity(cwd)
    value = {
        "domain": "reprollm.skill.run-plan/v1",
        "identity": identity,
        "controls": controls,
        "argv": argv,
        "cwd": cwd_identity,
        "cwd_mapping": cwd_mapping,
        "source": source,
        "capture": capture,
        "env_capture": mode,
        "allowlist": config.extra_env_allowlist,
        "snapshot": snapshot,
        "max_bytes": config.snapshot_max_bytes,
        "name": name,
    }
    return _Selection(
        argv,
        cwd,
        cast(Literal["saved", "explicit"], source),
        capture,
        mode,
        tuple(config.extra_env_allowlist),
        snapshot,
        config.snapshot_max_bytes,
        name,
        controls,
        cwd_identity,
        cwd_path,
        cwd_mapping,
        _sha(_canonical(value)),
    )


def _failure(
    request: Request, error: Exception, run_id: str | None = None, *, entered: bool = False
) -> Reply:
    from reprollm.core.errors import UserError

    if isinstance(error, RunError):
        reply = blocked(request.action, str(error))
    else:
        reply = Reply(
            request.action,
            invocation="user_error" if isinstance(error, UserError) else "internal_error",
            cli_exit_code=None,
            complete=False,
            diagnostics=[
                {
                    "code": "native_run_error" if isinstance(error, UserError) else "run_failed",
                    "text": "Check the executable, cwd and ReproLLM control documents.",
                }
            ],
        )
    reply.data = {
        "run_id": run_id,
        "record_scope": "unknown",
        "recorder_entered": entered,
        "execution_started": None if entered else False,
    }
    return reply


def _preview_notes(error: Exception, root: Path, code: str) -> list[dict[str, Any]]:
    from skill_runtime import _sanitize

    notes: list[dict[str, Any]] = []
    try:
        text = _sanitize("error: " + str(error) + "\n", root, context=("text",), diagnostics=notes)
        if not isinstance(text, str):
            raise ValueError("diagnostic_projection_failed")
    except Exception:
        text = (
            "Run `reprollm init` if reprollm.yaml is missing; repair reprollm.yaml, "
            ".reprollm/project-rules.yaml, .reprollm/config.yaml or reprollm.lock, "
            "then retry run.preview."
        )
        notes = [{"code": "preview_diagnostic_delivery_failed"}]
    return [{"code": code, "text": text}, *notes]


def preview_run(request: Request, *, root: Path, identity: str) -> Reply:
    """Return a finite launch-plan hash independently of preflight availability."""
    from reprollm.core.errors import UserError
    from reprollm.run.preflight import preview

    try:
        root = root.resolve(strict=True)
        selected = _selection(request, root, identity)
        data: dict[str, Any] = {
            "plan_hash": selected.plan_hash,
            "start_ready": True,
            "command_source": selected.source,
            "execution_started": False,
            "artifacts_written": [],
        }
        try:
            text = preview(
                selected.argv,
                cwd=selected.cwd,
                capture_output=selected.capture,
                env_capture=selected.env_capture,
                snapshot=selected.snapshot,
            )
            data["preflight"] = {"available": True, "text": text + "\n"}
            reply = Reply(request.action, cli_exit_code=0, data=data)
        except UserError as error:
            data["preflight"] = {
                "available": False,
                "code": "native_preflight_unavailable",
            }
            reply = Reply(
                request.action,
                invocation="user_error",
                cli_exit_code=2,
                complete=False,
                data=data,
                diagnostics=_preview_notes(error, root, "native_preflight_unavailable"),
            )
        if (
            _controls(root) != selected.controls
            or _cwd_identity(selected.cwd) != selected.cwd_identity
            or _cwd_mapping(selected.cwd_path) != selected.cwd_mapping
        ):
            raise RunError("run_plan_changed")
        return reply
    except (OSError, ValueError, RuntimeError, UserError) as error:
        reply = _failure(request, error)
        if isinstance(error, UserError):
            reply.cli_exit_code = 2
            reply.diagnostics = _preview_notes(error, root, "native_usage_error")
        return reply


def _worker_io() -> None:
    if (
        not sys.platform.startswith("linux")
        or threading.current_thread() is not threading.main_thread()
    ):
        raise RunError("run_worker_platform_unavailable")
    null = os.stat(os.devnull)
    for number in (0, 1, 2):
        info = os.fstat(number)
        if not stat.S_ISCHR(info.st_mode) or info.st_rdev != null.st_rdev:
            raise RunError("run_worker_streams_not_isolated")


def _folder(root: Path, run_dir: Path) -> tuple[int, int]:
    base = root / ".reprollm/runs"
    if (
        (root / ".reprollm").is_symlink()
        or base.is_symlink()
        or run_dir.is_symlink()
        or run_dir.resolve(strict=True).parent != base
    ):
        raise RunError("run_directory_changed")
    info = run_dir.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise RunError("run_directory_changed")
    return info.st_dev, info.st_ino


def _record_reply(
    request: Request,
    root: Path,
    record: RunRecord,
    *,
    scope: Literal["native_return", "native_readback"] = "native_return",
) -> Reply:
    from skill_runtime import _sanitize

    notes: list[dict[str, Any]] = []
    try:
        safe = _sanitize(
            record.model_dump(mode="json"), root, action="runs.show", diagnostics=notes
        )
    except Exception:
        return Reply(
            request.action,
            invocation="internal_error",
            complete=False,
            child_exit_code=record.exit_code,
            data={
                "run_id": record.run_id,
                "native_status": record.status.value,
                "record_scope": scope,
                "record_delivery": "incomplete",
            },
            diagnostics=[{"code": "run_result_delivery_failed"}],
        )
    return Reply(
        request.action,
        child_exit_code=record.exit_code,
        data={"run_id": record.run_id, "record": safe, "record_scope": scope},
        diagnostics=notes,
    )


def execute_run(request: Request, *, root: Path, identity: str, lifecycle: RunLifecycle) -> Reply:
    """Bind the allocated native ID before one unchanged native recorder call."""
    from reprollm.core.errors import UserError
    from reprollm.core.paths import find_root
    from reprollm.run import wrapper

    if not request.grants.run or not request.grants.write:
        return blocked(request.action, "run_authorization_required", needs_authorization=True)
    if request.grants.plan_hash is None:
        reply = blocked(request.action, "run_plan_required")
        reply.data = {"next_action": "run.preview", "execution_started": False}
        return reply
    run_dir: Path | None = None
    stamp: tuple[int, int] | None = None
    entered = False
    try:
        root = root.resolve(strict=True)
        _worker_io()
        selected = _selection(request, root, identity)
        if selected.plan_hash != request.grants.plan_hash:
            raise RunError("run_plan_changed")
        lifecycle.check_cancel()
        if find_root(selected.cwd) != root:
            raise RunError("run_project_scope_required")
        run_dir = wrapper.create_run_dir(root)
        stamp = _folder(root, run_dir)
        lifecycle.bind_run(run_dir.name)
        if (
            _controls(root) != selected.controls
            or _cwd_identity(selected.cwd) != selected.cwd_identity
            or _cwd_mapping(selected.cwd_path) != selected.cwd_mapping
            or _folder(root, run_dir) != stamp
        ):
            raise RunError("run_plan_changed")
        lifecycle.check_cancel()
        entered = True
        record = wrapper.execute(
            selected.argv,
            root=root,
            cwd=selected.cwd,
            run_dir=run_dir,
            name=selected.name,
            capture_output=selected.capture,
            env_capture=selected.env_capture,
            extra_allowlist=list(selected.allowlist),
            snapshot=selected.snapshot,
            max_bytes=selected.max_bytes,
        )
        return _record_reply(request, root, record)
    except (OSError, ValueError, RuntimeError, UserError) as error:
        reply = _failure(
            request, error, run_dir.name if run_dir is not None else None, entered=entered
        )
        if isinstance(error, UserError) and run_dir is not None and stamp is not None:
            from reprollm.run.reader import read_run

            try:
                if _folder(root, run_dir) != stamp:
                    raise RunError("run_directory_changed")
                partial, _ = read_run(root, run_dir.name)
                if _folder(root, run_dir) != stamp:
                    raise RunError("run_directory_changed")
                known = _record_reply(request, root, partial, scope="native_readback")
                reply.child_exit_code = known.child_exit_code
                reply.data = known.data
                reply.diagnostics += known.diagnostics
            except (OSError, ValueError, RuntimeError, UserError):
                reply.diagnostics.append({"code": "run_partial_record_unavailable"})
        return reply
