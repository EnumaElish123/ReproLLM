"""M9-T02: --format github emits workflow commands for CI annotations."""

from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import commit_all, materialize_repo

runner = CliRunner()


def test_github_format_emits_annotations(monkeypatch, tmp_path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    result = runner.invoke(app, ["audit", str(repo), "--format", "github", "--fail-on", "never"])
    assert result.exit_code == 0
    lines = result.output.splitlines()
    errors = [line for line in lines if line.startswith("::error")]
    assert errors, "critical findings must produce ::error commands"
    warnings = [line for line in lines if line.startswith("::warning")]
    assert warnings, "warning findings must produce ::warning commands"
    assert any("ReproLLM audit" in line for line in lines)


def test_github_format_error_includes_rule_and_message(monkeypatch, tmp_path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    result = runner.invoke(app, ["audit", str(repo), "--format", "github", "--fail-on", "never"])
    error_lines = [line for line in result.output.splitlines() if line.startswith("::error")]
    assert any("code.git_repo" in line for line in error_lines)
    for line in error_lines:
        assert "::" in line[2:], "must have proper annotation body"


def test_github_format_pass_only(monkeypatch, tmp_path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    commit_all(repo)
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", ".", "--format", "github", "--fail-on", "never"])
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert not any(line.startswith("::error") for line in lines), "clean repo must have no errors"
    notice = [line for line in lines if line.startswith("::notice") and "ReproLLM audit" in line]
    assert notice, "summary notice must be present"
    assert "0 critical" in notice[0]


def test_github_format_exit_codes(monkeypatch, tmp_path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    result = runner.invoke(app, ["audit", str(repo), "--format", "github"])
    assert result.exit_code == 1
    result = runner.invoke(app, ["audit", str(repo), "--format", "github", "--fail-on", "never"])
    assert result.exit_code == 0
