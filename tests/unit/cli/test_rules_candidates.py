"""M7-T04: candidate lifecycle visibility; no discovery or model request."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.project_rules import load_project_rules
from reprollm.schemas.discover_candidates import Candidate, DiscoverCandidates

runner = CliRunner()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: candidate-trial}\n"
        "experiment: {profiles: []}\ncustom: {alpha: 0.25}\n",
        encoding="utf-8",
    )
    discover = tmp_path / ".reprollm" / "discover"
    discover.mkdir(parents=True)
    document = DiscoverCandidates(
        reprollm_version="0.6.1",
        generated_at=datetime(2026, 10, 2, tzinfo=timezone.utc),
        model="fake-model-no-request",
        input_files=["README.md"],
        candidates=[
            Candidate(
                id=f"c-{number:06x}",
                kind="parameter",
                name=name,
                suggested_field=f"custom.{name}",
                suggested_severity="WARNING",
                confidence="high",
                rationale=f"Keep {name} reproducible.",
            )
            for number, name in enumerate(("alpha", "beta", "gamma"), start=1)
        ],
    )
    (discover / "20261002T000000Z.json").write_text(
        document.model_dump_json(indent=2), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _candidate_line(text: str, candidate_id: str) -> str:
    return next(line for line in text.splitlines() if f"candidate {candidate_id}" in line)


def test_pending_candidates_visible_without_project_rules(repo: Path) -> None:
    result = runner.invoke(app, ["rules", "list"])
    assert result.exit_code == 0, result.output
    assert "[pending]" in _candidate_line(result.output, "c-000001")
    assert not (repo / ".reprollm" / "project-rules.yaml").exists()


def test_ignored_candidates_visible_without_accepted_rules(repo: Path) -> None:
    assert runner.invoke(app, ["rules", "ignore", "c-000002"]).exit_code == 0
    result = runner.invoke(app, ["rules", "list"])
    assert result.exit_code == 0, result.output
    assert "[ignored]" in _candidate_line(result.output, "c-000002")
    assert "[pending]" in _candidate_line(result.output, "c-000001")


def test_accepted_candidate_not_pending(repo: Path) -> None:
    accepted = runner.invoke(app, ["rules", "accept", "c-000001"])
    assert accepted.exit_code == 0, accepted.output
    result = runner.invoke(app, ["rules", "list"])
    assert result.exit_code == 0, result.output
    assert "project.alpha" in result.output
    assert "[accepted]" in _candidate_line(result.output, "c-000001")
    assert "[pending]" in _candidate_line(result.output, "c-000003")


def test_mixed_states_use_project_rules_document(repo: Path) -> None:
    assert runner.invoke(app, ["rules", "accept", "c-000001"]).exit_code == 0
    assert runner.invoke(app, ["rules", "ignore", "c-000002"]).exit_code == 0
    result = runner.invoke(app, ["rules", "list"])
    assert "[accepted]" in _candidate_line(result.output, "c-000001")
    assert "[ignored]" in _candidate_line(result.output, "c-000002")
    assert "[pending]" in _candidate_line(result.output, "c-000003")


def test_json_without_accepted_rules_stays_array(repo: Path) -> None:
    result = runner.invoke(app, ["rules", "list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_json_with_rules_preserves_current_rule_payload(repo: Path) -> None:
    assert runner.invoke(app, ["rules", "accept", "c-000001"]).exit_code == 0
    assert runner.invoke(app, ["rules", "ignore", "c-000002"]).exit_code == 0
    document = load_project_rules(repo)
    assert document is not None
    result = runner.invoke(app, ["rules", "list", "--json"])
    assert result.exit_code == 0
    assert (
        result.output
        == json.dumps([rule.model_dump(mode="json") for rule in document.rules], indent=2) + "\n"
    )


def test_without_discovery_keeps_existing_message(repo: Path) -> None:
    (repo / ".reprollm" / "discover" / "20261002T000000Z.json").unlink()
    result = runner.invoke(app, ["rules", "list"])
    assert result.exit_code == 0
    assert result.output == "No project rules accepted. Add one with `reprollm rules add`.\n"
