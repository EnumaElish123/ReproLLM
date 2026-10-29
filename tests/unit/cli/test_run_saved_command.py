"""Saved command selection keeps capture semantics and preflight side-effect limits."""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.errors import UserError
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo
from tests.conftest import CmdStub

runner = CliRunner()


def write_manifest(root: Path, command: str | None, cwd: str | None = None) -> None:
    document: dict[str, Any] = {
        "schema_version": 1,
        "project": {"name": "saved-command"},
        "experiment": {"profiles": []},
        "execution": {"command": command, "cwd": cwd},
    }
    (root / "reprollm.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")


def usage(result: Any) -> None:
    assert result.exit_code == 2 or isinstance(result.exception, UserError), result.output


@pytest.fixture(autouse=True)
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub) -> None:
    monkeypatch.chdir(tmp_path)
    stub_run_cmd.on("git", returncode=128)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))


def test_saved_command_executes_exact_tokens_and_preserves_child_exit(tmp_path: Path) -> None:
    source = "import sys; assert sys.argv[1:] == ['two words', '', 'literal;value']; sys.exit(7)"
    write_manifest(
        tmp_path, shlex.join([sys.executable, "-c", source, "two words", "", "literal;value"])
    )
    result = runner.invoke(app, ["run", "--name", "saved"])
    assert result.exit_code == 7, result.output
    (record,) = (tmp_path / ".reprollm/runs").glob("*/run.json")
    saved = json.loads(record.read_text())
    assert saved["status"] == "completed" and saved["exit_code"] == 7
    assert saved["command"]["argv"][3:] == ["two words", "", "literal;value"]
    assert saved["command"]["cwd"] == "." and saved["schema_version"] == 2


def test_explicit_command_overrides_unusable_saved_command(tmp_path: Path) -> None:
    write_manifest(tmp_path, "python broken.py | private-secret-marker", "missing")
    result = runner.invoke(app, ["run", "--", sys.executable, "-c", "pass"])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize("configured_cwd", [None, "work"])
def test_saved_command_from_subdirectory_uses_manifest_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, configured_cwd: str | None
) -> None:
    (tmp_path / "caller").mkdir()
    (tmp_path / "work").mkdir()
    expected = tmp_path / (configured_cwd or ".")
    (expected / "marker.txt").write_text("correct")
    write_manifest(
        tmp_path,
        shlex.join(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; assert Path('marker.txt').read_text() == 'correct'",
            ]
        ),
        configured_cwd,
    )
    monkeypatch.chdir(tmp_path / "caller")
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    (record,) = (tmp_path / ".reprollm/runs").glob("*/run.json")
    assert json.loads(record.read_text())["command"]["cwd"] == (configured_cwd or ".")


def test_explicit_cwd_overrides_saved_cwd(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    write_manifest(
        tmp_path,
        shlex.join(
            [sys.executable, "-c", "from pathlib import Path; assert Path.cwd().name == 'work'"]
        ),
        "missing",
    )
    result = runner.invoke(app, ["run", "--cwd", str(work)])
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    "command",
    [
        None,
        "",
        "   ",
        "python 'unterminated",
        "python x.py && echo unsafe",
        "TOKEN=canary python x.py",
        "python x.py\nsecond-command",
    ],
    ids=["missing", "empty", "blank", "bad-quote", "shell", "assignment", "newline"],
)
@pytest.mark.parametrize("preview", [False, True])
def test_invalid_saved_command_is_private_and_allocates_nothing(
    tmp_path: Path, command: str | None, preview: bool
) -> None:
    write_manifest(tmp_path, command)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    result = runner.invoke(app, ["run", *(["--dry-run"] if preview else [])])
    usage(result)
    assert "canary" not in str(result.exception) + result.output
    assert "execution.command" in str(result.exception) + result.output
    assert before == {
        p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "bad_manifest",
    ["broken: [private-canary", "schema_version: 90\nprivate: canary", "x" * (2 * 1024 * 1024 + 1)],
    ids=["invalid-yaml", "invalid-schema", "oversized"],
)
def test_unusable_manifest_does_not_leak_or_allocate(tmp_path: Path, bad_manifest: str) -> None:
    (tmp_path / "reprollm.yaml").write_text(bad_manifest)
    result = runner.invoke(app, ["run"])
    usage(result)
    assert "canary" not in str(result.exception) + result.output
    assert not (tmp_path / ".reprollm").exists()


@pytest.mark.parametrize("manifest_cwd", ["missing", "nested"])
def test_invalid_or_nested_saved_cwd_rejected(tmp_path: Path, manifest_cwd: str) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    write_manifest(nested, "python other.py")
    write_manifest(tmp_path, "python child.py", manifest_cwd)
    result = runner.invoke(app, ["run"])
    usage(result)
    assert "execution.cwd" in str(result.exception) + result.output
    assert not (tmp_path / ".reprollm").exists()
    assert not (nested / ".reprollm").exists()


def test_saved_preflight_is_read_only_without_subprocesses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_manifest(tmp_path, "python child.py --password private-canary")
    (tmp_path / "child.py").write_text("pass\n")
    before = (tmp_path / "reprollm.yaml").read_bytes()

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("saved preflight performed a forbidden side effect")

    for target in [
        "reprollm.cli.run.execute",
        "reprollm.cli.run.create_run_dir",
        "reprollm.core.proc.run_cmd",
        "subprocess.Popen",
        "httpx.Client",
    ]:
        monkeypatch.setattr(target, forbidden)
    result = runner.invoke(app, ["run", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "not executed" in result.stdout and "private-canary" not in result.output
    assert "child.py" in result.output
    assert (tmp_path / "reprollm.yaml").read_bytes() == before
    assert not (tmp_path / ".reprollm").exists()


def test_missing_saved_manifest_preflight_does_not_call_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("unexpected subprocess")

    monkeypatch.setattr("reprollm.core.proc.run_cmd", forbidden)
    result = runner.invoke(app, ["run", "--dry-run"])
    usage(result)
    assert "init" in str(result.exception) + result.output


@pytest.mark.parametrize("kind", ["escape", "dangling", "cwd_escape"])
def test_saved_selection_rejects_links_outside_root(tmp_path: Path, kind: str) -> None:
    outside = tmp_path.parent / (tmp_path.name + "-outside")
    outside.mkdir()
    write_manifest(outside, "python private-canary.py")
    try:
        if kind == "cwd_escape":
            (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
            write_manifest(tmp_path, "python child.py", "linked")
        else:
            target = outside / ("reprollm.yaml" if kind == "escape" else "missing.yaml")
            (tmp_path / "reprollm.yaml").symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")
    result = runner.invoke(app, ["run", "--dry-run"])
    usage(result)
    assert "private-canary" not in result.output + str(result.exception)
    assert not (tmp_path / ".reprollm").exists()
    assert not (outside / ".reprollm").exists()


def test_saved_manifest_directory_is_rejected_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "reprollm.yaml").mkdir()

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("nonregular manifest was opened")

    monkeypatch.setattr(Path, "open", forbidden)
    usage(runner.invoke(app, ["run"]))
    assert not (tmp_path / ".reprollm").exists()


def test_manifest_read_failure_is_private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_manifest(tmp_path, "python child.py")

    def unavailable(*args: Any, **kwargs: Any) -> None:
        raise PermissionError("private-canary /private/host/identity")

    monkeypatch.setattr(Path, "open", unavailable)
    result = runner.invoke(app, ["run"])
    usage(result)
    assert "private-canary" not in result.output + str(result.exception)
    assert str(tmp_path) not in result.output + str(result.exception)


def test_saved_command_uses_existing_output_capture_default(tmp_path: Path) -> None:
    write_manifest(tmp_path, shlex.join([sys.executable, "-c", "print('saved output')"]))
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/config.yaml").write_text(
        "schema_version: 1\nrun: {capture_output: true}\n"
    )
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 0, result.output
    (record,) = (tmp_path / ".reprollm/runs").glob("*/run.json")
    assert (record.parent / "stdout.log").read_text() == "saved output\n"


@pytest.mark.linux_only
@pytest.mark.skipif(sys.platform != "linux", reason="FIFO semantics require Linux")
def test_saved_manifest_fifo_is_rejected_without_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    os.mkfifo(tmp_path / "reprollm.yaml")

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("FIFO manifest was opened")

    monkeypatch.setattr(Path, "open", forbidden)
    usage(runner.invoke(app, ["run", "--dry-run"]))
    assert not (tmp_path / ".reprollm").exists()
