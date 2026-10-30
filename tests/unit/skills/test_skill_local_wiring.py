"""SK15 protocol, result delivery and transferred environment ownership."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_runtime as runtime  # noqa: E402
from skill_request import (  # noqa: E402
    Grants,
    Reply,
    Request,
    ResponseOptions,
    encode_reply,
    parse_request,
    required_grants,
)


@pytest.mark.parametrize(
    "action", ["lock", "rules.add", "rules.accept", "rules.ignore", "rules.remove", "rules.restore"]
)
def test_write_previews_are_typed_without_project_write_grants(action: str) -> None:
    required: dict[str, Any] = {
        "rules.add": {"field": "training.seed", "severity": "WARNING", "reason": "test"},
        "rules.accept": {"candidate_id": "candidate"},
        "rules.ignore": {"candidate_id": "candidate"},
        "rules.remove": {"rule_id": "rule", "reason": "test"},
        "rules.restore": {"archive_id": "archive"},
    }.get(action, {"offline": True})
    req = parse_request(
        {"schema_version": 1, "action": action, "options": {**required, "preview": True}}
    )
    assert "write" not in required_grants(req)


def test_check_priority_and_operation_query_grants() -> None:
    req = parse_request(
        {
            "schema_version": 1,
            "action": "lock",
            "options": {
                "check": True,
                "offline": False,
                "verify_api": True,
                "hash_large_files": True,
                "operation_id": "0" * 32,
            },
        }
    )
    assert not required_grants(req)
    for action in ("operation.status", "operation.result"):
        req = parse_request(
            {"schema_version": 1, "action": action, "options": {"operation_id": "0" * 32}}
        )
        assert not required_grants(req)
    req = parse_request(
        {"schema_version": 1, "action": "operation.cancel", "options": {"operation_id": "0" * 32}}
    )
    assert required_grants(req) == {"write"}


@pytest.mark.parametrize("action", ["lock", "rules.list", "rules.show"])
def test_native_local_result_uses_privacy_and_retains_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    raw = Reply(
        action,
        cli_exit_code=1 if action == "lock" else 0,
        data={"api_key": "public-synthetic-secret", "reasons": ["stale"]},
        diagnostics=[{"code": "cli_stderr", "text": "password=public-secret"}],
    )
    local = SimpleNamespace(execute_lock=lambda *a, **k: raw, execute_rules=lambda *a, **k: raw)
    monkeypatch.setitem(sys.modules, "skill_local", local)
    options = (
        {"offline": True, "check": True}
        if action == "lock"
        else ({"id": "public-rule"} if action == "rules.show" else {})
    )
    reply = runtime.execute(Request(action, str(root), options), cache_home=tmp_path / "responses")
    text = json.dumps(reply.as_dict())
    assert reply.invocation == "handled_result" and reply.cli_exit_code == raw.cli_exit_code
    assert reply.gate_failed is None and reply.child_exit_code is None
    assert "public-synthetic-secret" not in text and "public-secret" not in text
    assert reply.data["reasons"] == ["stale"]


def test_safe_complete_result_can_be_persisted_before_paging(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    req = Request(
        "operation.result",
        str(root),
        {"operation_id": "0" * 32},
        response=ResponseOptions(page_size=2),
    )
    original = Reply(
        req.action,
        cli_exit_code=1,
        gate_failed=True,
        child_exit_code=7,
        data=[{"index": i, "password": "synthetic-private"} for i in range(5)],
    )
    safe = runtime.sanitize_reply(original, root)
    assert "synthetic-private" not in json.dumps(safe.as_dict())
    assert len(safe.data) == 5 and safe.complete
    assert original.data[0]["password"] == "synthetic-private"
    page = runtime.finish_reply(
        safe,
        req,
        root=root,
        external=[],
        cache_home=tmp_path / "responses",
        identity="fixed-helper",
    )
    assert not page.complete and page.next_cursor and page.gate_failed is True
    assert page.cli_exit_code == 1 and page.child_exit_code == 7
    follow = dataclasses.replace(req, response=ResponseOptions(2, page.next_cursor))
    final = runtime.execute(follow, cache_home=tmp_path / "responses", identity="fixed-helper")
    assert not final.complete and final.next_cursor
    assert [item["index"] for item in final.data["items"]] == [2, 3]


class Manager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _lock(self) -> Any:
        return contextlib.nullcontext()

    def _verify(self, name: str) -> dict[str, Any]:
        return {"state": "READY", "environment": name, "capabilities": ["contextual_word_scan"]}

    def environment_path(self, name: str) -> Path:
        return self.root / name


def test_transfer_keeps_only_owned_lease_until_terminal_release(tmp_path: Path) -> None:
    manager = Manager(tmp_path)
    name = "1" * 32
    manager.environment_path(name).mkdir()
    with runtime._worker_lease(manager, name) as lease:
        claim = lease.claim
        lease.transfer()
        own = manager.environment_path(name) / "leases" / (claim["lease_id"] + ".json")
        foreign = own.with_name("foreign.json")
        foreign.write_text('{"schema_version":1,"owner":"other"}')
    assert own.is_file() and not lease.cleanup_failed
    assert str(tmp_path) not in json.dumps(claim)
    assert runtime.release_owned_lease(manager, claim)
    assert not own.exists() and foreign.is_file()


def test_proven_no_launch_can_reclaim_transferred_lease(tmp_path: Path) -> None:
    manager = Manager(tmp_path)
    name = "2" * 32
    manager.environment_path(name).mkdir()
    with runtime._worker_lease(manager, name) as lease:
        lease.transfer()
        lease.reclaim()
    assert not (manager.environment_path(name) / "leases").exists()


def test_terminal_cleanup_refuses_changed_ownership(tmp_path: Path) -> None:
    manager = Manager(tmp_path)
    name = "3" * 32
    manager.environment_path(name).mkdir()
    with runtime._worker_lease(manager, name) as lease:
        claim = lease.claim
        path = manager.environment_path(name) / "leases" / (claim["lease_id"] + ".json")
        path.write_text('{"schema_version":1,"owner":"another"}')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert lease.cleanup_failed and path.is_file()
    assert not runtime.release_owned_lease(manager, claim)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("action", ["operation.status", "operation.result", "operation.cancel"])
def test_operation_controls_do_not_prepare_an_active_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    import bootstrap

    root = tmp_path / "project"
    root.mkdir()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("An owned operation query must not prepare a replacement installation")

    monkeypatch.setattr(bootstrap, "Bootstrap", forbidden)
    calls: list[str] = []
    monkeypatch.setitem(
        sys.modules,
        "skill_operations",
        SimpleNamespace(
            control=lambda req, **kw: (
                calls.append(req.action)
                or Reply(
                    req.action, data={"operation": {"state": "COMPLETED", "result_available": True}}
                )
            ),
        ),
    )
    req = Request(action, str(root), {"operation_id": "0" * 32}, Grants(write=True))
    reply = runtime.RuntimeExecutor(tmp_path / "owned-home")(req)
    assert reply.invocation == "handled_result" and calls == [action]
    assert reply.data["operation"]["state"] == "COMPLETED"


def test_large_hash_cannot_enter_the_short_rpc_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    root.mkdir()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("A large hash must use the owned long-operation controller")

    monkeypatch.setitem(
        sys.modules,
        "skill_local",
        SimpleNamespace(
            execute_lock=forbidden,
            execute_rules=forbidden,
        ),
    )
    req = Request(
        "lock", str(root), {"offline": True, "hash_large_files": True}, Grants(write=True)
    )
    reply = runtime.execute(req, cache_home=tmp_path / "responses")
    assert reply.invocation == "blocked"
    assert reply.diagnostics == [{"code": "long_operation_requires_controller"}]


def test_lock_check_keeps_precedence_over_long_hash_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    seen = []
    monkeypatch.setitem(
        sys.modules,
        "skill_local",
        SimpleNamespace(
            execute_lock=lambda req, **kw: (
                seen.append(req.options) or Reply(req.action, cli_exit_code=1)
            ),
            execute_rules=lambda *args, **kwargs: pytest.fail("wrong producer"),
        ),
    )
    req = Request("lock", str(root), {"check": True, "hash_large_files": True})
    reply = runtime.execute(req, cache_home=tmp_path / "responses")
    assert reply.cli_exit_code == 1 and reply.gate_failed is None
    assert len(seen) == 1


def test_delivery_failure_retains_operation_handle_and_known_exit() -> None:
    reply = Reply(
        "operation.result",
        cli_exit_code=1,
        gate_failed=True,
        child_exit_code=7,
        data={
            "operation": {
                "operation_id": "a" * 32,
                "kind": "lock",
                "state": "COMPLETED",
                "execution_started": True,
                "result_available": True,
                "artifact_publication": "known",
                "safe_to_repeat": False,
            },
            "result": {"stdout": "x" * 300_000},
        },
    )
    wire = encode_reply(reply)
    compact = json.loads(wire)
    assert compact["cli_exit_code"] == 1 and compact["child_exit_code"] == 7
    assert compact["gate_failed"] is True and not compact["complete"]
    assert compact["data"]["operation"]["operation_id"] == "a" * 32
    assert compact["data"]["safe_to_repeat"] is False
    assert len(wire) + 1 <= 256 * 1024


def test_review_diagnostic_payload_is_private_before_result_storage(tmp_path: Path) -> None:
    original = Reply(
        "rules.candidates",
        diagnostics=[
            {
                "code": "rule_source_snapshot",
                "source": "api_key=synthetic-snapshot-secret",
                "api_key": "unmarked-private",
                "active_sha256": "a" * 64,
            }
        ],
    )
    safe = runtime.sanitize_reply(original, tmp_path)
    assert "synthetic-snapshot-secret" not in json.dumps(safe.as_dict())
    assert "unmarked-private" not in json.dumps(safe.as_dict())
    assert safe.diagnostics[0]["code"] == "rule_source_snapshot"
    assert safe.diagnostics[0]["active_sha256"] == "a" * 64
    assert original.diagnostics[0]["source"] == "api_key=synthetic-snapshot-secret"


@pytest.mark.parametrize(
    "action,options,unknown",
    [
        ("lock", {"offline": True}, True),
        ("lock", {"check": True}, False),
        ("lock", {"offline": True, "preview": True}, False),
        ("rules.add", {"field": "training.seed", "severity": "INFO", "reason": "test"}, True),
        ("rules.remove", {"rule_id": "user.seed", "reason": "test"}, True),
        ("rules.restore", {"archive_id": "a" * 64}, True),
    ],
)
def test_lost_local_worker_reports_unknown_writes_only_when_applicable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    options: dict[str, Any],
    unknown: bool,
) -> None:
    import bootstrap
    import install_catalog
    from tests.unit.skills.test_bootstrap import FakeBackend, candidate, source_blob

    root = tmp_path / "project"
    root.mkdir()
    blob = source_blob()
    selected = dataclasses.replace(
        candidate("local-timeout", blob), capabilities=("contextual_word_scan",)
    )
    catalog = install_catalog.Catalog(1, selected.id, (selected,))
    manager = bootstrap.Bootstrap(tmp_path / "owned-home", catalog, backend=FakeBackend(blob))
    manager.ensure()
    monkeypatch.setattr(bootstrap, "Bootstrap", lambda *args: manager)
    monkeypatch.setattr(install_catalog, "load_catalog", lambda *args: catalog)

    def lose_worker(argv: list[str], **kwargs: Any) -> Any:
        raise runtime.subprocess.TimeoutExpired(argv, 120)

    monkeypatch.setattr(runtime.subprocess, "run", lose_worker)
    reply = runtime.RuntimeExecutor(manager.home)(
        Request(action, str(root), options, Grants(write=True))
    )
    assert reply.invocation == "blocked" and not reply.complete
    if unknown:
        assert reply.data == {
            "scope": "unknown_completion",
            "artifact_publication_unknown": True,
            "safe_to_repeat": False,
        }
    else:
        assert reply.data is None
