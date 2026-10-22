"""R07-C D-G: final depth frontier, preserving the captured dependency view."""

from dataclasses import fields
from pathlib import Path, PurePosixPath
from typing import IO, Any

import pytest

from reprollm.core import deps as deps_module
from reprollm.core.deps import (
    DeclarationReadIssue,
    Declarations,
    DependencyDeclaration,
    Lockfile,
    _RequirementsClosure,
    _RequirementsGraph,
    scan_dependencies,
)
from reprollm.core.git import GitInfo
from reprollm.core.scanner import RepoScanner


class _RecordingScanner(RepoScanner):
    def __init__(self, root: Path) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.reads: list[str] = []
        self.candidate_checks: list[str] = []

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        self.reads.append(rel_path)
        assert max_bytes == 512 * 1024
        return super().read_text(rel_path, max_bytes)

    def is_analysis_candidate(self, rel_path: str) -> bool:
        self.candidate_checks.append(rel_path)
        return super().is_analysis_candidate(rel_path)

    def exists(self, rel_path: str) -> bool:
        raise AssertionError(f"Unexpected existence probe: {rel_path}")

    def size(self, rel_path: str) -> int | None:
        raise AssertionError(f"Unexpected size probe: {rel_path}")


class _ObservedGraph(_RequirementsGraph):
    def __init__(self, scanner: RepoScanner, result: Declarations) -> None:
        super().__init__(scanner, result)
        self.after_roots: list[tuple[str, frozenset[str]]] = []

    def _expand(self, source: str, depth: int, active: set[str]) -> None:
        super()._expand(source, depth, active)
        if depth == 0:
            self.after_roots.append((source, frozenset(self.nodes)))


def _scan(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Declarations, _RecordingScanner, _ObservedGraph]:
    graphs: list[_ObservedGraph] = []

    def graph_factory(scanner: RepoScanner, result: Declarations) -> _ObservedGraph:
        graph = _ObservedGraph(scanner, result)
        graphs.append(graph)
        return graph

    monkeypatch.setattr(deps_module, "_RequirementsGraph", graph_factory)
    scanner = _RecordingScanner(root)
    result = scan_dependencies(scanner)
    assert len(graphs) == 1
    return result, scanner, graphs[0]


def _write(root: Path, path: str, body: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def _chain(root: Path, *, entry: str = "requirements.txt", final_depth: int = 11) -> None:
    _write(root, entry, "torch>=2\n-r deps/1.txt\n")
    for depth in range(1, final_depth):
        _write(root, f"deps/{depth}.txt", f"-r {depth + 1}.txt\n")


def _torch(source: str, *, exact: bool = False) -> DependencyDeclaration:
    return DependencyDeclaration(
        "torch", "torch", "==2.5.1" if exact else ">=2", "2.5.1" if exact else None, source, 1
    )


def _depth_diagnostics(entry: str = "requirements.txt") -> list[str]:
    return (
        ["deps/10.txt:1: include depth limit"]
        + [f"deps/{depth}.txt:1: include incomplete" for depth in range(9, 0, -1)]
        + [f"{entry}:2: include incomplete"]
    )


def _assert_state(
    result: Declarations,
    *,
    declarations: list[DependencyDeclaration],
    diagnostics: list[str],
    frontier: tuple[str, ...],
    locks: list[Lockfile] | None = None,
    issues: dict[str, DeclarationReadIssue] | None = None,
    projects: dict[str, frozenset[str]] | None = None,
    barriers: set[PurePosixPath] | None = None,
    manifest: bool = True,
) -> None:
    # Check the full pre-existing inventory before the new fact, including negative evidence.
    assert result.declarations == declarations
    assert result.unparsed == diagnostics
    assert result.lockfiles == ([] if locks is None else locks)
    assert result.manifest_present is manifest
    assert result.declaration_read_issues == ({} if issues is None else issues)
    assert result._project_manifests == ({} if projects is None else projects)
    assert result._uncertain_directories == (set() if barriers is None else barriers)
    assert result.unexpanded_requirement_targets == frontier


@pytest.mark.parametrize("depth", [9, 10])
@pytest.mark.parametrize("exact", [False, True])
@pytest.mark.parametrize("root_exact", [False, True])
def test_g01_boundary_entries_are_captured_without_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, depth: int, exact: bool, root_exact: bool
) -> None:
    _chain(tmp_path, final_depth=depth)
    if root_exact:
        _write(tmp_path, "requirements.txt", "torch==2.5.1\n-r deps/1.txt\n")
    _write(tmp_path, f"deps/{depth}.txt", "torch==2.5.1\n" if exact else "torch>=2\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    expected = [
        _torch("requirements.txt", exact=root_exact),
        _torch(f"deps/{depth}.txt", exact=exact),
    ]
    assert scanner.reads == ["requirements.txt"] + [f"deps/{n}.txt" for n in range(1, depth + 1)]
    assert scanner.candidate_checks == scanner.reads
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            True, frozenset(scanner.reads), frozenset(expected)
        )
    }
    assert graph.closures["requirements.txt"].is_exact is (root_exact and exact)
    _assert_state(
        result,
        declarations=expected,
        diagnostics=[],
        frontier=(),
        locks=[Lockfile("requirements.txt", frozenset({"torch"}))] if root_exact and exact else [],
    )


@pytest.mark.parametrize("body", ["torch==2.5.1\n", "torch>=2\n", "", None])
def test_g02_g03_depth_eleven_is_not_probed_or_credited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str | None
) -> None:
    _chain(tmp_path)
    if body is not None:
        _write(tmp_path, "deps/11.txt", body)
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    reads = ["requirements.txt"] + [f"deps/{n}.txt" for n in range(1, 11)]
    assert scanner.reads == reads
    assert scanner.candidate_checks == reads
    assert set(graph.nodes) == set(reads)
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            False, frozenset(reads), frozenset({_torch("requirements.txt")})
        )
    }
    _assert_state(
        result,
        declarations=[_torch("requirements.txt")],
        diagnostics=_depth_diagnostics(),
        frontier=("deps/11.txt",),
    )


@pytest.mark.parametrize("excluded", [".venv/hidden.txt", "environment/hidden.txt"])
@pytest.mark.parametrize("depth", [1, 11])
def test_g04_g05_candidate_filter_is_not_probed_beyond_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, excluded: str, depth: int
) -> None:
    _write(tmp_path, excluded, "torch==2.5.1\n")
    if excluded.startswith("environment/"):
        _write(tmp_path, "environment/pyvenv.cfg", "home = local\n")
    if depth == 1:
        _write(tmp_path, "requirements.txt", f"torch>=2\n-r {excluded}\n")
    else:
        _chain(tmp_path)
        _write(tmp_path, "deps/10.txt", f"-r ../{excluded}\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    reads = ["requirements.txt"] + ([] if depth == 1 else [f"deps/{n}.txt" for n in range(1, 11)])
    assert scanner.reads == reads
    assert scanner.candidate_checks == reads + ([excluded] if depth == 1 else [])
    if depth == 1:
        assert graph.nodes[excluded].readable is False
    else:
        assert excluded not in graph.nodes
    assert graph.closures["requirements.txt"] == _RequirementsClosure(
        False, frozenset(reads), frozenset({_torch("requirements.txt")})
    )
    _assert_state(
        result,
        declarations=[_torch("requirements.txt")],
        diagnostics=["requirements.txt:2: include unreadable"]
        if depth == 1
        else _depth_diagnostics(),
        frontier=() if depth == 1 else (excluded,),
    )


@pytest.mark.parametrize("failure", ["missing", "binary", "oversize", "permission"])
def test_g06_reached_body_failure_keeps_its_existing_fact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    _write(tmp_path, "requirements.txt", "torch>=2\n-r body.txt\n")
    if failure != "missing":
        body = (
            "bad\x00\n"
            if failure == "binary"
            else "x" * (512 * 1024 + 1)
            if failure == "oversize"
            else "torch==2.5.1\n"
        )
        _write(tmp_path, "body.txt", body)
    if failure == "permission":
        original_open = Path.open

        def fail_body_open(path: Path, *args: object, **kwargs: object) -> IO[Any]:
            if path == tmp_path / "body.txt":
                raise PermissionError("fixture read denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", fail_body_open)
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == ["requirements.txt", "body.txt"]
    assert scanner.candidate_checks == scanner.reads
    assert graph.nodes["body.txt"].readable is False
    assert graph.closures["requirements.txt"] == _RequirementsClosure(
        False, frozenset({"requirements.txt"}), frozenset({_torch("requirements.txt")})
    )
    _assert_state(
        result,
        declarations=[_torch("requirements.txt")],
        diagnostics=["requirements.txt:2: include unreadable"],
        frontier=(),
        issues={"body.txt": "unreadable"},
    )


@pytest.mark.parametrize("body", ["torch==2.5.1\n", "torch>=2\n", ""])
@pytest.mark.parametrize("deep_first", [True, False])
def test_g07_g08_all_roots_can_capture_a_previously_unexpanded_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, deep_first: bool
) -> None:
    deep = "requirements-a.txt" if deep_first else "requirements-z.txt"
    shallow = "requirements-z.txt" if deep_first else "requirements-a.txt"
    _chain(tmp_path, entry=deep)
    _write(tmp_path, "deps/11.txt", body)
    _write(tmp_path, shallow, "-r deps/11.txt\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    chain_reads = [deep] + [f"deps/{n}.txt" for n in range(1, 11)]
    shallow_reads = [shallow, "deps/11.txt"]
    assert scanner.reads == (
        chain_reads + shallow_reads if deep_first else shallow_reads + chain_reads
    )
    assert scanner.candidate_checks == scanner.reads
    assert [root for root, _ in graph.after_roots] == ["requirements-a.txt", "requirements-z.txt"]
    assert ("deps/11.txt" in graph.after_roots[0][1]) is (not deep_first)
    assert "deps/11.txt" in graph.after_roots[1][1]
    target_decls = [_torch("deps/11.txt", exact=body.startswith("torch=="))] if body else []
    expected = [_torch(deep)] + target_decls if deep_first else target_decls + [_torch(deep)]
    assert graph.closures == {
        deep: _RequirementsClosure(False, frozenset(chain_reads), frozenset({_torch(deep)})),
        shallow: _RequirementsClosure(True, frozenset(shallow_reads), frozenset(target_decls)),
    }
    locks = [Lockfile(shallow, frozenset({"torch"}))] if body.startswith("torch==") else []
    assert result.qualified_lock_packages([]) == (frozenset({"torch"}) if locks else frozenset())
    _assert_state(
        result,
        declarations=expected,
        diagnostics=_depth_diagnostics(deep),
        frontier=(),
        locks=locks,
    )


def test_g09_independently_discovered_target_root_resolves_depth_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _chain(tmp_path, entry="requirements-a.txt")
    _write(tmp_path, "deps/10.txt", "-r ../requirements-extra.txt\n")
    _write(tmp_path, "requirements-extra.txt", "torch==2.5.1\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    chain_reads = ["requirements-a.txt"] + [f"deps/{n}.txt" for n in range(1, 11)]
    assert scanner.reads == chain_reads + ["requirements-extra.txt"]
    assert scanner.candidate_checks == scanner.reads
    assert "requirements-extra.txt" not in graph.after_roots[0][1]
    assert "requirements-extra.txt" in graph.after_roots[1][1]
    assert graph.closures["requirements-extra.txt"] == _RequirementsClosure(
        True,
        frozenset({"requirements-extra.txt"}),
        frozenset({_torch("requirements-extra.txt", exact=True)}),
    )
    _assert_state(
        result,
        declarations=[_torch("requirements-a.txt"), _torch("requirements-extra.txt", exact=True)],
        diagnostics=_depth_diagnostics("requirements-a.txt"),
        frontier=(),
        locks=[Lockfile("requirements-extra.txt", frozenset({"torch"}))],
    )


def test_g10_reexpanded_target_can_have_a_distinct_final_child_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _chain(tmp_path, entry="requirements-a.txt", final_depth=20)
    _write(tmp_path, "deps/20.txt", "torch==2.5.1\n")
    _write(tmp_path, "requirements-z.txt", "-r deps/2.txt\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == ["requirements-a.txt"] + [f"deps/{n}.txt" for n in range(1, 11)] + [
        "requirements-z.txt",
        "deps/11.txt",
    ]
    assert scanner.candidate_checks == scanner.reads
    assert "deps/11.txt" not in graph.after_roots[0][1]
    assert "deps/11.txt" in graph.after_roots[1][1]
    assert "deps/12.txt" not in graph.nodes
    assert graph.closures == {
        "requirements-a.txt": _RequirementsClosure(
            False,
            frozenset(["requirements-a.txt"] + [f"deps/{n}.txt" for n in range(1, 11)]),
            frozenset({_torch("requirements-a.txt")}),
        ),
        "requirements-z.txt": _RequirementsClosure(
            False,
            frozenset(["requirements-z.txt"] + [f"deps/{n}.txt" for n in range(2, 12)]),
            frozenset(),
        ),
    }
    _assert_state(
        result,
        declarations=[_torch("requirements-a.txt")],
        diagnostics=_depth_diagnostics("requirements-a.txt")
        + [
            "deps/11.txt:1: include depth limit",
            "deps/10.txt:1: include incomplete",
            "requirements-z.txt:1: include incomplete",
        ],
        frontier=("deps/12.txt",),
    )


@pytest.mark.parametrize("reverse", [False, True])
def test_g11_g12_frontier_normalizes_deduplicates_and_sorts_across_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reverse: bool
) -> None:
    roots = ["requirements-a.txt", "requirements-z.txt"]
    for entry, prefix in zip(roots, ["a", "z"], strict=True):
        _write(tmp_path, entry, f"torch>=2\n-r {prefix}/1.txt\n")
        for n in range(1, 10):
            _write(tmp_path, f"{prefix}/{n}.txt", f"-r {n + 1}.txt\n")
        targets = ["../targets/z.txt", "../targets/a.txt", "../targets/inside/../a.txt"]
        if reverse:
            targets.reverse()
        _write(tmp_path, f"{prefix}/10.txt", "".join(f"-r {target}\n" for target in targets))
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == [
        item
        for entry, prefix in zip(roots, ["a", "z"], strict=True)
        for item in [entry] + [f"{prefix}/{n}.txt" for n in range(1, 11)]
    ]
    assert scanner.candidate_checks == scanner.reads
    diagnostics = []
    for entry, prefix in zip(roots, ["a", "z"], strict=True):
        lines = [1, 3] if reverse else [1, 2]
        diagnostics.extend(f"{prefix}/10.txt:{line}: include depth limit" for line in lines)
        diagnostics.extend(f"{prefix}/{n}.txt:1: include incomplete" for n in range(9, 0, -1))
        diagnostics.append(f"{entry}:2: include incomplete")
        assert graph.closures[entry] == _RequirementsClosure(
            False,
            frozenset([entry] + [f"{prefix}/{n}.txt" for n in range(1, 11)]),
            frozenset({_torch(entry)}),
        )
    _assert_state(
        result,
        declarations=[_torch(entry) for entry in roots],
        diagnostics=diagnostics,
        frontier=("targets/a.txt", "targets/z.txt"),
    )


@pytest.mark.parametrize("shape", ["self", "cycle", "diamond"])
def test_g13_cycles_and_shared_captured_nodes_do_not_imply_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    if shape == "self":
        _write(tmp_path, "requirements.txt", "torch>=2\n-r requirements.txt\n")
        reads = ["requirements.txt"]
        diagnostics = ["requirements.txt:2: include cycle"]
    elif shape == "cycle":
        _write(tmp_path, "requirements.txt", "torch>=2\n-r a.txt\n")
        _write(tmp_path, "a.txt", "-r requirements.txt\n")
        reads = ["requirements.txt", "a.txt"]
        diagnostics = ["a.txt:1: include cycle", "requirements.txt:2: include incomplete"]
    else:
        _write(tmp_path, "requirements.txt", "torch>=2\n-r a.txt\n-r b.txt\n")
        _write(tmp_path, "a.txt", "-r shared.txt\n")
        _write(tmp_path, "b.txt", "-r shared.txt\n")
        _write(tmp_path, "shared.txt", "torch==2.5.1\n")
        reads = ["requirements.txt", "a.txt", "shared.txt", "b.txt"]
        diagnostics = []
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    expected = [_torch("requirements.txt")] + (
        [_torch("shared.txt", exact=True)] if shape == "diamond" else []
    )
    assert scanner.reads == reads
    assert scanner.candidate_checks == reads
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            shape == "diamond", frozenset(reads), frozenset(expected)
        )
    }
    _assert_state(result, declarations=expected, diagnostics=diagnostics, frontier=())


@pytest.mark.parametrize("repair", ["shallow", "remove", "exact-root"])
def test_g21_fresh_scan_does_not_retain_frontier_after_graph_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repair: str
) -> None:
    _chain(tmp_path)
    _write(tmp_path, "deps/11.txt", "torch==2.5.1\n")
    before, _, _ = _scan(tmp_path, monkeypatch)
    if repair == "shallow":
        _write(tmp_path, "requirements.txt", "torch>=2\n-r deps/11.txt\n")
        expected = [_torch("requirements.txt"), _torch("deps/11.txt", exact=True)]
        reads = ["requirements.txt", "deps/11.txt"]
        locks = []
    elif repair == "remove":
        _write(tmp_path, "requirements.txt", "torch>=2\n")
        expected = [_torch("requirements.txt")]
        reads = ["requirements.txt"]
        locks = []
    else:
        _write(tmp_path, "requirements.txt", "torch==2.5.1\n")
        expected = [_torch("requirements.txt", exact=True)]
        reads = ["requirements.txt"]
        locks = [Lockfile("requirements.txt", frozenset({"torch"}))]
    after, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == reads
    assert scanner.candidate_checks == reads
    assert graph.closures["requirements.txt"] == _RequirementsClosure(
        True, frozenset(reads), frozenset(expected)
    )
    assert before.unexpanded_requirement_targets == ("deps/11.txt",)
    _assert_state(after, declarations=expected, diagnostics=[], frontier=(), locks=locks)


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("-r", "include malformed"),
        ("-r bad\x00.txt", "include malformed"),
        ('-r "quoted.txt"', "include unsupported syntax"),
        ("-r 'quoted.txt'", "include unsupported syntax"),
        ("-rname.txt", "include unsupported syntax"),
        ("--requirement=name.txt", "include unsupported syntax"),
        ("-r https://example.invalid/a.txt", "include unsupported syntax"),
        ("-r /outside.txt", "include unreadable"),
        ("-r C:\\outside.txt", "include unreadable"),
        ("-r ../outside.txt", "include unreadable"),
        ("-r a.txt # comment", "include unsupported syntax"),
        ("-r $TARGET", "include unsupported syntax"),
    ],
)
def test_g22_unsupported_edges_do_not_create_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line: str, reason: str
) -> None:
    # NUL is supplied at the reader seam: real binary-body handling is covered separately.
    _write(tmp_path, "requirements.txt", "torch>=2\n" + line.replace("\x00", "") + "\n")
    if "\x00" in line:
        monkeypatch.setattr(
            RepoScanner, "read_text", lambda self, path, cap: "torch>=2\n" + line + "\n"
        )
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == ["requirements.txt"]
    assert scanner.candidate_checks == scanner.reads
    assert graph.closures["requirements.txt"] == _RequirementsClosure(
        False, frozenset({"requirements.txt"}), frozenset({_torch("requirements.txt")})
    )
    _assert_state(
        result,
        declarations=[_torch("requirements.txt")],
        diagnostics=[f"requirements.txt:2: {reason}"],
        frontier=(),
    )


@pytest.mark.parametrize(
    "line",
    [
        "???",
        "torch>=2 # comment",
        "torch==2.5.1 \\",
        "--index-url https://example.invalid",
        "-c constraints.txt",
        "--constraint constraints.txt",
        "-e .",
        "git+https://example.invalid/pkg.git",
        "torch @ https://example.invalid/pkg.whl",
    ],
)
def test_g23_readable_unsupported_grammar_does_not_create_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line: str
) -> None:
    _write(tmp_path, "requirements.txt", f"torch>=2\n{line}\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == ["requirements.txt"]
    assert scanner.candidate_checks == scanner.reads
    assert graph.closures["requirements.txt"] == _RequirementsClosure(
        False, frozenset({"requirements.txt"}), frozenset({_torch("requirements.txt")})
    )
    _assert_state(
        result,
        declarations=[_torch("requirements.txt")],
        diagnostics=[f"requirements.txt:2: {line}"],
        frontier=(),
    )


@pytest.mark.parametrize("omission", ["excluded-root", "oversize-root", "no-root"])
def test_g24_omitted_roots_do_not_invent_include_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, omission: str
) -> None:
    if omission == "excluded-root":
        _write(tmp_path, ".venv/requirements.txt", "torch>=2\n-r hidden.txt\n")
    elif omission == "oversize-root":
        _write(tmp_path, "requirements.txt", "-r hidden.txt\n" + "#" * (2 * 1024 * 1024))
    else:
        _write(tmp_path, "deps.txt", "torch>=2\n-r hidden.txt\n")
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == []
    assert scanner.candidate_checks == []
    assert graph.nodes == {}
    assert graph.closures == {}
    _assert_state(result, declarations=[], diagnostics=[], frontier=(), manifest=False)


def test_g29_new_fact_is_appended_without_reinterpreting_legacy_positional_values() -> None:
    declarations = [_torch("requirements.txt")]
    diagnostics = ["requirements.txt:2: unsupported"]
    locks = [Lockfile("uv.lock", frozenset({"torch"}))]
    projects = {"pyproject.toml": frozenset({"uv.lock"})}
    barriers = {PurePosixPath("nested")}
    issues: dict[str, DeclarationReadIssue] = {"Pipfile": "invalid_syntax"}
    result = Declarations(declarations, diagnostics, locks, True, projects, barriers, issues)
    assert result.declarations is declarations
    assert result.unparsed is diagnostics
    assert result.lockfiles is locks
    assert result._project_manifests is projects
    assert result._uncertain_directories is barriers
    assert result.declaration_read_issues is issues
    assert result.unexpanded_requirement_targets == ()
    assert Declarations().unexpanded_requirement_targets == ()
    assert [item.name for item in fields(Declarations)] == [
        "declarations",
        "unparsed",
        "lockfiles",
        "manifest_present",
        "_project_manifests",
        "_uncertain_directories",
        "declaration_read_issues",
        "unexpanded_requirement_targets",
    ]


def test_frontier_does_not_change_other_project_roots_barriers_or_lock_qualification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _chain(tmp_path)
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies=["torch>=2"]\n')
    _write(
        tmp_path,
        "uv.lock",
        '[[package]]\nname="torch"\nversion="2.5.1"\n[[package]]\nname="numpy"\nversion="2.1"\n',
    )
    _write(tmp_path, "nested/pyproject.toml", "project=false\n")
    result, scanner, _ = _scan(tmp_path, monkeypatch)
    assert scanner.reads == ["pyproject.toml", "nested/pyproject.toml", "requirements.txt"] + [
        f"deps/{n}.txt" for n in range(1, 11)
    ] + ["uv.lock"]
    assert scanner.candidate_checks == ["requirements.txt"] + [
        f"deps/{n}.txt" for n in range(1, 11)
    ]
    assert result.qualified_lock_packages([("torch", "nested/train.py")]) == frozenset({"torch"})
    assert result.qualified_lock_packages([("numpy", "nested/train.py")]) == frozenset({"torch"})
    assert result.qualified_lock_packages([("numpy", "train.py")]) == frozenset({"torch", "numpy"})
    assert result.unverified_lock_paths([]) == {}
    _assert_state(
        result,
        declarations=[
            DependencyDeclaration("torch", "torch", ">=2", None, "pyproject.toml", 2),
            _torch("requirements.txt"),
        ],
        diagnostics=_depth_diagnostics(),
        frontier=("deps/11.txt",),
        locks=[Lockfile("uv.lock", frozenset({"torch", "numpy"}))],
        issues={"nested/pyproject.toml": "invalid_structure"},
        projects={"pyproject.toml": frozenset({"uv.lock", "poetry.lock"})},
        barriers={PurePosixPath("nested")},
    )
