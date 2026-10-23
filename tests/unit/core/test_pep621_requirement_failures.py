"""R07-C D-M-P: failed PEP 621 strings retain every captured sibling fact."""

import json
from dataclasses import fields
from pathlib import Path, PurePosixPath

import pytest
from packaging.requirements import Requirement

from reprollm.core import deps as deps_module
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

_PROJECT_FORMATS = frozenset({"uv.lock", "poetry.lock"})


class _Scanner(RepoScanner):
    def __init__(self, root: Path, *, reverse: bool = False) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.reads: list[tuple[str, int]] = []
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


def _decl(
    name: str,
    specifier: str | None,
    exact: str | None,
    line: int,
    source: str = "pyproject.toml",
    display: str | None = None,
) -> DependencyDeclaration:
    return DependencyDeclaration(name, display or name, specifier, exact, source, line)


def _expected(
    declarations: tuple[DependencyDeclaration, ...] = (),
    diagnostics: tuple[str, ...] = (),
    *,
    manifest: bool = True,
    projects: dict[str, frozenset[str]] | None = None,
    barriers: tuple[str, ...] = (),
    locks: tuple[Lockfile, ...] = (),
    issues: dict[str, str] | None = None,
    frontier: tuple[str, ...] = (),
) -> Declarations:
    return Declarations(
        list(declarations),
        list(diagnostics),
        list(locks),
        manifest,
        {"pyproject.toml": _PROJECT_FORMATS} if projects is None else projects,
        {PurePosixPath(path) for path in barriers},
        {} if issues is None else issues,
        frontier,
    )


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
    # Confirm all original capture facts before the newly accepted failure fact.
    for field in fields(Declarations):
        if field.name != "declaration_read_issues":
            assert getattr(result, field.name) == getattr(expected, field.name), field.name
    assert list(result._project_manifests.items()) == list(expected._project_manifests.items())
    assert list(result.declaration_read_issues.items()) == list(
        expected.declaration_read_issues.items()
    )


def _one_list(optional: bool, entries: list[str]) -> str:
    header, key = (
        ("project.optional-dependencies", "extras") if optional else ("project", "dependencies")
    )
    return f"[{header}]\n{key} = {json.dumps(entries)}\n"


@pytest.mark.parametrize("optional", [False, True])
@pytest.mark.parametrize(
    "value",
    [
        "torch==",
        "not a requirement",
        "torch==broken",
        "torch @",
        "torch==2 # note",
        "",
        " ",
        "\t",
        "\n",
    ],
)
def test_p01_p03_p04_actual_failed_string_records_only_file_fact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    optional: bool,
    value: str,
) -> None:
    _write(tmp_path, {"pyproject.toml": _one_list(optional, [value])})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == [value]
    assert graph.nodes == graph.closures == {}
    _assert_capture(
        result,
        _expected(
            diagnostics=(f"pyproject.toml:2: {value}",),
            issues={"pyproject.toml": "unparsed_requirement"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("bad_group", [0, 1, 2])
def test_p02_optional_groups_keep_order_and_unusual_group_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    bad_group: int,
) -> None:
    entries = ["numpy>=1", "torch==2.5.1", "peft>=0.1"]
    entries[bad_group] = "torch=="
    body = "[project.optional-dependencies]\n" + "".join(
        f"{json.dumps(group)} = [{json.dumps(value)}]\n"
        for group, value in zip(["z", "", "a invalid group"], entries, strict=True)
    )
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    all_expected = [
        _decl("numpy", ">=1", None, 2),
        # The existing source index falls back to the header for an empty group key.
        _decl("torch", "==2.5.1", "2.5.1", 1),
        _decl("peft", ">=0.1", None, 4),
    ]
    del all_expected[bad_group]
    assert requirement_calls == entries
    _assert_capture(
        result,
        _expected(
            tuple(all_expected),
            (f"pyproject.toml:{[2, 1, 4][bad_group]}: torch==",),
            issues={"pyproject.toml": "unparsed_requirement"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize(
    "body",
    [
        "[project]\n",
        "[project]\ndependencies=[]\n",
        "[project]\noptional-dependencies={}\n",
        "[project.optional-dependencies]\nempty=[]\n",
        '[project.optional-dependencies]\n""=[]\nz=[]\n',
    ],
)
def test_p05_empty_and_missing_are_not_parse_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], body: str
) -> None:
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    assert graph.nodes == graph.closures == {}
    _assert_capture(result, _expected(), scanner, ["pyproject.toml"])


@pytest.mark.parametrize("optional", [False, True])
@pytest.mark.parametrize(
    ("value", "specifier", "exact", "display"),
    [
        ("torch", None, None, "torch"),
        ("torch>=2", ">=2", None, "torch"),
        ("torch==2.5.1", "==2.5.1", "2.5.1", "torch"),
        ("PyTorch[cpu]==2.5.1+cpu", "==2.5.1+cpu", "2.5.1+cpu", "PyTorch"),
        ('torch==2.5.1; python_version < "0"', "==2.5.1", "2.5.1", "torch"),
        ('torch==2.5.1; os_name == "x # marker"', "==2.5.1", "2.5.1", "torch"),
        ("torch @ https://example.invalid/torch.whl#sha256=abc", None, None, "torch"),
        ("torch===2.5.1", "===2.5.1", None, "torch"),
        ("torch==2.*", "==2.*", None, "torch"),
        ("torch==2.5.1,!=2.0", "!=2.0,==2.5.1", None, "torch"),
    ],
)
def test_p06_successful_original_grammar_is_not_reparsed_or_reinterpreted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    optional: bool,
    value: str,
    specifier: str | None,
    exact: str | None,
    display: str,
) -> None:
    _write(tmp_path, {"pyproject.toml": _one_list(optional, [value])})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == [value]
    _assert_capture(
        result,
        _expected((_decl("torch", specifier, exact, 2, display=display),)),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("optional", [False, True])
@pytest.mark.parametrize("failure_position", [0, 1, 2])
def test_p07_partial_success_keeps_all_physical_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    optional: bool,
    failure_position: int,
) -> None:
    entries = ["torch>=2", "torch==2.5.1"]
    entries.insert(failure_position, "torch==")
    header = "project.optional-dependencies" if optional else "project"
    key = "extras" if optional else "dependencies"
    body = (
        f"[{header}]\n{key} = [\n"
        + "".join(f"  {json.dumps(value)},\n" for value in entries)
        + "]\n"
    )
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    loose_line = 4 if failure_position == 0 else 3
    exact_line = 5 if failure_position < 2 else 4
    assert requirement_calls == entries
    _assert_capture(
        result,
        _expected(
            (
                _decl("torch", ">=2", None, loose_line),
                _decl("torch", "==2.5.1", "2.5.1", exact_line),
            ),
            (f"pyproject.toml:{failure_position + 3}: torch==",),
            issues={"pyproject.toml": "unparsed_requirement"},
        ),
        scanner,
        ["pyproject.toml"],
    )


def test_p08_repeated_failures_keep_each_diagnostic_and_one_source_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    body = (
        '[project]\ndependencies = [\n"torch>=2",\n"torch==",\n"torch==",\n]\n'
        '[project.optional-dependencies]\nz = ["torch==", "numpy==1.26.4"]\n'
        'a = ["torch==", ""]\n'
    )
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == [
        "torch>=2",
        "torch==",
        "torch==",
        "torch==",
        "numpy==1.26.4",
        "torch==",
        "",
    ]
    _assert_capture(
        result,
        _expected(
            (_decl("torch", ">=2", None, 3), _decl("numpy", "==1.26.4", "1.26.4", 8)),
            (
                "pyproject.toml:4: torch==",
                "pyproject.toml:5: torch==",
                "pyproject.toml:8: torch==",
                "pyproject.toml:9: torch==",
                "pyproject.toml:9: ",
            ),
            issues={"pyproject.toml": "unparsed_requirement"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_p09_discovery_order_does_not_change_source_or_declaration_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], reverse: bool
) -> None:
    _write(
        tmp_path,
        {
            "z/pyproject.toml": _one_list(False, ["peft>=0.1", "torch=="]),
            "pyproject.toml": _one_list(False, ["numpy>=1"]),
            "a/pyproject.toml": _one_list(True, ["torch==", "torch>=2"]),
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch, reverse=reverse)
    assert requirement_calls == ["numpy>=1", "torch==", "torch>=2", "peft>=0.1", "torch=="]
    _assert_capture(
        result,
        _expected(
            (
                _decl("numpy", ">=1", None, 2),
                _decl("torch", ">=2", None, 2, "a/pyproject.toml"),
                _decl("peft", ">=0.1", None, 2, "z/pyproject.toml"),
            ),
            ("a/pyproject.toml:2: torch==", "z/pyproject.toml:2: torch=="),
            projects={
                "pyproject.toml": _PROJECT_FORMATS,
                "a/pyproject.toml": _PROJECT_FORMATS,
                "z/pyproject.toml": _PROJECT_FORMATS,
            },
            issues={
                "a/pyproject.toml": "unparsed_requirement",
                "z/pyproject.toml": "unparsed_requirement",
            },
        ),
        scanner,
        ["pyproject.toml", "a/pyproject.toml", "z/pyproject.toml"],
    )


@pytest.mark.parametrize("optional", [False, True])
@pytest.mark.parametrize("bad_member", ["false", "0", "[]", "{}"])
def test_p10_p12_nonstring_sibling_preserves_prior_structure_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    optional: bool,
    bad_member: str,
) -> None:
    header, key = (
        ("project.optional-dependencies", "x") if optional else ("project", "dependencies")
    )
    _write(
        tmp_path,
        {"pyproject.toml": f'[{header}]\n{key}=[{bad_member}, "torch==", "numpy==1.26.4"]\n'},
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["torch==", "numpy==1.26.4"]
    _assert_capture(
        result,
        _expected(
            (_decl("numpy", "==1.26.4", "1.26.4", 2),),
            ("pyproject.toml:2: torch==",),
            issues={"pyproject.toml": "invalid_structure"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("prefix", "suffix", "diagnostics", "barriers"),
    [
        ("tool=false\n", "", (), (".",)),
        ('tool="wrong"\n', "", ("pyproject.toml:0: invalid tool table",), (".",)),
        ("tool.poetry=false\n", "", (), (".",)),
        ("", "[project.optional-dependencies]\nbad=false\n", (), ()),
        ("", "[tool.poetry]\ndependencies=[]\n", (), ()),
    ],
)
def test_p10_other_structure_cause_survives_actual_failed_pep621_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    prefix: str,
    suffix: str,
    diagnostics: tuple[str, ...],
    barriers: tuple[str, ...],
) -> None:
    _write(
        tmp_path, {"pyproject.toml": prefix + _one_list(False, ["torch==", "torch>=2"]) + suffix}
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    line = 3 if prefix else 2
    assert requirement_calls == ["torch==", "torch>=2"]
    _assert_capture(
        result,
        _expected(
            (_decl("torch", ">=2", None, line),),
            diagnostics + (f"pyproject.toml:{line}: torch==",),
            barriers=barriers,
            issues={"pyproject.toml": "invalid_structure"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("failure", ["binary", "syntax"])
def test_p11_body_failures_return_before_any_requirement_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], failure: str
) -> None:
    _write(tmp_path, {"broken/pyproject.toml": "[project\n"})
    if failure == "binary":
        (tmp_path / "broken/pyproject.toml").write_bytes(b"\x00torch==")
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    diagnostic = (
        "unreadable"
        if failure == "binary"
        else "Expected ']' at the end of a table declaration (at line 1, column 9)"
    )
    _assert_capture(
        result,
        _expected(
            diagnostics=(f"broken/pyproject.toml:0: {diagnostic}",),
            manifest=False,
            projects={},
            barriers=("broken",),
            issues={
                "broken/pyproject.toml": "unreadable" if failure == "binary" else "invalid_syntax"
            },
        ),
        scanner,
        ["broken/pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("body", "manifest", "barriers"),
    [
        ('project="torch=="\n', False, (".",)),
        ('[project]\ndependencies="torch=="\n', True, ()),
        ('[project]\noptional-dependencies=["torch=="]\n', True, ()),
        ('[project.optional-dependencies]\na="torch=="\n', True, ()),
        ("[project]\ndependencies=[false, 0, [], {}]\n", True, ()),
    ],
)
def test_p12_untraversed_shapes_are_not_requirement_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    body: str,
    manifest: bool,
    barriers: tuple[str, ...],
) -> None:
    _write(tmp_path, {"pyproject.toml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            manifest=manifest,
            projects={"pyproject.toml": _PROJECT_FORMATS} if manifest else {},
            barriers=barriers,
            issues={"pyproject.toml": "invalid_structure"},
        ),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize(
    ("body", "formats"),
    [
        ('[build-system]\nrequires=["torch=="]\n', frozenset()),
        ('[dependency-groups]\na=["torch=="]\n', frozenset()),
        ('[tool.example]\ndependencies=["torch=="]\n', frozenset()),
        ('[tool.poetry.group.dev.dependencies]\ntorch="=="\n', frozenset({"poetry.lock"})),
        (
            '[project]\ndynamic=["dependencies"]\n[tool.example]\ndependencies=["torch=="]\n',
            _PROJECT_FORMATS,
        ),
    ],
)
def test_p13_unsupported_fields_and_excluded_candidates_add_no_parse_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    body: str,
    formats: frozenset[str],
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": body,
            ".venv/pyproject.toml": _one_list(False, ["torch=="]),
            "unread.toml": _one_list(False, ["torch=="]),
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(manifest=bool(formats), projects={"pyproject.toml": formats} if formats else {}),
        scanner,
        ["pyproject.toml"],
    )


@pytest.mark.parametrize("pep_failure", [False, True])
def test_p14_other_managers_and_embedded_pip_keep_their_separately_accepted_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], pep_failure: bool
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": _one_list(False, ["torch=="] if pep_failure else [])
            + '[tool.poetry.dependencies]\npeft=[{version="^0.1"}]\n',
            "environment.yml": (
                'dependencies:\n  - "torch=="\n  - pip: ["", "   ", "torch==", "numpy>=1"]\n'
            ),
            "Pipfile": "[packages]\ntransformers={version=false}\n",
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == (["torch=="] if pep_failure else []) + ["torch==", "numpy>=1"]
    _assert_capture(
        result,
        _expected(
            (
                _decl("peft", None, None, 4),
                _decl("torch", "(unsupported conda declaration)", None, 1, "environment.yml"),
                _decl("numpy", ">=1", None, 2, "environment.yml"),
                _decl("transformers", None, None, 2, "Pipfile"),
            ),
            (("pyproject.toml:2: torch==",) if pep_failure else ())
            + ("environment.yml:1: unsupported conda declaration", "environment.yml:2: torch=="),
            projects={
                "pyproject.toml": _PROJECT_FORMATS,
                "environment.yml": frozenset({"conda-lock.yml"}),
                "Pipfile": frozenset({"Pipfile.lock"}),
            },
            issues=(
                {
                    "pyproject.toml": "unparsed_requirement",
                    "environment.yml": "unparsed_requirement",
                }
                if pep_failure
                else {"environment.yml": "unparsed_requirement"}
            ),
        ),
        scanner,
        ["pyproject.toml", "environment.yml", "Pipfile"],
    )


@pytest.mark.parametrize("pep_failure", [False, True])
def test_p15_graph_comment_recovery_does_not_spread_to_pep621_strings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], pep_failure: bool
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": _one_list(False, ["torch==2.5.1 # pin"] if pep_failure else []),
            "requirements.txt": "torch==2.5.1 # pin\n-r deps/child.txt\n",
            "deps/child.txt": "numpy==1.26.4\n",
            "z/requirements.txt": "peft==\n--index-url https://example.invalid/simple\n",
        },
    )
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    torch = _decl("torch", "==2.5.1", "2.5.1", 1, "requirements.txt")
    numpy = _decl("numpy", "==1.26.4", "1.26.4", 1, "deps/child.txt")
    assert requirement_calls == (["torch==2.5.1 # pin"] if pep_failure else []) + [
        "torch==2.5.1 # pin",
        "torch==2.5.1",
        "torch==2.5.1",
        "numpy==1.26.4",
        "peft==",
    ]
    assert graph.nodes == {
        "requirements.txt": _RequirementFile(
            True, (torch, _RequirementInclude(2, "deps/child.txt"))
        ),
        "deps/child.txt": _RequirementFile(True, (numpy,)),
        "z/requirements.txt": _RequirementFile(
            True,
            (
                "z/requirements.txt:1: peft==",
                "z/requirements.txt:2: --index-url https://example.invalid/simple",
            ),
        ),
    }
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            True, frozenset({"requirements.txt", "deps/child.txt"}), frozenset({torch, numpy})
        ),
        "z/requirements.txt": _RequirementsClosure(False, frozenset({"z/requirements.txt"})),
    }
    _assert_capture(
        result,
        _expected(
            (torch, numpy),
            (("pyproject.toml:2: torch==2.5.1 # pin",) if pep_failure else ())
            + (
                "z/requirements.txt:1: peft==",
                "z/requirements.txt:2: --index-url https://example.invalid/simple",
            ),
            locks=(Lockfile("requirements.txt", frozenset({"torch", "numpy"})),),
            issues={"pyproject.toml": "unparsed_requirement"} if pep_failure else {},
        ),
        scanner,
        ["pyproject.toml", "requirements.txt", "deps/child.txt", "z/requirements.txt"],
        candidates=["requirements.txt", "deps/child.txt", "z/requirements.txt"],
        credit=frozenset({"torch", "numpy"}),
    )


@pytest.mark.parametrize("pep_failure", [False, True])
def test_p15_depth_frontier_remains_separate_from_pep621_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], pep_failure: bool
) -> None:
    paths = ["requirements.txt", *[f"deps/{index}.txt" for index in range(1, 12)]]
    bodies = {paths[0]: "torch>=2\n-r deps/1.txt\n"}
    bodies.update({paths[index]: f"-r {index + 1}.txt\n" for index in range(1, 11)})
    bodies[paths[11]] = "torch==2.5.1\n"
    bodies["pyproject.toml"] = _one_list(False, ["torch=="] if pep_failure else [])
    _write(tmp_path, bodies)
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    torch = _decl("torch", ">=2", None, 1, "requirements.txt")
    assert requirement_calls == (["torch=="] if pep_failure else []) + ["torch>=2"]
    assert list(graph.nodes) == paths[:11]
    assert graph.nodes[paths[0]] == _RequirementFile(
        True, (torch, _RequirementInclude(2, paths[1]))
    )
    assert all(
        graph.nodes[paths[index]]
        == _RequirementFile(True, (_RequirementInclude(1, paths[index + 1]),))
        for index in range(1, 11)
    )
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(False, frozenset(paths[:11]), frozenset({torch}))
    }
    _assert_capture(
        result,
        _expected(
            (torch,),
            (("pyproject.toml:2: torch==",) if pep_failure else ())
            + ("deps/10.txt:1: include depth limit",)
            + tuple(f"deps/{index}.txt:1: include incomplete" for index in range(9, 0, -1))
            + ("requirements.txt:2: include incomplete",),
            issues={"pyproject.toml": "unparsed_requirement"} if pep_failure else {},
            frontier=("deps/11.txt",),
        ),
        scanner,
        ["pyproject.toml", *paths[:11]],
        candidates=paths[:11],
    )


def test_p16_new_capture_drops_old_cause_without_changing_prior_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    states = [
        (
            ["torch=="],
            _expected(
                diagnostics=("pyproject.toml:2: torch==",),
                issues={"pyproject.toml": "unparsed_requirement"},
            ),
        ),
        (
            ["torch=="],
            _expected(
                diagnostics=("pyproject.toml:2: torch==",),
                issues={"pyproject.toml": "unparsed_requirement"},
            ),
        ),
        (["torch==2.5.1"], _expected((_decl("torch", "==2.5.1", "2.5.1", 2),))),
        (["torch>=2"], _expected((_decl("torch", ">=2", None, 2),))),
        ([], _expected()),
    ]
    prior: list[tuple[Declarations, Declarations]] = []
    for values, expected in states:
        requirement_calls.clear()
        _write(tmp_path, {"pyproject.toml": _one_list(False, values)})
        result, scanner, _ = _capture(tmp_path, monkeypatch)
        assert requirement_calls == values
        _assert_capture(result, expected, scanner, ["pyproject.toml"])
        for captured, original in prior:
            assert captured == original
        prior.append((result, expected))


@pytest.mark.parametrize("lock_name", ["uv.lock", "poetry.lock"])
@pytest.mark.parametrize("pep_failure", [False, True])
def test_p17_same_directory_lock_credit_and_origin_boundaries_are_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    lock_name: str,
    pep_failure: bool,
) -> None:
    entries = ["numpy>=1", "torch=="] if pep_failure else ["numpy>=1"]
    _write(
        tmp_path,
        {
            "pkg/pyproject.toml": _one_list(False, entries),
            f"pkg/{lock_name}": (
                '[[package]]\nname="torch"\n[[package]]\nname="numpy"\n[[package]]\nname="peft"\n'
            ),
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == entries
    assert result.qualified_lock_packages([("torch", "pkg/src/a.py")]) == frozenset(
        {"numpy", "torch"}
    )
    assert result.qualified_lock_packages([("torch", "pkg/src/../a.py")]) == frozenset(
        {"numpy", "torch"}
    )
    for origin in ["../pkg/a.py", "/pkg/a.py", "C:/pkg/a.py", "outside/a.py", "pkg/../../a.py"]:
        assert result.qualified_lock_packages([("torch", origin)]) == frozenset({"numpy"})
    _assert_capture(
        result,
        _expected(
            (_decl("numpy", ">=1", None, 2, "pkg/pyproject.toml"),),
            ("pkg/pyproject.toml:2: torch==",) if pep_failure else (),
            projects={"pkg/pyproject.toml": _PROJECT_FORMATS},
            locks=(Lockfile(f"pkg/{lock_name}", frozenset({"torch", "numpy", "peft"})),),
            issues={"pkg/pyproject.toml": "unparsed_requirement"} if pep_failure else {},
        ),
        scanner,
        ["pkg/pyproject.toml", f"pkg/{lock_name}"],
        credit=frozenset({"numpy"}),
    )


@pytest.mark.parametrize("outside", [False, True])
def test_p17_safe_source_aliases_do_not_invent_physical_issue_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], outside: bool
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "outside.toml" if outside else root / "storage/manifest.toml"
    target.parent.mkdir(exist_ok=True)
    target.write_text(_one_list(False, ["torch=="]), encoding="utf-8")
    try:
        (root / "pyproject.toml").symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")
    result, scanner, _ = _capture(root, monkeypatch)
    assert requirement_calls == ([] if outside else ["torch=="])
    expected = (
        _expected(
            diagnostics=("pyproject.toml:0: unreadable",),
            manifest=False,
            projects={},
            barriers=(".",),
            issues={"pyproject.toml": "unreadable"},
        )
        if outside
        else _expected(
            diagnostics=("pyproject.toml:2: torch==",),
            issues={"pyproject.toml": "unparsed_requirement"},
        )
    )
    _assert_capture(result, expected, scanner, ["pyproject.toml"])


def test_p17_legacy_manual_defaults_are_fresh_and_positional_compatible() -> None:
    old = Declarations([], [], [], False, {}, set())
    other = Declarations()
    assert old == other == Declarations()
    assert old.declaration_read_issues is not other.declaration_read_issues
    assert old.unexpanded_requirement_targets == ()
    assert old.qualified_lock_packages([]) == frozenset()
    assert old.unverified_lock_paths([]) == {}
