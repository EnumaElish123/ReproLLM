"""SK19 cancellation: proven pidfds, honest scope, and no recorder force kill."""

from __future__ import annotations

import importlib
import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"))
pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux pidfd cancellation"),
]


@pytest.fixture
def control(monkeypatch):
    mod = importlib.import_module("skill_run_cancel")
    anchor = mod.Process(10001, 1, 10001, 40, "ns", "S")
    child = mod.Process(10002, 10001, 10001, 41, "ns", "S")
    grandchild = mod.Process(10003, 10002, 10001, 42, "ns", "S")
    foreign = mod.Process(20001, 1, 20001, 44, "ns", "S")
    procs = {p.pid: p for p in [anchor, child, grandchild, foreign]}
    sent, closed, writes = [], [], []
    clock = [100_000_000_000]
    monkeypatch.setattr(mod, "_boot", lambda: "b" * 64)
    monkeypatch.setattr(mod.time, "monotonic_ns", lambda: clock[0])
    monkeypatch.setattr(mod, "_process", lambda pid: procs.get(pid))
    monkeypatch.setattr(mod, "_pids", lambda: iter(procs))
    monkeypatch.setattr(mod, "_open", lambda pid: pid + 30000)
    monkeypatch.setattr(mod, "_close", closed.append)
    monkeypatch.setattr(mod, "_send", lambda fd, number: sent.append((fd - 30000, number)))
    record = {
        "kind": "run.start",
        "worker_pid": anchor.pid,
        "worker_identity": mod._identity(anchor),
        "native_run_id": "20261031T000000Z-abcdef",
        "cancel_delivered": False,
        "cancel_escalated": False,
    }
    return mod, record, procs, clock, sent, closed, writes


def invoke(c, ack=True):
    mod, record, _, _, _, _, writes = c
    mod.cancel_run(
        record, acknowledged=ack, save=lambda: writes.append(record["run_cancel"]["phase"])
    )


def test_first_cancel_is_term_only_and_intent_precedes_signal(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    assert w[0] == "worker_term_pending"
    assert r["cancel_delivered"] and not r["cancel_escalated"]
    assert r["run_cancel"]["cleanup_scope"] == "unknown_descendants"
    assert c == [40001]


def test_ack_or_generation_failure_signals_nothing(control):
    invoke(control, False)
    assert control[4] == []
    control[1]["worker_identity"] = "e" * 64
    invoke(control)
    assert control[4] == []
    assert not control[1]["cancel_delivered"]


def test_only_live_original_new_session_anchor_authorizes_force(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    p[10001] = m.Process(10001, 1, 30000, 40, "ns", "S")
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    assert not r["cancel_escalated"]


def test_force_uses_retained_descendant_fds_deepest_first_never_recorder(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    invoke(control)
    assert s == [(10001, signal.SIGTERM), (10003, signal.SIGKILL), (10002, signal.SIGKILL)]
    assert r["cancel_escalated"]
    assert r["run_cancel"]["kill_accepted"] == 2
    assert r["run_cancel"]["cleanup_scope"] == "unknown_descendants"
    assert "state" not in r and "child_exit_code" not in r
    assert sorted(c) == [40001, 40001, 40002, 40003]


def test_clock_jump_and_boot_change_never_enable_force(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] -= 6_000_000_000
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    t[0] += 30_000_000_000
    r["run_cancel"]["boot_sha256"] = "c" * 64
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]


def test_lost_anchor_does_not_discover_or_signal_old_session(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    del p[10001]
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    assert not r["cancel_escalated"]


def test_no_run_binding_refuses_force_but_preserves_term_delivery(control):
    m, r, p, t, s, c, w = control
    r["native_run_id"] = None
    invoke(control)
    t[0] += 6_000_000_000
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    assert r["cancel_delivered"]


def test_pid_reuse_between_open_and_recheck_never_targets_replacement(control, monkeypatch):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000

    def open_pid(pid):
        if pid == 10002:
            p[pid] = m.Process(pid, 1, 10001, 999, "ns", "S")
        return pid + 30000

    monkeypatch.setattr(m, "_open", open_pid)
    invoke(control)
    assert (10002, signal.SIGKILL) not in s
    assert (10003, signal.SIGKILL) in s


def test_permission_failure_does_not_erase_prior_accepted_delivery(control, monkeypatch):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    monkeypatch.setattr(m, "_send", lambda *a: (_ for _ in ()).throw(PermissionError()))
    invoke(control)
    assert r["cancel_delivered"] and not r["cancel_escalated"]
    assert r["run_cancel"]["kill_accepted"] == 0


def test_foreign_namespace_or_session_never_signalled(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    p[10003] = m.Process(10003, 10002, 10001, 42, "other", "S")
    invoke(control)
    assert s == [(10001, signal.SIGTERM), (10002, signal.SIGKILL)]


def test_save_failure_before_signal_delivers_nothing(control):
    m, r, p, t, s, c, w = control
    with pytest.raises(OSError):
        m.cancel_run(r, acknowledged=True, save=lambda: (_ for _ in ()).throw(OSError()))
    assert s == []


def test_enumeration_failure_and_limit_keep_unknown_scope(control, monkeypatch):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    monkeypatch.setattr(m, "_pids", lambda: (_ for _ in ()).throw(OSError()))
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    assert r["run_cancel"]["cleanup_scope"] == "unknown_descendants"


def test_zombie_witness_is_not_a_live_signal_target(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    p[10003] = m.Process(10003, 10002, 10001, 42, "ns", "Z")
    invoke(control)
    assert s == [(10001, signal.SIGTERM), (10002, signal.SIGKILL)]


def test_already_exited_or_wrong_kind_does_not_invent_completion(control):
    m, r, p, t, s, c, w = control
    r["kind"] = "lock"
    invoke(control)
    assert s == []
    assert "state" not in r


def test_grace_begins_after_term_delivery_not_before_slow_persistence(control):
    m, r, p, t, s, c, w = control

    def save():
        if r["run_cancel"]["phase"] == "worker_term_pending":
            t[0] += 6_000_000_000

    m.cancel_run(r, acknowledged=True, save=save)
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]


def test_unacknowledged_term_timestamp_never_enables_force(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    del r["run_cancel"]["term_monotonic_ns"]
    t[0] += 6_000_000_000
    invoke(control)
    assert s == [(10001, signal.SIGTERM)]
    assert r["run_cancel"]["lease_must_retain"] is True


def test_public_cancel_projection_is_finite_and_has_no_machine_fields(control):
    m, r, p, t, s, c, w = control
    invoke(control)
    result = m.public_summary({**r["run_cancel"], "raw": "/host/private", "phase": "secret-value"})
    assert result["phase"] == "unknown"
    assert "raw" not in result and "witnesses" not in result
    assert result["cleanup_scope"] == "unknown_descendants"
    assert result["signal_acceptance_is_exit_proof"] is False


def test_generation_matches_existing_worker_identity_contract(control):
    import os

    import skill_operations

    module = control[0]
    # Restore the real metadata reader only for this current-process observation.
    import importlib.util

    spec = importlib.util.spec_from_file_location("cancel_metadata_probe", module.__file__)
    fresh = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fresh
    spec.loader.exec_module(fresh)
    process = fresh._process(os.getpid())
    assert process is not None
    assert fresh._identity(process) == skill_operations._process_identity(os.getpid())


@pytest.mark.parametrize("session,namespace", [(30000, "ns"), (10001, "other")])
def test_observed_escaped_direct_child_retains_lease_without_signalling(
    control, session, namespace
):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    p[10002] = m.Process(10002, 10001, session, 41, namespace, "S")
    invoke(control)
    assert (10002, signal.SIGKILL) not in s
    assert r["cancel_delivered"] is True
    assert r["run_cancel"]["discovery_limited"] is True
    assert r["run_cancel"]["lease_must_retain"] is True


def test_observed_escaped_grandchild_before_parent_enumeration_is_a_gap(control, monkeypatch):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    p[10003] = m.Process(10003, 10002, 30000, 42, "ns", "S")
    monkeypatch.setattr(m, "_pids", lambda: iter([10003, 20001, 10002, 10001]))
    invoke(control)
    assert s == [(10001, signal.SIGTERM), (10002, signal.SIGKILL)]
    assert r["run_cancel"]["discovery_limited"] is True
    assert r["run_cancel"]["lease_must_retain"] is True


def test_known_escape_remains_unknown_after_parent_exit_and_repeated_cancel(control, monkeypatch):
    m, r, p, t, s, c, w = control
    monkeypatch.setattr(m, "_exited", lambda fd: True)
    p[10003] = m.Process(10003, 10002, 30000, 42, "ns", "S")
    invoke(control)
    t[0] += 6_000_000_000
    invoke(control)
    assert r["run_cancel"]["discovery_limited"] is True
    assert r["run_cancel"]["lease_must_retain"] is True
    before = list(s)
    del p[10002]
    p[10003] = m.Process(10003, 1, 30000, 42, "ns", "S")
    invoke(control)
    assert s == before
    assert r["run_cancel"]["discovery_limited"] is True
    assert r["run_cancel"]["lease_must_retain"] is True
    assert r["run_cancel"]["cleanup_scope"] == "unknown_descendants"
    assert "state" not in r and "child_exit_code" not in r


def test_discovery_gap_cannot_be_cleared_by_later_successful_scan(control, monkeypatch):
    m, r, p, t, s, c, w = control
    invoke(control)
    t[0] += 6_000_000_000
    original = m._pids

    def unavailable():
        raise m.CancelError("run_cancel_discovery_limit")

    monkeypatch.setattr(m, "_pids", unavailable)
    invoke(control)
    assert r["run_cancel"]["lease_must_retain"] is True
    monkeypatch.setattr(m, "_pids", original)
    monkeypatch.setattr(m, "_exited", lambda fd: True)
    invoke(control)
    assert r["run_cancel"]["discovery_limited"] is True
    assert r["run_cancel"]["lease_must_retain"] is True


@pytest.mark.parametrize("platform", ["win32", "darwin"])
@pytest.mark.parametrize("primitive", ["_open", "_send", "_exited"])
def test_unsupported_platform_never_touches_linux_primitive(
    control, monkeypatch, platform, primitive
):
    from types import SimpleNamespace

    m = control[0]
    monkeypatch.setattr(m, "sys", SimpleNamespace(platform=platform), raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported platform touched Linux syscall")

    monkeypatch.setattr(m.os, "pidfd_open", forbidden)
    monkeypatch.setattr(m.signal, "pidfd_send_signal", forbidden)
    monkeypatch.setattr(m.select, "poll", forbidden)
    # The ordinary fixture stubs internal primitive functions; use a fresh module
    # so this assertion exercises their real platform dispatch, never a syscall.
    import importlib.util

    spec = importlib.util.spec_from_file_location("cancel_platform_probe", m.__file__)
    fresh = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fresh
    spec.loader.exec_module(fresh)
    monkeypatch.setattr(fresh, "sys", SimpleNamespace(platform=platform), raising=False)
    args = (99, 15) if primitive == "_send" else (99,)
    with pytest.raises(fresh.CancelError, match="run_cancel_platform_unavailable"):
        getattr(fresh, primitive)(*args)
