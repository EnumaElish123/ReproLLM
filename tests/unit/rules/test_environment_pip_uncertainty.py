"""D-M-E A09/A18-A28: embedded-pip failures retain established consumer contracts."""

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


@pytest.mark.parametrize("credit", ["pip", "conda", "pep621", "unrelated", "conflicting", "lock"])
@pytest.mark.parametrize("coverage", ["complete", "gap"])
def test_exact_and_qualified_credit_survive_embedded_failure_and_python_veto(
    tmp_path: Path, credit: str, coverage: str
) -> None:
    """A19/A20/A27: neither a new cause nor a Python gap revokes positive credit."""
    _write(tmp_path, {"environment.yml": 'dependencies: [{pip: ["torch>=2", "bad !!!"]}]\n'})
    if credit == "pip":
        _write(
            tmp_path,
            {"environment.yml": 'dependencies: [{pip: ["torch>=2", "bad !!!", "torch==2"]}]\n'},
        )
    elif credit == "conda":
        _write(
            tmp_path,
            {"environment.yml": 'dependencies: [pytorch==2, {pip: ["torch>=2", "bad !!!"]}]\n'},
        )
    elif credit == "pep621":
        _write(tmp_path, {"pyproject.toml": '[project]\ndependencies=["torch==2"]\n'})
    elif credit == "lock":
        _write(tmp_path, {"conda-lock.yml": "package: [{name: pytorch}]\n"})
    else:
        _write(tmp_path, {"other/requirements.txt": "torch==2\n"})
        if credit == "conflicting":
            _write(tmp_path, {"requirements.txt": "torch==1\n"})
    ctx = _context(tmp_path, coverage)
    assert ctx.deps.declaration_read_issues == {"environment.yml": "unparsed_requirement"}
    assert _results(ctx) == []
    assert (LlmCriticalDepsPinnedRule().pass_skip_reason(ctx) is not None) == (coverage == "gap")


@pytest.mark.parametrize("qualifier", ["declaration", "import"])
def test_unique_environment_keeps_lock_pairing_and_credit(tmp_path: Path, qualifier: str) -> None:
    """A20: a failed pip sibling does not become a project ownership barrier."""
    _write(
        tmp_path,
        {
            "environment.yaml": 'dependencies: [{pip: ["bad !!!"]}]\n',
            "conda-lock.yml": "package: [{name: torch}]\n",
        },
    )
    if qualifier == "declaration":
        _write(
            tmp_path,
            {"environment.yaml": 'dependencies: [{pip: ["torch>=2", "bad !!!"]}]\n'},
        )
    else:
        _write(tmp_path, {"control.py": "import torch\n"})
    ctx = _context(tmp_path)
    assert ctx.deps._project_manifests == {"environment.yaml": frozenset({"conda-lock.yml"})}
    assert ctx.deps._uncertain_directories == set()
    assert _results(ctx) == []


def test_two_environment_basenames_keep_ambiguous_lock_pairing(tmp_path: Path) -> None:
    """A21: the new cause does not repair the existing same-directory ambiguity."""
    _write(
        tmp_path,
        {
            "environment.yml": 'dependencies: [{pip: ["torch>=2", "bad !!!"]}]\n',
            "environment.yaml": "dependencies: []\n",
            "conda-lock.yml": "package: [{name: torch}]\n",
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps._project_manifests == {
        "environment.yaml": frozenset(),
        "environment.yml": frozenset(),
    }
    assert _results(ctx) == [_expected("torch", ["environment.yml"], path="environment.yml")]


@pytest.mark.parametrize("lock_body", ["[broken\n", "package: [{}]\n"])
def test_associated_conda_lock_failure_precedes_new_body_cause(
    tmp_path: Path, lock_body: str
) -> None:
    """A22: D-F/D-S findings exclude lower-priority declaration-failure evidence."""
    _write(
        tmp_path,
        {
            "environment.yml": 'dependencies: [{pip: ["torch>=2", "bad !!!"]}]\n',
            "conda-lock.yml": lock_body,
        },
    )
    assert _results(_context(tmp_path, "gap")) == [
        _expected("torch", ["conda-lock.yml"], cause="lock", path="environment.yml")
    ]


def test_each_package_keeps_its_own_exact_lock_origin_or_new_body_branch(tmp_path: Path) -> None:
    """A23/A28: the global cause cannot short-circuit the per-package priority loop."""
    _write(
        tmp_path,
        {
            "requirements.txt": "numpy==2\nvllm>=2\npeft>=2\n",
            "a/environment.yml": 'dependencies: [{pip: ["torch>=2", "bad !!!"]}]\n',
            "a/conda-lock.yml": "package: [{}]\n",
            "b/pyproject.toml": "[project]\n",
            "b/uv.lock": 'package=[{name="vllm"}]\n',
        },
    )
    assert _results(_context(tmp_path, "gap")) == [
        _expected("peft", ["a/environment.yml"], line=3),
        _expected("torch", ["a/conda-lock.yml"], cause="lock", path="a/environment.yml"),
        _expected("vllm", ["b/uv.lock"], cause="origin", line=2),
    ]


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
@pytest.mark.parametrize("bad", ["torch==", "-r pins-extra.txt", "# comment"])
def test_unrelated_embedded_failure_affects_all_uncredited_use_without_inventing_names(
    tmp_path: Path, coverage: str, bad: str
) -> None:
    """A25/A26: conservative scope is repository-wide and independent of Python coverage."""
    _write(
        tmp_path,
        {
            "app/requirements.txt": "torch>=2\nnumpy>=1\n",
            "unrelated/environment.yaml": f"dependencies: [{{pip: [{bad!r}]}}]\n",
        },
    )
    assert _results(_context(tmp_path, coverage)) == [
        _expected(
            "numpy",
            ["unrelated/environment.yaml"],
            path="app/requirements.txt",
            line=2,
            specifier=">=1",
        ),
        _expected("torch", ["unrelated/environment.yaml"], path="app/requirements.txt"),
    ]


def test_sorted_mixed_causes_expand_existing_body_evidence_and_precede_depth(
    tmp_path: Path,
) -> None:
    """A09/A24: already-skipped status can still gain distinct sorted file evidence."""
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "control.py": "# heading\nimport torch\n",
            "a/Pipfile": "packages=false\n",
            "m/pyproject.toml": '[project]\ndependencies=["bad !!!"]\n',
            "z/environment.yml": 'dependencies: [{pip: ["bad !!!"]}]\n',
        },
    )
    ctx = _context(tmp_path)
    assert ctx.deps.unexpanded_requirement_targets == ("depth/pins.txt",)
    assert _results(ctx) == [
        _expected(
            "torch",
            ["a/Pipfile", "m/pyproject.toml", "z/environment.yml"],
            path="control.py",
            line=2,
            imported=True,
        )
    ]


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
def test_failed_text_alone_does_not_create_use_or_aggregate(tmp_path: Path, coverage: str) -> None:
    """A27: an invalid critical-looking string is not a declaration or import."""
    _write(tmp_path, {"environment.yml": 'dependencies: [{pip: ["vllm ???"]}]\n'})
    ctx = _context(tmp_path, coverage)
    rule = LlmCriticalDepsPinnedRule()
    assert not rule.applies(ctx)
    assert _results(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"


@pytest.mark.parametrize("restored", ["exact", "loose", "blank", "removed"])
def test_fresh_restoration_drops_cause_without_mutating_old_context(
    tmp_path: Path, restored: str
) -> None:
    """A18/A35: new scans recompute causes while old captured objects retain their meaning."""
    _write(
        tmp_path,
        {"control.py": "import torch\n", "environment.yml": 'dependencies: [{pip: ["bad !!!"]}]\n'},
    )
    old = _context(tmp_path)
    old_findings = [_expected("torch", ["environment.yml"], path="control.py", imported=True)]
    assert _results(old) == old_findings
    if restored == "removed":
        (tmp_path / "environment.yml").unlink()
    else:
        value = {"exact": "torch==2", "loose": "torch>=2", "blank": " "}[restored]
        _write(tmp_path, {"environment.yml": f"dependencies: [{{pip: [{value!r}]}}]\n"})
    fresh = _context(tmp_path)
    assert fresh.deps.declaration_read_issues == {}
    results = _results(fresh)
    if restored == "exact":
        assert results == []
    else:
        assert len(results) == 1
        assert (results[0]["status"], results[0]["severity"]) == ("fail", "WARNING")
    assert old.deps.declaration_read_issues == {"environment.yml": "unparsed_requirement"}
    assert _results(old) == old_findings


def test_installed_versions_only_suggest_when_no_cause_and_never_change_declarations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A18/A29: installed metadata is a suggestion, never credit or a D-M message source."""
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {"torch": "2.7.1"})
    _write(tmp_path, {"environment.yml": 'dependencies: [{pip: ["torch>=2", "bad !!!"]}]\n'})
    ctx = _context(tmp_path)
    assert _results(ctx) == [_expected("torch", ["environment.yml"], path="environment.yml")]
    _write(tmp_path, {"environment.yml": 'dependencies: [{pip: ["torch>=2"]}]\n'})
    (finding,) = _results(_context(tmp_path))
    assert finding["message"] == (
        "torch is used but not pinned to an exact version (suggestion: torch==2.7.1)"
    )
    assert finding["fix_hint"] == "Pin torch exactly, e.g. `torch==2.7.1`."
    assert [(d.name, d.specifier, d.exact_version) for d in ctx.deps.declarations] == [
        ("torch", ">=2", None)
    ]
