"""env.* rule tests (spec §12.2) — one PASS and one FAIL per rule."""

from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.rules.env import (
    DependencyManifestPresentRule,
    LlmCriticalDepsPinnedRule,
    LockfilePresentRule,
    PythonVersionDeclaredRule,
    ReprollmInitializedRule,
    SecretFilesIgnoredRule,
)
from reprollm.schemas.finding import Severity
from tests.conftest import materialize_repo


def _ctx(repo: Path, level: int = 0) -> AuditContext:
    return AuditContext(repo, level=level)


# --- env.dependency_manifest_present ----------------------------------------


def test_manifest_present_pass_on_fixture(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert DependencyManifestPresentRule().check(_ctx(repo)) == []


def test_manifest_missing_fails_on_no_deps_file(tmp_path: Path) -> None:
    repo = materialize_repo("no_deps_file", tmp_path)
    finding = DependencyManifestPresentRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.CRITICAL
    assert "no dependency manifest" in finding.message


# --- env.lockfile_present ----------------------------------------------------


def test_lockfile_present_warning_when_loose(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    finding = LockfilePresentRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.WARNING


def test_lockfile_present_pass_when_all_pinned(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    assert LockfilePresentRule().check(_ctx(repo)) == []


def test_lockfile_skipped_without_manifest(tmp_path: Path) -> None:
    repo = materialize_repo("no_deps_file", tmp_path)
    ctx = _ctx(repo)
    assert LockfilePresentRule().applies(ctx) is False


# --- env.llm_critical_deps_pinned -------------------------------------------


def test_llm_deps_unpinned_vllm_on_hf_fixture(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    findings = LlmCriticalDepsPinnedRule().check(_ctx(repo))
    assert [f.message.split(" ")[0] for f in findings] == ["vllm"]
    assert findings[0].severity == Severity.WARNING
    assert "==" in findings[0].fix_hint


def test_llm_deps_pass_when_exact(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    assert LlmCriticalDepsPinnedRule().check(_ctx(repo)) == []


def test_llm_deps_import_without_declaration(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    # train.py imports torch; requirements.txt pins torch==2.8.0 → PASS
    assert LlmCriticalDepsPinnedRule().check(_ctx(repo)) == []


def test_llm_deps_skipped_when_no_critical(tmp_path: Path) -> None:
    repo = materialize_repo("no_deps_file", tmp_path)
    ctx = _ctx(repo)
    assert LlmCriticalDepsPinnedRule().applies(ctx) is False
    assert "no LLM-critical" in (LlmCriticalDepsPinnedRule().skip_reason(ctx) or "")


# --- env.python_version_declared --------------------------------------------


def test_python_version_warning_without_declaration(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    finding = PythonVersionDeclaredRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.WARNING


def test_python_version_pass_via_requires_python(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    assert PythonVersionDeclaredRule().check(_ctx(repo)) == []


def test_python_version_pass_via_conda_python(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    assert PythonVersionDeclaredRule().check(_ctx(repo)) == []


# --- env.secret_files_ignored ------------------------------------------------


def test_secret_files_critical_on_tracked_env(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    finding = SecretFilesIgnoredRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.CRITICAL
    assert finding.evidence[0].path == ".env"


def test_secret_files_pass_with_example_exempt(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    assert SecretFilesIgnoredRule().check(_ctx(repo)) == []


def test_secret_files_ignored_stays_silent_when_gitignored(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / ".env").write_text("OPENAI_API_KEY=x\n")
    (repo / ".gitignore").write_text("outputs/\n__pycache__/\n.env\n")
    from tests.conftest import commit_all

    commit_all(repo)  # commit .gitignore; .env is ignored → not listed
    assert SecretFilesIgnoredRule().check(_ctx(repo)) == []


def test_secret_files_downgraded_outside_git(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    (repo / "creds.pem").write_text("-----BEGIN PRIVATE KEY-----")
    finding = SecretFilesIgnoredRule().check(_ctx(repo))[0]
    assert finding.severity == Severity.WARNING  # CRITICAL downgraded, not a git repo
    assert "not a git repo" in finding.message


# --- env.reprollm_initialized ------------------------------------------------


def test_reprollm_initialized_info_at_level0(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    ctx = _ctx(repo)
    finding = ReprollmInitializedRule().check(ctx)[0]
    assert finding.severity == Severity.INFO
    assert "reprollm init" in finding.message


def test_reprollm_initialized_passes_when_initialized(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "reprollm.yaml").write_text("project:\n  name: p\n")
    assert ReprollmInitializedRule().check(_ctx(repo)) == []


def test_reprollm_initialized_skipped_above_level0(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    ctx = _ctx(repo, level=1)
    assert ReprollmInitializedRule().applies(ctx) is False
