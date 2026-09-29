"""M8-T04 performance boundary: large-repository audit stays interactive.

Marked ``slow``; CI runs it in the nightly workflow, not per-PR (spec M8-T04).
Budgets: a 20 000-file repository with 500 Python files audits in < 10 s and
``init`` completes in < 15 s on current runners.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


def test_large_repo_audit_budget(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from reprollm.cli.main import app

    repo = tmp_path / "big"
    repo.mkdir()
    (repo / "requirements.txt").write_text("torch==2.8.0\n", encoding="utf-8")
    (repo / "README.md").write_text("# Big repo\nbenchmark accuracy\n", encoding="utf-8")
    for i in range(500):
        (repo / f"m{i:04d}.py").write_text("import os\n", encoding="utf-8")
    for i in range(19_500):
        (repo / f"d{i:05d}.dat").write_text("x\n", encoding="utf-8")

    from tests.conftest import make_git_repo

    make_git_repo(repo)
    from tests.conftest import commit_all

    commit_all(repo)

    runner = CliRunner()
    monkeypatch.chdir(repo)

    start = time.monotonic()
    result = runner.invoke(app, ["audit", ".", "--fail-on", "never", "--format", "json"])
    elapsed = time.monotonic() - start
    assert result.exit_code == 0, result.output
    assert elapsed < 10.0, f"audit took {elapsed:.1f}s on 20k files (budget 10s)"


def test_large_repo_init_budget(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from reprollm.cli.main import app

    repo = tmp_path / "big"
    repo.mkdir()
    (repo / "requirements.txt").write_text("torch==2.8.0\n", encoding="utf-8")
    for i in range(500):
        (repo / f"m{i:04d}.py").write_text("import vllm\n", encoding="utf-8")
    for i in range(2_000):
        (repo / f"d{i:05d}.dat").write_text("x\n", encoding="utf-8")

    runner = CliRunner()
    monkeypatch.chdir(repo)
    start = time.monotonic()
    result = runner.invoke(app, ["init", "."])
    elapsed = time.monotonic() - start
    assert result.exit_code == 0, result.output
    assert elapsed < 15.0, f"init took {elapsed:.1f}s (budget 15s)"
