"""SK19 owned run claims, finite delivery and native integration seams."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_operations as operations  # noqa: E402
import skill_runtime as runtime  # noqa: E402
from skill_request import (  # noqa: E402
    Grants,
    Reply,
    Request,
    encode_reply,
    parse_request,
    required_grants,
)
from tests.unit.skills import test_skill_operations as contract  # noqa: E402

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned runs"),
]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    return contract.setup.__wrapped__(tmp_path, monkeypatch)


def run_request(root, token=None, plan=None, **options):
    return Request(
        "run.start",
        str(root),
        {"argv": ["python", "public.py"], **options, **({"operation_id": token} if token else {})},
        Grants(install=False, write=True, run=True, plan_hash=plan),
    )


def alias(setup, action, token, *, grants=None):
    return operations.control(
        Request(action, str(setup["root"]), {"operation_id": token}, grants or Grants()),
        home=setup["home"],
        root=setup["root"],
    )


def test_run_actions_are_typed_and_available():
    names = {"run.start", "run.status", "run.result", "run.cancel", "run.logs"}
    assert names <= runtime.AVAILABLE_ACTIONS
    assert runtime.long_operation(run_request(Path("/public")))
    req = parse_request(
        {
            "schema_version": 1,
            "action": "run.start",
            "project": "/public",
            "options": {"operation_id": "a" * 32},
        }
    )
    assert req.options["operation_id"] == "a" * 32
    assert required_grants(Request("run.cancel")) == {"write", "run"}


def test_prepare_without_plan_is_zero_work_then_known_id_binds_once(setup):
    prepared = contract.start(setup, run_request(setup["root"]))
    token = contract.operation_id(prepared)
    assert prepared.data["operation"]["state"] == "PREPARED"
    assert setup["launches"] == [] and not (setup["root"] / ".reprollm").exists()
    missing = contract.start(setup, run_request(setup["root"], token))
    assert missing.invocation == "blocked" and setup["launches"] == []
    started = contract.start(setup, run_request(setup["root"], token, "d" * 64))
    assert started.data["operation"]["state"] == "STARTING"
    record = json.loads(contract.record_path(setup, token).read_bytes())
    assert record["run_plan_sha256"] == "d" * 64
    assert len(setup["launches"]) == 1
    contract.start(setup, run_request(setup["root"], token, "d" * 64))
    changed = contract.start(setup, run_request(setup["root"], token, "e" * 64))
    assert changed.invocation == "blocked" and len(setup["launches"]) == 1


@pytest.mark.parametrize("action", ["run.status", "run.result", "run.cancel", "run.logs"])
def test_unknown_run_handle_refuses_before_install_or_work(setup, action):
    reply = alias(setup, action, "0" * 32, grants=Grants(write=True, run=True))
    assert reply is not None and reply.invocation == "blocked"
    assert not setup["home"].exists() and setup["launches"] == []


@pytest.mark.parametrize("action", ["run.status", "run.result", "run.cancel", "run.logs"])
def test_run_alias_cannot_control_a_lock_operation(setup, action):
    token = contract.operation_id(contract.start(setup, contract.request(setup["root"])))
    reply = alias(setup, action, token, grants=Grants(write=True, run=True))
    assert reply.invocation == "blocked" and setup["launches"] == []


def test_cancel_prepared_run_is_truthful_zero_child(setup):
    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    reply = alias(setup, "run.cancel", token, grants=Grants(write=True, run=True))
    assert reply.data["operation"]["state"] == "CANCELLED"
    assert reply.data["operation"]["execution_started"] is False and setup["launches"] == []


def test_starting_cancel_without_ack_never_signals_or_restarts(setup, monkeypatch):
    import skill_run_cancel

    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    contract.start(setup, run_request(setup["root"], token, "d" * 64))
    monkeypatch.setattr(skill_run_cancel, "_send", lambda *a: pytest.fail("Unacknowledged worker"))
    reply = alias(setup, "run.cancel", token, grants=Grants(write=True, run=True))
    assert reply.data["operation"]["state"] == "STARTING"
    assert (
        reply.data["operation"]["cancel_requested"]
        and not reply.data["operation"]["cancel_delivered"]
    )
    contract.start(setup, run_request(setup["root"], token, "d" * 64))
    assert len(setup["launches"]) == 1


@pytest.mark.parametrize(
    "native_status",
    [
        "/tmp/private api_key=OpaqueSyntheticStateSecret",
        {"private": "OpaqueSyntheticStateSecret"},
        7,
        True,
    ],
)
def test_native_status_requires_finite_type_and_defensive_public_projection(setup, native_status):
    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    contract.edit_record(setup, token, native_status=native_status)
    reply = alias(setup, "run.status", token)
    assert reply.invocation == "blocked"
    assert "OpaqueSyntheticStateSecret" not in json.dumps(reply.as_dict())
    record = json.loads(contract.record_path(setup, token).read_bytes())
    public = operations._public(record)
    assert public["native_status"] is None
    assert "OpaqueSyntheticStateSecret" not in json.dumps(public)


def test_run_cancel_uses_kind_aware_controller_never_generic_worker_kill(setup, monkeypatch):
    import skill_run_cancel

    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    contract.start(setup, run_request(setup["root"], token, "d" * 64))
    contract.edit_record(setup, token, state="RUNNING", cancel_delivered=True)
    monkeypatch.setattr(operations, "_signal_owned", lambda *a: pytest.fail("No generic run kill"))
    seen = []

    def cancel(record, *, acknowledged, save):
        seen.append(acknowledged)
        record["run_cancel"] = {"cleanup_scope": "unknown_descendants", "phase": "term"}
        save()

    monkeypatch.setattr(skill_run_cancel, "cancel_run", cancel)
    reply = alias(setup, "run.cancel", token, grants=Grants(write=True, run=True))
    assert seen == [True] and reply.data["operation"]["state"] == "RUNNING"
    assert reply.data["operation"]["run_cancel"]["cleanup_scope"] == "unknown_descendants"


def test_native_run_binding_is_durable_exact_and_cannot_change(setup, monkeypatch):
    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    contract.start(setup, run_request(setup["root"], token, "d" * 64))
    contract.edit_record(setup, token, worker_pid=os.getpid(), worker_identity="c" * 64)
    record = json.loads(contract.record_path(setup, token).read_bytes())
    context = operations.WorkerContext(
        setup["home"],
        setup["root"],
        "d" * 64,
        token,
        record["lease"],
        setup["home"] / "operations",
        "synthetic",
    )
    contract.edit_record(setup, token, nonce_hash=hashlib.sha256(b"synthetic").hexdigest())
    folder = setup["root"] / ".reprollm/runs/20261031T000000Z-abcdef"
    folder.mkdir(parents=True)
    context.bind_run(folder.name)
    record = json.loads(contract.record_path(setup, token).read_bytes())
    assert record["native_run_id"] == folder.name and len(record["native_run_identity"]) == 64
    context.bind_run(folder.name)
    with pytest.raises(ValueError):
        context.bind_run("20261031T000000Z-fedcba")
    assert "public.py" not in contract.record_path(setup, token).read_text()


def test_original_run_preview_now_uses_plan_and_saved_cwd_without_tree_hash(setup, monkeypatch):
    root = setup["root"]
    (root / "work").mkdir()
    (root / "reprollm.yaml").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": {"name": "public"},
                "experiment": {"profiles": []},
                "execution": {"command": "python public.py", "cwd": "work"},
            }
        )
    )
    monkeypatch.setattr(
        runtime, "input_signature", lambda *a: pytest.fail("No experiment tree hash")
    )
    reply = runtime.execute(
        Request("run.preview", str(root)), cache_home=setup["home"] / "responses"
    )
    assert reply.data["start_ready"] is True and len(reply.data["plan_hash"]) == 64
    assert "Working directory: work" in reply.data["preflight"]["text"]


@pytest.mark.parametrize("changed_source", ["claim", "result"])
def test_finite_result_pages_retain_known_exit_without_tree_hash(
    setup, monkeypatch, changed_source
):
    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    folder = contract.record_path(setup, token).parent
    raw = json.dumps(
        Reply("run.start", child_exit_code=7, data={"large": "public" * 60000}).as_dict()
    ).encode()
    (folder / "result.json").write_bytes(raw)
    (folder / "result.json").chmod(0o600)
    contract.edit_record(
        setup,
        token,
        state="COMPLETED",
        result_sha256=hashlib.sha256(raw).hexdigest(),
        ended_at=operations._utc(),
    )
    monkeypatch.setattr(
        runtime, "input_signature", lambda *a: pytest.fail("No experiment tree hash")
    )
    req = Request("run.result", str(setup["root"]), {"operation_id": token})
    full = alias(setup, "run.result", token)
    reply = runtime.finish_reply(
        full,
        req,
        root=setup["root"],
        external=[],
        cache_home=setup["home"] / "responses",
        identity="public",
        sanitized=True,
    )
    assert reply.child_exit_code == 7 and reply.next_cursor and not reply.complete
    follow = dataclasses.replace(
        req, response=dataclasses.replace(req.response, cursor=reply.next_cursor)
    )
    page = runtime.execute(follow, cache_home=setup["home"] / "responses", identity="public")
    assert page.child_exit_code == 7 and page.invocation == "handled_result"
    if changed_source == "claim":
        contract.edit_record(setup, token, cancel_requested=True)
        expected_invocation, expected_code = "blocked", "response_snapshot_stale"
    else:
        (folder / "result.json").write_bytes(raw + b" ")
        expected_invocation, expected_code = "user_error", "readonly_input_unavailable"
    stale = runtime.execute(follow, cache_home=setup["home"] / "responses", identity="public")
    assert stale.invocation == expected_invocation and not stale.complete
    assert stale.diagnostics == [{"code": expected_code}]
    assert stale.data is None and stale.next_cursor is None


def test_oversized_run_delivery_retains_operation_and_actual_native_id():
    actual = "20261031T000000Z-abcdef"
    reply = Reply(
        "run.result",
        child_exit_code=7,
        data={
            "operation": {
                "operation_id": "a" * 32,
                "kind": "run.start",
                "state": "COMPLETED",
                "native_run_id": actual,
                "native_status": "completed",
                "cleanup_scope": "unknown_descendants",
            },
            "result": "public" * 100000,
        },
    )
    compact = json.loads(encode_reply(reply))
    assert compact["child_exit_code"] == 7
    assert compact["data"]["operation"]["native_run_id"] == actual
    assert compact["data"]["operation"]["kind"] == "run.start"


def test_worker_delivery_failure_keeps_bound_run_scope_and_actual_seven(setup, monkeypatch):
    real_popen = operations.subprocess.Popen
    payloads = []

    def capture(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        payloads.append(process.stdin)
        return process

    monkeypatch.setattr(operations.subprocess, "Popen", capture)
    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    contract.start(setup, run_request(setup["root"], token, "d" * 64))
    contract.edit_record(setup, token, worker_pid=os.getpid(), worker_identity="c" * 64)
    actual = "20261031T000000Z-abcdef"

    def returned(request, context):
        (setup["root"] / ".reprollm/runs" / actual).mkdir(parents=True)
        context.bind_run(actual)
        return Reply(
            "run.start",
            child_exit_code=7,
            data={
                "run_id": actual,
                "record_scope": "native_return",
                "record": {"status": "completed"},
                "bad": float("nan"),
            },
        )

    monkeypatch.setattr(runtime, "operation_worker_entry", returned)
    monkeypatch.setattr(runtime, "release_operation_lease", lambda *a: True)
    reader, writer = os.pipe()
    os.write(writer, payloads[0].saved)
    os.close(writer)
    try:
        assert operations.worker_main(setup["home"], token, reader) == 0
    finally:
        os.close(reader)
    reply = alias(setup, "run.result", token)
    assert reply.child_exit_code == 7
    assert reply.data["operation"]["state"] == "COMPLETED"
    assert reply.data["result"]["data"]["run_id"] == actual
    assert reply.data["result"]["data"]["record_scope"] == "native_return"


@pytest.mark.parametrize("action", ["run.status", "run.result", "run.cancel"])
def test_run_controls_survive_without_active_installation(setup, monkeypatch, action):
    import bootstrap

    token = contract.operation_id(contract.start(setup, run_request(setup["root"])))
    monkeypatch.setattr(bootstrap, "Bootstrap", lambda *a: pytest.fail("Control must not install"))
    reply = runtime.RuntimeExecutor(setup["home"])(
        Request(
            action,
            str(setup["root"]),
            {"operation_id": token},
            Grants(install=False, write=True, run=True),
        )
    )
    assert reply.invocation == "handled_result" and reply.data["operation"]["operation_id"] == token


def test_preview_paging_rechecks_finite_plan_and_keeps_ready_fact(setup, monkeypatch):
    from reprollm.run import preflight

    root = setup["root"]
    (root / "reprollm.yaml").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": {"name": "public"},
                "experiment": {"profiles": []},
                "execution": {"command": "python public.py"},
            }
        )
    )
    monkeypatch.setattr(preflight, "preview", lambda *a, **kw: "public advisory\n" * 30000)
    monkeypatch.setattr(
        runtime, "input_signature", lambda *a: pytest.fail("No experiment tree hash")
    )
    request = Request("run.preview", str(root))
    first = runtime.execute(request, cache_home=setup["home"] / "responses", identity="public")
    assert first.next_cursor and not first.complete
    follow = dataclasses.replace(
        request, response=dataclasses.replace(request.response, cursor=first.next_cursor)
    )
    assert (
        runtime.execute(
            follow, cache_home=setup["home"] / "responses", identity="public"
        ).invocation
        == "handled_result"
    )
    (root / "reprollm.yaml").write_text(
        (root / "reprollm.yaml").read_text().replace("public.py", "changed.py")
    )
    stale = runtime.execute(follow, cache_home=setup["home"] / "responses", identity="public")
    assert stale.invocation == "blocked" and not stale.complete
