"""Independent complete CLI contracts for the accepted requirements depth frontier."""

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
from reprollm.schemas.finding import AuditReport
from tests.conftest import commit_all, make_git_repo

runner = CliRunner()
_MESSAGE = (
    "torch is used; a supported requirements include was not expanded within the depth budget, "
    "so missing pin evidence is not established"
)
_MANIFEST = "schema_version: 1\nproject: {name: frontier}\nexperiment: {profiles: []}\n"


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _repo(tmp_path: Path, severity: str = "CRITICAL", mixed: bool = False) -> Path:
    repo = make_git_repo(tmp_path / "frontier")
    profiles = repo / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated requirements depth frontier.",
                "rules": ["env.llm_critical_deps_pinned"]
                + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {"env.llm_critical_deps_pinned": severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(_MANIFEST, encoding="utf-8")
    (repo / "requirements.txt").write_text("torch>=2\n", encoding="utf-8")
    chain = repo / "unrelated/chain"
    chain.mkdir(parents=True)
    (repo / "unrelated/requirements.txt").write_text("-r chain/0.txt\n", encoding="utf-8")
    for index in range(9):
        (chain / f"{index}.txt").write_text(f"-r {index + 1}.txt\n", encoding="utf-8")
    (chain / "9.txt").write_text("", encoding="utf-8")
    commit_all(repo)
    return repo


def _set_frontier(repo: Path, enabled: bool) -> None:
    (repo / "unrelated/chain/9.txt").write_text(
        "-r ../pins.txt\n" if enabled else "", encoding="utf-8"
    )
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


def _pin_finding(state: str, severity: str = "CRITICAL") -> dict[str, Any]:
    finding: dict[str, Any] = {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 1,
        "message": _MESSAGE,
        "evidence": [
            _evidence("requirements.txt", "declared as >=2", line=1, value=">=2"),
            _evidence("unrelated/pins.txt", "torch include target unexpanded at the depth limit"),
        ],
        "fix_hint": (
            "Review torch declarations and unexpanded requirements include targets; restructure "
            "the supported include graph within the depth budget before deciding that exact pin "
            "evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    if state == "fail":
        finding.update(
            severity=severity,
            status="fail",
            severity_origin="profile:core",
            message=(
                "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
            ),
            fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
            evidence=finding["evidence"][:1],
        )
    elif state == "pass":
        finding.update(
            severity="PASS",
            status="pass",
            message="Every LLM-critical dependency in use is pinned to an exact version.",
            fix_hint="Pin the package exactly (see the message for the suggested version).",
            evidence=[],
        )
    elif state == "suppressed":
        reason = "Reviewed requirements depth uncertainty."
        finding.update(status="suppressed", suppressed_reason=reason)
        finding["evidence"].append(
            _evidence(
                ".reprollm/config.yaml",
                f"suppressed: original severity INFO; reason: {reason}",
                kind="field",
                field="audit.ignore",
            )
        )
    else:
        assert state == "skipped"
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
    repo: Path, state: str, severity: str = "CRITICAL", mixed: bool = False
) -> dict[str, Any]:
    pin = _pin_finding(state, severity)
    findings = [pin]
    if mixed:
        findings = [pin, _python_warning()] if state == "fail" else [_python_warning(), pin]
    return {
        "schema_version": 1,
        "reprollm_version": __version__,
        "target": ".",
        "level": 1,
        "profiles": {"declared": [], "resolved": ["core"], "detected": []},
        "documents": {
            "manifest": (
                "sha256:" + hashlib.sha256((repo / "reprollm.yaml").read_bytes()).hexdigest()
            ),
            "lock": None,
            "runs": 0,
        },
        "summary": {
            "critical": int(state == "fail" and severity == "CRITICAL"),
            "warning": int(state == "fail" and severity == "WARNING") + int(mixed),
            "info": 0,
            "pass": int(state == "pass"),
            "suppressed": int(state == "suppressed"),
            "skipped": int(state == "skipped"),
        },
        "findings": findings,
    }


def _report(stdout: str) -> dict[str, Any]:
    report, end = json.JSONDecoder().raw_decode(stdout)
    assert stdout[end:].strip() == ""
    schema_path = Path(__file__).resolve().parents[3] / "schemas/audit_report.schema.json"
    jsonschema.validate(report, json.loads(schema_path.read_text(encoding="utf-8")))
    AuditReport.model_validate(report)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", report.pop("generated_at"))
    return report


def _without_timestamp(stdout: str) -> str:
    return re.sub(r'("generated_at": ")[^"]+(\")', r"\1<TIMESTAMP>\2", stdout)


@pytest.mark.parametrize(
    ("severity", "threshold", "mixed", "baseline_exit"),
    [
        ("WARNING", "never", False, 0),
        ("WARNING", "critical", False, 0),
        ("WARNING", "warning", False, 1),
        ("CRITICAL", "never", False, 0),
        ("CRITICAL", "critical", False, 1),
        ("CRITICAL", "warning", False, 1),
        ("WARNING", "warning", True, 1),
    ],
)
def test_depth_frontier_changes_only_missing_pin_outcome_and_restores_after_edge_removal(
    tmp_path: Path, severity: str, threshold: str, mixed: bool, baseline_exit: int
) -> None:
    repo = _repo(tmp_path, severity, mixed)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]

    baseline = runner.invoke(app, args)

    assert baseline.exit_code == baseline_exit, baseline.output
    assert baseline.stderr == ""
    historical = _report(baseline.stdout)
    assert historical == _expected_report(repo, "fail", severity, mixed)
    _set_frontier(repo, True)

    uncertain = runner.invoke(app, args)

    assert uncertain.exit_code == int(mixed), uncertain.output
    assert uncertain.stderr == ""
    assert _report(uncertain.stdout) == _expected_report(repo, "skipped", severity, mixed)
    assert _report(baseline.stdout) == historical
    _set_frontier(repo, False)

    restored = runner.invoke(app, args)

    assert restored.exit_code == baseline_exit, restored.output
    assert restored.stderr == ""
    assert _report(restored.stdout) == historical


def test_depth_frontier_full_json_text_export_suppression_and_byte_determinism(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    _set_frontier(repo, True)
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", "critical"]
    first, second = runner.invoke(app, args), runner.invoke(app, args)

    assert first.exit_code == second.exit_code == 0
    assert first.stderr == second.stderr == ""
    assert _report(first.stdout) == _report(second.stdout) == _expected_report(repo, "skipped")
    assert _without_timestamp(first.stdout) == _without_timestamp(second.stdout)
    hidden = runner.invoke(app, ["audit", str(repo), "--no-color", "--fail-on", "critical"])
    shown = runner.invoke(
        app, ["audit", str(repo), "--no-color", "--show-skipped", "--fail-on", "critical"]
    )
    assert hidden.exit_code == shown.exit_code == 0
    assert hidden.stderr == shown.stderr == ""
    assert _MESSAGE not in hidden.stdout
    assert _MESSAGE in shown.stdout
    assert "Findings: PASS" in hidden.stdout
    assert "0 passed · 0 suppressed · 1 skipped" in hidden.stdout
    verbose = runner.invoke(app, ["--verbose", *args])
    expected_diagnostics = [
        *(f"unrelated/chain/{index}.txt:1: include incomplete" for index in range(9)),
        "unrelated/chain/9.txt:1: include depth limit",
        "unrelated/requirements.txt:1: include incomplete",
    ]
    assert verbose.exit_code == 0
    assert _report(verbose.stdout) == _expected_report(repo, "skipped")
    assert verbose.stderr == "".join(f"scan: {line}\n" for line in sorted(expected_diagnostics))
    outputs = [tmp_path / "first.md", tmp_path / "second.md"]
    for output in outputs:
        exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert exported.exit_code == 0, exported.output
        assert exported.stderr == ""
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    document = outputs[0].read_text(encoding="utf-8")
    assert "0 critical · 0 warning ·\n0 info · 0 passed." in document
    assert "env.llm_critical_deps_pinned" not in document
    assert _MESSAGE not in document
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    } == before
    (repo / ".reprollm/config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed requirements depth uncertainty.\n",
        encoding="utf-8",
    )
    commit_all(repo)
    ignored = runner.invoke(app, args)

    assert ignored.exit_code == 0, ignored.output
    assert ignored.stderr == ""
    assert _report(ignored.stdout) == _expected_report(repo, "suppressed")


@pytest.mark.parametrize("exact", [False, True])
def test_shallow_include_restores_current_evidence_without_stale_depth_state(
    tmp_path: Path, exact: bool
) -> None:
    repo = _repo(tmp_path)
    _set_frontier(repo, True)
    args = ["audit", str(repo), "--format", "json", "--fail-on", "critical"]
    uncertain = runner.invoke(app, args)
    assert uncertain.exit_code == 0
    assert _report(uncertain.stdout) == _expected_report(repo, "skipped")
    (repo / "requirements_z.txt").write_text("-r unrelated/pins.txt\n", encoding="utf-8")
    (repo / "unrelated/pins.txt").write_text(
        "torch==2.5.1\n" if exact else "torch>=1\n", encoding="utf-8"
    )
    commit_all(repo)
    restored = runner.invoke(app, args)

    assert restored.exit_code == (0 if exact else 1), restored.output
    assert restored.stderr == ""
    assert _report(restored.stdout) == _expected_report(repo, "pass" if exact else "fail")
