"""D-M-PF A20-A39: Pipfile type facts retain complete rule evidence and priority."""

from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.deps import Lockfile
from reprollm.core.git import GitInfo
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule
from tests.unit.rules.test_pep621_requirement_failures import _expected


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


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


def _results(ctx: AuditContext) -> list[dict[str, Any]]:
    return [finding.model_dump(mode="json") for finding in LlmCriticalDepsPinnedRule().check(ctx)]


def _frontier(root: Path) -> None:
    files = {"depth/requirements.txt": "-r chain/0.txt\n"}
    for index in range(9):
        files[f"depth/chain/{index}.txt"] = f"-r {index + 1}.txt\n"
    files["depth/chain/9.txt"] = "-r ../pins.txt\n"
    _write(root, files)


def _warning() -> dict[str, Any]:
    return {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "WARNING",
        "status": "fail",
        "level": 0,
        "message": (
            "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
        ),
        "evidence": [
            {
                "kind": "file",
                "path": "Pipfile",
                "field": None,
                "line": 2,
                "value": ">=2",
                "expected": None,
                "note": "declared as >=2",
            }
        ],
        "fix_hint": "Pin torch exactly, e.g. `torch==<version>`.",
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
def test_noncritical_field_gap_has_repository_wide_scope_without_inventing_use(
    tmp_path: Path, section: str, coverage: str
) -> None:
    """A33/A36: unrelated requests cannot narrow the repository-wide missing-pin veto."""
    _write(
        tmp_path,
        {
            "app/requirements.txt": "torch>=2\nnumpy>=1\n",
            "unrelated/Pipfile": f"[{section}]\nrequests={{version=false}}\n",
        },
    )
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"unrelated/Pipfile": "invalid_structure"}
    assert _results(ctx) == [
        _expected(
            "numpy", ["unrelated/Pipfile"], path="app/requirements.txt", line=2, specifier=">=1"
        ),
        _expected("torch", ["unrelated/Pipfile"], path="app/requirements.txt"),
    ]
    assert [(d.name, d.specifier, d.exact_version) for d in ctx.deps.declarations] == [
        ("torch", ">=2", None),
        ("numpy", ">=1", None),
        ("requests", None, None),
    ]


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
def test_noncritical_failure_alone_keeps_no_use_applicability(
    tmp_path: Path, section: str, coverage: str
) -> None:
    _write(tmp_path, {"Pipfile": f"[{section}]\nrequests={{version=0}}\n"})
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"Pipfile": "invalid_structure"}
    rule = LlmCriticalDepsPinnedRule()
    assert not rule.applies(ctx)
    assert _results(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
def test_critical_named_declaration_remains_use_without_any_import(
    tmp_path: Path, section: str
) -> None:
    _write(tmp_path, {"Pipfile": f"[{section}]\ntorch={{version=false}}\n"})
    ctx = _context(tmp_path)
    assert ctx.pyscan.imports == []
    assert LlmCriticalDepsPinnedRule().applies(ctx)
    expected = _expected("torch", ["Pipfile"], path="Pipfile", line=2, specifier="(no version)")
    expected["evidence"][0]["note"] = "declared as unversioned"
    assert _results(ctx) == [expected]


@pytest.mark.parametrize(
    "credit",
    ["pipfile", "poetry", "pep621", "requirements", "conflicting", "lock-default", "lock-develop"],
)
@pytest.mark.parametrize("coverage", ["complete", "gap"])
def test_exact_and_qualified_credit_survive_partial_named_declarations(
    tmp_path: Path, credit: str, coverage: str
) -> None:
    files = {"Pipfile": "[packages]\ntorch={version=false}\n"}
    if credit == "pipfile":
        files["Pipfile"] += '[dev-packages]\ntorch="==2"\n'
    elif credit == "poetry":
        files["other/pyproject.toml"] = '[tool.poetry.dependencies]\ntorch="2"\n'
    elif credit == "pep621":
        files["pyproject.toml"] = '[project]\ndependencies=["torch==2"]\n'
    elif credit.startswith("lock-"):
        section = "default" if credit == "lock-default" else "develop"
        files["Pipfile.lock"] = '{"' + section + '": {"torch": {}}}\n'
    else:
        files["other/requirements.txt"] = "torch==2\n"
        if credit == "conflicting":
            files["requirements.txt"] = "torch==1\n"
    _write(tmp_path, files)
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"Pipfile": "invalid_structure"}
    assert _results(ctx) == []
    assert (LlmCriticalDepsPinnedRule().pass_skip_reason(ctx) is not None) == (coverage == "gap")
    assert any(d.name == "torch" and d.exact_version is None for d in ctx.deps.declarations)
    assert ctx.deps._uncertain_directories == set()
    assert ctx.deps._project_manifests["Pipfile"] == frozenset({"Pipfile.lock"})


@pytest.mark.parametrize("body", ["{broken", '{"default": []}'])
def test_associated_pipfile_lock_failure_wins_in_full(tmp_path: Path, body: str) -> None:
    _write(
        tmp_path,
        {
            "Pipfile": '[packages]\ntorch=">=2"\nrequests={version=false}\n',
            "Pipfile.lock": body,
        },
    )
    ctx = _context(tmp_path, "gap")
    assert ctx.deps.declaration_read_issues == {"Pipfile": "invalid_structure"}
    assert _results(ctx) == [
        _expected("torch", ["Pipfile.lock"], cause="lock", path="Pipfile", line=2)
    ]


def test_possible_origin_lock_and_python_gap_precede_global_body_failure(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "a/Pipfile": "[packages]\nrequests={version=false}\n",
            "b/Pipfile": "[packages]\n",
            "b/Pipfile.lock": '{"default": {"torch": {}}}\n',
        },
    )
    ctx = _context(tmp_path, "gap")
    assert ctx.deps.declaration_read_issues == {"a/Pipfile": "invalid_structure"}
    assert _results(ctx) == [_expected("torch", ["b/Pipfile.lock"], cause="origin")]


def test_body_failure_replaces_depth_branch_without_appending_frontier_paths(
    tmp_path: Path,
) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "control.py": "# heading\nimport torch\n",
            "other/Pipfile": "[dev-packages]\nrequests={version=false}\n",
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps.unexpanded_requirement_targets == ("depth/pins.txt",)
    assert _results(ctx) == [
        _expected("torch", ["other/Pipfile"], path="control.py", line=2, imported=True)
    ]


def test_parent_section_failure_retains_barrier_and_partial_other_section(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {"Pipfile": 'packages=false\n[dev-packages]\ntorch=">=2"\nrequests={version=false}\n'},
    )
    ctx = _context(tmp_path)
    assert ctx.deps.declaration_read_issues == {"Pipfile": "invalid_structure"}
    assert ctx.deps._uncertain_directories == {PurePosixPath(".")}
    assert ctx.deps.unparsed == []
    assert _results(ctx) == [_expected("torch", ["Pipfile"], path="Pipfile", line=3)]


def test_bad_values_in_both_sections_keep_one_distinct_source(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "Pipfile": '[packages]\ntorch=">=2"\nrequests={version=false}\n'
            "[dev-packages]\nflask={version=0}\nclick={version=[]}\n"
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps.declaration_read_issues == {"Pipfile": "invalid_structure"}
    assert [d.name for d in ctx.deps.declarations] == ["torch", "requests", "flask", "click"]
    assert ctx.deps.unparsed == []
    assert _results(ctx) == [_expected("torch", ["Pipfile"], path="Pipfile", line=2)]


def test_distinct_sorted_failures_enlarge_existing_body_finding_only(tmp_path: Path) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "control.py": "# heading\nimport torch\n",
            "a/pyproject.toml": "[tool.poetry.dependencies]\nrequests={version=false}\n",
            "m/Pipfile": "[packages]\nrequests={version=false}\n",
            "z/environment.yml": 'dependencies: [{pip: ["bad !!!"]}]\n',
        },
    )
    ctx = _context(tmp_path)
    assert _results(ctx) == [
        _expected(
            "torch",
            ["a/pyproject.toml", "m/Pipfile", "z/environment.yml"],
            path="control.py",
            line=2,
            imported=True,
        )
    ]


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize(
    "value",
    ['"2.5.1"', '"==2.*"', '""', '"bad !!!"', "false", "0", "[{version=false}]", '{git="public"}'],
)
def test_excluded_values_keep_entire_original_warning(
    tmp_path: Path, section: str, value: str
) -> None:
    _write(tmp_path, {"Pipfile": f'[{section}]\ntorch=">=2"\nrequests={value}\n'})
    ctx = _context(tmp_path)
    assert ctx.deps.declaration_read_issues == {}
    assert _results(ctx) == [_warning()]


def test_unvisited_category_does_not_join_existing_missing_pin_finding(tmp_path: Path) -> None:
    _write(tmp_path, {"Pipfile": '[packages]\ntorch=">=2"\n[docs]\nrequests={version=false}\n'})
    ctx = _context(tmp_path)
    assert ctx.deps.declaration_read_issues == {}
    assert [d.name for d in ctx.deps.declarations] == ["torch"]
    assert _results(ctx) == [_warning()]


@pytest.mark.parametrize(
    "case", ["wrong-manager", "missing-package", "unpaired-directory", "nearer-project"]
)
def test_a23_nonqualifying_locks_keep_inventory_without_granting_credit(
    tmp_path: Path, case: str
) -> None:
    """A23: a field gap grants no raw-lock credit, even when a lock lists torch."""
    files = {"Pipfile": '[packages]\ntorch=">=2"\nrequests={version=false}\n'}
    lock_path = "Pipfile.lock"
    packages = frozenset({"torch"})
    if case == "wrong-manager":
        lock_path = "poetry.lock"
        files[lock_path] = 'package=[{name="torch"}]\n'
    elif case == "missing-package":
        packages = frozenset({"numpy"})
        files[lock_path] = '{"default": {"numpy": {}}}\n'
    elif case == "unpaired-directory":
        lock_path = "other/Pipfile.lock"
        files[lock_path] = '{"default": {"torch": {}}}\n'
    else:
        files["Pipfile"] = "[packages]\nrequests={version=false}\n"
        files[lock_path] = '{"default": {"torch": {}}}\n'
        files["child/pyproject.toml"] = "[project]\ndependencies=[]\n"
        files["child/app.py"] = "import torch\n"
    _write(tmp_path, files)
    ctx = _context(tmp_path)
    origins = [(info.module, info.path) for info in ctx.pyscan.imports]
    assert ctx.deps.lockfiles == [Lockfile(lock_path, packages)]
    assert ctx.deps.qualified_lock_packages(origins) == frozenset()
    assert ctx.deps.unverified_lock_paths(origins) == {}
    assert ctx.deps._uncertain_directories == set()
    expected = (
        _expected("torch", ["Pipfile"], path="child/app.py", line=1, imported=True)
        if case == "nearer-project"
        else _expected("torch", ["Pipfile"], path="Pipfile", line=2)
    )
    assert _results(ctx) == [expected]
    assert ctx.deps.declaration_read_issues == {"Pipfile": "invalid_structure"}
