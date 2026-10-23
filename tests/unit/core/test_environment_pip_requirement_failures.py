"""R07-C D-M-E: one failed embedded-pip call preserves all other capture facts."""

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

_CONDA_FORMATS = frozenset({"conda-lock.yml"})


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
    line: int = 1,
    source: str = "environment.yml",
    display: str | None = None,
) -> DependencyDeclaration:
    return DependencyDeclaration(name, display or name, specifier, exact, source, line)


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
        {"environment.yml": _CONDA_FORMATS} if projects is None else projects,
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
    # A failed new assertion must not hide a change in the original captured facts.
    for field in fields(Declarations):
        if field.name != "declaration_read_issues":
            assert getattr(result, field.name) == getattr(expected, field.name), field.name
    assert list(result._project_manifests.items()) == list(expected._project_manifests.items())
    assert list(result.declaration_read_issues.items()) == list(
        expected.declaration_read_issues.items()
    )


def _pip(entries: list[str]) -> str:
    return f"dependencies: [{{pip: {json.dumps(entries)}}}]\n"


@pytest.mark.parametrize(
    "path", ["environment.yml", "environment.yaml", "a/environment.yml", "z/environment.yaml"]
)
@pytest.mark.parametrize("value", ["torch==", "not a requirement", "torch==broken"])
def test_a01_a02_failed_existing_call_keeps_logical_source_and_all_other_facts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    path: str,
    value: str,
) -> None:
    _write(tmp_path, {path: _pip([value])})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == [value]
    assert graph.nodes == graph.closures == {}
    _assert_capture(
        result,
        _expected(
            diagnostics=(f"{path}:1: {value}",),
            projects={path: _CONDA_FORMATS},
            issues={path: "unparsed_requirement"},
        ),
        scanner,
        [path],
    )


@pytest.mark.parametrize("entries", [[], [""], [" "], ["\t"], ["\n"], ["\u2003"], ["", " \t\n"]])
def test_a03_blank_embedded_strings_are_skipped_before_requirement_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    entries: list[str],
) -> None:
    _write(tmp_path, {"environment.yml": _pip(entries)})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    assert graph.nodes == graph.closures == {}
    _assert_capture(result, _expected(), scanner, ["environment.yml"])


@pytest.mark.parametrize("ordinal", [1, 2, 3])
def test_a04_a05_strip_once_and_keep_outer_dependency_ordinal_not_yaml_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], ordinal: int
) -> None:
    body = "# physical line deliberately differs\n\ndependencies:\n"
    body += "  - {}\n" * (ordinal - 1)
    body += '  - pip: ["  torch >= 2  ", " \\t torch== \\n", "numpy==1.26.4"]\n'
    _write(tmp_path, {"environment.yml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["torch >= 2", "torch==", "numpy==1.26.4"]
    _assert_capture(
        result,
        _expected(
            (_decl("torch", ">=2", None, ordinal), _decl("numpy", "==1.26.4", "1.26.4", ordinal)),
            (f"environment.yml:{ordinal}: torch==",),
            issues={"environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ["environment.yml"],
    )


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
        ("torch==1!2.5.1", "==1!2.5.1", "1!2.5.1", "torch"),
        ("torch==2.5.1rc1", "==2.5.1rc1", "2.5.1rc1", "torch"),
        ("torch==2.5.1.post1", "==2.5.1.post1", "2.5.1.post1", "torch"),
        ("torch==2.5.1.dev1", "==2.5.1.dev1", "2.5.1.dev1", "torch"),
    ],
)
def test_a06_successful_grammar_and_exact_contract_are_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    value: str,
    specifier: str | None,
    exact: str | None,
    display: str,
) -> None:
    _write(tmp_path, {"environment.yml": _pip([value])})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == [value]
    _assert_capture(
        result,
        _expected((_decl("torch", specifier, exact, display=display),)),
        scanner,
        ["environment.yml"],
    )


@pytest.mark.parametrize("position", [0, 1, 2])
def test_a07_partial_exact_and_loose_siblings_keep_order_and_conda_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], position: int
) -> None:
    entries = ["torch>=2", "numpy==1.26.4"]
    entries.insert(position, "torch==")
    body = "dependencies:\n  - pytorch=2.5.1=cuda12.1\n  - pip: " + json.dumps(entries) + "\n"
    body += '  - pip: ["peft>=0.1", "torch==2.5.1"]\n'
    _write(tmp_path, {"environment.yml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == entries + ["peft>=0.1", "torch==2.5.1"]
    _assert_capture(
        result,
        _expected(
            (
                _decl("torch", "=2.5.1=cuda12.1", "2.5.1", 1, display="pytorch"),
                _decl("torch", ">=2", None, 2),
                _decl("numpy", "==1.26.4", "1.26.4", 2),
                _decl("peft", ">=0.1", None, 3),
                _decl("torch", "==2.5.1", "2.5.1", 3),
            ),
            ("environment.yml:2: torch==",),
            issues={"environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ["environment.yml"],
    )


def test_a08_repeated_failures_keep_each_original_diagnostic_and_one_file_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {"environment.yml": 'dependencies: [{pip: ["torch==", "torch=="]}, {pip: ["torch=="]}]\n'},
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["torch=="] * 3
    _assert_capture(
        result,
        _expected(
            diagnostics=("environment.yml:1: torch==",) * 2 + ("environment.yml:2: torch==",),
            issues={"environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ["environment.yml"],
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_a09_all_logical_sources_keep_fixed_parser_order_with_existing_pep621_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], reverse: bool
) -> None:
    _write(
        tmp_path,
        {
            "z/environment.yml": _pip(["torch==", "peft>=0.1"]),
            "environment.yaml": _pip(["numpy>=1", "torch=="]),
            "a/environment.yml": _pip(["torch==", "torch>=2"]),
            "pyproject.toml": '[project]\ndependencies=["numpy=="]\n',
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch, reverse=reverse)
    assert requirement_calls == [
        "numpy==",
        "numpy>=1",
        "torch==",
        "torch==",
        "torch>=2",
        "torch==",
        "peft>=0.1",
    ]
    _assert_capture(
        result,
        _expected(
            (
                _decl("numpy", ">=1", None, source="environment.yaml"),
                _decl("torch", ">=2", None, source="a/environment.yml"),
                _decl("peft", ">=0.1", None, source="z/environment.yml"),
            ),
            (
                "pyproject.toml:2: numpy==",
                "environment.yaml:1: torch==",
                "a/environment.yml:1: torch==",
                "z/environment.yml:1: torch==",
            ),
            projects={
                "pyproject.toml": frozenset({"uv.lock", "poetry.lock"}),
                "environment.yaml": _CONDA_FORMATS,
                "a/environment.yml": _CONDA_FORMATS,
                "z/environment.yml": _CONDA_FORMATS,
            },
            issues={
                "pyproject.toml": "unparsed_requirement",
                "environment.yaml": "unparsed_requirement",
                "a/environment.yml": "unparsed_requirement",
                "z/environment.yml": "unparsed_requirement",
            },
        ),
        scanner,
        ["pyproject.toml", "environment.yaml", "a/environment.yml", "z/environment.yml"],
    )


@pytest.mark.parametrize("bad_member", ["null", "false", "0", "[]", "{}"])
@pytest.mark.parametrize("member_after", [False, True])
def test_a10_whole_document_structure_cause_wins_even_when_error_appears_after_failed_string(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    bad_member: str,
    member_after: bool,
) -> None:
    pip_members = f'"torch==", {bad_member}, "numpy==1.26.4"'
    if member_after:
        body = f'dependencies: [{{pip: ["torch==", "numpy==1.26.4"]}}, {bad_member}]\n'
        # An empty mapping is an existing valid unknown-installer member.
        issue = "unparsed_requirement" if bad_member == "{}" else "invalid_structure"
    else:
        body = f"dependencies: [{{pip: [{pip_members}]}}]\n"
        issue = "invalid_structure"
    _write(tmp_path, {"environment.yml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["torch==", "numpy==1.26.4"]
    _assert_capture(
        result,
        _expected(
            (_decl("numpy", "==1.26.4", "1.26.4"),),
            ("environment.yml:1: torch==",),
            issues={"environment.yml": issue},
        ),
        scanner,
        ["environment.yml"],
    )


@pytest.mark.parametrize("failure", ["binary", "syntax"])
def test_a11_existing_body_failures_return_before_requirement_parse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], failure: str
) -> None:
    _write(tmp_path, {"broken/environment.yml": "dependencies: [\n"})
    if failure == "binary":
        (tmp_path / "broken/environment.yml").write_bytes(b"\x00torch==")
    else:
        import yaml

        def decoder(text: str) -> object:
            assert text == "dependencies: [\n"
            raise yaml.YAMLError("synthetic decoder failure")

        monkeypatch.setattr(deps_module.yaml, "safe_load", decoder)
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            diagnostics=(
                "broken/environment.yml:0: "
                + ("unreadable" if failure == "binary" else "synthetic decoder failure"),
            ),
            projects={},
            barriers=("broken",),
            issues={
                "broken/environment.yml": "unreadable" if failure == "binary" else "invalid_syntax"
            },
        ),
        scanner,
        ["broken/environment.yml"],
    )


@pytest.mark.parametrize(
    ("body", "qualified", "issue", "barriers"),
    [
        ("", False, None, ()),
        ("null\n", False, None, ()),
        ("false\n", False, "invalid_structure", ()),
        ("[]\n", False, "invalid_structure", ()),
        ("dependencies: null\n", False, "invalid_structure", (".",)),
        ("dependencies: {}\n", False, "invalid_structure", (".",)),
        ("dependencies: [{pip: false}]\n", True, "invalid_structure", ()),
        ("dependencies: [{pip: [false, 0, [], {}]}]\n", True, "invalid_structure", ()),
        ("name: example\n", False, None, ()),
        ("dependencies: []\n", True, None, ()),
        ("dependencies: [{}, {unknown: false}, {selector: [null]}, {pip: []}]\n", True, None, ()),
    ],
)
def test_a12_a13_untraversed_shapes_and_empty_manager_values_create_no_parse_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    body: str,
    qualified: bool,
    issue: str | None,
    barriers: tuple[str, ...],
) -> None:
    _write(tmp_path, {"environment.yml": body})
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            projects={"environment.yml": _CONDA_FORMATS} if qualified else {},
            issues={} if issue is None else {"environment.yml": issue},
            barriers=barriers,
        ),
        scanner,
        ["environment.yml"],
    )


def test_a14_nested_or_unknown_installer_keys_are_not_recovered_as_pip_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": (
                'pip: ["torch=="]\ndependencies: [{unknown: {pip: ["torch=="]}}, '
                '{selector: {pip: ["torch=="]}}, {pip: ["numpy>=1"], extra: {pip: false}}]\n'
            )
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["numpy>=1"]
    _assert_capture(
        result, _expected((_decl("numpy", ">=1", None, 3),)), scanner, ["environment.yml"]
    )


@pytest.mark.parametrize("pip_failure", [False, True])
def test_a15_conda_grammar_diagnostics_do_not_themselves_opt_in_to_pip_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    pip_failure: bool,
) -> None:
    entries = ["", " "] + (["torch=="] if pip_failure else [])
    _write(
        tmp_path,
        {
            "environment.yml": (
                "dependencies:\n  - pytorch::torch\n  - pytorch==\n"
                "  - pytorch==2.5.1\n  - numpy>=1.24\n  - pip: " + json.dumps(entries) + "\n"
            )
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == (["torch=="] if pip_failure else [])
    _assert_capture(
        result,
        _expected(
            (
                _decl("torch", "(unsupported conda declaration)", None, 2, display="pytorch"),
                _decl("torch", "==2.5.1", "2.5.1", 3, display="pytorch"),
                _decl("numpy", ">=1.24", None, 4),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:2: unsupported conda declaration",
                "environment.yml:4: unsupported conda declaration",
            )
            + (("environment.yml:5: torch==",) if pip_failure else ()),
            issues={"environment.yml": "unparsed_requirement"} if pip_failure else {},
        ),
        scanner,
        ["environment.yml"],
    )


@pytest.mark.parametrize("pip_failure", [False, True])
def test_a16_other_shared_helper_and_manager_callers_do_not_gain_new_causes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    pip_failure: bool,
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": '[tool.poetry.dependencies]\npeft=[{version="^0.1"}]\n',
            "requirements.txt": "torch==\n",
            "Pipfile": "[packages]\ntransformers={version=false}\n",
            "environment.yml": _pip(["torch=="] if pip_failure else []),
        },
    )
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["torch=="] * (2 if pip_failure else 1)
    assert graph.nodes == {
        "requirements.txt": _RequirementFile(True, ("requirements.txt:1: torch==",))
    }
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(False, frozenset({"requirements.txt"}))
    }
    _assert_capture(
        result,
        _expected(
            (
                _decl("peft", None, None, 2, "pyproject.toml"),
                _decl("transformers", None, None, 2, "Pipfile"),
            ),
            ("requirements.txt:1: torch==",)
            + (("environment.yml:1: torch==",) if pip_failure else ()),
            projects={
                "pyproject.toml": frozenset({"poetry.lock"}),
                "environment.yml": _CONDA_FORMATS,
                "Pipfile": frozenset({"Pipfile.lock"}),
            },
            issues={"environment.yml": "unparsed_requirement"} if pip_failure else {},
        ),
        scanner,
        ["pyproject.toml", "requirements.txt", "environment.yml", "Pipfile"],
        candidates=["requirements.txt"],
    )


@pytest.mark.parametrize(
    "value", ["# comment", "--index-url https://example.invalid/simple", "torch==2.5.1 # pin"]
)
def test_a16_pip_directives_and_comments_do_not_gain_graph_only_comment_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], value: str
) -> None:
    _write(tmp_path, {"environment.yml": _pip([value])})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    assert requirement_calls == [value]
    assert graph.nodes == graph.closures == {}
    _assert_capture(
        result,
        _expected(
            diagnostics=(f"environment.yml:1: {value}",),
            issues={"environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ["environment.yml"],
    )


@pytest.mark.parametrize("independent_root", [False, True])
def test_a16_embedded_include_is_not_followed_but_existing_requirements_root_still_is(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    independent_root: bool,
) -> None:
    target = "extras/requirements-extra.txt" if independent_root else "extras/pins-extra.txt"
    value = f"-r {target}"
    _write(tmp_path, {"environment.yml": _pip([value]), target: "torch==2.5.1\n"})
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    declaration = _decl("torch", "==2.5.1", "2.5.1", source=target)
    assert requirement_calls == (["torch==2.5.1"] if independent_root else []) + [value]
    assert graph.nodes == (
        {target: _RequirementFile(True, (declaration,))} if independent_root else {}
    )
    assert graph.closures == (
        {target: _RequirementsClosure(True, frozenset({target}), frozenset({declaration}))}
        if independent_root
        else {}
    )
    _assert_capture(
        result,
        _expected(
            (declaration,) if independent_root else (),
            (f"environment.yml:1: {value}",),
            locks=(Lockfile(target, frozenset({"torch"})),) if independent_root else (),
            issues={"environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ([target] if independent_root else []) + ["environment.yml"],
        candidates=[target] if independent_root else [],
        credit=frozenset({"torch"}) if independent_root else frozenset(),
    )


@pytest.mark.parametrize("pip_failure", [False, True])
def test_a16_a24_requirements_depth_frontier_is_not_expanded_or_rewritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requirement_calls: list[str],
    pip_failure: bool,
) -> None:
    paths = ["requirements.txt", *[f"deps/{index}.txt" for index in range(1, 12)]]
    bodies = {paths[0]: "torch>=2\n-r deps/1.txt\n"}
    bodies.update({paths[index]: f"-r {index + 1}.txt\n" for index in range(1, 11)})
    bodies[paths[11]] = "torch==2.5.1\n"
    bodies["environment.yml"] = _pip(["torch=="] if pip_failure else [])
    _write(tmp_path, bodies)
    result, scanner, graph = _capture(tmp_path, monkeypatch)
    torch = _decl("torch", ">=2", None, source="requirements.txt")
    assert requirement_calls == ["torch>=2"] + (["torch=="] if pip_failure else [])
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
            ("deps/10.txt:1: include depth limit",)
            + tuple(f"deps/{index}.txt:1: include incomplete" for index in range(9, 0, -1))
            + ("requirements.txt:2: include incomplete",)
            + (("environment.yml:1: torch==",) if pip_failure else ()),
            frontier=("deps/11.txt",),
            issues={"environment.yml": "unparsed_requirement"} if pip_failure else {},
        ),
        scanner,
        [*paths[:11], "environment.yml"],
        candidates=paths[:11],
    )


@pytest.mark.security
@pytest.mark.parametrize("outside", [False, True])
def test_a17_real_source_alias_retains_logical_identity_and_rejects_external_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], outside: bool
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "outside.txt" if outside else root / "storage/body.txt"
    target.parent.mkdir(exist_ok=True)
    target.write_text(_pip(["torch=="]), encoding="utf-8")
    try:
        (root / "environment.yml").symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"real symlink unavailable: {type(exc).__name__}")
    result, scanner, _ = _capture(root, monkeypatch)
    assert requirement_calls == ([] if outside else ["torch=="])
    assert scanner.physical_reads == ([] if outside else [target.resolve()])
    _assert_capture(
        result,
        _expected(
            diagnostics=("environment.yml:0: unreadable",)
            if outside
            else ("environment.yml:1: torch==",),
            projects={} if outside else {"environment.yml": _CONDA_FORMATS},
            barriers=(".",) if outside else (),
            issues={"environment.yml": "unreadable" if outside else "unparsed_requirement"},
        ),
        scanner,
        ["environment.yml"],
    )


@pytest.mark.security
@pytest.mark.parametrize("failure", ["binary", "oversize"])
def test_a17_filtered_candidates_stay_unread_and_read_rejection_is_not_pip_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str], failure: str
) -> None:
    _write(
        tmp_path,
        {
            ".venv/environment.yml": _pip(["torch=="]),
            ".reprollm/runs/old/environment.yml": _pip(["torch=="]),
            "other.yml": _pip(["torch=="]),
        },
    )
    content = b"\x00torch==" if failure == "binary" else b" " * (512 * 1024 + 1)
    (tmp_path / "environment.yml").write_bytes(content)
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == []
    _assert_capture(
        result,
        _expected(
            diagnostics=("environment.yml:0: unreadable",),
            projects={},
            barriers=(".",),
            issues={"environment.yml": "unreadable"},
        ),
        scanner,
        ["environment.yml"],
    )


def test_a17_old_manual_constructor_and_default_failure_dictionary_remain_independent() -> None:
    old = Declarations([], [], [], False, {}, set())
    other = Declarations()
    assert old == other == Declarations()
    assert old.declaration_read_issues is not other.declaration_read_issues
    assert old.unexpanded_requirement_targets == ()
    assert old.qualified_lock_packages([]) == frozenset()
    assert old.unverified_lock_paths([]) == {}


def test_a18_fresh_captures_recompute_causes_and_do_not_modify_prior_objects_or_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    history = b'{"schema_version":"historical","note":"preserve bytes"}\n'
    _write(tmp_path, {".reprollm/runs/old/environment.yml": _pip(["torch=="])})
    (tmp_path / "old-audit.json").write_bytes(history)
    states = [
        (
            ["torch=="],
            _expected(
                diagnostics=("environment.yml:1: torch==",),
                issues={"environment.yml": "unparsed_requirement"},
            ),
        ),
        (
            ["torch=="],
            _expected(
                diagnostics=("environment.yml:1: torch==",),
                issues={"environment.yml": "unparsed_requirement"},
            ),
        ),
        (["torch==2.5.1"], _expected((_decl("torch", "==2.5.1", "2.5.1"),))),
        (["torch>=2"], _expected((_decl("torch", ">=2", None),))),
        ([" \t\n"], _expected()),
        ([], _expected()),
    ]
    previous: list[tuple[Declarations, Declarations]] = []
    for values, expected in states:
        requirement_calls.clear()
        _write(tmp_path, {"environment.yml": _pip(values)})
        result, scanner, _ = _capture(tmp_path, monkeypatch)
        assert requirement_calls == [value.strip() for value in values if value.strip()]
        _assert_capture(result, expected, scanner, ["environment.yml"])
        assert (tmp_path / "old-audit.json").read_bytes() == history
        for captured, original in previous:
            assert captured == original
        previous.append((result, expected))
    (tmp_path / "environment.yml").unlink()
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    _assert_capture(result, _expected(projects={}, manifest=False), scanner, [])
    for captured, original in previous:
        assert captured == original


def test_a20_conda_lock_credit_from_declarations_and_imports_retains_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {
            "pkg/environment.yml": _pip(["numpy>=1", "torch=="]),
            "pkg/conda-lock.yml": "package: [{name: torch}, {name: numpy}, {name: peft}]\n",
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["numpy>=1", "torch=="]
    for origin in ["pkg/src/a.py", "pkg/src/../a.py"]:
        assert result.qualified_lock_packages([("torch", origin)]) == frozenset({"numpy", "torch"})
    for origin in ["outside/a.py", "../pkg/a.py", "/pkg/a.py", "C:/pkg/a.py", "pkg/../../a.py"]:
        assert result.qualified_lock_packages([("torch", origin)]) == frozenset({"numpy"})
    _assert_capture(
        result,
        _expected(
            (_decl("numpy", ">=1", None, source="pkg/environment.yml"),),
            ("pkg/environment.yml:1: torch==",),
            projects={"pkg/environment.yml": _CONDA_FORMATS},
            locks=(Lockfile("pkg/conda-lock.yml", frozenset({"torch", "numpy", "peft"})),),
            issues={"pkg/environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ["pkg/environment.yml", "pkg/conda-lock.yml"],
        credit=frozenset({"numpy"}),
    )


def test_a21_two_environment_basenames_keep_ambiguous_pairing_even_with_partial_declarations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, requirement_calls: list[str]
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": _pip(["torch=="]),
            "environment.yaml": _pip(["numpy>=1"]),
            "conda-lock.yml": "package: [{name: torch}, {name: numpy}]\n",
        },
    )
    result, scanner, _ = _capture(tmp_path, monkeypatch)
    assert requirement_calls == ["numpy>=1", "torch=="]
    assert result.qualified_lock_packages([("torch", "control.py")]) == frozenset()
    _assert_capture(
        result,
        _expected(
            (_decl("numpy", ">=1", None, source="environment.yaml"),),
            ("environment.yml:1: torch==",),
            projects={"environment.yaml": frozenset(), "environment.yml": frozenset()},
            locks=(Lockfile("conda-lock.yml", frozenset({"torch", "numpy"})),),
            issues={"environment.yml": "unparsed_requirement"},
        ),
        scanner,
        ["environment.yaml", "environment.yml", "conda-lock.yml"],
    )
