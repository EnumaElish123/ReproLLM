"""find_root / RepoPaths tests (spec §1, §2)."""

from pathlib import Path

from reprollm.core import paths
from reprollm.core.paths import find_root, repo_paths
from tests.conftest import run_git


def test_find_root_prefers_manifest_ancestor(tmp_path: Path) -> None:
    (tmp_path / "reprollm.yaml").write_text("project:\n  name: p\n")
    deep = tmp_path / "src" / "pkg"
    deep.mkdir(parents=True)
    assert find_root(deep) == tmp_path.resolve()


def test_find_root_falls_back_to_git_toplevel(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "commit", "--allow-empty", "-m", "init")
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    assert find_root(nested) == repo.resolve()


def test_find_root_falls_back_to_start(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert find_root(plain) == plain.resolve()


def test_repo_paths_layout(tmp_path: Path) -> None:
    layout = repo_paths(tmp_path)
    assert layout.manifest == tmp_path / "reprollm.yaml"
    assert layout.lock == tmp_path / "reprollm.lock"
    assert layout.config == tmp_path / ".reprollm/config.yaml"
    assert layout.project_rules == tmp_path / ".reprollm/project-rules.yaml"
    assert layout.runs == tmp_path / ".reprollm/runs"
    assert layout.dotdir == tmp_path / ".reprollm"


def test_path_constants_match_spec() -> None:
    assert paths.MANIFEST == "reprollm.yaml"
    assert paths.LOCK == "reprollm.lock"
    assert paths.DOTDIR == ".reprollm"
    assert paths.CONFIG == ".reprollm/config.yaml"
    assert paths.PROJECT_RULES == ".reprollm/project-rules.yaml"
    assert paths.USER_PROFILES_DIR == ".reprollm/profiles"
    assert paths.RUNS_DIR == ".reprollm/runs"
    assert paths.DISCOVER_DIR == ".reprollm/discover"
