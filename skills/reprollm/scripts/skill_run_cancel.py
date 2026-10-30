"""Cancel a verified run worker and witnessed instances, retaining unknown scope.

The recorder alone determines child exit and run status. Session observations
supply finite provenance, not complete containment of arbitrary descendants.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import select
import signal
import sys
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GRACE_NS = 5_000_000_000
MAX_WITNESSES = 128
MAX_PROC_ENTRIES = 32768
DISCOVERY_SECONDS = 2.0


class CancelError(ValueError):
    """A fixed controller diagnostic, without process names or host paths."""


@dataclass(frozen=True)
class Process:
    pid: int
    parent: int
    session: int
    start: int
    namespace: str
    state: str


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _boot() -> str:
    return _sha(Path("/proc/sys/kernel/random/boot_id").read_bytes().strip())


def _identity(process: Process) -> str:
    # This is the existing operation worker generation contract.
    boot = Path("/proc/sys/kernel/random/boot_id").read_bytes().strip()
    return _sha(boot + b":" + str(process.pid).encode() + b":" + str(process.start).encode())


def _process(pid: int) -> Process | None:
    if sys.platform != "linux":
        return None
    if type(pid) is not int or pid <= 0:
        return None
    try:
        descriptor = os.open(f"/proc/{pid}/stat", os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            return None
        fields = raw[raw.rfind(b")") + 2 :].split()
        namespace = os.stat(f"/proc/{pid}/ns/pid")
        return Process(
            pid,
            int(fields[1]),
            int(fields[3]),
            int(fields[19]),
            _sha(f"{namespace.st_dev}:{namespace.st_ino}".encode()),
            fields[0].decode("ascii"),
        )
    except (OSError, ValueError, IndexError, UnicodeError):
        return None


def _pids() -> Iterator[int]:
    deadline = time.monotonic() + DISCOVERY_SECONDS
    count = 0
    with os.scandir("/proc") as entries:
        for entry in entries:
            if time.monotonic() > deadline:
                raise CancelError("run_cancel_discovery_limit")
            if entry.name.isascii() and entry.name.isdecimal():
                count += 1
                if count > MAX_PROC_ENTRIES:
                    raise CancelError("run_cancel_discovery_limit")
                yield int(entry.name)


def _open(pid: int) -> int:
    if sys.platform != "linux":
        raise CancelError("run_cancel_platform_unavailable")
    return os.pidfd_open(pid)


def _close(descriptor: int) -> None:
    os.close(descriptor)


def _send(descriptor: int, number: int) -> None:
    if sys.platform != "linux":
        raise CancelError("run_cancel_platform_unavailable")
    signal.pidfd_send_signal(descriptor, number, None, 0)


def _exited(descriptor: int) -> bool:
    if sys.platform != "linux":
        raise CancelError("run_cancel_platform_unavailable")
    observer = select.poll()
    observer.register(descriptor, select.POLLIN)
    return any(flags & select.POLLIN for _, flags in observer.poll(10))


def _live(process: Process | None) -> bool:
    return process is not None and process.state not in {"Z", "X", "x"}


def _same(current: Process | None, expected: Process) -> bool:
    return (
        _live(current)
        and current is not None
        and (current.pid, current.start, current.session, current.namespace)
        == (expected.pid, expected.start, expected.session, expected.namespace)
    )


def _anchor(record: dict[str, Any], stack: contextlib.ExitStack) -> tuple[Process, int]:
    pid = record.get("worker_pid")
    if type(pid) is not int or pid <= 0:
        raise CancelError("run_cancel_worker_unproven")
    before = _process(pid)
    if not _live(before) or before is None or _identity(before) != record.get("worker_identity"):
        raise CancelError("run_cancel_worker_unproven")
    if before.session != before.pid:
        raise CancelError("run_cancel_session_unproven")
    try:
        descriptor = _open(before.pid)
    except OSError:
        raise CancelError("run_cancel_pidfd_unavailable") from None
    stack.callback(_close, descriptor)
    if not _same(_process(before.pid), before):
        raise CancelError("run_cancel_worker_unproven")
    return before, descriptor


def _depth(process: Process, processes: dict[int, Process], anchor: Process) -> int:
    seen = {process.pid}
    parent = process.parent
    depth = 1
    while parent != anchor.pid and parent in processes and parent not in seen and depth < 64:
        seen.add(parent)
        parent = processes[parent].parent
        depth += 1
    return depth


def _witnesses(
    anchor: Process,
    stack: contextlib.ExitStack,
) -> tuple[list[tuple[Process, int]], bool]:
    witnesses: list[tuple[Process, int]] = []
    observed: list[Process] = []
    limited = False
    try:
        for pid in _pids():
            if pid == anchor.pid:
                continue
            if not _same(_process(anchor.pid), anchor):
                raise CancelError("run_cancel_worker_unproven")
            before = _process(pid)
            if not _live(before) or before is None:
                continue
            observed.append(before)
            if before.session != anchor.session:
                continue
            if before.namespace != anchor.namespace:
                continue
            if len(witnesses) >= MAX_WITNESSES:
                limited = True
                break
            try:
                descriptor = _open(pid)
            except OSError:
                limited = True
                continue
            stack.callback(_close, descriptor)
            if _same(_process(pid), before):
                witnesses.append((before, descriptor))
            else:
                limited = True
    except OSError:
        limited = True
    parents = {anchor.pid} | {
        process.pid
        for process in observed
        if process.session == anchor.session and process.namespace == anchor.namespace
    }
    if any(
        process.parent in parents
        and (process.session != anchor.session or process.namespace != anchor.namespace)
        for process in observed
    ):
        limited = True
    processes = {process.pid: process for process, _ in witnesses}
    witnesses.sort(key=lambda item: (-_depth(item[0], processes, anchor), item[0].pid))
    return witnesses, limited


def _state(record: dict[str, Any]) -> dict[str, Any]:
    current = record.get("run_cancel")
    if current is not None:
        if (
            not isinstance(current, dict)
            or current.get("schema_version") != 1
            or type(current.get("requested_monotonic_ns")) is not int
            or not isinstance(current.get("boot_sha256"), str)
            or not isinstance(current.get("witnesses"), list)
            or len(current["witnesses"]) > MAX_WITNESSES
            or any(
                not isinstance(entry, dict)
                or not isinstance(entry.get("identity_sha256"), str)
                or entry.get("outcome") not in {"pending", "accepted", "refused"}
                for entry in current["witnesses"]
            )
        ):
            raise CancelError("run_cancel_state_unavailable")
        return current
    current = {
        "schema_version": 1,
        "boot_sha256": _boot(),
        "requested_monotonic_ns": time.monotonic_ns(),
        "phase": "requested",
        "cleanup_scope": "unknown_descendants",
        "kill_accepted": 0,
        "lease_must_retain": False,
        "witnesses": [],
    }
    record["run_cancel"] = current
    return current


def _force(
    record: dict[str, Any],
    state: dict[str, Any],
    anchor: Process,
    stack: contextlib.ExitStack,
    save: Callable[[], None],
) -> None:
    if sys.platform != "linux":
        raise CancelError("run_cancel_platform_unavailable")
    if not isinstance(record.get("native_run_id"), str) or not record["native_run_id"]:
        raise CancelError("run_cancel_child_binding_unproven")
    witnesses, limited = _witnesses(anchor, stack)
    # A later scan can lose an escaped instance's former parent edge. It cannot
    # reconcile an earlier gap merely by observing fewer current candidates.
    state["discovery_limited"] = bool(state.get("discovery_limited")) or limited
    state["lease_must_retain"] = state["discovery_limited"]
    state["phase"] = "witnessed_instances_only"
    journal = state["witnesses"]
    by_identity = {item["identity_sha256"]: item for item in journal}
    for process, descriptor in witnesses:
        identity = _identity(process)
        entry = by_identity.get(identity)
        if entry is not None:
            # A prior planned-but-unacknowledged signal is not permission to
            # replay it or infer that the process actually died.
            continue
        if len(journal) >= MAX_WITNESSES:
            state["discovery_limited"] = True
            break
        if not _same(_process(anchor.pid), anchor):
            raise CancelError("run_cancel_worker_unproven")
        if not _same(_process(process.pid), process):
            state["discovery_limited"] = True
            continue
        entry = {"identity_sha256": identity, "outcome": "pending", "exit_observed": False}
        journal.append(entry)
        state["lease_must_retain"] = True
        state["phase"] = "instance_kill_pending"
        save()
        try:
            _send(descriptor, signal.SIGKILL)
        except OSError:
            entry["outcome"] = "refused"
        else:
            entry["outcome"] = "accepted"
            record["cancel_escalated"] = True
        state["kill_accepted"] = sum(item["outcome"] == "accepted" for item in journal)
        state["phase"] = "witnessed_instances_only"
        save()
    for process, descriptor in witnesses:
        entry = next(
            (item for item in journal if item["identity_sha256"] == _identity(process)), None
        )
        if entry is not None and entry["outcome"] == "accepted":
            entry["exit_observed"] = _exited(descriptor)
    state["lease_must_retain"] = bool(
        state["discovery_limited"] or any(item.get("exit_observed") is not True for item in journal)
    )


def cancel_run(
    record: dict[str, Any],
    *,
    acknowledged: bool,
    save: Callable[[], None],
) -> None:
    """Control only an acknowledged live operation; never set its terminal state.

    Caller holds the existing claim lock. Each delivery intent is durable before
    its syscall. Catchable failures close held pidfds; no process is ever paused.
    Returned scope is always unknown for unseen/escaped descendants.
    """
    if record.get("kind") != "run.start":
        return
    try:
        state = _state(record)
        if not acknowledged:
            raise CancelError("run_cancel_worker_ack_required")
        with contextlib.ExitStack() as stack:
            anchor, descriptor = _anchor(record, stack)
            if not record.get("cancel_delivered"):
                state["phase"] = "worker_term_pending"
                save()
                try:
                    _send(descriptor, signal.SIGTERM)
                except OSError:
                    state["phase"] = "run_cancel_term_unproven"
                else:
                    record["cancel_delivered"] = True
                    state["term_monotonic_ns"] = time.monotonic_ns()
                    state["phase"] = "cooperative_wait"
                save()
                return
            delivered_at = state.get("term_monotonic_ns")
            if type(delivered_at) is not int:
                raise CancelError("run_cancel_term_time_unproven")
            elapsed = time.monotonic_ns() - delivered_at
            if state["boot_sha256"] != _boot() or elapsed < 0:
                raise CancelError("run_cancel_clock_unproven")
            if elapsed < GRACE_NS:
                state["phase"] = "cooperative_wait"
                save()
                return
            _force(record, state, anchor, stack, save)
            save()
    except (CancelError, AttributeError) as error:
        if isinstance(record.get("run_cancel"), dict):
            record["run_cancel"]["lease_must_retain"] = True
            record["run_cancel"]["discovery_limited"] = True
            record["run_cancel"]["phase"] = (
                str(error) if isinstance(error, CancelError) else "run_cancel_platform_unavailable"
            )
            save()
    except OSError:
        # Persistence failures must propagate when inside save(), before any
        # later signal. Proc/open failures are handled at their owned call sites.
        raise


_PUBLIC_PHASES = frozenset(
    {
        "requested",
        "worker_term_pending",
        "cooperative_wait",
        "instance_kill_pending",
        "witnessed_instances_only",
        "run_cancel_term_unproven",
        "run_cancel_worker_unproven",
        "run_cancel_session_unproven",
        "run_cancel_child_binding_unproven",
        "run_cancel_clock_unproven",
        "run_cancel_term_time_unproven",
        "run_cancel_worker_ack_required",
        "run_cancel_state_unavailable",
        "run_cancel_platform_unavailable",
        "run_cancel_discovery_limit",
        "run_cancel_pidfd_unavailable",
    }
)


def public_summary(value: Any) -> dict[str, Any]:
    """Project only finite controller facts; no pid, paths, nonce or raw metadata."""
    source = value if isinstance(value, dict) else {}
    witnesses = source.get("witnesses", [])
    witnesses = witnesses if isinstance(witnesses, list) and len(witnesses) <= MAX_WITNESSES else []
    return {
        "phase": source.get("phase")
        if isinstance(source.get("phase"), str) and source["phase"] in _PUBLIC_PHASES
        else "unknown",
        "cleanup_scope": "unknown_descendants",
        "witnessed_instances": len(witnesses),
        "kill_accepted": sum(
            isinstance(item, dict) and item.get("outcome") == "accepted" for item in witnesses
        ),
        "instance_exit_observed": sum(
            isinstance(item, dict) and item.get("exit_observed") is True for item in witnesses
        ),
        "discovery_limited": source.get("discovery_limited") is True,
        "lease_must_retain": source.get("lease_must_retain") is True,
        "signal_acceptance_is_exit_proof": False,
    }
