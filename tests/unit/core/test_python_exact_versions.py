"""Independent format and consumer regressions for R05-A Python exact versions."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.rules.env import LlmCriticalDepsPinnedRule, LockfilePresentRule
from reprollm.schemas.finding import FindingStatus, Severity


def test_wildcard_does_not_prove_exact_version_lock_or_critical_pin(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("# input\n\ntorch==2.5.*\n")
    context = AuditContext(tmp_path)
    declarations = context.deps.declarations
    assert len(declarations) == 1
    declaration = declarations[0]
    assert declaration.name == "torch"
    assert declaration.source_file == "requirements.txt"
    assert declaration.line == 3
    assert declaration.specifier == "==2.5.*"
    assert declaration.exact_version is None
    assert not declaration.is_exact
    assert context.deps.lockfiles == []
    lock_findings = LockfilePresentRule().check(context)
    assert len(lock_findings) == 1
    assert lock_findings[0].status == FindingStatus.FAIL
    assert lock_findings[0].severity == Severity.WARNING
    critical_findings = LlmCriticalDepsPinnedRule().check(context)
    assert len(critical_findings) == 1
    assert critical_findings[0].status == FindingStatus.FAIL
    assert critical_findings[0].severity == Severity.WARNING
    assert critical_findings[0].evidence[0].path == "requirements.txt"
    assert critical_findings[0].evidence[0].line == 3


@pytest.mark.parametrize("format_name", ["poetry", "pipfile"])
def test_local_version_in_each_version_field_pins_critical_dependency(
    tmp_path: Path, format_name: str
) -> None:
    filename, table = (
        ("pyproject.toml", "tool.poetry.dependencies")
        if format_name == "poetry"
        else ("Pipfile", "packages")
    )
    (tmp_path / filename).write_text(f'[{table}]\n\ntorch = "==2.5.1+cu121"\n')
    context = AuditContext(tmp_path)
    assert len(context.deps.declarations) == 1
    declaration = context.deps.declarations[0]
    assert declaration.source_file == filename
    assert declaration.line == 3
    assert declaration.exact_version == "2.5.1+cu121"
    assert declaration.is_exact
    assert context.deps.lockfiles == []
    assert LlmCriticalDepsPinnedRule().check(context) == []
    findings = LockfilePresentRule().check(context)
    assert len(findings) == 1
    assert findings[0].status == FindingStatus.FAIL


@pytest.mark.parametrize("format_name", ["poetry", "pipfile"])
@pytest.mark.parametrize("transport", ["url", "git", "path", "file", "hg", "svn", "bzr"])
def test_transport_table_is_not_an_exact_python_version(
    tmp_path: Path, format_name: str, transport: str
) -> None:
    filename, table = (
        ("pyproject.toml", "tool.poetry.dependencies")
        if format_name == "poetry"
        else ("Pipfile", "packages")
    )
    value = f'{{version = "==2.5.1", {transport} = "placeholder"}}'
    (tmp_path / filename).write_text(f"[{table}]\n\ntorch = {value}\n")
    context = AuditContext(tmp_path)
    declaration = context.deps.declarations[0]
    assert declaration.source_file == filename
    assert declaration.line == 3
    assert declaration.exact_version is None
    assert not declaration.is_exact
    assert declaration.specifier == "==2.5.1"
    assert context.deps.lockfiles == []
    findings = LlmCriticalDepsPinnedRule().check(context)
    assert len(findings) == 1
    assert findings[0].status == FindingStatus.FAIL


@pytest.mark.parametrize("format_name", ["poetry", "pipfile"])
@pytest.mark.parametrize("value", ['[{version = "==2.5.1", python = "<3.10"}]', "42", "true"])
def test_unsupported_version_field_types_are_nonexact_without_crashing(
    tmp_path: Path, format_name: str, value: str
) -> None:
    filename, table = (
        ("pyproject.toml", "tool.poetry.dependencies")
        if format_name == "poetry"
        else ("Pipfile", "packages")
    )
    (tmp_path / filename).write_text(f"[{table}]\n\ntorch = {value}\n")
    context = AuditContext(tmp_path)
    assert len(context.deps.declarations) == 1
    declaration = context.deps.declarations[0]
    assert declaration.source_file == filename
    assert declaration.line == 3
    assert declaration.exact_version is None
    assert not declaration.is_exact
    assert context.deps.lockfiles == []
    assert len(LlmCriticalDepsPinnedRule().check(context)) == 1


def _write_format(tmp_path: Path, format_name: str, expression: str) -> tuple[str, int]:
    if format_name == "requirements":
        filename, line = "requirements.txt", 2
        text = f"# independent exact-version fixture\ntorch{expression}\n"
    elif format_name == "pep621":
        filename, line = "pyproject.toml", 5
        requirement = json.dumps(f"torch{expression}")
        text = (
            '[project]\nname = "sample"\nrequires-python = ">=3.10"\n'
            f"dependencies = [\n  {requirement},\n]\n"
        )
    elif format_name == "poetry":
        filename, line = "pyproject.toml", 4
        text = (
            '[tool.poetry]\nname = "sample"\n[tool.poetry.dependencies]\n'
            f"torch = {json.dumps(expression)}\n"
        )
    else:
        assert format_name == "pipfile"
        filename, line = "Pipfile", 2
        text = f"[packages]\ntorch = {json.dumps(expression)}\n"
    (tmp_path / filename).write_text(text)
    (tmp_path / "control.py").write_text("import torch\n")
    return filename, line


def _assert_format_consumers(
    tmp_path: Path, filename: str, line: int, expected_exact: str | None
) -> None:
    context = AuditContext(tmp_path)
    declarations = context.deps.declarations
    if expected_exact is None:
        assert all(item.exact_version is None and not item.is_exact for item in declarations)
    else:
        assert len(declarations) == 1
        assert declarations[0].name == "torch"
        assert declarations[0].display_name == "torch"
        assert declarations[0].exact_version == expected_exact
        assert declarations[0].is_exact
    for declaration in declarations:
        assert declaration.source_file == filename
        assert declaration.line == line
    expected_lock = filename == "requirements.txt" and expected_exact is not None
    assert [(lock.path, lock.packages) for lock in context.deps.lockfiles] == (
        [(filename, frozenset({"torch"}))] if expected_lock else []
    )
    lock_findings = LockfilePresentRule().check(context)
    assert len(lock_findings) == (0 if expected_lock else 1)
    critical_findings = LlmCriticalDepsPinnedRule().check(context)
    assert len(critical_findings) == (0 if expected_exact is not None else 1)
    for finding in lock_findings + critical_findings:
        assert finding.status == FindingStatus.FAIL
        assert finding.severity == Severity.WARNING
    if critical_findings and any(item.name == "torch" for item in declarations):
        assert critical_findings[0].evidence[0].path == filename
        assert critical_findings[0].evidence[0].line == line


@pytest.mark.parametrize("format_name", ["requirements", "pep621", "poetry", "pipfile"])
@pytest.mark.parametrize(
    ("kind", "expression", "expected_exact"),
    [
        ("release", "==2.5.1", "2.5.1"),
        ("local", "==2.5.1+cu121", "2.5.1+cu121"),
        ("pre", "==2.5.1rc1", "2.5.1rc1"),
        ("post", "==2.5.1.post1", "2.5.1.post1"),
        ("dev", "==2.5.1.dev1", "2.5.1.dev1"),
        ("epoch", "==1!2.5.1", "1!2.5.1"),
        ("wildcard", "==2.5.*", None),
        ("range", ">=2.5", None),
        ("compatible", "~=2.5", None),
        ("multiclause", "==2.5.1,>=2", None),
        ("arbitrary", "===2.5.1", None),
        ("malformed", "==", None),
        ("bare", "2.5.1", None),
    ],
    ids=lambda value: value if isinstance(value, str) else "nonexact",
)
def test_accepted_format_table(
    tmp_path: Path, format_name: str, kind: str, expression: str, expected_exact: str | None
) -> None:
    # The accepted table uses Poetry's bare form for the six valid releases.
    if format_name == "poetry":
        if expected_exact is not None:
            expression = expected_exact
        elif kind == "bare":
            expected_exact = "2.5.1"
    filename, line = _write_format(tmp_path, format_name, expression)
    _assert_format_consumers(tmp_path, filename, line, expected_exact)


@pytest.mark.parametrize("format_name", ["requirements", "pep621"])
@pytest.mark.parametrize(
    ("expression", "expected_exact"),
    [
        ('[extra]==2.5.1; python_version >= "3.10"', "2.5.1"),
        (" @ https://example.invalid/torch.whl", None),
    ],
)
def test_accepted_requirement_modifiers_and_url(
    tmp_path: Path, format_name: str, expression: str, expected_exact: str | None
) -> None:
    filename, line = _write_format(tmp_path, format_name, expression)
    _assert_format_consumers(tmp_path, filename, line, expected_exact)
    if format_name == "requirements" and expected_exact is None:
        assert AuditContext(tmp_path).deps.unparsed == [
            f"{filename}:{line}: torch @ https://example.invalid/torch.whl"
        ]


@pytest.mark.parametrize("format_name", ["poetry", "pipfile"])
def test_accepted_explicit_local_version(tmp_path: Path, format_name: str) -> None:
    filename, line = _write_format(tmp_path, format_name, "==2.5.1+cu121")
    _assert_format_consumers(tmp_path, filename, line, "2.5.1+cu121")


@pytest.mark.parametrize("format_name", ["requirements", "pep621", "poetry", "pipfile"])
@pytest.mark.parametrize("expression", ["==2.5.*", "==2.5.1+cu121"])
def test_audit_json_agrees_with_exact_version_consumers(
    tmp_path: Path, format_name: str, expression: str
) -> None:
    _write_format(tmp_path, format_name, expression)
    result = CliRunner().invoke(
        app, ["audit", str(tmp_path), "--format", "json", "--fail-on", "never"]
    )
    assert result.exit_code == 0, result.output
    findings = json.loads(result.output)["findings"]
    rule_ids = {"env.lockfile_present", "env.llm_critical_deps_pinned"}
    statuses = {
        finding["rule_id"]: finding["status"]
        for finding in findings
        if finding["rule_id"] in rule_ids
    }
    exact = expression == "==2.5.1+cu121"
    assert statuses == {
        "env.lockfile_present": FindingStatus.PASS.value
        if format_name == "requirements" and exact
        else FindingStatus.FAIL.value,
        "env.llm_critical_deps_pinned": FindingStatus.PASS.value
        if exact
        else FindingStatus.FAIL.value,
    }
    warnings = {
        finding["rule_id"]
        for finding in findings
        if finding["rule_id"] in rule_ids
        and finding["status"] == FindingStatus.FAIL.value
        and finding["severity"] == Severity.WARNING.value
    }
    expected_warnings = set()
    if not exact:
        expected_warnings = rule_ids
    elif format_name != "requirements":
        expected_warnings = {"env.lockfile_present"}
    assert warnings == expected_warnings


@pytest.mark.parametrize("format_name", ["poetry", "pipfile"])
@pytest.mark.parametrize(
    "version", ["2.5.1", "2.5.1+cu121", "2.5.1rc1", "2.5.1.post1", "2.5.1.dev1", "1!2.5.1"]
)
def test_version_tables_keep_supported_versions_with_extras_and_markers(
    tmp_path: Path, format_name: str, version: str
) -> None:
    filename, table = (
        ("pyproject.toml", "tool.poetry.dependencies")
        if format_name == "poetry"
        else ("Pipfile", "packages")
    )
    expression = version if format_name == "poetry" else f"=={version}"
    (tmp_path / filename).write_text(
        f'[{table}]\n\ntorch = {{version = "{expression}", extras = ["extra"], '
        "markers = \"python_version >= '3.10'\"}\n"
    )
    _assert_format_consumers(tmp_path, filename, 3, version)


@pytest.mark.parametrize("format_name", ["optional", "embedded_pip"])
@pytest.mark.parametrize(
    ("expression", "expected_exact"),
    [
        ("==2.5.1", "2.5.1"),
        ("==2.5.1+cu121", "2.5.1+cu121"),
        ("==2.5.1rc1", "2.5.1rc1"),
        ("==2.5.1.post1", "2.5.1.post1"),
        ("==2.5.1.dev1", "2.5.1.dev1"),
        ("==1!2.5.1", "1!2.5.1"),
        ("==2.5.*", None),
        ("===2.5.1", None),
        ('[extra]==2.5.1; python_version >= "3.10"', "2.5.1"),
    ],
)
def test_optional_and_embedded_pip_share_python_exact_contract(
    tmp_path: Path, format_name: str, expression: str, expected_exact: str | None
) -> None:
    requirement = f"torch{expression}"
    if format_name == "optional":
        filename = "pyproject.toml"
        (tmp_path / filename).write_text(
            '[project]\nname = "sample"\n[project.optional-dependencies]\ntrain = [\n'
            f"  {json.dumps(requirement)},\n]\n"
        )
        _assert_format_consumers(tmp_path, filename, 5, expected_exact)
    else:
        filename = "environment.yml"
        (tmp_path / filename).write_text(f"dependencies:\n  - pip:\n      - {requirement}\n")
        context = AuditContext(tmp_path)
        assert len(context.deps.declarations) == 1
        declaration = context.deps.declarations[0]
        assert declaration.name == "torch"
        assert declaration.source_file == filename
        assert declaration.exact_version == expected_exact
        assert declaration.is_exact == (expected_exact is not None)
        assert len(LlmCriticalDepsPinnedRule().check(context)) == (
            0 if expected_exact is not None else 1
        )
        assert context.deps.lockfiles == []


@pytest.mark.parametrize("format_name", ["requirements", "pep621", "poetry", "pipfile"])
def test_repeated_identical_clause_remains_one_exact_constraint(
    tmp_path: Path, format_name: str
) -> None:
    filename, line = _write_format(tmp_path, format_name, "==2.5.1,==2.5.1")
    _assert_format_consumers(tmp_path, filename, line, "2.5.1")


@pytest.mark.parametrize("expression", ["^2.5", "~2.5", "2.5.*", "*", ""])
def test_poetry_nonexact_syntax_does_not_borrow_requirement_or_bare_rules(
    tmp_path: Path, expression: str
) -> None:
    filename, line = _write_format(tmp_path, "poetry", expression)
    _assert_format_consumers(tmp_path, filename, line, None)


@pytest.mark.parametrize("shadow", ["comment", "description"])
@pytest.mark.parametrize("inline", [True, False])
def test_escaped_marker_source_is_the_dependency_array_not_a_shadow_string(
    tmp_path: Path, shadow: str, inline: bool
) -> None:
    requirement = json.dumps('torch[extra]==2.5.1; python_version >= "3.10"')
    prefix = f"# {requirement}" if shadow == "comment" else f"description = {requirement}"
    dependencies = (
        f"dependencies = [{requirement}]\n"
        if inline
        else f"dependencies = [\n  {requirement},\n]\n"
    )
    (tmp_path / "pyproject.toml").write_text(
        f'[project]\nname = "sample"\n{prefix}\n{dependencies}'
    )
    _assert_format_consumers(tmp_path, "pyproject.toml", 4 if inline else 5, "2.5.1")
