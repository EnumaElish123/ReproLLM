"""M2F-T01: persisted audit metadata normalization (F-01, F-02)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import materialize_repo

runner = CliRunner()


def _audit(monkeypatch, repo: Path, target_arg: str) -> dict:
    monkeypatch.chdir(repo if target_arg == "." else repo.parent)
    result = runner.invoke(app, ["audit", target_arg, "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


def test_relative_and_absolute_invocations_are_identical(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    repo = repo.resolve()
    via_relative = _audit(monkeypatch, repo, "hf_vllm_eval")
    via_absolute = _audit(monkeypatch, repo.parent, str(repo))
    via_dot = _audit(monkeypatch, repo, ".")
    for document in (via_relative, via_absolute, via_dot):
        document.pop("generated_at")
    assert via_relative == via_absolute == via_dot


def test_target_is_root_relative_and_never_absolute(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    document = _audit(monkeypatch, repo.parent, str(repo))
    assert document["target"] == "."
    serialized = json.dumps(document)
    assert str(tmp_path) not in serialized  # no temp-checkout prefix anywhere
    assert "/home/" not in serialized


def test_subdirectory_target_is_relative_to_root(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", "configs", "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["target"] == "configs"


def test_symlinked_invocation_normalizes(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    link = tmp_path / "link-to-repo"
    link.symlink_to(repo)
    document = _audit(monkeypatch, tmp_path, "link-to-repo")
    assert document["target"] == "."


def test_generated_at_second_precision_with_z(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    document = _audit(monkeypatch, repo, ".")
    stamp = document["generated_at"]
    assert stamp.endswith("Z")
    assert "." not in stamp  # no microseconds
    from datetime import datetime

    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert parsed.microsecond == 0
