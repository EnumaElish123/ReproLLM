"""D-M-P P18-P28: PEP 621 parse failures reuse the bounded declaration policy."""

from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.git import GitInfo
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule


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


def _frontier(root: Path) -> None:
    files = {"unrelated/requirements.txt": "-r chain/0.txt\n"}
    for index in range(9):
        files[f"unrelated/chain/{index}.txt"] = f"-r {index + 1}.txt\n"
    files["unrelated/chain/9.txt"] = "-r ../pins.txt\n"
    _write(root, files)


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
    sources: list[str],
    *,
    cause: str = "body",
    path: str = "requirements.txt",
    line: int = 1,
    specifier: str = ">=2",
    imported: bool = False,
) -> dict[str, Any]:
    messages = {
        "body": "a dependency declaration body could not be read or parsed",
        "lock": "an associated format lock could not be read or parsed",
        "origin": (
            "Python analysis is incomplete or unavailable and a captured format lock "
            "lists the package"
        ),
        "depth": "a supported requirements include was not expanded within the depth budget",
    }
    notes = {
        "body": "possible exact declaration unverified",
        "lock": "associated; lock package contents unverified",
        "origin": "listed; import-origin credit unverified",
        "depth": "include target unexpanded at the depth limit",
    }
    hints = {
        "body": (
            f"Review {package} declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        ),
        "lock": (
            f"Review {package} declarations and associated format-lock files; restore readable, "
            "valid lock contents before deciding that exact pin evidence is absent."
        ),
        "origin": (
            f"Review {package} declarations and format-lock origins; complete Python analysis "
            "before deciding that exact pin evidence is absent."
        ),
        "depth": (
            f"Review {package} declarations and unexpanded requirements include targets; "
            "restructure the supported include graph within the depth budget before deciding "
            "that exact pin evidence is absent."
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
            *[_evidence(source, f"{package} {notes[cause]}") for source in sources],
        ],
        "fix_hint": hints[cause],
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


def _results(ctx: AuditContext) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in LlmCriticalDepsPinnedRule().check(ctx)]


@pytest.mark.parametrize("credit", ["same", "optional", "unrelated", "conflicting", "lock"])
@pytest.mark.parametrize("coverage", ["complete", "gap"])
def test_positive_credit_survives_unparsed_strings_and_empty_result_veto(
    tmp_path: Path, credit: str, coverage: str
) -> None:
    _write(tmp_path, {"pyproject.toml": '[project]\ndependencies=["torch>=2", "bad !!!"]\n'})
    if credit == "same":
        _write(
            tmp_path,
            {"pyproject.toml": '[project]\ndependencies=["torch>=2", "bad !!!", "torch==2"]\n'},
        )
    elif credit == "optional":
        with (tmp_path / "pyproject.toml").open("a", encoding="utf-8") as stream:
            stream.write('[project.optional-dependencies]\nextra=["torch==2"]\n')
    elif credit == "lock":
        _write(tmp_path, {"uv.lock": 'package=[{name="torch"},{}]\n'})
    else:
        _write(tmp_path, {"other/requirements.txt": "torch==2\n"})
        if credit == "conflicting":
            _write(tmp_path, {"requirements.txt": "torch==1\n"})
    ctx = _context(tmp_path, coverage)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx)
    assert _results(ctx) == []
    assert (rule.pass_skip_reason(ctx) is not None) == (coverage == "gap")


@pytest.mark.parametrize("lock_body", ["[broken\n", "package=[{}]\n"])
def test_associated_lock_failure_wins_without_lower_priority_evidence(
    tmp_path: Path, lock_body: str
) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "pyproject.toml": '[project]\ndependencies=["torch>=2", "bad !!!"]\n',
            "uv.lock": lock_body,
            "broken/Pipfile": "packages=false\n",
        },
    )
    assert _results(_context(tmp_path, "gap")) == [
        _expected("torch", ["uv.lock"], cause="lock", path="pyproject.toml", line=2)
    ]


def test_unverified_lock_origin_wins_without_declaration_or_depth_evidence(tmp_path: Path) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "nested/pyproject.toml": '[project]\ndependencies=["bad !!!"]\n',
            "nested/uv.lock": 'package=[{name="torch"}]\n',
            "broken/Pipfile": "packages=false\n",
        },
    )
    assert _results(_context(tmp_path, "gap")) == [
        _expected("torch", ["nested/uv.lock"], cause="origin")
    ]


def test_each_package_chooses_its_own_credit_or_priority(tmp_path: Path) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "requirements.txt": "numpy==2\nvllm>=2\npeft>=2\n",
            "a/pyproject.toml": '[project]\ndependencies=["torch>=2", "bad !!!"]\n',
            "a/uv.lock": "package=[{}]\n",
            "b/pyproject.toml": "[project]\n",
            "b/uv.lock": 'package=[{name="vllm"}]\n',
        },
    )
    assert _results(_context(tmp_path, "gap")) == [
        _expected("peft", ["a/pyproject.toml"], line=3),
        _expected("torch", ["a/uv.lock"], cause="lock", path="a/pyproject.toml", line=2),
        _expected("vllm", ["b/uv.lock"], cause="origin", line=2),
    ]


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
@pytest.mark.parametrize("bad", ['""', '" "', '"\\t"', '"\\n"', '"bad !!!"'])
def test_unrelated_blank_or_bad_string_conservatively_affects_every_uncredited_package(
    tmp_path: Path, coverage: str, bad: str
) -> None:
    _write(
        tmp_path,
        {
            "app/requirements.txt": "torch>=2\nnumpy>=1\n",
            "unrelated/pyproject.toml": f"[project]\ndependencies=[{bad}]\n",
        },
    )
    assert _results(_context(tmp_path, coverage)) == [
        _expected(
            "numpy",
            ["unrelated/pyproject.toml"],
            path="app/requirements.txt",
            line=2,
            specifier=">=1",
        ),
        _expected("torch", ["unrelated/pyproject.toml"], path="app/requirements.txt"),
    ]


@pytest.mark.parametrize("origin", ["declaration", "import"])
def test_sorted_mixed_body_failures_keep_first_use_and_precede_depth(
    tmp_path: Path, origin: str
) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {
            "z/pyproject.toml": '[project]\ndependencies=["bad !!!"]\n',
            "a/Pipfile": "packages=false\n",
            "m/environment.yml": "dependencies: false\n",
            "later.py": "import torch\n",
        },
    )
    if origin == "declaration":
        _write(tmp_path, {"requirements.txt": "# heading\ntorch>=2\ntorch>=1\n"})
    else:
        _write(tmp_path, {"first.py": "# heading\nimport torch\n"})
    assert _results(_context(tmp_path)) == [
        _expected(
            "torch",
            ["a/Pipfile", "m/environment.yml", "z/pyproject.toml"],
            path="first.py" if origin == "import" else "requirements.txt",
            line=2,
            imported=origin == "import",
        )
    ]


def test_adding_removing_new_source_expands_only_sorted_body_evidence(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "z/pyproject.toml": '[project]\ndependencies=[1, "bad !!!"]\n',
        },
    )
    original = [_expected("torch", ["z/pyproject.toml"])]
    ctx = _context(tmp_path)
    assert _results(ctx) == original
    assert ctx.deps.declaration_read_issues == {"z/pyproject.toml": "invalid_structure"}
    _write(tmp_path, {"z/pyproject.toml": "[project]\ndependencies=[1]\n"})
    assert _results(_context(tmp_path)) == original
    _write(tmp_path, {"a/pyproject.toml": '[project]\ndependencies=["bad !!!"]\n'})
    assert _results(_context(tmp_path)) == [
        _expected("torch", ["a/pyproject.toml", "z/pyproject.toml"])
    ]
    (tmp_path / "a/pyproject.toml").unlink()
    assert _results(_context(tmp_path)) == original


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
@pytest.mark.parametrize("valid", ["", '"requests>=2", '])
def test_bad_text_cannot_invent_critical_use_or_override_applicability(
    tmp_path: Path, coverage: str, valid: str
) -> None:
    _write(tmp_path, {"pyproject.toml": f'[project]\ndependencies=[{valid}"vllm ???"]\n'})
    ctx = _context(tmp_path, coverage)
    rule = LlmCriticalDepsPinnedRule()
    assert not rule.applies(ctx)
    assert _results(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"


def test_restored_empty_collection_returns_existing_depth_reason(tmp_path: Path) -> None:
    _frontier(tmp_path)
    _write(
        tmp_path,
        {"requirements.txt": "torch>=2\n", "pyproject.toml": '[project]\ndependencies=[""]\n'},
    )
    assert _results(_context(tmp_path)) == [_expected("torch", ["pyproject.toml"])]
    _write(tmp_path, {"pyproject.toml": "[project]\ndependencies=[]\n"})
    assert _results(_context(tmp_path)) == [
        _expected("torch", ["unrelated/pins.txt"], cause="depth")
    ]
