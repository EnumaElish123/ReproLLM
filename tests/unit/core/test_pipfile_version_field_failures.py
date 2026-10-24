"""R07-C D-M-PF: typed Pipfile entry gaps preserve the captured dependency view."""

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

_PIPFILE_FORMATS = frozenset({"Pipfile.lock"})


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


@pytest.fixture
def helper_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[object, bool, tuple[str | None, str | None]]]:
    calls: list[tuple[object, bool, tuple[str | None, str | None]]] = []
    original = deps_module._dependency_version_field

    def recorded(value: object, *, allow_bare: bool) -> tuple[str | None, str | None]:
        answer = original(value, allow_bare=allow_bare)
        calls.append((value, allow_bare, answer))
        return answer

    monkeypatch.setattr(deps_module, "_dependency_version_field", recorded)
    return calls


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))


def _pipfile(value: str, section: str = "packages") -> str:
    return f"[{section}]\nPyTorch={value}\n"


def _decl(
    name: str = "torch",
    specifier: str | None = None,
    exact: str | None = None,
    line: int = 2,
    source: str = "Pipfile",
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
        {"Pipfile": _PIPFILE_FORMATS} if projects is None else projects,
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
    # Every pre-existing capture field must survive before checking the new fact.
    for field in fields(Declarations):
        if field.name != "declaration_read_issues":
            assert getattr(result, field.name) == getattr(expected, field.name), field.name
    assert list(result._project_manifests.items()) == list(expected._project_manifests.items())
    assert list(result.declaration_read_issues.items()) == list(
        expected.declaration_read_issues.items()
    )


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
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
def test_a01_a06_real_nonstring_version_retains_named_entry_without_new_barrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    helper_calls: list[tuple[object, bool, tuple[str | None, str | None]]],
    section: str,
    literal: str,
    decoded_type: type,
) -> None:
    body = _pipfile(f"{{version={literal}}}", section)
    decoded = tomllib.loads(body)[section]["PyTorch"]["version"]
    assert type(decoded) is decoded_type
    if literal == "nan":
        assert math.isnan(decoded)
    if literal in ("inf", "+inf", "-inf"):
        assert math.isinf(decoded)
    _write(tmp_path, {"Pipfile": body})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    assert graph.nodes == graph.closures == {}
    assert len(helper_calls) == 1
    value, bare, answer = helper_calls[0]
    assert isinstance(value, dict) and type(value["version"]) is decoded_type
    assert bare is False and answer == (None, None)
    _assert_capture(
        result,
        _expected((_decl(),), issues={"Pipfile": "invalid_structure"}),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize(
    ("value", "specifier", "exact"),
    [
        ('""', None, None),
        ('" \\t "', None, None),
        ('"2.5.1"', "2.5.1", None),
        ('" 2.5.1 "', "2.5.1", None),
        ('"==2.5.1"', None, "2.5.1"),
        ('"==1!2.5.1"', None, "1!2.5.1"),
        ('"==2.5.1rc1"', None, "2.5.1rc1"),
        ('"==2.5.1.post1"', None, "2.5.1.post1"),
        ('"==2.5.1.dev1"', None, "2.5.1.dev1"),
        ('"==2.5.1+cpu"', None, "2.5.1+cpu"),
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
def test_a08_a10_every_string_keeps_pipfile_exact_contract_without_a_type_issue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    helper_calls: list[tuple[object, bool, tuple[str | None, str | None]]],
    section: str,
    value: str,
    specifier: str | None,
    exact: str | None,
) -> None:
    _write(tmp_path, {"Pipfile": _pipfile(f"{{version={value}}}", section)})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    assert helper_calls == [
        ({"version": tomllib.loads(f"v={value}")["v"]}, False, (specifier, exact))
    ]
    _assert_capture(
        result, _expected((_decl(specifier=specifier, exact=exact),)), scanner, ["Pipfile"]
    )


@pytest.mark.parametrize(
    "value",
    [
        "{}",
        '{index="private-source"}',
        "{optional=true}",
        '{extras=["cpu"], markers="python_version > 0"}',
        "{Version=false}",
        "{VERSION=0}",
        "{unknown={version=false}}",
        "{versioned=false}",
    ],
)
def test_a07_a16_missing_exact_version_key_is_not_inferred_from_helper_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], value: str
) -> None:
    _write(tmp_path, {"Pipfile": _pipfile(value)})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(result, _expected((_decl(),)), scanner, ["Pipfile"])


@pytest.mark.parametrize("key", ['"version"', "'version'", "version"])
def test_a16_decoded_raw_version_key_is_checked_without_extra_property_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str
) -> None:
    _write(tmp_path, {"Pipfile": _pipfile(f'{{Version="==2.5.1", unknown=true, {key}=false}}')})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result,
        _expected((_decl(),), issues={"Pipfile": "invalid_structure"}),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize(
    ("value", "specifier", "exact"),
    [
        ('"2.5.1"', "2.5.1", None),
        ('"==2.5.1"', None, "2.5.1"),
        ('"^2"', "^2", None),
        ("false", None, None),
        ("0", None, None),
        ("2.5", None, None),
        ("1979-05-27", None, None),
        ("[]", None, None),
        ('["2.5.1"]', None, None),
        ('[{version="==2.5.1"}, {version=false}]', None, None),
        ("[{version={nested=false}}]", None, None),
    ],
)
def test_a11_a12_whole_nonmapping_values_and_arrays_are_not_descended_into(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    value: str,
    specifier: str | None,
    exact: str | None,
) -> None:
    _write(tmp_path, {"Pipfile": _pipfile(value, section)})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result, _expected((_decl(specifier=specifier, exact=exact),)), scanner, ["Pipfile"]
    )


@pytest.mark.parametrize("transport", ["url", "git", "path", "file", "hg", "svn", "bzr"])
@pytest.mark.parametrize(
    ("version", "specifier", "issue"),
    [("", None, False), (',version="==2.5.1"', "==2.5.1", False), (",version=0", None, True)],
)
def test_a13_a15_transport_does_not_grant_exact_or_exempt_nonstring_version(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transport: str,
    version: str,
    specifier: str | None,
    issue: bool,
) -> None:
    _write(tmp_path, {"Pipfile": _pipfile(f"{{{transport}=false{version}}}")})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result,
        _expected(
            (_decl(specifier=specifier),),
            issues={"Pipfile": "invalid_structure"} if issue else {},
        ),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize("reverse_headers", [False, True])
def test_a17_a18_sections_retain_traversal_order_duplicate_names_and_shared_line_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reverse_headers: bool
) -> None:
    packages = '[packages]\nPyTorch={version=false}\npeft="==0.13.0"\n'
    dev = '[dev-packages]\nPyTorch="==2.5.1"\nrequests={version=[]}\n'
    _write(tmp_path, {"Pipfile": dev + packages if reverse_headers else packages + dev})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    # The shared bucket consumes duplicate physical lines in caller order, despite reversed headers.
    _assert_capture(
        result,
        _expected(
            (
                _decl(),
                _decl("peft", None, "0.13.0", 6 if reverse_headers else 3, display="peft"),
                _decl(exact="2.5.1", line=5),
                _decl("requests", line=3 if reverse_headers else 6, display="requests"),
            ),
            issues={"Pipfile": "invalid_structure"},
        ),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize("wrong", ["packages", "dev-packages"])
def test_a19_existing_section_precheck_barrier_and_valid_sibling_survive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, wrong: str
) -> None:
    good = "dev-packages" if wrong == "packages" else "packages"
    _write(
        tmp_path, {"Pipfile": f'{wrong}=false\n[{good}]\nPyTorch={{version=0}}\npeft="==0.13.0"\n'}
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result,
        _expected(
            (_decl(line=3), _decl("peft", None, "0.13.0", 4, display="peft")),
            barriers=(".",),
            issues={"Pipfile": "invalid_structure"},
        ),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize("reason", ["unreadable", "invalid_syntax", "unparsed_requirement"])
def test_a28_in_loop_setdefault_preserves_an_existing_manual_cause(
    tmp_path: Path, reason: str
) -> None:
    _write(tmp_path, {"Pipfile": _pipfile("{version=false}")})
    scanner = _Scanner(tmp_path)
    result = Declarations(declaration_read_issues={"Pipfile": reason})
    deps_module._parse_pipfile("Pipfile", scanner, result)
    assert result == _expected((_decl(),), issues={"Pipfile": reason}, manifest=False)
    assert scanner.reads == [("Pipfile", 512 * 1024)]
    assert scanner.candidates == []


@pytest.mark.parametrize("section", ["default", "develop"])
def test_a22_a24_entry_issue_does_not_block_qualified_parent_lock_for_child_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, section: str
) -> None:
    _write(
        tmp_path,
        {
            "Pipfile": "[packages]\nrequests={version=0}\n",
            "Pipfile.lock": f'{{"{section}": {{"torch": {{"version":"==2.5.1"}}}}}}\n',
            "child/run.py": "import torch\n",
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    lock = Lockfile("Pipfile.lock", frozenset({"torch"}))
    _assert_capture(
        result,
        _expected(
            (_decl("requests", display="requests"),),
            locks=(lock,),
            issues={"Pipfile": "invalid_structure"},
        ),
        scanner,
        ["Pipfile", "Pipfile.lock"],
    )
    assert result.qualified_lock_packages([("torch", "child/run.py")]) == frozenset({"torch"})
    assert result._format_lock_origins([("torch", "child/run.py")]) == {lock: {"requests", "torch"}}


@pytest.mark.parametrize("reverse", [False, True])
def test_a17_a37_multiple_sources_keep_deterministic_order_and_distinct_logical_causes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reverse: bool
) -> None:
    _write(
        tmp_path,
        {
            "z/Pipfile": _pipfile("{version=[]}", "dev-packages"),
            "Pipfile": '[packages]\nrequests={version=0}\nPyTorch="==2.5.1"\n',
            "a/Pipfile": _pipfile("{version=false}"),
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch, reverse=reverse)
    _assert_capture(
        result,
        _expected(
            (
                _decl("requests", display="requests"),
                _decl(exact="2.5.1", line=3),
                _decl(source="a/Pipfile"),
                _decl(source="z/Pipfile"),
            ),
            projects={
                "Pipfile": _PIPFILE_FORMATS,
                "a/Pipfile": _PIPFILE_FORMATS,
                "z/Pipfile": _PIPFILE_FORMATS,
            },
            issues={
                "Pipfile": "invalid_structure",
                "a/Pipfile": "invalid_structure",
                "z/Pipfile": "invalid_structure",
            },
        ),
        scanner,
        ["Pipfile", "a/Pipfile", "z/Pipfile"],
    )


@pytest.mark.parametrize(
    ("body", "qualified"),
    [
        ("", False),
        ("[packages]\n", True),
        ("[dev-packages]\n", True),
        ("[docs]\nPyTorch={version=false}\n", False),
        ("[tests]\nPyTorch={version=false}\n", False),
        ("[packages]\n[custom]\nPyTorch={version=false}\n", True),
    ],
)
def test_a30_a31_empty_sections_and_unvisited_categories_do_not_create_entry_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, qualified: bool
) -> None:
    _write(tmp_path, {"Pipfile": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result,
        _expected(projects={"Pipfile": _PIPFILE_FORMATS} if qualified else {}),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize(
    ("body", "line"),
    [
        ("# heading\n\n[packages]\nPyTorch={version=false}\n", 4),
        ("# heading\n[packages.PyTorch]\nversion=false\n", 1),
        ("# heading\n[dev-packages.PyTorch]\nversion=false\n", 1),
        ("packages={PyTorch={version=false}}\n", 1),
    ],
)
def test_a32_expanded_inline_and_header_fallback_locations_are_not_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, line: int
) -> None:
    _write(tmp_path, {"Pipfile": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result,
        _expected((_decl(line=line),), issues={"Pipfile": "invalid_structure"}),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.parametrize("failure", ["binary", "oversize", "syntax"])
@pytest.mark.security
def test_a29_read_decode_failures_return_before_any_entry_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    body = "[packages broken\nPyTorch={version=false}\n"
    _write(tmp_path, {"Pipfile": body})
    if failure == "syntax":

        def decoder(text: str) -> dict[str, object]:
            assert text == body
            raise tomllib.TOMLDecodeError("synthetic TOML failure")

        monkeypatch.setattr(deps_module.tomllib, "loads", decoder)
        issue = "invalid_syntax"
        diagnostic = "synthetic TOML failure"
    else:
        (tmp_path / "Pipfile").write_bytes(
            b"\x00version=false" if failure == "binary" else b" " * (512 * 1024 + 1)
        )
        issue = "unreadable"
        diagnostic = "unreadable"

    def helper(value: object, *, allow_bare: bool) -> tuple[str | None, str | None]:
        raise AssertionError("A failed body must not reach an entry helper")

    monkeypatch.setattr(deps_module, "_dependency_version_field", helper)
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(
        result,
        _expected(
            diagnostics=(f"Pipfile:0: {diagnostic}",),
            projects={},
            barriers=(".",),
            issues={"Pipfile": issue},
        ),
        scanner,
        ["Pipfile"],
    )


@pytest.mark.security
@pytest.mark.parametrize("outside", [False, True])
def test_a29_a43_real_alias_retains_logical_source_and_refuses_external_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outside: bool
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "outside.txt" if outside else root / "storage/body.txt"
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(_pipfile("{version=false}").encode())
    try:
        (root / "Pipfile").symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"real symlink unavailable: {type(exc).__name__}")
    result, scanner, _ = _capture(root, monkeypatch)
    assert scanner.physical_reads == ([] if outside else [target.resolve()])
    _assert_capture(
        result,
        _expected(
            () if outside else (_decl(),),
            ("Pipfile:0: unreadable",) if outside else (),
            projects={} if outside else {"Pipfile": _PIPFILE_FORMATS},
            barriers=(".",) if outside else (),
            issues={"Pipfile": "unreadable" if outside else "invalid_structure"},
        ),
        scanner,
        ["Pipfile"],
    )


def test_a38_other_manager_policies_and_shared_helper_flags_are_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    helper_calls: list[tuple[object, bool, tuple[str | None, str | None]]],
) -> None:
    _write(
        tmp_path,
        {
            "Pipfile": '[packages]\nPyTorch="2.5.1"\nrequests={version=false}\n',
            "pyproject.toml": '[tool.poetry.dependencies]\npeft="0.13.0"\nnumpy={version=false}\n',
            "environment.yml": 'dependencies: [{pip: ["openai=="]}]\n',
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["openai=="]
    assert helper_calls == [
        ("0.13.0", True, (None, "0.13.0")),
        ({"version": False}, True, (None, None)),
        ("2.5.1", False, ("2.5.1", None)),
        ({"version": False}, False, (None, None)),
    ]
    _assert_capture(
        result,
        _expected(
            (
                _decl("peft", None, "0.13.0", 2, "pyproject.toml", "peft"),
                _decl("numpy", line=3, source="pyproject.toml", display="numpy"),
                _decl(specifier="2.5.1"),
                _decl("requests", line=3, display="requests"),
            ),
            ("environment.yml:1: openai==",),
            projects={
                "pyproject.toml": frozenset({"poetry.lock"}),
                "environment.yml": frozenset({"conda-lock.yml"}),
                "Pipfile": _PIPFILE_FORMATS,
            },
            issues={
                "pyproject.toml": "invalid_structure",
                "environment.yml": "unparsed_requirement",
                "Pipfile": "invalid_structure",
            },
        ),
        scanner,
        ["pyproject.toml", "environment.yml", "Pipfile"],
    )


def test_a21_a39_complete_requirements_graph_and_exact_siblings_keep_all_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {
            "Pipfile": '[packages]\nPyTorch={version=false}\npeft="==0.13.0"\n',
            "requirements.txt": "-r deps/pins.txt\ntorch>=2\n",
            "deps/pins.txt": "numpy==1.26.4 # exact comment\n",
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
            (numpy, torch, _decl(), _decl("peft", None, "0.13.0", 3, display="peft")),
            issues={"Pipfile": "invalid_structure"},
        ),
        scanner,
        ["requirements.txt", "deps/pins.txt", "Pipfile"],
        candidates=["requirements.txt", "deps/pins.txt"],
    )


def test_a43_fresh_captures_do_not_reinterpret_prior_records_or_historical_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    historical = b'{"schema_version":"historical","note":"preserve bytes"}\n'
    (tmp_path / "old-audit.json").write_bytes(historical)
    previous: list[tuple[Declarations, Declarations]] = []
    for value, expected in [
        ("{version=false}", _expected((_decl(),), issues={"Pipfile": "invalid_structure"})),
        ('{version="2.5.1"}', _expected((_decl(specifier="2.5.1"),))),
        ('{version="==2.5.1"}', _expected((_decl(exact="2.5.1"),))),
        ("{}", _expected((_decl(),))),
        ("{Version=false}", _expected((_decl(),))),
        ("{version=0}", _expected((_decl(),), issues={"Pipfile": "invalid_structure"})),
    ]:
        _write(tmp_path, {"Pipfile": _pipfile(value)})
        result, scanner, _ = _capture(tmp_path, monkeypatch)
        _assert_capture(result, expected, scanner, ["Pipfile"])
        assert (tmp_path / "old-audit.json").read_bytes() == historical
        for captured, frozen in previous:
            assert captured == frozen
        previous.append((result, expected))


def test_a43_legacy_manual_defaults_remain_empty_and_independent() -> None:
    old = Declarations([], [], [], False, {}, set())
    other = Declarations()
    assert old == other == Declarations()
    assert old.declaration_read_issues is not other.declaration_read_issues
    old.declarations.append(_decl())
    assert old.declaration_read_issues == {}
    assert other.declarations == []
    assert old.unexpanded_requirement_targets == ()


def test_a31_a45_filtered_and_unrecognized_sources_do_not_expand_pipfile_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = _pipfile("{version=false}")
    _write(
        tmp_path,
        {
            ".venv/Pipfile": body,
            ".reprollm/runs/old/Pipfile": body,
            "elsewhere.toml": body,
            "Pipfile.txt": body,
            "Pipfile": "[packages]\n",
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(result, _expected(), scanner, ["Pipfile"])
