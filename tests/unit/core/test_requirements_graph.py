"""Public requirements closure and bounded include graph (R06-P, spec §12.2)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.deps import Declarations, scan_dependencies
from reprollm.core.git import GitInfo
from reprollm.core.scanner import MAX_READ_BYTES, RepoScanner
from reprollm.rules.env import LlmCriticalDepsPinnedRule, LockfilePresentRule
from reprollm.schemas.finding import FindingStatus, Severity

pytestmark = pytest.mark.security


class CountingScanner(RepoScanner):
    def __init__(self, root: Path) -> None:
        super().__init__(root, GitInfo(is_repo=False))
        self.requests: Counter[str] = Counter()

    def read_text(self, rel_path: str, max_bytes: int = MAX_READ_BYTES) -> str | None:
        self.requests[rel_path] += 1
        return super().read_text(rel_path, max_bytes)


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _symlink(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {type(exc).__name__}")


def _scan(root: Path) -> tuple[Declarations, CountingScanner]:
    scanner = CountingScanner(root)
    return scan_dependencies(scanner), scanner


def _locks(result: Declarations) -> dict[str, frozenset[str]]:
    return {lock.path: lock.packages for lock in result.lockfiles}


def _rows(result: Declarations) -> list[tuple[str, str, int]]:
    return [(d.name, d.source_file, d.line) for d in result.declarations]


def _diagnostic(result: Declarations, path: str, line: int, reason: str) -> None:
    assert f"{path}:{line}: {reason}" in result.unparsed


def _rule_states(root: Path, *, lock_present: bool, critical_pinned: bool) -> None:
    context = AuditContext(root)
    lock_findings = LockfilePresentRule().check(context)
    critical_findings = LlmCriticalDepsPinnedRule().check(context)
    assert bool(lock_findings) == (not lock_present)
    assert bool(critical_findings) == (not critical_pinned)
    for finding in lock_findings + critical_findings:
        assert finding.status == FindingStatus.FAIL
        assert finding.severity == Severity.WARNING


def _never_open(monkeypatch: pytest.MonkeyPatch, forbidden: Path) -> list[Path]:
    opened: list[Path] = []
    original = Path.open

    def traced(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.resolve() == forbidden:
            opened.append(path)
            raise AssertionError("outside content read attempted")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", traced)
    return opened


def _outside_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> tuple[Declarations, CountingScanner, Path, list[Path]]:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside-sentinel-private.txt"
    outside.write_text("openai==1.51.0 # SYNTHETIC_OUTSIDE_GRAPH_CANARY\n")
    if kind == "absolute":
        _write(root, {"requirements.txt": f"-r {outside}\n"})
    elif kind == "relative":
        _write(root, {"requirements.txt": f"--requirement ../{outside.name}\n"})
    elif kind == "child_symlink":
        _write(root, {"requirements.txt": "-r deps/linked.txt\n"})
        (root / "deps").mkdir()
        _symlink(root / "deps/linked.txt", outside)
    else:
        assert kind == "root_symlink"
        _symlink(root / "requirements.txt", outside)
    opened = _never_open(monkeypatch, outside)
    result, scanner = _scan(root)
    assert opened == []
    assert result.declarations == []
    assert _locks(result) == {}
    diagnostics = "\n".join(result.unparsed + scanner.warnings)
    assert str(outside) not in diagnostics
    assert outside.name not in diagnostics
    assert "SYNTHETIC_OUTSIDE_GRAPH_CANARY" not in diagnostics
    return result, scanner, root, opened


def test_root_referenced_child(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/base.txt\n",
            "deps/base.txt": "torch==2.5.1\n",
            "deps/unused.txt": "transformers==4.45.2\n",
        },
    )
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/base.txt", 1)]
    assert _locks(result) == {"requirements.txt": frozenset({"torch"})}
    assert result.unparsed == []
    assert scanner.requests == Counter({"requirements.txt": 1, "deps/base.txt": 1})
    _rule_states(tmp_path, lock_present=True, critical_pinned=True)


def test_normalized_internal_parent(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "--requirement deps/base.txt\n",
            "deps/base.txt": "torch==2.5.1\n-r ../common.txt\n",
            "common.txt": "numpy==2.1.2\n",
        },
    )
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/base.txt", 1), ("numpy", "common.txt", 1)]
    assert _locks(result) == {"requirements.txt": frozenset({"torch", "numpy"})}
    assert result.unparsed == []
    assert scanner.requests == Counter({"requirements.txt": 1, "deps/base.txt": 1, "common.txt": 1})


def test_unreferenced_sibling_cannot_repair(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/base.txt\n",
            "deps/base.txt": "torch>=2\n",
            "deps/unused.txt": "torch==2.5.1\n",
        },
    )
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/base.txt", 1)]
    assert not result.declarations[0].is_exact
    assert _locks(result) == {}
    assert scanner.requests["deps/unused.txt"] == 0
    _rule_states(tmp_path, lock_present=False, critical_pinned=False)


def test_repeated_normalized_edge(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/base.txt\n-r deps/../deps/base.txt\n",
            "deps/base.txt": "torch==2.5.1\n",
        },
    )
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/base.txt", 1)]
    assert _locks(result) == {"requirements.txt": frozenset({"torch"})}
    assert result.unparsed == []
    assert set(scanner.requests.values()) == {1}
    assert set(scanner.requests) == {"requirements.txt", "deps/base.txt"}


@pytest.mark.parametrize("shape", ["diamond", "layered_fanout"])
def test_diamond_shared_node(tmp_path: Path, shape: str) -> None:
    if shape == "diamond":
        files = {
            "requirements.txt": "-r deps/left.txt\n-r deps/right.txt\n",
            "deps/left.txt": "-r common.txt\n",
            "deps/right.txt": "-r common.txt\n",
            "deps/common.txt": "torch==2.5.1\n",
        }
        expected_rows = [("torch", "deps/common.txt", 1)]
    else:
        width = 5
        files = {"requirements.txt": "".join(f"-r graph/l1-n{node}.txt\n" for node in range(width))}
        for level in range(1, 11):
            for node in range(width):
                files[f"graph/l{level}-n{node}.txt"] = (
                    "torch==2.5.1\n"
                    if level == 10
                    else "".join(f"-r l{level + 1}-n{child}.txt\n" for child in range(width))
                )
        expected_rows = [("torch", f"graph/l10-n{node}.txt", 1) for node in range(width)]
    _write(tmp_path, files)
    result, scanner = _scan(tmp_path)
    assert _rows(result) == expected_rows
    assert _locks(result) == {"requirements.txt": frozenset({"torch"})}
    assert result.unparsed == []
    assert set(scanner.requests) == set(files)
    assert set(scanner.requests.values()) == {1}


def test_cycle_with_package(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch==2.5.1\n-r deps/a.txt\n",
            "deps/a.txt": "-r ../requirements.txt\n",
        },
    )
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [("torch", "requirements.txt", 1)]
    assert _locks(result) == {}
    _diagnostic(result, "deps/a.txt", 1, "include cycle")
    assert set(scanner.requests.values()) == {1}
    _rule_states(tmp_path, lock_present=False, critical_pinned=True)


def test_empty_cycle(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/a.txt\n",
            "deps/a.txt": "-r ../requirements.txt\n",
        },
    )
    result, _ = _scan(tmp_path)
    assert result.declarations == []
    assert _locks(result) == {}
    _diagnostic(result, "deps/a.txt", 1, "include cycle")


def test_empty_comment_child(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {"requirements.txt": "-r deps/a.txt\n", "deps/a.txt": "# comment only\n"},
    )
    result, _ = _scan(tmp_path)
    assert result.declarations == []
    assert _locks(result) == {}
    assert result.unparsed == []


def test_missing_child(tmp_path: Path) -> None:
    _write(tmp_path, {"requirements.txt": "torch==2.5.1\n-r deps/missing.txt\n"})
    result, _ = _scan(tmp_path)
    assert _rows(result) == [("torch", "requirements.txt", 1)]
    assert _locks(result) == {}
    _diagnostic(result, "requirements.txt", 2, "include unreadable")


def test_absolute_include(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, _, _ = _outside_case(tmp_path, monkeypatch, "absolute")
    _diagnostic(result, "requirements.txt", 1, "include unreadable")


def test_outside_relative_include(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, _, _ = _outside_case(tmp_path, monkeypatch, "relative")
    _diagnostic(result, "requirements.txt", 1, "include unreadable")


def test_outside_symlink_include(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, _, _ = _outside_case(tmp_path, monkeypatch, "child_symlink")
    _diagnostic(result, "requirements.txt", 1, "include unreadable")


def test_outside_root_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result, _, _, _ = _outside_case(tmp_path, monkeypatch, "root_symlink")
    _diagnostic(result, "requirements.txt", 0, "unreadable")


def test_legal_inside_source_alias(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r alias/base.txt\n",
            "storage/entry.txt": "torch==2.5.1\n-r sibling.txt\n",
            "alias/sibling.txt": "numpy==2.1.2\n",
            "storage/sibling.txt": "transformers==4.45.2\n",
        },
    )
    _symlink(tmp_path / "alias/base.txt", tmp_path / "storage/entry.txt")
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [
        ("torch", "alias/base.txt", 1),
        ("numpy", "alias/sibling.txt", 1),
    ]
    assert _locks(result) == {"requirements.txt": frozenset({"torch", "numpy"})}
    assert scanner.requests["storage/entry.txt"] == scanner.requests["storage/sibling.txt"] == 0


def test_permission_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/private.txt\n",
            "deps/private.txt": "torch==2.5.1\n",
        },
    )
    original = Path.open
    private = tmp_path / "deps/private.txt"

    def denied(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path == private:
            raise PermissionError(f"{private}: SYNTHETIC_UNSAFE_EXCEPTION_CANARY")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    result, scanner = _scan(tmp_path)
    assert _locks(result) == {}
    _diagnostic(result, "requirements.txt", 1, "include unreadable")
    diagnostics = "\n".join(result.unparsed + scanner.warnings)
    assert str(private) not in diagnostics
    assert "SYNTHETIC_UNSAFE_EXCEPTION_CANARY" not in diagnostics


@pytest.mark.parametrize("kind", ["binary", "oversized"])
def test_binary_or_oversized_child(tmp_path: Path, kind: str) -> None:
    _write(tmp_path, {"requirements.txt": "-r deps/large.txt\n"})
    (tmp_path / "deps").mkdir()
    content = b"torch==2.5.1\x00\n" if kind == "binary" else b"x" * (MAX_READ_BYTES + 1)
    (tmp_path / "deps/large.txt").write_bytes(content)
    result, _ = _scan(tmp_path)
    assert result.declarations == []
    assert _locks(result) == {}
    _diagnostic(result, "requirements.txt", 1, "include unreadable")


def test_child_malformed_line(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/base.txt\n",
            "deps/base.txt": "torch==2.5.1\nthis is not === a requirement!!!\n",
        },
    )
    result, _ = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/base.txt", 1)]
    assert _locks(result) == {}
    assert "deps/base.txt:2: this is not === a requirement!!!" in result.unparsed
    _diagnostic(result, "requirements.txt", 1, "include incomplete")


@pytest.mark.parametrize(
    "directive", ["-e .", "-r", "-rbase.txt", "--requirement=base.txt", '-r "base.txt"']
)
def test_unsupported_child_directive(tmp_path: Path, directive: str) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "-r deps/base.txt\n",
            "deps/base.txt": f"torch==2.5.1\n{directive}\n",
            "deps/base.txt.txt": "transformers==4.45.2\n",
        },
    )
    result, _ = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/base.txt", 1)]
    assert _locks(result) == {}
    if directive == "-e .":
        assert "deps/base.txt:2: -e ." in result.unparsed
    elif directive == "-r":
        _diagnostic(result, "deps/base.txt", 2, "include malformed")
    else:
        _diagnostic(result, "deps/base.txt", 2, "include unsupported syntax")
    _diagnostic(result, "requirements.txt", 1, "include incomplete")


def test_safe_legacy_noninclude_bytes(tmp_path: Path) -> None:
    lines = [
        "torch==2.5.1",
        "-e .",
        "--index-url https://pypi.example",
        "art==6.2 # existing inline comment",
        "tenacity==8.2.2 # existing inline comment",
        "git+https://example.invalid/repo.git",
    ]
    _write(tmp_path, {"requirements.txt": "\n".join(lines) + "\n"})
    result, _ = _scan(tmp_path)
    assert _rows(result) == [
        ("torch", "requirements.txt", 1),
        ("art", "requirements.txt", 4),
        ("tenacity", "requirements.txt", 5),
    ]
    assert _locks(result) == {}
    assert result.unparsed == [
        f"requirements.txt:{line}: {text}"
        for line, text in enumerate(lines, 1)
        if line in {2, 3, 6}
    ]


@pytest.mark.parametrize("layout", ["flat", "same_directory"])
def test_independent_roots_keep_aggregate_scope(tmp_path: Path, layout: str) -> None:
    if layout == "flat":
        files = {
            "requirements.txt": "torch>=2\n",
            "requirements-extra.txt": "torch==2.5.1\n",
        }
        expected = {"requirements-extra.txt": frozenset({"torch"})}
    else:
        files = {
            "requirements.txt": "torch>=2\n",
            "deps/requirements.txt": "-r base.txt\n",
            "deps/base.txt": "torch==2.5.1\n",
            "deps/requirements-unused.txt": "transformers==4.45.2\n",
        }
        expected = {
            "deps/requirements.txt": frozenset({"torch"}),
            "deps/requirements-unused.txt": frozenset({"transformers"}),
        }
    _write(tmp_path, files)
    result, _ = _scan(tmp_path)
    assert _locks(result) == expected
    _rule_states(tmp_path, lock_present=True, critical_pinned=True)


def test_between_scan_retarget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "project"
    root.mkdir()
    _write(
        root,
        {
            "requirements.txt": "-r deps/alias.txt\n",
            "deps/inside.txt": "torch==2.5.1\n",
        },
    )
    alias = root / "deps/alias.txt"
    _symlink(alias, root / "deps/inside.txt")
    outside = tmp_path / "outside-sentinel-private.txt"
    outside.write_text("openai==1.51.0 # SYNTHETIC_OUTSIDE_GRAPH_CANARY\n")
    opened = _never_open(monkeypatch, outside)
    scanner = CountingScanner(root)
    first = scan_dependencies(scanner)
    assert _locks(first) == {"requirements.txt": frozenset({"torch"})}
    assert _rows(first) == [("torch", "deps/alias.txt", 1)]
    alias.unlink()
    _symlink(alias, outside)
    second = scan_dependencies(scanner)
    assert second.declarations == []
    assert _locks(second) == {}
    _diagnostic(second, "requirements.txt", 1, "include unreadable")
    assert opened == []
    assert str(outside) not in "\n".join(second.unparsed + scanner.warnings)


def _chain(edges: int) -> dict[str, str]:
    files = {"requirements.txt": "-r deps/n1.txt\n"}
    for number in range(1, edges):
        files[f"deps/n{number}.txt"] = f"-r n{number + 1}.txt\n"
    files[f"deps/n{edges}.txt"] = "torch==2.5.1\n"
    return files


def test_chain_10_edges(tmp_path: Path) -> None:
    _write(tmp_path, _chain(10))
    result, scanner = _scan(tmp_path)
    assert _rows(result) == [("torch", "deps/n10.txt", 1)]
    assert _locks(result) == {"requirements.txt": frozenset({"torch"})}
    assert result.unparsed == []
    assert scanner.requests["deps/n10.txt"] == 1


def test_chain_11_edges(tmp_path: Path) -> None:
    _write(tmp_path, _chain(11))
    result, scanner = _scan(tmp_path)
    assert result.declarations == []
    assert _locks(result) == {}
    _diagnostic(result, "deps/n10.txt", 1, "include depth limit")
    assert scanner.requests["deps/n11.txt"] == 0


def _shared_budget(tmp_path: Path, *, short_edge_first: bool, shallow_root_first: bool) -> None:
    long_root = "requirements-z-long.txt" if shallow_root_first else "requirements-a-long.txt"
    shallow_root = (
        "requirements-a-shallow.txt" if shallow_root_first else "requirements-z-shallow.txt"
    )
    edges = ["-r deps/shared.txt\n", "-r chain/n1.txt\n"]
    if not short_edge_first:
        edges.reverse()
    files = {
        long_root: "".join(edges),
        shallow_root: "-r deps/shared.txt\n",
        "deps/shared.txt": "torch==2.5.1\n-r ../tail/terminal.txt\n",
        "tail/terminal.txt": "numpy==2.1.2\n",
    }
    for number in range(1, 9):
        files[f"chain/n{number}.txt"] = f"-r n{number + 1}.txt\n"
    files["chain/n9.txt"] = "-r ../deps/shared.txt\n"
    _write(tmp_path, files)
    result, scanner = _scan(tmp_path)
    assert _locks(result) == {shallow_root: frozenset({"torch", "numpy"})}
    assert Counter(_rows(result)) == Counter(
        {("torch", "deps/shared.txt", 1): 1, ("numpy", "tail/terminal.txt", 1): 1}
    )
    _diagnostic(result, "deps/shared.txt", 2, "include depth limit")
    assert set(scanner.requests) == set(files)
    assert set(scanner.requests.values()) == {1}
    # The independent shallow root can still establish global aggregate facts.
    _rule_states(tmp_path, lock_present=True, critical_pinned=True)


@pytest.mark.parametrize("shallow_root_first", [True, False])
def test_shared_budget_shallow_first(tmp_path: Path, shallow_root_first: bool) -> None:
    _shared_budget(tmp_path, short_edge_first=True, shallow_root_first=shallow_root_first)


@pytest.mark.parametrize("shallow_root_first", [True, False])
def test_shared_budget_long_first(tmp_path: Path, shallow_root_first: bool) -> None:
    _shared_budget(tmp_path, short_edge_first=False, shallow_root_first=shallow_root_first)
