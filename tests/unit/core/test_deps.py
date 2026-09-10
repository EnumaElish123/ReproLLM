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
    # Malformed TOML is diagnosed and does not qualify as a manifest (M2F-T03).
    assert result.unparsed and result.manifest_present is False


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


# --- M2F-T03: pyproject manifest qualification (F-04) ------------------------


def test_tool_only_pyproject_is_not_a_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "ruff-only"
    repo.mkdir()
    _write(repo, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    result = _scan(repo)
    assert result.manifest_present is False


def test_build_system_only_pyproject_is_not_a_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "build-only"
    repo.mkdir()
    _write(repo, "pyproject.toml", '[build-system]\nrequires = ["hatchling"]\n')
    assert _scan(repo).manifest_present is False


def test_project_table_with_empty_deps_qualifies(tmp_path: Path) -> None:
    repo = tmp_path / "pep621-empty"
    repo.mkdir()
    _write(repo, "pyproject.toml", '[project]\nname = "x"\nversion = "0"\ndependencies = []\n')
    assert _scan(repo).manifest_present is True


def test_poetry_table_without_dependencies_qualifies(tmp_path: Path) -> None:
    repo = tmp_path / "poetry-empty"
    repo.mkdir()
    _write(repo, "pyproject.toml", '[tool.poetry]\nname = "x"\nversion = "0"\n')
    assert _scan(repo).manifest_present is True


def test_invalid_toml_diagnosed_and_not_a_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "bad-toml"
    repo.mkdir()
    _write(repo, "pyproject.toml", "[project ] oops")
    result = _scan(repo)
    assert result.manifest_present is False
    assert any(entry.startswith("pyproject.toml:") for entry in result.unparsed)


def test_tool_only_pyproject_rule_reports_critical(tmp_path: Path) -> None:
    from reprollm.core.context import AuditContext
    from reprollm.rules.env import DependencyManifestPresentRule
    from reprollm.schemas.finding import FindingStatus

    repo = tmp_path / "rule-check"
    repo.mkdir()
    _write(repo, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    finding = DependencyManifestPresentRule().check(AuditContext(repo, level=0))[0]
    assert finding.status == FindingStatus.FAIL


def test_requirements_still_qualifies_without_pyproject(tmp_path: Path) -> None:
    repo = tmp_path / "req-only"
    repo.mkdir()
    _write(repo, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    _write(repo, "requirements.txt", "torch==2.8.0\n")
    assert _scan(repo).manifest_present is True


# --- M2F-T04: physical pyproject evidence lines (F-05) ------------------------


PYPROJECT_PHYSICAL = """\
[build-system]
requires = ["hatchling"]

[project]
name = "x"
version = "0.1"

# comment inside project
dependencies = [
    "torch>=1.8",           # 10
    "transformers==4.57.0",
    "datasets==3.2.0",
]

[project.optional-dependencies]
gpu = [
    "accelerate>=0.26",     # 18
]
cpu = ["numpy==1.26.0"]

[tool.poetry.dependencies]
python = "^3.10"
torch = "2.8.0"             # 23
transformers = {version = "^4.57"}
"""


def test_pyproject_physical_lines(tmp_path: Path) -> None:
    repo = tmp_path / "physical"
    repo.mkdir()
    _write(repo, "pyproject.toml", PYPROJECT_PHYSICAL)
    decls = _scan(repo).declarations

    def line_of(name: str) -> int:
        return _by_name(decls, name)[0].line

    assert line_of("torch") == 10  # not an array index
    assert line_of("transformers") == 11
    assert line_of("datasets") == 12
    assert line_of("accelerate") == 17  # optional group, physical line
    assert line_of("numpy") == 19
    assert line_of("python") == 22  # poetry key, not mapping index
    assert all(d.line >= 1 for d in decls)


def test_pyproject_repeated_names_consume_in_order(tmp_path: Path) -> None:
    repo = tmp_path / "repeat"
    repo.mkdir()
    _write(
        repo,
        "pyproject.toml",
        (
            "[project]\n"
            'dependencies = ["peft>=0.2", "torch>=1.8"]\n\n'
            "[project.optional-dependencies]\n"
            'extra = ["peft==0.13.0"]\n'
        ),
    )
    decls = [d for d in _scan(repo).declarations if d.name == "peft"]
    assert [d.line for d in sorted(decls, key=lambda d: d.line)] == [2, 5]
    assert decls[0].specifier != decls[1].specifier


def test_pyproject_no_line_zero_emitted(tmp_path: Path) -> None:
    repo = tmp_path / "nozero"
    repo.mkdir()
    _write(
        repo,
        "pyproject.toml",
        '[project]\nname = "x"\ndependencies = ["vllm>=0.10", "openai>=1.0"]\n',
    )
    decls = _scan(repo).declarations
    assert decls and all(d.line >= 1 for d in decls)
    assert {d.line for d in decls} == {3}  # same physical line is legitimate


def test_pipfile_physical_lines(tmp_path: Path) -> None:
    repo = tmp_path / "pipfile-lines"
    repo.mkdir()
    _write(
        repo,
        "Pipfile",
        '[packages]\nrequests = "*"\n\n# comment\nnumpy = {version = "==1.26.0"}\n',
    )
    decls = _scan(repo).declarations
    assert _by_name(decls, "requests")[0].line == 2
    assert _by_name(decls, "numpy")[0].line == 5
