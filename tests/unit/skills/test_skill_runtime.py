"""SK13: read-only results preserve CLI evidence and safe bounded delivery."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
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
)


class VerifiedManagerStub:
    def _lock(self) -> Any:
        return contextlib.nullcontext()

    def _verify(self, name: str) -> dict[str, Any]:
        environment = self.environment_path(name)
        environment.mkdir(parents=True, exist_ok=True)
        return {"state": "READY", "environment": name, "capabilities": ["contextual_word_scan"]}

    def environment_path(self, name: str) -> Path:
        raise NotImplementedError


def request(project: Path, action: str = "audit", **options: Any) -> Request:
    return parse_request(
        {"schema_version": 1, "action": action, "project": str(project), "options": options}
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "研究 project"
    root.mkdir()
    (root / "config.json").write_text('{"temperature":0}')
    return root


def report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "summary": {"warning": 1, "skipped": 1},
        "findings": [{"status": "fail", "value": False}, {"status": "skipped", "value": 0}],
    }


def run(
    project: Path,
    tmp_path: Path,
    payload: dict[str, Any] | list[Any] | str,
    *,
    code: int = 0,
    stderr: str = "",
    action: str = "audit",
    **options: Any,
) -> Reply:
    raw = json.dumps(payload) if not isinstance(payload, str) else payload
    return runtime.execute(
        request(project, action, **options),
        cache_home=tmp_path / "cache",
        cli_runner=lambda argv, cwd: runtime.CliResult(code, raw, stderr),
    )


@pytest.mark.parametrize("code,gate", [(0, False), (1, True)])
def test_audit_gate_preserves_complete_json_and_diagnostics(
    project: Path,
    tmp_path: Path,
    code: int,
    gate: bool,
) -> None:
    reply = run(project, tmp_path, report(), code=code, stderr="selected Python view incomplete\n")
    assert reply.invocation == "handled_result" and reply.cli_exit_code == code
    assert reply.gate_failed is gate and reply.child_exit_code is None
    assert reply.complete and reply.data == report()
    assert "view incomplete" in json.dumps(reply.diagnostics)


@pytest.mark.parametrize("code,invocation", [(2, "user_error"), (3, "internal_error")])
def test_cli_errors_remain_distinct(
    project: Path, tmp_path: Path, code: int, invocation: str
) -> None:
    reply = run(project, tmp_path, "", code=code, stderr="repair fixture input")
    assert reply.invocation == invocation and reply.cli_exit_code == code
    assert reply.gate_failed is None and not reply.complete and reply.data is None
    assert "repair fixture" in json.dumps(reply.diagnostics)


def test_invalid_json_success_is_internal_error(project: Path, tmp_path: Path) -> None:
    reply = run(project, tmp_path, '{"incomplete":')
    assert reply.invocation == "internal_error" and not reply.complete
    assert reply.gate_failed is None


def test_doctor_missing_tools_is_handled_diagnosis(project: Path, tmp_path: Path) -> None:
    reply = run(project, tmp_path, {"checks": [{"status": "missing"}]}, action="doctor", code=1)
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 1
    assert reply.gate_failed is None


def test_explicit_text_and_local_network_boundary(project: Path, tmp_path: Path) -> None:
    calls = []
    req = request(project, "doctor", json=False)
    reply = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda argv, cwd: calls.append(argv) or runtime.CliResult(0, "local only\n", ""),
    )
    assert reply.data == "local only\n" and "--check-network" not in calls[0]
    req = request(project, "doctor", check_network=True)
    blocked = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: pytest.fail("No network before SK16"),
    )
    assert blocked.invocation == "blocked" and blocked.needs_authorization


def test_run_limit_does_not_become_pagination_limit(project: Path, tmp_path: Path) -> None:
    req = dataclasses.replace(
        request(project, "runs.list", limit=2), response=ResponseOptions(page_size=1)
    )
    calls = []
    result = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda argv, cwd: (
            calls.append(argv) or runtime.CliResult(0, '[{"id":1},{"id":2}]', "")
        ),
    )
    assert calls[0][calls[0].index("--limit") + 1] == "2"
    assert result.complete is False and result.next_cursor
    assert result.data["items"] == [{"id": 1}]


def test_paging_reconstructs_all_findings_and_diagnostics_without_second_cli(
    project: Path,
    tmp_path: Path,
) -> None:
    payload = report()
    payload["findings"] = [{"status": "skipped", "n": n} for n in range(7)]
    req = dataclasses.replace(request(project), response=ResponseOptions(page_size=2))
    calls = []

    def cli(argv: list[str], cwd: Path) -> runtime.CliResult:
        calls.append(argv)
        return runtime.CliResult(1, json.dumps(payload), "full diagnostic\n")

    reply = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    found = []
    snapshots = set()
    while True:
        assert len(encode_reply(reply)) <= 256 * 1024 and reply.gate_failed is True
        assert reply.data["summary"] == payload["summary"]
        assert "full diagnostic" in json.dumps(reply.diagnostics)
        found.extend(reply.data["items"])
        snapshots.add(reply.snapshot)
        if not reply.next_cursor:
            break
        req = dataclasses.replace(
            req, response=ResponseOptions(page_size=2, cursor=reply.next_cursor)
        )
        reply = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    assert found == payload["findings"] and len(calls) == 1 and len(snapshots) == 1
    assert not reply.complete


def test_single_large_value_is_lossless_bounded_json_fragments(
    project: Path, tmp_path: Path
) -> None:
    payload = {"value": "研究" * 100_000 + chr(92) + chr(34)}
    req = request(project)
    reply = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, json.dumps(payload), ""),
    )
    parts = []
    while True:
        assert len(encode_reply(reply)) <= 256 * 1024 and not reply.complete
        assert reply.data["scope"] == "partial_document"
        parts.append(reply.data["text"])
        if not reply.next_cursor:
            break
        req = dataclasses.replace(req, response=ResponseOptions(cursor=reply.next_cursor))
        reply = runtime.execute(
            req,
            cache_home=tmp_path / "cache",
            cli_runner=lambda *_: pytest.fail("Cursor must not rerun CLI"),
        )
    restored = json.loads("".join(parts))
    assert restored["data"] == payload


def test_source_change_invalidates_cursor(project: Path, tmp_path: Path) -> None:
    req = dataclasses.replace(request(project, "runs.list"), response=ResponseOptions(page_size=1))
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    (project / "config.json").write_text('{"temperature":1}')
    req = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    second = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: pytest.fail("Stale cursor must not rerun CLI"),
    )
    assert second.invocation == "blocked" and not second.complete


def test_display_and_cache_are_private(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime.getpass, "getuser", lambda: "private-person")
    monkeypatch.setattr(runtime.socket, "gethostname", lambda: "private-node")
    secret = "sk-proj-SyntheticOnlyNeverARealCredential123456789"
    payload = {
        "password": "synthetic-password-value",
        "note": f"{secret} private-person private-node /private/machine/config\x1b[31m\u202e",
    }
    reply = run(project, tmp_path, payload)
    wire = encode_reply(reply)
    for value in (
        secret,
        "synthetic-password-value",
        "private-person",
        "private-node",
        "/private/machine",
    ):
        assert value.encode() not in wire
    assert b"\\u001b" not in wire and b"\xe2\x80\xae" not in wire
    for file in (tmp_path / "cache").rglob("*.json"):
        raw = file.read_bytes()
        assert secret.encode() not in raw and str(project).encode() not in raw


def test_audit_output_requires_exact_approval_and_preserves_complete_cli_bytes(
    project: Path, tmp_path: Path
) -> None:
    output = project / "audit.json"
    raw = json.dumps(report(), indent=2) + "\n"
    req = request(project, output="audit.json")

    def cli(argv: list[str], cwd: Path) -> runtime.CliResult:
        assert "--output" not in argv
        return runtime.CliResult(1, raw, "")

    denied = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    assert denied.invocation == "blocked" and not output.exists()
    req = dataclasses.replace(req, grants=Grants(write=True, expected_hashes={"audit.json": None}))
    reply = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    assert output.read_bytes() == raw.encode() and reply.gate_failed is True
    assert reply.data["report"] == report() and "Wrote audit report" in reply.data["stdout"]
    output.write_text("new editor content")
    stale = runtime.execute(
        req, cache_home=tmp_path / "cache", cli_runner=lambda *_: pytest.fail("No stale write")
    )
    assert stale.invocation == "blocked" and output.read_text() == "new editor content"


def test_external_diff_inputs_need_specific_paths(project: Path, tmp_path: Path) -> None:
    other = tmp_path / "other.lock"
    other.write_text("fixture")
    req = request(project, "diff", a=str(other), b="inside.lock")
    blocked = runtime.execute(
        req, cache_home=tmp_path / "cache", cli_runner=lambda *_: pytest.fail("No unapproved read")
    )
    assert blocked.invocation == "blocked" and blocked.needs_authorization


def test_ancestor_scope_requires_explicit_authority(project: Path, tmp_path: Path) -> None:
    (project / "reprollm.yaml").write_text("schema_version: 1")
    nested = project / "nested"
    nested.mkdir()
    reply = runtime.execute(
        request(nested),
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: pytest.fail("Do not scan unauthorized ancestor"),
    )
    assert reply.invocation == "blocked" and reply.needs_authorization


@pytest.mark.parametrize(
    "action,options,argv,json_output",
    [
        (
            "audit",
            {
                "format": "github",
                "show_passed": False,
                "show_skipped": True,
                "profiles": ["inference"],
                "level": "1",
                "details": True,
            },
            [
                "audit",
                "<ROOT>",
                "--format",
                "github",
                "--level",
                "1",
                "--profiles",
                "inference",
                "--no-show-passed",
                "--show-skipped",
                "--details",
            ],
            False,
        ),
        ("doctor", {}, ["doctor", "--json"], True),
        ("profiles.list", {}, ["profiles", "list", "--json"], True),
        ("profiles.show", {"name": "inference"}, ["profiles", "show", "--", "inference"], False),
        ("init.tasks", {}, ["init", "<ROOT>", "--list-tasks"], False),
        ("runs.show", {"run_id": "20260101"}, ["runs", "show", "--json", "--", "20260101"], True),
        (
            "diff",
            {"latest_successful": True, "name": "sample", "min_severity": "LOW", "fail_on": "HIGH"},
            [
                "diff",
                "--format",
                "json",
                "--latest-successful",
                "--name",
                "sample",
                "--min-severity",
                "LOW",
                "--fail-on",
                "HIGH",
            ],
            True,
        ),
    ],
)
def test_each_readonly_command_has_explicit_typed_argv(
    project: Path,
    action: str,
    options: dict[str, Any],
    argv: list[str],
    json_output: bool,
) -> None:
    actual, parsed_json = runtime.command_args(request(project, action, **options), project)
    assert actual == [str(project) if value == "<ROOT>" else value for value in argv]
    assert parsed_json is json_output


def test_actual_cli_parity_keeps_full_audit_and_profile_data(project: Path, tmp_path: Path) -> None:
    direct = runtime.invoke_cli(
        ["audit", str(project), "--format", "json", "--fail-on", "never"], project
    )
    actual = runtime.execute(request(project, fail_on="never"), cache_home=tmp_path / "cache")
    expected = json.loads(direct.stdout)
    assert actual.cli_exit_code == direct.exit_code == 0
    assert actual.complete and actual.data.keys() == expected.keys()
    actual.data.pop("generated_at")
    expected.pop("generated_at")
    assert actual.data == expected
    direct_profiles = runtime.invoke_cli(["profiles", "list", "--json"], project)
    profiles = runtime.execute(request(project, "profiles.list"), cache_home=tmp_path / "cache")
    assert profiles.data == json.loads(direct_profiles.stdout)
    for action, options in (
        ("profiles.show", {"name": "inference"}),
        ("init.tasks", {}),
        ("runs.list", {}),
    ):
        req = request(project, action, **options)
        argv, is_json = runtime.command_args(req, project)
        native = runtime.invoke_cli(argv, project)
        result = runtime.execute(req, cache_home=tmp_path / "cache")
        assert result.cli_exit_code == native.exit_code
        assert result.data == (json.loads(native.stdout) if is_json else native.stdout)


def test_preview_uses_saved_command_and_false_capture_without_experiment(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = {
        "schema_version": 1,
        "project": {"name": "preview"},
        "experiment": {"profiles": []},
        "execution": {"command": "python probe.py"},
    }
    (project / "reprollm.yaml").write_text(json.dumps(manifest))
    (project / ".reprollm").mkdir()
    (project / ".reprollm/config.yaml").write_text(
        "schema_version: 1\nrun:\n  capture_output: true\n"
    )
    before = {
        p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()
    }

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Preview must not execute an experiment, network or git")

    for target in (
        "reprollm.core.proc.run_cmd",
        "subprocess.Popen",
        "httpx.Client",
        "reprollm.cli.run.execute",
    ):
        monkeypatch.setattr(target, forbidden)
    default = runtime.execute(request(project, "run.preview"), cache_home=tmp_path / "cache")
    assert default.cli_exit_code == 0 and "Output capture: enabled" in default.data
    explicit = runtime.execute(
        request(project, "run.preview", capture_output=False), cache_home=tmp_path / "cache"
    )
    assert explicit.cli_exit_code == 0 and "Output capture: disabled" in explicit.data
    after = {
        p.relative_to(project).as_posix(): p.read_bytes() for p in project.rglob("*") if p.is_file()
    }
    assert before == after


def test_cursor_tamper_and_request_change_are_rejected(project: Path, tmp_path: Path) -> None:
    req = dataclasses.replace(request(project, "runs.list"), response=ResponseOptions(page_size=1))
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    assert first.snapshot and first.next_cursor
    cursor = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    changed = dataclasses.replace(cursor, options={"limit": 2})
    assert runtime.execute(changed, cache_home=tmp_path / "cache").invocation == "blocked"
    snapshot = tmp_path / "cache" / (first.snapshot + ".json")
    snapshot.write_bytes(snapshot.read_bytes() + b" ")
    assert runtime.execute(cursor, cache_home=tmp_path / "cache").invocation == "blocked"


def test_oversized_diagnostics_are_fully_retrievable(project: Path, tmp_path: Path) -> None:
    diagnostic = "ordinary diagnostic " * 20_000
    req = request(project)
    reply = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, json.dumps(report()), diagnostic),
    )
    fragments = []
    while True:
        assert len(encode_reply(reply)) <= 256 * 1024 and not reply.complete
        assert reply.data["scope"] == "partial_document"
        fragments.append(reply.data["text"])
        if not reply.next_cursor:
            break
        req = dataclasses.replace(req, response=ResponseOptions(cursor=reply.next_cursor))
        reply = runtime.execute(req, cache_home=tmp_path / "cache")
    restored = json.loads("".join(fragments))
    assert restored["diagnostics"][0]["text"] == diagnostic


def test_output_prewrite_race_preserves_editor_content(project: Path, tmp_path: Path) -> None:
    target = project / "report.json"
    target.write_text("initial")
    expected = hashlib.sha256(target.read_bytes()).hexdigest()
    req = dataclasses.replace(
        request(project, output="report.json"),
        grants=Grants(write=True, expected_hashes={"report.json": expected}),
    )

    def cli(*args: Any) -> runtime.CliResult:
        target.write_text("editor intervened")
        return runtime.CliResult(0, json.dumps(report()), "")

    reply = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    assert reply.invocation == "blocked" and target.read_text() == "editor intervened"


def test_actual_runs_and_recent_diff_keep_ids_and_full_high_drift(
    project: Path, tmp_path: Path
) -> None:
    from reprollm.schemas.run_record import CommandInfo, RunRecord, RunStatus

    records = []
    for index, cap in enumerate((32, 48), 1):
        row = RunRecord(
            reprollm_version="0.6.1",
            run_id=f"20261001T100000Z-{index:06x}",
            name="baseline",
            status=RunStatus.COMPLETED,
            exit_code=0,
            started_at=f"2026-10-01T10:00:0{index}Z",
            command=CommandInfo(argv=["python", "probe.py"], cwd="."),
            bindings_observed={
                "generation.max_new_tokens": [
                    {"value": cap, "source": {"type": "cli", "key": "--max-new-tokens"}}
                ]
            },
        )
        folder = project / ".reprollm/runs" / row.run_id
        folder.mkdir(parents=True)
        (folder / "run.json").write_text(row.model_dump_json(indent=2) + "\n")
        records.append(row)
    show = runtime.execute(
        request(project, "runs.show", run_id=records[0].run_id), cache_home=tmp_path / "cache"
    )
    assert show.complete and show.data == records[0].model_dump(mode="json")
    req = request(project, "diff", latest_successful=True, name="baseline", fail_on="HIGH")
    native = runtime.invoke_cli(runtime.command_args(req, project)[0], project)
    actual = runtime.execute(req, cache_home=tmp_path / "cache")
    assert actual.cli_exit_code == native.exit_code == 1 and actual.gate_failed
    assert actual.data == json.loads(native.stdout)
    assert actual.data["a"]["ref"] == records[0].run_id
    assert actual.data["b"]["ref"] == records[1].run_id
    change = next(x for x in actual.data["changes"] if x["path"] == "generation.max_new_tokens")
    assert (change["a"], change["b"], change["severity"]) == (32, 48, "HIGH")


def test_giant_record_after_small_records_still_has_a_full_fragment_view(
    project: Path, tmp_path: Path
) -> None:
    payload = report()
    payload["findings"] = [
        {"status": "skipped", "n": 0},
        {"status": "skipped", "long": "ordinary text " * 30_000},
    ]
    req = dataclasses.replace(request(project), response=ResponseOptions(page_size=1))
    reply = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, json.dumps(payload), ""),
    )
    fragments = []
    while True:
        assert reply.invocation == "handled_result" and reply.data["scope"] == "partial_document"
        fragments.append(reply.data["text"])
        if not reply.next_cursor:
            break
        req = dataclasses.replace(req, response=ResponseOptions(cursor=reply.next_cursor))
        reply = runtime.execute(req, cache_home=tmp_path / "cache")
    assert json.loads("".join(fragments))["data"] == payload


@pytest.mark.parametrize(
    "action,options",
    [
        ("profiles.show", {"name": "--help"}),
        ("runs.show", {"run_id": "--help"}),
        ("diff", {"a": "--help", "b": "missing"}),
    ],
)
def test_typed_positional_values_cannot_inject_cli_options(
    project: Path, tmp_path: Path, action: str, options: dict[str, Any]
) -> None:
    reply = runtime.execute(request(project, action, **options), cache_home=tmp_path / "cache")
    assert reply.invocation == "user_error" and reply.cli_exit_code == 2


def test_output_parent_replacement_is_refused(project: Path, tmp_path: Path) -> None:
    import shutil

    inside = project / "reports"
    inside.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    req = dataclasses.replace(
        request(project, output="reports/audit.json"),
        grants=Grants(write=True, expected_hashes={"reports/audit.json": None}),
    )

    def cli(*args: Any) -> runtime.CliResult:
        shutil.rmtree(inside)
        try:
            inside.symlink_to(outside, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
        return runtime.CliResult(0, json.dumps(report()), "")

    reply = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    assert reply.invocation == "blocked" and not (outside / "audit.json").exists()


def test_worktree_head_change_invalidates_cursor(project: Path, tmp_path: Path) -> None:
    metadata = tmp_path / "git-metadata"
    metadata.mkdir()
    (metadata / "HEAD").write_text("ref: refs/heads/main\n")
    (project / ".git").write_text("gitdir: " + str(metadata) + "\n")
    req = dataclasses.replace(request(project, "runs.list"), response=ResponseOptions(page_size=1))
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    (metadata / "HEAD").write_text("a" * 40 + "\n")
    req = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    result = runtime.execute(req, cache_home=tmp_path / "cache")
    assert result.invocation == "blocked" and not result.complete


def test_host_executor_keeps_request_on_stdin_and_uses_verified_isolated_python(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    import bootstrap

    calls = []

    class Manager(VerifiedManagerStub):
        current = {
            "state": "READY",
            "environment": "test-env",
            "capabilities": ["contextual_word_scan"],
        }

        def __init__(self, *args: Any) -> None:
            pass

        def ensure(self) -> dict[str, Any]:
            calls.append("ensure")
            return {"state": "READY", "environment": "test-env"}

        def status(self) -> dict[str, Any]:
            calls.append("status")
            return self.current

        def environment_path(self, name: str) -> Path:
            assert name == "test-env"
            return tmp_path / "verified-env"

    monkeypatch.setattr(bootstrap, "Bootstrap", Manager)

    def process(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(argv)
        assert argv[1:3] == ["-I", "-B"] and "--worker" in argv
        assert str(project) not in argv
        assert json.loads(kwargs["input"])["project"] == str(project)
        assert kwargs["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
        return subprocess.CompletedProcess(
            argv, 0, encode_reply(Reply("audit", data=report())) + b"\n", b""
        )

    monkeypatch.setattr(runtime.subprocess, "run", process)
    reply = runtime.RuntimeExecutor(tmp_path / "owned-tool")(request(project))
    assert reply.complete and reply.data == report() and calls[0] == "status"
    calls.clear()
    Manager.current = {"state": "NOT_INSTALLED"}
    req = dataclasses.replace(request(project), grants=Grants(install=False))
    denied = runtime.RuntimeExecutor(tmp_path / "owned-tool")(req)
    assert denied.invocation == "blocked" and calls == ["status"]


def test_doctor_no_color_selects_native_command_ascii_flag(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.cli import doctor

    monkeypatch.setattr(
        doctor,
        "run_checks",
        lambda *args, **kwargs: [{"name": "python", "status": "ok", "detail": "available"}],
    )
    native = runtime.invoke_cli(["doctor", "--no-color"], project)
    reply = runtime.execute(
        request(project, "doctor", json=False, no_color=True), cache_home=tmp_path / "cache"
    )
    assert reply.data == native.stdout and all(ord(c) < 128 for c in reply.data)


def test_expired_owned_snapshot_is_cleaned_but_foreign_files_are_preserved(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime.time, "time", lambda: 1000.0)
    req = dataclasses.replace(request(project, "runs.list"), response=ResponseOptions(page_size=1))
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    old = tmp_path / "cache" / (first.snapshot + ".json")
    unknown = tmp_path / "cache" / "user-notes.txt"
    unknown.write_text("preserve this")
    import os

    os.utime(old, (1000, 1000))
    monkeypatch.setattr(runtime.time, "time", lambda: 1000.0 + runtime.SNAPSHOT_TTL_SECONDS + 1)
    second = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    assert second.next_cursor and not old.exists() and unknown.read_text() == "preserve this"
    stale = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    assert runtime.execute(stale, cache_home=tmp_path / "cache").invocation == "blocked"


@pytest.mark.parametrize(
    "state,install,should_update,blocked",
    [
        ("compatible", True, False, False),
        ("incompatible", True, True, False),
        ("missing", True, True, False),
        ("invalid", True, True, False),
        ("incompatible", False, False, True),
        ("missing", False, False, True),
        ("invalid", False, False, True),
    ],
)
def test_install_authority_prepares_required_capability_without_upgrading_compatible_tools(
    project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    install: bool,
    should_update: bool,
    blocked: bool,
) -> None:
    import subprocess

    import bootstrap
    import install_catalog

    original = install_catalog.load_catalog(SCRIPTS.parent / "assets/install-catalog.json")
    # Hypothetical verified capabilities at the manager boundary, not a public candidate claim.
    candidate = dataclasses.replace(
        original.get_candidate(), id="mock-compatible", capabilities=("contextual_word_scan",)
    )
    catalog = install_catalog.Catalog(1, candidate.id, (candidate,))
    monkeypatch.setattr(install_catalog, "load_catalog", lambda _: catalog)
    calls = []

    class Manager(VerifiedManagerStub):
        def __init__(self, *args: Any) -> None:
            pass

        def status(self) -> dict[str, Any]:
            calls.append("status")
            if state == "invalid":
                raise bootstrap.BootstrapError("private synthetic invalid state")
            return (
                {"state": "NOT_INSTALLED"}
                if state == "missing"
                else {
                    "state": "READY",
                    "environment": "owned",
                    "capabilities": ["contextual_word_scan"] if state == "compatible" else [],
                }
            )

        def ensure(self) -> None:
            pytest.fail("Compatible installed tools must not be silently upgraded or reinstalled")

        def update(self, candidate_id: str) -> dict[str, Any]:
            calls.append("update")
            assert candidate_id == candidate.id
            return {
                "state": "READY",
                "environment": "owned",
                "capabilities": ["contextual_word_scan"],
            }

        def environment_path(self, name: str) -> Path:
            return tmp_path / name

    monkeypatch.setattr(bootstrap, "Bootstrap", Manager)

    def process(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append("worker")
        return subprocess.CompletedProcess(
            argv, 0, encode_reply(Reply("audit", data=report())) + b"\n", b""
        )

    monkeypatch.setattr(runtime.subprocess, "run", process)
    req = dataclasses.replace(request(project), grants=Grants(install=install))
    reply = runtime.RuntimeExecutor(tmp_path / "owned-home")(req)
    assert ("update" in calls) is should_update
    assert (reply.invocation == "blocked") is blocked
    assert reply.needs_authorization is blocked
    assert ("worker" in calls) is not blocked


@pytest.mark.parametrize("username", ["audit", "data", "rule_id", "handled_result", "code"])
def test_machine_identity_cannot_rewrite_fixed_frames_or_native_schema_symbols(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, username: str
) -> None:
    monkeypatch.setattr(runtime.getpass, "getuser", lambda: username)
    payload = report()
    payload["findings"][0]["rule_id"] = "code.git_repo"
    reply = run(project, tmp_path, payload)
    assert reply.action == "audit" and reply.invocation == "handled_result"
    assert reply.data["findings"][0]["rule_id"] == "code.git_repo"
    assert reply.data["summary"] == payload["summary"]


def test_display_key_collisions_preserve_members_and_original_secret_context(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime.getpass, "getuser", lambda: "private-person")
    canary = "NoProviderPrefixCanaryValue123"
    payload = {
        "private-person": {"api_key": canary, "text": "ordinary text " * 30_000},
        "<REDACTED:username>": {"password": canary + "two", "control": "\x01"},
    }
    req = request(project)
    reply = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, json.dumps(payload), ""),
    )
    pieces = []
    while True:
        assert len(encode_reply(reply)) <= 256 * 1024 and canary not in encode_reply(reply).decode()
        pieces.append(reply.data["text"])
        if not reply.next_cursor:
            break
        req = dataclasses.replace(req, response=ResponseOptions(cursor=reply.next_cursor))
        reply = runtime.execute(req, cache_home=tmp_path / "cache")
    restored = json.loads("".join(pieces))
    assert len(restored["data"]) == 2
    assert any(x["code"] == "display_keys_disambiguated" for x in restored["diagnostics"])
    assert canary not in json.dumps(restored) and "\x01" not in json.dumps(restored)


def test_canonical_project_identity_is_not_inferred_from_identical_relative_trees(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os
    import shutil

    left = tmp_path / "left"
    right = tmp_path / "right"
    (left / "project").mkdir(parents=True)
    (left / "project/input.json").write_text('{"same":true}')
    shutil.copytree(left, right, copy_function=shutil.copy2)
    monkeypatch.chdir(left)
    req = parse_request(
        {
            "schema_version": 1,
            "action": "runs.list",
            "project": "project",
            "response": {"page_size": 1},
        }
    )
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    os.chdir(right)
    req = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    other = runtime.execute(
        req, cache_home=tmp_path / "cache", cli_runner=lambda *_: pytest.fail("No second CLI")
    )
    assert other.invocation == "blocked" and other.data is None


def test_sanitized_result_budget_is_checked_before_advertising_a_cursor(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "MAX_CAPTURE_BYTES", 65536)
    reply = runtime.execute(
        request(project),
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, json.dumps(report()), "\x01" * 60000),
    )
    assert reply.invocation == "blocked" and not reply.complete and reply.next_cursor is None
    assert any(x["code"] == "sanitized_result_limit" for x in reply.diagnostics)


def test_supported_control_character_diagnostics_reconstruct_under_scaled_budgets(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "MAX_CAPTURE_BYTES", 65536)
    monkeypatch.setattr(runtime, "MAX_REPLY_BYTES", 32768)
    req = request(project)
    reply = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, json.dumps(report()), "\x01" * 10000),
    )
    pieces = []
    while True:
        assert reply.invocation == "handled_result" and len(encode_reply(reply)) + 1 <= 32768
        pieces.append(reply.data["text"])
        if not reply.next_cursor:
            break
        req = dataclasses.replace(req, response=ResponseOptions(cursor=reply.next_cursor))
        reply = runtime.execute(req, cache_home=tmp_path / "cache")
    restored = json.loads("".join(pieces))
    assert restored["diagnostics"][0]["text"] == "\\u0001" * 10000


@pytest.mark.parametrize(
    "kind", ["lock_existing", "lock_created", "run_snapshot", "internal_symlink"]
)
def test_native_diff_consumed_sidecars_invalidate_cursor(
    project: Path, tmp_path: Path, kind: str
) -> None:
    import shutil

    from reprollm.schemas.run_record import CommandInfo, DocumentRef, RunRecord, RunStatus

    outside = tmp_path / "inputs"
    outside.mkdir()
    pairs = []
    target = None
    for label, n in [("A", 1), ("B", 2)]:
        folder = (project if kind == "internal_symlink" else outside) / label
        folder.mkdir()
        body = {
            "schema_version": 1,
            "project": {"name": "sidecars"},
            "experiment": {"profiles": []},
            "custom": {"one": n, "two": n, "three": n},
        }
        manifest = folder / "reprollm.yaml"
        if kind == "internal_symlink":
            (folder / ".venv").mkdir()
            real = folder / ".venv/source.yaml"
            real.write_text(json.dumps(body))
            try:
                manifest.symlink_to(real)
            except OSError:
                pytest.skip("symlinks unavailable")
            if label == "A":
                target = real
        elif not (kind == "lock_created" and label == "A"):
            manifest.write_text(json.dumps(body))
        if label == "A" and target is None:
            target = manifest
        if kind.startswith("lock"):
            source = folder / "reprollm.lock"
            shutil.copyfile(SCRIPTS.parents[2] / "examples/hf_vllm_eval/reprollm.lock", source)
        else:
            source = folder / "run.json"
            record = RunRecord(
                reprollm_version="0.6.1",
                run_id="20260101T000000Z-aabbcc",
                status=RunStatus.COMPLETED,
                exit_code=0,
                command=CommandInfo(argv=["python"], cwd="."),
                manifest=DocumentRef(
                    path="reprollm.yaml",
                    snapshot="reprollm.yaml",
                    sha256="sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest(),
                ),
            )
            source.write_text(record.model_dump_json())
        pairs.append(source)
    req = request(project, "diff", a=str(pairs[0]), b=str(pairs[1]))
    req = dataclasses.replace(
        req,
        grants=Grants(
            external_paths=tuple(str(x) for x in pairs) if kind != "internal_symlink" else ()
        ),
        response=ResponseOptions(page_size=1),
    )
    first = runtime.execute(req, cache_home=tmp_path / "cache")
    assert first.invocation == "handled_result" and first.next_cursor, (
        first.diagnostics,
        first.data,
    )
    assert target is not None
    body = {
        "schema_version": 1,
        "project": {"name": "sidecars"},
        "experiment": {"profiles": []},
        "custom": {"one": 3, "two": 3, "three": 3},
    }
    target.write_text(json.dumps(body))
    req = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    stale = runtime.execute(req, cache_home=tmp_path / "cache")
    assert stale.invocation == "blocked" and not stale.complete


@pytest.mark.parametrize("worker_exit,cli_exit", [(9, 0), (-9, 1), (0, 1), (0, 2), (0, 3)])
def test_worker_process_status_is_separate_from_valid_cli_reply(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, worker_exit: int, cli_exit: int
) -> None:
    import subprocess

    import bootstrap

    class Manager(VerifiedManagerStub):
        def __init__(self, *args: Any) -> None:
            pass

        def status(self) -> dict[str, Any]:
            return {
                "state": "READY",
                "environment": "owned",
                "capabilities": ["contextual_word_scan"],
            }

        def environment_path(self, name: str) -> Path:
            return tmp_path / name

    monkeypatch.setattr(bootstrap, "Bootstrap", Manager)
    frame = Reply(
        "audit",
        cli_exit_code=cli_exit,
        gate_failed=cli_exit == 1 if cli_exit < 2 else None,
        invocation="handled_result"
        if cli_exit < 2
        else "user_error"
        if cli_exit == 2
        else "internal_error",
        complete=cli_exit < 2,
        data=report() if cli_exit < 2 else None,
    )
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(
            argv, worker_exit, encode_reply(frame) + b"\n", b""
        ),
    )
    reply = runtime.RuntimeExecutor(tmp_path / "owned")(request(project))
    assert reply.cli_exit_code == cli_exit and reply.child_exit_code is None
    if worker_exit:
        assert (
            reply.invocation == "internal_error"
            and not reply.complete
            and reply.next_cursor is None
        )
        assert any(
            d.get("code") == "runtime_worker_exit" and d.get("worker_exit_code") == worker_exit
            for d in reply.diagnostics
        )
    else:
        assert reply.invocation == frame.invocation and reply.gate_failed == frame.gate_failed


@pytest.mark.parametrize("extra,expected_exit", [(0, 0), (1, 2)])
def test_actual_entry_lf_is_inside_the_exact_reply_budget(
    monkeypatch: pytest.MonkeyPatch, extra: int, expected_exit: int
) -> None:
    import io

    import reprollm_skill as entry
    import skill_request

    base = Reply("audit", data="")
    available = skill_request.MAX_REPLY_BYTES - 1 - len(encode_reply(base))
    reply = dataclasses.replace(base, data="x" * (available + extra))
    source = io.TextIOWrapper(io.BytesIO(b"{}"))
    output = io.BytesIO()
    target = io.TextIOWrapper(output)
    monkeypatch.setattr(entry.sys, "stdin", source)
    monkeypatch.setattr(entry.sys, "stdout", target)
    monkeypatch.setattr(entry, "handle", lambda *args, **kwargs: reply)
    assert entry.main([]) == expected_exit
    target.flush()
    wire = output.getvalue()
    assert wire.endswith(b"\n") and len(wire) <= skill_request.MAX_REPLY_BYTES
    if not extra:
        assert len(wire) == skill_request.MAX_REPLY_BYTES
    else:
        assert json.loads(wire)["invocation"] == "blocked"


@pytest.mark.parametrize("username", ["path", "snapshot", "present"])
def test_nullable_native_metadata_keeps_its_schema_fields(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, username: str
) -> None:
    monkeypatch.setattr(runtime.getpass, "getuser", lambda: username)
    payload = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": "20260101T000000Z-aabbcc",
        "status": "completed",
        "command": {"argv": ["python"], "cwd": "."},
        "manifest": {
            "path": "reprollm.yaml",
            "snapshot": "manifest.yaml",
            "sha256": "sha256:" + "0" * 64,
        },
        "environment": {
            "os": "test",
            "platform": "linux",
            "python": "3.12",
            "hostname_sha256": "0" * 64,
            "env": {"HF_TOKEN": {"present": True}},
        },
    }
    reply = run(project, tmp_path, payload, action="runs.show", run_id="20260101")
    assert reply.invocation == "handled_result" and set(reply.data["manifest"]) == {
        "path",
        "snapshot",
        "sha256",
    }
    assert reply.data["environment"]["env"]["HF_TOKEN"] == {"present": True}


def test_explicit_project_alias_stays_bound_to_its_canonical_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import shutil

    first = tmp_path / "first"
    first.mkdir()
    (first / "config.json").write_text('{"same":true}')
    second = tmp_path / "second"
    shutil.copytree(first, second, copy_function=shutil.copy2)
    alias = tmp_path / "explicit-alias"
    try:
        alias.symlink_to(first, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    req = dataclasses.replace(request(alias, "runs.list"), response=ResponseOptions(page_size=1))
    page = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    cursor = dataclasses.replace(req, response=ResponseOptions(cursor=page.next_cursor))
    assert runtime.execute(cursor, cache_home=tmp_path / "cache").invocation == "handled_result"
    alias.unlink()
    alias.symlink_to(second, target_is_directory=True)
    assert runtime.execute(cursor, cache_home=tmp_path / "cache").invocation == "blocked"


def test_external_alias_target_change_is_not_hidden_by_identical_file_contents(
    project: Path, tmp_path: Path
) -> None:
    import shutil

    left = tmp_path / "left.lock"
    right = tmp_path / "right.lock"
    left.write_text("identical")
    shutil.copy2(left, right)
    alias = tmp_path / "external.lock"
    try:
        alias.symlink_to(left)
    except OSError:
        pytest.skip("file symlinks unavailable")
    req = request(project, "diff", a=str(alias), b="missing")
    req = dataclasses.replace(
        req, grants=Grants(external_paths=(str(alias),)), response=ResponseOptions(page_size=1)
    )
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        cli_runner=lambda *_: runtime.CliResult(0, '{"changes":[1,2,3]}', ""),
    )
    alias.unlink()
    alias.symlink_to(right)
    req = dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor))
    assert runtime.execute(req, cache_home=tmp_path / "cache").invocation == "blocked"


@pytest.mark.parametrize(
    "field,source_key,value,source_path",
    [
        ("custom.beta", "--api-key", "NoPrefixHistoricalCanary12345", None),
        (
            "custom.password",
            "credentials.password",
            "<REDACTED:generic_kv>",
            "configs/options.yaml",
        ),
        (
            "custom.password",
            "credentials.password",
            "<REDACTED:generic_kv>",
            "configs/sk-proj-SyntheticDescriptorSecret123456789.yaml",
        ),
    ],
)
def test_native_observation_reuses_dynamic_value_context_and_separate_descriptors(
    project: Path,
    tmp_path: Path,
    field: str,
    source_key: str,
    value: str,
    source_path: str | None,
) -> None:
    from reprollm.schemas.run_record import CommandInfo, RunRecord, RunStatus

    record = RunRecord(
        reprollm_version="0.6.1",
        run_id="20260101T000000Z-aabbcc",
        status=RunStatus.COMPLETED,
        exit_code=0,
        command=CommandInfo(argv=["python"], cwd="."),
        bindings_observed={
            field: [
                {
                    "value": value,
                    "source": {
                        "type": "config" if source_path else "cli",
                        "key": source_key,
                        "path": source_path,
                    },
                }
            ]
        },
    )
    folder = project / ".reprollm/runs" / record.run_id
    folder.mkdir(parents=True)
    source = folder / "run.json"
    original = record.model_dump_json(indent=2) + "\n"
    source.write_text(original)
    native = runtime.invoke_cli(["runs", "show", record.run_id, "--json"], project)
    assert json.loads(native.stdout)["bindings_observed"][field][0]["value"] == value
    reply = runtime.execute(
        request(project, "runs.show", run_id=record.run_id), cache_home=tmp_path / "cache"
    )
    observation = reply.data["bindings_observed"][field][0]
    assert observation["value"] == "<REDACTED:generic_kv>"
    assert observation["source"]["key"] == source_key
    if source_path and "sk-proj-" not in source_path:
        assert observation["source"]["path"] == source_path
    if source_path and "sk-proj-" in source_path:
        assert "SyntheticDescriptorSecret" not in json.dumps(reply.as_dict())
    assert source.read_text() == original
    assert "NoPrefixHistoricalCanary" not in json.dumps(reply.as_dict())


@pytest.mark.parametrize("path_present", [False, True])
@pytest.mark.parametrize("private_value", [False, True])
def test_native_observation_preserves_omitted_and_explicit_null_source_path(
    project: Path, tmp_path: Path, path_present: bool, private_value: bool
) -> None:
    from reprollm.schemas.run_record import RunRecord

    run_id = "20260101T000000Z-aabbcc"
    canary = "HistoricalOptionalSourceCanary12345"
    source: dict[str, Any] = {
        "type": "cli",
        "key": "--api-key" if private_value else "--alpha",
    }
    if path_present:
        source["path"] = None
    payload = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": run_id,
        "status": "completed",
        "exit_code": 0,
        "command": {"argv": ["python"], "cwd": "."},
        "bindings_observed": {"custom.alpha": [{"value": canary, "source": source}]},
    }
    RunRecord.model_validate(payload)
    folder = project / ".reprollm/runs" / run_id
    folder.mkdir(parents=True)
    record_path = folder / "run.json"
    original = json.dumps(payload) + "\n"
    record_path.write_text(original)
    native = runtime.invoke_cli(["runs", "show", run_id, "--json"], project)
    assert native.exit_code == 0
    native_observation = json.loads(native.stdout)["bindings_observed"]["custom.alpha"][0]
    assert native_observation == {"value": canary, "source": source}
    reply = runtime.execute(
        request(project, "runs.show", run_id=run_id), cache_home=tmp_path / "cache"
    )
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0
    shown = reply.data["bindings_observed"]["custom.alpha"][0]
    assert shown["source"] == native_observation["source"]
    assert shown["value"] == ("<REDACTED:generic_kv>" if private_value else canary)
    assert record_path.read_text() == original


def _legacy_display_input(
    project: Path,
    argv: list[str],
    bindings: dict[str, Any],
    environment: dict[str, Any] | None = None,
    run_id: str = "20260101T000000Z-aabbcc",
) -> tuple[str, Path, str]:
    from reprollm.schemas.run_record import RunRecord

    payload: dict[str, Any] = {
        "schema_version": 1,
        "reprollm_version": "0.6.1",
        "run_id": run_id,
        "status": "completed",
        "exit_code": 0,
        "command": {"argv": argv, "cwd": ".", "redactions": 0},
        "bindings_observed": bindings,
    }
    if environment is not None:
        payload["environment"] = {
            "os": "test",
            "platform": "linux",
            "python": "3.12",
            "hostname_sha256": "0" * 64,
            "env": environment,
        }
    RunRecord.model_validate(payload)
    folder = project / ".reprollm/runs" / run_id
    folder.mkdir(parents=True)
    record_path = folder / "run.json"
    original = json.dumps(payload) + "\n"
    record_path.write_text(original)
    return run_id, record_path, original


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize(
    "source_type,source_key",
    [
        ("cli", "--api-key"),
        ("config", "credentials.password"),
        ("env", "HF_TOKEN"),
        ("env", "OPENAI_API_KEY"),
        ("env", "PRIVATE_API_KEY"),
    ],
)
def test_native_historical_display_masks_typed_sources_in_both_formats(
    project: Path, tmp_path: Path, as_json: bool, source_type: str, source_key: str
) -> None:
    canary = "HistoricalBothFormatsCanary12345"
    source = {"type": source_type, "key": source_key}
    run_id, record_path, original = _legacy_display_input(
        project,
        ["python", "eval.py"],
        {"custom.alpha": [{"value": canary, "source": source}]},
    )
    native = runtime.invoke_cli(
        ["runs", "show", *(["--json"] if as_json else []), "--", run_id], project
    )
    assert native.exit_code == 0 and canary in native.stdout
    reply = runtime.execute(
        request(project, "runs.show", run_id=run_id, json=as_json), cache_home=tmp_path / "cache"
    )
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0 and reply.complete
    assert canary not in json.dumps(reply.as_dict())
    assert "<REDACTED:generic_kv>" in json.dumps(reply.data)
    if as_json:
        assert reply.data["bindings_observed"]["custom.alpha"][0]["source"] == source
        assert reply.data["command"]["redactions"] == 0
    assert any(item["code"] == "display_value_transformation" for item in reply.diagnostics)
    assert record_path.read_text() == original


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("inline", [False, True])
def test_native_historical_display_masks_argv_with_original_flag_context(
    project: Path, tmp_path: Path, as_json: bool, inline: bool
) -> None:
    canary = "HistoricalArgvBothFormatsCanary12345"
    args = ["--api-key=" + canary] if inline else ["--api-key", canary]
    run_id, record_path, original = _legacy_display_input(project, ["python", "eval.py", *args], {})
    native = runtime.invoke_cli(
        ["runs", "show", *(["--json"] if as_json else []), "--", run_id], project
    )
    assert native.exit_code == 0 and canary in native.stdout
    reply = runtime.execute(
        request(project, "runs.show", run_id=run_id, json=as_json), cache_home=tmp_path / "cache"
    )
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 0 and reply.complete
    assert canary not in json.dumps(reply.as_dict())
    assert "<REDACTED:generic_kv>" in json.dumps(reply.data)
    if as_json:
        assert reply.data["command"]["redactions"] == 0
    assert record_path.read_text() == original


def test_historical_environment_string_is_private_and_presence_metadata_is_preserved(
    project: Path, tmp_path: Path
) -> None:
    canary = "HistoricalEnvironmentStringCanary12345"
    run_id, record_path, original = _legacy_display_input(
        project,
        ["python"],
        {},
        {"HF_TOKEN": canary, "OPENAI_API_KEY": {"present": True}, "LANG": "C.UTF-8"},
    )
    reply = runtime.execute(
        request(project, "runs.show", run_id=run_id), cache_home=tmp_path / "cache"
    )
    assert reply.invocation == "handled_result" and reply.complete
    assert reply.data["environment"]["env"] == {
        "HF_TOKEN": "<REDACTED:generic_kv>",
        "OPENAI_API_KEY": {"present": True},
        "LANG": "C.UTF-8",
    }
    assert canary not in json.dumps(reply.as_dict())
    assert record_path.read_text() == original


def test_public_historical_text_keeps_native_format_and_saved_counts(
    project: Path, tmp_path: Path
) -> None:
    run_id, record_path, original = _legacy_display_input(
        project,
        ["python", "eval.py", "--alpha", "public-value", ""],
        {"custom.alpha": [{"value": 0, "source": {"type": "cli", "key": "--alpha"}}]},
    )
    native = runtime.invoke_cli(["runs", "show", "--", run_id], project)
    reply = runtime.execute(
        request(project, "runs.show", run_id=run_id, json=False), cache_home=tmp_path / "cache"
    )
    assert native.exit_code == reply.cli_exit_code == 0
    assert reply.data == native.stdout and reply.diagnostics == [] and reply.complete
    assert record_path.read_text() == original


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("latest", [False, True])
def test_native_diff_preserves_raw_drift_and_projects_each_private_source(
    project: Path, tmp_path: Path, as_json: bool, latest: bool
) -> None:
    from reprollm.reporters.diff_text import render_diff_text
    from reprollm.schemas.diff_report import DiffReport

    records = []
    for maximum, suffix, run_id in [
        (32, "Before", "20260101T000000Z-aabbcc"),
        (48, "After", "20260101T010000Z-ddeeff"),
    ]:
        opaque = "HistoricalDiffSourceCanary" + suffix
        records.append(
            _legacy_display_input(
                project,
                ["python", "eval.py", "--api-key", "HistoricalDiffArgv" + suffix],
                {
                    "custom.alpha": [
                        {"value": opaque, "source": {"type": "cli", "key": "--api-key"}}
                    ],
                    "custom.beta": [{"value": opaque, "source": {"type": "cli", "key": "--beta"}}],
                    "generation.max_tokens": [
                        {"value": maximum, "source": {"type": "cli", "key": "--max-tokens"}}
                    ],
                },
                run_id=run_id,
            )
        )
    selection = ["--latest-successful"] if latest else ["--", records[0][0], records[1][0]]
    native = runtime.invoke_cli(
        ["diff", "--format", "json", "--fail-on", "HIGH", *selection], project
    )
    assert native.exit_code == 1
    expected = json.loads(native.stdout)
    assert expected["summary"]["highest"] == "HIGH"
    for change in expected["changes"]:
        if change["path"] == "custom.alpha":
            change["a"] = change["b"] = "<REDACTED:generic_kv>"
        if change["path"] == "command.argv":
            change["a"][3] = change["b"][3] = "<REDACTED:generic_kv>"
    options: dict[str, Any] = {"format": "json" if as_json else "text", "fail_on": "HIGH"}
    if latest:
        options["latest_successful"] = True
    else:
        options.update(a=records[0][0], b=records[1][0])
    reply = runtime.execute(request(project, "diff", **options), cache_home=tmp_path / "cache")
    assert reply.invocation == "handled_result" and reply.cli_exit_code == 1
    assert reply.gate_failed is True and reply.complete
    if as_json:
        assert reply.data == expected
    else:
        assert reply.data == render_diff_text(DiffReport.model_validate(expected))
    assert "HistoricalDiffArgv" not in json.dumps(reply.as_dict())
    assert "HistoricalDiffSourceCanaryBefore" in json.dumps(reply.data)
    assert "HistoricalDiffSourceCanaryAfter" in json.dumps(reply.data)
    for _, path, original in records:
        assert path.read_text() == original


def test_changed_trusted_sibling_invalidates_old_cursor_without_rerunning_cli(
    project: Path, tmp_path: Path
) -> None:
    helper = tmp_path / "trusted-helpers"
    helper.mkdir()
    (helper / "entry.py").write_text("pass\n")
    sibling = helper / "private_display.py"
    sibling.write_text("VERSION = 1\n")
    before = runtime.helper_code_identity(helper)
    req = dataclasses.replace(request(project, "runs.list"), response=ResponseOptions(page_size=1))
    first = runtime.execute(
        req,
        cache_home=tmp_path / "cache",
        identity=before,
        cli_runner=lambda *_: runtime.CliResult(0, "[1,2,3]", ""),
    )
    assert first.next_cursor
    sibling.write_text("VERSION = 2\n")
    after = runtime.helper_code_identity(helper)
    assert before != after
    resumed = runtime.execute(
        dataclasses.replace(req, response=ResponseOptions(cursor=first.next_cursor)),
        cache_home=tmp_path / "cache",
        identity=after,
        cli_runner=lambda *_: pytest.fail("Changed helper must not replay the CLI"),
    )
    assert resumed.invocation == "blocked" and not resumed.complete and not resumed.next_cursor


@pytest.mark.parametrize("sink", ["json", "text", "github", "file"])
def test_native_audit_keeps_findings_but_projects_sensitive_runtime_evidence(
    project: Path, tmp_path: Path, sink: str
) -> None:
    canary = "HistoricalAuditRuntimeCanary12345"
    _, record_path, original = _legacy_display_input(
        project,
        ["python", "eval.py"],
        {"custom.alpha": [{"value": canary, "source": {"type": "cli", "key": "--api-key"}}]},
    )
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: public-audit}\n"
        "experiment: {profiles: []}\ncustom: {alpha: declared-public}\n"
    )
    (project / ".reprollm/project-rules.yaml").write_text(
        "schema_version: 1\nrules:\n  - id: project.alpha\n    field: custom.alpha\n"
        "    severity: WARNING\n    reason: Public reviewed synthetic binding\n"
        "    source: manual\n    accepted_at: '2026-10-30T00:00:00Z'\n"
        "    bindings: {cli: --alpha}\n"
    )
    native = runtime.invoke_cli(
        ["audit", str(project), "--level", "2", "--format", "json", "--fail-on", "warning"],
        project,
    )
    assert native.exit_code == 1 and canary in native.stdout
    expected = json.loads(native.stdout)
    expected.pop("generated_at")
    options: dict[str, Any] = {
        "format": "json" if sink == "file" else sink,
        "level": "2",
        "fail_on": "warning",
    }
    req = request(project, **options)
    target = project / "report.json"
    if sink == "file":
        req = dataclasses.replace(
            request(project, output="report.json", **options),
            grants=Grants(write=True, expected_hashes={"report.json": None}),
        )
    result = runtime.execute(req, cache_home=tmp_path / "cache")
    assert result.invocation == "handled_result" and result.cli_exit_code == native.exit_code
    assert result.gate_failed is True and result.complete
    assert canary not in json.dumps(result.as_dict())
    assert any(item["code"] == "display_value_transformation" for item in result.diagnostics)
    if sink in {"json", "file"}:
        actual = json.loads(target.read_bytes()) if sink == "file" else result.data
        assert canary not in json.dumps(actual)
        actual.pop("generated_at")
        assert actual["summary"] == expected["summary"]
        for before, after in zip(expected["findings"], actual["findings"], strict=True):
            assert {k: v for k, v in before.items() if k not in {"message", "evidence"}} == {
                k: v for k, v in after.items() if k not in {"message", "evidence"}
            }
        observed = next(
            item for item in actual["findings"] if item["rule_id"] == "consistency.custom_fields"
        )
        assert (
            observed["status"] == "fail" and observed["evidence"][0]["value"] == "declared-public"
        )
        assert observed["evidence"][1]["value"] == "<REDACTED:generic_kv>"
    assert record_path.read_text() == original


def test_trusted_helper_identity_is_order_independent_and_refuses_symlink_reads(
    tmp_path: Path,
) -> None:
    helper = tmp_path / "trusted-helpers"
    helper.mkdir()
    first = helper / "b.py"
    first.write_text("B = 1\n")
    (helper / "a.py").write_text("A = 1\n")
    original = runtime.helper_code_identity(helper)
    first.unlink()
    first.write_text("B = 1\n")
    (helper / "notes.txt").write_text("not executable helper input\n")
    assert runtime.helper_code_identity(helper) == original
    outside = tmp_path / "private-data.txt"
    outside.write_text("must not be read\n")
    try:
        (helper / "escaped.py").symlink_to(outside)
    except OSError:
        pytest.skip("file symlinks unavailable")
    with pytest.raises(runtime.ScopeError, match="trusted_helper_symlink_refused"):
        runtime.helper_code_identity(helper)


def test_freeform_value_source_shape_never_gets_native_observation_privilege(
    project: Path, tmp_path: Path
) -> None:
    canary = "UnprefixedFreeformCanary123456"
    payload = report()
    payload["findings"][0]["evidence"] = [
        {
            "kind": "field",
            "value": {
                "api_key": {
                    "value": "ordinary",
                    "source": {"type": "config", "key": "ordinary", "path": canary},
                }
            },
        }
    ]
    reply = run(project, tmp_path, payload)
    assert canary not in json.dumps(reply.as_dict())
    assert reply.complete


def test_maximum_worker_reply_failure_keeps_known_facts_inside_final_wire(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    import bootstrap
    import skill_request

    class Manager(VerifiedManagerStub):
        def __init__(self, *args: Any) -> None:
            pass

        def status(self) -> dict[str, Any]:
            return {
                "state": "READY",
                "environment": "owned",
                "capabilities": ["contextual_word_scan"],
            }

        def environment_path(self, name: str) -> Path:
            return tmp_path / name

    monkeypatch.setattr(bootstrap, "Bootstrap", Manager)
    base = Reply("audit", cli_exit_code=1, gate_failed=True, complete=True, data="")
    amount = skill_request.MAX_REPLY_BYTES - 1 - len(encode_reply(base))
    frame = dataclasses.replace(base, data="x" * amount)
    encoded = encode_reply(frame) + b"\n"
    assert len(encoded) == skill_request.MAX_REPLY_BYTES
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda argv, **kwargs: subprocess.CompletedProcess(argv, 9, encoded, b""),
    )
    reply = runtime.RuntimeExecutor(tmp_path / "owned")(request(project))
    final = encode_reply(reply) + b"\n"
    result = json.loads(final)
    assert len(final) <= skill_request.MAX_REPLY_BYTES
    assert result["invocation"] == "internal_error" and not result["complete"]
    assert (
        result["action"] == "audit"
        and result["cli_exit_code"] == 1
        and result["gate_failed"] is True
    )
    assert result["child_exit_code"] is None and result["next_cursor"] is None
    assert any(
        x.get("code") == "runtime_worker_exit" and x.get("worker_exit_code") == 9
        for x in result["diagnostics"]
    )


def test_budget_fallback_bounds_repeated_worker_diagnostics() -> None:
    import skill_request

    reply = Reply(
        "audit",
        invocation="internal_error",
        cli_exit_code=1,
        gate_failed=True,
        complete=False,
        diagnostics=[{"code": "runtime_worker_exit", "worker_exit_code": i} for i in range(20000)],
    )
    raw = encode_reply(reply) + b"\n"
    final = json.loads(raw)
    assert len(raw) <= skill_request.MAX_REPLY_BYTES
    assert final["invocation"] == "internal_error" and final["cli_exit_code"] == 1
    assert final["gate_failed"] is True and not final["complete"]
    facts = [d for d in final["diagnostics"] if d["code"] == "runtime_worker_exit"]
    assert facts == [{"code": "runtime_worker_exit", "worker_exit_code": 19999}]
    assert final["diagnostics"][0]["diagnostics_omitted"] == 19999


@pytest.mark.parametrize("failure", [None, "launch", "timeout"])
def test_worker_lease_preserves_environment_during_uninstall_and_releases_only_itself(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    import subprocess

    import bootstrap
    import install_catalog
    from tests.unit.skills.test_bootstrap import FakeBackend, candidate, source_blob

    blob = source_blob()
    selected = dataclasses.replace(
        candidate("lease-candidate", blob), capabilities=("contextual_word_scan",)
    )
    catalog = install_catalog.Catalog(1, selected.id, (selected,))
    manager = bootstrap.Bootstrap(tmp_path / "owned-home", catalog, backend=FakeBackend(blob))
    ready = manager.ensure()
    environment = manager.environment_path(ready["environment"])
    monkeypatch.setattr(bootstrap, "Bootstrap", lambda *args: manager)
    monkeypatch.setattr(install_catalog, "load_catalog", lambda _: catalog)
    observed: list[Path] = []

    def process(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        leases = list((environment / "leases").iterdir())
        assert len(leases) == 1 and leases[0].is_file()
        descriptor = json.loads(leases[0].read_bytes())
        assert descriptor["schema_version"] == 1 and descriptor["lease_id"] == leases[0].stem
        assert str(tmp_path) not in json.dumps(descriptor)
        observed.extend(leases)
        if failure == "launch":
            raise OSError("synthetic launch failure")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(argv, 120)
        (environment / "leases" / "foreign.json").write_text('{"owner":"another-worker"}')
        assert manager.uninstall()["state"] == "NOT_INSTALLED"
        assert environment.is_dir() and leases[0].is_file()
        return subprocess.CompletedProcess(
            argv, 0, encode_reply(Reply("audit", data=report())), b""
        )

    monkeypatch.setattr(runtime.subprocess, "run", process)
    result = runtime.RuntimeExecutor(manager.home)(request(project))
    assert observed and not observed[0].exists()
    assert environment.is_dir()
    if failure is not None:
        assert result.invocation == "blocked"
        assert not (environment / "leases").exists()
        assert manager.status()["state"] == "READY"
    else:
        assert result.complete and result.data == report()
        assert (environment / "leases" / "foreign.json").read_text() == '{"owner":"another-worker"}'
        assert manager.status()["state"] == "NOT_INSTALLED"


def test_worker_reverifies_environment_under_installer_lock_before_launch(
    project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import bootstrap
    import install_catalog
    from tests.unit.skills.test_bootstrap import FakeBackend, candidate, source_blob

    blob = source_blob()
    selected = dataclasses.replace(
        candidate("lease-race", blob), capabilities=("contextual_word_scan",)
    )
    catalog = install_catalog.Catalog(1, selected.id, (selected,))
    manager = bootstrap.Bootstrap(tmp_path / "owned-home", catalog, backend=FakeBackend(blob))
    ready = manager.ensure()

    def stale_status() -> dict[str, Any]:
        manager.uninstall()
        return ready

    monkeypatch.setattr(manager, "status", stale_status)
    monkeypatch.setattr(bootstrap, "Bootstrap", lambda *args: manager)
    monkeypatch.setattr(install_catalog, "load_catalog", lambda _: catalog)
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("removed environment must not launch"),
    )
    result = runtime.RuntimeExecutor(manager.home)(request(project))
    assert result.invocation == "blocked" and not result.complete


@pytest.mark.parametrize("binding", ["declared-new", "declared-existing", "expected", "external"])
def test_report_rechecks_declared_and_authorization_path_mappings_before_first_write(
    project: Path, tmp_path: Path, binding: str
) -> None:
    base = tmp_path if binding == "external" else project
    first, second = base / "reports-a", base / "reports-b"
    first.mkdir()
    second.mkdir()
    left, right = first / "result.json", second / "result.json"
    if binding != "declared-new":
        left.write_bytes(b"preserve original A")
        right.write_bytes(b"preserve original B")
    expected = hashlib.sha256(left.read_bytes()).hexdigest() if left.exists() else None
    before = tuple(path.read_bytes() if path.exists() else None for path in (left, right))
    alias = base / "approved-alias"
    try:
        alias.symlink_to(first, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    spelling = alias / "result.json"
    output = str(spelling if binding.startswith("declared-") else left)
    approved_hash = str(spelling if binding == "expected" else left)
    grants = Grants(
        write=True,
        external_paths=(str(spelling),) if binding == "external" else (),
        expected_hashes={approved_hash: expected},
    )
    req = dataclasses.replace(request(project, output=output), grants=grants)

    def cli(*args: Any) -> runtime.CliResult:
        alias.unlink()
        alias.symlink_to(second, target_is_directory=True)
        return runtime.CliResult(1, json.dumps(report()) + "\n", "")

    result = runtime.execute(req, cache_home=tmp_path / "cache", cli_runner=cli)
    assert result.invocation == "blocked" and not result.complete
    assert result.cli_exit_code == 1 and result.gate_failed is True
    assert tuple(path.read_bytes() if path.exists() else None for path in (left, right)) == before
    assert sorted(path.name for path in first.iterdir()) == ([left.name] if left.exists() else [])
    assert sorted(path.name for path in second.iterdir()) == (
        [right.name] if right.exists() else []
    )


def test_maximum_reply_cleanup_failure_preserves_fixed_lease_diagnostic() -> None:
    import skill_request

    base = Reply(
        "audit",
        invocation="internal_error",
        cli_exit_code=1,
        gate_failed=True,
        complete=False,
        data="",
    )
    amount = skill_request.MAX_REPLY_BYTES - 1 - len(encode_reply(base))
    reply = dataclasses.replace(base, data="x" * amount)
    reply.diagnostics.append(
        {"code": "runtime_lease_cleanup_failed", "unsafe_extra": "never echo this"}
    )
    final = encode_reply(reply) + b"\n"
    decoded = json.loads(final)
    assert len(final) <= skill_request.MAX_REPLY_BYTES
    assert decoded["invocation"] == "internal_error" and decoded["cli_exit_code"] == 1
    assert decoded["gate_failed"] is True and not decoded["complete"]
    assert {"code": "runtime_lease_cleanup_failed"} in decoded["diagnostics"]
    assert "never echo this" not in final.decode()
