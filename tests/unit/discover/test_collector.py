"""M7-T03: discover collector — selection, redaction gating, budget, dry run."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_exclude_removes_text_snippets_and_tree_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Public experiment\n", encoding="utf-8")
    (tmp_path / "private.json").write_text('{"note": "DO_NOT_SEND"}', encoding="utf-8")
    (tmp_path / "private.py").write_text(
        'parser.add_argument("--private-alpha", default=0.2)\n', encoding="utf-8"
    )
    scanner = RepoScanner(tmp_path, inspect_git(tmp_path))
    payload = collect(tmp_path, scanner, DiscoverConfig(exclude=["private.*"]))
    assert _paths(payload) == {"README.md"}
    assert payload.tree == ["README.md"]
    assert "DO_NOT_SEND" not in payload.render()
    assert "private" not in payload.render()
    assert "Excluded by discover.exclude" in dry_run_report(payload)


def test_include_adds_nested_text_without_replacing_defaults(tmp_path: Path) -> None:
    nested = tmp_path / "configs" / "experiment"
    nested.mkdir(parents=True)
    (tmp_path / "README.md").write_text("Experiment\n", encoding="utf-8")
    (nested / "eval.yaml").write_text("temperature: 0.25\n", encoding="utf-8")
    scanner = RepoScanner(tmp_path, inspect_git(tmp_path))
    payload = collect(tmp_path, scanner, DiscoverConfig(include=["configs/**/*.yaml"]))
    assert _paths(payload) == {"README.md", "configs/experiment/eval.yaml"}
    assert "temperature: 0.25" in payload.render()


def test_extra_includes_cannot_override_safety_or_exclude(tmp_path: Path) -> None:
    for path, contents in {
        "README.md": "Public\n",
        "data/private.txt": "RESTRICTED_DATA\n",
        ".env": "FAKE_CREDENTIAL\n",
        "uv.lock": "LOCKFILE_CONTENT\n",
        "notes/private.txt": "EXCLUDED_TEXT\n",
        "notes/leaky.txt": "api_key: abcdefgh12345678\n",
        "notes/oversize.txt": "x" * (64 * 1024 + 1),
        "notes/binary.txt": "binary\x00content",
    }.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")
    scanner = RepoScanner(tmp_path, inspect_git(tmp_path))
    payload = collect(
        tmp_path, scanner, DiscoverConfig(include=["*"], exclude=["notes/private.txt"])
    )
    assert _paths(payload) == {"README.md"}
    assert "notes/leaky.txt" in payload.dropped_files
    assert "notes/oversize.txt" in payload.truncated_files
    assert "notes/private.txt" not in payload.tree
    for forbidden in (
        "RESTRICTED_DATA",
        "FAKE_CREDENTIAL",
        "LOCKFILE_CONTENT",
        "EXCLUDED_TEXT",
        "abcdefgh12345678",
    ):
        assert forbidden not in payload.render()


def test_explicit_source_included_once_and_excluded_before_read(tmp_path: Path) -> None:
    (tmp_path / "args.py").write_text('p.add_argument("--alpha", default=0.25)\n', encoding="utf-8")
    scanner = RepoScanner(tmp_path, inspect_git(tmp_path))
    payload = collect(tmp_path, scanner, DiscoverConfig(include=["args.py"]))
    assert _paths(payload) == {"args.py"}
    assert payload.render().count('p.add_argument("--alpha"') == 1
    payload = collect(tmp_path, scanner, DiscoverConfig(include=["args.py"], exclude=["*.py"]))
    assert not payload.files
    assert not payload.tree


def test_oversize_source_cannot_send_snippets(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text(
        'p.add_argument("--do-not-send", default=0.25)\n#' + "x" * (64 * 1024),
        encoding="utf-8",
    )
    payload = _collect(tmp_path)
    assert not payload.files
    assert payload.truncated_files == ["large.py"]
    assert "--do-not-send" not in payload.render()


def test_secret_anywhere_in_source_drops_all_its_snippets(tmp_path: Path) -> None:
    (tmp_path / "args.py").write_text(
        'p.add_argument("--public-alpha", default=0.25)\napi_key = "abcdefgh12345678"\n',
        encoding="utf-8",
    )
    payload = _collect(tmp_path)
    assert not payload.files
    assert payload.dropped_files == ["args.py"]
    assert "--public-alpha" not in payload.render()


def test_secret_in_path_never_enters_tree_header_or_report(tmp_path: Path) -> None:
    fake_secret = "sk-" + "a" * 40
    path = tmp_path / "notes" / f"{fake_secret}.txt"
    path.parent.mkdir()
    path.write_text("Public marker\n", encoding="utf-8")
    for config in (DiscoverConfig(), DiscoverConfig(include=["notes/*"])):
        payload = collect(tmp_path, RepoScanner(tmp_path, inspect_git(tmp_path)), config)
        assert not payload.files
        assert not payload.tree
        assert payload.dropped_files
        assert fake_secret not in payload.render() + dry_run_report(payload)


def test_includes_cannot_follow_aliases_to_excluded_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in ("data/private.txt", ".env", "private.txt", "uv.lock", "public.txt"):
        target = repo / name
        target.parent.mkdir(exist_ok=True)
        target.write_text(f"MARKER_{name}\n", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("OUTSIDE_MARKER\n", encoding="utf-8")
    targets = ["data/private.txt", ".env", "private.txt", "uv.lock", "../outside.txt"]
    try:
        for index, target in enumerate(targets):
            (repo / f"alias{index}.txt").symlink_to(target)
        (repo / "safe-alias.txt").symlink_to("public.txt")
    except OSError:
        pytest.skip("symlink creation is unavailable")
    payload = collect(
        repo,
        RepoScanner(repo, inspect_git(repo)),
        DiscoverConfig(include=["*.txt"], exclude=["private.txt"]),
    )
    assert _paths(payload) == {"public.txt", "safe-alias.txt"}
    assert all(f"alias{index}.txt" not in payload.tree for index in (0, 1, 2, 4))
    assert "MARKER_private" not in payload.render()
    assert "MARKER_uv.lock" not in payload.render()
    assert "OUTSIDE_MARKER" not in payload.render()
