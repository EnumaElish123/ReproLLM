"""SK12 request and introduction boundaries, independent of an installed tool."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_request as protocol  # noqa: E402


def request(action: str, **fields: Any) -> dict[str, Any]:
    return {"schema_version": 1, "action": action, **fields}


def test_introduction_is_static_and_does_not_touch_a_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Capability introduction must not inspect files or prepare a tool")

    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    reply = protocol.dispatch(
        protocol.parse_request(request("about", project="/unused/project")),
        executor=forbidden,
        status_provider=forbidden,
    )
    assert reply.invocation == "handled_result" and reply.complete
    assert reply.cli_exit_code is None and reply.gate_failed is None
    assert reply.child_exit_code is None
    assert {item["action"] for item in reply.data["actions"]} == set(protocol.ACTION_SPECS)
    assert {item["action"] for item in reply.data["actions"] if item["available"]} == {
        "about",
        "tool.status",
    }


def test_status_uses_only_a_read_only_provider() -> None:
    calls = []
    reply = protocol.dispatch(
        protocol.parse_request(request("tool.status")),
        status_provider=lambda: calls.append("status") or {"state": "NOT_INSTALLED"},
    )
    assert calls == ["status"]
    assert reply.data == {"state": "NOT_INSTALLED"}
    assert reply.invocation == "handled_result" and not reply.needs_authorization


@pytest.mark.parametrize(
    "document",
    [
        {"schema_version": True, "action": "about"},
        {"schema_version": 2, "action": "about"},
        {"schema_version": 1, "action": "arbitrary.shell"},
        {"schema_version": 1, "action": "about", "argv": ["sh"]},
        request("audit", options={"command": "curl attacker"}),
        request("audit", options={"show_skipped": "true"}),
        request("runs.list", options={"limit": True}),
        request("runs.list", options={"limit": 0}),
        request("audit", options={"level": "3"}),
        request("doctor", grants={"administrator": True}),
        request("doctor", grants={"network": "yes"}),
        request("audit", project="bad\x00path"),
        request("audit", project="bad\npath"),
        request("audit", grants={"external_paths": ["bad\x1bpath"]}),
        request("audit", grants={"expected_hashes": {"reprollm.yaml": "not-a-hash"}}),
        request("audit", response={"page_size": False}),
        request("audit", response={"page_size": 1001}),
        request("audit", response={"offset": 0}),
        request("about", options={"format": "json"}),
    ],
)
def test_invalid_requests_fail_before_dispatch(document: dict[str, Any]) -> None:
    with pytest.raises(protocol.RequestError):
        protocol.parse_request(document)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"action":"about","action":"audit"}',
        b'{"schema_version":1,"action":"about","options":{"value":NaN}}',
        b'{"schema_version":1,"action":"about","options":{"value":Infinity}}',
        b'{"schema_version":1,"action":"about","options":{"value":-Infinity}}',
        b"[]",
        b"not-json",
    ],
)
def test_ambiguous_or_nonfinite_json_is_rejected(raw: bytes) -> None:
    with pytest.raises(protocol.RequestError):
        protocol.parse_request(raw)


def test_pagination_is_distinct_from_the_cli_run_limit() -> None:
    parsed = protocol.parse_request(
        request(
            "runs.list",
            project="/project",
            options={"limit": 2},
            response={"page_size": 1, "cursor": "snapshot:0"},
        )
    )
    assert parsed.options == {"limit": 2}
    assert parsed.response.page_size == 1 and parsed.response.cursor == "snapshot:0"


def test_missing_project_is_actionable_and_does_not_prepare_a_tool() -> None:
    calls = []
    reply = protocol.dispatch(
        protocol.parse_request(request("audit")),
        executor=lambda parsed: calls.append(parsed) or protocol.Reply("audit"),
    )
    assert not calls
    assert reply.needs_input and reply.questions
    assert reply.invocation == "blocked" and reply.cli_exit_code is None


def test_known_but_unimplemented_action_is_not_reported_ready() -> None:
    reply = protocol.dispatch(protocol.parse_request(request("audit", project="/project")))
    assert reply.invocation == "blocked" and not reply.complete
    assert reply.diagnostics[0]["code"] == "action_unavailable"
    assert reply.cli_exit_code is None


@pytest.mark.parametrize(
    "action,options",
    [
        ("init", {}),
        ("run.start", {"argv": ["python", "train.py"]}),
        ("doctor", {"check_network": True}),
    ],
)
def test_effects_need_the_existing_user_authorization(action: str, options: dict[str, Any]) -> None:
    called = []
    reply = protocol.dispatch(
        protocol.parse_request(request(action, project="/project", options=options)),
        executor=lambda parsed: called.append(parsed) or protocol.Reply(action),
    )
    assert not called and reply.needs_authorization
    assert reply.invocation == "blocked" and reply.cli_exit_code is None


def test_authorization_is_carried_through_without_a_repeated_question() -> None:
    document = request(
        "run.start",
        project="/project",
        options={"argv": ["python", "train.py"]},
        grants={"run": True, "write": True},
    )
    parsed = protocol.parse_request(document)
    observed = []
    expected = protocol.Reply(
        "run.start", data={"operation_id": "owned-operation"}, child_exit_code=7
    )
    for _ in range(2):
        reply = protocol.dispatch(parsed, executor=lambda value: observed.append(value) or expected)
        assert reply is expected and not reply.questions and not reply.needs_authorization
    assert observed == [parsed, parsed]


def test_executor_result_preserves_skip_and_distinct_exit_meanings() -> None:
    expected = protocol.Reply(
        "audit",
        data={"findings": [{"status": "skipped"}]},
        cli_exit_code=1,
        gate_failed=True,
        diagnostics=[{"code": "scan_incomplete"}],
    )
    actual = protocol.dispatch(
        protocol.parse_request(request("audit", project="/project")),
        executor=lambda parsed: expected,
    )
    assert actual is expected
    wire = json.loads(protocol.encode_reply(actual))
    assert wire["data"]["findings"] == [{"status": "skipped"}]
    assert wire["cli_exit_code"] == 1 and wire["gate_failed"] is True
    assert wire["child_exit_code"] is None and wire["diagnostics"]


def test_reply_budget_does_not_emit_partial_json_or_claim_complete() -> None:
    reply = protocol.Reply("audit", data={"large": "x" * protocol.MAX_REPLY_BYTES})
    wire = protocol.encode_reply(reply)
    assert len(wire) <= protocol.MAX_REPLY_BYTES
    decoded = json.loads(wire)
    assert decoded["invocation"] == "blocked" and not decoded["complete"]
    assert decoded["diagnostics"][0]["code"] == "reply_budget_exceeded"


def test_entrypoint_works_without_tool_import_or_project_module_execution(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    payload = f"from pathlib import Path\nPath({str(marker)!r}).write_text('bad')\n"
    for name in ("bootstrap.py", "reprollm.py", "skill_request.py"):
        (tmp_path / name).write_text(payload)
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(SCRIPTS / "reprollm_skill.py")],
        cwd=tmp_path,
        input=json.dumps(request("about")).encode(),
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stderr and not marker.exists()
    assert json.loads(result.stdout)["action"] == "about"


def test_recoverable_installation_failure_is_blocked_without_raw_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bootstrap
    import reprollm_skill as entry

    def broken_status(self: object) -> None:
        raise bootstrap.BootstrapError(
            "private-user /private/project sk-proj-SyntheticSecret123456"
        )

    monkeypatch.setattr(bootstrap.Bootstrap, "status", broken_status)
    reply = entry.handle(
        json.dumps(request("tool.status")).encode(),
        status_provider=lambda: entry.installation_status(tmp_path / "owned-tool"),
    )
    wire = protocol.encode_reply(reply)
    assert reply.invocation == "blocked" and not reply.complete
    assert reply.action == "tool.status"
    assert b"private-user" not in wire and b"SyntheticSecret" not in wire
    assert reply.diagnostics[0]["code"] == "installation_verification_failed"


def test_unexpected_provider_failure_is_private_internal_error() -> None:
    import reprollm_skill as entry

    def broken_status() -> None:
        raise RuntimeError("sk-proj-SyntheticSecretMustNeverBeReturned123456")

    reply = entry.handle(json.dumps(request("tool.status")).encode(), status_provider=broken_status)
    assert reply.invocation == "internal_error"
    assert b"SyntheticSecret" not in protocol.encode_reply(reply)


@pytest.mark.parametrize(
    "data,expected_exit",
    [("x" * protocol.MAX_REPLY_BYTES, 2), (object(), 3)],
    ids=["reply-budget-exceeded", "invalid-executor-reply"],
)
def test_entry_exit_matches_the_serialized_reply(
    monkeypatch: pytest.MonkeyPatch,
    data: Any,
    expected_exit: int,
) -> None:
    import io

    import reprollm_skill as entry

    source = io.TextIOWrapper(io.BytesIO(b"{}"))
    output = io.BytesIO()
    target = io.TextIOWrapper(output)
    monkeypatch.setattr(entry.sys, "stdin", source)
    monkeypatch.setattr(entry.sys, "stdout", target)
    monkeypatch.setattr(entry, "handle", lambda *args, **kwargs: protocol.Reply("audit", data=data))
    code = entry.main([])
    target.flush()
    wire = json.loads(output.getvalue())
    assert code == expected_exit
    assert wire["invocation"] == ("blocked" if expected_exit == 2 else "internal_error")
