"""D-C complete consumer contracts, authored before the parser implementation."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml
from typer.testing import CliRunner

from reprollm import __version__
from reprollm.cli.main import app
from reprollm.core.pyscan import PyScanResult
from reprollm.schemas.finding import AuditReport
from tests.conftest import commit_all, make_git_repo

runner = CliRunner()
_PIN = "env.llm_critical_deps_pinned"
_HINT = "Pin the package exactly (see the message for the suggested version)."
_PASS = "Every LLM-critical dependency in use is pinned to an exact version."
_NO_USE = "no LLM-critical package is declared or imported"
_VETO = "# a conservative file veto \\\n"
_REASON = "Reviewed captured dependency declaration."


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _repo(tmp_path: Path, severity: str = "WARNING", mixed: bool = False) -> Path:
    repo = make_git_repo(tmp_path / "comments")
    profiles = repo / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated inline comment consumers.",
                "rules": [_PIN] + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {_PIN: severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: comments}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    return repo


def _requirements(repo: Path, body: str) -> None:
    (repo / "requirements.txt").write_text(body, encoding="utf-8")
    commit_all(repo)


def _evidence(path: str | None, note: str, **fields: Any) -> dict[str, Any]:
    return {
        "kind": "file",
        "path": path,
        "field": None,
        "line": None,
        "value": None,
        "expected": None,
        "note": note,
        **fields,
    }


def _pin_finding(
    state: str, severity: str = "WARNING", *, package: str = "torch", suppressed: bool = False
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "rule_id": _PIN,
        "aliases": [],
        "category": "env",
        "severity": "PASS" if state == "pass" else "INFO",
        "status": state,
        "level": 1,
        "message": _PASS if state == "pass" else _NO_USE,
        "evidence": [],
        "fix_hint": _HINT,
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    if state == "fail":
        finding.update(
            severity=severity,
            severity_origin="profile:core",
            message=(
                f"{package} is used but not pinned to an exact version "
                f"(suggestion: {package}==<version>)"
            ),
            evidence=[_evidence("requirements.txt", "declared as >=2", line=1, value=">=2")],
            fix_hint=f"Pin {package} exactly, e.g. `{package}==<version>`.",
        )
    if suppressed:
        finding["evidence"].append(
            _evidence(
                ".reprollm/config.yaml",
                f"suppressed: original severity {finding['severity']}; reason: {_REASON}",
                kind="field",
                field="audit.ignore",
            )
        )
        finding.update(severity="INFO", status="suppressed", suppressed_reason=_REASON)
    return finding


def _python_warning() -> dict[str, Any]:
    return {
        "rule_id": "env.python_version_declared",
        "aliases": [],
        "category": "env",
        "severity": "WARNING",
        "status": "fail",
        "level": 1,
        "message": "no Python version requirement is declared",
        "evidence": [_evidence(None, "no requires-python / .python-version / conda python= found")],
        "fix_hint": (
            "Add `requires-python` to pyproject.toml, a .python-version file, or a "
            "`python=3.x` entry in environment.yml."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


def _expected_report(
    repo: Path,
    state: str,
    severity: str = "WARNING",
    *,
    mixed: bool = False,
    suppressed: bool = False,
) -> dict[str, Any]:
    pin = _pin_finding(state, severity, suppressed=suppressed)
    findings = [pin]
    if mixed:
        findings = (
            [pin, _python_warning()]
            if state == "fail" and not suppressed
            else [_python_warning(), pin]
        )
    return {
        "schema_version": 1,
        "reprollm_version": __version__,
        "target": ".",
        "level": 1,
        "profiles": {"declared": [], "resolved": ["core"], "detected": []},
        "documents": {
            "manifest": "sha256:"
            + hashlib.sha256((repo / "reprollm.yaml").read_bytes()).hexdigest(),
            "lock": None,
            "runs": 0,
        },
        "summary": {
            "critical": int(state == "fail" and severity == "CRITICAL" and not suppressed),
            "warning": int(state == "fail" and severity == "WARNING" and not suppressed)
            + int(mixed),
            "info": 0,
            "pass": int(state == "pass" and not suppressed),
            "suppressed": int(suppressed),
            "skipped": int(state == "skipped" and not suppressed),
        },
        "findings": findings,
    }


def _report(stdout: str) -> dict[str, Any]:
    report, end = json.JSONDecoder().raw_decode(stdout)
    assert not stdout[end:].strip()
    schema = Path(__file__).resolve().parents[3] / "schemas/audit_report.schema.json"
    jsonschema.validate(report, json.loads(schema.read_text(encoding="utf-8")))
    AuditReport.model_validate(report)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", report.pop("generated_at"))
    return report


def _stable(stdout: str) -> str:
    return re.sub(r'("generated_at": ")[^"]+(\")', r"\1<TIMESTAMP>\2", stdout)


@pytest.mark.parametrize("exact", [False, True])
@pytest.mark.parametrize(
    ("severity", "threshold", "failure_exit"),
    [
        ("WARNING", "never", 0),
        ("WARNING", "critical", 0),
        ("WARNING", "warning", 1),
        ("CRITICAL", "never", 0),
        ("CRITICAL", "critical", 1),
        ("CRITICAL", "warning", 1),
    ],
)
def test_inline_comments_change_exit_in_both_directions_and_veto_restores_history(
    tmp_path: Path, exact: bool, severity: str, threshold: str, failure_exit: int
) -> None:
    repo = _repo(tmp_path, severity)
    body = "torch>=2\ntorch==2.5.1 # pin\n" if exact else "torch>=2 # use\n"
    old_state, new_state = ("fail", "pass") if exact else ("skipped", "fail")
    _requirements(repo, body + _VETO)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]
    before = runner.invoke(app, args)
    assert before.exit_code == (failure_exit if exact else 0), before.output
    assert before.stderr == ""
    historical = _report(before.stdout)
    assert historical == _expected_report(repo, old_state, severity)

    _requirements(repo, body)
    after = runner.invoke(app, args)
    assert after.exit_code == (0 if exact else failure_exit), after.output
    assert after.stderr == ""
    assert _report(after.stdout) == _expected_report(repo, new_state, severity)
    assert _report(before.stdout) == historical

    _requirements(repo, body + _VETO)
    restored = runner.invoke(app, args)
    assert restored.exit_code == before.exit_code
    assert restored.stderr == ""
    assert _report(restored.stdout) == historical


@pytest.mark.parametrize("exact", [False, True])
def test_inline_comment_credit_does_not_hide_an_independent_warning(
    tmp_path: Path, exact: bool
) -> None:
    repo = _repo(tmp_path, mixed=True)
    _requirements(repo, "torch==2.5.1 # pin\n" if exact else "torch>=2 # use\n")
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 1
    assert result.stderr == ""
    assert _report(result.stdout) == _expected_report(repo, "pass" if exact else "fail", mixed=True)


@pytest.mark.parametrize("coverage", ["gap", "unavailable", "inconsistent"])
def test_inline_comment_exact_credit_still_reaches_engine_python_pass_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str
) -> None:
    repo = _repo(tmp_path, "CRITICAL")
    _requirements(repo, "torch==2.5.1 # pin\n")
    monkeypatch.setattr(
        "reprollm.core.context.scan_python",
        lambda _scanner: PyScanResult(
            coverage_observed=coverage != "unavailable",
            python_candidate_count=2,
            python_selected_count=1,
            python_parsed_count=2 if coverage == "inconsistent" else 1,
            python_file_limit=1,
        ),
    )
    expected = _expected_report(repo, "skipped", "CRITICAL")
    expected["findings"][0]["message"] = (
        "Python candidate analysis incomplete: parsed 1 of 2 candidate files; selected 1 "
        "(limit 1); no rule-wide PASS is established."
        if coverage == "gap"
        else "Python candidate coverage is unavailable; no rule-wide PASS is established."
    )
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "critical"])
    assert result.exit_code == 0, result.output
    assert _report(result.stdout) == expected


def test_inline_comments_keep_package_sorting_credit_and_first_declaration_evidence(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _requirements(repo, "torch>=2 # first\nopenai==1.50.0 # pin\ntorch>=3\n")
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 1
    assert result.stderr == ""
    assert _report(result.stdout) == _expected_report(repo, "fail")


@pytest.mark.parametrize("state", ["fail", "pass", "skipped"])
def test_inline_comment_full_json_diagnostics_text_export_suppression_and_determinism(
    tmp_path: Path, state: str
) -> None:
    repo = _repo(tmp_path, "CRITICAL")
    body = "torch==2.5.1 # pin\n" if state == "pass" else "torch>=2 # use\n"
    _requirements(repo, body + (_VETO if state == "skipped" else ""))
    original = {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", "critical"]
    first, repeated = runner.invoke(app, args), runner.invoke(app, args)
    expected = _expected_report(repo, state, "CRITICAL")
    assert first.exit_code == repeated.exit_code == int(state == "fail")
    assert first.stderr == repeated.stderr == ""
    assert _report(first.stdout) == _report(repeated.stdout) == expected
    assert _stable(first.stdout) == _stable(repeated.stdout)
    verbose = runner.invoke(app, ["--verbose", *args])
    assert verbose.exit_code == first.exit_code
    assert _report(verbose.stdout) == expected
    assert verbose.stderr == (
        "scan: requirements.txt:1: torch>=2 # use\n" if state == "skipped" else ""
    )
    hidden = runner.invoke(app, ["audit", str(repo), "--no-color", "--fail-on", "critical"])
    shown = runner.invoke(
        app,
        [
            "audit",
            str(repo),
            "--no-color",
            "--show-passed",
            "--show-skipped",
            "--fail-on",
            "critical",
        ],
    )
    assert hidden.exit_code == shown.exit_code == first.exit_code
    assert hidden.stderr == shown.stderr == ""
    message = expected["findings"][0]["message"]
    assert (message in hidden.stdout) == (state == "fail")
    assert message in shown.stdout
    assert ("Findings: PASS" in hidden.stdout) == (state != "fail")
    paths = [tmp_path / "first.md", tmp_path / "second.md"]
    for path in paths:
        result = runner.invoke(app, ["export", str(repo), "--output", str(path)])
        assert result.exit_code == 0, result.output
        assert result.stderr == ""
    assert paths[0].read_bytes() == paths[1].read_bytes()
    document = paths[0].read_text(encoding="utf-8")
    assert (_PIN in document) == (state == "fail")
    exported_message = (
        "torch is used but not pinned to an exact version (suggestion: torch==&lt;version&gt;)"
        if state == "fail"
        else message
    )
    assert (exported_message in document) == (state == "fail")
    assert {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    } == original
    (repo / ".reprollm/config.yaml").write_text(
        f"schema_version: 1\naudit:\n  ignore:\n    - rule: {_PIN}\n      reason: {_REASON}\n",
        encoding="utf-8",
    )
    commit_all(repo)
    suppressed = runner.invoke(app, args)
    assert suppressed.exit_code == 0
    assert suppressed.stderr == ""
    assert _report(suppressed.stdout) == _expected_report(repo, state, "CRITICAL", suppressed=True)
    assert _report(first.stdout) == expected


@pytest.mark.parametrize("override", [False, True])
def test_inline_comment_default_and_explicit_init_feed_complete_l1_and_export(
    tmp_path: Path, override: bool
) -> None:
    repo = _repo(tmp_path)
    (repo / "reprollm.yaml").unlink()
    profiles = repo / ".reprollm/profiles"
    (profiles / "inference.yaml").write_text(
        "schema_version: 1\nname: inference\ndescription: Isolated init consumer.\n"
        "extends: [core]\nrules: [gen.backend_declared]\n"
        "required_fields: [inference.backend]\ndetect: {dependencies: [vllm]}\n",
        encoding="utf-8",
    )
    (profiles / "manual.yaml").write_text(
        "schema_version: 1\nname: manual\ndescription: Explicit selection.\nextends: [core]\n",
        encoding="utf-8",
    )
    _requirements(repo, "vllm>=2 # use\n")
    selected = "manual" if override else "inference"
    result = runner.invoke(
        app, ["init", str(repo), *(["--profiles", "manual"] if override else [])]
    )
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    assert (
        f"Applied {'selected' if override else 'detected'} profiles: {selected}." in result.stdout
    )
    expected_manifest: dict[str, Any] = {
        "schema_version": 1,
        "project": {"name": "comments"},
        "experiment": {"profiles": [selected]},
    }
    if not override:
        expected_manifest["inference"] = {"backend": None}
    assert yaml.safe_load((repo / "reprollm.yaml").read_text(encoding="utf-8")) == expected_manifest
    assert yaml.safe_load((repo / ".reprollm/project-rules.yaml").read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "rules": [],
        "ignored_candidates": [],
    }
    assert yaml.safe_load((repo / ".reprollm/config.yaml").read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "audit": {"fail_on": "critical", "ignore": [], "show_passed": False},
        "run": {
            "env_capture": "allowlist",
            "capture_output": False,
            "snapshot_max_bytes": 1048576,
            "extra_env_allowlist": [],
        },
        "discover": {
            "enabled": False,
            "base_url_env": "REPROLLM_LLM_BASE_URL",
            "api_key_env": "REPROLLM_LLM_API_KEY",
            "model_env": "REPROLLM_LLM_MODEL",
            "max_chars": 60000,
        },
    }
    expected = _expected_report(repo, "fail")
    expected["findings"] = [_pin_finding("fail", package="vllm")]
    expected["profiles"] = {
        "declared": [selected],
        "resolved": ["core", selected],
        "detected": [
            {
                "profile": "inference",
                "confidence": "medium",
                "shipped": True,
                "evidence": [
                    _evidence("requirements.txt", "dependency vllm", kind="detection", line=1)
                ],
            }
        ],
    }
    if not override:
        expected["summary"]["warning"] = 2
        expected["findings"].append(
            {
                "rule_id": "gen.backend_declared",
                "aliases": [],
                "category": "gen",
                "severity": "WARNING",
                "status": "fail",
                "level": 1,
                "message": "inference.backend is missing",
                "evidence": [_evidence(None, "absent", kind="field", field="inference.backend")],
                "fix_hint": "Set inference.backend in reprollm.yaml.",
                "profile_origin": [],
                "severity_origin": "default",
                "suppressed_reason": None,
            }
        )
    commit_all(repo)
    args = ["audit", str(repo), "--format", "json", "--fail-on", "warning"]
    first, repeated = runner.invoke(app, args), runner.invoke(app, args)
    assert first.exit_code == repeated.exit_code == 1
    assert first.stderr == repeated.stderr == ""
    assert _report(first.stdout) == _report(repeated.stdout) == expected
    assert _stable(first.stdout) == _stable(repeated.stdout)
    paths = [tmp_path / "init-a.md", tmp_path / "init-b.md"]
    for path in paths:
        exported = runner.invoke(app, ["export", str(repo), "--output", str(path)])
        assert exported.exit_code == 0, exported.output
        assert exported.stderr == ""
    assert paths[0].read_bytes() == paths[1].read_bytes()
    document = paths[0].read_text(encoding="utf-8")
    assert "vllm is used but not pinned" in document
    assert ("inference.backend is missing" in document) == (not override)
