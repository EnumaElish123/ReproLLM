"""inspect_git / check_ignore / ls_files tests."""

from pathlib import Path

from reprollm.core.git import check_ignore, inspect_git, ls_files, strip_credentials
from tests.conftest import make_git_repo, run_git


def _commit_all(repo: Path, message: str = "fixture") -> None:
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--allow-empty", "-m", message)


def test_inspect_git_outside_repo(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    info = inspect_git(plain)
    assert info.is_repo is False
    assert info.commit is None


def test_inspect_git_unborn_branch(tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "unborn")
    info = inspect_git(repo)
    assert info.is_repo is True
    assert info.commit is None
    assert info.branch == "main"


def test_inspect_git_clean_repo(git_repo: Path) -> None:
    (git_repo / "a.txt").write_text("a")
    _commit_all(git_repo)
    info = inspect_git(git_repo)
    assert info.is_repo is True
    assert info.commit is not None and len(info.commit) == 40
    assert info.branch == "main"
    assert info.modified == []
    assert info.untracked == []
    assert info.dirty is False


def test_inspect_git_modified_and_untracked(git_repo: Path) -> None:
    (git_repo / "tracked.txt").write_text("one")
    _commit_all(git_repo)
    (git_repo / "tracked.txt").write_text("two")
    (git_repo / "fresh.txt").write_text("new")
    info = inspect_git(git_repo)
    assert info.modified == ["tracked.txt"]
    assert info.untracked == ["fresh.txt"]
    assert info.dirty is True


def test_inspect_git_detached_head(git_repo: Path) -> None:
    (git_repo / "a.txt").write_text("a")
    _commit_all(git_repo, "first")
    (git_repo / "b.txt").write_text("b")
    _commit_all(git_repo, "second")
    run_git(git_repo, "checkout", "HEAD~1")
    info = inspect_git(git_repo)
    assert info.branch == "HEAD"


def test_remote_credentials_stripped(git_repo: Path) -> None:
    run_git(
        git_repo,
        "remote",
        "add",
        "origin",
        "https://user:secret@github.com/org/repo.git",
    )
    info = inspect_git(git_repo)
    assert info.remote_origin == "https://github.com/org/repo.git"


def test_strip_credentials_variants() -> None:
    assert strip_credentials("https://alice:hunter2@host/x.git") == "https://host/x.git"
    assert strip_credentials("https://host/x.git") == "https://host/x.git"
    assert strip_credentials("git@github.com:org/repo.git") == "git@github.com:org/repo.git"


def test_check_ignore(git_repo: Path) -> None:
    (git_repo / ".gitignore").write_text("*.log\n")
    (git_repo / "x.log").write_text("x")
    (git_repo / "y.txt").write_text("y")
    assert check_ignore(git_repo, ["x.log", "y.txt"]) == {"x.log"}
    assert check_ignore(git_repo, []) == set()


def test_ls_files_tracked_and_untracked(git_repo: Path) -> None:
    (git_repo / "a.txt").write_text("a")
    (git_repo / "b.txt").write_text("b")
    _commit_all(git_repo)
    (git_repo / "ignored.log").write_text("log")
    (git_repo / ".gitignore").write_text("*.log\n")
    _commit_all(git_repo, "gitignore")
    (git_repo / "c.txt").write_text("c")  # untracked, not ignored
    assert ls_files(git_repo) == [".gitignore", "a.txt", "b.txt", "c.txt"]
    assert ls_files(git_repo, include_untracked=False) == [".gitignore", "a.txt", "b.txt"]
