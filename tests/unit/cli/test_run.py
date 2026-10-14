"""CLI subprocess contract and configuration precedence (M5-T05)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.errors import UserError
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo, RunRecord
from tests.conftest import CmdStub

runner = CliRunner()


@pytest.fixture(autouse=True)
def local_run(monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    stub_run_cmd.on("git", returncode=128)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))


def record(root: Path) -> tuple[Path, dict]:
    (path,) = (root / ".reprollm/runs").glob("*/run.json")
    return path, json.loads(path.read_text())


def manifest(root: Path) -> None:
    (root / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: test}\nexperiment: {profiles: []}\n"
    )


def test_run_no_manifest_warns_but_preserves_child_code(tmp_path: Path) -> None:
    result = runner.invoke(app, ["run", "--", sys.executable, "-c", "import sys; sys.exit(3)"])
    assert result.exit_code == 3, result.output
    path, saved = record(tmp_path)
    assert saved["exit_code"] == 3 and saved["status"] == "completed"
    assert "no reprollm.yaml; bindings and declared files unavailable" in result.stderr
    assert f"Recorded run {path.parent.name} (exit 3," in result.stdout
    assert ".reprollm/runs/" in result.stdout and str(tmp_path) not in result.stdout


def test_command_tokens_after_separator_are_unchanged(tmp_path: Path) -> None:
    manifest(tmp_path)
    script = "import sys; assert sys.argv[1:] == ['--name', 'child', '--', 'literal;value']"
    result = runner.invoke(
        app,
        [
            "run",
            "--name",
            "parent",
            "--",
            sys.executable,
            "-c",
            script,
            "--name",
            "child",
            "--",
            "literal;value",
        ],
    )
    assert result.exit_code == 0, result.output
    _, saved = record(tmp_path)
    assert saved["name"] == "parent"
    assert saved["command"]["argv"][3:] == ["--name", "child", "--", "literal;value"]


def test_run_config_defaults_and_explicit_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest(tmp_path)
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/config.yaml").write_text(
        "schema_version: 1\nrun:\n  capture_output: true\n  env_capture: all\n"
        "  snapshot_max_bytes: 4\n  extra_env_allowlist: [EXTRA_NOTE]\n"
    )
    (tmp_path / "small.txt").write_text("fits")
    (tmp_path / "large.txt").write_text("does not fit")
    monkeypatch.setenv("EXTRA_NOTE", "allowed")
    monkeypatch.setenv("UNLISTED_NOTE", "omitted")
    result = runner.invoke(
        app,
        [
            "run",
            "--env-capture",
            "allowlist",
            "--",
            sys.executable,
            "-c",
            "print('output')",
            "small.txt",
            "large.txt",
        ],
    )
    assert result.exit_code == 0, result.output
    path, saved = record(tmp_path)
    assert (path.parent / "stdout.log").read_text() == "output\n"
    assert "output" in result.stdout
    assert saved["environment"]["env_capture"] == "allowlist"
    assert saved["environment"]["env"]["EXTRA_NOTE"] == "allowed"
    assert "UNLISTED_NOTE" not in saved["environment"]["env"]
    files = {f["path"]: f for f in saved["files"]}
    assert files["small.txt"]["snapshot"] is not None
    assert files["large.txt"]["snapshot"] is None


def test_cwd_and_no_snapshot(tmp_path: Path) -> None:
    manifest(tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    (work / "input.txt").write_text("text")
    result = runner.invoke(
        app,
        [
            "run",
            "--cwd",
            str(work),
            "--no-snapshot",
            "--",
            sys.executable,
            "-c",
            "from pathlib import Path; assert Path('input.txt').read_text() == 'text'",
            "input.txt",
        ],
    )
    assert result.exit_code == 0, result.output
    path, saved = record(tmp_path)
    assert saved["command"]["cwd"] == "work"
    assert saved["files"][0]["path"] == "work/input.txt"
    assert saved["files"][0]["snapshot"] is None
    assert (path.parent / "manifest.yaml").exists()


@pytest.mark.parametrize("arguments", [["run"], ["run", "--cwd", "missing", "--", "python"]])
def test_invalid_usage_does_not_allocate_run(tmp_path: Path, arguments: list[str]) -> None:
    result = runner.invoke(app, arguments)
    assert isinstance(result.exception, UserError) or result.exit_code == 2
    assert not (tmp_path / ".reprollm/runs").exists()


def test_invalid_env_mode_is_usage_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["run", "--env-capture", "unsafe", "--", "python"])
    assert result.exit_code == 2
    assert not (tmp_path / ".reprollm/runs").exists()


def test_runs_list_show_json_prefix_and_ambiguity(tmp_path: Path) -> None:
    manifest(tmp_path)
    for name in ("first", "second"):
        result = runner.invoke(app, ["run", "--name", name, "--", sys.executable, "-c", "pass"])
        assert result.exit_code == 0, result.output
    listing = runner.invoke(app, ["runs", "list", "--json"])
    assert listing.exit_code == 0, listing.output
    rows = json.loads(listing.stdout)
    assert {row["name"] for row in rows} == {"first", "second"}
    assert all(row["status"] == "completed" and row["exit_code"] == 0 for row in rows)
    selected = rows[0]["run_id"]
    shown = runner.invoke(app, ["runs", "show", selected[:-1], "--json"])
    assert shown.exit_code == 0, shown.output
    assert shown.stdout == (tmp_path / ".reprollm/runs" / selected / "run.json").read_text()
    table = runner.invoke(app, ["runs", "list"])
    assert table.exit_code == 0 and "first" in table.stdout and "second" in table.stdout
    summary = runner.invoke(app, ["runs", "show", selected])
    assert summary.exit_code == 0 and selected in summary.stdout and "Command:" in summary.stdout
    ambiguous = runner.invoke(app, ["runs", "show", selected[:8]])
    assert isinstance(ambiguous.exception, UserError) and "ambiguous" in str(ambiguous.exception)


def test_runs_corruption_missing_and_path_escape(tmp_path: Path) -> None:
    manifest(tmp_path)
    assert runner.invoke(app, ["runs", "list", "--json"]).stdout == "[]\n"
    bad = tmp_path / ".reprollm/runs/20261005T000000Z-abcdef"
    bad.mkdir(parents=True)
    (bad / "run.json").write_text('{"bad":"secret-payload"')
    result = runner.invoke(app, ["runs", "list", "--json"])
    assert result.exit_code == 0 and json.loads(result.stdout) == []
    assert "warning" in result.stderr and "secret-payload" not in result.output
    for prefix in ("../", "missing", "20261005T000000Z-abcdef"):
        shown = runner.invoke(app, ["runs", "show", prefix, "--json"])
        assert isinstance(shown.exception, UserError)
        assert "secret-payload" not in str(shown.exception)


@pytest.mark.parametrize(
    ("schema_version", "producer", "python_scope", "host_scope", "env_scope", "input_phase"),
    [
        (
            1,
            "0.6.2",
            "recorder/post_child",
            "host/post_child",
            "inherited_environment/pre_child",
            "unknown",
        ),
        (
            2,
            "0.7.0",
            "recorder/post_child",
            "host/post_child",
            "inherited_environment/pre_child",
            "pre_child",
        ),
        (2, "custom-writer", "unknown/unknown", "unknown/unknown", "unknown/unknown", "pre_child"),
    ],
)
def test_runs_show_scopes_environment_and_typed_input_checks_without_rewriting_json(
    tmp_path: Path,
    schema_version: int,
    producer: str,
    python_scope: str,
    host_scope: str,
    env_scope: str,
    input_phase: str,
) -> None:
    manifest(tmp_path)
    data = {
        "schema_version": schema_version,
        "reprollm_version": producer,
        "run_id": "20261014T000000Z-000001",
        "status": "completed",
        "exit_code": 0,
        "command": {"argv": ["python", "child.py"], "cwd": "."},
        "environment": {
            "os": "fixture",
            "platform": "linux",
            "python": "3.11.9",
            "hostname_sha256": "sha256:" + "a" * 64,
            "packages": {"torch": "2.6.0"},
            "env": {"OMP_NUM_THREADS": "2"},
        },
        "hardware": {"cpu_count": 2, "source": "nvidia_smi"},
        "bindings_observed": {
            "generation.temperature": [
                {
                    "value": 0.1,
                    "source": {"type": "config", "path": "config.json", "key": "temperature"},
                }
            ],
        },
    }
    if schema_version == 2:
        data["input_capture"] = {
            "baseline_phase": "pre_child",
            "check_phase": "post_child",
            "consumption": "unverified",
            "checks": [
                {
                    "path": "config.json",
                    "origin": "declared",
                    "before": {
                        "availability": "present",
                        "sha256": "sha256:" + "1" * 64,
                        "size_bytes": 21,
                    },
                    "after": {
                        "availability": "present",
                        "sha256": "sha256:" + "2" * 64,
                        "size_bytes": 21,
                    },
                    "change": "changed",
                }
            ],
        }
    parsed = RunRecord.model_validate(data)
    folder = tmp_path / ".reprollm/runs" / parsed.run_id
    folder.mkdir(parents=True)
    raw = parsed.model_dump_json(indent=2) + "\n"
    saved = folder / "run.json"
    saved.write_text(raw, encoding="utf-8", newline="")

    result = runner.invoke(app, ["runs", "show", parsed.run_id])
    assert result.exit_code == 0, result.output
    assert f"Python 3.11.9 ({python_scope}; child unverified)" in result.stdout
    assert f"torch: 2.6.0 ({python_scope}; child unverified)" in result.stdout
    assert f"GPU source: nvidia_smi ({host_scope}; child unverified)" in result.stdout
    assert f"Inherited environment: allowlist ({env_scope}; child unverified)" in result.stdout
    assert f"Input baseline: input_file/{input_phase}; child unverified" in result.stdout
    assert "Child environment and input consumption are unverified." in result.stdout
    assert f"input_file/{input_phase}; child unverified" in result.stdout
    if schema_version == 2:
        assert "Input recheck phase: post_child; child consumption unverified." in result.stdout
        assert (
            "Input check: config.json; change changed; before present; after present"
            in result.stdout
        )
    else:
        assert "Input check:" not in result.stdout
    shown = runner.invoke(app, ["runs", "show", parsed.run_id, "--json"])
    assert shown.exit_code == 0 and shown.stdout == raw
    assert saved.read_text(encoding="utf-8") == raw
