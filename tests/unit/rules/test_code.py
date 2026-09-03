"""code.git_repo / code.git_commit rule tests (spec §12.1)."""

from pathlib import Path

from reprollm.core.context import AuditContext
from reprollm.core.registry import all_rules, get_rule
from reprollm.rules.code import GitCommitRule, GitRepoRule
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import make_git_repo


def test_rules_are_registered() -> None:
    ids = {rule.id for rule in all_rules()}
    assert "code.git_repo" in ids
    assert "code.git_commit" in ids
    assert get_rule("code.git_repo") is GitRepoRule
    assert get_rule("code.git_commit") is GitCommitRule


def test_git_repo_passes_in_repository(git_repo: Path) -> None:
    ctx = AuditContext(git_repo, level=0)
    assert GitRepoRule().check(ctx) == []


def test_git_repo_fails_outside_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    AuditContext(plain, level=0)
    findings = GitRepoRule().check(AuditContext(plain, level=0))
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].status == FindingStatus.FAIL
    assert "not inside a git work tree" in findings[0].message
    assert findings[0].fix_hint


def test_git_commit_passes_with_head(git_repo: Path) -> None:
    from tests.conftest import commit_all

    commit_all(git_repo)
    ctx = AuditContext(git_repo, level=0)
    assert GitCommitRule().applies(ctx) is True
    assert GitCommitRule().check(ctx) == []


def test_git_commit_fails_on_unborn_branch(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "unborn")
    ctx = AuditContext(repo, level=0)
    findings = GitCommitRule().check(ctx)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert "no commits" in findings[0].message
    assert "main" in findings[0].message


def test_git_commit_skips_outside_repository(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    ctx = AuditContext(plain, level=0)
    assert GitCommitRule().applies(ctx) is False
    assert GitCommitRule().skip_reason(ctx) == "not a git repository"
