"""SK18: fixed native selection, pre-start plan and evidence fidelity.

All execution below is a native-peer test double. Popen and proc gateway are
blocked. This draft is not standard-library, GPU, paid or installed acceptance.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

WORKTREE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKTREE / "src"))
sys.path.insert(0, str(WORKTREE / "skills/reprollm/scripts"))
from skill_request import Grants, Request  # noqa: E402

from reprollm.core import proc  # noqa: E402
from reprollm.core.errors import UserError  # noqa: E402
from reprollm.run import wrapper  # noqa: E402
from reprollm.schemas.run_record import (  # noqa: E402
    CommandInfo,
    InputCapture,
    RunRecord,
    RunStatus,
)

IDENTITY = "a" * 64


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SK18 draft may not start a real child")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(
        proc, "run_cmd", lambda *a, **k: proc.CmdResult(127, "", "fixture unavailable")
    )


@pytest.fixture
def adapter():
    return importlib.import_module("skill_run")


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "public-project"
    root.mkdir()
    (root / "work").mkdir()
    write_manifest(root)
    (root / "probe.py").write_text('raise RuntimeError("never execute in this draft")\n')
    return root


def write_manifest(root, command="python probe.py --label original", cwd=None):
    data = {
        "schema_version": 1,
        "project": {"name": "public"},
        "experiment": {"profiles": []},
        "execution": {"command": command, "cwd": cwd},
    }
    (root / "reprollm.yaml").write_text(json.dumps(data))


def inventory(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def request(root, action="run.preview", options=None, *, plan=None, run=False, write=False):
    return Request(
        action,
        str(root),
        options or {},
        Grants(install=False, run=run, write=write, plan_hash=plan),
    )


def preview(adapter, root, options=None):
    reply = adapter.preview_run(request(root, options=options), root=root, identity=IDENTITY)
    assert reply.data["start_ready"] is True
    assert len(reply.data["plan_hash"]) == 64
    return reply


class Lifecycle:
    def __init__(self, root, events, on_bind=None):
        self.root, self.events, self.on_bind = root, events, on_bind
        self.run_id = None

    def check_cancel(self):
        self.events.append("check_cancel")

    def bind_run(self, run_id):
        assert (self.root / ".reprollm/runs" / run_id).is_dir()
        assert self.run_id is None
        self.run_id = run_id
        self.events.append(("bound", run_id))
        if self.on_bind:
            self.on_bind()


@pytest.fixture
def native_double(monkeypatch):
    calls, events = [], []
    result = {"exit": 0}
    if sys.platform.startswith("linux"):
        real_fstat = os.fstat
        null = os.stat(os.devnull)
        # Kernel I/O stub is unit-only. Real DEVNULL isolation is a later installed
        # worker test; every other fstat still examines the actual temporary file.
        monkeypatch.setattr(os, "fstat", lambda fd: null if fd in (0, 1, 2) else real_fstat(fd))
    else:
        # This unit double exercises selection and record binding, not worker support.
        monkeypatch.setattr(importlib.import_module("skill_run"), "_worker_io", lambda: None)

    def execute(argv, **kwargs):
        assert events and ("bound", kwargs["run_dir"].name) in events
        calls.append((list(argv), kwargs, dict(os.environ)))
        events.append("native_execute")
        code = result["exit"]
        return RunRecord(
            schema_version=2,
            input_capture=InputCapture(),
            reprollm_version="0.7.0",
            run_id=kwargs["run_dir"].name,
            name=kwargs.get("name"),
            status=RunStatus.INTERRUPTED if code < 0 else RunStatus.COMPLETED,
            exit_code=code,
            command=CommandInfo(
                argv=list(argv), cwd=kwargs["cwd"].relative_to(kwargs["root"]).as_posix()
            ),
        )

    monkeypatch.setattr(wrapper, "execute", execute)
    return calls, events, result


def start(adapter, root, options, plan, lifecycle, *, run=True, write=True):
    return adapter.execute_run(
        request(root, "run.start", options, plan=plan, run=run, write=write),
        root=root,
        identity=IDENTITY,
        lifecycle=lifecycle,
    )


def test_plan_is_deterministic_safe_and_has_no_product_artifacts(adapter, project):
    before = inventory(project)
    first = preview(adapter, project)
    second = preview(adapter, project)
    assert first.data["plan_hash"] == second.data["plan_hash"]
    assert inventory(project) == before and not (project / ".reprollm/runs").exists()
    assert "python probe.py" not in json.dumps(first.as_dict())


def test_omitted_cwd_preserves_native_saved_execution_cwd(adapter, project, native_double):
    write_manifest(project, cwd="work")
    calls, events, _ = native_double
    p = preview(adapter, project)
    lifecycle = Lifecycle(project, events)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.invocation == "handled_result"
    assert calls[0][1]["cwd"] == project / "work"


def test_explicit_cwd_overrides_saved_cwd(adapter, project, native_double):
    write_manifest(project, cwd="work")
    calls, events, _ = native_double
    options = {"cwd": "."}
    p = preview(adapter, project, options)
    start(adapter, project, options, p.data["plan_hash"], Lifecycle(project, events))
    assert calls[0][1]["cwd"] == project


def test_explicit_tokens_override_broken_saved_grammar(adapter, project, native_double):
    write_manifest(project, command="python bad.py | forbidden-shell")
    calls, events, _ = native_double
    options = {"argv": ["selected-python", "probe.py", "", "标签 with space", "$literal"]}
    p = preview(adapter, project, options)
    reply = start(adapter, project, options, p.data["plan_hash"], Lifecycle(project, events))
    assert reply.invocation == "handled_result" and calls[0][0] == options["argv"]


def test_explicit_no_manifest_has_ready_plan_but_no_false_native_preflight_pass(
    adapter, project, native_double
):
    (project / "reprollm.yaml").unlink()
    calls, events, _ = native_double
    options = {"argv": ["selected-python", "probe.py"]}
    p = preview(adapter, project, options)
    assert p.data["preflight"]["available"] is False
    reply = start(adapter, project, options, p.data["plan_hash"], Lifecycle(project, events))
    assert reply.invocation == "handled_result" and calls[0][0] == options["argv"]
    assert not (project / "reprollm.yaml").exists()


@pytest.mark.parametrize("failure", ["missing_manifest", "invalid_lock", "missing_saved"])
def test_preview_retains_native_actionable_user_diagnostics(adapter, project, failure):
    options = {"argv": ["python", "probe.py"]}
    if failure == "missing_manifest":
        (project / "reprollm.yaml").unlink()
        expected = "reprollm init"
    elif failure == "invalid_lock":
        (project / "reprollm.lock").write_text("schema_version: invalid\n", encoding="utf-8")
        expected = "repair this file"
    else:
        write_manifest(project, command=None)
        options = {}
        expected = "execution.command is missing"
    before = inventory(project)
    reply = adapter.preview_run(request(project, options=options), root=project, identity=IDENTITY)
    assert reply.invocation == "user_error" and reply.cli_exit_code == 2
    assert expected in json.dumps(reply.as_dict()) and not reply.complete
    if failure != "missing_saved":
        assert reply.data["start_ready"] is True
        assert reply.data["preflight"]["available"] is False
    else:
        assert reply.data["execution_started"] is False
    assert inventory(project) == before


def test_preview_user_diagnostic_uses_existing_privacy_projection(adapter, project, monkeypatch):
    from reprollm.run import preflight

    secret = "OpaqueSyntheticPreviewCredentialNeverSent"
    private_path = "/tmp/private-diagnostic-host/forbidden-input.json"

    def unavailable(*args, **kwargs):
        raise UserError(f"cannot inspect {private_path}; api_key={secret}; repair reprollm.lock")

    monkeypatch.setattr(preflight, "preview", unavailable)
    reply = preview(adapter, project)
    text = json.dumps(reply.as_dict())
    assert reply.invocation == "user_error" and "repair reprollm.lock" in text
    assert private_path not in text and secret not in text


def test_preview_privacy_failure_returns_fixed_actionable_hint(adapter, project, monkeypatch):
    import skill_runtime

    (project / "reprollm.yaml").unlink()

    def failed(*args, **kwargs):
        raise RuntimeError("synthetic private projection exception")

    monkeypatch.setattr(skill_runtime, "_sanitize", failed)
    reply = adapter.preview_run(
        request(project, options={"argv": ["python", "probe.py"]}), root=project, identity=IDENTITY
    )
    text = json.dumps(reply.as_dict())
    assert "reprollm init" in text and "repair" in text
    assert "synthetic private projection exception" not in text
    assert reply.data["start_ready"] is True and reply.cli_exit_code == 2


@pytest.mark.parametrize("run,write", [(False, False), (False, True), (True, False)])
def test_missing_run_or_write_grant_never_allocates(adapter, project, native_double, run, write):
    calls, events, _ = native_double
    p = preview(adapter, project)
    reply = start(
        adapter, project, {}, p.data["plan_hash"], Lifecycle(project, events), run=run, write=write
    )
    assert reply.invocation == "blocked" and reply.needs_authorization
    assert calls == [] and not (project / ".reprollm/runs").exists()


def test_missing_plan_is_automatic_preview_next_step_not_launch(adapter, project, native_double):
    calls, events, _ = native_double
    reply = start(adapter, project, {}, None, Lifecycle(project, events))
    assert reply.invocation == "blocked" and calls == []
    assert not (project / ".reprollm/runs").exists()
    assert any(x["code"] == "run_plan_required" for x in reply.diagnostics)


@pytest.mark.parametrize(
    "change", ["saved_command", "config", "rules", "argv", "cwd", "capture", "name", "snapshot"]
)
def test_plan_changes_refuse_before_allocation(adapter, project, native_double, change):
    calls, events, _ = native_double
    p = preview(adapter, project)
    options = {}
    if change == "saved_command":
        write_manifest(project, command="python entirely-different.py")
    elif change in {"config", "rules"}:
        d = project / ".reprollm"
        d.mkdir(exist_ok=True)
        (d / ("config.yaml" if change == "config" else "project-rules.yaml")).write_text(
            "schema_version: 1\nrun: {capture_output: true}\n"
            if change == "config"
            else "schema_version: 1\nrules: []\n"
        )
    else:
        options = (
            {"argv": ["other-python", "probe.py"]}
            if change == "argv"
            else {
                {
                    "cwd": "cwd",
                    "capture": "capture_output",
                    "name": "name",
                    "snapshot": "no_snapshot",
                }[change]: {
                    "cwd": "work",
                    "capture": True,
                    "name": "new-public-label",
                    "snapshot": True,
                }[change]
            }
        )
    before = inventory(project)
    reply = start(adapter, project, options, p.data["plan_hash"], Lifecycle(project, events))
    assert reply.invocation == "blocked" and calls == [] and inventory(project) == before


def test_run_id_is_bound_before_the_only_native_execute(adapter, project, native_double):
    calls, events, _ = native_double
    p = preview(adapter, project)
    lifecycle = Lifecycle(project, events)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert len(calls) == 1 and events.index(("bound", lifecycle.run_id)) < events.index(
        "native_execute"
    )
    assert reply.data["run_id"] == lifecycle.run_id
    assert len(list((project / ".reprollm/runs").iterdir())) == 1


def test_changed_saved_command_at_bind_never_becomes_another_launch(
    adapter, project, native_double
):
    calls, events, _ = native_double
    p = preview(adapter, project)
    lifecycle = Lifecycle(
        project, events, on_bind=lambda: write_manifest(project, command="python attacker.py")
    )
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.invocation == "blocked" and calls == [] and lifecycle.run_id
    assert (project / ".reprollm/runs" / lifecycle.run_id).is_dir()


def test_bind_failure_preserves_allocated_directory_without_execute(
    adapter, project, native_double
):
    calls, events, _ = native_double
    p = preview(adapter, project)

    def failed():
        raise OSError("synthetic private error text must not be exposed")

    lifecycle = Lifecycle(project, events, on_bind=failed)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.invocation in {"blocked", "internal_error"} and calls == []
    assert len(list((project / ".reprollm/runs").iterdir())) == 1
    assert "synthetic private error text" not in json.dumps(reply.as_dict())


@pytest.mark.parametrize("code", [0, 7, 127, -15])
def test_native_child_outcome_is_not_a_wrapper_or_gate_outcome(
    adapter, project, native_double, code
):
    calls, events, result = native_double
    result["exit"] = code
    p = preview(adapter, project)
    reply = start(adapter, project, {}, p.data["plan_hash"], Lifecycle(project, events))
    assert reply.invocation == "handled_result" and reply.child_exit_code == code
    assert reply.cli_exit_code is None and reply.gate_failed is None and len(calls) == 1
    assert reply.data["record_scope"] == "native_return"


@pytest.mark.parametrize("capture", [None, False, True])
def test_native_config_capture_precedence(adapter, project, native_double, capture):
    d = project / ".reprollm"
    d.mkdir()
    (d / "config.yaml").write_text(
        "schema_version: 1\nrun:\n  capture_output: true\n  env_capture: all\n"
        "  snapshot_max_bytes: 123\n  extra_env_allowlist: [PUBLIC_RUN_]\n"
    )
    calls, events, _ = native_double
    options = {"capture_output": capture}
    p = preview(adapter, project, options)
    start(adapter, project, options, p.data["plan_hash"], Lifecycle(project, events))
    effective = calls[0][1]
    assert effective["capture_output"] is (True if capture is None else capture)
    assert effective["env_capture"] == "all" and effective["max_bytes"] == 123
    assert effective["extra_allowlist"] == ["PUBLIC_RUN_"]


@pytest.mark.parametrize("bytecode", [None, "0", "1"])
def test_adapter_does_not_rewrite_selected_caller_environment(
    adapter, project, native_double, monkeypatch, bytecode
):
    if bytecode is None:
        monkeypatch.delenv("PYTHONDONTWRITEBYTECODE", raising=False)
    else:
        monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", bytecode)
    for key, value in {
        "PATH": "public-selected-bin",
        "PYTHONPATH": "public-selected-path",
        "CUDA_VISIBLE_DEVICES": "public-selected-device",
        "PUBLIC_TEST_API_KEY": "OpaqueSyntheticCredentialNotSentToProvider",
    }.items():
        monkeypatch.setenv(key, value)
    calls, events, _ = native_double
    p = preview(adapter, project)
    before = dict(os.environ)
    reply = start(adapter, project, {}, p.data["plan_hash"], Lifecycle(project, events))
    assert calls[0][2] == before and dict(os.environ) == before
    assert "OpaqueSyntheticCredential" not in json.dumps(reply.as_dict())


def test_native_start_error_keeps_bound_identity_and_unknown_child(
    adapter, project, native_double, monkeypatch
):
    calls, events, _ = native_double

    def cannot_start(*a, **kw):
        raise UserError("cannot start command (FileNotFoundError); check executable")

    monkeypatch.setattr(wrapper, "execute", cannot_start)
    p = preview(adapter, project)
    lifecycle = Lifecycle(project, events)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.invocation == "user_error" and reply.child_exit_code is None
    assert reply.data["run_id"] == lifecycle.run_id and lifecycle.run_id


@pytest.mark.parametrize("replacement", ["before_read", "during_read"])
def test_partial_recovery_refuses_replaced_allocated_directory(
    adapter, project, native_double, monkeypatch, replacement
):
    from reprollm.run import reader

    calls, events, _ = native_double
    p = preview(adapter, project)
    allocated = {}
    real_read = reader.read_run

    def replace(folder):
        folder.rename(folder.with_name("held-original-" + folder.name))
        folder.mkdir()

    def completed_record(folder):
        record = RunRecord(
            schema_version=2,
            input_capture=InputCapture(),
            reprollm_version="0.7.0",
            run_id=folder.name,
            status=RunStatus.COMPLETED,
            exit_code=7,
            command=CommandInfo(argv=["python", "synthetic.py"], cwd="."),
        )
        (folder / "run.json").write_text(record.model_dump_json(), encoding="utf-8")

    def failed(argv, **kwargs):
        folder = kwargs["run_dir"]
        allocated["stamp"] = (folder.stat().st_dev, folder.stat().st_ino)
        if replacement == "before_read":
            replace(folder)
        completed_record(folder)
        raise UserError("synthetic opaque startup failure")

    def guarded_read(root, run_id):
        folder = root / ".reprollm/runs" / run_id
        # A foreign replacement must be refused without reading its payload.
        assert (folder.stat().st_dev, folder.stat().st_ino) == allocated["stamp"]
        result = real_read(root, run_id)
        if replacement == "during_read":
            replace(folder)
            completed_record(folder)
        return result

    monkeypatch.setattr(wrapper, "execute", failed)
    monkeypatch.setattr(reader, "read_run", guarded_read)
    lifecycle = Lifecycle(project, events)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.child_exit_code is None and reply.data["run_id"] == lifecycle.run_id
    assert reply.data["record_scope"] == "unknown" and "record" not in reply.data
    assert any(d["code"] == "run_partial_record_unavailable" for d in reply.diagnostics)
    assert calls == []


def test_partial_recovery_labels_native_readback_separately_from_return(
    adapter, project, native_double, monkeypatch
):
    calls, events, _ = native_double
    p = preview(adapter, project)

    def failed(argv, **kwargs):
        record = RunRecord(
            schema_version=2,
            input_capture=InputCapture(),
            reprollm_version="0.7.0",
            run_id=kwargs["run_dir"].name,
            status=RunStatus.FAILED,
            command=CommandInfo(argv=list(argv), cwd="."),
        )
        (kwargs["run_dir"] / "run.json").write_text(record.model_dump_json(), encoding="utf-8")
        raise UserError("synthetic opaque startup failure")

    monkeypatch.setattr(wrapper, "execute", failed)
    reply = start(adapter, project, {}, p.data["plan_hash"], Lifecycle(project, events))
    assert reply.invocation == "user_error" and reply.child_exit_code is None
    assert reply.data["record_scope"] == "native_readback"
    assert reply.data["record"]["status"] == "failed" and calls == []


def test_replaced_selected_cwd_at_bind_refuses_launch(adapter, project, native_double):
    write_manifest(project, cwd="work")
    calls, events, _ = native_double
    p = preview(adapter, project)

    def replace():
        (project / "work").rename(project / "original-work")
        (project / "work").mkdir()

    lifecycle = Lifecycle(project, events, on_bind=replace)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.invocation == "blocked" and calls == []


@pytest.mark.parametrize("source", ["explicit", "saved", "saved_override"])
@pytest.mark.parametrize("parent_alias", [False, True])
def test_cwd_alias_retarget_at_bind_refuses_launch(
    adapter, project, native_double, source, parent_alias
):
    first, second = project / "first", project / "second"
    first.mkdir()
    second.mkdir()
    if parent_alias:
        (first / "work").mkdir()
        (second / "work").mkdir()
    alias = project / "selected-cwd"
    try:
        alias.symlink_to("first", target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks unavailable")
    selected = "selected-cwd/work" if parent_alias else "selected-cwd"
    options = {"argv": ["python", "probe.py"]} if source == "explicit" else {}
    if source == "saved":
        write_manifest(project, cwd=selected)
    else:
        options["cwd"] = selected
    calls, events, _ = native_double
    p = preview(adapter, project, options)

    def retarget():
        alias.unlink()
        alias.symlink_to("second", target_is_directory=True)

    lifecycle = Lifecycle(project, events, on_bind=retarget)
    reply = start(adapter, project, options, p.data["plan_hash"], lifecycle)
    assert reply.invocation == "blocked" and calls == []
    assert reply.data["run_id"] == lifecycle.run_id and lifecycle.run_id
    assert any(d["code"] == "run_plan_changed" for d in reply.diagnostics)


@pytest.mark.linux_only
@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux worker stream isolation")
@pytest.mark.parametrize("number", [0, 1, 2])
def test_non_null_worker_fd_refuses_before_allocation(
    adapter, project, native_double, monkeypatch, number
):
    calls, events, _ = native_double
    p = preview(adapter, project)
    original = os.fstat
    regular = (project / "reprollm.yaml").stat()
    monkeypatch.setattr(os, "fstat", lambda fd: regular if fd == number else original(fd))
    reply = start(adapter, project, {}, p.data["plan_hash"], Lifecycle(project, events))
    assert reply.invocation == "blocked" and calls == []
    assert not (project / ".reprollm/runs").exists()


def test_safe_result_projection_failure_preserves_known_child_seven(
    adapter, project, native_double, monkeypatch
):
    import skill_runtime

    calls, events, result = native_double
    result["exit"] = 7
    p = preview(adapter, project)

    def failed(*a, **k):
        raise RuntimeError("private opaque projection error")

    monkeypatch.setattr(skill_runtime, "_sanitize", failed)
    reply = start(adapter, project, {}, p.data["plan_hash"], Lifecycle(project, events))
    assert len(calls) == 1 and reply.child_exit_code == 7
    assert reply.invocation == "internal_error" and not reply.complete
    assert reply.data["native_status"] == "completed"
    assert reply.data["record_scope"] == "native_return"
    assert reply.data["record_delivery"] == "incomplete"
    assert "private opaque" not in json.dumps(reply.as_dict())


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes unavailable")
def test_control_fifo_is_refused_without_a_writer(adapter, project):
    d = project / ".reprollm"
    d.mkdir()
    os.mkfifo(d / "config.yaml")
    reply = adapter.preview_run(request(project), root=project, identity=IDENTITY)
    assert reply.invocation in {"blocked", "user_error"}
    assert not (project / ".reprollm/runs").exists()


def test_preview_never_hashes_experiment_file_contents(adapter, project, monkeypatch):
    import hashlib

    marker = b"UNIQUE_EXPERIMENT_BODY_DO_NOT_HASH"
    (project / "probe.py").write_bytes(marker)
    original = hashlib.sha256

    def hash_without_input_bytes(raw=b"", *a, **k):
        assert marker not in raw
        return original(raw, *a, **k)

    monkeypatch.setattr(hashlib, "sha256", hash_without_input_bytes)
    preview(adapter, project)


@pytest.mark.parametrize(
    "role",
    ["reprollm.yaml", ".reprollm/config.yaml", ".reprollm/project-rules.yaml", "reprollm.lock"],
)
def test_each_control_role_has_a_two_mib_limit(adapter, project, role):
    target = project / role
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    reply = adapter.preview_run(request(project), root=project, identity=IDENTITY)
    assert reply.invocation == "blocked"
    assert any(d["code"] == "run_control_limit" for d in reply.diagnostics)
    assert not (project / ".reprollm/runs").exists()


def test_escaping_control_is_refused_before_open(adapter, project, monkeypatch):
    foreign = project.parent / "foreign-control.yaml"
    foreign.write_text("schema_version: 1\n")
    d = project / ".reprollm"
    d.mkdir()
    try:
        (d / "config.yaml").symlink_to(foreign)
    except OSError:
        pytest.skip("File symlinks unavailable")
    original = os.open

    def guarded(path, *a, **k):
        assert Path(path) != foreign
        return original(path, *a, **k)

    monkeypatch.setattr(os, "open", guarded)
    reply = adapter.preview_run(request(project), root=project, identity=IDENTITY)
    assert reply.invocation == "blocked"


def test_selection_changed_during_native_load_is_not_a_valid_plan(adapter, project, monkeypatch):
    original = wrapper._safe_load

    def load_then_change(root):
        result = original(root)
        write_manifest(project, command="python changed-selection.py")
        return result

    monkeypatch.setattr(wrapper, "_safe_load", load_then_change)
    reply = adapter.preview_run(request(project), root=project, identity=IDENTITY)
    assert reply.invocation == "blocked" and not (project / ".reprollm/runs").exists()


def test_control_alias_retarget_at_bind_preserves_known_id_without_execute(
    adapter, project, native_double
):
    d = project / ".reprollm"
    d.mkdir()
    first, second = project / "first.yaml", project / "second.yaml"
    first.write_text("schema_version: 1\nrun: {capture_output: false}\n")
    second.write_text("schema_version: 1\nrun: {capture_output: true}\n")
    alias = d / "config.yaml"
    try:
        alias.symlink_to(first)
    except OSError:
        pytest.skip("File symlinks unavailable")
    calls, events, _ = native_double
    p = preview(adapter, project)

    def retarget():
        alias.unlink()
        alias.symlink_to(second)

    lifecycle = Lifecycle(project, events, on_bind=retarget)
    reply = start(adapter, project, {}, p.data["plan_hash"], lifecycle)
    assert reply.invocation == "blocked" and calls == []
    assert reply.data["run_id"] == lifecycle.run_id and lifecycle.run_id
