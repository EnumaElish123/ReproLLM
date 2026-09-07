"""RepoScanner tests (M2-T01 acceptance)."""

from pathlib import Path

from reprollm.core.git import inspect_git
from reprollm.core.scanner import MAX_FILE_BYTES, RepoScanner

from tests.conftest import materialize_repo, run_git


def _scanner(root: Path) -> RepoScanner:
    return RepoScanner(root, inspect_git(root))


def test_files_matches_git_ls_files(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    expected = sorted(
        p.decode()
        for p in run_git(
            repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
        ).stdout.split(b"\x00")
        if p
    )
    assert _scanner(repo).files() == expected


def test_gitignored_files_not_listed(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "outputs").mkdir()
    (repo / "outputs" / "result.json").write_text("{}")
    assert "outputs/result.json" not in _scanner(repo).files()


def test_reprollm_runs_never_listed(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    runs = repo / ".reprollm" / "runs" / "20260101T000000Z-abcdef"
    runs.mkdir(parents=True)
    (runs / "run.json").write_text("{}")
    assert all(not p.startswith(".reprollm/runs/") for p in _scanner(repo).files())


def test_large_files_filtered(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "big.bin").write_bytes(b"\x00" * (MAX_FILE_BYTES + 1))
    assert "big.bin" not in _scanner(repo).files()


def test_non_git_walk_ignores_builtin_dirs(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "x.js").write_text("")
    (repo / "__pycache__").mkdir()
    (repo / "__pycache__" / "x.pyc").write_text("")
    (repo / ".venv").mkdir()
    (repo / ".venv" / "pyvenv.cfg").write_text("")
    (repo / "src").mkdir()
    (repo / "src" / "train.py").write_text("x = 1\n")
    files = _scanner(repo).files()
    assert files == ["requirements.txt", "src/train.py", "train.py"]


def test_venv_by_marker_skipped(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    (repo / "customenv").mkdir()
    (repo / "customenv" / "pyvenv.cfg").write_text("")
    (repo / "customenv" / "lib.py").write_text("x = 1\n")
    assert "customenv/lib.py" not in _scanner(repo).files()


def test_read_text_binary_returns_none(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    (repo / "blob.bin").write_bytes(b"\xff\xd8\xff\xe0\x00binary")
    scanner = _scanner(repo)
    assert scanner.read_text("blob.bin") is None
    text = scanner.read_text("train.py")
    assert text is not None
    assert text.startswith('"""Minimal training script')
    assert "import torch" in text


def test_read_text_cached(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    scanner = _scanner(repo)
    first = scanner.read_text("train.py")
    (repo / "train.py").write_text("# changed\n")
    assert scanner.read_text("train.py") == first  # cached, not re-read


def test_glob_and_exists(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    scanner = _scanner(repo)
    assert scanner.glob("configs/*.yaml") == ["configs/eval.yaml"]
    assert scanner.glob("*.py") == ["eval.py"]
    assert scanner.exists("requirements.txt") is True
    assert scanner.exists("missing.txt") is False


def test_python_readme_config_helpers(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    scanner = _scanner(repo)
    assert scanner.python_files() == ["eval.py"]
    assert scanner.readme_files() == ["README.md"]
    assert scanner.config_files() == ["configs/eval.yaml"]

    (repo / "sub").mkdir()
    (repo / "sub" / "README.md").write_text("nested readme")
    (repo / "sub" / "deep").mkdir()
    (repo / "sub" / "deep" / "README.md").write_text("too deep")
    # listings are cached by design; a fresh scanner sees the new tree
    assert _scanner(repo).readme_files() == ["README.md", "sub/README.md"]


def test_config_files_exclude_lockfiles(tmp_path: Path) -> None:
    repo = materialize_repo("openai_judge_eval", tmp_path)
    (repo / "uv.lock").write_text("")
    (repo / ".reprollm").mkdir()
    (repo / ".reprollm" / "settings.yaml").write_text("a: 1")
    scanner = _scanner(repo)
    assert "uv.lock" not in scanner.config_files()
    assert all(not p.startswith(".reprollm/") for p in scanner.config_files())
    assert "pyproject.toml" in scanner.config_files()


def test_dir_names(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    assert _scanner(repo).dir_names() == {"configs", "prompts"}


def test_python_files_cap_records_warning(tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    scanner = _scanner(repo)
    scanner._files = [f"f{i}.py" for i in range(501)] + ["keep.py"]  # type: ignore[assignment]
    scanner._files.sort()
    assert len(scanner.python_files()) == 500
    assert scanner.warnings
