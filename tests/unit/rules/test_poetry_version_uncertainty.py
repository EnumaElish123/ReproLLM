"""D-M-V T20-T31: explicit Poetry version gaps preserve complete rule contracts."""

from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
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


@pytest.mark.parametrize("name", ["requests", "python"])
@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
def test_noncritical_field_gap_has_repository_wide_scope_without_inventing_use(
    tmp_path: Path, name: str, coverage: str
) -> None:
    """T20/T23: independent captured uses receive the unchanged complete D-M finding."""
    _write(
        tmp_path,
        {
            "app/requirements.txt": "torch>=2\nnumpy>=1\n",
            "unrelated/pyproject.toml": f"[tool.poetry.dependencies]\n{name}={{version=false}}\n",
        },
    )
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"unrelated/pyproject.toml": "invalid_structure"}
    assert _results(ctx) == [
        _expected(
            "numpy",
            ["unrelated/pyproject.toml"],
            path="app/requirements.txt",
            line=2,
            specifier=">=1",
        ),
        _expected("torch", ["unrelated/pyproject.toml"], path="app/requirements.txt"),
    ]
    assert [(d.name, d.specifier, d.exact_version) for d in ctx.deps.declarations] == [
        ("requests" if name == "requests" else "python", None, None),
        ("torch", ">=2", None),
        ("numpy", ">=1", None),
    ]


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
def test_noncritical_failure_alone_keeps_no_use_applicability(
    tmp_path: Path, coverage: str
) -> None:
    """T21: the present wrong type cannot invent a critical package."""
    _write(tmp_path, {"pyproject.toml": "[tool.poetry.dependencies]\nrequests={version=0}\n"})
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"pyproject.toml": "invalid_structure"}
    rule = LlmCriticalDepsPinnedRule()
    assert not rule.applies(ctx)
    assert _results(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"


@pytest.mark.parametrize("credit", ["poetry", "pep621", "requirements", "conflicting", "lock"])
@pytest.mark.parametrize("coverage", ["complete", "gap"])
def test_exact_and_qualified_credit_survive_with_partial_named_declaration(
    tmp_path: Path, credit: str, coverage: str
) -> None:
    """T22/T24: a failure grants or revokes no exact or qualified lock credit."""
    files = {"pyproject.toml": "[tool.poetry.dependencies]\ntorch={version=false}\n"}
    if credit == "poetry":
        files["other/pyproject.toml"] = '[tool.poetry.dependencies]\ntorch="2"\n'
    elif credit == "pep621":
        files["pyproject.toml"] = (
            '[project]\ndependencies=["torch==2"]\n'
            "[tool.poetry.dependencies]\ntorch={version=false}\n"
        )
    elif credit == "lock":
        files["poetry.lock"] = 'package=[{name="torch"}]\n'
    else:
        files["other/requirements.txt"] = "torch==2\n"
        if credit == "conflicting":
            files["requirements.txt"] = "torch==1\n"
    _write(tmp_path, files)
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"pyproject.toml": "invalid_structure"}
    assert _results(ctx) == []
    assert (LlmCriticalDepsPinnedRule().pass_skip_reason(ctx) is not None) == (coverage == "gap")
    assert any(d.name == "torch" and d.exact_version is None for d in ctx.deps.declarations)
    assert ctx.deps._uncertain_directories == set()
    assert ctx.deps._project_manifests["pyproject.toml"] == frozenset(
        {"uv.lock", "poetry.lock"} if credit == "pep621" else {"poetry.lock"}
    )


@pytest.mark.parametrize("body", ["[broken\n", "package=[{}]\n"])
def test_associated_poetry_lock_failure_wins_in_full(tmp_path: Path, body: str) -> None:
    """T25: both decoder and supported structure failure precede lower D-M evidence."""
    _write(
        tmp_path,
        {
            "pyproject.toml": '[tool.poetry.dependencies]\ntorch=">=2"\nrequests={version=false}\n',
            "poetry.lock": body,
        },
    )
    ctx = _context(tmp_path, "gap")
    assert ctx.deps.declaration_read_issues == {"pyproject.toml": "invalid_structure"}
    assert _results(ctx) == [
        _expected("torch", ["poetry.lock"], cause="lock", path="pyproject.toml", line=2)
    ]


def test_possible_origin_lock_and_python_gap_precede_global_body_failure(tmp_path: Path) -> None:
    """T26: the complete D-L finding does not gain lower-priority body paths."""
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "a/pyproject.toml": "[tool.poetry.dependencies]\nrequests={version=false}\n",
            "b/pyproject.toml": "[tool.poetry]\n",
            "b/poetry.lock": 'package=[{name="torch"}]\n',
        },
    )
    ctx = _context(tmp_path, "gap")
    assert ctx.deps.declaration_read_issues == {"a/pyproject.toml": "invalid_structure"}
    assert _results(ctx) == [_expected("torch", ["b/poetry.lock"], cause="origin")]


def test_body_failure_replaces_depth_branch_without_appending_depth_paths(tmp_path: Path) -> None:
    """T27: D-M precedes D-G but leaves the captured frontier unchanged."""
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "control.py": "# heading\nimport torch\n",
            "other/pyproject.toml": "[tool.poetry.dependencies]\npython={version=false}\n",
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps.unexpanded_requirement_targets == ("depth/pins.txt",)
    assert _results(ctx) == [
        _expected("torch", ["other/pyproject.toml"], path="control.py", line=2, imported=True)
    ]


@pytest.mark.parametrize("earlier", ["shape", "pep621"])
def test_existing_same_file_cause_keeps_priority_and_original_diagnostics(
    tmp_path: Path, earlier: str
) -> None:
    """T28/T29: late field inspection never moves before an earlier extraction failure."""
    prefix = "dependencies=false" if earlier == "shape" else 'dependencies=["bad !!!"]'
    _write(
        tmp_path,
        {
            "pyproject.toml": (
                f"[project]\n{prefix}\n[tool.poetry.dependencies]\n"
                'torch=">=2"\nrequests={version=false}\n'
            ),
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps.declaration_read_issues == {
        "pyproject.toml": "invalid_structure" if earlier == "shape" else "unparsed_requirement"
    }
    assert ctx.deps.unparsed == ([] if earlier == "shape" else ["pyproject.toml:2: bad !!!"])
    assert _results(ctx) == [_expected("torch", ["pyproject.toml"], path="pyproject.toml", line=4)]


def test_multiple_bad_values_keep_all_declarations_and_one_source(tmp_path: Path) -> None:
    """T30: findings and source evidence are not duplicated for each invalid value."""
    _write(
        tmp_path,
        {
            "pyproject.toml": (
                '[tool.poetry.dependencies]\ntorch=">=2"\n'
                "requests={version=false}\npython={version=0}\nflask={version=[]}\n"
            ),
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps.declaration_read_issues == {"pyproject.toml": "invalid_structure"}
    assert [(d.name, d.line) for d in ctx.deps.declarations] == [
        ("torch", 2),
        ("requests", 3),
        ("python", 4),
        ("flask", 5),
    ]
    assert ctx.deps.unparsed == []
    assert _results(ctx) == [_expected("torch", ["pyproject.toml"], path="pyproject.toml", line=2)]


def test_distinct_sorted_failures_enlarge_existing_body_finding_only(tmp_path: Path) -> None:
    """T31: the original import stays first, followed by distinct sorted D-M files."""
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "control.py": "# heading\nimport torch\n",
            "a/Pipfile": "packages=false\n",
            "m/pyproject.toml": "[tool.poetry.dependencies]\nrequests={version=false}\n",
            "z/environment.yml": 'dependencies: [{pip: ["bad !!!"]}]\n',
        },
    )
    ctx = _context(tmp_path)
    assert _results(ctx) == [
        _expected(
            "torch",
            ["a/Pipfile", "m/pyproject.toml", "z/environment.yml"],
            path="control.py",
            line=2,
            imported=True,
        )
    ]
