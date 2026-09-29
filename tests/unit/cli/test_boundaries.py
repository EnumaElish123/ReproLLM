"""M8-T04 boundary matrix: hostile inputs get actionable errors, never tracebacks."""

from __future__ import annotations

from pathlib import Path

import pytest

from reprollm.cli.main import cli
from tests.conftest import make_git_repo


def _cli(monkeypatch, argv: list[str]) -> tuple[int, str]:
    import contextlib
    import io

    out = io.StringIO()
    err = io.StringIO()
    monkeypatch.setattr("sys.argv", ["reprollm", *argv])
    with (
        pytest.raises(SystemExit) as excinfo,
        contextlib.redirect_stdout(out),
        contextlib.redirect_stderr(err),
    ):
        cli()
    return excinfo.value.code, out.getvalue() + err.getvalue()


def test_empty_manifest_is_user_error(tmp_path: Path, monkeypatch) -> None:
    repo = make_git_repo(tmp_path / "r")
    (repo / "reprollm.yaml").write_text("", encoding="utf-8")
    code, text = _cli(monkeypatch, ["audit", str(repo)])
    assert code == 2
    assert "reprollm.yaml" in text
    assert "Traceback" not in text


def test_corrupt_lock_is_user_error(tmp_path: Path, monkeypatch) -> None:
    repo = make_git_repo(tmp_path / "r")
    (repo / "reprollm.yaml").write_text(
        "project:\n  name: x\nexperiment:\n  profiles: []\n", encoding="utf-8"
    )
    (repo / "reprollm.lock").write_text("{{{{not yaml", encoding="utf-8")
    code, text = _cli(monkeypatch, ["audit", str(repo), "--fail-on", "never"])
    assert code == 2
    assert "reprollm.lock" in text
    assert "Traceback" not in text


def test_future_lock_schema_rejected_with_upgrade_hint(tmp_path: Path, monkeypatch) -> None:
    repo = make_git_repo(tmp_path / "r")
    (repo / "reprollm.yaml").write_text(
        "project:\n  name: x\nexperiment:\n  profiles: []\n", encoding="utf-8"
    )
    (repo / "reprollm.lock").write_text(
        "schema_version: 99\nreprollm_version: x\n"
        "generated_at: 2026-01-01T00:00:00Z\nmanifest_sha256: sha256:00\n"
        "project_rules_sha256: null\nresolution: {mode: online}\n",
        encoding="utf-8",
    )
    code, text = _cli(monkeypatch, ["audit", str(repo), "--fail-on", "never"])
    assert code == 2
    assert "schema_version 99" in text
    assert "upgrade" in text.lower()


def test_manifest_only_repo_audits_cleanly(tmp_path: Path, monkeypatch) -> None:
    """A repository containing only reprollm.yaml audits; findings, no crash."""
    repo = make_git_repo(tmp_path / "r")
    (repo / "reprollm.yaml").write_text(
        "project:\n  name: x\nexperiment:\n  profiles: []\n", encoding="utf-8"
    )
    from tests.conftest import commit_all

    commit_all(repo)
    code, text = _cli(monkeypatch, ["audit", str(repo), "--format", "json"])
    assert code in (0, 1)
    assert '"level": 1' in text


def test_non_utf8_filenames_do_not_crash_audit(tmp_path: Path, monkeypatch) -> None:
    """A byte filename git cannot index must not take the audit down. git add
    fails on raw 0xE9 bytes on Windows, so this file simply stays untracked —
    which is itself a path the scanner must tolerate."""
    repo = make_git_repo(tmp_path / "r")
    (repo / "ok.py").write_text("x = 1\n", encoding="utf-8")
    from tests.conftest import commit_all

    commit_all(repo)
    try:
        import os

        with open(
            os.path.join(str(repo), "bad-\udce9.py"),
            "w",
            encoding="utf-8",
            errors="surrogateescape",
        ) as handle:
            handle.write("x = 1\n")
    except (OSError, ValueError):
        pytest.skip("filesystem rejects surrogate filenames")
    code, text = _cli(monkeypatch, ["audit", str(repo), "--fail-on", "never"])
    assert code in (0, 1)
    assert "Traceback" not in text


def test_help_first_lines_are_actionable_summaries() -> None:
    """Every registered command's help starts with a standalone one-liner."""
    from typer.main import get_command as _get

    from reprollm.cli.main import app

    def walk(group) -> list[str]:
        problems: list[str] = []
        for name, cmd in group.commands.items():
            if hasattr(cmd, "commands"):
                problems.extend(walk(cmd))
                continue
            first = (cmd.help or "").strip().splitlines()
            if not first or not first[0]:
                problems.append(name)
        return problems

    assert walk(_get(app)) == [], "commands missing a one-line help summary"
