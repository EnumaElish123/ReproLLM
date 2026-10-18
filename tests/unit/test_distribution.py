"""D02: candidate identity, interpreter isolation and walkthrough acceptance."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from scripts import gen_quickstart, validate_distribution


def _wheel(tmp_path: Path, *, version: str = "0.7.0", name: str = "reprollm") -> Path:
    wheel = tmp_path / f"{name}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"{name}-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        )
    return wheel


def test_wheel_without_build_manifest_has_unconfirmed_source(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    identity = validate_distribution.inspect_wheel(wheel)
    assert identity["sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert identity["version"] == "0.7.0"
    assert validate_distribution.source_provenance(identity, None) == {
        "status": "UNCONFIRMED",
        "source_commit": None,
    }


@pytest.mark.parametrize("change", ["hash", "filename", "version", "commit", "schema"])
def test_build_manifest_rejects_broken_artifact_association(tmp_path: Path, change: str) -> None:
    wheel = _wheel(tmp_path)
    identity = validate_distribution.inspect_wheel(wheel)
    manifest = {
        "schema_version": 1,
        "source_commit": "a" * 40,
        "version": "0.7.0",
        "artifacts": [{"filename": wheel.name, "sha256": identity["sha256"]}],
    }
    if change == "hash":
        manifest["artifacts"][0]["sha256"] = "b" * 64
    elif change == "filename":
        manifest["artifacts"][0]["filename"] = "other.whl"
    elif change == "version":
        manifest["version"] = "0.6.1"
    elif change == "commit":
        manifest["source_commit"] = "main"
    else:
        manifest["schema_version"] = True
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(validate_distribution.ValidationFailure):
        validate_distribution.source_provenance(identity, path)


def test_build_manifest_binds_exact_hash_version_and_commit(tmp_path: Path) -> None:
    wheel = _wheel(tmp_path)
    identity = validate_distribution.inspect_wheel(wheel)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_commit": "a" * 40,
                "version": "0.7.0",
                "artifacts": [{"filename": wheel.name, "sha256": identity["sha256"]}],
            }
        ),
        encoding="utf-8",
    )
    assert validate_distribution.source_provenance(identity, manifest) == {
        "status": "BUILD_MANIFEST_ASSOCIATED",
        "source_commit": "a" * 40,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize("expected_version,tag", [("0.6.1", None), (None, "v0.6.1")])
def test_metadata_mismatch_stops_before_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expected_version: str | None, tag: str | None
) -> None:
    wheel = _wheel(tmp_path)
    monkeypatch.setattr(
        validate_distribution, "_install", lambda *a, **k: pytest.fail("must not install")
    )
    summary = validate_distribution.validate(
        wheel, expected_version=expected_version, expected_tag=tag
    )
    assert summary["status"] == "FAIL"
    assert summary["failure"] == "wheel_target_version"


def test_wheel_metadata_rejects_another_distribution(tmp_path: Path) -> None:
    with pytest.raises(validate_distribution.ValidationFailure):
        validate_distribution.inspect_wheel(_wheel(tmp_path, name="another"))


def test_quickstart_selects_explicit_interpreter_and_removes_source_injection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/synthetic/source")
    monkeypatch.setenv("PYTHONHOME", "/synthetic/home")
    monkeypatch.setenv("HF_TOKEN", "synthetic-secret")
    python = tmp_path / "venv" / "bin" / "python"
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="0.7.0\n", stderr="")

    monkeypatch.setattr(gen_quickstart.subprocess, "run", run)
    step = gen_quickstart._run(["--version"], tmp_path, python=python)
    command, kwargs = calls[0]
    assert command[:5] == [str(python), "-I", "-X", "utf8", "-c"]
    assert step.executable == str(python)
    assert kwargs["env"]["PATH"].split(os.pathsep)[0] == str(python.parent)
    assert kwargs["env"]["PYTHONNOUSERSITE"] == "1"
    assert not {"PYTHONPATH", "PYTHONHOME", "HF_TOKEN"} & kwargs["env"].keys()


def test_isolated_walkthrough_preserves_utf8_mode_and_non_ascii_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = gen_quickstart._env()
    environment["LC_ALL"] = "C.UTF-8"
    monkeypatch.setattr(gen_quickstart, "_env", lambda python=None: environment)
    monkeypatch.setattr(
        gen_quickstart,
        "OFFLINE_CLI",
        "import json, sys; print(json.dumps({'utf8_mode': sys.flags.utf8_mode, "
        "'text': 'café — 训练'}, ensure_ascii=False))",
    )
    step = gen_quickstart._run(["--version"], tmp_path)
    assert json.loads(step.stdout) == {"utf8_mode": 1, "text": "café — 训练"}
    assert step.raw_stdout == step.stdout + "\n"
    assert step.stderr == "" and step.raw_stderr == ""


def test_windows_reader_keeps_stderr_instead_of_losing_an_undecodable_pipe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = gen_quickstart._env()
    environment["LC_ALL"] = "C.UTF-8"
    monkeypatch.setattr(gen_quickstart, "_env", lambda python=None: environment)
    monkeypatch.setattr(
        gen_quickstart,
        "OFFLINE_CLI",
        "import sys\n"
        "if not sys.flags.utf8_mode:\n"
        "    sys.stderr.reconfigure(encoding='cp1252')\n"
        "print('stdout retained')\n"
        "print('diagnostic — café', file=sys.stderr)\n",
    )
    real_run = subprocess.run

    def windows_reader(command, **kwargs):
        # Windows reader threads leave None when decoding the pipe fails.
        # Capture real child bytes so its selected UTF-8 mode controls this edge.
        kwargs.pop("encoding")
        result = real_run(command, **kwargs)
        try:
            stderr = result.stderr.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            stderr = None
        return subprocess.CompletedProcess(
            command,
            result.returncode,
            result.stdout.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"),
            stderr,
        )

    monkeypatch.setattr(gen_quickstart.subprocess, "run", windows_reader)
    step = gen_quickstart._run(["--version"], tmp_path)
    assert step.stdout == "stdout retained"
    assert step.stderr == "diagnostic — café"
    assert step.raw_stderr == "diagnostic — café\n"


def test_offline_walkthrough_blocks_socket_connection_before_product_import(tmp_path: Path) -> None:
    program = gen_quickstart.OFFLINE_CLI.replace(
        "from reprollm.cli.main import cli\ncli()",
        "import socket\nsocket.create_connection(('127.0.0.1', 9))",
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", program],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
        env=gen_quickstart._env(),
    )
    assert result.returncode != 0
    assert "The offline walkthrough forbids network access" in result.stderr


@pytest.mark.parametrize(
    "defect", ["module", "cli_module", "prefix", "user_site", "editable", "hash", "version"]
)
def test_import_probe_rejects_source_leaks_or_wrong_installed_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    environment = tmp_path / "venv"
    identity = {"version": "0.7.0", "sha256": "a" * 64}
    direct_url = {"archive_info": {"hashes": {"sha256": identity["sha256"]}}}
    info = {
        "module": str(environment / "lib/reprollm/__init__.py"),
        "cli_module": str(environment / "lib/reprollm/cli/main.py"),
        "distribution_root": str(environment / "lib"),
        "prefix": str(environment),
        "version": "0.7.0",
        "code_version": "0.7.0",
        "sys_path": [str(environment / "lib")],
        "user_site_enabled": False,
    }
    if defect in {"module", "cli_module", "prefix"}:
        info[defect] = str(tmp_path / "source")
    elif defect == "user_site":
        info["user_site_enabled"] = True
    elif defect == "editable":
        direct_url["dir_info"] = {"editable": True}
    elif defect == "hash":
        direct_url["archive_info"]["hashes"]["sha256"] = "b" * 64
    else:
        info["code_version"] = "0.6.1"
    info["direct_url"] = json.dumps(direct_url)
    monkeypatch.setattr(
        validate_distribution.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, json.dumps(info), ""),
    )
    with pytest.raises(validate_distribution.ValidationFailure):
        validate_distribution._import_evidence(
            environment / "bin/python", environment, tmp_path, identity
        )


@pytest.fixture(scope="module")
def walkthrough(tmp_path_factory):
    work = tmp_path_factory.mktemp("distribution-assertions") / "tour"
    return gen_quickstart.run_workflow(work, python=Path(sys.executable)), work


def test_walkthrough_acceptance_checks_real_records(walkthrough) -> None:
    records, work = walkthrough
    checks = validate_distribution.verify_walkthrough(records, work)
    assert all(check["passed"] for check in checks)
    assert {"audit_levels", "capture_values", "semantic_cap_drift", "export_selected_run"} <= {
        check["id"] for check in checks
    }


def test_only_help_is_not_a_distribution_walkthrough(tmp_path: Path) -> None:
    step = gen_quickstart.Step("help", ["--help"], "Usage", "", 0, 0.0)
    with pytest.raises(validate_distribution.ValidationFailure):
        validate_distribution.verify_walkthrough([step], tmp_path)


def test_high_summary_does_not_hide_wrong_target_leaf(walkthrough) -> None:
    records, work = walkthrough
    index = next(i for i, row in enumerate(records) if row.command[0] == "diff")
    report = json.loads(records[index].report_json)
    cap = next(row for row in report["changes"] if row["path"] == "generation.max_tokens")
    cap["b"] = 47
    tampered = list(records)
    tampered[index] = replace(records[index], report_json=json.dumps(report))
    with pytest.raises(validate_distribution.ValidationFailure, match="semantic_cap_drift"):
        validate_distribution.verify_walkthrough(tampered, work)


def test_unrelated_48_does_not_hide_missing_export_parameter(walkthrough, tmp_path: Path) -> None:
    records, work = walkthrough
    for source in work.glob(".reprollm/runs/*/run.json"):
        target = tmp_path / source.relative_to(work)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    document = (work / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "- `max_tokens`: 48\n" in document
    (tmp_path / "REPRODUCIBILITY.md").write_text(
        document.replace("- `max_tokens`: 48\n", "")
        + "\n### Unrelated note: 48\n- `max_tokens`: 48\n",
        encoding="utf-8",
    )
    with pytest.raises(validate_distribution.ValidationFailure, match="export_selected_run"):
        validate_distribution.verify_walkthrough(records, tmp_path)


def test_public_summary_uses_logical_executable_and_hashes(tmp_path: Path) -> None:
    step = gen_quickstart.Step(
        "version", ["--version"], "0.7.0", "", 0, 0.1, executable=str(tmp_path / "python")
    )
    public = validate_distribution.command_evidence(step)
    assert public["executable"] == "<venv-python>"
    assert str(tmp_path) not in json.dumps(public)
    assert public["stdout_sha256"] == hashlib.sha256(b"0.7.0").hexdigest()


def test_failed_command_keeps_raw_output_for_evidence_before_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        gen_quickstart.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 3, "output\n", "failure\n"),
    )
    seen = []
    with pytest.raises(gen_quickstart.CommandError):
        gen_quickstart._run(["export", "."], tmp_path, on_step=seen.append)
    assert len(seen) == 1
    assert seen[0].raw_stdout == "output\n" and seen[0].raw_stderr == "failure\n"
    assert (
        validate_distribution.command_evidence(seen[0])["stdout_sha256"]
        == hashlib.sha256(b"output\n").hexdigest()
    )


@pytest.mark.parametrize("record_count", [0, 2])
def test_successful_child_without_unique_record_emits_safe_json_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    record_count: int,
) -> None:
    wheel = _wheel(tmp_path)
    output = tmp_path / "summary.json"
    private_detail = f"{tmp_path}/synthetic-private-detail"
    monkeypatch.setattr(validate_distribution.venv.EnvBuilder, "create", lambda *a: None)
    monkeypatch.setattr(validate_distribution, "_install", lambda *a, **k: {"exit_code": 0})
    monkeypatch.setattr(validate_distribution, "_import_evidence", lambda *a: {})

    def run(command, **kwargs):
        for index in range(record_count):
            record = Path(kwargs["cwd"]) / f".reprollm/runs/record-{index}/run.json"
            record.parent.mkdir(parents=True)
            record.write_text("{}", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, private_detail, private_detail)

    def walkthrough(work, *, python, on_step):
        work.mkdir()
        gen_quickstart._capture(work, "capture-a", python=python, on_step=on_step)
        pytest.fail("capture must reject a missing or ambiguous record")

    monkeypatch.setattr(gen_quickstart.subprocess, "run", run)
    monkeypatch.setattr(gen_quickstart, "run_workflow", walkthrough)
    assert validate_distribution.main(["--wheel", str(wheel), "--output", str(output)]) == 1
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert captured.err == ""
    assert json.loads(output.read_text(encoding="utf-8")) == summary
    assert summary["status"] == "FAIL"
    assert summary["failure"] == "invalid_input_or_execution"
    assert summary["error_type"] == "RuntimeError"
    assert summary["commands"][0]["exit_code"] == 0
    assert private_detail not in captured.out
    assert str(tmp_path) not in captured.out
    assert "capture must create exactly one run record" not in captured.out


def test_private_outputs_cannot_be_written_into_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        validate_distribution, "_install", lambda *a, **k: pytest.fail("must not install")
    )
    summary = validate_distribution.validate(
        _wheel(tmp_path), raw_output_dir=validate_distribution.ROOT / "raw-distribution-evidence"
    )
    assert summary["status"] == "FAIL"
    assert summary["failure"] == "private_output_outside_checkout"
