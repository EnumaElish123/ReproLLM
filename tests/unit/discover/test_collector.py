"""M7-T03: discover collector — selection, redaction gating, budget, dry run."""

from __future__ import annotations

from pathlib import Path

from reprollm.core.git import inspect_git
from reprollm.core.scanner import RepoScanner
from reprollm.discover.collector import Payload, collect, dry_run_report
from reprollm.schemas.config import DiscoverConfig
from tests.conftest import materialize_repo


def _collect(repo: Path, max_chars: int = 60_000):
    scanner = RepoScanner(repo, inspect_git(repo))
    return collect(repo, scanner, DiscoverConfig(max_chars=max_chars))


def _paths(payload: Payload) -> set[str]:
    return {f.path for f in payload.files}


def test_fixture_dry_run_snapshots(tmp_path: Path) -> None:
    import os

    for name in ("hf_vllm_eval", "openai_judge_eval", "privacy_custom_params"):
        repo = materialize_repo(name, tmp_path / name)
        payload = _collect(repo)
        report = dry_run_report(payload)
        expected = (
            Path(__file__).resolve().parents[2]
            / "fixtures"
            / "repos"
            / name
            / "expected"
            / "discover_dry_run.txt"
        )
        if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
            expected.write_text(report, encoding="utf-8")
        else:
            assert report == expected.read_text(encoding="utf-8"), name


def test_forbidden_files_never_collected(tmp_path: Path) -> None:
    repo = materialize_repo("privacy_custom_params", tmp_path)
    payload = _collect(repo)
    assert ".env" not in _paths(payload)
    assert ".env" not in payload.tree
    assert all(not p.startswith(tuple(("data", "outputs", "wandb"))) for p in payload.tree)


def test_file_with_secret_is_dropped_whole(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "leaky.yaml").write_text("note: ok\napi_key: abcdefgh12345678\n", encoding="utf-8")
    payload = _collect(repo)
    assert "leaky.yaml" in payload.dropped_files
    assert "leaky.yaml" not in _paths(payload)
    rendered = payload.render()
    assert "abcdefgh12345678" not in rendered


def test_budget_truncation(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    full = _collect(repo)
    squeezed = _collect(repo, max_chars=50)
    assert squeezed.total_chars <= 50 or len(squeezed.files) < len(full.files)
    assert squeezed.truncated_files or len(squeezed.tree) < len(full.tree)


def test_tree_capped_and_sorted(tmp_path: Path) -> None:
    repo = tmp_path / "big"
    repo.mkdir()
    for i in range(30):
        (repo / f"f{i:03d}.txt").write_text("x\n", encoding="utf-8")
    payload = _collect(repo)
    assert payload.tree == sorted(p for p in payload.tree)
    assert len(payload.tree) <= 30


def test_lockfiles_and_nested_excluded(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "uv.lock").write_text("[]\n", encoding="utf-8")
    (repo / "deep" / "nested").mkdir(parents=True)
    (repo / "deep" / "nested" / "conf.yaml").write_text("a: 1\n", encoding="utf-8")
    payload = _collect(repo)
    assert "uv.lock" not in _paths(payload)
    assert "deep/nested/conf.yaml" not in _paths(payload)  # top-level configs only


def test_deterministic(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    first = _collect(repo)
    second = _collect(repo)
    assert [f.path for f in first.files] == [f.path for f in second.files]
    assert first.render() == second.render()
    assert first.tree == second.tree
