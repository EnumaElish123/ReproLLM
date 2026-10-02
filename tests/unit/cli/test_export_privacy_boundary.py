"""Full export persistence removes machine-specific data, preserving portable values."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import commit_all, make_git_repo

pytestmark = pytest.mark.security

FAKE_USER = "fake-export-user"
FAKE_HOST = "fake-export-host"
FAKE_UNIX_PATH = "/Users/fake-private-user/private-study"
FAKE_WINDOWS_PATH = r"C:\fake-private-user\private-study"
FAKE_KEY = "sk-" + "a" * 40


@pytest.mark.parametrize("template", ["default", "neurips", "acl", "acm"])
@pytest.mark.parametrize("username", [FAKE_USER, "models", "role"])
def test_export_removes_paths_identities_and_secrets_before_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, template: str, username: str
) -> None:
    repo = make_git_repo(tmp_path / "experiment")
    inside_root = str(repo / "configs" / "run.json")
    private_text = (
        f"{FAKE_UNIX_PATH}; {FAKE_WINDOWS_PATH}; {inside_root}; "
        f"owner={username}; node={FAKE_HOST}; {FAKE_KEY}"
    )
    manifest = {
        "schema_version": 1,
        "project": {"name": "portable-privacy-trial"},
        "experiment": {"profiles": []},
        "models": {"primary": {"provider": "huggingface", "id": "fake/portable-model"}},
        "datasets": {"eval": {"provider": "local", "id": "relative/data", "split": "test"}},
        "prompts": {"task": {"text": "Use </s> and configs/*.yaml unchanged.", "format": "plain"}},
        "generation": {"stop": ["</s>"]},
        "inference": {
            "backend": "other",
            "params": {
                "source_url": "https://example.invalid/dataset",
                "glob": "configs/*.yaml",
                "relative": "configs/task.yaml",
                "private_description": private_text,
            },
        },
        "privacy": {
            "threat_model": private_text,
            "mechanism": {"name": f"declared-mechanism {private_text}"},
        },
    }
    (repo / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr("getpass.getuser", lambda: username)
    monkeypatch.setattr("socket.gethostname", lambda: FAKE_HOST)
    output = tmp_path / f"{template}.md"
    result = CliRunner().invoke(
        app, ["export", str(repo), "--template", template, "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    document = output.read_text(encoding="utf-8")
    for private in [FAKE_UNIX_PATH, FAKE_WINDOWS_PATH, inside_root, FAKE_HOST, FAKE_KEY]:
        assert private not in document
    assert f"owner={username}" not in document
    assert "owner=<REDACTED:username>" in document
    assert "| primary | huggingface | fake/portable-model" in document
    for marker in [
        "<REDACTED:path>",
        "<REDACTED:username>",
        "<REDACTED:hostname>",
        "<REDACTED:openai>",
    ]:
        assert marker in document
    for portable in [
        "configs/run.json",
        "configs/task.yaml",
        "https://example.invalid/dataset",
        "configs/*.yaml",
        "</s>",
        "fake/portable-model",
        "relative/data",
    ]:
        assert portable in document
    assert "## Experiment identity" in document
    assert "https://github.com/EnumaElish123/ReproLLM" in document
    if template == "neurips":
        assert "Hyperparameters / runs" in document
        privacy = next(
            line for line in document.splitlines() if line.startswith("| 5.7 Attack/defense |")
        )
        assert privacy.count("<REDACTED:hostname>") == 2
        assert privacy.count("<REDACTED:path>") == 4


def test_export_preserves_portable_dot_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_git_repo(tmp_path / "relative-experiment")
    manifest = {
        "schema_version": 1,
        "project": {"name": "relative-path-trial"},
        "experiment": {"profiles": []},
        "models": {"primary": {"provider": "huggingface", "id": "fake/portable-model"}},
        "inference": {"params": {"relative": "./configs/task.yaml"}},
    }
    (repo / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr("getpass.getuser", lambda: FAKE_USER)
    monkeypatch.setattr("socket.gethostname", lambda: FAKE_HOST)
    output = tmp_path / "relative.md"
    result = CliRunner().invoke(app, ["export", str(repo), "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert "- `params.relative`: ./configs/task.yaml" in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("template", ["default", "neurips", "acl", "acm"])
def test_export_keyed_opaque_secret_is_not_hidden_by_markdown_backticks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, template: str
) -> None:
    monkeypatch.setattr("getpass.getuser", lambda: FAKE_USER)
    monkeypatch.setattr("socket.gethostname", lambda: FAKE_HOST)
    repo = make_git_repo(tmp_path / "keyed-experiment")
    opaque_fake = "opaque-validation-only-credential"
    manifest = {
        "schema_version": 1,
        "project": {"name": "keyed-value-trial"},
        "experiment": {"profiles": []},
        "models": {"primary": {"provider": "huggingface", "id": "fake/portable-model"}},
        "inference": {
            "params": {
                "api_key": opaque_fake,
                "nested": {"password": "opaque-nested-validation-value"},
                "access_token": ["opaque-list-validation-value", {"label": "opaque-map-value"}],
                "records": [{"auth_token": "opaque-record-validation-value"}],
                "private_description": "ordinary scientific metadata",
                "public_number": 12345678,
                "public_enabled": True,
                "public_nested": {"name": "ordinary nested metadata", "count": 42},
            }
        },
    }
    (repo / "reprollm.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    commit_all(repo)
    output = tmp_path / "keyed.md"
    result = CliRunner().invoke(
        app, ["export", str(repo), "--template", template, "--output", str(output)]
    )
    assert result.exit_code == 0, result.output
    document = output.read_text(encoding="utf-8")
    for opaque in [
        opaque_fake,
        "opaque-nested-validation-value",
        "opaque-list-validation-value",
        "opaque-map-value",
        "opaque-record-validation-value",
    ]:
        assert opaque not in document
    assert "<REDACTED:generic_kv>" in document
    assert "- `params.private_description`: ordinary scientific metadata" in document
    assert "- `params.public_number`: 12345678" in document
    assert "- `params.public_enabled`: True" in document
    assert "ordinary nested metadata" in document
    assert "- `params.public_nested.count`: 42" in document
