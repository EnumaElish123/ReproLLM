"""R07-C D-C: bounded comments preserve the captured graph and old grammar."""

from dataclasses import asdict
from pathlib import Path, PurePosixPath

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


class _Scanner(RepoScanner):
    def __init__(self, root: Path) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.reads: list[str] = []
        self.candidates: list[str] = []

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        self.reads.append(rel_path)
        assert max_bytes == 512 * 1024
        return super().read_text(rel_path, max_bytes)

    def is_analysis_candidate(self, rel_path: str) -> bool:
        self.candidates.append(rel_path)
        return super().is_analysis_candidate(rel_path)

    def exists(self, rel_path: str) -> bool:
        raise AssertionError(f"Unexpected existence probe: {rel_path}")

    def size(self, rel_path: str) -> int | None:
        raise AssertionError(f"Unexpected size probe: {rel_path}")


class _Graph(_RequirementsGraph):
    def __init__(self, scanner: RepoScanner, result: Declarations) -> None:
        super().__init__(scanner, result)
        self.after_roots: list[tuple[str, frozenset[str]]] = []

    def _expand(self, source: str, depth: int, active: set[str]) -> None:
        super()._expand(source, depth, active)
        if depth == 0:
            self.after_roots.append((source, frozenset(self.nodes)))


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, body in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body.encode("utf-8"))


def _scan(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Declarations, _Scanner, _Graph]:
    graphs: list[_Graph] = []

    def factory(scanner: RepoScanner, result: Declarations) -> _Graph:
        graph = _Graph(scanner, result)
        graphs.append(graph)
        return graph

    monkeypatch.setattr(deps_module, "_RequirementsGraph", factory)
    scanner = _Scanner(root)
    result = scan_dependencies(scanner)
    assert len(graphs) == 1
    return result, scanner, graphs[0]


def _declaration(
    name: str = "torch",
    specifier: str | None = "==2.5.1",
    exact: str | None = "2.5.1",
    source: str = "requirements.txt",
    line: int = 1,
    display: str | None = None,
) -> DependencyDeclaration:
    return DependencyDeclaration(name, display or name, specifier, exact, source, line)


def _facts(
    result: Declarations,
    declarations: list[DependencyDeclaration],
    diagnostics: list[str],
    *,
    locks: list[Lockfile] | None = None,
    issues: dict[str, DeclarationReadIssue] | None = None,
    frontier: tuple[str, ...] = (),
    projects: dict[str, frozenset[str]] | None = None,
    barriers: set[PurePosixPath] | None = None,
    qualified: frozenset[str] | None = None,
) -> None:
    expected_locks = [] if locks is None else locks
    assert result.declarations == declarations
    assert result.unparsed == diagnostics
    assert result.lockfiles == expected_locks
    assert result.manifest_present is True
    assert result.declaration_read_issues == ({} if issues is None else issues)
    assert result.unexpanded_requirement_targets == frontier
    assert result._project_manifests == ({} if projects is None else projects)
    assert result._uncertain_directories == (set() if barriers is None else barriers)
    expected_credit = (
        frozenset(package for lock in expected_locks for package in lock.packages)
        if qualified is None
        else qualified
    )
    assert result.qualified_lock_packages([]) == expected_credit


@pytest.mark.parametrize(
    ("body", "name", "display", "specifier", "exact"),
    [
        ("torch==2.5.1 # pin", "torch", "torch", "==2.5.1", "2.5.1"),
        ("torch==2.5.1\t# pin", "torch", "torch", "==2.5.1", "2.5.1"),
        ("torch==2.5.1  \t #", "torch", "torch", "==2.5.1", "2.5.1"),
        ("torch==2.5.1 # one # two", "torch", "torch", "==2.5.1", "2.5.1"),
        ("PyTorch[extra]==2.5.1 # alias", "torch", "PyTorch", "==2.5.1", "2.5.1"),
        ("torch==2.5.1; os_name == 'posix' # pin", "torch", "torch", "==2.5.1", "2.5.1"),
        ("torch==2.5.1+cpu # local", "torch", "torch", "==2.5.1+cpu", "2.5.1+cpu"),
        ("torch==2.5rc1 # pre", "torch", "torch", "==2.5rc1", "2.5rc1"),
        ("torch==2.5.post1 # post", "torch", "torch", "==2.5.post1", "2.5.post1"),
        ("torch==2.5.dev1 # dev", "torch", "torch", "==2.5.dev1", "2.5.dev1"),
        ("torch==1!2.5 # epoch", "torch", "torch", "==1!2.5", "1!2.5"),
        ("torch>=2 # range", "torch", "torch", ">=2", None),
        ("torch # unversioned", "torch", "torch", None, None),
        ("torch==2.* # wildcard", "torch", "torch", "==2.*", None),
        ("torch===2.5.1 # arbitrary", "torch", "torch", "===2.5.1", None),
        ("torch==2.5.1,!=2.0 # compound", "torch", "torch", "!=2.0,==2.5.1", None),
    ],
)
def test_c01_c06_literal_comment_capture_and_exact_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    name: str,
    display: str,
    specifier: str | None,
    exact: str | None,
) -> None:
    _write(tmp_path, {"requirements.txt": f" \n\t# heading\n  {body}  \n"})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    expected = [_declaration(name, specifier, exact, line=3, display=display)]
    locks = [Lockfile("requirements.txt", frozenset({name}))] if exact else []
    _facts(result, expected, [], locks=locks)
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            True, frozenset({"requirements.txt"}), frozenset(expected)
        )
    }
    assert graph.closures["requirements.txt"].is_exact is (exact is not None)
    assert graph.nodes["requirements.txt"].events == tuple(expected)


@pytest.mark.parametrize("body", ["", " \t\n", "# comment\n  # indented\n"])
def test_c05_empty_comments_do_not_create_a_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str
) -> None:
    _write(tmp_path, {"requirements.txt": body})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    _facts(result, [], [])
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(True, frozenset({"requirements.txt"}))
    }
    assert graph.closures["requirements.txt"].is_exact is False


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("torch==2.5.1#pin", None),
        ("torch==2.5.1\u00a0# pin", None),
        ("torch==2.5.1\u2003# pin", None),
        ("??? # one # two", None),
        ("torch==2.5.1; os_name == 'x # y' # outer", None),
        ("torch==2.5.1 # contact @ team", None),
        ("torch@https://example.invalid/a.whl # note", None),
        ("torch @https://example.invalid/a.whl # note", None),
        ("torch\t@\thttps://example.invalid/a.whl # note", None),
        ("git+https://example.invalid/a.git # note", None),
        ("./local.whl # note", None),
        ("-r child.txt # note", "include unsupported syntax"),
        ("--requirement child.txt # note", "include unsupported syntax"),
        ('-r "child.txt" # note', "include unsupported syntax"),
        ("-rchild.txt # note", "include unsupported syntax"),
        ("--requirement=child.txt # note", "include unsupported syntax"),
        ("--index-url https://example.invalid # note", None),
        ("-c child.txt # note", None),
        ("--constraint child.txt # note", None),
        ("-e . # note", None),
    ],
)
def test_c04_c08_c13_excluded_routes_retain_original_diagnostic_and_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, line: str, reason: str | None
) -> None:
    _write(
        tmp_path, {"requirements.txt": f"torch==2.5.1\n  {line}  \n", "child.txt": "peft==0.12.0\n"}
    )
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    expected = [_declaration()]
    diagnostic = f"requirements.txt:2: {reason or line}"
    _facts(result, expected, [diagnostic])
    assert set(graph.nodes) == {"requirements.txt"}
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            False, frozenset({"requirements.txt"}), frozenset(expected)
        )
    }


@pytest.mark.parametrize(
    ("line", "specifier", "exact"),
    [
        ("torch==2.5.1; os_name == 'x # y'", "==2.5.1", "2.5.1"),
        ("torch@https://example.invalid/a.whl#fragment", None, None),
        ("torch @https://example.invalid/a.whl", None, None),
    ],
)
@pytest.mark.parametrize("veto", [False, True])
def test_c07_c13_original_success_wins_even_with_file_veto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    line: str,
    specifier: str | None,
    exact: str | None,
    veto: bool,
) -> None:
    _write(tmp_path, {"requirements.txt": line + "\n" + ("# trailing\\\n" if veto else "")})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    expected = [_declaration(specifier=specifier, exact=exact)]
    locks = [Lockfile("requirements.txt", frozenset({"torch"}))] if exact else []
    _facts(result, expected, [], locks=locks)
    assert graph.nodes["requirements.txt"].events == tuple(expected)
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            True, frozenset({"requirements.txt"}), frozenset(expected)
        )
    }


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
@pytest.mark.parametrize("veto_line", ["# end\\", "# end\\\\", "# end\\  \t", "--unknown \\"])
@pytest.mark.parametrize("before", [True, False])
def test_c14_c15_any_trailing_backslash_vetoes_whole_file_without_revoking_old_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: str, veto_line: str, before: bool
) -> None:
    candidate = "peft==0.12.0 # candidate"
    lines = (
        ["torch==2.5.1", veto_line, candidate] if before else ["torch==2.5.1", candidate, veto_line]
    )
    _write(tmp_path, {"requirements.txt": newline.join(lines) + newline})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    diagnostics = [
        f"requirements.txt:{number}: {text.strip()}"
        for number, text in enumerate(lines, 1)
        if text == candidate or text.startswith("--")
    ]
    expected = [_declaration()]
    _facts(result, expected, diagnostics)
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            False, frozenset({"requirements.txt"}), frozenset(expected)
        )
    }


@pytest.mark.parametrize("suffix", ["# slash \\ inside", "# slash \\ followed"])
def test_c16_nonterminal_backslash_does_not_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    _write(tmp_path, {"requirements.txt": f"torch==2.5.1 {suffix}\n"})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    expected = [_declaration()]
    _facts(result, expected, [], locks=[Lockfile("requirements.txt", frozenset({"torch"}))])
    assert graph.closures["requirements.txt"].is_exact is True


@pytest.mark.parametrize("veto_parent", [True, False])
def test_c17_file_veto_does_not_cross_include_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, veto_parent: bool
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch==2.5.1 # root\n-r child.txt\n"
            + ("# end\\\n" if veto_parent else ""),
            "child.txt": "peft==0.12.0 # child\n" + ("# end\\\n" if not veto_parent else ""),
        },
    )
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt", "child.txt"]
    expected = (
        [_declaration("peft", "==0.12.0", "0.12.0", "child.txt")]
        if veto_parent
        else [_declaration()]
    )
    diagnostics = (
        ["requirements.txt:1: torch==2.5.1 # root"]
        if veto_parent
        else ["child.txt:1: peft==0.12.0 # child", "requirements.txt:2: include incomplete"]
    )
    _facts(result, expected, diagnostics)
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            False, frozenset({"requirements.txt", "child.txt"}), frozenset(expected)
        )
    }


def test_c18_shared_child_preserves_root_order_duplicates_and_physical_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "requirements-a.txt": "-r shared.txt\n-r shared.txt\ntorch>=2 # loose\n",
            "requirements-z.txt": "-r shared.txt\npeft==0.12.0 # pin\n",
            "shared.txt": "PyTorch==2.5.1 # alias\ntorch==2.5.1 # duplicate package\n",
        },
    )
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert (
        scanner.reads
        == scanner.candidates
        == ["requirements-a.txt", "shared.txt", "requirements-z.txt"]
    )
    shared = [
        _declaration(source="shared.txt", display="PyTorch"),
        _declaration(source="shared.txt", line=2),
    ]
    loose = _declaration(specifier=">=2", exact=None, source="requirements-a.txt", line=3)
    peft = _declaration("peft", "==0.12.0", "0.12.0", "requirements-z.txt", 2)
    _facts(
        result,
        [*shared, loose, peft],
        [],
        locks=[Lockfile("requirements-z.txt", frozenset({"torch", "peft"}))],
    )
    assert graph.closures == {
        "requirements-a.txt": _RequirementsClosure(
            True, frozenset({"requirements-a.txt", "shared.txt"}), frozenset([*shared, loose])
        ),
        "requirements-z.txt": _RequirementsClosure(
            True, frozenset({"requirements-z.txt", "shared.txt"}), frozenset([*shared, peft])
        ),
    }
    assert len(graph.nodes["requirements-a.txt"].events) == 2


@pytest.mark.parametrize("other", ["exact", "loose", "bad", "cycle", "missing", "excluded"])
def test_c19_c25_comment_recovery_only_repairs_its_own_closure_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, other: str
) -> None:
    child = "torch==2.5.1 # captured\n"
    extra = {
        "exact": "peft==0.12.0 # second\n",
        "loose": "peft>=0.12 # second\n",
        "bad": "???\n",
        "cycle": "-r ../requirements.txt\n",
        "missing": "-r absent.txt\n",
        "excluded": "-r ../.venv/hidden.txt\n",
    }[other]
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/child.txt\n",
            "deps/child.txt": child + extra,
            ".venv/hidden.txt": "peft==0.12.0 # hidden\n",
        },
    )
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    reached = "deps/absent.txt" if other == "missing" else ".venv/hidden.txt"
    assert scanner.candidates == ["requirements.txt", "deps/child.txt"] + (
        [reached] if other in {"missing", "excluded"} else []
    )
    assert scanner.reads == ["requirements.txt", "deps/child.txt"] + (
        [reached] if other == "missing" else []
    )
    expected = [_declaration(source="deps/child.txt")]
    if other in {"exact", "loose"}:
        expected.append(
            _declaration(
                "peft",
                "==0.12.0" if other == "exact" else ">=0.12",
                "0.12.0" if other == "exact" else None,
                "deps/child.txt",
                2,
            )
        )
    reason = {
        "bad": "???",
        "cycle": "include cycle",
        "missing": "include unreadable",
        "excluded": "include unreadable",
    }.get(other)
    diagnostics = (
        []
        if reason is None
        else [f"deps/child.txt:2: {reason}", "requirements.txt:1: include incomplete"]
    )
    locks = [Lockfile("requirements.txt", frozenset({"torch", "peft"}))] if other == "exact" else []
    _facts(
        result,
        expected,
        diagnostics,
        locks=locks,
        issues={"deps/absent.txt": "unreadable"} if other == "missing" else {},
    )
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            other in {"exact", "loose"},
            frozenset({"requirements.txt", "deps/child.txt"}),
            frozenset(expected),
        )
    }


@pytest.mark.parametrize("shallow", ["none", "later", "earlier"])
def test_c20_comment_credit_does_not_rewrite_depth_frontier_or_root_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shallow: str
) -> None:
    deep = "requirements-z.txt" if shallow == "earlier" else "requirements-a.txt"
    shallow_root = "requirements-a.txt" if shallow == "earlier" else "requirements-z.txt"
    files = {deep: "torch==2.5.1 # root\n-r deps/1.txt\n"}
    files.update({f"deps/{n}.txt": f"-r {n + 1}.txt\n" for n in range(1, 11)})
    files["deps/11.txt"] = "peft==0.12.0 # late\n"
    if shallow != "none":
        files[shallow_root] = "-r deps/11.txt\n"
    _write(tmp_path, files)
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    deep_reads = [deep, *[f"deps/{n}.txt" for n in range(1, 11)]]
    shallow_reads = [shallow_root, "deps/11.txt"] if shallow != "none" else []
    assert (
        scanner.reads
        == scanner.candidates
        == (shallow_reads + deep_reads if shallow == "earlier" else deep_reads + shallow_reads)
    )
    torch = _declaration(source=deep)
    peft = _declaration("peft", "==0.12.0", "0.12.0", "deps/11.txt")
    expected = (
        [peft, torch] if shallow == "earlier" else [torch, peft] if shallow == "later" else [torch]
    )
    diagnostics = [
        "deps/10.txt:1: include depth limit",
        *[f"deps/{n}.txt:1: include incomplete" for n in range(9, 0, -1)],
        f"{deep}:2: include incomplete",
    ]
    _facts(
        result,
        expected,
        diagnostics,
        frontier=("deps/11.txt",) if shallow == "none" else (),
        locks=[] if shallow == "none" else [Lockfile(shallow_root, frozenset({"peft"}))],
    )
    closures = {deep: _RequirementsClosure(False, frozenset(deep_reads), frozenset({torch}))}
    if shallow != "none":
        closures[shallow_root] = _RequirementsClosure(
            True, frozenset(shallow_reads), frozenset({peft})
        )
    assert graph.closures == closures
    assert [r for r, _ in graph.after_roots] == (
        [deep] if shallow == "none" else ["requirements-a.txt", "requirements-z.txt"]
    )
    assert ("deps/11.txt" in graph.after_roots[0][1]) is (shallow == "earlier")


@pytest.mark.parametrize("manager", ["project", "optional", "poetry", "pipfile", "environment"])
def test_c21_shared_manager_strings_keep_their_existing_grammar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, manager: str
) -> None:
    sources = {
        "project": ("pyproject.toml", '[project]\ndependencies=["torch==2.5.1 # pin"]\n'),
        "optional": (
            "pyproject.toml",
            '[project.optional-dependencies]\ndev=["torch==2.5.1 # pin"]\n',
        ),
        "poetry": ("pyproject.toml", '[tool.poetry.dependencies]\ntorch="==2.5.1 # pin"\n'),
        "pipfile": ("Pipfile", '[packages]\ntorch="==2.5.1 # pin"\n'),
        "environment": (
            "environment.yml",
            'dependencies:\n  - pip:\n      - "torch==2.5.1 # pin"\n',
        ),
    }
    source, body = sources[manager]
    _write(tmp_path, {source: body, "requirements.txt": "peft==0.12.0 # graph only\n"})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == (
        [source, "requirements.txt"] if source == "pyproject.toml" else ["requirements.txt", source]
    )
    assert scanner.candidates == ["requirements.txt"]
    peft = _declaration("peft", "==0.12.0", "0.12.0")
    value_decls = (
        [_declaration(specifier="==2.5.1 # pin", exact=None, source=source, line=2)]
        if manager in {"poetry", "pipfile"}
        else []
    )
    expected = [*value_decls, peft] if manager == "poetry" else [peft, *value_decls]
    diagnostics = (
        []
        if value_decls
        else [f"{source}:{1 if manager == 'environment' else 2}: torch==2.5.1 # pin"]
    )
    formats = {
        "project": {"uv.lock", "poetry.lock"},
        "optional": {"uv.lock", "poetry.lock"},
        "poetry": {"poetry.lock"},
        "pipfile": {"Pipfile.lock"},
        "environment": {"conda-lock.yml"},
    }
    _facts(
        result,
        expected,
        diagnostics,
        locks=[Lockfile("requirements.txt", frozenset({"peft"}))],
        projects={source: frozenset(formats[manager])},
        issues={source: "unparsed_requirement"}
        if manager in {"project", "optional", "environment"}
        else {},
    )
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            True, frozenset({"requirements.txt"}), frozenset({peft})
        )
    }


def test_c26_c27_new_exact_keeps_format_origins_partial_credit_and_body_barriers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "pyproject.toml": '[project]\ndependencies=["numpy>=1"]\n',
            "uv.lock": '[[package]]\nname="numpy"\n[[package]]\nname=42\n',
            "requirements.txt": "torch==2.5.1 # positive\n-r absent.txt\n",
            "other/pyproject.toml": "project=42\n",
            "other/requirements.txt": "torch==2.4.0 # conflicting exact retained\n",
        },
    )
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == [
        "pyproject.toml",
        "other/pyproject.toml",
        "other/requirements.txt",
        "requirements.txt",
        "absent.txt",
        "uv.lock",
    ]
    assert scanner.candidates == ["other/requirements.txt", "requirements.txt", "absent.txt"]
    numpy = _declaration("numpy", ">=1", None, "pyproject.toml", 2)
    other = _declaration(specifier="==2.4.0", exact="2.4.0", source="other/requirements.txt")
    root = _declaration()
    _facts(
        result,
        [numpy, other, root],
        ["requirements.txt:2: include unreadable", "uv.lock:0: invalid package name"],
        locks=[
            Lockfile("uv.lock", frozenset({"numpy"}), "invalid_structure"),
            Lockfile("other/requirements.txt", frozenset({"torch"})),
        ],
        issues={"other/pyproject.toml": "invalid_structure", "absent.txt": "unreadable"},
        projects={"pyproject.toml": frozenset({"uv.lock", "poetry.lock"})},
        barriers={PurePosixPath("other")},
    )
    assert result.unverified_lock_paths([]) == {"numpy": ("uv.lock",)}
    assert result.qualified_lock_packages([("torch", "other/main.py")]) == frozenset(
        {"numpy", "torch"}
    )
    assert graph.closures == {
        "other/requirements.txt": _RequirementsClosure(
            True, frozenset({"other/requirements.txt"}), frozenset({other})
        ),
        "requirements.txt": _RequirementsClosure(
            False, frozenset({"requirements.txt"}), frozenset({root})
        ),
    }


@pytest.mark.parametrize(
    ("body", "specifier", "exact", "captured"),
    [
        ("torch==2.5.1 # pin\n", "==2.5.1", "2.5.1", True),
        ("torch>=2 # pin\n", ">=2", None, True),
        ("torch==2.5.1 # pin\n# veto\\\n", "==2.5.1", "2.5.1", False),
    ],
)
def test_c33_fresh_scan_recomputes_changed_comment_and_file_veto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: str,
    specifier: str,
    exact: str | None,
    captured: bool,
) -> None:
    _write(tmp_path, {"requirements.txt": "torch>=1 # initial\n"})
    initial, _, _ = _scan(tmp_path, monkeypatch)
    _facts(initial, [_declaration(specifier=">=1", exact=None)], [])
    _write(tmp_path, {"requirements.txt": body})
    result, scanner, graph = _scan(tmp_path, monkeypatch)
    assert scanner.reads == scanner.candidates == ["requirements.txt"]
    expected = [_declaration(specifier=specifier, exact=exact)] if captured else []
    _facts(
        result,
        expected,
        [] if captured else ["requirements.txt:1: torch==2.5.1 # pin"],
        locks=[Lockfile("requirements.txt", frozenset({"torch"}))] if captured and exact else [],
    )
    assert graph.closures == {
        "requirements.txt": _RequirementsClosure(
            captured, frozenset({"requirements.txt"}), frozenset(expected)
        )
    }
    _write(tmp_path, {"requirements.txt": "torch==2.5.1 # restored\n"})
    restored, _, _ = _scan(tmp_path, monkeypatch)
    _facts(
        restored, [_declaration()], [], locks=[Lockfile("requirements.txt", frozenset({"torch"}))]
    )


def test_c34_same_bytes_in_separate_paths_have_identical_complete_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = {
        "requirements.txt": "# header\n-r deps/pins.txt\n",
        "deps/pins.txt": "torch==2.5.1 # pin\npeft>=0.12 # loose\n",
    }
    expected = [
        _declaration(source="deps/pins.txt"),
        _declaration("peft", ">=0.12", None, "deps/pins.txt", 2),
    ]
    observations = []
    for dirname in ("first", "second"):
        root = tmp_path / dirname
        _write(root, files)
        before = {p: (root / p).read_bytes() for p in files}
        result, scanner, graph = _scan(root, monkeypatch)
        assert scanner.reads == scanner.candidates == ["requirements.txt", "deps/pins.txt"]
        _facts(result, expected, [])
        assert graph.closures == {
            "requirements.txt": _RequirementsClosure(True, frozenset(files), frozenset(expected))
        }
        assert {p: (root / p).read_bytes() for p in files} == before
        observations.append((asdict(result), graph.closures, scanner.reads))
    assert observations[0] == observations[1]
