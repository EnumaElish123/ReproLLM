"""R07-C D-M-CE: omitted Conda strings retain the captured dependency view."""

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


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _expected(
    declarations: tuple[DependencyDeclaration, ...] = (),
    diagnostics: tuple[str, ...] = (),
    *,
    projects: dict[str, frozenset[str]] | None = None,
    barriers: tuple[str, ...] = (),
    locks: tuple[Lockfile, ...] = (),
    issues: dict[str, DeclarationReadIssue] | None = None,
    frontier: tuple[str, ...] = (),
    manifest: bool = True,
) -> Declarations:
    return Declarations(
        declarations=list(declarations),
        unparsed=list(diagnostics),
        lockfiles=list(locks),
        manifest_present=manifest,
        _project_manifests=(
            {"environment.yml": frozenset({"conda-lock.yml"})} if projects is None else projects
        ),
        _uncertain_directories={PurePosixPath(path) for path in barriers},
        declaration_read_issues={} if issues is None else issues,
        unexpanded_requirement_targets=frontier,
    )


def _assert_capture(
    scanner: _Scanner,
    expected: Declarations,
    reads: list[str],
    *,
    candidates: list[str] | None = None,
) -> Declarations:
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


def test_empty_native_entry_records_omission_without_losing_siblings(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - pytorch==2.8.0\n  - ''\n  - numpy\n", encoding="utf-8"
    )

    result = scan_dependencies(RepoScanner(tmp_path, GitInfo(is_repo=False)))

    assert result.declarations == [
        DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 1),
        DependencyDeclaration("numpy", "numpy", None, None, "environment.yml", 3),
    ]
    assert result.unparsed == ["environment.yml:2: unsupported conda declaration"]
    assert result.declaration_read_issues == {"environment.yml": "unparsed_conda"}


@pytest.mark.parametrize("path", ["environment.yml", "nested/environment.yaml"])
@pytest.mark.parametrize(
    "entry,name,display,specifier,exact,diagnosed,issue",
    [
        pytest.param("", None, None, None, None, True, "unparsed_conda", id="empty"),
        pytest.param(" \t ", None, None, None, None, True, "unparsed_conda", id="ascii-blank"),
        pytest.param("\u2003", None, None, None, None, True, "unparsed_conda", id="unicode-blank"),
        pytest.param("*", None, None, None, None, True, "unparsed_conda", id="wildcard-name"),
        pytest.param(
            "[version='2.8.0']", None, None, None, None, True, "unparsed_conda", id="bracket-first"
        ),
        pytest.param(
            "==2.8.0", None, None, None, None, True, "unparsed_conda", id="operator-first"
        ),
        pytest.param(
            "\u00e9torch==2.8.0", None, None, None, None, True, "unparsed_conda", id="unicode-first"
        ),
        pytest.param(
            "torch\n==2.8.0", None, None, None, None, True, "unparsed_conda", id="inner-newline"
        ),
        pytest.param(
            "conda-forge::pytorch==2.8.0",
            None,
            None,
            None,
            None,
            True,
            "unparsed_conda",
            id="channel",
        ),
        pytest.param(
            "conda-forge/linux-64::pytorch==2.8.0",
            None,
            None,
            None,
            None,
            True,
            "unparsed_conda",
            id="channel-subdir",
        ),
        pytest.param(
            "/tmp/pkg", None, None, None, None, True, "unparsed_conda", id="leading-slash"
        ),
        pytest.param("torch/path", None, None, None, None, True, "unparsed_conda", id="head-slash"),
        pytest.param("pytorch", "torch", "pytorch", None, None, False, None, id="bare-name"),
        pytest.param("  PyTorch  ", "torch", "PyTorch", None, None, False, None, id="case-space"),
        pytest.param("pytorch=2.8.0", "torch", "pytorch", "=2.8.0", None, False, None, id="prefix"),
        pytest.param(
            "pytorch==2.8.0",
            "torch",
            "pytorch",
            "==2.8.0",
            "2.8.0",
            False,
            None,
            id="numeric-equality",
        ),
        pytest.param(
            "pytorch=2.8.0=cuda12.1",
            "torch",
            "pytorch",
            "=2.8.0=cuda12.1",
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
        pytest.param("torch>=2.0", "torch", "torch", ">=2.0", None, True, None, id="gte"),
        pytest.param("torch<=2.0", "torch", "torch", "<=2.0", None, True, None, id="lte"),
        pytest.param("torch!=2.0", "torch", "torch", "!=2.0", None, True, None, id="not-equal"),
        pytest.param("torch>2.0", "torch", "torch", ">2.0", None, True, None, id="gt"),
        pytest.param("torch<2.0", "torch", "torch", "<2.0", None, True, None, id="lt"),
        pytest.param("torch~=2.0", "torch", "torch", "~=2.0", None, True, None, id="compatible"),
        pytest.param(
            "torch>=2.0,<3",
            "torch",
            "torch",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="compound",
        ),
        pytest.param(
            "torch=2.8.*",
            "torch",
            "torch",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="version-wildcard",
        ),
        pytest.param(
            "torch==2.8.0=*cuda*",
            "torch",
            "torch",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="build-wildcard",
        ),
        pytest.param(
            "torch[version='==2.8.0']",
            "torch",
            "torch",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="bracket-suffix",
        ),
        pytest.param(
            "torch 2.8.0 py_0",
            "torch",
            "torch",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="positional-suffix",
        ),
        pytest.param(
            "https://example.invalid/pkg",
            "https",
            "https",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="url-looking",
        ),
        pytest.param(
            "conda-forge ::pytorch==2.8.0",
            "conda-forge",
            "conda-forge",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="space-before-channel",
        ),
        pytest.param(
            "torch /path",
            "torch",
            "torch",
            "(unsupported conda declaration)",
            None,
            True,
            "unparsed_conda_specifier",
            id="space-before-slash",
        ),
    ],
)
def test_native_string_boundary_retains_complete_capture(
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
    declarations = (
        ()
        if name is None
        else (DependencyDeclaration(name, display or name, specifier, exact, path, 1),)
    )
    _assert_capture(
        _Scanner(tmp_path),
        _expected(
            declarations,
            (f"{path}:1: unsupported conda declaration",) if diagnosed else (),
            projects={path: frozenset({"conda-lock.yml"})},
            issues={} if issue is None else {path: issue},
        ),
        [path],
    )


@pytest.mark.parametrize(
    "body,reason,diagnostics,declarations",
    [
        pytest.param(
            "dependencies: [false, 'conda-forge::torch', pytorch==2.8.0]\n",
            "invalid_structure",
            ("environment.yml:2: unsupported conda declaration",),
            (DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 3),),
            id="shape-before-omission",
        ),
        pytest.param(
            "dependencies: ['conda-forge::torch', false, pytorch==2.8.0]\n",
            "invalid_structure",
            ("environment.yml:1: unsupported conda declaration",),
            (DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 3),),
            id="shape-after-omission",
        ),
        pytest.param(
            "dependencies: ['conda-forge::torch', {pip: [false]}, pytorch==2.8.0]\n",
            "invalid_structure",
            ("environment.yml:1: unsupported conda declaration",),
            (DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 3),),
            id="pip-shape-after-omission",
        ),
        pytest.param(
            "dependencies: [{pip: ['torch==']}, 'conda-forge::torch']\n",
            "unparsed_requirement",
            ("environment.yml:1: torch==", "environment.yml:2: unsupported conda declaration"),
            (),
            id="pip-failure-first",
        ),
        pytest.param(
            "dependencies: ['conda-forge::torch', {pip: ['torch==']}]\n",
            "unparsed_conda",
            ("environment.yml:1: unsupported conda declaration", "environment.yml:2: torch=="),
            (),
            id="conda-omission-first",
        ),
        pytest.param(
            "dependencies: [{pip: ['', '  ', 'numpy==1.0']}, 'conda-forge::torch']\n",
            "unparsed_conda",
            ("environment.yml:2: unsupported conda declaration",),
            (DependencyDeclaration("numpy", "numpy", "==1.0", "1.0", "environment.yml", 1),),
            id="blank-pip-members-do-not-set-cause",
        ),
    ],
)
def test_original_first_cause_wins_without_losing_partial_declarations(
    tmp_path: Path,
    body: str,
    reason: DeclarationReadIssue,
    diagnostics: tuple[str, ...],
    declarations: tuple[DependencyDeclaration, ...],
) -> None:
    _write(tmp_path, {"environment.yml": body})
    _assert_capture(
        _Scanner(tmp_path),
        _expected(declarations, diagnostics, issues={"environment.yml": reason}),
        ["environment.yml"],
    )


def test_yaml_aliases_preserve_repeated_visits_and_outer_ordinals(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": (
                "dependencies:\n"
                "  - &native conda-forge::pytorch==2.8.0\n"
                "  - *native\n"
                "  - &installer {pip: ['numpy==1.0', 'torch==']}\n"
                "  - *installer\n"
                "  - pytorch==2.8.0\n"
            )
        },
    )
    _assert_capture(
        _Scanner(tmp_path),
        _expected(
            (
                DependencyDeclaration("numpy", "numpy", "==1.0", "1.0", "environment.yml", 3),
                DependencyDeclaration("numpy", "numpy", "==1.0", "1.0", "environment.yml", 4),
                DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 5),
            ),
            (
                "environment.yml:1: unsupported conda declaration",
                "environment.yml:2: unsupported conda declaration",
                "environment.yml:3: torch==",
                "environment.yml:4: torch==",
            ),
            issues={"environment.yml": "unparsed_conda"},
        ),
        ["environment.yml"],
    )


def test_cyclic_yaml_container_is_not_recursively_searched(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {"environment.yml": "dependencies: &deps\n  - *deps\n  - conda-forge::pytorch\n"},
    )
    _assert_capture(
        _Scanner(tmp_path),
        _expected(
            diagnostics=("environment.yml:2: unsupported conda declaration",),
            issues={"environment.yml": "invalid_structure"},
        ),
        ["environment.yml"],
    )


@pytest.mark.parametrize(
    "body,expected",
    [
        pytest.param(
            "dependencies:\n  - |\n    pytorch==2.8.0\n",
            _expected(
                (
                    DependencyDeclaration(
                        "torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 1
                    ),
                )
            ),
            id="trailing-newline-stripped",
        ),
        pytest.param(
            "dependencies:\n  - |-\n    pytorch\n    ==2.8.0\n",
            _expected(
                diagnostics=("environment.yml:1: unsupported conda declaration",),
                issues={"environment.yml": "unparsed_conda"},
            ),
            id="inner-newline-omitted",
        ),
        pytest.param(
            "dependencies:\n  - >-\n    pytorch\n    ==2.8.0\n",
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
                ("environment.yml:1: unsupported conda declaration",),
                issues={"environment.yml": "unparsed_conda_specifier"},
            ),
            id="folded-space-retains-name",
        ),
    ],
)
def test_yaml_scalar_decoding_preserves_capture_boundary(
    tmp_path: Path, body: str, expected: Declarations
) -> None:
    _write(tmp_path, {"environment.yml": body})
    _assert_capture(_Scanner(tmp_path), expected, ["environment.yml"])


@pytest.mark.parametrize(
    "body,projects,issues,barriers",
    [
        pytest.param("", {}, {}, (), id="empty-document"),
        pytest.param("null\n", {}, {}, (), id="null-document"),
        pytest.param("{}\n", {}, {}, (), id="missing-dependencies"),
        pytest.param(
            "dependencies: []\n",
            {"environment.yml": frozenset({"conda-lock.yml"})},
            {},
            (),
            id="empty-list",
        ),
        pytest.param(
            "dependencies: null\n",
            {},
            {"environment.yml": "invalid_structure"},
            (".",),
            id="null-dependencies",
        ),
        pytest.param(
            "dependencies: [false]\n",
            {"environment.yml": frozenset({"conda-lock.yml"})},
            {"environment.yml": "invalid_structure"},
            (),
            id="nonstring-member",
        ),
        pytest.param(
            "dependencies: [{pip: ['  ', '']}]\n",
            {"environment.yml": frozenset({"conda-lock.yml"})},
            {},
            (),
            id="blank-embedded-pip",
        ),
        pytest.param(
            "dependencies: [{other: ['conda-forge::torch']}, {sel(linux): '::torch'}]\n",
            {"environment.yml": frozenset({"conda-lock.yml"})},
            {},
            (),
            id="unknown-mappings",
        ),
    ],
)
def test_unvisited_strings_and_absence_do_not_create_conda_issue(
    tmp_path: Path,
    body: str,
    projects: dict[str, frozenset[str]],
    issues: dict[str, DeclarationReadIssue],
    barriers: tuple[str, ...],
) -> None:
    _write(tmp_path, {"environment.yml": body})
    _assert_capture(
        _Scanner(tmp_path),
        _expected(projects=projects, issues=issues, barriers=barriers),
        ["environment.yml"],
    )


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"\x00conda-forge::torch", id="binary-refusal"),
        pytest.param(b"\xff", id="decode-refusal"),
        pytest.param(b"x" * (512 * 1024 + 1), id="size-refusal"),
    ],
)
def test_existing_body_refusal_is_not_reclassified_or_retried(
    tmp_path: Path, content: bytes
) -> None:
    (tmp_path / "environment.yml").write_bytes(content)
    _assert_capture(
        _Scanner(tmp_path),
        _expected(
            diagnostics=("environment.yml:0: unreadable",),
            projects={},
            barriers=(".",),
            issues={"environment.yml": "unreadable"},
        ),
        ["environment.yml"],
    )


def test_root_first_order_and_dual_environment_lock_ambiguity_are_unchanged(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "environment.yaml": "dependencies: ['conda-forge::torch', numpy]\n",
            "environment.yml": "dependencies: [pytorch==2.8.0, 'conda-forge::numpy']\n",
            "a/environment.yml": "dependencies: ['conda-forge::other']\n",
            "conda-lock.yml": "package: [{name: pytorch}]\n",
        },
    )
    result = _assert_capture(
        _Scanner(tmp_path),
        _expected(
            (
                DependencyDeclaration("numpy", "numpy", None, None, "environment.yaml", 2),
                DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 1),
            ),
            (
                "environment.yaml:1: unsupported conda declaration",
                "environment.yml:2: unsupported conda declaration",
                "a/environment.yml:1: unsupported conda declaration",
            ),
            projects={
                "environment.yaml": frozenset(),
                "environment.yml": frozenset(),
                "a/environment.yml": frozenset({"conda-lock.yml"}),
            },
            locks=(Lockfile("conda-lock.yml", frozenset({"torch"})),),
            issues={
                "environment.yaml": "unparsed_conda",
                "environment.yml": "unparsed_conda",
                "a/environment.yml": "unparsed_conda",
            },
        ),
        ["environment.yaml", "environment.yml", "a/environment.yml", "conda-lock.yml"],
    )
    assert result.qualified_lock_packages([("torch", "train.py")]) == frozenset()
    assert result.unverified_lock_paths([("torch", "train.py")]) == {}


def test_omission_keeps_existing_child_project_without_adding_uncertain_barrier(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies: []\n",
            "nested/environment.yaml": "dependencies: ['conda-forge::other']\n",
            "conda-lock.yml": "package: [{name: pytorch}]\n",
        },
    )
    result = _assert_capture(
        _Scanner(tmp_path),
        _expected(
            diagnostics=("nested/environment.yaml:1: unsupported conda declaration",),
            projects={
                "environment.yml": frozenset({"conda-lock.yml"}),
                "nested/environment.yaml": frozenset({"conda-lock.yml"}),
            },
            locks=(Lockfile("conda-lock.yml", frozenset({"torch"})),),
            issues={"nested/environment.yaml": "unparsed_conda"},
        ),
        ["environment.yml", "nested/environment.yaml", "conda-lock.yml"],
    )
    assert result.qualified_lock_packages([("torch", "train.py")]) == frozenset({"torch"})
    assert result.qualified_lock_packages([("torch", "nested/train.py")]) == frozenset()
    assert result.qualified_lock_packages([]) == frozenset()
    assert result.unverified_lock_paths([("torch", "nested/train.py")]) == {}


@pytest.mark.parametrize(
    "pin,exact,locks,credit",
    [
        pytest.param(
            "==2.8.0",
            "2.8.0",
            (Lockfile("requirements.txt", frozenset({"torch"})),),
            frozenset({"torch"}),
            id="exact-closure",
        ),
        pytest.param(
            ">=2.0",
            None,
            (),
            frozenset(),
            id="range-closure-not-lock",
        ),
        pytest.param(
            "==2.*",
            None,
            (),
            frozenset(),
            id="wildcard-closure-not-lock",
        ),
    ],
)
def test_requirements_include_closure_and_lock_credit_survive_conda_omission(
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
            "environment.yml": "dependencies: ['', numpy]\n",
        },
    )
    result = _assert_capture(
        _Scanner(tmp_path),
        _expected(
            (
                DependencyDeclaration("torch", "torch", pin, exact, "deps/pins.txt", 1),
                DependencyDeclaration("numpy", "numpy", None, None, "environment.yml", 2),
            ),
            ("environment.yml:1: unsupported conda declaration",),
            locks=locks,
            issues={"environment.yml": "unparsed_conda"},
        ),
        ["requirements.txt", "deps/pins.txt", "environment.yml"],
        candidates=["requirements.txt", "deps/pins.txt"],
    )
    assert result.qualified_lock_packages([]) == credit
    assert result.unverified_lock_paths([]) == {}


def test_existing_requirements_depth_frontier_is_preserved_without_expansion(
    tmp_path: Path,
) -> None:
    files = {
        "requirements.txt": "-r deps/p0.txt\n",
        "environment.yml": "dependencies: ['conda-forge::other']\n",
        "deps/p10.txt": "torch==2.8.0\n",
    }
    files.update({f"deps/p{number}.txt": f"-r p{number + 1}.txt\n" for number in range(10)})
    _write(tmp_path, files)
    result = _assert_capture(
        _Scanner(tmp_path),
        _expected(
            diagnostics=(
                "deps/p9.txt:1: include depth limit",
                "deps/p8.txt:1: include incomplete",
                "deps/p7.txt:1: include incomplete",
                "deps/p6.txt:1: include incomplete",
                "deps/p5.txt:1: include incomplete",
                "deps/p4.txt:1: include incomplete",
                "deps/p3.txt:1: include incomplete",
                "deps/p2.txt:1: include incomplete",
                "deps/p1.txt:1: include incomplete",
                "deps/p0.txt:1: include incomplete",
                "requirements.txt:1: include incomplete",
                "environment.yml:1: unsupported conda declaration",
            ),
            issues={"environment.yml": "unparsed_conda"},
            frontier=("deps/p10.txt",),
        ),
        ["requirements.txt", *[f"deps/p{number}.txt" for number in range(10)], "environment.yml"],
        candidates=["requirements.txt", *[f"deps/p{number}.txt" for number in range(10)]],
    )
    assert result.qualified_lock_packages([]) == frozenset()
    assert (tmp_path / "deps/p10.txt").read_text(encoding="utf-8") == "torch==2.8.0\n"


def test_excluded_and_unrecognized_environment_files_are_not_read(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies: []\n",
            ".venv/environment.yml": "dependencies: ['conda-forge::torch']\n",
            ".reprollm/runs/old/environment.yaml": "dependencies: ['conda-forge::torch']\n",
            "env.yml": "dependencies: ['conda-forge::torch']\n",
            "environment.yaml.bak": "dependencies: ['conda-forge::torch']\n",
        },
    )
    _assert_capture(_Scanner(tmp_path), _expected(), ["environment.yml"])


def test_new_captures_preserve_input_bytes_and_do_not_disclose_omitted_text(tmp_path: Path) -> None:
    canary = "CE_SYNTHETIC_SECRET_TOKEN_082"
    files = {
        "environment.yml": f"dependencies: ['{canary}::pytorch==2.8.0', pytorch==2.8.0]\n",
        "historical-audit.json": '{"schema_version":"historical","note":"retain bytes"}\n',
    }
    _write(tmp_path, files)
    before = {name: (tmp_path / name).read_bytes() for name in files}
    expected = _expected(
        (DependencyDeclaration("torch", "pytorch", "==2.8.0", "2.8.0", "environment.yml", 2),),
        ("environment.yml:1: unsupported conda declaration",),
        issues={"environment.yml": "unparsed_conda"},
    )
    captures = [
        _assert_capture(_Scanner(tmp_path), expected, ["environment.yml"]) for _ in range(3)
    ]
    for result in captures:
        assert canary not in repr(result)
        assert str(tmp_path) not in repr(result)
    for name, content in before.items():
        assert (tmp_path / name).read_bytes() == content


def test_legacy_capture_defaults_stay_empty_and_independent() -> None:
    legacy = Declarations([], [], [], False, {}, set())
    fresh = Declarations()
    assert legacy == fresh
    assert legacy.declaration_read_issues is not fresh.declaration_read_issues
    legacy.declaration_read_issues["environment.yml"] = "unparsed_conda"
    assert fresh.declaration_read_issues == {}
    assert legacy.unexpanded_requirement_targets == fresh.unexpanded_requirement_targets == ()
