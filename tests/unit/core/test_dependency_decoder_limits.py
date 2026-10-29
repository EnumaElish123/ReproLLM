"""Known decoder limits retain bounded dependency evidence without fabricated credit."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from reprollm.core._toml import tomllib
from reprollm.core.deps import scan_dependencies
from reprollm.core.engine import run_audit
from reprollm.core.git import inspect_git
from reprollm.core.scanner import RepoScanner

_MARKER = "synthetic-dependency-decoder-limit"
_CANARY = "SyntheticDependencyDecoderPrivateCanary"
_DECLARATIONS = {"pyproject.toml", "Pipfile", "environment.yml"}
_FORMATS = [
    "pyproject.toml",
    "Pipfile",
    "environment.yml",
    "uv.lock",
    "poetry.lock",
    "Pipfile.lock",
    "conda-lock.yml",
]
_BODIES = {
    "pyproject.toml": f'# {_MARKER}\n[project]\ndependencies=["torch>=2"]\n',
    "Pipfile": f'# {_MARKER}\n[packages]\ntorch=">=2"\n',
    "environment.yml": f"# {_MARKER}\ndependencies:\n  - pip:\n      - torch>=2\n",
    "uv.lock": f'# {_MARKER}\n[[package]]\nname="torch"\nversion="2.4.0"\n',
    "poetry.lock": f'# {_MARKER}\n[[package]]\nname="torch"\nversion="2.4.0"\n',
    "Pipfile.lock": json.dumps({"marker": _MARKER, "default": {"torch": {"version": "==2.4.0"}}}),
    "conda-lock.yml": f"# {_MARKER}\npackage:\n  - name: torch\n    version: 2.4.0\n",
}


def _write(root: Path, source: str, body: str) -> None:
    path = root / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _inputs(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _project(root: Path, filename: str) -> tuple[str, dict[str, Any]]:
    _write(root, "pyproject.toml", '[project]\nname="parent"\ndependencies=[]\n')
    _write(root, "uv.lock", '[[package]]\nname="torch"\nversion="2.4.0"\n')
    _write(root, "preserved/requirements.txt", "tokenizers==0.20.0\n")
    _write(root, "broken/train.py", "import torch\n")
    source = "broken/" + filename
    _write(root, source, _BODIES[filename])
    if filename in _DECLARATIONS:
        return source, _file_evidence("broken/train.py", line=1, note="imported")
    if filename in {"uv.lock", "poetry.lock"}:
        manifest, body, line = (
            "broken/pyproject.toml",
            '[project]\nname="child"\ndependencies=["torch>=2"]\n',
            3,
        )
    elif filename == "Pipfile.lock":
        manifest, body, line = "broken/Pipfile", '[packages]\ntorch=">=2"\n', 2
    else:
        manifest, body, line = (
            "broken/environment.yml",
            "dependencies:\n  - pip:\n      - torch>=2\n",
            1,
        )
    _write(root, manifest, body)
    return source, _file_evidence(manifest, line=line, value=">=2", note="declared as >=2")


def _file_evidence(
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


def _faults(monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]) -> list[str]:
    observed: list[str] = []

    def limited(original: Callable[..., Any], name: str) -> Callable[..., Any]:
        def decode(body: object, *args: Any, **kwargs: Any) -> Any:
            if isinstance(body, str) and _MARKER in body:
                observed.append(name)
                raise failure_type(_CANARY)
            return original(body, *args, **kwargs)

        return decode

    monkeypatch.setattr(tomllib, "loads", limited(tomllib.loads, "toml"))
    monkeypatch.setattr(json, "loads", limited(json.loads, "json"))
    monkeypatch.setattr(yaml, "safe_load", limited(yaml.safe_load, "yaml"))
    return observed


def _pin_finding(message: str, evidence: list[dict[str, Any]], hint: str) -> dict[str, Any]:
    return {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 0,
        "message": message,
        "evidence": evidence,
        "fix_hint": hint,
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.security
@pytest.mark.parametrize("filename", _FORMATS)
def test_decoder_recursion_preserves_typed_uncertainty_and_complete_rule_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    source, use = _project(tmp_path, filename)
    before = _inputs(tmp_path)
    observed = _faults(monkeypatch, RecursionError)

    result = scan_dependencies(RepoScanner(tmp_path, inspect_git(tmp_path)))

    assert observed
    assert result.manifest_present is True
    assert [(d.name, d.exact_version) for d in result.declarations if d.is_exact] == [
        ("tokenizers", "0.20.0")
    ]
    assert result.qualified_lock_packages([("torch", "broken/train.py")]) == frozenset(
        {"tokenizers"}
    )
    if filename in _DECLARATIONS:
        assert result.declaration_read_issues == {source: "parser_limit"}
        assert result.unparsed == [f"{source}:0: decoder recursion limit; skipped"]
        assert result.unverified_lock_paths([("torch", "broken/train.py")]) == {}
        note = "torch possible exact declaration unverified"
        message = (
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established"
        )
        hint = (
            "Review torch declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        )
    else:
        assert result.declaration_read_issues == {}
        failed = [lock for lock in result.lockfiles if lock.path == source]
        assert len(failed) == 1
        assert failed[0].read_issue == "parser_limit"
        assert failed[0].packages == frozenset()
        assert result.unverified_lock_paths([("torch", "broken/train.py")]) == {"torch": (source,)}
        note = "torch associated; lock package contents unverified"
        message = (
            "torch is used; an associated format lock could not be read or parsed, "
            "so missing pin evidence is not established"
        )
        hint = (
            "Review torch declarations and associated format-lock files; restore readable, "
            "valid lock contents before deciding that exact pin evidence is absent."
        )
    diagnostics: list[str] = []

    report = run_audit(tmp_path, diagnostics=diagnostics)

    findings = [
        item.model_dump(mode="json")
        for item in report.findings
        if item.rule_id == "env.llm_critical_deps_pinned"
    ]
    assert findings == [_pin_finding(message, [use, _file_evidence(source, note=note)], hint)]
    presence = next(item for item in report.findings if item.rule_id == "env.lockfile_present")
    assert (presence.status.value, presence.severity.value) == ("pass", "PASS")
    shared = report.model_dump_json() + json.dumps(diagnostics)
    assert _CANARY not in shared
    assert str(tmp_path) not in shared
    assert _inputs(tmp_path) == before


@pytest.mark.parametrize("filename", ["pyproject.toml", "Pipfile.lock", "environment.yml"])
@pytest.mark.parametrize("failure_type", [MemoryError, ValueError])
def test_unrelated_decoder_failures_remain_visible_to_the_caller(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    failure_type: type[Exception],
) -> None:
    _project(tmp_path, filename)
    before = _inputs(tmp_path)
    observed = _faults(monkeypatch, failure_type)

    with pytest.raises(failure_type, match=_CANARY):
        scan_dependencies(RepoScanner(tmp_path, inspect_git(tmp_path)))

    assert observed
    assert _inputs(tmp_path) == before


def test_other_qualified_and_exact_credit_win_despite_both_decoder_limit_kinds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, _ = _project(tmp_path, "pyproject.toml")
    _write(tmp_path, "pyproject.toml", '[project]\ndependencies=["torch>=2"]\n')
    _write(tmp_path, "broken/poetry.lock", _BODIES["poetry.lock"])
    before = _inputs(tmp_path)
    _faults(monkeypatch, RecursionError)

    result = scan_dependencies(RepoScanner(tmp_path, inspect_git(tmp_path)))

    assert result.declaration_read_issues == {source: "parser_limit"}
    assert next(
        lock for lock in result.lockfiles if lock.path == "broken/poetry.lock"
    ).read_issue == ("parser_limit")
    assert result.qualified_lock_packages([("torch", "broken/train.py")]) == frozenset(
        {"tokenizers", "torch"}
    )
    report = run_audit(tmp_path)
    findings = [item for item in report.findings if item.rule_id == "env.llm_critical_deps_pinned"]
    assert len(findings) == 1
    assert (findings[0].status.value, findings[0].severity.value) == ("pass", "PASS")
    assert findings[0].evidence == []
    assert _CANARY not in report.model_dump_json()
    assert _inputs(tmp_path) == before
