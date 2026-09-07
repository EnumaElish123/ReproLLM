"""code.* rule tests (spec §12.1)."""

from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.core.registry import all_rules
from reprollm.rules.code import (
    CleanTreeRule,
    GitCommitRule,
    GitRepoRule,
    NoUntrackedRule,
    RemoteRecordedRule,
    SubmodulesInitializedRule,
)
from reprollm.schemas.finding import FindingStatus, Severity

from tests.conftest import CmdStub, commit_all, make_git_repo, materialize_repo, run_git


def test_all_code_rules_registered() -> None:
    ids = {rule.id for rule in all_rules()}
    assert ids >= {
        "code.git_repo",
        "code.git_commit",
        "code.clean_tree",
        "code.no_untracked",
        "code.submodules_initialized",
        "code.remote_recorded",
    }


def test_git_repo_passes_in_repository(git_repo: Path) -> None:
    assert GitRepoRule().check(AuditContext(git_repo, level=0)) == []


def test_git_repo_fails_outside_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    findings = GitRepoRule().check(AuditContext(plain, level=0))
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].status == FindingStatus.FAIL
    assert "not inside a git work tree" in findings[0].message
    assert findings[0].fix_hint


def test_git_commit_passes_with_head(git_repo: Path) -> None:
    commit_all(git_repo)
    assert GitCommitRule().check(AuditContext(git_repo, level=0)) == []


def test_git_commit_fails_on_unborn_branch(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "unborn")
    findings = GitCommitRule().check(AuditContext(repo, level=0))
    assert len(findings) == 1
    assert "no commits" in findings[0].message
    assert "main" in findings[0].message


def test_git_commit_skips_outside_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    ctx = AuditContext(plain, level=0)
    assert GitCommitRule().applies(ctx) is False
    assert GitCommitRule().skip_reason(ctx) == "not a git repository"


# --- M2-T02 -----------------------------------------------------------------


def _stub_healthy_git(stub: CmdStub, repo: Path) -> None:
    """Standard responses for inspect_git on a clean repo (no origin)."""
    stub.on("git", "rev-parse", returncode=0, stdout=f"{repo}\n")
    stub.on("git", "branch", "--show-current", stdout="main\n")
    stub.on("git", "status", "--porcelain", stdout="")
    stub.on("git", "remote", "get-url", "origin", returncode=1)


def test_clean_tree_and_no_untracked_on_dirty_tree(tmp_path: Path) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    ctx = AuditContext(repo, level=0)
    clean = CleanTreeRule().check(ctx)
    assert len(clean) == 1
    assert clean[0].severity == Severity.WARNING
    assert clean[0].evidence[0].path == "configs/run.yaml"
    untracked = NoUntrackedRule().check(ctx)
    assert len(untracked) == 1
    assert untracked[0].evidence[0].path == "scratch.txt"


def test_clean_tree_passes_on_clean_repo(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    ctx = AuditContext(repo, level=0)
    assert CleanTreeRule().check(ctx) == []
    assert NoUntrackedRule().check(ctx) == []


def test_evidence_caps_at_ten_paths(git_repo: Path) -> None:
    (git_repo / "seed.txt").write_text("x")
    commit_all(git_repo)
    for i in range(12):
        (git_repo / f"file{i}.txt").write_text("y")
        commit_all(git_repo)
    for i in range(12):
        (git_repo / f"file{i}.txt").write_text("z")
    finding = CleanTreeRule().check(AuditContext(git_repo, level=0))[0]
    path_evidence = [e for e in finding.evidence if e.path]
    assert len(path_evidence) == 10
    assert any("2 more" in (e.note or "") for e in finding.evidence)


def test_submodules_skipped_without_gitmodules(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    ctx = AuditContext(repo, level=0)
    assert SubmodulesInitializedRule().applies(ctx) is False
    assert SubmodulesInitializedRule().skip_reason(ctx) == "no .gitmodules"


def test_submodules_fail_when_uninitialized(git_repo: Path, stub_run_cmd: CmdStub) -> None:
    (git_repo / ".gitmodules").write_text('[submodule "vendor"]\n\tpath = vendor\n')
    commit_all(git_repo)
    _stub_healthy_git(stub_run_cmd, git_repo)
    stub_run_cmd.on(
        "git", "submodule", "status", stdout="-a1b2c3d vendor/lib (v1)\n e4f5a6b other (v2)\n"
    )
    ctx = AuditContext(git_repo, level=0)
    assert SubmodulesInitializedRule().applies(ctx) is True
    finding = SubmodulesInitializedRule().check(ctx)[0]
    assert finding.evidence[0].path == "vendor/lib"


def test_submodules_pass_when_initialized(git_repo: Path, stub_run_cmd: CmdStub) -> None:
    (git_repo / ".gitmodules").write_text('[submodule "vendor"]\n\tpath = vendor\n')
    commit_all(git_repo)
    _stub_healthy_git(stub_run_cmd, git_repo)
    stub_run_cmd.on("git", "submodule", "status", stdout=" a1b2c3d vendor (v1)\n")
    assert SubmodulesInitializedRule().check(AuditContext(git_repo, level=0)) == []


def test_remote_recorded_info_when_missing_origin(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    finding = RemoteRecordedRule().check(AuditContext(repo, level=0))[0]
    assert finding.severity == Severity.INFO
    assert finding.status == FindingStatus.FAIL
    assert "origin" in finding.message


def test_remote_recorded_passes_with_origin(git_repo: Path) -> None:
    run_git(git_repo, "remote", "add", "origin", "https://github.com/o/r.git")
    assert RemoteRecordedRule().check(AuditContext(git_repo, level=0)) == []
