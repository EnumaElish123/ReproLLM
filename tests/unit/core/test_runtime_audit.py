"""Run loading, latest selection and hand-written project bindings (M5-T06)."""

import json
from datetime import timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from reprollm.core.yaml_io import dump_yaml
from reprollm.run.reader import list_runs
from reprollm.schemas.run_record import RunRecord
from tests.unit.rules.test_runtime_consistency import (
    NOW,
    manifest,
    observation,
    project_rules,
    run_record,
)


def write_run(root: Path, run: RunRecord) -> Path:
    path = root / ".reprollm/runs" / run.run_id / "run.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(run.model_dump_json())
    return path


def test_context_sorts_runs_by_started_time_and_ties_by_id(tmp_path: Path) -> None:
    early = run_record(run_id="20261005T093000Z-ffffff")
    later = run_record(run_id="20261005T093000Z-000000", started_at=NOW + timedelta(seconds=1))
    ctx = AuditContext(tmp_path, runs=[later, early])
    assert ctx.runs == [early, later] and ctx.latest_run is later


def test_run_order_uses_timezones_then_id_and_handles_missing_time(tmp_path: Path) -> None:
    missing = run_record(started_at=None)
    early = run_record(run_id="20261005T090000Z-ffffff", started_at=NOW)
    tie = run_record(
        run_id="20261005T090001Z-abcdef",
        started_at=NOW.astimezone(timezone(timedelta(hours=8))),
    )
    for record in (missing, tie, early):
        write_run(tmp_path, record)
    records, warnings = list_runs(tmp_path)
    assert not warnings and records == [tie, early, missing]
    ctx = AuditContext(tmp_path, runs=records)
    assert ctx.runs == [missing, early, tie]


def test_audit_skips_run_file_symlink_outside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "reprollm.yaml").write_text(dump_yaml(manifest()))
    outside = tmp_path / "outside.json"
    outside.write_text(run_record().model_dump_json())
    target = write_run(root, run_record())
    target.unlink()
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    diagnostics: list[str] = []
    report = run_audit(root, diagnostics=diagnostics)
    assert report.level == 1 and report.documents.runs == 0
    assert any("outside the repository" in entry for entry in diagnostics)
    assert str(outside) not in str(diagnostics)


def test_audit_loads_latest_valid_run_and_warns_for_corruption(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text(dump_yaml(manifest(generation={"temperature": 0.0})))
    write_run(
        tmp_path, run_record(bindings_observed={"generation.temperature": [observation(1.0)]})
    )
    write_run(
        tmp_path,
        run_record(
            run_id="20261005T093001Z-abcdef",
            started_at=NOW + timedelta(seconds=1),
            bindings_observed={"generation.temperature": [observation("0")]},
        ),
    )
    broken = tmp_path / ".reprollm/runs/20261005T093002Z-abcdef/run.json"
    broken.parent.mkdir()
    broken.write_text('{"secret":"must-not-echo"')
    diagnostics = []
    report = run_audit(tmp_path, diagnostics=diagnostics)
    by_id = {f.rule_id: f for f in report.findings}
    assert report.level == 2 and report.documents.runs == 2
    assert by_id["exec.run_recorded"].status.value == "pass"
    assert by_id["consistency.generation_params"].status.value == "pass"
    assert len(diagnostics) == 1 and "run.json" in diagnostics[0]
    result = CliRunner().invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "never"]
    )
    assert result.exit_code == 0 and json.loads(result.stdout)["documents"]["runs"] == 2
    assert "warning:" in result.stderr and "run.json" in result.stderr
    assert "must-not-echo" not in result.output


def test_corrupt_only_run_does_not_claim_valid_runtime_truth(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text(dump_yaml(manifest()))
    path = write_run(tmp_path, run_record())
    path.write_text("not json")
    report = run_audit(tmp_path)
    assert report.documents.runs == 0 and report.level == 1
    assert (
        next(f for f in report.findings if f.rule_id == "exec.run_recorded").status.value == "fail"
    )


def test_handwritten_custom_binding_is_audited_with_project_severity(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text(
        dump_yaml(manifest(custom={"privacy": {"alpha": 0.25}}))
    )
    write_run(
        tmp_path,
        run_record(bindings_observed={"custom.privacy.alpha": [observation(0.5, key="--alpha")]}),
    )
    (tmp_path / ".reprollm/project-rules.yaml").write_text(dump_yaml(project_rules()))
    profiles = tmp_path / ".reprollm/profiles"
    profiles.mkdir()
    (profiles / "strict.yaml").write_text(
        "schema_version: 1\nname: strict\ndescription: Test\nextends: [core]\nrules: []\n"
        "severity_overrides: {consistency.custom_fields: CRITICAL}\n"
    )
    report = run_audit(tmp_path, profile_names=["strict"])
    (finding,) = [f for f in report.findings if f.rule_id == "consistency.custom_fields"]
    assert finding.status.value == "fail" and finding.severity.value == "WARNING"
    assert finding.severity_origin == "project_rule"


def test_invalid_project_rules_fail_without_echoing_parser_input(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text(dump_yaml(manifest()))
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/project-rules.yaml").write_text("rules: [private-input")
    with pytest.raises(UserError, match="project-rules.yaml") as exc:
        run_audit(tmp_path)
    assert "private-input" not in str(exc.value)
