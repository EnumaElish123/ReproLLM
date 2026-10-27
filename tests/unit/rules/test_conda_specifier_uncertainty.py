"""R07-C D-M-CS complete rule outcomes for retained Conda specifiers."""

from pathlib import Path
from typing import Any

import pytest

from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule
from tests.unit.rules.test_conda_omission_uncertainty import (
    _body_skip,
    _context,
    _evidence,
    _write,
)


def test_unrelated_nonexact_conda_specifier_does_not_establish_missing_torch_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {"environment.yml": "dependencies:\n- requests=2.*\n", "train.py": "import torch\n"},
    )
    ctx = _context(tmp_path, monkeypatch)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    assert [finding.model_dump(mode="json") for finding in rule.check(ctx)] == [
        _body_skip(["environment.yml"])
    ]
    assert [
        (d.name, d.display_name, d.specifier, d.exact_version, d.source_file, d.line)
        for d in ctx.deps.declarations
    ] == [("requests", "requests", "(unsupported conda declaration)", None, "environment.yml", 1)]
    assert [info.module for info in ctx.pyscan.imports] == ["torch"]


@pytest.mark.parametrize("entry", ["pytorch==2.5.1rc1", "pytorch=2.*", "pytorch>=2,<3"])
def test_retained_critical_name_keeps_first_declaration_and_full_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    _write(tmp_path, {"environment.yaml": f"dependencies:\n- {entry}\n"})
    ctx = _context(tmp_path, monkeypatch)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    assert [f.model_dump(mode="json") for f in rule.check(ctx)] == [
        _body_skip(
            ["environment.yaml"],
            first=_evidence(
                "environment.yaml",
                line=1,
                value="(unsupported conda declaration)",
                note="declared as (unsupported conda declaration)",
            ),
        )
    ]
    assert ctx.deps.declaration_read_issues == {"environment.yaml": "unparsed_conda_specifier"}
    assert [d.name for d in ctx.deps.declarations] == ["torch"]
    assert ctx.pyscan.imports == []


@pytest.mark.parametrize(
    ("entry", "value", "note"),
    [
        ("pytorch>=2.5", ">=2.5", "declared as >=2.5"),
        ("pytorch<=2.5", "<=2.5", "declared as <=2.5"),
        ("pytorch!=2.5", "!=2.5", "declared as !=2.5"),
        ("pytorch>2.5", ">2.5", "declared as >2.5"),
        ("pytorch<2.5", "<2.5", "declared as <2.5"),
        ("pytorch~=2.5", "~=2.5", "declared as ~=2.5"),
        ("pytorch", "(no version)", "declared as unversioned"),
        ("pytorch=2.5.1", "=2.5.1", "declared as =2.5.1"),
    ],
)
def test_known_nonexact_captured_subset_keeps_complete_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, value: str, note: str
) -> None:
    _write(tmp_path, {"environment.yml": f"dependencies:\n- {entry}\n"})
    ctx = _context(tmp_path, monkeypatch)
    expected = _body_skip([], first=_evidence("environment.yml", line=1, value=value, note=note))
    expected.update(
        severity="WARNING",
        status="fail",
        message="torch is used but not pinned to an exact version (suggestion: torch==<version>)",
        fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
    )

    assert ctx.deps.declaration_read_issues == {}
    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [expected]


@pytest.mark.parametrize(
    ("extra", "qualified"),
    [
        ({"environment.yml": "dependencies:\n- requests=2.*\n- pytorch==2.5.1\n"}, False),
        ({"environment.yml": "dependencies:\n- requests=2.*\n- pytorch=2.5.1=cpu\n"}, False),
        ({"pins/requirements.txt": "torch==2.5.1\n"}, True),
        ({"pyproject.toml": '[project]\ndependencies=["torch==2.5.1"]\n'}, False),
        ({"Pipfile": '[packages]\ntorch="==2.5.1"\n'}, False),
        ({"conda-lock.yml": "package: [{name: pytorch}]\n"}, True),
        (
            {"pyproject.toml": "[project]\n", "uv.lock": 'package=[{name="torch"}]\n'},
            True,
        ),
        ({"conda-lock.yml": "package: [{name: pytorch}, {}]\n"}, True),
    ],
)
def test_existing_positive_credit_wins_over_retained_specifier_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra: dict[str, str], qualified: bool
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- requests=2.*\n",
            "train.py": "import torch\n",
            **extra,
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    assert rule.check(ctx) == []
    assert rule.pass_skip_reason(ctx) is None
    assert ctx.deps.declaration_read_issues == {"environment.yml": "unparsed_conda_specifier"}
    assert ("torch" in ctx.deps.qualified_lock_packages([("torch", "train.py")])) is qualified


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
def test_specifier_fact_and_complete_skip_do_not_depend_on_python_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- pytorch=2.*\n",
            "analysis.py": "broken =\n" if coverage == "gap" else "pass\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    if coverage == "unavailable":
        ctx._pyscan = PyScanResult()
    elif coverage == "inconsistent":
        ctx._pyscan = PyScanResult(
            coverage_observed=True,
            python_candidate_count=0,
            python_selected_count=1,
            python_parsed_count=1,
            python_file_limit=500,
        )
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    assert [f.model_dump(mode="json") for f in rule.check(ctx)] == [
        _body_skip(
            ["environment.yml"],
            first=_evidence(
                "environment.yml",
                line=1,
                value="(unsupported conda declaration)",
                note="declared as (unsupported conda declaration)",
            ),
        )
    ]
    assert ctx.deps.declaration_read_issues == {"environment.yml": "unparsed_conda_specifier"}


@pytest.mark.parametrize(
    ("lock_path", "lock_text"),
    [
        ("poetry.lock", '[[package]]\nname="torch"\n'),
        ("conda-lock.yml", "package: []\n"),
        ("other/conda-lock.yml", "package: [{name: pytorch}]\n"),
    ],
)
def test_lock_existence_without_qualified_package_does_not_grant_pin_credit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_path: str, lock_text: str
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- requests=2.*\n",
            "train.py": "import torch\n",
            lock_path: lock_text,
        },
    )
    ctx = _context(tmp_path, monkeypatch)

    assert "torch" not in ctx.deps.qualified_lock_packages([("torch", "train.py")])
    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(["environment.yml"])
    ]
    assert len(ctx.deps.lockfiles) == 1 and ctx.deps.lockfiles[0].read_issue is None


@pytest.mark.parametrize("lock_text", ["package: [\n", "package: [{}]\n"])
def test_associated_lock_failure_keeps_complete_higher_priority_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_text: str
) -> None:
    _write(
        tmp_path,
        {"environment.yml": "dependencies:\n- pytorch=2.*\n", "conda-lock.yml": lock_text},
    )
    ctx = _context(tmp_path, monkeypatch)
    expected = _body_skip(
        ["conda-lock.yml"],
        first=_evidence(
            "environment.yml",
            line=1,
            value="(unsupported conda declaration)",
            note="declared as (unsupported conda declaration)",
        ),
    )
    expected["message"] = (
        "torch is used; an associated format lock could not be read or parsed, "
        "so missing pin evidence is not established"
    )
    expected["fix_hint"] = (
        "Review torch declarations and associated format-lock files; restore readable, valid "
        "lock contents before deciding that exact pin evidence is absent."
    )
    expected["evidence"][1]["note"] = "torch associated; lock package contents unverified"

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [expected]


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
def test_possible_lock_origin_keeps_priority_only_for_incomplete_python_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- pytorch=2.*\n",
            "poetry.lock": '[[package]]\nname="torch"\n',
            "broken.py": "broken =\n" if coverage == "gap" else "pass\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    if coverage == "unavailable":
        ctx._pyscan = PyScanResult()
    first = _evidence(
        "environment.yml",
        line=1,
        value="(unsupported conda declaration)",
        note="declared as (unsupported conda declaration)",
    )
    expected = _body_skip(["environment.yml"], first=first)
    if coverage != "complete":
        expected = _body_skip(["poetry.lock"], first=first)
        expected["message"] = (
            "torch is used; Python analysis is incomplete or unavailable and a captured format "
            "lock lists the package, so missing pin evidence is not established"
        )
        expected["fix_hint"] = (
            "Review torch declarations and format-lock origins; complete Python analysis before "
            "deciding that exact pin evidence is absent."
        )
        expected["evidence"][1]["note"] = "torch listed; import-origin credit unverified"
    rule = LlmCriticalDepsPinnedRule()

    assert "torch" not in ctx.deps.qualified_lock_packages([])
    assert (rule.pass_skip_reason(ctx) is not None) == (coverage != "complete")
    assert [f.model_dump(mode="json") for f in rule.check(ctx)] == [expected]


@pytest.mark.parametrize(
    ("body", "cause", "use_line"),
    [
        (
            "dependencies:\n- conda-forge::requests\n- pytorch=2.*\n",
            "unparsed_conda",
            2,
        ),
        (
            "dependencies:\n- pytorch=2.*\n- conda-forge::requests\n",
            "unparsed_conda_specifier",
            1,
        ),
        (
            'dependencies:\n- pip: ["torch @"]\n- pytorch=2.*\n',
            "unparsed_requirement",
            2,
        ),
        (
            'dependencies:\n- pytorch=2.*\n- pip: ["torch @"]\n',
            "unparsed_conda_specifier",
            1,
        ),
        ("dependencies:\n- pytorch=2.*\n- false\n", "invalid_structure", 1),
    ],
)
def test_first_existing_source_cause_and_original_use_ordinal_are_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, cause: str, use_line: int
) -> None:
    _write(tmp_path, {"environment.yml": body})
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(
            ["environment.yml"],
            first=_evidence(
                "environment.yml",
                line=use_line,
                value="(unsupported conda declaration)",
                note="declared as (unsupported conda declaration)",
            ),
        )
    ]
    assert ctx.deps.declaration_read_issues == {"environment.yml": cause}


@pytest.mark.parametrize(
    ("old_path", "old_body", "expected_paths"),
    [
        ("Pipfile", "[packages]\nrequests={version=false}\n", ["Pipfile", "environment.yml"]),
        (
            "pyproject.toml",
            "[tool.poetry.dependencies]\nrequests={version=false}\n",
            ["environment.yml", "pyproject.toml"],
        ),
    ],
)
def test_existing_body_skip_gains_only_additional_sorted_specifier_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    old_path: str,
    old_body: str,
    expected_paths: list[str],
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- requests=2.*\n",
            "train.py": "import torch\n",
            old_path: old_body,
        },
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(expected_paths)
    ]
    assert ctx.deps.declaration_read_issues == {
        old_path: "invalid_structure",
        "environment.yml": "unparsed_conda_specifier",
    }


def test_distinct_specifier_sources_follow_original_first_use_once_in_lexical_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "z/environment.yml": "dependencies:\n- requests=2.*\n- requests==2rc1\n",
            "a/environment.yaml": "dependencies:\n- requests>=2,<3\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(
            ["a/environment.yaml", "z/environment.yml"],
            first=_evidence("requirements.txt", line=1, value=">=2", note="declared as >=2"),
        )
    ]
    assert len(ctx.deps.unparsed) == 3


def test_retained_specifier_uncertainty_precedes_actual_unexpanded_include_frontier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "requirements-z.txt": "-r chain/0.txt\n",
            "unreached.txt": "torch==2.5.1\n",
            "environment.yml": "dependencies:\n- requests=2.*\n",
        },
    )
    _write(tmp_path, {f"chain/{n}.txt": f"-r {n + 1}.txt\n" for n in range(9)})
    _write(tmp_path, {"chain/9.txt": "-r ../unreached.txt\n"})
    ctx = _context(tmp_path, monkeypatch)

    assert ctx.deps.unexpanded_requirement_targets == ("unreached.txt",)
    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(
            ["environment.yml"],
            first=_evidence("requirements.txt", line=1, value=">=2", note="declared as >=2"),
        )
    ]


@pytest.mark.parametrize("entry", ["requests=2.*", "https://example.invalid/pytorch"])
def test_failed_specifier_without_known_critical_use_keeps_applicability_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    _write(tmp_path, {"environment.yml": f"dependencies:\n- {entry}\n"})
    ctx = _context(tmp_path, monkeypatch)
    rule = LlmCriticalDepsPinnedRule()

    assert ctx.deps.declaration_read_issues == {"environment.yml": "unparsed_conda_specifier"}
    assert rule.applies(ctx) is False
    assert rule.check(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"
    assert rule.pass_skip_reason(ctx) is None


@pytest.mark.parametrize("critical", [False, True], ids=["no-use", "exact-credit"])
@pytest.mark.parametrize(
    ("coverage", "reason"),
    [
        ("complete", None),
        (
            "gap",
            "Python candidate analysis incomplete: parsed 0 of 1 candidate files; "
            "selected 1 (limit 500); no rule-wide PASS is established.",
        ),
        (
            "unavailable",
            "Python candidate coverage is unavailable; no rule-wide PASS is established.",
        ),
        (
            "inconsistent",
            "Python candidate coverage is unavailable; no rule-wide PASS is established.",
        ),
    ],
)
def test_empty_raw_result_keeps_applicability_and_original_python_veto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    critical: bool,
    coverage: str,
    reason: str | None,
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": (
                "dependencies:\n- requests=2.*\n" + ("- pytorch==2.5.1\n" if critical else "")
            ),
            "analysis.py": "broken =\n" if coverage == "gap" else "pass\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    if coverage == "unavailable":
        ctx._pyscan = PyScanResult()
    elif coverage == "inconsistent":
        ctx._pyscan = PyScanResult(
            coverage_observed=True,
            python_candidate_count=0,
            python_selected_count=1,
            python_parsed_count=1,
            python_file_limit=500,
        )
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is critical
    assert rule.check(ctx) == []
    assert rule.skip_reason(ctx) == (
        None if critical else "no LLM-critical package is declared or imported"
    )
    assert rule.pass_skip_reason(ctx) == reason
    assert ctx.deps.declaration_read_issues == {"environment.yml": "unparsed_conda_specifier"}


@pytest.mark.parametrize(
    ("source", "entry", "torch_first"),
    [
        (
            "environment.yml",
            "requests=2.*",
            _evidence("train.py", line=1, note="imported"),
        ),
        (
            "other/environment.yaml",
            "requests>=2,<3",
            _evidence("train.py", line=1, note="imported"),
        ),
        (
            "environment.yml",
            "pytorch=2.*",
            _evidence(
                "environment.yml",
                line=1,
                value="(unsupported conda declaration)",
                note="declared as (unsupported conda declaration)",
            ),
        ),
    ],
)
def test_nonexact_specifier_keeps_accepted_repository_wide_multi_package_cost(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
    entry: str,
    torch_first: dict[str, Any],
) -> None:
    _write(
        tmp_path,
        {source: f"dependencies:\n- {entry}\n", "train.py": "import torch\nimport openai\n"},
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(
            [source],
            first=_evidence("train.py", line=2, note="imported"),
            package="openai",
        ),
        _body_skip([source], first=torch_first),
    ]
    assert [info.module for info in ctx.pyscan.imports] == ["torch", "openai"]


@pytest.mark.parametrize("level", [1, 2])
def test_specifier_skip_keeps_requested_audit_level_and_default_finding_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, level: int
) -> None:
    _write(
        tmp_path,
        {"environment.yml": "dependencies:\n- requests=2.*\n", "train.py": "import torch\n"},
    )
    ctx = _context(tmp_path, monkeypatch)
    ctx.level = level
    expected = _body_skip(["environment.yml"])
    expected["level"] = level

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [expected]
