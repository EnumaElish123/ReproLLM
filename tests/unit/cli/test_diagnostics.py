"""M2F-T07: scan diagnostics surface under -v (F-08)."""

import json
from pathlib import Path

from reprollm.cli.main import app
from reprollm.core.engine import run_audit
from reprollm.core.git import inspect_git
from reprollm.core.scanner import RepoScanner
from tests.conftest import materialize_repo


def _many_python_repo(tmp_path: Path, count: int) -> Path:
    repo = tmp_path / "many"
    repo.mkdir()
    for i in range(count):
        (repo / f"m{i:04d}.py").write_text("import os\n")
    (repo / "requirements.txt").write_text("torch==2.8.0\n")
    return repo


def test_truncation_diagnostic_collected(tmp_path: Path) -> None:
    repo = _many_python_repo(tmp_path, 501)
    diagnostics: list[str] = []
    run_audit(repo, diagnostics=diagnostics)
    assert diagnostics == ["python file scan truncated to 500 of 501 files"]


def test_diagnostic_reported_once_despite_repeated_access(tmp_path: Path) -> None:
    repo = _many_python_repo(tmp_path, 502)
    scanner = RepoScanner(repo, inspect_git(repo))
    scanner.python_files()
    scanner.python_files()
    assert scanner.warnings.count("python file scan truncated to 500 of 502 files") == 1


def test_syntax_and_unreadable_diagnostics_collected(tmp_path: Path) -> None:
    repo = tmp_path / "broken"
    repo.mkdir()
    (repo / "bad.py").write_text("def f(:\n")
    (repo / "requirements.txt").write_text("this is === not a requirement!!!\n")
    diagnostics: list[str] = []
    run_audit(repo, diagnostics=diagnostics)
    assert any("syntax error" in entry for entry in diagnostics)
    assert any("requirements.txt:1" in entry for entry in diagnostics)


def test_verbose_prints_diagnostics_to_stderr_json_stays_clean(monkeypatch, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "broken.py").write_text("def f(:\n")
    runner = CliRunner()
    monkeypatch.chdir(repo)
    # the global -v precedes the subcommand so the callback records it
    result = runner.invoke(app, ["-v", "audit", ".", "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0
    document = json.loads(result.stdout)  # exactly one JSON document on stdout
    assert document["level"] == 0
    assert "syntax error" in result.stderr
    assert "scan:" in result.stderr


def test_no_diagnostics_without_verbose_by_default(monkeypatch, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "broken.py").write_text("def f(:\n")
    runner = CliRunner()
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", ".", "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0
    assert "syntax error" not in (result.stderr + result.stdout)


def test_diagnostics_never_contain_absolute_paths(tmp_path: Path) -> None:
    repo = _many_python_repo(tmp_path, 501)
    (repo / "bad.py").write_text("def f(:\n")
    diagnostics: list[str] = []
    run_audit(repo, diagnostics=diagnostics)
    assert str(tmp_path) not in "\n".join(diagnostics)
    assert "/home/" not in "\n".join(diagnostics)
