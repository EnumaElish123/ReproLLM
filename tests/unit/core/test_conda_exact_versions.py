"""Accepted R05-S C Conda declaration and public consumer regressions (R05-B)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.rules.env import (
    LlmCriticalDepsPinnedRule,
    LockfilePresentRule,
    PythonVersionDeclaredRule,
)
from reprollm.schemas.finding import FindingStatus, Severity

CONDA_CASES = [
    ("bare", "torch", None, "torch", None, False),
    ("prefix-major", "torch=2", None, "torch", "=2", False),
    ("prefix-short", "torch=2.5", None, "torch", "=2.5", False),
    ("prefix-long", "torch=2.5.1", None, "torch", "=2.5.1", False),
    ("double-major", "torch==2", "2", "torch", "==2", False),
    ("double-short", "torch==2.5", "2.5", "torch", "==2.5", False),
    ("double-release", "torch==2.5.1", "2.5.1", "torch", "==2.5.1", False),
    ("double-zero-components", "torch==02.05.1", "02.05.1", "torch", "==02.05.1", False),
    ("export-build", "torch=2.5.1=cuda12.1", "2.5.1", "torch", "=2.5.1=cuda12.1", False),
    (
        "double-export-build",
        "torch==2.5.1=py_0+cuda-12",
        "2.5.1",
        "torch",
        "==2.5.1=py_0+cuda-12",
        False,
    ),
    ("build-digits", "torch=2.5.1=0", "2.5.1", "torch", "=2.5.1=0", False),
    ("build-all-literal-classes", "torch=2.5.1=Aa0._+-", "2.5.1", "torch", "=2.5.1=Aa0._+-", False),
    ("alias-prefix", "pytorch=2.5.1", None, "torch", "=2.5.1", False),
    ("alias-exact", "pytorch==2.5.1", "2.5.1", "torch", "==2.5.1", False),
    ("alias-build", "PyTorch=2.5.1=cuda12.1", "2.5.1", "torch", "=2.5.1=cuda12.1", False),
    ("alias-bare", "pytorch", None, "torch", None, False),
    ("outer-whitespace", "  torch==2.5.1  ", "2.5.1", "torch", "==2.5.1", False),
    ("range", "torch>=2.5", None, "torch", ">=2.5", True),
    ("compound", "torch>=2.5,<3", None, "torch", "(unsupported conda declaration)", True),
    ("wildcard-version", "torch==2.5.*", None, "torch", "(unsupported conda declaration)", True),
    ("wildcard-build", "torch=2.5.1=cuda*", None, "torch", "(unsupported conda declaration)", True),
    ("empty-version", "torch==", None, "torch", "(unsupported conda declaration)", True),
    ("empty-build", "torch=2.5.1=", None, "torch", "(unsupported conda declaration)", True),
    (
        "extra-part",
        "torch=2.5.1=py_0=extra",
        None,
        "torch",
        "(unsupported conda declaration)",
        True,
    ),
    ("triple-equality", "torch===2.5.1", None, "torch", "(unsupported conda declaration)", True),
    ("suffix-pre", "torch==2.5.1rc1", None, "torch", "(unsupported conda declaration)", True),
    ("suffix-post", "torch==2.5.1.post1", None, "torch", "(unsupported conda declaration)", True),
    ("suffix-local", "torch==2.5.1+cu121", None, "torch", "(unsupported conda declaration)", True),
    ("epoch", "torch==1!2.5.1", None, "torch", "(unsupported conda declaration)", True),
    ("trailing-version-dot", "torch==2.5.", None, "torch", "(unsupported conda declaration)", True),
    (
        "empty-version-component",
        "torch==2..5",
        None,
        "torch",
        "(unsupported conda declaration)",
        True,
    ),
    ("signed-version", "torch==-2.5.1", None, "torch", "(unsupported conda declaration)", True),
    ("unicode-version", "torch==２.５.１", None, "torch", "(unsupported conda declaration)", True),
    ("unicode-build", "torch=2.5.1=cudá", None, "torch", "(unsupported conda declaration)", True),
    (
        "space-in-version",
        "torch==2.5.1 =py_0",
        None,
        "torch",
        "(unsupported conda declaration)",
        True,
    ),
    (
        "slash-in-build",
        "torch=2.5.1=linux/py_0",
        None,
        "torch",
        "(unsupported conda declaration)",
        True,
    ),
    ("bracket", "torch[version='2.5.1']", None, "torch", "(unsupported conda declaration)", True),
    ("regex", "torch^2[.]5[.]1$", None, "torch", "(unsupported conda declaration)", True),
    ("channel", "conda-forge::torch==2.5.1", None, None, None, True),
    ("channel-subdir", "conda-forge/linux-64::torch==2.5.1", None, None, None, True),
    ("empty-name", "==2.5.1", None, None, None, True),
    ("empty-input", "", None, None, None, True),
]

PIP_CASES = [
    ("pip-local", "torch==2.5.1+cu121", "2.5.1+cu121"),
    ("pip-pre", "torch==2.5.1rc1", "2.5.1rc1"),
    ("pip-post", "torch==2.5.1.post1", "2.5.1.post1"),
    ("pip-dev", "torch==2.5.1.dev1", "2.5.1.dev1"),
    ("pip-epoch", "torch==1!2.5.1", "1!2.5.1"),
    ("pip-wildcard", "torch==2.5.*", None),
    ("pip-arbitrary", "torch===2.5.1", None),
    ("pip-range", "torch>=2.5", None),
]

SPECIFIER_GAP_CASES = frozenset(
    {
        "compound",
        "wildcard-version",
        "wildcard-build",
        "empty-version",
        "empty-build",
        "extra-part",
        "triple-equality",
        "suffix-pre",
        "suffix-post",
        "suffix-local",
        "epoch",
        "trailing-version-dot",
        "empty-version-component",
        "signed-version",
        "unicode-version",
        "unicode-build",
        "space-in-version",
        "slash-in-build",
        "bracket",
        "regex",
    }
)


@pytest.mark.parametrize(
    ("case_id", "entry", "expected_exact", "expected_name", "expected_specifier", "diagnosed"),
    CONDA_CASES,
    ids=[case[0] for case in CONDA_CASES],
)
def test_conda_support_matrix_and_public_consumers(
    tmp_path: Path,
    case_id: str,
    entry: str,
    expected_exact: str | None,
    expected_name: str | None,
    expected_specifier: str | None,
    diagnosed: bool,
) -> None:
    # JSON quoting is valid YAML and avoids fixture quoting changing the input string.
    (tmp_path / "environment.yml").write_text(
        "name: synthetic\ndependencies:\n  - " + json.dumps(entry, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "train.py").write_text("import torch\n", encoding="utf-8")
    ctx = AuditContext(tmp_path)
    assert ctx.deps.manifest_present
    assert ctx.deps.lockfiles == []
    declarations = ctx.deps.declarations
    assert len(declarations) == (0 if expected_name is None else 1)
    if declarations:
        declaration = declarations[0]
        assert declaration.name == expected_name
        assert declaration.exact_version == expected_exact
        assert declaration.is_exact == (expected_exact is not None)
        assert declaration.specifier == expected_specifier
        assert declaration.source_file == "environment.yml"
        # Preserve existing YAML entry indices; physical fixture line is independently 3.
        assert declaration.line == 1
    assert ctx.deps.unparsed == (
        ["environment.yml:1: unsupported conda declaration"] if diagnosed else []
    )
    critical = LlmCriticalDepsPinnedRule().check(ctx)
    assert len(critical) == (0 if expected_exact is not None else 1)
    lock = LockfilePresentRule().check(ctx)
    assert len(lock) == 1
    omitted = case_id in {"channel", "channel-subdir", "empty-name", "empty-input"}
    specifier_gap = case_id in SPECIFIER_GAP_CASES
    assert ctx.deps.declaration_read_issues == (
        {"environment.yml": "unparsed_conda"}
        if omitted
        else {"environment.yml": "unparsed_conda_specifier"}
        if specifier_gap
        else {}
    )
    for finding in critical:
        assert finding.status == (
            FindingStatus.SKIPPED if omitted or specifier_gap else FindingStatus.FAIL
        )
        assert finding.severity == (Severity.INFO if omitted or specifier_gap else Severity.WARNING)
    for finding in lock:
        assert finding.status == FindingStatus.FAIL
        assert finding.severity == Severity.WARNING
    if critical:
        assert critical[0].evidence[0].path == (
            "environment.yml" if expected_name is not None else "train.py"
        )
        assert critical[0].evidence[0].line == 1


@pytest.mark.parametrize(
    ("case_id", "entry", "expected_exact"), PIP_CASES, ids=[case[0] for case in PIP_CASES]
)
def test_embedded_pip_keeps_python_exact_contract(
    tmp_path: Path, case_id: str, entry: str, expected_exact: str | None
) -> None:
    (tmp_path / "environment.yml").write_text(
        "name: synthetic\ndependencies:\n  - pip:\n      - " + json.dumps(entry) + "\n",
        encoding="utf-8",
    )
    ctx = AuditContext(tmp_path)
    assert ctx.deps.manifest_present
    assert ctx.deps.lockfiles == []
    assert len(ctx.deps.declarations) == 1
    declaration = ctx.deps.declarations[0]
    assert declaration.name == "torch"
    assert declaration.source_file == "environment.yml"
    assert declaration.line == 1  # Physical input line is 4; existing YAML contract retained.
    assert declaration.exact_version == expected_exact
    assert declaration.is_exact == (expected_exact is not None)
    assert len(LlmCriticalDepsPinnedRule().check(ctx)) == (0 if expected_exact is not None else 1)
    assert len(LockfilePresentRule().check(ctx)) == 1


def test_python_prefix_is_declared_without_being_exact(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text("dependencies:\n  - python=3.11\n")
    ctx = AuditContext(tmp_path)
    declaration = ctx.deps.declarations[0]
    assert declaration.name == "python"
    assert declaration.exact_version is None
    assert declaration.specifier == "=3.11"
    assert not declaration.is_exact
    assert PythonVersionDeclaredRule().check(ctx) == []


@pytest.mark.security
@pytest.mark.parametrize(
    ("entry", "unsafe_marker"),
    [
        (
            "torch=2.5.1=/tmp/SyntheticCondaMachineUser/private-build",
            "/tmp/SyntheticCondaMachineUser/private-build",
        ),
        (
            "torch=2.5.1=https://example.invalid/?api_key=SyntheticSecretCanaryABC123",
            "SyntheticSecretCanaryABC123",
        ),
    ],
    ids=["absolute-build", "url-secret-build"],
)
def test_unknown_conda_evidence_does_not_echo_machine_paths_or_secrets(
    tmp_path: Path, entry: str, unsafe_marker: str
) -> None:
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - " + json.dumps(entry) + "\n", encoding="utf-8"
    )
    result = CliRunner().invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "never"]
    )
    assert result.exit_code == 0
    assert unsafe_marker not in result.stdout
    context = AuditContext(tmp_path)
    assert context.deps.declarations[0].specifier == "(unsupported conda declaration)"
    assert context.deps.declarations[0].exact_version is None
    assert context.deps.unparsed == ["environment.yml:1: unsupported conda declaration"]
    assert context.deps.declaration_read_issues == {"environment.yml": "unparsed_conda_specifier"}
    findings = json.loads(result.stdout)["findings"]
    critical = [item for item in findings if item["rule_id"] == "env.llm_critical_deps_pinned"]
    assert len(critical) == 1
    assert critical[0]["status"] == FindingStatus.SKIPPED.value
    assert critical[0]["severity"] == Severity.INFO.value
    assert critical[0]["evidence"][0]["value"] == "(unsupported conda declaration)"


@pytest.mark.parametrize(
    ("entry", "exact", "uncertain"),
    [
        ("torch=2.5.1", False, False),
        ("torch==2.5.1", True, False),
        ("torch=2.5.1=cuda12.1", True, False),
        ("torch==2.5.1=py_0+cuda-12", True, False),
        ("torch=2.5.1=cuda*", False, True),
        ("conda-forge::torch==2.5.1", False, True),
    ],
)
def test_real_audit_json_agrees_with_conda_version_and_lock_consumers(
    tmp_path: Path, entry: str, exact: bool, uncertain: bool
) -> None:
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - " + json.dumps(entry) + "\n", encoding="utf-8"
    )
    (tmp_path / "train.py").write_text("import torch\n", encoding="utf-8")
    result = CliRunner().invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "never"]
    )
    assert result.exit_code == 0, result.stdout
    findings = json.loads(result.stdout)["findings"]
    selected = {"env.llm_critical_deps_pinned", "env.lockfile_present"}
    by_rule = {
        finding["rule_id"]: finding for finding in findings if finding["rule_id"] in selected
    }
    assert set(by_rule) == selected
    assert by_rule["env.llm_critical_deps_pinned"]["status"] == (
        FindingStatus.PASS.value
        if exact
        else FindingStatus.SKIPPED.value
        if uncertain
        else FindingStatus.FAIL.value
    )
    assert by_rule["env.lockfile_present"]["status"] == FindingStatus.FAIL.value
    warnings = {
        finding["rule_id"]
        for finding in findings
        if finding["rule_id"] in selected
        and finding["status"] == FindingStatus.FAIL.value
        and finding["severity"] == Severity.WARNING.value
    }
    assert warnings == ({"env.lockfile_present"} if exact or uncertain else selected)
