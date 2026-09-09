"""exec.* rule + Level 1 engine tests (spec §12.3, M2-T06 acceptance)."""

from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.core.engine import run_audit
from reprollm.rules.exec_ import (
    CommandDeclaredRule,
    ProfileDetectionMismatchRule,
    RunRecordedRule,
    SeedDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import materialize_repo


def write_manifest(repo: Path, text: str) -> None:
    (repo / "reprollm.yaml").write_text(text, encoding="utf-8")


MINIMAL_MANIFEST = """\
schema_version: 1
project:
  name: eval-demo
experiment:
  profiles: [inference]
"""


def test_exec_rules_on_minimal_manifest(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(repo, MINIMAL_MANIFEST)
    report = run_audit(repo)
    assert report.level == 1
    by_id = {f.rule_id: f for f in report.findings}
    assert by_id["exec.command_declared"].status == FindingStatus.FAIL
    assert by_id["exec.command_declared"].severity == Severity.WARNING
    assert by_id["exec.seed_declared"].status == FindingStatus.FAIL
    assert by_id["exec.run_recorded"].severity == Severity.INFO
    assert by_id["exec.run_recorded"].status == FindingStatus.FAIL
    assert by_id["code.clean_tree"].status == FindingStatus.PASS  # full core still runs


def test_exec_seed_passes_with_generation_seed(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(
        repo,
        MINIMAL_MANIFEST.replace("experiment:", "generation:\n  seed: 42\nexperiment:"),
    )
    ctx = AuditContext(repo, level=1, manifest=_load(repo))
    assert SeedDeclaredRule().check(ctx) == []


def test_exec_seed_passes_with_execution_seed(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(
        repo,
        MINIMAL_MANIFEST + "execution:\n  seed: 7\n",
    )
    ctx = AuditContext(repo, level=1, manifest=_load(repo))
    assert SeedDeclaredRule().check(ctx) == []


def test_exec_command_passes_when_declared(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(
        repo,
        MINIMAL_MANIFEST + "execution:\n  command: python eval.py\n",
    )
    ctx = AuditContext(repo, level=1, manifest=_load(repo))
    assert CommandDeclaredRule().check(ctx) == []


def test_exec_run_recorded_passes_with_runs(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    from reprollm.schemas.run_record import CommandInfo, RunRecord

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(repo, MINIMAL_MANIFEST)
    run = RunRecord(
        reprollm_version="0.1.0",
        run_id="20260101T000000Z-abcdef",
        status="completed",
        command=CommandInfo(argv=["true"], cwd="."),
    )
    ctx = AuditContext(repo, level=1, manifest=_load(repo), runs=[run])
    assert RunRecordedRule().check(ctx) == []
    del datetime, timezone


def test_mismatch_detected_high_not_declared(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    write_manifest(repo, MINIMAL_MANIFEST.replace("[inference]", "[]"))
    # detection finds nothing in this fixture → declared [] matches
    ctx = AuditContext(repo, level=1, manifest=_load(repo))
    ctx.declared_profiles = []
    assert ProfileDetectionMismatchRule().check(ctx) == []


def test_mismatch_declared_without_evidence(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(repo, MINIMAL_MANIFEST.replace("[inference]", "[inference, finetuning]"))
    report = run_audit(repo)
    mismatch = [f for f in report.findings if f.rule_id == "exec.profile_detection_mismatch"]
    # inference is declared AND detected (high) → no mismatch for it;
    # evaluation is detected at medium → below the high bar → no mismatch;
    # finetuning is declared with zero evidence → one INFO finding.
    assert len(mismatch) == 1
    assert "finetuning" in mismatch[0].message
    assert mismatch[0].severity == Severity.INFO


def test_mismatch_high_detected_undeclared(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(repo, MINIMAL_MANIFEST.replace("[inference]", "[]"))
    report = run_audit(repo)
    mismatch = [f for f in report.findings if f.rule_id == "exec.profile_detection_mismatch"]
    messages = " | ".join(f.message for f in mismatch)
    # inference detected high but not declared → flagged; evaluation (medium) not flagged
    assert "inference" in messages
    assert "evaluation" not in messages


def test_level0_forced_downgrade_hides_exec(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(repo, MINIMAL_MANIFEST)
    report = run_audit(repo, level=0)
    assert report.level == 0
    assert not any(f.rule_id.startswith("exec.") for f in report.findings)


def test_exec_rules_skipped_at_level0(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)  # no manifest
    report = run_audit(repo)
    assert report.level == 0
    assert not any(f.rule_id.startswith("exec.") for f in report.findings)


def test_invalid_manifest_exits_with_field_path(tmp_path: Path) -> None:
    import pytest

    from reprollm.core.errors import UserError

    repo = materialize_repo("hf_vllm_eval", tmp_path)
    write_manifest(repo, "project: {}\n")  # name missing
    with pytest.raises(UserError, match="project.name"):
        run_audit(repo)


def _load(repo: Path):
    from reprollm.core.yaml_io import load_manifest

    return load_manifest(repo / "reprollm.yaml")
