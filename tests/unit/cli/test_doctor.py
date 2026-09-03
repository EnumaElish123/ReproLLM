"""doctor CLI tests (M1-T07)."""

import json
from pathlib import Path

import httpx
import respx
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.proc import NOT_FOUND
from tests.conftest import CmdStub

runner = CliRunner()


def test_doctor_text_reports_checks() -> None:
    result = runner.invoke(app, ["doctor", "--no-color"])
    assert result.exit_code == 0
    assert "reprollm" in result.output
    assert "git" in result.output
    assert "python" in result.output


def test_doctor_json_structure() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    document = json.loads(result.output)
    assert document["reprollm_version"]
    names = {check["name"] for check in document["checks"]}
    assert {"python", "git", "nvidia-smi", "uv", "llm-critical-packages"} <= names
    assert all(check["status"] in {"ok", "warn", "missing"} for check in document["checks"])


def test_doctor_exit_1_when_git_missing(stub_run_cmd: CmdStub, tmp_path: Path) -> None:
    stub_run_cmd.on("git", returncode=NOT_FOUND, stderr="command not found")
    # nvidia-smi also routed through the stub to keep the run hermetic
    stub_run_cmd.on("nvidia-smi", returncode=NOT_FOUND)
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    document = json.loads(result.output)
    git = next(check for check in document["checks"] if check["name"] == "git")
    assert git["status"] == "missing"


def test_doctor_old_git_version_is_warning(stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.on("git", stdout="git version 2.25.1\n")
    stub_run_cmd.on("nvidia-smi", returncode=NOT_FOUND)
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0  # warn, not missing
    document = json.loads(result.output)
    git = next(check for check in document["checks"] if check["name"] == "git")
    assert git["status"] == "warn"


def test_doctor_check_network_ok() -> None:
    respx.head("https://huggingface.co/api/models/gpt2").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["doctor", "--json", "--check-network"])
    assert result.exit_code == 0
    document = json.loads(result.output)
    network = next(c for c in document["checks"] if c["name"] == "network")
    assert network["status"] == "ok"
    assert "200" in network["detail"]


def test_doctor_check_network_failure_is_warning() -> None:
    respx.head("https://huggingface.co/api/models/gpt2").mock(
        side_effect=httpx.ConnectError("no route")
    )
    result = runner.invoke(app, ["doctor", "--json", "--check-network"])
    assert result.exit_code == 0  # network problems are warnings, not failures
    document = json.loads(result.output)
    network = next(c for c in document["checks"] if c["name"] == "network")
    assert network["status"] == "warn"


def test_doctor_reports_invalid_manifest(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "reprollm.yaml").write_text("project: {}\n")  # invalid: name missing
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["doctor", "--json"])
    document = json.loads(result.output)
    docs = next(c for c in document["checks"] if c["name"] == "reprollm-documents")
    assert docs["status"] == "warn"
    assert "INVALID" in docs["detail"]
