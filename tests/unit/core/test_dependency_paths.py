"""R06-A regressions: retain full paths independently of manifest qualification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.core.deps import Declarations, scan_dependencies
from reprollm.core.git import inspect_git
from reprollm.core.scanner import RepoScanner
from reprollm.rules.env import LlmCriticalDepsPinnedRule, PythonVersionDeclaredRule


def _write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _scan(root: Path) -> Declarations:
    return scan_dependencies(RepoScanner(root, inspect_git(root)))


def _declaration_text(basename: str, package: str, version: str) -> str:
    if basename == "pyproject.toml":
        return (
            '[project]\nname = "example"\nrequires-python = ">=3.10"\n'
            f'dependencies = ["{package}=={version}"]\n'
        )
    if basename == "Pipfile":
        return f'[packages]\n{package} = "=={version}"\n'
    return f"dependencies:\n  - {package}=={version}\n  - python=3.11\n"


@pytest.mark.parametrize("nested", ["a_tools/pyproject.toml", "zz_tools/pyproject.toml"])
def test_root_project_survives_tool_only_pyproject(tmp_path: Path, nested: str) -> None:
    _write(tmp_path, "pyproject.toml", _declaration_text("pyproject.toml", "torch", "2.8.0"))
    _write(tmp_path, nested, "[tool.ruff]\nline-length = 100\n")

    result = _scan(tmp_path)
    assert result.manifest_present
    assert [(d.name, d.source_file, d.line) for d in result.declarations] == [
        ("torch", "pyproject.toml", 4)
    ]
    assert PythonVersionDeclaredRule().check(AuditContext(tmp_path)) == []


@pytest.mark.parametrize(
    "basename", ["pyproject.toml", "environment.yml", "environment.yaml", "Pipfile"]
)
def test_all_qualified_declarations_keep_full_source_paths(tmp_path: Path, basename: str) -> None:
    _write(tmp_path, basename, _declaration_text(basename, "torch", "2.8.0"))
    _write(tmp_path, f"a_nested/{basename}", _declaration_text(basename, "numpy", "1.26.0"))

    result = _scan(tmp_path)
    assert result.manifest_present
    assert [(d.name, d.source_file) for d in result.declarations if d.name != "python"] == [
        ("torch", basename),
        ("numpy", f"a_nested/{basename}"),
    ]
    assert all(d.line > 0 for d in result.declarations)


@pytest.mark.parametrize(
    "basename", ["pyproject.toml", "environment.yml", "environment.yaml", "Pipfile"]
)
def test_nested_only_candidates_remain_qualified(tmp_path: Path, basename: str) -> None:
    _write(tmp_path, f"a_nested/{basename}", _declaration_text(basename, "torch", "2.8.0"))
    _write(tmp_path, f"z_nested/{basename}", _declaration_text(basename, "numpy", "1.26.0"))

    result = _scan(tmp_path)
    assert result.manifest_present
    assert [(d.name, d.source_file) for d in result.declarations if d.name != "python"] == [
        ("torch", f"a_nested/{basename}"),
        ("numpy", f"z_nested/{basename}"),
    ]


def _lock_text(basename: str, package: str) -> str:
    if basename in {"uv.lock", "poetry.lock"}:
        return f'[[package]]\nname = "{package}"\nversion = "1.0"\n'
    if basename == "Pipfile.lock":
        return json.dumps({"default": {package: {"version": "==1.0"}}, "develop": {}})
    return f"package:\n  - name: {package}\n    version: 1.0\n"


@pytest.mark.parametrize("basename", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
def test_same_named_locks_keep_separate_package_evidence(tmp_path: Path, basename: str) -> None:
    _write(tmp_path, basename, _lock_text(basename, "torch"))
    _write(tmp_path, f"a_nested/{basename}", _lock_text(basename, "numpy"))

    result = _scan(tmp_path)
    assert [(lock.path, lock.packages) for lock in result.lockfiles] == [
        (basename, frozenset({"torch"})),
        (f"a_nested/{basename}", frozenset({"numpy"})),
    ]


@pytest.mark.parametrize("basename", ["uv.lock", "poetry.lock", "Pipfile.lock", "conda-lock.yml"])
def test_nested_only_locks_keep_every_source(tmp_path: Path, basename: str) -> None:
    _write(tmp_path, f"a_nested/{basename}", _lock_text(basename, "torch"))
    _write(tmp_path, f"z_nested/{basename}", _lock_text(basename, "numpy"))

    result = _scan(tmp_path)
    assert [(lock.path, lock.packages) for lock in result.lockfiles] == [
        (f"a_nested/{basename}", frozenset({"torch"})),
        (f"z_nested/{basename}", frozenset({"numpy"})),
    ]


@pytest.mark.parametrize(
    "basename", ["pyproject.toml", ".python-version", "environment.yml", "environment.yaml"]
)
def test_python_version_selection_prefers_root_source(tmp_path: Path, basename: str) -> None:
    content = (
        "3.11\n" if basename == ".python-version" else _declaration_text(basename, "torch", "2.8.0")
    )
    _write(tmp_path, basename, content)
    _write(tmp_path, f"a_nested/{basename}", content)

    ctx = AuditContext(tmp_path)
    assert PythonVersionDeclaredRule().check(ctx) == []
    evidence = PythonVersionDeclaredRule._declared_where(ctx)
    assert evidence is not None
    assert evidence.path == basename


def test_python_nested_source_is_reported_with_its_actual_path(tmp_path: Path) -> None:
    _write(tmp_path, "nested/.python-version", "3.11\n")
    evidence = PythonVersionDeclaredRule._declared_where(AuditContext(tmp_path))
    assert evidence is not None
    assert evidence.path == "nested/.python-version"


@pytest.mark.parametrize("root_content", ["[tool.ruff]\nline-length = 100\n", "[project broken\n"])
def test_nonqualifying_root_does_not_hide_qualified_nested_project(
    tmp_path: Path, root_content: str
) -> None:
    _write(tmp_path, "pyproject.toml", root_content)
    _write(
        tmp_path,
        "nested/pyproject.toml",
        _declaration_text("pyproject.toml", "torch", "2.8.0"),
    )
    result = _scan(tmp_path)
    assert result.manifest_present
    assert [(d.name, d.source_file) for d in result.declarations] == [
        ("torch", "nested/pyproject.toml")
    ]
    assert PythonVersionDeclaredRule().check(AuditContext(tmp_path)) == []


def test_root_environment_alias_precedes_nested_other_extension(tmp_path: Path) -> None:
    _write(tmp_path, "environment.yaml", _declaration_text("environment.yaml", "torch", "2.8.0"))
    _write(
        tmp_path,
        "a_nested/environment.yml",
        _declaration_text("environment.yml", "numpy", "1.26.0"),
    )
    result = _scan(tmp_path)
    assert [(d.name, d.source_file) for d in result.declarations if d.name != "python"] == [
        ("torch", "environment.yaml"),
        ("numpy", "a_nested/environment.yml"),
    ]
    evidence = PythonVersionDeclaredRule._declared_where(AuditContext(tmp_path))
    assert evidence is not None
    assert evidence.path == "environment.yaml"


def test_tool_only_projects_do_not_qualify_by_root_priority(tmp_path: Path) -> None:
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    _write(tmp_path, "nested/pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    result = _scan(tmp_path)
    assert not result.manifest_present
    assert result.declarations == []
    assert result.lockfiles == []


def test_nested_requirements_keep_existing_aggregate_pinning_policy(tmp_path: Path) -> None:
    _write(tmp_path, "requirements.txt", "torch\nnumpy\n")
    _write(
        tmp_path,
        "scripts/nested/requirements.txt",
        "torch==2.8.0\nbitsandbytes==0.41.2.post2\nrequests>=2\n",
    )
    ctx = AuditContext(tmp_path)
    assert [(d.name, d.source_file) for d in ctx.deps.declarations] == [
        ("torch", "requirements.txt"),
        ("numpy", "requirements.txt"),
        ("torch", "scripts/nested/requirements.txt"),
        ("bitsandbytes", "scripts/nested/requirements.txt"),
        ("requests", "scripts/nested/requirements.txt"),
    ]
    assert not ctx.deps.lockfiles
    assert [f.message.split(" ")[0] for f in LlmCriticalDepsPinnedRule().check(ctx)] == ["numpy"]


def test_enumeration_order_does_not_change_complete_cli_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, "pyproject.toml", _declaration_text("pyproject.toml", "torch", "2.8.0"))
    _write(
        tmp_path,
        "a_nested/pyproject.toml",
        _declaration_text("pyproject.toml", "numpy", "1.26.0"),
    )
    _write(tmp_path, "zz_tools/pyproject.toml", "[tool.ruff]\nline-length = 100\n")
    _write(tmp_path, "uv.lock", _lock_text("uv.lock", "torch"))
    _write(tmp_path, "a_nested/uv.lock", _lock_text("uv.lock", "numpy"))
    paths = sorted(
        str(p.relative_to(tmp_path).as_posix()) for p in tmp_path.rglob("*") if p.is_file()
    )
    reports: list[str] = []
    for ordered in [paths, list(reversed(paths)), paths[2:] + paths[:2]]:
        monkeypatch.setattr(RepoScanner, "files", lambda self, selected=ordered: list(selected))
        result = CliRunner().invoke(
            app,
            ["audit", str(tmp_path), "--level", "0", "--format", "json", "--fail-on", "never"],
        )
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        report.pop("generated_at")
        reports.append(json.dumps(report, sort_keys=True, ensure_ascii=False))
    assert reports[0] == reports[1] == reports[2]


@pytest.mark.parametrize(
    ("basename", "malformed", "reason"),
    [
        ("pyproject.toml", "tool = 42\n", "invalid tool table"),
        ("environment.yml", "dependencies: 42\n", "invalid dependencies collection"),
        ("uv.lock", "package = 42\n", "invalid package collection"),
        ("poetry.lock", "package = 42\n", "invalid package collection"),
        ("Pipfile.lock", "[]\n", "invalid lock document"),
        ("conda-lock.yml", "package: 42\n", "invalid package collection"),
    ],
)
def test_newly_retained_malformed_candidate_keeps_root_facts_without_crashing(
    tmp_path: Path, basename: str, malformed: str, reason: str
) -> None:
    if basename in {"pyproject.toml", "environment.yml"}:
        root_text = _declaration_text(basename, "torch", "2.8.0")
    else:
        root_text = _lock_text(basename, "torch")
    _write(tmp_path, basename, root_text)
    _write(tmp_path, f"A_bad/{basename}", malformed)

    result = _scan(tmp_path)
    if basename in {"pyproject.toml", "environment.yml"}:
        assert result.manifest_present
        assert [(d.name, d.source_file) for d in result.declarations if d.name != "python"] == [
            ("torch", basename)
        ]
    else:
        assert [(lock.path, lock.packages) for lock in result.lockfiles] == [
            (basename, frozenset({"torch"})),
            (f"A_bad/{basename}", frozenset()),
        ]
    assert result.unparsed == [f"A_bad/{basename}:0: {reason}"]


@pytest.mark.parametrize("fallback", [False, True])
def test_python_rule_skips_newly_retained_scalar_project_and_keeps_fallback(
    tmp_path: Path, fallback: bool
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\nname = "root"\ndependencies = []\n')
    _write(tmp_path, "z_bad/pyproject.toml", "project = 42\n")
    if fallback:
        _write(tmp_path, ".python-version", "3.11\n")

    findings = PythonVersionDeclaredRule().check(AuditContext(tmp_path))
    if fallback:
        assert findings == []
    else:
        assert len(findings) == 1
        assert findings[0].rule_id == "env.python_version_declared"
        assert findings[0].message == "no Python version requirement is declared"


@pytest.mark.parametrize("table", ["project", "tool.poetry"])
def test_empty_project_table_keeps_existing_manifest_qualification(
    tmp_path: Path, table: str
) -> None:
    _write(tmp_path, "pyproject.toml", f"[{table}]\n")
    result = _scan(tmp_path)
    assert result.manifest_present
    assert result.declarations == []
    assert result.unparsed == []


@pytest.mark.parametrize("basename", ["uv.lock", "poetry.lock", "conda-lock.yml"])
def test_newly_retained_lock_package_name_type_does_not_crash_or_borrow_packages(
    tmp_path: Path, basename: str
) -> None:
    malformed = (
        "package:\n  - name: 42\n" if basename == "conda-lock.yml" else "[[package]]\nname = 42\n"
    )
    _write(tmp_path, basename, _lock_text(basename, "torch"))
    _write(tmp_path, f"A_bad/{basename}", malformed)

    result = _scan(tmp_path)
    assert [(lock.path, lock.packages) for lock in result.lockfiles] == [
        (basename, frozenset({"torch"})),
        (f"A_bad/{basename}", frozenset()),
    ]
    assert result.unparsed == [f"A_bad/{basename}:0: invalid package name"]


@pytest.mark.parametrize("requires", ["42", '[">=3.10"]', '{version = ">=3.10"}'])
def test_nonstring_python_requirement_does_not_hide_valid_fallback(
    tmp_path: Path, requires: str
) -> None:
    _write(tmp_path, "pyproject.toml", '[project]\nname = "root"\ndependencies = []\n')
    _write(tmp_path, "z_bad/pyproject.toml", f"[project]\nrequires-python = {requires}\n")
    _write(tmp_path, ".python-version", "3.11\n")
    context = AuditContext(tmp_path)
    assert PythonVersionDeclaredRule().check(context) == []
    evidence = PythonVersionDeclaredRule._declared_where(context)
    assert evidence is not None
    assert evidence.path == ".python-version"
