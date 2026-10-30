"""Bound complete native log lines before applying the existing display privacy."""

from __future__ import annotations

import contextlib
import getpass
import hashlib
import json
import os
import signal
import socket
import stat
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, TextIO, cast

from skill_request import Reply, Request, blocked

MAX_LOG_BYTES = 16 * 1024 * 1024
MAX_CONTEXT_BYTES = 128 * 1024 * 1024
SCAN_SECONDS = 5.0


class LogError(ValueError):
    """Fixed private log-scope diagnostic."""


class _ContextDeadline(BaseException):
    """Escape the native tee's broad capture-error recovery without raw drains."""


@contextlib.contextmanager
def _deadline() -> Iterator[Callable[[], None]]:
    if (
        not sys.platform.startswith("linux")
        or threading.current_thread() is not threading.main_thread()
    ):
        raise LogError("run_log_context_deadline_unavailable")
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    if any(previous_timer):
        raise LogError("run_log_context_deadline_unavailable")
    previous = signal.getsignal(signal.SIGALRM)
    until = time.monotonic() + SCAN_SECONDS

    def expired(number: int, frame: Any) -> None:
        raise _ContextDeadline

    def check() -> None:
        if time.monotonic() >= until:
            raise _ContextDeadline

    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, SCAN_SECONDS)
        yield check
    except _ContextDeadline:
        raise LogError("run_log_context_deadline") from None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@dataclass(frozen=True)
class _Window:
    prefix: bytes
    identity: str | None
    limited: bool
    partial: bool
    context_sha256: str
    context_bytes: int
    text: str = ""
    diagnostics: tuple[dict[str, Any], ...] = ()


class _Lines:
    def __init__(self, stream: BinaryIO, end: int, offset: int, check: Callable[[], None]) -> None:
        self.stream, self.end, self.offset, self.check = stream, end, offset, check
        self.start = self.position = 0
        self.digest, self.selected = hashlib.sha256(), hashlib.sha256()

    def __iter__(self) -> Iterator[str]:
        return self

    def __next__(self) -> str:
        self.check()
        if self.position == self.end:
            raise StopIteration
        self.start = self.position
        raw = self.stream.readline(min(MAX_LOG_BYTES + 1, self.end - self.position))
        if not raw.endswith(b"\n") or len(raw) > MAX_LOG_BYTES:
            raise LogError("run_log_context_unproven")
        self.position += len(raw)
        if self.start < self.offset < self.position:
            raise LogError("run_log_changed")
        self.digest.update(raw)
        if self.start >= self.offset:
            self.selected.update(raw)
        return raw.decode("utf-8")

    def read(self, size: int = -1) -> str:
        # Native capture recovery may request a raw drain after privacy failure.
        # This bounded read-only view terminates it instead of exposing raw bytes.
        return ""

    def close(self) -> None:
        pass


class _Sink:
    def __init__(self, source: _Lines, *, selected: bool) -> None:
        self.source, self.selected = source, selected
        self.parts: list[str] = []
        self.bytes = 0

    def write(self, value: str) -> int:
        self.source.check()
        if self.selected and self.source.start >= self.source.offset:
            self.bytes += len(value.encode("utf-8"))
            if self.bytes > 4 * MAX_LOG_BYTES:
                raise LogError("run_log_context_unproven")
            self.parts.append(value)
        return len(value)

    def flush(self) -> None:
        pass


def _digest_prefix(stream: BinaryIO, count: int, check: Callable[[], None]) -> str:
    stream.seek(0)
    digest = hashlib.sha256()
    remaining = count
    while remaining:
        check()
        block = stream.read(min(65536, remaining))
        if not block:
            raise LogError("run_log_changed")
        digest.update(block)
        remaining -= len(block)
    return digest.hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hash(value: Any) -> str:
    return _sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _context(request: Request, home: Path, root: Path) -> tuple[dict[str, Any], Path]:
    from skill_operations import run_binding, run_directory_identity

    record = run_binding(request, home=home, root=root)
    run_id = record.get("native_run_id")
    if not isinstance(run_id, str):
        raise LogError("run_record_not_allocated")
    if run_directory_identity(root, run_id) != record.get("native_run_identity"):
        raise LogError("run_directory_changed")
    stream = request.options.get("stream", "stdout")
    if stream not in {"stdout", "stderr"}:
        raise LogError("run_log_stream_invalid")
    return record, root / ".reprollm/runs" / run_id / (stream + ".log")


def _window(
    path: Path, root: Path, limit: int, *, offset: int = 0, exact: bool = False, render: bool = True
) -> _Window:
    if sys.platform != "linux":
        raise LogError("run_log_platform_unavailable")
    if not path.exists() and not path.is_symlink():
        if offset:
            raise LogError("run_log_offset_invalid")
        return _Window(b"", None, False, False, _sha(b""), 0)
    if offset > MAX_CONTEXT_BYTES:
        raise LogError("run_log_context_limit")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream, _deadline() as check:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise LogError("run_log_regular_file_required")
        if offset > before.st_size:
            raise LogError("run_log_offset_invalid")
        if offset:
            stream.seek(offset - 1)
            if stream.read(1) != b"\n":
                raise LogError("run_log_offset_requires_complete_line")
        stream.seek(offset)
        raw = stream.read(limit + (0 if exact else 1))
        limited = len(raw) > limit or before.st_size - offset > limit
        raw = raw[:limit]
        stop = raw.rfind(b"\n") + 1
        prefix = raw[:stop]
        end = offset + stop
        if end > MAX_CONTEXT_BYTES:
            raise LogError("run_log_context_limit")
        stream.seek(0)
        text = ""
        notes: list[dict[str, Any]] = []
        if render:
            from skill_runtime import _sanitize

            from reprollm.run.privacy import RunPrivacy
            from reprollm.run.wrapper import _tee

            source = _Lines(stream, end, offset, check)
            sink = _Sink(source, selected=True)
            warnings: list[str] = []
            _tee(
                cast(TextIO, source),
                cast(TextIO, _Sink(source, selected=False)),
                cast(TextIO, sink),
                RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser()),
                warnings,
                "display",
            )
            if warnings or source.position != end or source.selected.hexdigest() != _sha(prefix):
                raise LogError("run_log_context_unproven")
            context_sha256 = source.digest.hexdigest()
            text = "".join(sink.parts)
            text = cast(str, _sanitize(text, root, context=("text",), diagnostics=notes))
        else:
            context_sha256 = _digest_prefix(stream, end, check)
        if _digest_prefix(stream, end, check) != context_sha256:
            raise LogError("run_log_changed")
        after = os.fstat(stream.fileno())
        current = path.lstat()
        if (
            not stat.S_ISREG(current.st_mode)
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise LogError("run_log_changed")
        check()
        return _Window(
            prefix,
            _hash([before.st_dev, before.st_ino]),
            limited,
            stop < len(raw),
            context_sha256,
            end,
            text,
            tuple(notes),
        )


def snapshot_signature(request: Request, *, home: Path, root: Path, data: Any) -> str:
    from skill_operations import run_directory_identity

    if not isinstance(data, dict) or not isinstance(data.get("log_source"), dict):
        raise LogError("run_log_snapshot_unavailable")
    source = data["log_source"]
    count = source.get("prefix_bytes")
    if type(count) is not int or not 0 <= count <= MAX_LOG_BYTES:
        raise LogError("run_log_snapshot_unavailable")
    offset = source.get("offset_bytes", 0)
    if type(offset) is not int or offset < 0 or offset != request.options.get("offset_bytes", 0):
        raise LogError("run_log_snapshot_unavailable")
    record, path = _context(request, home, root)
    window = _window(path, root, count, offset=offset, exact=True, render=False)
    observed = {
        "run_id": record["native_run_id"],
        "run_identity": run_directory_identity(root, record["native_run_id"]),
        "file_identity": window.identity,
        "prefix_bytes": len(window.prefix),
        "prefix_sha256": _sha(window.prefix),
        "context_bytes": window.context_bytes,
        "context_sha256": window.context_sha256,
        "stream": request.options.get("stream", "stdout"),
        "offset_bytes": offset,
    }
    if observed != source:
        raise LogError("run_log_snapshot_changed")
    return _hash(observed)


def read_logs(request: Request, *, home: Path, root: Path) -> Reply:
    """Release an immutable sanitized complete-line prefix, never raw chunks."""
    from skill_operations import OperationError, run_directory_identity

    try:
        record, path = _context(request, home, root)
        offset = request.options.get("offset_bytes", 0)
        limit = request.options.get("limit_bytes", MAX_LOG_BYTES)
        if (
            type(offset) is not int
            or offset < 0
            or type(limit) is not int
            or not 1 <= limit <= MAX_LOG_BYTES
        ):
            raise LogError("run_log_window_invalid")
        window = _window(path, root, limit, offset=offset)
        prefix, identity, limited, partial = (
            window.prefix,
            window.identity,
            window.limited,
            window.partial,
        )
        stop = len(prefix)
        notes = list(window.diagnostics)
        safe = window.text
        data = {
            "run_id": record["native_run_id"],
            "scope": "complete_lines_prefix",
            "offset_bytes": offset,
            "next_offset_bytes": offset + stop if stop and (partial or limited) else None,
            "more_available": partial or limited,
            "line_exceeds_window": limited and not stop,
            "text": safe,
            "log_available": identity is not None,
            "capture_output": record.get("capture_output"),
            "withheld_partial_line": partial,
            "limit_reached": limited,
            "log_source": {
                "run_id": record["native_run_id"],
                "run_identity": run_directory_identity(root, record["native_run_id"]),
                "file_identity": identity,
                "prefix_bytes": len(prefix),
                "prefix_sha256": _sha(prefix),
                "context_bytes": window.context_bytes,
                "context_sha256": window.context_sha256,
                "stream": request.options.get("stream", "stdout"),
                "offset_bytes": offset,
            },
        }
        snapshot_signature(request, home=home, root=root, data=data)
        if partial:
            notes.append({"code": "run_log_partial_line_withheld"})
        if limited:
            notes.append({"code": "run_log_prefix_limit"})
            if not stop:
                notes.append(
                    {
                        "code": "run_log_line_exceeds_window",
                        "text": (
                            "Increase limit_bytes up to 16777216 for one complete line; "
                            "a longer line is unsupported and remains withheld."
                        ),
                    }
                )
        if identity is None:
            notes.append(
                {
                    "code": "run_capture_log_unavailable",
                    "text": (
                        "Capture may be disabled or pending; use capture_output: true "
                        "when starting a new authorized run."
                    ),
                }
            )
        return Reply(
            request.action, complete=not (partial or limited), data=data, diagnostics=notes
        )
    except _ContextDeadline:
        return blocked(request.action, "run_log_context_deadline")
    except (OSError, ValueError, RuntimeError) as error:
        return blocked(
            request.action,
            str(error) if isinstance(error, (LogError, OperationError)) else "run_log_unavailable",
        )
