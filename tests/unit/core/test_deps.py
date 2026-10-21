"""Dependency-declaration parsing tests (M2-T03): each format ≥3 cases."""

from pathlib import Path
from typing import IO, Any

import pytest

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
    assert not _by_name(decls, "python")[0].is_exact  # Single equality is prefix matching.
    torch = _by_name(decls, "torch")[0]  # pytorch → torch
    assert not torch.is_exact and torch.exact_version is None
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


# --- R07-C D-F: typed known format-lock body read/syntax failures ------------


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
@pytest.mark.parametrize("failure", ["syntax", "unreadable"])
def test_format_lock_known_failure_is_not_a_successfully_empty_package_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_name: str, failure: str
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\nname = "failed"\ndependencies = ["torch>=2"]\n')
    _write(tmp_path, lock_name, "[broken\n")
    if failure == "unreadable":
        original_open = Path.open

        def deny_lock(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
            if path == tmp_path / lock_name:
                raise PermissionError("synthetic lock read denial")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", deny_lock)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.path == lock_name
    assert lock.packages == frozenset()
    assert lock.read_issue == ("invalid_syntax" if failure == "syntax" else "unreadable")
    assert result.qualified_lock_packages([]) == frozenset()
    assert result.unparsed == []


@pytest.mark.parametrize(
    ("lock_name", "content"),
    [
        ("uv.lock", ""),
        ("poetry.lock", ""),
        ("Pipfile.lock", "{}\n"),
        ("conda-lock.yml", "package: []\n"),
        ("conda-lock.yml", "null\n"),
        ("conda-lock.yml", ""),
        ("uv.lock", '[[package]]\nname = "torch"\n'),
        ("poetry.lock", '[[package]]\nname = "torch"\n'),
        ("Pipfile.lock", '{"default": {"torch": {}}}\n'),
        ("conda-lock.yml", "package:\n  - name: pytorch\n"),
    ],
)
def test_successfully_decoded_lock_bodies_are_not_known_read_or_syntax_failures(
    tmp_path: Path, lock_name: str, content: str
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\nname = "readable"\n')
    _write(tmp_path, lock_name, content)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.read_issue is None
    assert result.unverified_lock_paths([("torch", "a.py")]) == {}


@pytest.mark.parametrize(
    ("lock_name", "content"),
    [
        ("uv.lock", 'package = "invalid collection"\n'),
        ("poetry.lock", "[[package]]\nname = 12\n"),
        ("Pipfile.lock", "[]\n"),
        ("Pipfile.lock", '{"default": ["torch"]}\n'),
        ("conda-lock.yml", "- torch\n"),
        ("conda-lock.yml", "package: invalid collection\n"),
        ("conda-lock.yml", "package:\n  - name: 12\n"),
    ],
)
def test_decoded_invalid_lock_shapes_are_known_structural_failures(
    tmp_path: Path, lock_name: str, content: str
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\nname = "shape"\ndependencies = ["torch>=2"]\n')
    if lock_name == "Pipfile.lock":
        _write(tmp_path, "Pipfile", '[packages]\ntorch = ">=2"\n')
    elif lock_name == "conda-lock.yml":
        _write(tmp_path, "environment.yml", "dependencies:\n  - pytorch>=2\n")
    _write(tmp_path, lock_name, content)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.read_issue == "invalid_structure"
    assert result.unverified_lock_paths([("torch", "a.py")]) == {"torch": (lock_name,)}
    assert result.qualified_lock_packages([("torch", "a.py")]) == frozenset()


# --- R07-C D-S: decoded container/name extraction uncertainty ---------------


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock"])
@pytest.mark.parametrize(
    ("body", "unparsed"),
    [
        ("package = false\n", []),
        ("package = 0\n", []),
        ('package = ""\n', []),
        ("package = {}\n", []),
        ('package = "not a list"\n', ["invalid package collection"]),
        ("package = [false]\n", []),
        ("package = [0]\n", []),
        ('package = ["torch"]\n', []),
        ("package = [[]]\n", []),
        ("package = [{}]\n", []),
        ('package = [{name = ""}]\n', []),
        ("package = [{name = false}]\n", ["invalid package name"]),
    ],
)
def test_toml_lock_structure_uncertainty_preserves_existing_diagnostics(
    tmp_path: Path, lock_name: str, body: str, unparsed: list[str]
) -> None:
    _write(tmp_path, lock_name, body)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.read_issue == "invalid_structure"
    assert lock.packages == frozenset()
    assert result.unparsed == [f"{lock_name}:0: {message}" for message in unparsed]


@pytest.mark.parametrize(
    ("body", "unparsed"),
    [
        ("false\n", []),
        ("0\n", []),
        ('""\n', []),
        ("[]\n", []),
        ("package: null\n", []),
        ("package: false\n", []),
        ("package: 0\n", []),
        ('package: ""\n', []),
        ("package: {}\n", []),
        ("package: invalid\n", ["invalid package collection"]),
        ("package: [null]\n", []),
        ("package: [false]\n", []),
        ("package: [0]\n", []),
        ("package: [torch]\n", []),
        ("package: [[]]\n", []),
        ("package: [{}]\n", []),
        ('package: [{name: ""}]\n', []),
        ("package: [{name: null}]\n", []),
        ("package: [{name: 12}]\n", ["invalid package name"]),
    ],
)
def test_conda_lock_structure_uncertainty_preserves_existing_diagnostics(
    tmp_path: Path, body: str, unparsed: list[str]
) -> None:
    _write(tmp_path, "conda-lock.yml", body)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.read_issue == "invalid_structure"
    assert lock.packages == frozenset()
    assert result.unparsed == [f"conda-lock.yml:0: {message}" for message in unparsed]


@pytest.mark.parametrize("body", ["null\n", "false\n", "0\n", '""\n', "[]\n"])
def test_pipfile_lock_nonmapping_document_is_structurally_unverified(
    tmp_path: Path, body: str
) -> None:
    _write(tmp_path, "Pipfile.lock", body)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.read_issue == "invalid_structure"
    assert lock.packages == frozenset()
    assert result.unparsed == ["Pipfile.lock:0: invalid lock document"]


@pytest.mark.parametrize("section", ["default", "develop"])
@pytest.mark.parametrize("value", ["null", "false", "0", '""', "[]"])
def test_pipfile_lock_present_wrong_section_is_not_a_successfully_empty_section(
    tmp_path: Path, section: str, value: str
) -> None:
    _write(tmp_path, "Pipfile.lock", f'{{"{section}": {value}}}\n')

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.read_issue == "invalid_structure"
    assert lock.packages == frozenset()
    assert result.unparsed == []


@pytest.mark.parametrize(
    ("lock_name", "body", "packages"),
    [
        ("uv.lock", "", frozenset()),
        ("uv.lock", "package = []\n", frozenset()),
        ("poetry.lock", "", frozenset()),
        ("poetry.lock", "package = []\n", frozenset()),
        ("Pipfile.lock", "{}\n", frozenset()),
        ("Pipfile.lock", '{"default": {}, "develop": {}}\n', frozenset()),
        ("conda-lock.yml", "", frozenset()),
        ("conda-lock.yml", "null\n", frozenset()),
        ("conda-lock.yml", "{}\n", frozenset()),
        ("conda-lock.yml", "package: []\n", frozenset()),
        ("uv.lock", '[[package]]\nname = " "\nversion = false\n', frozenset({""})),
        ("poetry.lock", '[[package]]\nname = "torch"\nversion = false\n', frozenset({"torch"})),
        ("Pipfile.lock", '{"default": {"torch": null}}\n', frozenset({"torch"})),
        ("Pipfile.lock", '{"default": {"": []}}\n', frozenset({""})),
        ("conda-lock.yml", 'package: [{name: " ", version: false}]\n', frozenset({""})),
        ("conda-lock.yml", "package: [{name: pytorch, version: false}]\n", frozenset({"torch"})),
    ],
)
def test_lock_structure_assessment_preserves_empty_and_opaque_legacy_contents(
    tmp_path: Path, lock_name: str, body: str, packages: frozenset[str]
) -> None:
    _write(tmp_path, lock_name, body)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.packages == packages
    assert lock.read_issue is None
    assert result.unparsed == []


@pytest.mark.parametrize(
    ("lock_name", "body", "unparsed"),
    [
        ("uv.lock", 'package = [{name = "torch"}, {}]\n', []),
        ("poetry.lock", 'package = [{name = "torch"}, {name = 12}]\n', ["invalid package name"]),
        ("Pipfile.lock", '{"default": {"torch": {}}, "develop": []}\n', []),
        ("Pipfile.lock", '{"default": null, "develop": {"torch": {}}}\n', []),
        ("conda-lock.yml", "package: [{name: pytorch}, false]\n", []),
    ],
)
def test_partially_extracted_lock_keeps_known_package_names_and_existing_credit(
    tmp_path: Path, lock_name: str, body: str, unparsed: list[str]
) -> None:
    if lock_name in {"uv.lock", "poetry.lock"}:
        _write(tmp_path, "pyproject.toml", '[project]\ndependencies = ["torch>=2", "numpy>=1"]\n')
    elif lock_name == "Pipfile.lock":
        _write(tmp_path, "Pipfile", '[packages]\ntorch = ">=2"\nnumpy = ">=1"\n')
    else:
        _write(tmp_path, "environment.yml", "dependencies:\n  - pytorch=2\n  - numpy=1\n")
    _write(tmp_path, lock_name, body)

    result = _scan(tmp_path)

    (lock,) = result.lockfiles
    assert lock.packages == frozenset({"torch"})
    assert lock.read_issue == "invalid_structure"
    assert result.qualified_lock_packages([]) == frozenset({"torch"})
    assert result.unverified_lock_paths([]) == {"numpy": (lock_name,), "torch": (lock_name,)}
    assert result.unparsed == [f"{lock_name}:0: {message}" for message in unparsed]


# --- R07-C D-M: bounded captured declaration-body uncertainty ---------------


class _DeclarationBodyScanner(RepoScanner):
    def __init__(self, root: Path) -> None:
        from reprollm.core.git import GitInfo

        super().__init__(root, GitInfo(is_repo=False))
        self.body_reads: list[str] = []

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        self.body_reads.append(rel_path)
        return super().read_text(rel_path, max_bytes)


def _assert_declaration_body_legacy_facts(result: Any, bad_path: str) -> None:
    assert [
        (d.name, d.display_name, d.specifier, d.exact_version, d.source_file, d.line)
        for d in result.declarations
    ] == [("torch", "torch", "==2.5.1", "2.5.1", "requirements.txt", 1)]
    assert result.manifest_present is True
    assert [(lock.path, lock.packages, lock.read_issue) for lock in result.lockfiles] == [
        ("requirements.txt", frozenset({"torch"}), None)
    ]
    assert result._project_manifests == {}
    if bad_path.endswith("requirements-bad.txt"):
        assert result._uncertain_directories == set()
    else:
        from pathlib import PurePosixPath

        assert result._uncertain_directories == {PurePosixPath("broken")}


def test_declaration_body_issue_map_defaults_preserve_legacy_positional_values() -> None:
    from reprollm.core.deps import Declarations

    declarations = Declarations([], [], [], False, {}, set())

    assert declarations.declaration_read_issues == {}
    assert Declarations().declaration_read_issues is not declarations.declaration_read_issues


@pytest.mark.parametrize(
    "basename",
    ["pyproject.toml", "Pipfile", "environment.yml", "environment.yaml", "requirements-bad.txt"],
)
@pytest.mark.parametrize("failure", ["permission", "binary", "invalid-utf8", "read-cap"])
def test_captured_declaration_body_read_failures_preserve_all_legacy_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, basename: str, failure: str
) -> None:
    _write(tmp_path, "requirements.txt", "torch==2.5.1\n")
    path = f"broken/{basename}"
    _write(tmp_path, path, "safe fixture\n")
    target = tmp_path / path
    if failure == "binary":
        target.write_bytes(b"SYNTHETIC_BODY_CANARY\x00\n")
    elif failure == "invalid-utf8":
        target.write_bytes(b"\xffSYNTHETIC_BODY_CANARY\n")
    elif failure == "read-cap":
        target.write_bytes(b"x" * (512 * 1024 + 1))
    else:
        original = Path.open

        def denied(source: Path, *args: Any, **kwargs: Any) -> Any:
            if source == target:
                raise PermissionError(f"{target}: SYNTHETIC_BODY_CANARY")
            return original(source, *args, **kwargs)

        monkeypatch.setattr(Path, "open", denied)
    scanner = _DeclarationBodyScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declaration_read_issues == {path: "unreadable"}
    assert result.unparsed == [f"{path}:0: unreadable"]
    assert scanner.body_reads.count(path) == 1
    assert sorted(scanner.body_reads) == sorted([path, "requirements.txt"])
    _assert_declaration_body_legacy_facts(result, path)
    diagnostics = "\n".join(result.unparsed + scanner.warnings)
    assert str(target) not in diagnostics
    assert "SYNTHETIC_BODY_CANARY" not in diagnostics


@pytest.mark.parametrize(
    ("basename", "body"),
    [
        ("pyproject.toml", "[project broken\n"),
        ("Pipfile", "[packages broken\n"),
        ("environment.yml", "dependencies: [broken\n"),
        ("environment.yaml", "dependencies: [broken\n"),
    ],
)
def test_caught_manager_body_decoder_failure_retains_old_diagnostic_and_capture(
    tmp_path: Path, basename: str, body: str
) -> None:
    import yaml

    from reprollm.core._toml import tomllib

    _write(tmp_path, "requirements.txt", "torch==2.5.1\n")
    path = f"broken/{basename}"
    _write(tmp_path, path, body)
    try:
        if basename.startswith("environment"):
            yaml.safe_load(body)
        else:
            tomllib.loads(body)
    except (tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
        legacy = f"{path}:0: {exc}"
    else:
        raise AssertionError("The test fixture must exercise an existing decoder failure")
    scanner = _DeclarationBodyScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declaration_read_issues == {path: "invalid_syntax"}
    assert result.unparsed == [legacy]
    assert sorted(scanner.body_reads) == sorted([path, "requirements.txt"])
    _assert_declaration_body_legacy_facts(result, path)


@pytest.mark.parametrize(
    "failure", ["missing", "binary", "invalid-utf8", "read-cap", "permission", "outside-alias"]
)
def test_requirements_actual_child_body_read_failure_is_recorded_without_extra_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root, "requirements.txt", "torch==2.5.1\n-r deps/base.txt\n")
    child = root / "deps/base.txt"
    child.parent.mkdir()
    outside = tmp_path / "outside-synthetic.txt"
    outside.write_text("openai==1.2.3 # SYNTHETIC_OUTSIDE_BODY_CANARY\n")
    if failure == "outside-alias":
        try:
            child.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    elif failure != "missing":
        child.write_bytes(
            b"x" * (512 * 1024 + 1)
            if failure == "read-cap"
            else b"\xffbad\n"
            if failure == "invalid-utf8"
            else b"bad\x00\n"
        )
    original = Path.open

    def guarded(source: Path, *args: Any, **kwargs: Any) -> Any:
        assert source != outside, "An outside include body must never be opened"
        if failure == "permission" and source == child:
            raise PermissionError("SYNTHETIC_BODY_EXCEPTION_CANARY")
        return original(source, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    scanner = _DeclarationBodyScanner(root)

    result = scan_dependencies(scanner)

    assert result.declaration_read_issues == {"deps/base.txt": "unreadable"}
    assert scanner.body_reads == ["requirements.txt", "deps/base.txt"]
    assert [(d.name, d.source_file, d.line, d.exact_version) for d in result.declarations] == [
        ("torch", "requirements.txt", 1, "2.5.1")
    ]
    assert result.lockfiles == []
    assert result.unparsed == ["requirements.txt:2: include unreadable"]
    assert result.manifest_present is True
    diagnostics = "\n".join(result.unparsed + scanner.warnings)
    assert str(outside) not in diagnostics
    assert "SYNTHETIC_OUTSIDE_BODY_CANARY" not in diagnostics
    assert "SYNTHETIC_BODY_EXCEPTION_CANARY" not in diagnostics


def test_shared_normalized_requirements_body_failure_is_read_and_recorded_once(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "requirements-a.txt", "-r deps/base.txt\n-r deps/../deps/base.txt\n")
    _write(tmp_path, "requirements-b.txt", "-r deps/base.txt\n")
    _write(tmp_path, "deps/base.txt", "bad\x00\n")
    scanner = _DeclarationBodyScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declaration_read_issues == {"deps/base.txt": "unreadable"}
    assert scanner.body_reads.count("deps/base.txt") == 1
    assert result.unparsed == [
        "requirements-a.txt:1: include unreadable",
        "requirements-b.txt:1: include unreadable",
    ]
    assert result.declarations == []
    assert result.lockfiles == []


@pytest.mark.parametrize(
    ("basename", "body", "structural_issue"),
    [
        ("pyproject.toml", "[tool.ruff]\n", False),
        ("pyproject.toml", "[project]\ndependencies=[]\n", False),
        ("pyproject.toml", "project=42\n", True),
        ("pyproject.toml", "tool=false\n", True),
        ("pyproject.toml", "[project]\ndependencies=42\n", True),
        ("pyproject.toml", "[tool.poetry]\ndependencies=[]\n", True),
        ("Pipfile", "[packages]\n", False),
        ("Pipfile", "packages=false\n", True),
        ("Pipfile", '[packages]\ntorch={version="==2.5.1",git="public"}\n', False),
        ("environment.yml", "", False),
        ("environment.yml", "null\n", False),
        ("environment.yml", "[]\n", True),
        ("environment.yml", "dependencies: false\n", True),
        ("environment.yml", "dependencies: [pytorch>=2, {pip: [false]}]\n", True),
        ("requirements.txt", "# comment only\n", False),
        ("requirements.txt", "not a requirement !!!\n", False),
        ("requirements.txt", "-e .\n--index-url https://example.invalid\n", False),
    ],
)
def test_readable_declaration_shapes_and_line_grammar_do_not_become_body_failures(
    tmp_path: Path, basename: str, body: str, structural_issue: bool
) -> None:
    _write(tmp_path, basename, body)

    result = scan_dependencies(_DeclarationBodyScanner(tmp_path))

    assert result.declaration_read_issues == (
        {basename: "invalid_structure"} if structural_issue else {}
    )


@pytest.mark.parametrize("edge", ["absolute", "escape", "malformed", "unsupported", "excluded"])
def test_unattempted_requirements_include_edges_do_not_invent_body_read_failures(
    tmp_path: Path, edge: str
) -> None:
    target = {
        "absolute": "/synthetic-outside-body.txt",
        "escape": "../synthetic-outside-body.txt",
        "malformed": "",
        "unsupported": '"quoted.txt"',
        "excluded": ".venv/base.txt",
    }[edge]
    _write(tmp_path, "requirements.txt", f"torch>=2\n-r {target}\n")
    scanner = _DeclarationBodyScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declaration_read_issues == {}
    assert scanner.body_reads == ["requirements.txt"]
    assert result.lockfiles == []
    assert result.unparsed == [
        "requirements.txt:2: "
        + (
            "include malformed"
            if edge == "malformed"
            else "include unsupported syntax"
            if edge == "unsupported"
            else "include unreadable"
        )
    ]


@pytest.mark.parametrize("graph", ["cycle", "depth", "excluded-root", "unlisted-root"])
def test_unexpanded_or_uncaptured_requirements_nodes_do_not_invent_body_read_failures(
    tmp_path: Path, graph: str
) -> None:
    if graph == "cycle":
        _write(tmp_path, "requirements.txt", "torch>=2\n-r deps/base.txt\n")
        _write(tmp_path, "deps/base.txt", "-r ../requirements.txt\n")
    elif graph == "depth":
        _write(tmp_path, "requirements.txt", "torch>=2\n-r deps/0.txt\n")
        for index in range(11):
            _write(tmp_path, f"deps/{index}.txt", f"-r {index + 1}.txt\n")
    elif graph == "excluded-root":
        _write(tmp_path, ".venv/requirements.txt", "bad\x00\n")
    else:
        _write(tmp_path, "requirements.txt", "x" * (2 * 1024 * 1024 + 1))
    scanner = _DeclarationBodyScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declaration_read_issues == {}
    if graph == "depth":
        assert "deps/10.txt" not in scanner.body_reads
        assert "deps/11.txt" not in scanner.body_reads
        assert "deps/9.txt:1: include depth limit" in result.unparsed
    elif graph in {"excluded-root", "unlisted-root"}:
        assert scanner.body_reads == []
        assert result.declarations == []
        assert result.unparsed == []
