"""doctor CLI tests (M1-T07)."""

import json
from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.proc import NOT_FOUND
from tests.conftest import CmdStub
from tests.unit.lock.conftest import hf_mock as hf_mock

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_hf_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("HF_ENDPOINT", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(name, raising=False)


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


def test_doctor_accepts_supported_apple_git_version(stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.on("git", stdout="git version 2.50.1 (Apple Git-155)\n")
    stub_run_cmd.on("nvidia-smi", returncode=NOT_FOUND)
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    checks = json.loads(result.output)["checks"]
    assert next(check for check in checks if check["name"] == "git")["status"] == "ok"


def test_doctor_check_network_ok(hf_mock: respx.MockRouter) -> None:
    result = runner.invoke(app, ["doctor", "--json", "--check-network"])
    assert result.exit_code == 0
    document = json.loads(result.output)
    network = next(c for c in document["checks"] if c["name"] == "network")
    assert network["status"] == "ok"
    assert "gpt2" in network["detail"]
    request = hf_mock.calls.last.request
    assert request.method == "GET"
    assert str(request.url) == "https://huggingface.co/api/models/gpt2/revision/main"


def test_doctor_check_network_failure_is_warning(
    monkeypatch: pytest.MonkeyPatch, hf_mock: respx.MockRouter
) -> None:
    delays = []
    monkeypatch.setattr("reprollm.lock.hf_client.time.sleep", delays.append)
    route = hf_mock.get("https://huggingface.co/api/models/gpt2/revision/main").mock(
        side_effect=httpx.ConnectError("no route; hf_FAKE_PRIVATE_TOKEN")
    )
    result = runner.invoke(app, ["doctor", "--json", "--check-network"])
    assert result.exit_code == 0  # network problems are warnings, not failures
    document = json.loads(result.output)
    network = next(c for c in document["checks"] if c["name"] == "network")
    assert network["status"] == "warn"
    assert "network_error" in network["detail"]
    assert route.call_count == 3
    assert delays == [0.5, 1.5]
    assert "hf_FAKE_PRIVATE_TOKEN" not in result.output


def test_doctor_network_honors_endpoint_and_keeps_token_private(
    monkeypatch: pytest.MonkeyPatch, hf_mock: respx.MockRouter
) -> None:
    monkeypatch.setenv("HF_ENDPOINT", "https://hf-mirror.example.com")
    token = "hf_DOCTOR_TEST_ONLY"
    monkeypatch.setenv("HF_TOKEN", token)
    route = hf_mock.get("https://hf-mirror.example.com/api/models/gpt2/revision/main").mock(
        return_value=httpx.Response(403, text=token)
    )
    result = runner.invoke(app, ["doctor", "--json", "--check-network"])
    assert result.exit_code == 0, result.output
    network = next(c for c in json.loads(result.output)["checks"] if c["name"] == "network")
    assert network["status"] == "warn"
    assert "hf_api_forbidden" in network["detail"]
    assert route.call_count == 1
    assert route.calls.last.request.headers["Authorization"] == f"Bearer {token}"
    assert token not in result.output


def test_doctor_invalid_hub_metadata_is_warning(hf_mock: respx.MockRouter) -> None:
    hf_mock.get("https://huggingface.co/api/models/gpt2/revision/main").mock(
        return_value=httpx.Response(200, json={"siblings": []})
    )
    result = runner.invoke(app, ["doctor", "--json", "--check-network"])
    assert result.exit_code == 0, result.output
    network = next(c for c in json.loads(result.output)["checks"] if c["name"] == "network")
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
