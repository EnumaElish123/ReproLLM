"""SK15: long native lock work is owned, replayable, private, and bounded."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_operations as operations  # noqa: E402
from skill_request import Grants, Reply, Request  # noqa: E402

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned worker lifecycle"),
]


def request(root: Path, operation_id: str | None = None, **options: Any) -> Request:
    return Request(
        "lock",
        str(root),
        {
            "offline": True,
            "hash_large_files": True,
            **options,
            **({"operation_id": operation_id} if operation_id is not None else {}),
        },
        Grants(write=True),
    )


class Lease:
    def __init__(self, environment: Path) -> None:
        self.environment = environment
        self.claim = {"schema_version": 1, "environment": "a" * 32, "lease_id": "b" * 32}
        self.transferred = False
        self.reclaimed = False
        self.cleanup_failed = False

    def transfer(self) -> None:
        self.transferred = True

    def reclaim(self) -> None:
        self.transferred = False
        self.reclaimed = True


class ClosedInput(io.BytesIO):
    def close(self) -> None:
        self.saved = self.getvalue()
        super().close()


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    root = tmp_path / "project"
    root.mkdir()
    home = tmp_path / "home"
    environment = tmp_path / "tool"
    (environment / "bin").mkdir(parents=True)
    lease = Lease(environment)
    launches = []

    @contextlib.contextmanager
    def lease_factory(manager: Any, name: str):
        assert name == "a" * 32
        yield lease

    def popen(argv: list[str], **kwargs: Any) -> Any:
        launches.append((argv, kwargs))
        return type("Worker", (), {"pid": 987654, "stdin": ClosedInput()})()

    monkeypatch.setattr(operations.subprocess, "Popen", popen)
    monkeypatch.setattr(operations, "_process_identity", lambda pid: "c" * 64)

    def send_input(stream: Any, raw: bytes) -> None:
        stream.write(len(raw).to_bytes(4, "big") + raw)
        stream.close()

    # Byte framing is asserted below. OS pipe backpressure/deadlines have actual
    # pipe/owned-process regressions in test_skill_operations_io.py.
    monkeypatch.setattr(operations, "_send_input", send_input)
    return {
        "root": root,
        "home": home,
        "lease": lease,
        "launches": launches,
        "lease_factory": lease_factory,
    }


def start(setup: dict[str, Any], req: Request) -> Reply:
    return operations.start(
        req,
        home=setup["home"],
        root=setup["root"],
        identity="d" * 64,
        manager=object(),
        environment_name="a" * 32,
        lease_factory=setup["lease_factory"],
    )


def operation_id(reply: Reply) -> str:
    assert reply.invocation == "handled_result", reply.as_dict()
    return reply.data["operation"]["operation_id"]


def control(setup: dict[str, Any], action: str, token: str) -> Reply:
    result = operations.control(
        Request(
            action,
            str(setup["root"]),
            {"operation_id": token},
            Grants(write=action == "operation.cancel"),
        ),
        home=setup["home"],
        root=setup["root"],
    )
    assert result is not None
    return result


def record_path(setup: dict[str, Any], token: str) -> Path:
    return setup["home"] / "operations" / "claims" / token / "status.json"


def edit_record(setup: dict[str, Any], token: str, **updates: Any) -> dict[str, Any]:
    path = record_path(setup, token)
    record = json.loads(path.read_bytes())
    record.update(updates)
    path.write_text(json.dumps(record), encoding="utf-8")
    if updates.get("state") in {"RUNNING", "FINALIZING"}:
        ack = {
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
        (path.parent / "worker.json").write_text(json.dumps(ack), encoding="utf-8")
        (path.parent / "worker.json").chmod(0o600)
    return record


def test_prepare_runs_no_worker_or_hash_and_replay_starts_once(setup):
    prepared = start(setup, request(setup["root"]))
    token = operation_id(prepared)
    assert prepared.data["operation"]["state"] == "PREPARED"
    assert prepared.data["operation"]["execution_started"] is False
    assert setup["launches"] == []
    assert (
        operations.control(request(setup["root"], token), home=setup["home"], root=setup["root"])
        is None
    )
    launched = start(setup, request(setup["root"], token))
    assert operation_id(launched) == token and len(setup["launches"]) == 1
    replay = operations.control(
        request(setup["root"], token), home=setup["home"], root=setup["root"]
    )
    assert replay is not None and operation_id(replay) == token
    assert len(setup["launches"]) == 1 and setup["lease"].transferred


def test_long_preview_needs_no_project_write_permission_but_apply_does(setup):
    preview = dataclasses.replace(request(setup["root"], preview=True), grants=Grants(write=False))
    token = operation_id(start(setup, preview))
    launched = start(
        setup, dataclasses.replace(preview, options={**preview.options, "operation_id": token})
    )
    assert launched.invocation == "handled_result" and len(setup["launches"]) == 1
    denied = start(setup, dataclasses.replace(request(setup["root"]), grants=Grants(write=False)))
    assert denied.invocation == "blocked" and denied.needs_authorization
    assert len(setup["launches"]) == 1


def test_direct_cancel_without_authorization_cannot_change_claim_or_signal(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))
    before = record_path(setup, token).read_bytes()
    monkeypatch.setattr(
        operations, "_signal_owned", lambda *a: pytest.fail("No cancellation approval")
    )
    denied = operations.control(
        Request("operation.cancel", str(setup["root"]), {"operation_id": token}),
        home=setup["home"],
        root=setup["root"],
    )
    assert denied is not None and denied.invocation == "blocked" and denied.needs_authorization
    assert record_path(setup, token).read_bytes() == before


def test_starting_cancel_waits_for_worker_ack_instead_of_signalling(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    monkeypatch.setattr(
        operations, "_signal_owned", lambda *a: pytest.fail("Worker has not acknowledged ownership")
    )
    result = control(setup, "operation.cancel", token)
    assert result.data["operation"]["state"] == "STARTING"
    assert json.loads(record_path(setup, token).read_bytes())["cancel_requested"]


def test_foreign_nonce_never_signals_matching_pid(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    edit_record(setup, token, state="RUNNING")
    edit_record(setup, token, nonce_hash="e" * 64)
    monkeypatch.setattr(
        operations,
        "_signal_owned",
        lambda *a: pytest.fail("Nonce differs from immutable worker ACK"),
    )
    result = control(setup, "operation.cancel", token)
    assert result.invocation == "blocked"


def test_concurrent_start_claims_only_one_worker(setup):
    from concurrent.futures import ThreadPoolExecutor

    token = operation_id(start(setup, request(setup["root"])))
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: start(setup, request(setup["root"], token)), range(2))
        )
    assert all(result.invocation == "handled_result" for result in results)
    assert len(setup["launches"]) == 1


@pytest.mark.parametrize("action", ["operation.status", "operation.result", "operation.cancel"])
def test_unknown_id_never_creates_state_or_launches(setup, action):
    result = control(setup, action, "0" * 32)
    assert result.invocation == "blocked" and setup["launches"] == []
    assert not setup["home"].exists()


def test_unknown_start_id_cannot_create_an_operation(setup):
    result = start(setup, request(setup["root"], "0" * 32))
    assert result.invocation == "blocked" and setup["launches"] == []


@pytest.mark.parametrize("change", ["options", "project", "policy"])
def test_changed_intent_or_policy_refuses_start(setup, change):
    token = operation_id(start(setup, request(setup["root"])))
    req = request(setup["root"], token)
    if change == "options":
        req = dataclasses.replace(req, options={**req.options, "verify_api": True})
    elif change == "project":
        other = setup["root"].parent / "other"
        other.mkdir()
        setup["root"] = other
        req = request(other, token)
    else:
        edit_record(setup, token, policy_identity="e" * 64)
    assert start(setup, req).invocation == "blocked"
    assert setup["launches"] == []


def test_process_streams_are_devnull_and_environment_is_unmodified(setup, monkeypatch):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "selected-by-user")
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    argv, kw = setup["launches"][0]
    assert "-I" in argv and "-B" in argv
    assert kw["stdout"] == kw["stderr"] == operations.subprocess.DEVNULL
    assert kw.get("env") is None or kw["env"] == dict(os.environ)
    assert kw["start_new_session"] is True


def test_state_never_persists_raw_request_argv_root_or_environment(setup, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_OnlyPublicSyntheticCanary123456")
    req = request(setup["root"], label="synthetic raw request text")
    token = operation_id(start(setup, req))
    start(setup, dataclasses.replace(req, options={**req.options, "operation_id": token}))
    for file in (setup["home"] / "operations").rglob("*.json"):
        raw = file.read_text(encoding="utf-8")
        assert str(setup["root"]) not in raw
        assert (
            "synthetic raw request text" not in raw
            and "hf_OnlyPublicSyntheticCanary123456" not in raw
        )
        assert json.loads(raw)["schema_version"] == 1
        assert file.stat().st_mode & 0o077 == 0


def test_known_popen_failure_reclaims_lease_unknown_failure_preserves_it(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))

    def fail(*args, **kwargs):
        raise OSError("private startup path must never escape")

    monkeypatch.setattr(operations.subprocess, "Popen", fail)
    result = start(setup, request(setup["root"], token))
    assert result.data["operation"]["state"] == "FAILED"
    assert {"code": "operation_launch_failed"} in result.diagnostics
    assert setup["lease"].reclaimed and not setup["lease"].transferred
    assert "private startup path" not in json.dumps(result.as_dict())


@pytest.mark.parametrize("cleanup_failed", [False, True])
def test_known_launch_failure_only_clears_claim_after_proven_context_cleanup(
    setup, monkeypatch, cleanup_failed
):
    token = operation_id(start(setup, request(setup["root"])))

    @contextlib.contextmanager
    def lease_factory(manager, name):
        yield setup["lease"]
        assert setup["lease"].reclaimed
        setup["lease"].cleanup_failed = cleanup_failed

    def fail(*a, **kw):
        raise OSError("known launch failure")

    setup["lease_factory"] = lease_factory
    monkeypatch.setattr(operations.subprocess, "Popen", fail)
    result = start(setup, request(setup["root"], token))
    record = json.loads(record_path(setup, token).read_bytes())
    assert record["lease"] == (setup["lease"].claim if cleanup_failed else None)
    if cleanup_failed:
        assert {"code": "operation_lease_cleanup_failed"} in result.diagnostics


def test_ambiguous_launch_preserves_lease_and_never_restarts(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(operations.subprocess, "Popen", interrupted)
    with pytest.raises(KeyboardInterrupt):
        start(setup, request(setup["root"], token))
    assert setup["lease"].transferred and not setup["lease"].reclaimed
    result = control(setup, "operation.status", token)
    assert result.data["operation"]["state"] == "UNKNOWN"
    assert (
        operations.control(request(setup["root"], token), home=setup["home"], root=setup["root"])
        is not None
    )


def test_cancel_prepared_never_signals_or_allocates_work(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))
    monkeypatch.setattr(operations, "_signal_owned", lambda *a: pytest.fail("No process exists"))
    result = control(setup, "operation.cancel", token)
    assert result.data["operation"]["state"] == "CANCELLED" and setup["launches"] == []


@pytest.mark.parametrize("phase", ["STARTING", "RUNNING", "FINALIZING"])
def test_dead_or_reused_process_is_unknown_and_never_signalled(setup, monkeypatch, phase):
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    edit_record(setup, token, state=phase)
    monkeypatch.setattr(operations, "_process_identity", lambda pid: "f" * 64)
    monkeypatch.setattr(operations, "_signal_owned", lambda *a: pytest.fail("Foreign process"))
    result = control(setup, "operation.cancel", token)
    assert result.data["operation"]["state"] == "UNKNOWN"


def test_finalizing_cancel_records_request_without_interrupting_publication(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    edit_record(setup, token, state="FINALIZING")
    monkeypatch.setattr(
        operations, "_signal_owned", lambda *a: pytest.fail("Publication in progress")
    )
    result = control(setup, "operation.cancel", token)
    assert result.data["operation"]["state"] == "FINALIZING"
    assert result.data["operation"]["cancel_requested"]
    assert not result.data["operation"]["cancel_delivered"]
    assert json.loads(record_path(setup, token).read_bytes())["cancel_requested"]


def test_wrong_project_or_symlinked_state_refuses_query(setup):
    token = operation_id(start(setup, request(setup["root"])))
    other = setup["root"].parent / "other"
    other.mkdir()
    assert (
        operations.control(
            Request("operation.status", str(other), {"operation_id": token}),
            home=setup["home"],
            root=other,
        ).invocation
        == "blocked"
    )
    target = record_path(setup, token)
    original = target.read_bytes()
    target.unlink()
    outside = setup["root"].parent / "foreign.json"
    outside.write_bytes(original)
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("File symlinks unavailable")
    assert control(setup, "operation.status", token).invocation == "blocked"
    assert outside.read_bytes() == original


def test_expired_preparation_cannot_be_started(setup):
    token = operation_id(start(setup, request(setup["root"])))
    edit_record(
        setup,
        token,
        created_at=datetime.fromtimestamp(
            time.time() - operations.PREPARED_TTL_SECONDS - 1, timezone.utc
        )
        .isoformat()
        .replace("+00:00", "Z"),
    )
    assert start(setup, request(setup["root"], token)).invocation == "blocked"
    assert setup["launches"] == []


def test_unsupported_platform_never_starts_background_work(setup, monkeypatch):
    monkeypatch.setattr(operations.sys, "platform", "win32")
    result = start(setup, request(setup["root"]))
    assert result.invocation == "blocked" and setup["launches"] == []


def test_process_identity_is_stable_and_rejects_missing_process():
    if not sys.platform.startswith("linux"):
        pytest.skip("Linux process ownership proof")
    identity = operations._process_identity(os.getpid())
    assert identity is not None and len(identity) == 64
    assert operations._process_identity(os.getpid()) == identity
    assert operations._process_identity(2**30) is None


def test_result_is_complete_safe_original_reply_and_never_restarts(setup):
    token = operation_id(start(setup, request(setup["root"])))
    folder = record_path(setup, token).parent
    reply = Reply("lock", cli_exit_code=0, data={"value": "public" * 60000})
    raw = json.dumps(reply.as_dict()).encode()
    (folder / "result.json").write_bytes(raw)
    (folder / "result.json").chmod(0o600)
    edit_record(
        setup,
        token,
        state="COMPLETED",
        result_sha256=hashlib.sha256(raw).hexdigest(),
        ended_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    result = control(setup, "operation.result", token)
    assert result.cli_exit_code == 0 and result.data["result"] == reply.as_dict()
    assert setup["launches"] == []


@pytest.mark.parametrize("failure", ["chmod", "fsync"])
def test_owner_marker_failure_is_atomic_and_normally_recoverable(setup, monkeypatch, failure):
    original = getattr(operations.os, failure)

    def fail(*a, **kw):
        raise OSError("synthetic metadata failure")

    monkeypatch.setattr(operations.os, failure, fail)
    assert start(setup, request(setup["root"])).invocation == "blocked"
    assert not (setup["home"] / "operations/owner.json").exists()
    monkeypatch.setattr(operations.os, failure, original)
    assert operation_id(start(setup, request(setup["root"])))


@pytest.mark.parametrize("tamper", ["content", "symlink", "nonfinite", "schema"])
def test_tampered_result_never_becomes_success(setup, tamper):
    token = operation_id(start(setup, request(setup["root"])))
    target = record_path(setup, token).parent / "result.json"
    value = Reply("lock", cli_exit_code=0, data={"value": "public"}).as_dict()
    raw = json.dumps(value).encode()
    if tamper == "schema":
        value["schema_version"] = 9
        raw = json.dumps(value).encode()
    if tamper == "nonfinite":
        raw = raw.replace(b'"public"', b"1e9999")
    target.write_bytes(raw)
    target.chmod(0o600)
    edit_record(
        setup,
        token,
        state="COMPLETED",
        result_sha256=hashlib.sha256(raw).hexdigest(),
        ended_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    if tamper == "content":
        target.write_bytes(raw.replace(b"public", b"edited"))
    if tamper == "symlink":
        other = setup["root"] / "other.json"
        target.rename(other)
        try:
            target.symlink_to(other)
        except OSError:
            pytest.skip("File symlinks unavailable")
    result = control(setup, "operation.result", token)
    assert result.invocation == "blocked"
    assert setup["launches"] == []


def test_expired_result_does_not_allow_reexecution(setup):
    token = operation_id(start(setup, request(setup["root"])))
    edit_record(
        setup,
        token,
        state="COMPLETED",
        result_sha256="a" * 64,
        ended_at=datetime.fromtimestamp(
            time.time() - operations.RESULT_TTL_SECONDS - 1, timezone.utc
        )
        .isoformat()
        .replace("+00:00", "Z"),
    )
    result = control(setup, "operation.result", token)
    assert result.data["result_expired"] and not result.data["operation"]["result_available"]
    assert start(setup, request(setup["root"], token)).data["operation"]["state"] == "COMPLETED"
    assert setup["launches"] == []


def test_frozen_bundle_rejects_changes_before_launch(setup):
    token = operation_id(start(setup, request(setup["root"])))
    record = json.loads(record_path(setup, token).read_bytes())
    bundle = setup["home"] / "operations/bundles" / record["bundle_id"]
    helper = bundle / "scripts/skill_operations.py"
    helper.write_bytes(helper.read_bytes() + b"\n# changed trusted bundle\n")
    result = start(setup, request(setup["root"], token))
    assert result.invocation == "blocked" and setup["launches"] == []


def test_unknown_and_live_claims_survive_retention_and_quota(setup, monkeypatch):
    first = operation_id(start(setup, request(setup["root"])))
    edit_record(setup, first, state="UNKNOWN", created_at="2000-01-01T00:00:00Z")
    monkeypatch.setattr(operations, "MAX_OPERATIONS", 1)
    result = start(setup, request(setup["root"]))
    assert result.invocation == "blocked"
    assert record_path(setup, first).exists()


def test_expired_unstarted_claim_is_cleaned_without_reusing_id(setup):
    first = operation_id(start(setup, request(setup["root"])))
    edit_record(setup, first, created_at="2000-01-01T00:00:00Z")
    second = operation_id(start(setup, request(setup["root"])))
    assert second != first and not record_path(setup, first).exists()
    assert start(setup, request(setup["root"], first)).invocation == "blocked"
    assert setup["launches"] == []


def test_cancel_escalation_still_checks_ownership_and_never_claims_terminal(setup, monkeypatch):
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    edit_record(
        setup,
        token,
        state="RUNNING",
        cancel_requested=True,
        cancel_delivered=True,
        cancel_requested_at="2000-01-01T00:00:00Z",
    )
    signals = []
    monkeypatch.setattr(
        operations, "_signal_owned", lambda record, number: signals.append(number) or True
    )
    result = control(setup, "operation.cancel", token)
    assert signals == [signal.SIGKILL]
    assert result.data["operation"]["state"] == "RUNNING"


def worker_in_process(setup, monkeypatch, callback, *, release_success=True):
    import skill_runtime

    real_popen = operations.subprocess.Popen
    payloads = []

    def capture(argv, **kw):
        proc = real_popen(argv, **kw)
        payloads.append(proc.stdin)
        return proc

    monkeypatch.setattr(operations.subprocess, "Popen", capture)
    token = operation_id(start(setup, request(setup["root"])))
    start(setup, request(setup["root"], token))
    raw = payloads[0].saved
    edit_record(setup, token, worker_pid=os.getpid(), worker_identity="c" * 64)
    releases = []
    monkeypatch.setattr(skill_runtime, "operation_worker_entry", callback, raising=False)
    monkeypatch.setattr(
        skill_runtime,
        "release_operation_lease",
        lambda home, claim: releases.append(claim) or release_success,
        raising=False,
    )
    reader, writer = os.pipe()
    os.write(writer, raw)
    os.close(writer)
    try:
        code = operations.worker_main(setup["home"], token, reader)
    finally:
        os.close(reader)
    return token, code, releases


def test_worker_stores_only_safe_full_reply_and_releases_own_lease(setup, monkeypatch):
    calls = []

    def execute(req, context):
        calls.append(req.action)
        context.check_cancel()
        with context.publication():
            (setup["root"] / "reprollm.lock").write_text(
                "public scientific artifact", encoding="utf-8"
            )
        return Reply("lock", cli_exit_code=0, data={"full": "public" * 60000})

    token, code, releases = worker_in_process(setup, monkeypatch, execute)
    assert code == 0 and calls == ["lock"] and len(releases) == 1
    record = json.loads(record_path(setup, token).read_bytes())
    assert record["state"] == "COMPLETED" and record["lease"] is None
    result = control(setup, "operation.result", token)
    assert result.cli_exit_code == 0 and result.data["result"]["data"] == {"full": "public" * 60000}


def test_terminal_worker_retains_exact_claim_when_shared_release_fails(setup, monkeypatch):
    token, code, releases = worker_in_process(
        setup,
        monkeypatch,
        lambda req, context: Reply("lock", cli_exit_code=0),
        release_success=False,
    )
    assert code == 0 and releases == [setup["lease"].claim]
    record = json.loads(record_path(setup, token).read_bytes())
    assert record["state"] == "COMPLETED" and record["lease"] == setup["lease"].claim
    assert {"code": "operation_lease_cleanup_failed"} in control(
        setup, "operation.status", token
    ).diagnostics


def test_cancelled_worker_preserves_old_lock_and_confirms_terminal(setup, monkeypatch):
    target = setup["root"] / "reprollm.lock"
    target.write_bytes(b"old lock")

    def execute(req, context):
        raise operations.OperationCancelled

    token, code, releases = worker_in_process(setup, monkeypatch, execute)
    assert code == 0 and len(releases) == 1
    assert json.loads(record_path(setup, token).read_bytes())["state"] == "CANCELLED"
    assert target.read_bytes() == b"old lock"


def test_native_known_status_survives_result_delivery_failure(setup, monkeypatch):
    def execute(req, context):
        with context.publication():
            pass
        return Reply("lock", cli_exit_code=7, child_exit_code=-15, data={"bad": float("nan")})

    token, code, releases = worker_in_process(setup, monkeypatch, execute)
    assert code == 0 and len(releases) == 1
    result = control(setup, "operation.result", token)
    assert result.cli_exit_code == 7 and result.child_exit_code == -15
    assert not result.data["result"]["complete"]
    assert result.data["result"]["data"]["safe_to_repeat"] is False


def test_worker_unknown_completion_preserves_lease_and_never_retries(setup, monkeypatch):
    def execute(req, context):
        raise RuntimeError("opaque private startup detail")

    token, code, releases = worker_in_process(setup, monkeypatch, execute)
    assert code == 1 and releases == []
    record = json.loads(record_path(setup, token).read_bytes())
    assert record["state"] == "UNKNOWN" and record["lease"] is not None
    assert "opaque private startup detail" not in record_path(setup, token).read_text(
        encoding="utf-8"
    )


def test_pidfd_proof_does_not_signal_foreign_start_identity(monkeypatch):
    if not operations._platform():
        pytest.skip("Linux pidfd cancellation")
    # Restore only Popen for this independent real standard-library process test.
    process = subprocess.Popen(
        [sys.executable, "-c", "import time;time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        identity = operations._process_identity(process.pid)
        assert identity is not None
        assert not operations._signal_owned(
            {"worker_pid": process.pid, "worker_identity": "0" * 64}
        )
        assert process.poll() is None
        assert operations._signal_owned({"worker_pid": process.pid, "worker_identity": identity})
        assert process.wait(timeout=5) == -signal.SIGTERM
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
