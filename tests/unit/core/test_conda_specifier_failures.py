"""R07-C D-M-CS: retained Conda names preserve capture when a specifier is lost."""

import json
from pathlib import Path, PurePosixPath

import pytest

from reprollm.core.deps import (
    DeclarationReadIssue,
    Declarations,
    DependencyDeclaration,
    Lockfile,
    scan_dependencies,
)
from reprollm.core.git import GitInfo
from reprollm.core.scanner import RepoScanner


class _Scanner(RepoScanner):
    def __init__(self, root: Path) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.reads: list[tuple[str, int]] = []
        self.list_calls = 0
        self.candidates: list[str] = []

    def analysis_files(self) -> list[str]:
        self.list_calls += 1
        return super().analysis_files()

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        self.reads.append((rel_path, max_bytes))
        return super().read_text(rel_path, max_bytes)

    def is_analysis_candidate(self, rel_path: str) -> bool:
        self.candidates.append(rel_path)
        return super().is_analysis_candidate(rel_path)


def _write(root: Path, files: dict[str, str], *, newline: str | None = None) -> dict[str, bytes]:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline=newline)
    return {name: (root / name).read_bytes() for name in files}


def _expected(
    declarations: tuple[DependencyDeclaration, ...] = (),
    diagnostics: tuple[str, ...] = (),
    *,
    projects: dict[str, frozenset[str]] | None = None,
    barriers: tuple[str, ...] = (),
    locks: tuple[Lockfile, ...] = (),
    issues: dict[str, DeclarationReadIssue] | None = None,
    frontier: tuple[str, ...] = (),
) -> Declarations:
    return Declarations(
        declarations=list(declarations),
        unparsed=list(diagnostics),
        lockfiles=list(locks),
        manifest_present=True,
        _project_manifests=(
            {"environment.yml": frozenset({"conda-lock.yml"})} if projects is None else projects
        ),
        _uncertain_directories={PurePosixPath(path) for path in barriers},
        declaration_read_issues={} if issues is None else issues,
        unexpanded_requirement_targets=frontier,
    )


def _capture(
    root: Path,
    expected: Declarations,
    reads: list[str],
    *,
    candidates: list[str] | None = None,
) -> Declarations:
    scanner = _Scanner(root)
    result = scan_dependencies(scanner)
    assert result == expected
    assert list(result.declaration_read_issues.items()) == list(
        expected.declaration_read_issues.items()
    )
    assert list(result._project_manifests.items()) == list(expected._project_manifests.items())
    assert scanner.reads == [(path, 512 * 1024) for path in reads]
    assert scanner.list_calls == 2
    assert scanner.candidates == ([] if candidates is None else candidates)
    return result


def test_retained_specifier_gap_keeps_complete_capture_and_exact_sibling(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - 'requests>=2,<3'\n  - pytorch==2.8.0\n", encoding="utf-8"
    )
    expected = Declarations(
        declarations=[
            DependencyDeclaration(
                "requests",
                "requests",
                "(unsupported conda declaration)",
                None,
                "environment.yml",
                1,
            ),
            DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 2),
        ],
        unparsed=["environment.yml:1: unsupported conda declaration"],
        lockfiles=[],
        manifest_present=True,
        _project_manifests={"environment.yml": frozenset({"conda-lock.yml"})},
        _uncertain_directories=set(),
        declaration_read_issues={"environment.yml": "unparsed_conda_specifier"},
        unexpanded_requirement_targets=(),
    )

    result = scan_dependencies(RepoScanner(tmp_path, GitInfo(is_repo=False)))

    assert result.declarations == expected.declarations
    assert result.unparsed == expected.unparsed
    assert result == expected


@pytest.mark.parametrize("path", ["environment.yml", "nested/environment.yaml"])
@pytest.mark.parametrize(
    "entry,name,display",
    [
        pytest.param("pytorch==2.8.0rc1", "torch", "pytorch", id="prerelease"),
        pytest.param("pytorch==2.8.0.dev1", "torch", "pytorch", id="development"),
        pytest.param("pytorch==2.8.0.post1", "torch", "pytorch", id="postrelease"),
        pytest.param("pytorch==2.8.0+cu121", "torch", "pytorch", id="local-version"),
        pytest.param("pytorch==1!2.8.0", "torch", "pytorch", id="epoch"),
        pytest.param("pytorch=2.8.*", "torch", "pytorch", id="version-wildcard"),
        pytest.param("pytorch==2.8.0=*cuda*", "torch", "pytorch", id="build-wildcard"),
        pytest.param("pytorch>=2,<3", "torch", "pytorch", id="compound-range"),
        pytest.param("pytorch>=3|<2", "torch", "pytorch", id="or-range"),
        pytest.param("pytorch==2.8.0,>=2", "torch", "pytorch", id="multiple-clauses"),
        pytest.param("pytorch[version='==2.8.0']", "torch", "pytorch", id="bracket-version"),
        pytest.param("pytorch[sha256='synthetic']", "torch", "pytorch", id="bracket-hash"),
        pytest.param(
            "pytorch[channel=conda-forge,subdir=linux-64]", "torch", "pytorch", id="bracket-origin"
        ),
        pytest.param("pytorch 2.8.0 py_0", "torch", "pytorch", id="legacy-triplet"),
        pytest.param("pytorch >= 2.8.0", "torch", "pytorch", id="spaced-operator"),
        pytest.param(
            "conda-forge ::pytorch==2.8.0", "conda-forge", "conda-forge", id="spaced-channel"
        ),
        pytest.param("pytorch /private/build", "torch", "pytorch", id="spaced-slash"),
        pytest.param("https://example.invalid/pkg", "https", "https", id="url-looking"),
        pytest.param("pytorch???", "torch", "pytorch", id="arbitrary-suffix"),
        pytest.param("pytorch==", "torch", "pytorch", id="empty-version"),
        pytest.param("pytorch=2.8.0=", "torch", "pytorch", id="empty-build"),
        pytest.param("pytorch=2.8.0=py_0=extra", "torch", "pytorch", id="extra-part"),
        pytest.param("pytorch==\uff12.\uff18.\uff10", "torch", "pytorch", id="unicode-version"),
        pytest.param("pytorch\u00e9", "torch", "pytorch", id="unicode-suffix"),
        pytest.param("pytorch^2[.]8$", "torch", "pytorch", id="regex-suffix"),
        pytest.param("pytorch\\specifier", "torch", "pytorch", id="backslash-suffix"),
    ],
)
def test_retained_suffix_records_only_new_fact_with_unchanged_declaration(
    tmp_path: Path, path: str, entry: str, name: str, display: str
) -> None:
    before = _write(tmp_path, {path: f"dependencies: [{json.dumps(entry)}]\n"})
    _capture(
        tmp_path,
        _expected(
            (
                DependencyDeclaration(
                    name, display, "(unsupported conda declaration)", None, path, 1
                ),
            ),
            (f"{path}:1: unsupported conda declaration",),
            projects={path: frozenset({"conda-lock.yml"})},
            issues={path: "unparsed_conda_specifier"},
        ),
        [path],
    )
    assert (tmp_path / path).read_bytes() == before[path]


@pytest.mark.parametrize("path", ["environment.yml", "nested/environment.yaml"])
@pytest.mark.parametrize(
    "entry,name,display,specifier,exact,diagnosed,issue",
    [
        pytest.param("pytorch>=2.8", "torch", "pytorch", ">=2.8", None, True, None, id="gte"),
        pytest.param("pytorch<=2.8", "torch", "pytorch", "<=2.8", None, True, None, id="lte"),
        pytest.param("pytorch!=2.8", "torch", "pytorch", "!=2.8", None, True, None, id="not-equal"),
        pytest.param("pytorch>2.8", "torch", "pytorch", ">2.8", None, True, None, id="gt"),
        pytest.param("pytorch<2.8", "torch", "pytorch", "<2.8", None, True, None, id="lt"),
        pytest.param(
            "pytorch~=2.8", "torch", "pytorch", "~=2.8", None, True, None, id="compatible"
        ),
        pytest.param("PyTorch", "torch", "PyTorch", None, None, False, None, id="bare-alias"),
        pytest.param(
            " pytorch=2.8.0 ", "torch", "pytorch", "=2.8.0", None, False, None, id="prefix"
        ),
        pytest.param(
            "pytorch==2.8.0",
            "torch",
            "pytorch",
            "==2.8.0",
            "2.8.0",
            False,
            None,
            id="exact-numeric",
        ),
        pytest.param(
            "pytorch=2.8.0=py_0+cpu",
            "torch",
            "pytorch",
            "=2.8.0=py_0+cpu",
            "2.8.0",
            False,
            None,
            id="single-equals-build",
        ),
        pytest.param(
            "pytorch==2.8.0=py_0+cpu",
            "torch",
            "pytorch",
            "==2.8.0=py_0+cpu",
            "2.8.0",
            False,
            None,
            id="double-equals-build",
        ),
        pytest.param(
            "pytorch==2.8.0\n",
            "torch",
            "pytorch",
            "==2.8.0",
            "2.8.0",
            False,
            None,
            id="terminal-newline",
        ),
        pytest.param("", None, None, None, None, True, "unparsed_conda", id="ce-empty"),
        pytest.param(" \t ", None, None, None, None, True, "unparsed_conda", id="ce-blank"),
        pytest.param("*", None, None, None, None, True, "unparsed_conda", id="ce-wildcard-name"),
        pytest.param(
            "conda-forge::pytorch==2.8.0",
            None,
            None,
            None,
            None,
            True,
            "unparsed_conda",
            id="ce-channel",
        ),
        pytest.param(
            "conda-forge/linux-64::pytorch==2.8.0",
            None,
            None,
            None,
            None,
            True,
            "unparsed_conda",
            id="ce-channel-subdir",
        ),
        pytest.param(
            "pytorch/path",
            None,
            None,
            None,
            None,
            True,
            "unparsed_conda",
            id="ce-slash",
        ),
        pytest.param(
            "pytorch\n==2.8.0",
            None,
            None,
            None,
            None,
            True,
            "unparsed_conda",
            id="ce-internal-newline",
        ),
    ],
)
def test_existing_range_credit_and_omission_routes_do_not_gain_specifier_issue(
    tmp_path: Path,
    path: str,
    entry: str,
    name: str | None,
    display: str | None,
    specifier: str | None,
    exact: str | None,
    diagnosed: bool,
    issue: DeclarationReadIssue | None,
) -> None:
    _write(tmp_path, {path: f"dependencies: [{json.dumps(entry)}]\n"})
    _capture(
        tmp_path,
        _expected(
            ()
            if name is None
            else (DependencyDeclaration(name, display or name, specifier, exact, path, 1),),
            (f"{path}:1: unsupported conda declaration",) if diagnosed else (),
            projects={path: frozenset({"conda-lock.yml"})},
            issues={} if issue is None else {path: issue},
        ),
        [path],
    )


@pytest.mark.parametrize(
    "entries,declarations,diagnostics,issue",
    [
        pytest.param(
            ["pytorch>=2,<3", "conda::numpy"],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:2: unsupported conda declaration",
            ),
            "unparsed_conda_specifier",
            id="specifier-before-omission",
        ),
        pytest.param(
            ["conda::numpy", "pytorch>=2,<3"],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    2,
                ),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:2: unsupported conda declaration",
            ),
            "unparsed_conda",
            id="omission-before-specifier",
        ),
        pytest.param(
            ["pytorch>=2,<3", {"pip": ["numpy=="]}],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            ("environment.yml:1: unsupported conda declaration", "environment.yml:2: numpy=="),
            "unparsed_conda_specifier",
            id="specifier-before-pip",
        ),
        pytest.param(
            [{"pip": ["numpy=="]}, "pytorch>=2,<3"],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    2,
                ),
            ),
            ("environment.yml:1: numpy==", "environment.yml:2: unsupported conda declaration"),
            "unparsed_requirement",
            id="pip-before-specifier",
        ),
        pytest.param(
            ["conda::numpy", {"pip": ["numpy=="]}, "pytorch>=2,<3"],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    3,
                ),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:2: numpy==",
                "environment.yml:3: unsupported conda declaration",
            ),
            "unparsed_conda",
            id="omission-before-pip-and-specifier",
        ),
        pytest.param(
            ["pytorch>=2.8", {"pip": ["  ", "numpy==1.0"]}, "pytorch>=2,<3"],
            (
                DependencyDeclaration("torch", "pytorch", ">=2.8", None, "environment.yml", 1),
                DependencyDeclaration("numpy", "numpy", "==1.0", "1.0", "environment.yml", 2),
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    3,
                ),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:3: unsupported conda declaration",
            ),
            "unparsed_conda_specifier",
            id="legacy-range-and-valid-pip-do-not-preempt",
        ),
    ],
)
def test_first_actual_failure_keeps_its_cause_and_all_partial_evidence(
    tmp_path: Path,
    entries: list[object],
    declarations: tuple[DependencyDeclaration, ...],
    diagnostics: tuple[str, ...],
    issue: DeclarationReadIssue,
) -> None:
    _write(tmp_path, {"environment.yml": json.dumps({"dependencies": entries})})
    _capture(
        tmp_path,
        _expected(declarations, diagnostics, issues={"environment.yml": issue}),
        ["environment.yml"],
    )


@pytest.mark.parametrize(
    "entries,declarations,diagnostic",
    [
        pytest.param(
            ["pytorch>=2,<3", False],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            "environment.yml:1: unsupported conda declaration",
            id="specifier-before-scalar-shape-error",
        ),
        pytest.param(
            [False, "pytorch>=2,<3"],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    2,
                ),
            ),
            "environment.yml:2: unsupported conda declaration",
            id="scalar-shape-error-before-specifier",
        ),
        pytest.param(
            ["pytorch>=2,<3", {"pip": [False, "numpy==1.0"]}],
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
                DependencyDeclaration("numpy", "numpy", "==1.0", "1.0", "environment.yml", 2),
            ),
            "environment.yml:1: unsupported conda declaration",
            id="specifier-before-pip-shape-error",
        ),
        pytest.param(
            [{"pip": [False, "numpy==1.0"]}, "pytorch>=2,<3"],
            (
                DependencyDeclaration("numpy", "numpy", "==1.0", "1.0", "environment.yml", 1),
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    2,
                ),
            ),
            "environment.yml:2: unsupported conda declaration",
            id="pip-shape-error-before-specifier",
        ),
    ],
)
def test_document_shape_precedes_specifier_gap_without_discarding_partial_capture(
    tmp_path: Path,
    entries: list[object],
    declarations: tuple[DependencyDeclaration, ...],
    diagnostic: str,
) -> None:
    _write(tmp_path, {"environment.yml": json.dumps({"dependencies": entries})})
    _capture(
        tmp_path,
        _expected(declarations, (diagnostic,), issues={"environment.yml": "invalid_structure"}),
        ["environment.yml"],
    )


def test_yaml_aliases_repeat_native_visits_but_not_unknown_installer_contents(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": (
                "dependencies:\n"
                "  - &retained 'pytorch>=2,<3'\n"
                "  - *retained\n"
                "  - unknown: [*retained, 'numpy==']\n"
                "  - &python\n"
                "    pip: ['requests==1.0']\n"
                "  - *python\n"
            )
        },
    )
    _capture(
        tmp_path,
        _expected(
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    2,
                ),
                DependencyDeclaration("requests", "requests", "==1.0", "1.0", "environment.yml", 4),
                DependencyDeclaration("requests", "requests", "==1.0", "1.0", "environment.yml", 5),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:2: unsupported conda declaration",
            ),
            issues={"environment.yml": "unparsed_conda_specifier"},
        ),
        ["environment.yml"],
    )


def test_cyclic_unknown_container_does_not_expand_or_hide_native_sibling(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {"environment.yml": "dependencies:\n  - &cycle [*cycle]\n  - 'pytorch>=2,<3'\n"},
    )
    _capture(
        tmp_path,
        _expected(
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    2,
                ),
            ),
            ("environment.yml:2: unsupported conda declaration",),
            issues={"environment.yml": "invalid_structure"},
        ),
        ["environment.yml"],
    )


@pytest.mark.parametrize(
    "document,projects,barriers,diagnostics,issues",
    [
        pytest.param("", {}, (), (), {}, id="empty-document"),
        pytest.param("null\n", {}, (), (), {}, id="null-document"),
        pytest.param("{}\n", {}, (), (), {}, id="missing-dependencies"),
        pytest.param(
            "dependencies: []\n",
            {"environment.yml": frozenset({"conda-lock.yml"})},
            (),
            (),
            {},
            id="empty-dependencies",
        ),
        pytest.param(
            "dependencies: null\n",
            {},
            (".",),
            (),
            {"environment.yml": "invalid_structure"},
            id="null-dependencies",
        ),
        pytest.param(
            "dependencies: 'pytorch>=2,<3'\n",
            {},
            (".",),
            ("environment.yml:0: invalid dependencies collection",),
            {"environment.yml": "invalid_structure"},
            id="wrong-collection",
        ),
        pytest.param(
            "dependencies:\n  - unknown: ['pytorch>=2,<3']\n  - sel(unix): 'pytorch>=2,<3'\n",
            {"environment.yml": frozenset({"conda-lock.yml"})},
            (),
            (),
            {},
            id="unknown-mappings-untraversed",
        ),
    ],
)
def test_absent_or_untraversed_native_strings_do_not_invent_specifier_gaps(
    tmp_path: Path,
    document: str,
    projects: dict[str, frozenset[str]],
    barriers: tuple[str, ...],
    diagnostics: tuple[str, ...],
    issues: dict[str, DeclarationReadIssue],
) -> None:
    _write(tmp_path, {"environment.yml": document})
    _capture(
        tmp_path,
        _expected(diagnostics=diagnostics, projects=projects, barriers=barriers, issues=issues),
        ["environment.yml"],
    )


@pytest.mark.parametrize(
    "body",
    [
        pytest.param(b"dependencies: ['pytorch>=2,<3']\x00\n", id="binary-body"),
        pytest.param(b"dependencies: ['pytorch>=2,<3']\xff\n", id="invalid-utf8"),
        pytest.param(b"dependencies: ['pytorch>=2,<3']\n#" + b"x" * (512 * 1024), id="read-limit"),
    ],
)
def test_unread_body_prevents_native_extraction_and_keeps_original_read_cause(
    tmp_path: Path, body: bytes
) -> None:
    path = tmp_path / "environment.yml"
    path.write_bytes(body)
    _capture(
        tmp_path,
        _expected(
            diagnostics=("environment.yml:0: unreadable",),
            projects={},
            barriers=(".",),
            issues={"environment.yml": "unreadable"},
        ),
        ["environment.yml"],
    )
    assert path.read_bytes() == body


def test_retained_name_preserves_exact_sibling_and_existing_paired_lock_credit(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies: ['pytorch>=2,<3', pytorch==2.8.0, numpy]\n",
            "conda-lock.yml": "package: [{name: pytorch}, {name: numpy}]\n",
            "child/environment.yaml": "dependencies: ['requests>=2,<3']\n",
        },
    )
    result = _capture(
        tmp_path,
        _expected(
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
                DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 2),
                DependencyDeclaration("numpy", "numpy", None, None, "environment.yml", 3),
                DependencyDeclaration(
                    "requests",
                    "requests",
                    "(unsupported conda declaration)",
                    None,
                    "child/environment.yaml",
                    1,
                ),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "child/environment.yaml:1: unsupported conda declaration",
            ),
            projects={
                "environment.yml": frozenset({"conda-lock.yml"}),
                "child/environment.yaml": frozenset({"conda-lock.yml"}),
            },
            locks=(Lockfile("conda-lock.yml", frozenset({"torch", "numpy"})),),
            issues={
                "environment.yml": "unparsed_conda_specifier",
                "child/environment.yaml": "unparsed_conda_specifier",
            },
        ),
        ["environment.yml", "child/environment.yaml", "conda-lock.yml"],
    )
    assert result.qualified_lock_packages([]) == frozenset({"torch", "numpy"})
    assert result.qualified_lock_packages([("requests", "train.py")]) == frozenset(
        {"torch", "numpy"}
    )
    assert result.qualified_lock_packages([("requests", "child/train.py")]) == frozenset(
        {"torch", "numpy"}
    )
    assert result.unverified_lock_paths([("torch", "train.py")]) == {}


def test_distinct_causes_and_ambiguous_environment_pair_keep_root_first_order(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "z/environment.yml": "dependencies: [{pip: ['numpy==']}]\n",
            "environment.yml": "dependencies: ['pytorch>=2,<3']\n",
            "environment.yaml": "dependencies: ['conda::numpy']\n",
            "conda-lock.yml": "package: [{name: pytorch}]\n",
            ".venv/environment.yml": "dependencies: ['ignored>=1,<2']\n",
            ".reprollm/runs/old/environment.yaml": "dependencies: ['ignored>=1,<2']\n",
        },
    )
    result = _capture(
        tmp_path,
        _expected(
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            (
                "environment.yaml:1: unsupported conda declaration",
                "environment.yml:1: unsupported conda declaration",
                "z/environment.yml:1: numpy==",
            ),
            projects={
                "environment.yaml": frozenset(),
                "environment.yml": frozenset(),
                "z/environment.yml": frozenset({"conda-lock.yml"}),
            },
            locks=(Lockfile("conda-lock.yml", frozenset({"torch"})),),
            issues={
                "environment.yaml": "unparsed_conda",
                "environment.yml": "unparsed_conda_specifier",
                "z/environment.yml": "unparsed_requirement",
            },
        ),
        ["environment.yaml", "environment.yml", "z/environment.yml", "conda-lock.yml"],
    )
    assert result.qualified_lock_packages([("torch", "train.py")]) == frozenset()
    assert result.unverified_lock_paths([("torch", "train.py")]) == {}


@pytest.mark.parametrize(
    "pin,exact,locks,credit",
    [
        pytest.param(
            "==2.8.0",
            "2.8.0",
            (Lockfile("requirements.txt", frozenset({"torch"})),),
            frozenset({"torch"}),
            id="exact-include",
        ),
        pytest.param(">=2.0", None, (), frozenset(), id="range-include"),
    ],
)
def test_existing_requirements_graph_credit_survives_retained_conda_gap(
    tmp_path: Path,
    pin: str,
    exact: str | None,
    locks: tuple[Lockfile, ...],
    credit: frozenset[str],
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/pins.txt\n",
            "deps/pins.txt": f"torch{pin}\n",
            "environment.yml": "dependencies: ['numpy>=1,<2']\n",
        },
    )
    result = _capture(
        tmp_path,
        _expected(
            (
                DependencyDeclaration("torch", "torch", pin, exact, "deps/pins.txt", 1),
                DependencyDeclaration(
                    "numpy", "numpy", "(unsupported conda declaration)", None, "environment.yml", 1
                ),
            ),
            ("environment.yml:1: unsupported conda declaration",),
            locks=locks,
            issues={"environment.yml": "unparsed_conda_specifier"},
        ),
        ["requirements.txt", "deps/pins.txt", "environment.yml"],
        candidates=["requirements.txt", "deps/pins.txt"],
    )
    assert result.qualified_lock_packages([]) == credit
    assert result.unverified_lock_paths([]) == {}


@pytest.mark.parametrize(
    "document,declarations,issue",
    [
        pytest.param(
            "dependencies:\n  - >-\n    pytorch\n    >=2,<3\n",
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            "unparsed_conda_specifier",
            id="folded-native-scalar",
        ),
        pytest.param(
            "dependencies:\n  - |\n    pytorch\n    >=2,<3\n",
            (),
            "unparsed_conda",
            id="literal-internal-newline",
        ),
        pytest.param(
            "dependencies:\n  - |\n    pytorch>=2,<3\n",
            (
                DependencyDeclaration(
                    "torch",
                    "pytorch",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            "unparsed_conda_specifier",
            id="literal-terminal-newline-stripped",
        ),
    ],
)
def test_decoded_yaml_scalar_uses_existing_native_traversal_boundary(
    tmp_path: Path,
    document: str,
    declarations: tuple[DependencyDeclaration, ...],
    issue: DeclarationReadIssue,
) -> None:
    _write(tmp_path, {"environment.yml": document})
    _capture(
        tmp_path,
        _expected(
            declarations,
            ("environment.yml:1: unsupported conda declaration",),
            issues={"environment.yml": issue},
        ),
        ["environment.yml"],
    )


@pytest.mark.parametrize("newline", [None, "\n", "\r\n"], ids=["native", "lf", "crlf"])
def test_repeated_captures_preserve_actual_input_bytes_and_omit_raw_suffix(
    tmp_path: Path, newline: str | None
) -> None:
    canary = "CS_CANARY_do_not_report_7c3f"
    source = "nested/environment.yaml"
    before = _write(
        tmp_path,
        {
            source: f"dependencies:\n  - 'pytorch=2.8.0=/private/{canary}'\n",
            ".reprollm/audit.json": '{"schema_version": 1, "historical": true}\n',
        },
        newline=newline,
    )
    expected = _expected(
        (
            DependencyDeclaration(
                "torch", "pytorch", "(unsupported conda declaration)", None, source, 1
            ),
        ),
        ("nested/environment.yaml:1: unsupported conda declaration",),
        projects={source: frozenset({"conda-lock.yml"})},
        issues={source: "unparsed_conda_specifier"},
    )
    captures = [_capture(tmp_path, expected, [source]) for _ in range(3)]
    assert captures[0] == captures[1] == captures[2]
    for capture in captures:
        assert canary not in repr(capture)
        assert "/private/" not in repr(capture)
        assert str(tmp_path) not in repr(capture)
    assert {name: (tmp_path / name).read_bytes() for name in before} == before


@pytest.mark.security
@pytest.mark.parametrize("outside", [False, True], ids=["inside", "outside"])
def test_real_source_alias_keeps_logical_gap_path_and_external_read_boundary(
    tmp_path: Path, outside: bool
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "outside.txt" if outside else root / "storage/body.txt"
    target.parent.mkdir(exist_ok=True)
    target.write_text("dependencies: ['requests>=2,<3']\n", encoding="utf-8")
    before = target.read_bytes()
    source = root / "environment.yml"
    try:
        source.symlink_to(target)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"real symlink unavailable: {type(exc).__name__}")
    original_link = source.readlink()

    _capture(
        root,
        _expected(
            ()
            if outside
            else (
                DependencyDeclaration(
                    "requests",
                    "requests",
                    "(unsupported conda declaration)",
                    None,
                    "environment.yml",
                    1,
                ),
            ),
            ("environment.yml:0: unreadable",)
            if outside
            else ("environment.yml:1: unsupported conda declaration",),
            projects={} if outside else {"environment.yml": frozenset({"conda-lock.yml"})},
            barriers=(".",) if outside else (),
            issues={"environment.yml": "unreadable" if outside else "unparsed_conda_specifier"},
        ),
        ["environment.yml"],
    )

    assert source.is_symlink() and source.readlink() == original_link
    assert target.read_bytes() == before
