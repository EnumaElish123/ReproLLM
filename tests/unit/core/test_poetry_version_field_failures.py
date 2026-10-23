"""R07-C D-M-V: explicit Poetry field types retain the complete captured view."""

import datetime
import math
from dataclasses import fields
from pathlib import Path, PurePosixPath

import pytest
from packaging.requirements import Requirement

from reprollm.core import deps as deps_module
from reprollm.core._toml import tomllib
from reprollm.core.deps import (
    Declarations,
    DependencyDeclaration,
    Lockfile,
    _RequirementFile,
    _RequirementInclude,
    _RequirementsClosure,
    _RequirementsGraph,
    scan_dependencies,
)
from reprollm.core.git import GitInfo
from reprollm.core.scanner import RepoScanner

_POETRY_FORMATS = frozenset({"poetry.lock"})
_PROJECT_FORMATS = frozenset({"uv.lock", "poetry.lock"})


class _Scanner(RepoScanner):
    def __init__(self, root: Path, *, reverse: bool = False) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.reads: list[tuple[str, int]] = []
        self.physical_reads: list[Path] = []
        self.candidates: list[str] = []
        self.list_calls = 0
        self.reverse = reverse

    def analysis_files(self) -> list[str]:
        self.list_calls += 1
        paths = super().analysis_files()
        return list(reversed(paths)) if self.reverse else paths

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        self.reads.append((rel_path, max_bytes))
        return super().read_text(rel_path, max_bytes)

    def _read_text_uncached(self, target: Path, rel_path: str, max_bytes: int) -> str | None:
        assert target.is_relative_to(self.root.resolve()), "External content reached physical open"
        self.physical_reads.append(target)
        return super()._read_text_uncached(target, rel_path, max_bytes)

    def is_analysis_candidate(self, rel_path: str) -> bool:
        self.candidates.append(rel_path)
        return super().is_analysis_candidate(rel_path)

    def exists(self, rel_path: str) -> bool:
        raise AssertionError(f"Unexpected existence probe: {rel_path}")

    def size(self, rel_path: str) -> int | None:
        raise AssertionError(f"Unexpected size probe: {rel_path}")


@pytest.fixture
def requirement_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def recorded(value: str) -> Requirement:
        calls.append(value)
        return Requirement(value)

    monkeypatch.setattr(deps_module, "Requirement", recorded)
    return calls


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))


def _poetry(value: str) -> str:
    return f"[tool.poetry.dependencies]\nPyTorch={value}\n"


def _decl(
    name: str = "torch",
    specifier: str | None = None,
    exact: str | None = None,
    line: int = 2,
    source: str = "pyproject.toml",
    display: str = "PyTorch",
) -> DependencyDeclaration:
    return DependencyDeclaration(name, display, specifier, exact, source, line)


def _expected(
    declarations: tuple[DependencyDeclaration, ...] = (),
    diagnostics: tuple[str, ...] = (),
    *,
    projects: dict[str, frozenset[str]] | None = None,
    barriers: tuple[str, ...] = (),
    locks: tuple[Lockfile, ...] = (),
    issues: dict[str, str] | None = None,
    frontier: tuple[str, ...] = (),
    manifest: bool = True,
) -> Declarations:
    return Declarations(
        list(declarations),
        list(diagnostics),
        list(locks),
        manifest,
        {"pyproject.toml": _POETRY_FORMATS} if projects is None else projects,
        {PurePosixPath(path) for path in barriers},
        {} if issues is None else issues,
        frontier,
    )


def _capture(
    root: Path, monkeypatch: pytest.MonkeyPatch, *, reverse: bool = False
) -> tuple[Declarations, _Scanner, _RequirementsGraph]:
    graphs: list[_RequirementsGraph] = []

    def graph_factory(scanner: RepoScanner, result: Declarations) -> _RequirementsGraph:
        graph = _RequirementsGraph(scanner, result)
        graphs.append(graph)
        return graph

    monkeypatch.setattr(deps_module, "_RequirementsGraph", graph_factory)
    scanner = _Scanner(root, reverse=reverse)
    result = scan_dependencies(scanner)
    assert len(graphs) == 1
    return result, scanner, graphs[0]


def _assert_capture(
    result: Declarations,
    expected: Declarations,
    scanner: _Scanner,
    reads: list[str],
    *,
    candidates: list[str] | None = None,
    credit: frozenset[str] = frozenset(),
) -> None:
    assert scanner.reads == [(path, 512 * 1024) for path in reads]
    assert scanner.candidates == ([] if candidates is None else candidates)
    assert scanner.list_calls == 2
    assert result.qualified_lock_packages([]) == credit
    assert result.unverified_lock_paths([]) == {}
    # Check all original capture facts before the new policy fact.
    for field in fields(Declarations):
        if field.name != "declaration_read_issues":
            assert getattr(result, field.name) == getattr(expected, field.name), field.name
    assert list(result._project_manifests.items()) == list(expected._project_manifests.items())
    assert list(result.declaration_read_issues.items()) == list(
        expected.declaration_read_issues.items()
    )


@pytest.mark.parametrize(
    ("literal", "decoded_type"),
    [
        ("false", bool),
        ("true", bool),
        ("0", int),
        ("7", int),
        ("0.0", float),
        ("2.5", float),
        ("inf", float),
        ("+inf", float),
        ("-inf", float),
        ("nan", float),
        ("[]", list),
        ('["2.5.1"]', list),
        ('["2.5.1", false]', list),
        ("{}", dict),
        ('{nested="2.5.1"}', dict),
        ("1979-05-27", datetime.date),
        ("07:32:00", datetime.time),
        ("1979-05-27T07:32:00", datetime.datetime),
        ("1979-05-27T07:32:00Z", datetime.datetime),
    ],
)
def test_t01_t06_real_toml_nonstring_field_records_one_issue_and_keeps_named_declaration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    literal: str,
    decoded_type: type,
) -> None:
    body = _poetry(f"{{version={literal}}}")
    decoded = tomllib.loads(body)["tool"]["poetry"]["dependencies"]["PyTorch"]["version"]
    assert type(decoded) is decoded_type
    if literal == "nan":
        assert math.isnan(decoded)
    if literal in ("inf", "+inf", "-inf"):
        assert math.isinf(decoded)
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    assert graph.nodes == graph.closures == {}
    _assert_capture(
        result,
        _expected((_decl(),), issues={"pyproject.toml": "invalid_structure"}),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("value", "specifier", "exact"),
    [
        ('""', None, None),
        ('" \\t "', None, None),
        ('"2.5.1"', None, "2.5.1"),
        ('" 2.5.1 "', None, "2.5.1"),
        ('"1!2.5.1"', None, "1!2.5.1"),
        ('"2.5.1rc1"', None, "2.5.1rc1"),
        ('"2.5.1.post1"', None, "2.5.1.post1"),
        ('"2.5.1.dev1"', None, "2.5.1.dev1"),
        ('"2.5.1+cpu"', None, "2.5.1+cpu"),
        ('"==2.5.1"', None, "2.5.1"),
        ('" >=2 "', ">=2", None),
        ('"^2.5"', "^2.5", None),
        ('"~2.5"', "~2.5", None),
        ('"*"', "*", None),
        ('"==2.*"', "==2.*", None),
        ('"==2.5.1,!=2.0"', "==2.5.1,!=2.0", None),
        ('"===2.5.1"', "===2.5.1", None),
        ('"not a version"', "not a version", None),
        ('"https://example.invalid/torch.whl"', "https://example.invalid/torch.whl", None),
    ],
)
def test_t09_t13_every_string_retains_existing_extraction_without_a_field_type_issue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    value: str,
    specifier: str | None,
    exact: str | None,
) -> None:
    _write(tmp_path, {"pyproject.toml": _poetry(f"{{version={value}}}")})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    assert graph.nodes == graph.closures == {}
    _assert_capture(
        result, _expected((_decl(specifier=specifier, exact=exact),)), scanner, ["pyproject.toml"]
    )


@pytest.mark.parametrize(
    "value",
    [
        "{}",
        '{source="private-source"}',
        "{optional=true}",
        '{extras=["cpu"], markers="python_version > 0"}',
        "{Version=false}",
        "{VERSION=0}",
        "{unknown={version=false}}",
        "{versioned=false}",
    ],
)
def test_t07_t08_t32_missing_raw_version_key_is_not_inferred_from_empty_helper_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], value: str
) -> None:
    _write(tmp_path, {"pyproject.toml": _poetry(value)})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(result, _expected((_decl(),)), scanner, ["pyproject.toml"])


@pytest.mark.parametrize("key", ['"version"', "'version'", "version"])
def test_t32_exact_decoded_raw_key_is_checked_without_other_property_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], key: str
) -> None:
    body = _poetry(f'{{Version="2.5.1", unknown=true, {key}=false}}')
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected((_decl(),), issues={"pyproject.toml": "invalid_structure"}),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("value", "specifier", "exact"),
    [
        ('"2.5.1"', None, "2.5.1"),
        ('"^2"', "^2", None),
        ("false", None, None),
        ("0", None, None),
        ("2.5", None, None),
        ("1979-05-27", None, None),
        ("[]", None, None),
        ('["2.5.1"]', None, None),
        ('[{version="^2", python="<3.11"}, {version="^3", python=">=3.11"}]', None, None),
        ("[{version=false}]", None, None),
        ("[{version={nested=false}}]", None, None),
    ],
)
def test_t14_t16_whole_nonmapping_values_and_multiple_constraints_are_not_descended_into(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    value: str,
    specifier: str | None,
    exact: str | None,
) -> None:
    _write(tmp_path, {"pyproject.toml": _poetry(value)})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result, _expected((_decl(specifier=specifier, exact=exact),)), scanner, ["pyproject.toml"]
    )


@pytest.mark.parametrize("transport", ["url", "git", "path", "file", "hg", "svn", "bzr"])
@pytest.mark.parametrize(
    ("version", "specifier", "issue"),
    [("", None, False), (',version="==2.5.1"', "==2.5.1", False), (",version=0", None, True)],
)
def test_t17_t19_transport_keys_preserve_no_exact_credit_and_do_not_exempt_nonstring_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    transport: str,
    version: str,
    specifier: str | None,
    issue: bool,
) -> None:
    # Even an empty/false transport field preserves the old no-exact policy.
    _write(tmp_path, {"pyproject.toml": _poetry(f"{{{transport}=false{version}}}")})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            (_decl(specifier=specifier),),
            issues={"pyproject.toml": "invalid_structure"} if issue else {},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("bad_first", [False, True])
def test_t28_existing_container_precheck_wins_without_losing_partial_pep621_or_poetry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    bad_first: bool,
) -> None:
    members = 'false,"numpy==","numpy==1.26.4"' if bad_first else '"numpy==",false,"numpy==1.26.4"'
    body = (
        f"[project]\ndependencies=[{members}]\n"
        '[tool.poetry.dependencies]\nPyTorch={version=false}\npeft="0.13.0"\n'
    )
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["numpy==", "numpy==1.26.4"]
    _assert_capture(
        result,
        _expected(
            (
                _decl("numpy", "==1.26.4", "1.26.4", 2, display="numpy"),
                _decl(line=4),
                _decl("peft", None, "0.13.0", 5, display="peft"),
            ),
            ("pyproject.toml:2: numpy==",),
            projects={"pyproject.toml": _PROJECT_FORMATS},
            issues={"pyproject.toml": "invalid_structure"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("optional", [False, True])
def test_t29_earlier_pep621_parse_failure_keeps_first_cause_before_poetry_field_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    optional: bool,
) -> None:
    project = (
        '[project.optional-dependencies]\nextra=["numpy==","torch==2.5.1"]\n'
        if optional
        else '[project]\ndependencies=["numpy==","torch==2.5.1"]\n'
    )
    _write(
        tmp_path,
        {"pyproject.toml": project + "[tool.poetry.dependencies]\nPyTorch={version=false}\n"},
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["numpy==", "torch==2.5.1"]
    _assert_capture(
        result,
        _expected(
            (_decl(specifier="==2.5.1", exact="2.5.1", display="torch"), _decl(line=4)),
            ("pyproject.toml:2: numpy==",),
            projects={"pyproject.toml": _PROJECT_FORMATS},
            issues={"pyproject.toml": "unparsed_requirement"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_t30_t31_all_logical_sources_and_siblings_keep_encounter_order_and_distinct_causes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], reverse: bool
) -> None:
    _write(
        tmp_path,
        {
            "z/pyproject.toml": _poetry("{version=[]}"),
            "pyproject.toml": (
                '[tool.poetry.dependencies]\nrequests={version=0}\nPyTorch="2.5.1"\n'
                'peft={version=false}\nnumpy="^1"\n'
            ),
            "a/pyproject.toml": _poetry("{version=false}"),
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch, reverse=reverse)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            (
                _decl("requests", line=2, display="requests"),
                _decl(exact="2.5.1", line=3),
                _decl("peft", line=4, display="peft"),
                _decl("numpy", "^1", line=5, display="numpy"),
                _decl(source="a/pyproject.toml"),
                _decl(source="z/pyproject.toml"),
            ),
            projects={
                "pyproject.toml": _POETRY_FORMATS,
                "a/pyproject.toml": _POETRY_FORMATS,
                "z/pyproject.toml": _POETRY_FORMATS,
            },
            issues={
                "pyproject.toml": "invalid_structure",
                "a/pyproject.toml": "invalid_structure",
                "z/pyproject.toml": "invalid_structure",
            },
        ),
        scanner,
        ["pyproject.toml", "a/pyproject.toml", "z/pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("body", "qualified", "diagnostics", "barriers"),
    [
        ("tool=false\n", False, (), (".",)),
        ("[tool]\npoetry=0\n", False, (), (".",)),
        ("[tool.poetry]\ndependencies=false\n", True, (), ()),
        ("[tool.poetry]\ndependencies=[{version=false}]\n", True, (), ()),
        (
            "project=false\n[tool.poetry.dependencies]\nPyTorch={version=false}\n",
            True,
            (),
            (".",),
        ),
    ],
)
def test_t33_existing_parent_checks_and_barriers_are_not_reordered_or_expanded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    body: str,
    qualified: bool,
    diagnostics: tuple[str, ...],
    barriers: tuple[str, ...],
) -> None:
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            (_decl(line=3),) if body.startswith("project=") else (),
            diagnostics,
            projects={"pyproject.toml": _POETRY_FORMATS} if qualified else {},
            manifest=qualified,
            barriers=barriers,
            issues={"pyproject.toml": "invalid_structure"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("body", "qualified"),
    [
        ("[tool.poetry.group.dev.dependencies]\ntorch={version=false}\n", True),
        ("[tool.poetry.dev-dependencies]\ntorch={version=false}\n", True),
        ("[dependency-groups]\ndev=[{version=false}]\n", False),
        ("[build-system]\nrequires=[{version=false}]\n", False),
    ],
)
def test_t34_unvisited_sections_are_neither_traversed_nor_validated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    body: str,
    qualified: bool,
) -> None:
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            projects={"pyproject.toml": _POETRY_FORMATS} if qualified else {},
            manifest=qualified,
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
def test_t35_pipfile_shared_helper_keeps_separate_opt_in_and_original_line_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], section: str
) -> None:
    _write(
        tmp_path,
        {"Pipfile": f'[{section}]\nPyTorch={{version=false}}\npeft="==0.13.0"\n'},
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            (
                _decl(source="Pipfile"),
                _decl("peft", None, "0.13.0", 3, "Pipfile", "peft"),
            ),
            projects={"Pipfile": frozenset({"Pipfile.lock"})},
        ),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize(
    ("body", "line"),
    [
        ("# first line\n\n[tool.poetry.dependencies]\nPyTorch={version=false}\n", 4),
        ("# first line\n[tool.poetry.dependencies.PyTorch]\n# version follows\nversion=false\n", 1),
        ("[tool.poetry]\ndependencies={PyTorch={version=false}}\n", 1),
        (
            '[tool.poetry.dependencies]\npeft="0.13.0"\n'
            "[tool.poetry.dependencies.PyTorch]\nversion=false\n",
            1,
        ),
    ],
)
def test_t39_inline_expanded_and_fallback_locations_keep_the_old_package_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    body: str,
    line: int,
) -> None:
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    declarations = (
        (_decl("peft", None, "0.13.0", 2, display="peft"), _decl(line=line))
        if body.startswith("[tool.poetry.dependencies]\npeft=")
        else (_decl(line=line),)
    )
    _assert_capture(
        result,
        _expected(declarations, issues={"pyproject.toml": "invalid_structure"}),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("failure", ["binary", "oversize", "syntax"])
@pytest.mark.security
def test_t37_t38_read_and_decode_failures_return_before_field_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    failure: str,
) -> None:
    _write(tmp_path, {"pyproject.toml": "[tool.poetry.dependencies]\nPyTorch={version=false}\n"})
    if failure == "syntax":
        body = "[tool.poetry.dependencies\nPyTorch={version=false}\n"
        (tmp_path / "pyproject.toml").write_text(body, encoding="utf-8")

        # Pin the caught decoder message while retaining the real decode-failure route.
        def decoder(text: str) -> dict[str, object]:
            assert text == body
            raise tomllib.TOMLDecodeError("synthetic TOML failure")

        monkeypatch.setattr(deps_module.tomllib, "loads", decoder)
        issue = "invalid_syntax"
        diagnostic = "synthetic TOML failure"
    else:
        (tmp_path / "pyproject.toml").write_bytes(
            b"\x00version=false" if failure == "binary" else b" " * (512 * 1024 + 1)
        )
        issue = "unreadable"
        diagnostic = "unreadable"

    def helper(value: object, *, allow_bare: bool) -> tuple[str | None, str | None]:
        raise AssertionError("No extracted package value should reach the helper")

    monkeypatch.setattr(deps_module, "_dependency_version_field", helper)
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            diagnostics=(f"pyproject.toml:0: {diagnostic}",),
            projects={},
            barriers=(".",),
            manifest=False,
            issues={"pyproject.toml": issue},
        ),
        scanner,
        ["pyproject.toml"],
    )


def test_t38_filtered_unlisted_and_unrecognized_sources_are_not_read_or_inferred(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    body = _poetry("{version=false}")
    _write(
        tmp_path,
        {
            ".venv/pyproject.toml": body,
            ".reprollm/runs/old/pyproject.toml": body,
            "elsewhere.toml": body,
            "pyproject.toml": "[tool.ruff]\nline-length=100\n",
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(result, _expected(projects={}, manifest=False), scanner, ["pyproject.toml"])


@pytest.mark.security
@pytest.mark.parametrize("outside", [False, True])
def test_t38_t41_real_alias_preserves_logical_identity_and_refuses_external_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], outside: bool
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "outside.txt" if outside else root / "storage/body.txt"
    target.parent.mkdir(exist_ok=True)
    target.write_text(_poetry("{version=false}"), encoding="utf-8")
    try:
        (root / "pyproject.toml").symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"real symlink unavailable: {type(exc).__name__}")
    result, scanner, _ = _capture(root, monkeypatch)
    assert requirement_calls == []
    assert scanner.physical_reads == ([] if outside else [target.resolve()])
    _assert_capture(
        result,
        _expected(
            () if outside else (_decl(),),
            ("pyproject.toml:0: unreadable",) if outside else (),
            projects={} if outside else {"pyproject.toml": _POETRY_FORMATS},
            barriers=(".",) if outside else (),
            manifest=not outside,
            issues={"pyproject.toml": "unreadable" if outside else "invalid_structure"},
        ),
        scanner,
        ["pyproject.toml"],
    )


def test_t40_legacy_manual_values_keep_empty_independent_internal_defaults() -> None:
    old = Declarations([], [], [], False, {}, set())
    other = Declarations()
    assert old == other == Declarations()
    assert old.declaration_read_issues is not other.declaration_read_issues
    old.declarations.append(_decl())
    assert old.declaration_read_issues == {}
    assert other.declarations == []
    assert old.unexpanded_requirement_targets == ()


def test_t36_t41_complete_graph_and_other_manager_facts_do_not_follow_poetry_field_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": _poetry("{version=false}"),
            "requirements.txt": "-r deps/pins.txt\ntorch>=2\n",
            "deps/pins.txt": "numpy==1.26.4 # exact comment\n",
            "environment.yml": 'dependencies: [{pip: ["peft=="]}]\n',
            "Pipfile": "[packages]\ntransformers={version=false}\n",
        },
    )
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    numpy = _decl("numpy", "==1.26.4", "1.26.4", 1, "deps/pins.txt", "numpy")
    torch = _decl(specifier=">=2", line=2, source="requirements.txt", display="torch")
    assert requirement_calls == [
        "torch>=2",
        "numpy==1.26.4 # exact comment",
        "numpy==1.26.4",
        "numpy==1.26.4",
        "peft==",
    ]
    assert graph.nodes == {
        "requirements.txt": _RequirementFile(
            True, (_RequirementInclude(1, "deps/pins.txt"), torch)
        ),
        "deps/pins.txt": _RequirementFile(True, (numpy,)),
    }
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            True, frozenset({"requirements.txt", "deps/pins.txt"}), frozenset({numpy, torch})
        )
    }
    _assert_capture(
        result,
        _expected(
            (
                _decl(),
                numpy,
                torch,
                _decl("transformers", line=2, source="Pipfile", display="transformers"),
            ),
            ("environment.yml:1: peft==",),
            projects={
                "pyproject.toml": _POETRY_FORMATS,
                "environment.yml": frozenset({"conda-lock.yml"}),
                "Pipfile": frozenset({"Pipfile.lock"}),
            },
            issues={
                "pyproject.toml": "invalid_structure",
                "environment.yml": "unparsed_requirement",
            },
        ),
        scanner,
        ["pyproject.toml", "requirements.txt", "deps/pins.txt", "environment.yml", "Pipfile"],
        candidates=["requirements.txt", "deps/pins.txt"],
    )


def test_t24_t41_lock_origins_manifest_roots_and_uncertain_barriers_are_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": _poetry("{version=false}"),
            "poetry.lock": '[[package]]\nname="torch"\nversion="2.5.1"\n',
            "broken/pyproject.toml": "project=false\n",
            "other/pyproject.toml": '[project]\ndependencies=["peft>=0.1"]\n',
            "other/uv.lock": '[[package]]\nname="peft"\nversion="0.13.0"\n',
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["peft>=0.1"]
    _assert_capture(
        result,
        _expected(
            (
                _decl(),
                _decl("peft", ">=0.1", line=2, source="other/pyproject.toml", display="peft"),
            ),
            projects={"pyproject.toml": _POETRY_FORMATS, "other/pyproject.toml": _PROJECT_FORMATS},
            barriers=("broken",),
            locks=(
                Lockfile("other/uv.lock", frozenset({"peft"})),
                Lockfile("poetry.lock", frozenset({"torch"})),
            ),
            issues={
                "pyproject.toml": "invalid_structure",
                "broken/pyproject.toml": "invalid_structure",
            },
        ),
        scanner,
        [
            "pyproject.toml",
            "broken/pyproject.toml",
            "other/pyproject.toml",
            "other/uv.lock",
            "poetry.lock",
        ],
        credit=frozenset({"torch", "peft"}),
    )
    assert result.qualified_lock_packages([("torch", "broken/run.py")]) == frozenset(
        {"torch", "peft"}
    )
    assert result._format_lock_origins(
        [("torch", "run.py"), ("peft", "other/run.py"), ("vllm", "broken/run.py")]
    ) == {
        Lockfile("poetry.lock", frozenset({"torch"})): {"torch"},
        Lockfile("other/uv.lock", frozenset({"peft"})): {"peft"},
    }


def test_t41_fresh_captures_recompute_without_mutating_prior_results_or_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    history = b'{"schema_version":"historical","note":"preserve bytes"}\n'
    (tmp_path / "old-audit.json").write_bytes(history)
    previous: list[tuple[Declarations, Declarations]] = []
    for value, expected in [
        ("{version=false}", _expected((_decl(),), issues={"pyproject.toml": "invalid_structure"})),
        ('{version="2.5.1"}', _expected((_decl(exact="2.5.1"),))),
        ("{}", _expected((_decl(),))),
        ("{Version=false}", _expected((_decl(),))),
        ("{version=0}", _expected((_decl(),), issues={"pyproject.toml": "invalid_structure"})),
    ]:
        _write(tmp_path, {"pyproject.toml": _poetry(value)})
        result, scanner, _ = _capture(tmp_path, monkeypatch)
        assert requirement_calls == []
        _assert_capture(result, expected, scanner, ["pyproject.toml"])
        assert (tmp_path / "old-audit.json").read_bytes() == history
        for captured, frozen in previous:
            assert captured == frozen
        previous.append((result, expected))
