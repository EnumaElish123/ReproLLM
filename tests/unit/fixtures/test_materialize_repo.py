"""Golden fixture infrastructure tests (spec §22 T-02, T-03).

If a fixture tree changes, its commit SHA changes: update
``HF_VLLM_EVAL_COMMIT_SHA`` and the fixture README together, on purpose.
"""

from pathlib import Path

import httpx
import pytest

from reprollm.core import proc
from reprollm.core.git import inspect_git
from tests.conftest import CmdStub, commit_all, materialize_repo, run_git

#: Deterministic HEAD of tests/fixtures/repos/hf_vllm_eval (T-03).
HF_VLLM_EVAL_COMMIT_SHA = "a93c8fd33a13a51257c71797866669f91564e49d"

ALL_GIT_FIXTURES = [
    "hf_vllm_eval",
    "openai_judge_eval",
    "privacy_custom_params",
    "dirty_tree",
    "no_deps_file",
]


def head_sha(repo: Path) -> str:
    return run_git(repo, "rev-parse", "HEAD").stdout.decode().strip()


def test_hf_vllm_eval_commit_is_deterministic(tmp_path: Path) -> None:
    first = materialize_repo("hf_vllm_eval", tmp_path / "a")
    second = materialize_repo("hf_vllm_eval", tmp_path / "b")
    assert head_sha(first) == head_sha(second)
    assert head_sha(first) == HF_VLLM_EVAL_COMMIT_SHA


def test_all_git_fixtures_materialize_on_main(tmp_path: Path) -> None:
    for name in ALL_GIT_FIXTURES:
        repo = materialize_repo(name, tmp_path)
        info = inspect_git(repo)
        assert info.is_repo, name
        assert info.branch == "main", name
        assert info.commit == head_sha(repo), name


def test_dirty_tree_post_commit_makes_tree_dirty(tmp_path: Path) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    info = inspect_git(repo)
    assert info.modified == ["configs/run.yaml"]
    assert info.untracked == ["scratch.txt"]
    assert (repo / "configs/run.yaml").read_text(encoding="utf-8").endswith("extra: 1\n")


def test_not_a_git_repo_has_no_git_dir(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    assert not (repo / ".git").exists()
    assert inspect_git(repo).is_repo is False


def test_fixed_dates_make_identical_commits(tmp_path: Path) -> None:
    shas = []
    for subdir in ("one", "two"):
        repo = materialize_repo("hf_vllm_eval", tmp_path / subdir)
        (repo / "extra.txt").write_text("x", encoding="utf-8")
        shas.append(commit_all(repo, "extra"))
    # same tree + parent + message + fixed identity/dates ⇒ identical SHA
    assert shas[0] == shas[1]


def test_stub_run_cmd_returns_canned_results(stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.on("git", "status", returncode=0, stdout="clean\n")
    stub_run_cmd.on("git", "rev-parse", "HEAD", returncode=0, stdout="abc123\n")
    stub_run_cmd.on("git", "rev-parse", returncode=1, stderr="ambiguous")

    assert proc.run_cmd(["git", "status"]).stdout == "clean\n"
    # longest matching prefix wins
    assert proc.run_cmd(["git", "rev-parse", "HEAD"]).stdout == "abc123\n"
    assert proc.run_cmd(["git", "rev-parse", "anything"]).returncode == 1
    assert stub_run_cmd.calls[0] == ("git", "status")
    with pytest.raises(AssertionError):
        proc.run_cmd(["nvidia-smi"])


def test_unmocked_http_fails() -> None:
    from respx.models import AllMockedAssertionError

    with pytest.raises(AllMockedAssertionError):
        httpx.get("https://reprollm-invalid.example.com/api")
