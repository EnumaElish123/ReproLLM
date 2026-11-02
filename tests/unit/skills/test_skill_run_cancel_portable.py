"""Public cancellation types require no process observation or signal support."""

from __future__ import annotations

import contextlib
import copy
import importlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"))


@pytest.mark.parametrize(
    "value", [None, {}, [], {"phase": []}, {"phase": {"bad": "value"}}, {"phase": 9}]
)
def test_public_projection_refuses_untyped_phase(value):
    result = importlib.import_module("skill_run_cancel").public_summary(value)
    assert result["phase"] == "unknown"


@pytest.fixture
def snapshot(monkeypatch):
    module = importlib.import_module("skill_run_cancel")
    anchor = module.Process(100, 1, 100, 10, "synthetic-namespace", "S")
    processes = {anchor.pid: anchor}
    opened, closed = [], []

    def open_handle(pid):
        handle = object()
        opened.append((pid, handle))
        return handle

    def forbidden(*args, **kwargs):
        pytest.fail("A witness snapshot must not signal or read real process identity")

    monkeypatch.setattr(module, "_pids", lambda: iter(processes))
    monkeypatch.setattr(module, "_process", processes.get)
    monkeypatch.setattr(module, "_open", open_handle)
    monkeypatch.setattr(module, "_close", closed.append)
    monkeypatch.setattr(module, "_send", forbidden)
    monkeypatch.setattr(module, "_identity", forbidden)
    monkeypatch.setattr(module, "_boot", forbidden)
    return SimpleNamespace(
        module=module, anchor=anchor, processes=processes, opened=opened, closed=closed
    )


def test_snapshot_orders_live_witnesses_deepest_first_and_keeps_handles_until_exit(snapshot):
    m, anchor = snapshot.module, snapshot.anchor
    child = m.Process(200, 100, 100, 20, anchor.namespace, "S")
    grandchild = m.Process(400, 200, 100, 40, anchor.namespace, "R")
    sibling = m.Process(150, 100, 100, 15, anchor.namespace, "S")
    snapshot.processes.update(
        {
            200: child,
            400: grandchild,
            150: sibling,
            250: replace(child, pid=250, state="Z"),
            260: replace(child, pid=260, state="X"),
            270: replace(child, pid=270, state="x"),
            500: replace(child, pid=500, parent=1, session=500),
            600: replace(child, pid=600, parent=1, namespace="foreign-namespace"),
            700: None,
        }
    )
    with contextlib.ExitStack() as stack:
        witnesses, limited = m._witnesses(anchor, stack)
        assert [process.pid for process, _ in witnesses] == [400, 150, 200]
        assert not limited
        assert [pid for pid, _ in snapshot.opened] == [200, 400, 150]
        assert snapshot.closed == []
    assert snapshot.closed == [handle for _, handle in reversed(snapshot.opened)]


@pytest.mark.parametrize("change", ["generation", "session", "namespace", "dead", "missing"])
def test_changed_anchor_aborts_snapshot_and_closes_already_retained_handles(
    snapshot, monkeypatch, change
):
    m, anchor = snapshot.module, snapshot.anchor
    snapshot.processes.update(
        {
            200: m.Process(200, 100, 100, 20, anchor.namespace, "S"),
            300: m.Process(300, 100, 100, 30, anchor.namespace, "S"),
        }
    )
    replacement = {
        "generation": replace(anchor, start=anchor.start + 1),
        "session": replace(anchor, session=999),
        "namespace": replace(anchor, namespace="replacement-namespace"),
        "dead": replace(anchor, state="Z"),
        "missing": None,
    }[change]
    anchor_reads = 0

    def read_process(pid):
        nonlocal anchor_reads
        if pid == anchor.pid:
            anchor_reads += 1
            return anchor if anchor_reads == 1 else replacement
        return snapshot.processes.get(pid)

    monkeypatch.setattr(m, "_process", read_process)
    with (
        pytest.raises(m.CancelError, match="run_cancel_worker_unproven"),
        contextlib.ExitStack() as stack,
    ):
        m._witnesses(anchor, stack)
    assert [pid for pid, _ in snapshot.opened] == [200]
    assert snapshot.closed == [snapshot.opened[0][1]]


@pytest.mark.parametrize("failure", ["open", "reused", "missing", "dead", "session", "namespace"])
def test_unproven_candidate_is_omitted_without_losing_later_witnesses(
    snapshot, monkeypatch, failure
):
    m, anchor = snapshot.module, snapshot.anchor
    first = m.Process(200, 100, 100, 20, anchor.namespace, "S")
    second = m.Process(300, 100, 100, 30, anchor.namespace, "S")
    snapshot.processes.update({first.pid: first, second.pid: second})
    original_open = m._open

    def changed_at_open(pid):
        if pid != first.pid:
            return original_open(pid)
        if failure == "open":
            raise OSError("synthetic unavailable handle")
        handle = original_open(pid)
        snapshot.processes[pid] = {
            "reused": replace(first, start=first.start + 1),
            "missing": None,
            "dead": replace(first, state="Z"),
            "session": replace(first, session=999),
            "namespace": replace(first, namespace="replacement-namespace"),
        }[failure]
        return handle

    monkeypatch.setattr(m, "_open", changed_at_open)
    with contextlib.ExitStack() as stack:
        witnesses, limited = m._witnesses(anchor, stack)
        assert [process for process, _ in witnesses] == [second]
        assert limited and snapshot.closed == []
    assert snapshot.closed == [handle for _, handle in reversed(snapshot.opened)]
    assert len(snapshot.closed) == (1 if failure == "open" else 2)


@pytest.mark.parametrize("escape", ["session", "namespace"])
def test_observed_escaped_child_keeps_scope_unknown_without_opening_it(snapshot, escape):
    m, anchor = snapshot.module, snapshot.anchor
    child = m.Process(200, 100, 100, 20, anchor.namespace, "S")
    snapshot.processes[child.pid] = (
        replace(child, session=200) if escape == "session" else replace(child, namespace="foreign")
    )
    with contextlib.ExitStack() as stack:
        witnesses, limited = m._witnesses(anchor, stack)
        assert witnesses == [] and limited
    assert snapshot.opened == snapshot.closed == []


@pytest.mark.parametrize("extra", [0, 1])
def test_witness_limit_retains_exact_bound_and_refuses_additional_handles(snapshot, extra):
    m, anchor = snapshot.module, snapshot.anchor
    for index in range(m.MAX_WITNESSES + extra):
        pid = 1000 + index
        snapshot.processes[pid] = m.Process(pid, 100, 100, index, anchor.namespace, "S")
    with contextlib.ExitStack() as stack:
        witnesses, limited = m._witnesses(anchor, stack)
        assert len(witnesses) == len(snapshot.opened) == m.MAX_WITNESSES
        assert limited is bool(extra)
        assert snapshot.closed == []
    assert snapshot.closed == [handle for _, handle in reversed(snapshot.opened)]


def test_enumeration_oserror_retains_partial_witnesses_and_closes_their_handles(
    snapshot, monkeypatch
):
    m, anchor = snapshot.module, snapshot.anchor
    child = m.Process(200, 100, 100, 20, anchor.namespace, "S")
    snapshot.processes[child.pid] = child

    def interrupted_enumeration():
        yield child.pid
        raise OSError("synthetic process enumeration failure")

    monkeypatch.setattr(m, "_pids", interrupted_enumeration)
    with contextlib.ExitStack() as stack:
        witnesses, limited = m._witnesses(anchor, stack)
        assert [process for process, _ in witnesses] == [child]
        assert limited and snapshot.closed == []
    assert snapshot.closed == [snapshot.opened[0][1]]


def test_discovery_budget_error_propagates_after_closing_retained_handles(snapshot, monkeypatch):
    m, anchor = snapshot.module, snapshot.anchor
    child = m.Process(200, 100, 100, 20, anchor.namespace, "S")
    snapshot.processes[child.pid] = child

    def limited_enumeration():
        yield child.pid
        raise m.CancelError("run_cancel_discovery_limit")

    monkeypatch.setattr(m, "_pids", limited_enumeration)
    with (
        pytest.raises(m.CancelError, match="run_cancel_discovery_limit"),
        contextlib.ExitStack() as stack,
    ):
        m._witnesses(anchor, stack)
    assert snapshot.closed == [snapshot.opened[0][1]]


@pytest.mark.parametrize("length,expected", [(1, 1), (63, 63), (64, 64), (65, 64)])
def test_witness_depth_has_a_finite_ancestry_bound(length, expected):
    m = importlib.import_module("skill_run_cancel")
    anchor = m.Process(100, 1, 100, 1, "synthetic", "S")
    processes = {
        pid: m.Process(pid, 100 if pid == 1 else pid - 1, 100, pid, "synthetic", "S")
        for pid in range(1, length + 1)
    }
    assert m._depth(processes[length], processes, anchor) == expected


@pytest.mark.parametrize("parent,expected", [(1, 1), (2, 2), (999, 1)])
def test_witness_depth_terminates_for_cycles_and_missing_parents(parent, expected):
    m = importlib.import_module("skill_run_cancel")
    anchor = m.Process(100, 1, 100, 1, "synthetic", "S")
    first = m.Process(1, parent, 100, 1, "synthetic", "S")
    second = m.Process(2, 1, 100, 2, "synthetic", "S")
    assert m._depth(first, {1: first, 2: second}, anchor) == expected


@pytest.fixture
def journal(monkeypatch):
    module = importlib.import_module("skill_run_cancel")
    calls = []

    def boot():
        calls.append("boot")
        return "a" * 64

    def monotonic_ns():
        calls.append("clock")
        return 100_000_000_000

    monkeypatch.setattr(module, "_boot", boot)
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic_ns=monotonic_ns))
    return module, calls


def saved_state():
    return {
        "schema_version": 1,
        "requested_monotonic_ns": 10,
        "boot_sha256": "b" * 64,
        "witnesses": [],
    }


@pytest.mark.parametrize("present", [False, True])
def test_new_cancel_state_is_bound_once_to_the_supplied_record(journal, present):
    m, calls = journal
    record = {"run_cancel": None} if present else {}
    current = m._state(record)
    assert current is record["run_cancel"]
    assert current == {
        "schema_version": 1,
        "boot_sha256": "a" * 64,
        "requested_monotonic_ns": 100_000_000_000,
        "phase": "requested",
        "cleanup_scope": "unknown_descendants",
        "kill_accepted": 0,
        "lease_must_retain": False,
        "witnesses": [],
    }
    assert m._state(record) is current and calls == ["boot", "clock"]


def test_valid_saved_cancel_state_is_reused_without_refreshing_boot_or_clock(journal):
    m, calls = journal
    current = saved_state()
    current["witnesses"] = [
        {"identity_sha256": str(index), "outcome": outcome}
        for index, outcome in enumerate(["pending", "accepted", "refused"])
    ]
    before = copy.deepcopy(current)
    assert m._state({"run_cancel": current}) is current
    assert current == before and calls == []


@pytest.mark.parametrize("current", [[], 0, "synthetic malformed journal"])
def test_non_mapping_saved_cancel_state_is_refused(journal, current):
    m, calls = journal
    with pytest.raises(m.CancelError, match="run_cancel_state_unavailable"):
        m._state({"run_cancel": current})
    assert calls == []


@pytest.mark.parametrize(
    "field,value,missing",
    [
        ("schema_version", 2, False),
        ("schema_version", None, True),
        ("requested_monotonic_ns", True, False),
        ("requested_monotonic_ns", False, False),
        ("requested_monotonic_ns", "10", False),
        ("requested_monotonic_ns", 10.0, False),
        ("requested_monotonic_ns", None, True),
        ("boot_sha256", 7, False),
        ("boot_sha256", None, True),
        ("witnesses", {}, False),
        ("witnesses", None, True),
    ],
)
def test_malformed_saved_state_fields_are_not_replaced_or_silently_accepted(
    journal, field, value, missing
):
    m, calls = journal
    current = saved_state()
    if missing:
        del current[field]
    else:
        current[field] = value
    before = copy.deepcopy(current)
    record = {"run_cancel": current}
    with pytest.raises(m.CancelError, match="run_cancel_state_unavailable"):
        m._state(record)
    assert record["run_cancel"] is current and current == before and calls == []


@pytest.mark.parametrize(
    "entry",
    [
        None,
        {},
        {"identity_sha256": 7, "outcome": "accepted"},
        {"identity_sha256": "synthetic"},
        {"identity_sha256": "synthetic", "outcome": "invalid"},
        {"identity_sha256": "synthetic", "outcome": None},
        {"identity_sha256": "synthetic", "outcome": 7},
    ],
)
def test_unproven_saved_witness_entries_are_refused_without_reinitializing(journal, entry):
    m, calls = journal
    current = saved_state()
    current["witnesses"] = [entry]
    before = copy.deepcopy(current)
    with pytest.raises(m.CancelError, match="run_cancel_state_unavailable"):
        m._state({"run_cancel": current})
    assert current == before and calls == []


@pytest.mark.parametrize("extra", [0, 1])
def test_saved_witness_limit_is_validated_without_truncating_the_journal(journal, extra):
    m, calls = journal
    current = saved_state()
    current["witnesses"] = [
        {"identity_sha256": str(index), "outcome": "pending"}
        for index in range(m.MAX_WITNESSES + extra)
    ]
    before = copy.deepcopy(current)
    if extra:
        with pytest.raises(m.CancelError, match="run_cancel_state_unavailable"):
            m._state({"run_cancel": current})
    else:
        assert m._state({"run_cancel": current}) is current
    assert current == before and calls == []


def test_public_witness_projection_is_finite_and_never_turns_signal_acceptance_into_exit():
    m = importlib.import_module("skill_run_cancel")
    current = {
        "phase": "witnessed_instances_only",
        "witnesses": [
            {"outcome": "accepted", "exit_observed": False, "pid": 100, "raw": "private-first"},
            {"outcome": "accepted", "exit_observed": True, "path": "private-second"},
            {"outcome": "refused", "exit_observed": True, "identity_sha256": "private-third"},
        ],
        "discovery_limited": 1,
        "lease_must_retain": True,
        "raw": "private-top-level",
    }
    assert m.public_summary(current) == {
        "phase": "witnessed_instances_only",
        "cleanup_scope": "unknown_descendants",
        "witnessed_instances": 3,
        "kill_accepted": 2,
        "instance_exit_observed": 2,
        "discovery_limited": False,
        "lease_must_retain": True,
        "signal_acceptance_is_exit_proof": False,
    }


def test_public_counts_require_typed_witness_fields_and_strict_booleans():
    m = importlib.import_module("skill_run_cancel")
    result = m.public_summary(
        {
            "witnesses": [
                None,
                7,
                {"outcome": "accepted", "exit_observed": 1},
                {"outcome": "pending", "exit_observed": True},
            ],
            "lease_must_retain": 1,
        }
    )
    assert result["witnessed_instances"] == 4
    assert result["kill_accepted"] == result["instance_exit_observed"] == 1
    assert result["lease_must_retain"] is False
    assert result["signal_acceptance_is_exit_proof"] is False


@pytest.mark.parametrize("kind", ["not_list", "over_limit"])
def test_public_projection_does_not_present_an_invalid_witness_group_as_partial_evidence(kind):
    m = importlib.import_module("skill_run_cancel")
    witnesses = {} if kind == "not_list" else [{"outcome": "accepted"}] * (m.MAX_WITNESSES + 1)
    result = m.public_summary({"witnesses": witnesses})
    assert result["witnessed_instances"] == result["kill_accepted"] == 0
    assert result["instance_exit_observed"] == 0
    assert result["signal_acceptance_is_exit_proof"] is False
