"""Dependency-declaration parsing tests (M2-T03): each format ≥3 cases."""

from pathlib import Path

from reprollm.core.deps import canonical_dep_name, scan_dependencies
from reprollm.core.git import inspect_git
from reprollm.core.scanner import RepoScanner


def _scan(repo: Path):
    return scan_dependencies(RepoScanner(repo, inspect_git(repo)))


def _write(repo: Path, rel: str, content: str) -> None:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)


def _by_name(decls, name):
    return [d for d in decls if d.name == name]


# --- name normalization ------------------------------------------------------


def test_pytorch_normalizes_to_torch() -> None:
    assert canonical_dep_name("pytorch") == "torch"
    assert canonical_dep_name("PyTorch") == "torch"
    assert canonical_dep_name("Flash_Attn") == "flash-attn"


# --- requirements*.txt -------------------------------------------------------


def test_requirements_exact_and_loose(tmp_path: Path) -> None:
    repo = tmp_path / "req"
    repo.mkdir()
    _write(repo, "requirements.txt", "torch==2.8.0\nvllm>=0.10\ntransformers\n")
    decls = _scan(repo).declarations
    assert _by_name(decls, "torch")[0].is_exact
    assert not _by_name(decls, "vllm")[0].is_exact
    assert not _by_name(decls, "transformers")[0].is_exact
    assert _by_name(decls, "vllm")[0].specifier == ">=0.10"


def test_requirements_recursion_and_unparsed(tmp_path: Path) -> None:
    repo = tmp_path / "req2"
    repo.mkdir()
    _write(repo, "requirements.txt", "-r base.txt\n-e .\n--index-url https://pypi.example\n")
    _write(repo, "base.txt", "datasets==3.2.0\n")
    result = _scan(repo)
    assert _by_name(result.declarations, "datasets")[0].is_exact
    assert _by_name(result.declarations, "datasets")[0].source_file == "base.txt"
    assert len(result.unparsed) == 2
    assert not result.lockfiles  # -e/--index-url lines break the all-== property


def test_requirements_all_pinned_is_lockfile(tmp_path: Path) -> None:
    repo = tmp_path / "req3"
    repo.mkdir()
    _write(repo, "requirements.txt", "# comment\ntorch==2.8.0\ntransformers==4.57.0\n")
    result = _scan(repo)
    assert [lock.path for lock in result.lockfiles] == ["requirements.txt"]
    assert "torch" in result.lockfiles[0].packages


def test_requirements_syntax_error_recoreded_not_raised(tmp_path: Path) -> None:
    repo = tmp_path / "req4"
    repo.mkdir()
    _write(repo, "requirements.txt", "this is not === a requirement!!!\n")
    result = _scan(repo)
    assert result.unparsed and result.manifest_present


# --- pyproject.toml ----------------------------------------------------------


def test_pyproject_pep621_and_optional(tmp_path: Path) -> None:
    repo = tmp_path / "pp"
    repo.mkdir()
    _write(
        repo,
        "pyproject.toml",
        (
            "[project]\nname = 'x'\nversion = '0.1'\n"
            'dependencies = ["openai>=1.0", "pandas==2.2.0"]\n\n'
            '[project.optional-dependencies]\ngpu = ["torch==2.8.0"]\n'
        ),
    )
    decls = _scan(repo).declarations
    assert not _by_name(decls, "openai")[0].is_exact
    assert _by_name(decls, "pandas")[0].is_exact
    assert _by_name(decls, "torch")[0].is_exact


def test_pyproject_poetry_exact_and_caret(tmp_path: Path) -> None:
    repo = tmp_path / "poetry"
    repo.mkdir()
    _write(
        repo,
        "pyproject.toml",
        (
            "[tool.poetry.dependencies]\n"
            'python = "^3.10"\n'
            'torch = "2.8.0"\n'
            'transformers = {version = "^4.57"}\n'
            'datasets = {version = "3.2.0"}\n'
        ),
    )
    decls = _scan(repo).declarations
    assert _by_name(decls, "torch")[0].is_exact
    assert not _by_name(decls, "transformers")[0].is_exact
    assert _by_name(decls, "datasets")[0].is_exact
    assert not _by_name(decls, "python")[0].is_exact


def test_pyproject_malformed_never_crashes(tmp_path: Path) -> None:
    repo = tmp_path / "pp-bad"
    repo.mkdir()
    _write(repo, "pyproject.toml", "[project ] oops not toml")
    result = _scan(repo)
    assert result.unparsed and result.manifest_present


# --- environment.yml ---------------------------------------------------------


def test_environment_yml_conda_and_pip(tmp_path: Path) -> None:
    repo = tmp_path / "conda"
    repo.mkdir()
    _write(
        repo,
        "environment.yml",
        (
            "name: privinf\ndependencies:\n"
            "  - python=3.11\n"
            "  - pytorch=2.8.0\n"
            "  - pip\n"
            "  - pip:\n"
            "      - transformers==4.57.0\n"
            "      - pyyaml\n"
        ),
    )
    decls = _scan(repo).declarations
    assert _by_name(decls, "python")[0].is_exact  # python=3.11
    torch = _by_name(decls, "torch")[0]  # pytorch → torch
    assert torch.is_exact and torch.exact_version == "2.8.0"
    assert _by_name(decls, "transformers")[0].is_exact
    assert not _by_name(decls, "pyyaml")[0].is_exact


def test_environment_yml_operators_not_exact(tmp_path: Path) -> None:
    repo = tmp_path / "conda2"
    repo.mkdir()
    _write(repo, "environment.yml", "dependencies:\n  - numpy>=1.24\n  - scipy\n")
    decls = _scan(repo).declarations
    assert not _by_name(decls, "numpy")[0].is_exact
    assert _by_name(decls, "numpy")[0].specifier == ">=1.24"
    assert not _by_name(decls, "scipy")[0].is_exact


def test_environment_yml_build_strings_exact(tmp_path: Path) -> None:
    repo = tmp_path / "conda3"
    repo.mkdir()
    _write(repo, "environment.yml", "dependencies:\n  - pytorch=2.8.0=cuda12.1\n")
    decls = _scan(repo).declarations
    assert _by_name(decls, "torch")[0].is_exact


# --- Pipfile -----------------------------------------------------------------


def test_pipfile_exact_only_for_double_equals(tmp_path: Path) -> None:
    repo = tmp_path / "pipfile"
    repo.mkdir()
    _write(
        repo,
        "Pipfile",
        '[packages]\nrequests = "*"\ntorch = ">=2.0"\nnumpy = {version = "==1.26.0"}\n',
    )
    decls = _scan(repo).declarations
    assert not _by_name(decls, "requests")[0].is_exact
    assert not _by_name(decls, "torch")[0].is_exact
    assert _by_name(decls, "numpy")[0].is_exact


# --- lockfiles ---------------------------------------------------------------


def test_lockfile_packages_parsed(tmp_path: Path) -> None:
    repo = tmp_path / "locks"
    repo.mkdir()
    _write(repo, "pyproject.toml", "[project]\nname='x'\n")
    _write(repo, "uv.lock", '[[package]]\nname = "vllm"\nversion = "0.10.0"\n')
    _write(
        repo,
        "Pipfile.lock",
        '{"default": {"torch": {"version": "==2.8.0"}}, "develop": {}}',
    )
    _write(repo, "conda-lock.yml", "package:\n  - name: transformers\n    version: 4.57.0\n")
    locks = {lock.path: lock for lock in _scan(repo).lockfiles}
    assert "vllm" in locks["uv.lock"].packages
    assert "torch" in locks["Pipfile.lock"].packages
    assert "transformers" in locks["conda-lock.yml"].packages


def test_lockfile_counts_as_pinned(tmp_path: Path) -> None:
    repo = tmp_path / "lockpin"
    repo.mkdir()
    _write(repo, "requirements.txt", "vllm\n")
    _write(repo, "uv.lock", '[[package]]\nname = "vllm"\n')
    result = _scan(repo)
    assert "vllm" in result.lockfiles[0].packages
