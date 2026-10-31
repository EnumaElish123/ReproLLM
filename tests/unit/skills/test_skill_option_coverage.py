"""SK20 additional local acceptance cases; no subprocess, signals or network.

These portable cases supplement the full native-command option coverage table.
The native recorder is a declared unit double for override delegation; actual
native environment capture remains the separately recorded SK18 evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "skills/reprollm/scripts")]

import skill_discover as discovery  # noqa: E402
import skill_run as run  # noqa: E402
import skill_runtime as runtime  # noqa: E402
from skill_request import ACTION_SPECS, Grants, Request, RequestError, parse_request  # noqa: E402

from reprollm.cli import main as native_main  # noqa: E402
from reprollm.core.proc import CmdResult  # noqa: E402
from reprollm.run import wrapper  # noqa: E402
from reprollm.schemas.run_record import (  # noqa: E402
    CommandInfo,
    InputCapture,
    RunRecord,
    RunStatus,
)


@pytest.fixture(autouse=True)
def no_external_effects(monkeypatch):
    previous = dict(native_main.STATE)
    monkeypatch.setattr("subprocess.Popen", lambda *a, **kw: pytest.fail("subprocess forbidden"))
    monkeypatch.setattr("os.kill", lambda *a, **kw: pytest.fail("signals forbidden"))
    monkeypatch.setattr(
        httpx.Client, "__init__", lambda *a, **kw: pytest.fail("HTTP client forbidden")
    )
    monkeypatch.setattr("reprollm.core.proc.run_cmd", lambda *a, **kw: CmdResult(127, "", ""))
    yield
    native_main.STATE.clear()
    native_main.STATE.update(previous)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "research"
    root.mkdir()
    (root / "README.md").write_text(
        "# Public bounded input\n" + "public reproducibility fact\n" * 180
    )
    (root / "experiment.py").write_text(
        "import argparse\np=argparse.ArgumentParser()\np.add_argument('--temperature',type=float)\n"
    )
    return root


def inventory(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("cap", [700, 1400])
def test_discovery_max_chars_matches_actual_native_cli_body_report_and_truncation(
    project, tmp_path, cap
):
    before = inventory(project)
    native = runtime.invoke_cli(
        [
            "discover",
            str(project),
            "--experimental",
            "--dry-run",
            "--show-content",
            "--max-chars",
            str(cap),
        ],
        project,
    )
    assert native.exit_code == 0
    report, encoded = native.stdout.split("\nRequest messages (nothing sent):\n", 1)
    messages = json.loads(encoded)
    reply = discovery.preview(
        Request(
            "discover.preview",
            str(project),
            {"experimental": True, "show_content": True, "max_chars": cap},
        ),
        root=project,
        state_home=tmp_path / "state",
        helper_identity="a" * 64,
    )
    assert reply.cli_exit_code == 0 and reply.complete and reply.data["nothing_sent"]
    assert reply.data["report"] == report
    assert reply.data["messages"] == messages
    assert reply.data["truncated_files"] == ["README.md"]
    assert ("public reproducibility fact\n" * 180) not in messages[1]["content"]
    assert inventory(project) == before and not (tmp_path / "state").exists()


def test_distinct_max_chars_change_actual_eligible_body_and_approval_binding(project, tmp_path):
    # Collector omits an over-budget file; this pair crosses its complete-file
    # inclusion boundary rather than assuming the native collector slices text.
    replies = [
        discovery.preview(
            Request(
                "discover.preview",
                str(project),
                {"experimental": True, "show_content": True, "max_chars": cap},
            ),
            root=project,
            state_home=tmp_path / "state",
            helper_identity="a" * 64,
        )
        for cap in (700, 6000)
    ]
    assert len(replies[0].data["messages"][1]["content"]) < len(
        replies[1].data["messages"][1]["content"]
    )
    assert (
        replies[0].data["approval_requirements"]["messages_sha256"]
        != replies[1].data["approval_requirements"]["messages_sha256"]
    )
    assert (
        replies[0].data["approval_requirements"]["source_sha256"]
        != replies[1].data["approval_requirements"]["source_sha256"]
    )


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux native run delegation")
@pytest.mark.parametrize("configured,explicit", [("all", "allowlist"), ("allowlist", "all")])
def test_explicit_env_capture_overrides_opposite_native_config_at_execute_seam(
    project, monkeypatch, configured, explicit
):
    (project / "reprollm.yaml").write_text(
        "schema_version: 1\n"
        "project: {name: public}\n"
        "experiment: {profiles: []}\n"
        "execution: {command: 'python3 experiment.py', cwd: '.'}\n"
    )
    directory = project / ".reprollm"
    directory.mkdir()
    (directory / "config.yaml").write_text(
        f"schema_version: 1\nrun: {{env_capture: {configured}}}\n"
    )
    calls, bound = [], []
    selected_env = dict(os.environ)
    null, real_fstat = os.stat(os.devnull), os.fstat
    monkeypatch.setattr(os, "fstat", lambda fd: null if fd in (0, 1, 2) else real_fstat(fd))

    def native_execute(argv, **kwargs):
        assert bound == [kwargs["run_dir"].name]
        assert kwargs["env_capture"] == explicit
        assert dict(os.environ) == selected_env
        calls.append(kwargs)
        return RunRecord(
            schema_version=2,
            input_capture=InputCapture(),
            reprollm_version="0.7.0",
            run_id=kwargs["run_dir"].name,
            status=RunStatus.FAILED,
            exit_code=7,
            command=CommandInfo(argv=list(argv), cwd="."),
        )

    monkeypatch.setattr(wrapper, "execute", native_execute)
    options = {"env_capture": explicit}
    preview = run.preview_run(
        Request("run.preview", str(project), options), root=project, identity="b" * 64
    )
    assert preview.data["start_ready"] is True

    class Lifecycle:
        def check_cancel(self):
            pass

        def bind_run(self, run_id):
            assert (project / ".reprollm/runs" / run_id).is_dir()
            bound.append(run_id)

    reply = run.execute_run(
        Request(
            "run.start",
            str(project),
            options,
            Grants(install=False, write=True, run=True, plan_hash=preview.data["plan_hash"]),
        ),
        root=project,
        identity="b" * 64,
        lifecycle=Lifecycle(),
    )
    assert len(calls) == 1 and reply.child_exit_code == 7
    assert reply.data["record"]["status"] == "failed"


@pytest.mark.parametrize("flag", ["verbose", "quiet", "no_color"])
def test_common_flags_reach_real_native_readonly_cli_without_extra_authority(project, flag):
    request = parse_request(
        {
            "schema_version": 1,
            "action": "profiles.list",
            "project": str(project),
            "options": {flag: True, "json": True},
        }
    )
    argv, is_json = runtime.command_args(request, project)
    assert argv == ["--" + flag.replace("_", "-"), "profiles", "list", "--json"] and is_json
    observed = runtime.invoke_cli(argv, project)
    baseline = runtime.invoke_cli(["profiles", "list", "--json"], project)
    assert observed.exit_code == baseline.exit_code == 0
    assert json.loads(observed.stdout) == json.loads(baseline.stdout)
    assert "\x1b[" not in observed.stdout
    # Quiet currently has no additional product-wide suppression behavior; the
    # important assertion is honest native parity, not an invented quieter JSON.


def test_native_verbose_effect_is_diagnostic_traceback_not_a_changed_audit_gate(
    project, monkeypatch
):
    import reprollm.cli.audit as audit

    def fail(*a, **kw):
        raise RuntimeError("public synthetic failure")

    monkeypatch.setattr(audit, "run_audit", fail)
    plain = runtime.invoke_cli(["audit", str(project), "--format", "json"], project)
    verbose = runtime.invoke_cli(["--verbose", "audit", str(project), "--format", "json"], project)
    assert plain.exit_code == verbose.exit_code == 3
    assert "Traceback" not in plain.stderr and "Traceback" in verbose.stderr


def test_service_preview_presentation_flags_are_neutral_and_never_grant_execution(project):
    options = {"argv": ["python3", "experiment.py"]}
    plain = run.preview_run(
        Request("run.preview", str(project), options), root=project, identity="b" * 64
    )
    flagged = run.preview_run(
        Request(
            "run.preview",
            str(project),
            {**options, "verbose": True, "quiet": True, "no_color": True},
        ),
        root=project,
        identity="b" * 64,
    )
    assert plain.as_dict() == flagged.as_dict()
    assert not (project / ".reprollm/runs").exists()


@pytest.mark.parametrize("action", sorted(ACTION_SPECS))
def test_unknown_option_for_each_action_is_rejected_before_any_dispatch(action):
    with pytest.raises(RequestError, match="unknown_option"):
        parse_request(
            {
                "schema_version": 1,
                "action": action,
                "project": "/no-filesystem-read-needed",
                "options": {"arbitrary_shell": "irrelevant"},
            }
        )


@pytest.mark.parametrize(
    "action,options",
    [
        ("discover.preview", {"max_chars": 0}),
        ("discover", {"max_chars": True}),
        ("run.start", {"env_capture": "all-unredacted"}),
        ("run.preview", {"capture_output": "true"}),
        ("audit", {"verbose": 1}),
        ("doctor", {"quiet": 0}),
        ("audit", {"no_color": "false"}),
    ],
)
def test_newly_measured_option_shapes_reject_non_native_values(action, options):
    with pytest.raises(RequestError, match="invalid_option_type_or_value"):
        parse_request(
            {
                "schema_version": 1,
                "action": action,
                "project": "/no-filesystem-read-needed",
                "options": options,
            }
        )
