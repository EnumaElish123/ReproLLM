"""Audit engine tests (spec §11) — M1 subset (Level 0, core profile)."""

from pathlib import Path

import pytest

from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from tests.conftest import materialize_repo


def test_level0_clean_repo_full_core(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    report = run_audit(repo)
    assert report.level == 0
    assert report.profiles.resolved == ["core"]
    assert report.profiles.declared == []
    by_id = {f.rule_id: (f.status.value, f.severity.value) for f in report.findings}
    assert by_id == {
        "code.git_repo": ("pass", "PASS"),
        "code.git_commit": ("pass", "PASS"),
        "code.clean_tree": ("pass", "PASS"),
        "code.no_untracked": ("pass", "PASS"),
        "code.submodules_initialized": ("skipped", "INFO"),
        "code.remote_recorded": ("fail", "INFO"),
        "env.dependency_manifest_present": ("pass", "PASS"),
        "env.lockfile_present": ("fail", "WARNING"),
        "env.llm_critical_deps_pinned": ("fail", "WARNING"),
        "env.python_version_declared": ("fail", "WARNING"),
        "env.secret_files_ignored": ("pass", "PASS"),
        "env.reprollm_initialized": ("fail", "INFO"),
    }
    assert report.summary.pass_ == 6
    assert report.summary.warning == 3
    assert report.summary.info == 2
    assert report.summary.skipped == 1
    assert report.summary.critical == 0


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
    by_id = {f.rule_id: (f.status.value, f.severity.value) for f in report.findings}
    assert by_id["code.git_repo"] == ("fail", "CRITICAL")
    assert by_id["code.git_commit"] == ("skipped", "INFO")
    assert by_id["code.clean_tree"] == ("skipped", "INFO")
    assert by_id["env.dependency_manifest_present"] == ("pass", "PASS")
    assert by_id["env.lockfile_present"] == ("pass", "PASS")  # all-== requirements
    assert by_id["env.llm_critical_deps_pinned"] == ("pass", "PASS")
    assert by_id["env.python_version_declared"] == ("fail", "WARNING")
    assert report.summary.critical == 1
    assert report.summary.skipped == 5


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
