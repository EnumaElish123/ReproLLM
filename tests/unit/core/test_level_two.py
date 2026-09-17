from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from reprollm.schemas.lock import GpuEnvLock

runner = CliRunner()


def _lock_openai_fixture(materialize, monkeypatch: pytest.MonkeyPatch, suffix: str) -> Path:
    root = materialize("openai_judge_eval", manifest="complete")
    monkeypatch.setattr(
        "reprollm.lock.resolver._resolve_gpu", lambda: GpuEnvLock(source="unavailable")
    )
    result = runner.invoke(app, ["lock", str(root)])
    assert result.exit_code == 0, f"{suffix}: {result.output}"
    return root


def test_lock_auto_detects_level_two_and_loads_context(materialize, monkeypatch) -> None:
    root = _lock_openai_fixture(materialize, monkeypatch, "level")

    report = run_audit(root)

    assert report.level == 2
    by_id = {finding.rule_id: finding for finding in report.findings}
    assert by_id["consistency.lock_fresh"].status.value == "pass"
    assert by_id["consistency.file_hashes"].status.value == "pass"


def test_manifest_edit_after_lock_reports_lock_fresh(materialize, monkeypatch) -> None:
    root = _lock_openai_fixture(materialize, monkeypatch, "manifest")
    path = root / "reprollm.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    findings = [
        finding
        for finding in run_audit(root).findings
        if finding.rule_id == "consistency.lock_fresh" and finding.status.value == "fail"
    ]

    assert len(findings) == 1
    assert "reprollm.yaml changed" in findings[0].message


def test_prompt_edit_after_lock_reports_file_hash(materialize, monkeypatch) -> None:
    root = _lock_openai_fixture(materialize, monkeypatch, "prompt")
    prompt = root / "prompts/judge.txt"
    prompt.write_text("changed judge prompt\n", encoding="utf-8")

    findings = [
        finding
        for finding in run_audit(root).findings
        if finding.rule_id == "consistency.file_hashes" and finding.status.value == "fail"
    ]

    assert len(findings) == 1
    assert findings[0].evidence[0].path == "prompts/judge.txt"


def test_project_rule_added_after_lock_reports_lock_fresh(materialize, monkeypatch) -> None:
    root = _lock_openai_fixture(materialize, monkeypatch, "project rules")
    rules = root / ".reprollm/project-rules.yaml"
    rules.parent.mkdir(exist_ok=True)
    rules.write_text("schema_version: 1\nrules: []\n", encoding="utf-8")

    findings = [
        finding
        for finding in run_audit(root).findings
        if finding.rule_id == "consistency.lock_fresh" and finding.status.value == "fail"
    ]

    assert len(findings) == 1
    assert "project-rules.yaml changed" in findings[0].message


@pytest.mark.parametrize(
    ("lock_text", "message"),
    [
        ("schema_version: 999\n", "newer schema_version 999"),
        ("schema_version: 1\nmodels: []\n", "invalid lock"),
    ],
)
def test_invalid_lock_is_actionable_exit_two(materialize, lock_text: str, message: str) -> None:
    root = materialize("openai_judge_eval", manifest="complete")
    (root / "reprollm.lock").write_text(lock_text, encoding="utf-8")

    with pytest.raises(UserError, match=message):
        run_audit(root)
