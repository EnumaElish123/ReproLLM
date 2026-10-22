"""D-G consumer contracts: final depth gaps do not erase credit or earlier reasons."""

from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.deps import Declarations, DependencyDeclaration
from reprollm.core.git import GitInfo
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, body in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


def _frontier(root: Path, targets: tuple[str, ...] = ("pins.txt",)) -> list[str]:
    files = {"unrelated/requirements.txt": "-r chain/0.txt\n"}
    for index in range(9):
        files[f"unrelated/chain/{index}.txt"] = f"-r {index + 1}.txt\n"
    files["unrelated/chain/9.txt"] = "".join(f"-r ../{path}\n" for path in targets)
    _write(root, files)
    return [f"unrelated/{path}" for path in sorted(set(targets))]


def _context(root: Path, coverage: str = "complete") -> AuditContext:
    ctx = AuditContext(root)
    ctx._git = GitInfo(is_repo=False)
    if coverage != "complete":
        ctx._pyscan = PyScanResult(
            coverage_observed=coverage != "unavailable",
            python_candidate_count=2,
            python_selected_count=1,
            python_parsed_count=2 if coverage == "inconsistent" else 1,
            python_file_limit=1,
        )
    return ctx


def _evidence(
    path: str, note: str, *, line: int | None = None, value: str | None = None
) -> dict[str, Any]:
    return {
        "kind": "file",
        "path": path,
        "field": None,
        "line": line,
        "value": value,
        "expected": None,
        "note": note,
    }


def _expected(
    package: str,
    targets: list[str],
    *,
    cause: str = "depth",
    path: str = "requirements.txt",
    line: int = 1,
    specifier: str = ">=2",
    imported: bool = False,
) -> dict[str, Any]:
    messages = {
        "depth": "a supported requirements include was not expanded within the depth budget",
        "lock": "an associated format lock could not be read or parsed",
        "origin": (
            "Python analysis is incomplete or unavailable and a captured format lock "
            "lists the package"
        ),
        "body": "a dependency declaration body could not be read or parsed",
    }
    notes = {
        "depth": "include target unexpanded at the depth limit",
        "lock": "associated; lock package contents unverified",
        "origin": "listed; import-origin credit unverified",
        "body": "possible exact declaration unverified",
    }
    hints = {
        "depth": (
            f"Review {package} declarations and unexpanded requirements include targets; "
            "restructure the supported include graph within the depth budget before deciding "
            "that exact pin evidence is absent."
        ),
        "lock": (
            f"Review {package} declarations and associated format-lock files; restore readable, "
            "valid lock contents before deciding that exact pin evidence is absent."
        ),
        "origin": (
            f"Review {package} declarations and format-lock origins; complete Python analysis "
            "before deciding that exact pin evidence is absent."
        ),
        "body": (
            f"Review {package} declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        ),
    }
    return {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 0,
        "message": (
            f"{package} is used; {messages[cause]}, so missing pin evidence is not established"
        ),
        "evidence": [
            _evidence(
                path,
                "imported" if imported else f"declared as {specifier}",
                line=line,
                value=None if imported else specifier,
            ),
            *[_evidence(target, f"{package} {notes[cause]}") for target in targets],
        ],
        "fix_hint": hints[cause],
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


def _results(ctx: AuditContext) -> list[dict[str, Any]]:
    return [finding.model_dump(mode="json") for finding in LlmCriticalDepsPinnedRule().check(ctx)]


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
@pytest.mark.parametrize("target_body", [None, "", "torch>=1\n", "torch==2.5.1\n"])
def test_depth_gap_keeps_full_skip_independent_of_coverage_and_unread_target_contents(
    tmp_path: Path, coverage: str, target_body: str | None
) -> None:
    _write(tmp_path, {"requirements.txt": "torch>=2\n"})
    targets = _frontier(tmp_path)
    if target_body is not None:
        _write(tmp_path, {targets[0]: target_body})
    ctx = _context(tmp_path, coverage)

    assert _results(ctx) == [_expected("torch", targets)]
    assert ctx.deps.declaration_read_issues == {}
    assert not any(declaration.is_exact for declaration in ctx.deps.declarations)


def test_unrelated_depth_frontier_affects_all_remaining_packages_and_sorts_target_evidence(
    tmp_path: Path,
) -> None:
    _write(tmp_path, {"requirements.txt": "torch>=2\nnumpy>=1\n"})
    targets = _frontier(tmp_path, ("z.txt", "a.txt", "z.txt"))

    assert _results(_context(tmp_path)) == [
        _expected("numpy", targets, line=2, specifier=">=1"),
        _expected("torch", targets),
    ]


def test_unreached_excluded_target_is_unknown_without_claiming_file_existence(
    tmp_path: Path,
) -> None:
    _write(tmp_path, {"requirements.txt": "torch>=2\n"})
    targets = _frontier(tmp_path, (".venv/missing.txt",))

    assert _results(_context(tmp_path)) == [_expected("torch", targets)]
    assert not (tmp_path / targets[0]).exists()


@pytest.mark.parametrize("origin", ["import", "conda-alias"])
def test_depth_gap_retains_first_import_or_canonical_conda_evidence(
    tmp_path: Path, origin: str
) -> None:
    targets = _frontier(tmp_path)
    if origin == "import":
        _write(tmp_path, {"app.py": "import torch\n"})
        expected = _expected("torch", targets, path="app.py", imported=True)
    else:
        _write(tmp_path, {"environment.yml": "dependencies:\n - pytorch=2\n"})
        expected = _expected("torch", targets, path="environment.yml", specifier="=2")

    assert _results(_context(tmp_path)) == [expected]


@pytest.mark.parametrize("credit", ["root-exact", "unrelated-exact", "conflicting-exact", "lock"])
@pytest.mark.parametrize("coverage", ["complete", "gap"])
def test_positive_credit_wins_over_depth_and_other_uncertainty(
    tmp_path: Path, credit: str, coverage: str
) -> None:
    _frontier(tmp_path)
    _write(tmp_path, {"requirements.txt": "torch>=2\n", "broken/Pipfile": "packages=false\n"})
    if credit == "lock":
        _write(
            tmp_path,
            {
                "pyproject.toml": '[project]\ndependencies=["torch>=2"]\n',
                "uv.lock": 'package=[{name="torch"},{}]\n',
            },
        )
    else:
        source = "requirements.txt" if credit == "root-exact" else "pins/requirements.txt"
        _write(tmp_path, {source: "torch==2.5.1\n"})
        if credit == "conflicting-exact":
            _write(tmp_path, {"requirements.txt": "torch==2.4.0\n"})
    ctx = _context(tmp_path, coverage)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.check(ctx) == []
    assert rule.applies(ctx)
    assert (rule.pass_skip_reason(ctx) is not None) == (coverage == "gap")


def test_exact_credit_removes_only_its_package_while_other_package_keeps_depth_skip(
    tmp_path: Path,
) -> None:
    targets = _frontier(tmp_path)
    _write(tmp_path, {"requirements.txt": "torch==2.5.1\nnumpy>=1\n"})

    assert _results(_context(tmp_path)) == [_expected("numpy", targets, line=2, specifier=">=1")]


@pytest.mark.parametrize("lock_body", ["[broken\n", "package=[{}]\n"])
def test_associated_lock_failure_keeps_entire_finding_before_body_and_depth(
    tmp_path: Path, lock_body: str
) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "pyproject.toml": '[project]\ndependencies=["torch>=2"]\n',
            "uv.lock": lock_body,
            "broken/Pipfile": "packages=false\n",
        },
    )
    ctx = _context(tmp_path, "gap")

    assert _results(ctx) == [
        _expected("torch", ["uv.lock"], cause="lock", path="pyproject.toml", line=2)
    ]


def test_unverified_origin_keeps_entire_finding_before_body_and_depth(tmp_path: Path) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "nested/pyproject.toml": "[project]\n",
            "nested/uv.lock": 'package=[{name="torch"}]\n',
            "broken/Pipfile": "packages=false\n",
        },
    )

    assert _results(_context(tmp_path, "gap")) == [
        _expected("torch", ["nested/uv.lock"], cause="origin")
    ]


@pytest.mark.parametrize("body", ["[broken\n", "packages=false\n", "bad\x00\n"])
def test_body_syntax_structure_or_read_failure_keeps_entire_finding_before_depth(
    tmp_path: Path, body: str
) -> None:
    _frontier(tmp_path)
    _write(tmp_path, {"requirements.txt": "torch>=2\n", "broken/Pipfile": body})

    assert _results(_context(tmp_path)) == [_expected("torch", ["broken/Pipfile"], cause="body")]


@pytest.mark.parametrize("coverage", ["complete", "unavailable"])
def test_depth_frontier_does_not_invent_use_or_change_empty_result_python_veto(
    tmp_path: Path, coverage: str
) -> None:
    _frontier(tmp_path)
    _write(tmp_path, {"requirements.txt": "requests>=2\n"})
    ctx = _context(tmp_path, coverage)
    rule = LlmCriticalDepsPinnedRule()

    assert not rule.applies(ctx)
    assert rule.check(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"
    assert (rule.pass_skip_reason(ctx) is not None) == (coverage != "complete")


def test_manual_legacy_positional_declarations_keep_the_existing_warning(tmp_path: Path) -> None:
    declaration = DependencyDeclaration("torch", "torch", ">=2", None, "requirements.txt", 1)
    ctx = _context(tmp_path)
    ctx._deps = Declarations([declaration], [], [], True, {}, set(), {})
    expected = _expected("torch", [])
    expected.update(
        severity="WARNING",
        status="fail",
        message="torch is used but not pinned to an exact version (suggestion: torch==<version>)",
        fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
    )

    assert _results(ctx) == [expected]
