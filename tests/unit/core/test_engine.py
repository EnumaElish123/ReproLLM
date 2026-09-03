"""Audit engine tests (spec §11) — M1 subset (Level 0, core profile)."""

from pathlib import Path

import pytest

from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import materialize_repo


def test_level0_clean_repo_two_passes(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    report = run_audit(repo)
    assert report.level == 0
    assert report.profiles.resolved == ["core"]
    assert report.profiles.declared == []
    assert report.summary.pass_ == 2
    assert report.summary.critical == 0
    assert report.summary.skipped == 0
    assert report.findings[0].severity == Severity.PASS


def test_report_is_deterministic_modulo_timestamp(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    first = run_audit(repo).model_dump(mode="json")
    second = run_audit(repo).model_dump(mode="json")
    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_level0_not_a_git_repo(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    report = run_audit(repo)
    assert report.level == 0
    by_id = {f.rule_id: f for f in report.findings}
    assert by_id["code.git_repo"].status == FindingStatus.FAIL
    assert by_id["code.git_repo"].severity == Severity.CRITICAL
    assert by_id["code.git_commit"].status == FindingStatus.SKIPPED
    assert report.summary.critical == 1
    assert report.summary.skipped == 1


def test_unknown_profile_is_user_error(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    with pytest.raises(UserError, match="unknown profile"):
        run_audit(repo, profile_names=["made_up"])


def test_core_may_not_be_declared(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    with pytest.raises(UserError, match="core"):
        run_audit(repo, profile_names=["core"])


def test_documents_section_hashes(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    report = run_audit(repo)
    assert report.documents.manifest is None
    assert report.documents.lock is None
    assert report.documents.runs == 0
