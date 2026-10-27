"""R07-C D-M-CE rule behavior for omitted native Conda dependency strings."""

from pathlib import Path
from typing import Any

import pytest

from reprollm.core.context import AuditContext
from reprollm.core.git import GitInfo
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule


def test_unrelated_conda_omission_does_not_establish_missing_torch_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "train.py").write_text("import torch\n", encoding="utf-8")
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n- conda-forge::requests\n", encoding="utf-8"
    )
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    ctx = AuditContext(tmp_path)
    ctx._git = GitInfo(is_repo=False)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    (finding,) = rule.check(ctx)

    assert finding.model_dump(mode="json") == {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 0,
        "message": (
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established"
        ),
        "evidence": [
            {
                "kind": "file",
                "path": "train.py",
                "field": None,
                "line": 1,
                "value": None,
                "expected": None,
                "note": "imported",
            },
            {
                "kind": "file",
                "path": "environment.yml",
                "field": None,
                "line": None,
                "value": None,
                "expected": None,
                "note": "torch possible exact declaration unverified",
            },
        ],
        "fix_hint": (
            "Review torch declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    assert ctx.deps.declarations == []
    assert [info.module for info in ctx.pyscan.imports] == ["torch"]
    assert ctx.pyscan.coverage().pass_skip_reason() is None


def _context(root: Path, monkeypatch: pytest.MonkeyPatch) -> AuditContext:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    ctx = AuditContext(root)
    ctx._git = GitInfo(is_repo=False)
    return ctx


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _evidence(
    path: str, *, line: int | None = None, value: str | None = None, note: str
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


def _body_skip(
    paths: list[str], *, first: dict[str, Any] | None = None, package: str = "torch"
) -> dict[str, Any]:
    return {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 0,
        "message": (
            f"{package} is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established"
        ),
        "evidence": [
            first if first is not None else _evidence("train.py", line=1, note="imported"),
            *[
                _evidence(path, note=f"{package} possible exact declaration unverified")
                for path in paths
            ],
        ],
        "fix_hint": (
            f"Review {package} declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.parametrize(
    "entry",
    [
        "''",
        '"  \\t "',
        "conda-forge::requests",
        "conda-forge/linux-64::requests=2.32",
        "requests/subdir",
        "::requests=2.32",
        "'*requests*'",
        "'requests\n\n  ==2.32'",
    ],
)
def test_omitted_native_string_keeps_imported_use_and_full_body_skip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    _write(
        tmp_path,
        {"train.py": "import torch\n", "environment.yaml": f"dependencies:\n- {entry}\n"},
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(["environment.yaml"])
    ]
    assert ctx.deps.declarations == []
    assert [item.module for item in ctx.pyscan.imports] == ["torch"]
    assert ctx.deps.qualified_lock_packages([]) == frozenset()


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
def test_omission_uncertainty_does_not_depend_on_python_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- pytorch=2\n- conda-forge::requests\n",
            "broken.py": "broken =\n" if coverage == "gap" else "pass\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    if coverage == "unavailable":
        ctx._pyscan = PyScanResult()
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    assert [f.model_dump(mode="json") for f in rule.check(ctx)] == [
        _body_skip(
            ["environment.yml"],
            first=_evidence("environment.yml", line=1, value="=2", note="declared as =2"),
        )
    ]
    assert (rule.pass_skip_reason(ctx) is not None) == (coverage != "complete")


@pytest.mark.parametrize(
    ("extra_files", "qualified"),
    [
        ({"environment.yml": "dependencies:\n- conda-forge::requests\n- pytorch==2.5.1\n"}, False),
        (
            {
                "environment.yml": (
                    "dependencies:\n- conda-forge::requests\n- pytorch=2.5.1=py310_cpu\n"
                )
            },
            False,
        ),
        ({"requirements.txt": "torch==2.5.1 # independently exact\n"}, True),
        ({"pyproject.toml": '[project]\ndependencies=["torch==2.5.1"]\n'}, False),
        ({"conda-lock.yml": "package:\n- name: pytorch\n"}, True),
        (
            {
                "pyproject.toml": "[project]\n",
                "uv.lock": 'package=[{name="torch"}]\n',
            },
            True,
        ),
        ({"conda-lock.yml": "package:\n- name: pytorch\n- {}\n"}, True),
    ],
)
def test_positive_exact_or_qualified_credit_precedes_omitted_conda_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_files: dict[str, str],
    qualified: bool,
) -> None:
    _write(
        tmp_path,
        {
            "train.py": "import torch\n",
            "environment.yml": "dependencies:\n- conda-forge::requests\n",
            **extra_files,
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is True
    assert rule.check(ctx) == []
    assert rule.pass_skip_reason(ctx) is None
    assert ("torch" in ctx.deps.qualified_lock_packages([("torch", "train.py")])) is qualified


@pytest.mark.parametrize("lock_body", ["package: [\n", "package: [{}]\n"])
def test_associated_lock_failure_retains_full_finding_before_conda_omission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lock_body: str
) -> None:
    _write(
        tmp_path,
        {
            "train.py": "import torch\n",
            "environment.yml": "dependencies:\n- conda-forge::requests\n",
            "conda-lock.yml": lock_body,
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    expected = _body_skip(["conda-lock.yml"])
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


@pytest.mark.parametrize("coverage", ["gap", "unavailable"])
def test_lock_origin_uncertainty_retains_full_finding_before_conda_omission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str
) -> None:
    _write(
        tmp_path,
        {
            "train.py": "import torch\n",
            "environment.yml": "dependencies:\n- conda-forge::requests\n",
            "poetry.lock": '[[package]]\nname="torch"\n',
            "broken.py": "broken =\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    if coverage == "unavailable":
        ctx._pyscan = PyScanResult(imports=list(ctx.pyscan.imports))
    expected = _body_skip(["poetry.lock"])
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

    assert rule.pass_skip_reason(ctx) is not None
    assert [f.model_dump(mode="json") for f in rule.check(ctx)] == [expected]


@pytest.mark.parametrize(
    ("body", "first_issue"),
    [
        ("dependencies:\n- conda-forge::requests\n- pip:\n  - 42\n", "invalid_structure"),
        (
            "dependencies:\n- pip:\n  - torch @\n- conda-forge::requests\n",
            "unparsed_requirement",
        ),
        (
            "dependencies:\n- conda-forge::requests\n- pip:\n  - torch @\n",
            "unparsed_conda",
        ),
    ],
)
def test_existing_document_or_first_traversed_entry_cause_keeps_same_body_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, first_issue: str
) -> None:
    _write(tmp_path, {"train.py": "import torch\n", "environment.yml": body})
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(["environment.yml"])
    ]
    assert ctx.deps.declaration_read_issues == {"environment.yml": first_issue}


@pytest.mark.parametrize(
    ("path", "body", "expected_paths"),
    [
        (
            "pyproject.toml",
            "[tool.poetry.dependencies]\nrequests={version=false}\n",
            ["environment.yml", "pyproject.toml"],
        ),
        ("Pipfile", "[packages]\nrequests={version=false}\n", ["Pipfile", "environment.yml"]),
    ],
)
def test_existing_body_skip_gains_only_new_sorted_conda_source_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    body: str,
    expected_paths: list[str],
) -> None:
    _write(
        tmp_path,
        {
            "train.py": "import torch\n",
            "environment.yml": "dependencies:\n- conda-forge::requests\n",
            path: body,
        },
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(expected_paths)
    ]
    assert [declaration.name for declaration in ctx.deps.declarations] == ["requests"]


def test_distinct_omission_sources_are_sorted_once_after_original_use_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "z/environment.yml": "dependencies:\n- conda-forge::requests\n- ::requests\n",
            "a/environment.yaml": "dependencies:\n- ''\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(
            ["a/environment.yaml", "z/environment.yml"],
            first=_evidence("requirements.txt", line=1, value=">=2", note="declared as >=2"),
        )
    ]


def test_conda_omission_precedes_unexpanded_requirements_target_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "requirements.txt": "torch>=2\n",
            "requirements-z.txt": "-r chain/0.txt\n",
            "unreached.txt": "torch==2.5.1\n",
            "environment.yml": "dependencies:\n- conda-forge::requests\n",
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


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable"])
def test_omission_does_not_create_unknown_critical_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str
) -> None:
    _write(
        tmp_path,
        {
            "environment.yml": "dependencies:\n- conda-forge::pytorch==2.5.1\n",
            "train.py": "broken =\n" if coverage == "gap" else "pass\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)
    if coverage == "unavailable":
        ctx._pyscan = PyScanResult()
    rule = LlmCriticalDepsPinnedRule()

    assert rule.applies(ctx) is False
    assert rule.check(ctx) == []
    assert rule.skip_reason(ctx) == "no LLM-critical package is declared or imported"
    assert (rule.pass_skip_reason(ctx) is not None) == (coverage != "complete")


@pytest.mark.parametrize(
    ("entry", "value"),
    [
        ("pytorch>=2.5", ">=2.5"),
        ("pytorch==2.5.*", "(unsupported conda declaration)"),
        ("pytorch>=2.5,<3.0", "(unsupported conda declaration)"),
        ("pytorch==2.5.1rc1", "(unsupported conda declaration)"),
        ("pytorch /subdir", "(unsupported conda declaration)"),
        ("conda-forge ::pytorch=2.5.1", None),
        ("https://example.invalid/packages/pytorch", None),
    ],
)
def test_retained_name_grammar_still_warns_without_new_conda_uncertainty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str, value: str | None
) -> None:
    _write(
        tmp_path,
        {"train.py": "import torch\n", "environment.yml": f"dependencies:\n- {entry}\n"},
    )
    ctx = _context(tmp_path, monkeypatch)
    expected = _body_skip([])
    expected.update(
        severity="WARNING",
        status="fail",
        message="torch is used but not pinned to an exact version (suggestion: torch==<version>)",
        fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
    )
    if value is not None:
        expected["evidence"] = [
            _evidence("environment.yml", line=1, value=value, note=f"declared as {value}")
        ]

    assert ctx.deps.declaration_read_issues == {}
    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [expected]


def test_unrelated_omission_conservatively_affects_each_existing_uncredited_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(
        tmp_path,
        {
            "train.py": "import torch\nimport openai\n",
            "other/environment.yml": "dependencies:\n- conda-forge::requests\n",
        },
    )
    ctx = _context(tmp_path, monkeypatch)

    assert [f.model_dump(mode="json") for f in LlmCriticalDepsPinnedRule().check(ctx)] == [
        _body_skip(
            ["other/environment.yml"],
            first=_evidence("train.py", line=2, note="imported"),
            package="openai",
        ),
        _body_skip(["other/environment.yml"]),
    ]
    assert ctx.deps.declarations == []
