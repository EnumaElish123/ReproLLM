"""R06-B: format-lock ownership reaches real audit and export consumers (§12.2)."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import commit_all, make_git_repo

runner = CliRunner()
RULE = "env.llm_critical_deps_pinned"


def _foreign_lock_repo(tmp_path: Path) -> Path:
    root = make_git_repo(tmp_path / "project")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "experiment"\nrequires-python = ">=3.10"\ndependencies = ["torch>=2"]\n',
        encoding="utf-8",
    )
    tools = root / "tools"
    tools.mkdir()
    (tools / "pyproject.toml").write_text('[project]\nname = "tools"\n', encoding="utf-8")
    (tools / "uv.lock").write_text('[[package]]\nname = "torch"\n', encoding="utf-8")
    commit_all(root)
    return root


def test_unrelated_lock_warns_with_existing_evidence_and_thresholds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _foreign_lock_repo(tmp_path)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    result = runner.invoke(app, ["audit", str(root), "--format", "json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    findings = [finding for finding in report["findings"] if finding["rule_id"] == RULE]
    assert len(findings) == 1
    finding = findings[0]
    assert finding["status"] == "fail"
    assert finding["severity"] == "WARNING"
    assert finding["message"] == (
        "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
    )
    assert finding["fix_hint"] == "Pin torch exactly, e.g. `torch==<version>`."
    assert finding["evidence"] == [
        {
            "kind": "file",
            "path": "pyproject.toml",
            "field": None,
            "line": 4,
            "value": ">=2",
            "expected": None,
            "note": "declared as >=2",
        }
    ]
    by_id = {item["rule_id"]: item for item in report["findings"]}
    assert by_id["env.lockfile_present"]["status"] == "pass"
    assert by_id["env.dependency_manifest_present"]["status"] == "pass"
    for threshold, exit_code in [("warning", 1), ("never", 0)]:
        outcome = runner.invoke(app, ["audit", str(root), "--fail-on", threshold])
        assert outcome.exit_code == exit_code, outcome.output

    repeat = runner.invoke(app, ["audit", str(root), "--format", "json"])
    repeated_report = json.loads(repeat.stdout)
    report.pop("generated_at")
    repeated_report.pop("generated_at")
    assert repeated_report == report
    github = runner.invoke(app, ["audit", str(root), "--format", "github"])
    assert github.exit_code == 0, github.output
    assert f"::warning title=WARNING%3A {RULE},file=pyproject.toml,line=4::" in github.stdout
    assert finding["message"] in github.stdout

    initialized = runner.invoke(app, ["init", str(root)])
    assert initialized.exit_code == 0, initialized.output
    exported = runner.invoke(app, ["export", str(root)])
    assert exported.exit_code == 0, exported.output
    document = (root / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert RULE in document
    assert escape(finding["message"]) in document
    assert str(root) not in document
