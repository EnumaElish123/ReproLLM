"""R07-C D-M-S: finite decoded shapes, without changing captured evidence."""

from pathlib import Path, PurePosixPath

import pytest

from reprollm.core.deps import Declarations, scan_dependencies
from reprollm.core.git import GitInfo
from reprollm.core.scanner import RepoScanner


class _RecordingScanner(RepoScanner):
    def __init__(self, root: Path) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.reads: list[tuple[str, int]] = []

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        self.reads.append((rel_path, max_bytes))
        return super().read_text(rel_path, max_bytes)


def _write(root: Path, name: str, body: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _declarations(result: Declarations) -> list[tuple[str, str, str | None, str | None, str, int]]:
    return [
        (
            item.name,
            item.display_name,
            item.specifier,
            item.exact_version,
            item.source_file,
            item.line,
        )
        for item in result.declarations
    ]


@pytest.mark.parametrize("location", ["project", "tool", "tool.poetry"])
@pytest.mark.parametrize("value", ["false", "0", '""', "[]", '"wrong"', "[1]"])
def test_pyproject_raw_wrong_mapping_is_recorded_before_qualification(
    tmp_path: Path, location: str, value: str
) -> None:
    body = f"{location} = {value}\n"
    _write(tmp_path, "nested/pyproject.toml", body)
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declarations == []
    assert result.lockfiles == []
    assert result.manifest_present is False
    assert result._project_manifests == {}
    assert result._uncertain_directories == {PurePosixPath("nested")}
    # Legacy diagnostics intentionally differ between falsey and truthy bad tool values.
    assert result.unparsed == (
        ["nested/pyproject.toml:0: invalid tool table"]
        if location == "tool" and value in {'"wrong"', "[1]"}
        else []
    )
    assert scanner.reads == [("nested/pyproject.toml", 512 * 1024)]
    assert result.declaration_read_issues == {"nested/pyproject.toml": "invalid_structure"}


@pytest.mark.parametrize(
    ("body", "formats"),
    [
        ("", frozenset()),
        ("tool = {}\n", frozenset()),
        ("[tool.ruff]\nline-length=100\n", frozenset()),
        ("project = {}\n", frozenset({"uv.lock", "poetry.lock"})),
        ("[tool.poetry]\n", frozenset({"poetry.lock"})),
        ("[project]\ndependencies=[]\n", frozenset({"uv.lock", "poetry.lock"})),
        ("[project]\noptional-dependencies={}\n", frozenset({"uv.lock", "poetry.lock"})),
        (
            '[project.optional-dependencies]\n""=[]\n',
            frozenset({"uv.lock", "poetry.lock"}),
        ),
        ("[tool.poetry]\ndependencies={}\n", frozenset({"poetry.lock"})),
        (
            "build-system=false\ndependency-groups=7\n[tool.poetry.group]\nbad=false\n",
            frozenset({"poetry.lock"}),
        ),
    ],
)
def test_pyproject_empty_missing_and_unchecked_fields_retain_qualification(
    tmp_path: Path, body: str, formats: frozenset[str]
) -> None:
    _write(tmp_path, "pyproject.toml", body)
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declarations == []
    assert result.lockfiles == []
    assert result.unparsed == []
    assert result.manifest_present is bool(formats)
    assert result._project_manifests == ({"pyproject.toml": formats} if formats else {})
    assert result._uncertain_directories == set()
    assert scanner.reads == [("pyproject.toml", 512 * 1024)]
    assert result.declaration_read_issues == {}


@pytest.mark.parametrize(
    ("header", "field", "value", "formats"),
    [
        ("project", "dependencies", value, frozenset({"uv.lock", "poetry.lock"}))
        for value in ["false", "0", '""', "{}", '"wrong"', "{x=1}"]
    ]
    + [
        ("project", "optional-dependencies", value, frozenset({"uv.lock", "poetry.lock"}))
        for value in ["false", "0", '""', "[]", '"wrong"', "[1]"]
    ]
    + [
        ("tool.poetry", "dependencies", value, frozenset({"poetry.lock"}))
        for value in ["false", "0", '""', "[]", '"wrong"', "[1]"]
    ],
)
def test_wrong_dependency_container_preserves_project_and_legacy_diagnostics(
    tmp_path: Path, header: str, field: str, value: str, formats: frozenset[str]
) -> None:
    _write(tmp_path, "pyproject.toml", f"[{header}]\n{field}={value}\n")
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declarations == []
    assert result.lockfiles == []
    assert result.unparsed == []
    assert result.manifest_present is True
    assert result._project_manifests == {"pyproject.toml": formats}
    assert result._uncertain_directories == set()
    assert scanner.reads == [("pyproject.toml", 512 * 1024)]
    assert result.declaration_read_issues == {"pyproject.toml": "invalid_structure"}


@pytest.mark.parametrize("bad_member", ["false", "7", "[]", "{}"])
@pytest.mark.parametrize("optional", [False, True])
def test_project_partial_lists_keep_each_valid_declaration_and_exact_credit(
    tmp_path: Path, bad_member: str, optional: bool
) -> None:
    body = (
        '[project]\ndependencies=["numpy==1.26.4", ' + bad_member + ', "torch>=2"]\n'
        if not optional
        else '[project.optional-dependencies]\nfirst=["numpy==1.26.4", '
        + bad_member
        + ', "torch>=2"]\n'
    )
    _write(tmp_path, "pyproject.toml", body)
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert _declarations(result) == [
        ("numpy", "numpy", "==1.26.4", "1.26.4", "pyproject.toml", 2),
        ("torch", "torch", ">=2", None, "pyproject.toml", 2),
    ]
    assert result.unparsed == []
    assert result.lockfiles == []
    assert result.manifest_present is True
    assert result._project_manifests == {"pyproject.toml": frozenset({"uv.lock", "poetry.lock"})}
    assert result._uncertain_directories == set()
    assert scanner.reads == [("pyproject.toml", 512 * 1024)]
    assert result.declaration_read_issues == {"pyproject.toml": "invalid_structure"}


@pytest.mark.parametrize("bad_group", ["false", "0", '""', "{}", '"wrong"'])
def test_optional_bad_group_does_not_drop_good_sibling_groups(
    tmp_path: Path, bad_group: str
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        '[project.optional-dependencies]\nfirst=["numpy==1.26.4"]\n'
        f"bad={bad_group}\n"
        'last=["torch>=2"]\n',
    )

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert _declarations(result) == [
        ("numpy", "numpy", "==1.26.4", "1.26.4", "pyproject.toml", 2),
        ("torch", "torch", ">=2", None, "pyproject.toml", 4),
    ]
    assert result.unparsed == []
    assert result._uncertain_directories == set()
    assert result.declaration_read_issues == {"pyproject.toml": "invalid_structure"}


@pytest.mark.parametrize("manager", ["poetry", "pipfile"])
@pytest.mark.parametrize(
    ("value", "specifier", "exact"),
    [
        ('[{version="^2", python="<3.11"}, {version="^3", python=">=3.11"}]', None, None),
        ('{git="public"}', None, None),
        ('{path="local", version="==2.5.1"}', "==2.5.1", None),
        ("{version=false}", None, None),
        ("[]", None, None),
        ("{}", None, None),
        ("0", None, None),
    ],
)
def test_individual_manager_package_values_are_outside_structural_policy(
    tmp_path: Path, manager: str, value: str, specifier: str | None, exact: str | None
) -> None:
    name = "pyproject.toml" if manager == "poetry" else "Pipfile"
    section = "tool.poetry.dependencies" if manager == "poetry" else "packages"
    _write(tmp_path, name, f"[{section}]\ntorch={value}\n")

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert _declarations(result) == [("torch", "torch", specifier, exact, name, 2)]
    assert result.unparsed == []
    assert result.manifest_present is True
    assert result.declaration_read_issues == {}


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize("value", ["false", "0", '""', "[]", '"wrong"', "[1]"])
def test_pipfile_bad_section_preserves_the_other_section_and_barrier(
    tmp_path: Path, section: str, value: str
) -> None:
    other = "dev-packages" if section == "packages" else "packages"
    _write(tmp_path, "Pipfile", f'{section}={value}\n[{other}]\ntorch="==2.5.1"\n')
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert _declarations(result) == [("torch", "torch", None, "2.5.1", "Pipfile", 3)]
    assert result.unparsed == []
    assert result.manifest_present is True
    assert result._project_manifests == {"Pipfile": frozenset({"Pipfile.lock"})}
    assert result._uncertain_directories == {PurePosixPath(".")}
    assert scanner.reads == [("Pipfile", 512 * 1024)]
    assert result.declaration_read_issues == {"Pipfile": "invalid_structure"}


@pytest.mark.parametrize(
    ("body", "qualified"),
    [("", False), ("custom=false\n", False), ("packages={}\n", True), ("dev-packages={}\n", True)],
)
def test_pipfile_missing_empty_and_custom_categories_do_not_create_issues(
    tmp_path: Path, body: str, qualified: bool
) -> None:
    _write(tmp_path, "Pipfile", body)

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert result.declarations == []
    assert result.unparsed == []
    assert result.manifest_present is True
    assert result._project_manifests == (
        {"Pipfile": frozenset({"Pipfile.lock"})} if qualified else {}
    )
    assert result._uncertain_directories == set()
    assert result.declaration_read_issues == {}


@pytest.mark.parametrize("name", ["environment.yml", "environment.yaml"])
@pytest.mark.parametrize("body", ["[]", "false", "0", '""', "text", "[pytorch==2.5.1]"])
def test_environment_wrong_root_is_not_misreported_as_a_body_decoder_failure(
    tmp_path: Path, name: str, body: str
) -> None:
    _write(tmp_path, name, body + "\n")
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declarations == []
    assert result.lockfiles == []
    assert result.unparsed == []
    assert result.manifest_present is True
    assert result._project_manifests == {}
    assert result._uncertain_directories == set()
    assert scanner.reads == [(name, 512 * 1024)]
    assert result.declaration_read_issues == {name: "invalid_structure"}


@pytest.mark.parametrize(
    ("body", "qualified"),
    [
        ("", False),
        ("null\n", False),
        ("~\n", False),
        ("{}\n", False),
        ("name: example\n", False),
        ("dependencies: []\n", True),
        (
            "dependencies: [{}, {unknown: false}, {selector: [null]}, {pip: [], other: false}]\n",
            True,
        ),
    ],
)
def test_environment_none_and_unknown_mappings_keep_the_bounded_compatibility_exception(
    tmp_path: Path, body: str, qualified: bool
) -> None:
    _write(tmp_path, "environment.yml", body)

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert result.declarations == []
    assert result.unparsed == []
    assert result.manifest_present is True
    assert result._project_manifests == (
        {"environment.yml": frozenset({"conda-lock.yml"})} if qualified else {}
    )
    assert result._uncertain_directories == set()
    assert result.declaration_read_issues == {}


@pytest.mark.parametrize("value", ["null", "false", "0", '""', "{}", "text", "{pip: []}"])
def test_environment_present_wrong_dependencies_preserves_barrier_and_falsey_diagnostics(
    tmp_path: Path, value: str
) -> None:
    _write(tmp_path, "environment.yml", f"dependencies: {value}\n")
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert result.declarations == []
    assert result.lockfiles == []
    assert result.unparsed == (
        ["environment.yml:0: invalid dependencies collection"]
        if value in {"text", "{pip: []}"}
        else []
    )
    assert result.manifest_present is True
    assert result._project_manifests == {}
    assert result._uncertain_directories == {PurePosixPath(".")}
    assert scanner.reads == [("environment.yml", 512 * 1024)]
    assert result.declaration_read_issues == {"environment.yml": "invalid_structure"}


@pytest.mark.parametrize("bad_member", ["null", "false", "0", "[]", "[nested]"])
def test_environment_bad_members_preserve_conda_and_embedded_pip_evidence(
    tmp_path: Path, bad_member: str
) -> None:
    _write(
        tmp_path,
        "environment.yml",
        f"dependencies:\n  - pytorch==2.5.1\n  - {bad_member}\n  - pip: [numpy>=1]\n",
    )
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert _declarations(result) == [
        ("torch", "pytorch", "==2.5.1", "2.5.1", "environment.yml", 1),
        ("numpy", "numpy", ">=1", None, "environment.yml", 3),
    ]
    assert result.unparsed == []
    assert result._project_manifests == {"environment.yml": frozenset({"conda-lock.yml"})}
    assert result._uncertain_directories == set()
    assert scanner.reads == [("environment.yml", 512 * 1024)]
    assert result.declaration_read_issues == {"environment.yml": "invalid_structure"}


@pytest.mark.parametrize("value", ["null", "false", "0", '""', "{}", "text"])
def test_environment_wrong_pip_value_does_not_drop_other_declarations(
    tmp_path: Path, value: str
) -> None:
    _write(
        tmp_path,
        "environment.yml",
        f"dependencies:\n  - pip: {value}\n    unknown: false\n  - pytorch==2.5.1\n",
    )

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert _declarations(result) == [("torch", "pytorch", "==2.5.1", "2.5.1", "environment.yml", 2)]
    assert result.unparsed == []
    assert result._uncertain_directories == set()
    assert result.declaration_read_issues == {"environment.yml": "invalid_structure"}


@pytest.mark.parametrize("bad_member", ["null", "false", "0", "[]", "{}"])
def test_environment_partial_pip_list_preserves_exact_loose_and_empty_string_handling(
    tmp_path: Path, bad_member: str
) -> None:
    _write(
        tmp_path,
        "environment.yml",
        'dependencies:\n  - pip: ["torch==2.5.1", '
        + bad_member
        + ', "numpy>=1", "", "  "]\n    unknown: false\n',
    )

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert _declarations(result) == [
        ("torch", "torch", "==2.5.1", "2.5.1", "environment.yml", 1),
        ("numpy", "numpy", ">=1", None, "environment.yml", 1),
    ]
    assert result.unparsed == []
    assert result._uncertain_directories == set()
    assert result.declaration_read_issues == {"environment.yml": "invalid_structure"}


def test_file_level_structure_failure_keeps_lock_inventory_and_partial_credit(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "pyproject.toml",
        '[project]\ndependencies=["torch>=2", false]\noptional-dependencies=false\n',
    )
    _write(tmp_path, "uv.lock", 'package=[{name="torch"}]\n')
    scanner = _RecordingScanner(tmp_path)

    result = scan_dependencies(scanner)

    assert _declarations(result) == [("torch", "torch", ">=2", None, "pyproject.toml", 2)]
    assert [(lock.path, lock.packages, lock.read_issue) for lock in result.lockfiles] == [
        ("uv.lock", frozenset({"torch"}), None)
    ]
    assert result.qualified_lock_packages([]) == frozenset({"torch"})
    assert result.qualified_lock_packages([("torch", "main.py")]) == frozenset({"torch"})
    assert result.unparsed == []
    assert result._uncertain_directories == set()
    assert scanner.reads == [("pyproject.toml", 512 * 1024), ("uv.lock", 512 * 1024)]
    assert result.declaration_read_issues == {"pyproject.toml": "invalid_structure"}


def test_repaired_or_removed_structure_issue_is_not_retained_across_fresh_scans(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies=["torch>=2", false]\n')
    broken = scan_dependencies(_RecordingScanner(tmp_path))
    assert broken.declaration_read_issues == {"pyproject.toml": "invalid_structure"}

    _write(tmp_path, "pyproject.toml", '[project]\ndependencies=["torch>=2", "torch==2.5.1"]\n')
    repaired = scan_dependencies(_RecordingScanner(tmp_path))
    assert repaired.declaration_read_issues == {}
    assert _declarations(repaired) == [
        ("torch", "torch", ">=2", None, "pyproject.toml", 2),
        ("torch", "torch", "==2.5.1", "2.5.1", "pyproject.toml", 2),
    ]

    _write(tmp_path, "pyproject.toml", '[project]\ndependencies=["torch>=2"]\n')
    removed = scan_dependencies(_RecordingScanner(tmp_path))
    assert removed.declaration_read_issues == {}
    assert _declarations(removed) == [("torch", "torch", ">=2", None, "pyproject.toml", 2)]
    assert broken.declaration_read_issues == {"pyproject.toml": "invalid_structure"}


@pytest.mark.parametrize(
    "body", ['[project]\ndependencies=["", "  "]\n', '[project]\ndependencies=["bad !!!"]\n']
)
def test_pep508_string_grammar_does_not_become_a_structure_issue(tmp_path: Path, body: str) -> None:
    _write(tmp_path, "pyproject.toml", body)

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert result.declarations == []
    assert result.declaration_read_issues == {"pyproject.toml": "unparsed_requirement"}


def test_pip_string_failure_is_separate_from_unchanged_unknown_nested_structure_checks(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "environment.yml",
        'dependencies: [{pip: ["", "  ", "not a requirement !!!"], unknown: {pip: false}}]\n',
    )

    result = scan_dependencies(_RecordingScanner(tmp_path))

    assert result.declarations == []
    assert result._uncertain_directories == set()
    assert result.declaration_read_issues == {"environment.yml": "unparsed_requirement"}
