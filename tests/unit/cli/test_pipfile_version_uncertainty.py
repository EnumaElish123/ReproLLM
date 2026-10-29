"""D-M-PF A33-A43: complete consumer oracles written before implementation."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import registry
from reprollm.core.context import AuditContext
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule
from reprollm.schemas.run_record import RunRecord
from tests.conftest import commit_all, make_git_repo
from tests.unit.cli.test_pep621_requirement_failures import (
    _CONFIG,
    _PROJECT_RULES,
    _expected_report,
    _export_expected,
    _manifest,
    _python_warning,
    _report,
    _stable,
)

runner = CliRunner()
_PIN = "env.llm_critical_deps_pinned"
_GOOD = '[packages]\ntorch=">=2"\nrequests={version=">=2"}\n'
_BAD = '[packages]\ntorch=">=2"\nrequests={version=false}\n'
_REASON = "Reviewed captured pipfile-version extraction failure."


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _repo(tmp_path: Path, severity: str = "WARNING", mixed: bool = False) -> Path:
    repo = make_git_repo(tmp_path / "pipfile-version")
    profiles = repo / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated pipfile-version consumers.",
                "rules": [_PIN] + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {_PIN: severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: pipfile-version}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    return repo


def _body(repo: Path, text: str) -> None:
    (repo / "Pipfile").write_text(text, encoding="utf-8")
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


def _pin(
    state: str, severity: str = "WARNING", *, suppressed: bool = False, alias: bool = False
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "rule_id": _PIN,
        "aliases": ["env.previous_pin"] if alias else [],
        "category": "env",
        "severity": "PASS" if state == "pass" else "INFO",
        "status": "skipped" if state == "no-use" else state,
        "level": 1,
        "message": (
            "Every LLM-critical dependency in use is pinned to an exact version."
            if state == "pass"
            else "no LLM-critical package is declared or imported"
        ),
        "evidence": [],
        "fix_hint": "Pin the package exactly (see the message for the suggested version).",
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    if state in {"fail", "skipped"}:
        finding["evidence"] = [_evidence("Pipfile", "declared as >=2", line=2, value=">=2")]
    if state == "fail":
        finding.update(
            severity=severity,
            severity_origin="profile:core",
            message=(
                "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
            ),
            fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
        )
    elif state == "skipped":
        finding.update(
            message=(
                "torch is used; a dependency declaration body could not be read or parsed, "
                "so missing pin evidence is not established"
            ),
            fix_hint=(
                "Review torch declarations and failed dependency source files; restore readable, "
                "valid declaration bodies before deciding that exact pin evidence is absent."
            ),
        )
        finding["evidence"].append(
            _evidence("Pipfile", "torch possible exact declaration unverified")
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


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize(
    ("severity", "threshold", "old_exit"),
    [
        ("WARNING", "warning", 1),
        ("CRITICAL", "critical", 1),
        ("WARNING", "critical", 0),
        ("CRITICAL", "warning", 1),
        ("WARNING", "never", 0),
        ("CRITICAL", "never", 0),
    ],
)
def test_entire_json_threshold_and_repeat_then_repair(
    tmp_path: Path, severity: str, threshold: str, old_exit: int, section: str
) -> None:
    """A40/A41/A43: only the two root T-02 report fields are exempt from full comparison."""
    repo = _repo(tmp_path, severity)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]
    _body(repo, _GOOD.replace("[packages]", f"[{section}]"))
    before = runner.invoke(app, args)
    assert before.exit_code == old_exit and before.stderr == "", before.output
    assert _report(before.stdout) == _expected_report(repo, [_pin("fail", severity)])
    _body(repo, _BAD.replace("[packages]", f"[{section}]"))
    after = runner.invoke(app, args)
    assert after.exit_code == 0 and after.stderr == "", after.output
    assert _report(after.stdout) == _expected_report(repo, [_pin("skipped")])
    repeat = runner.invoke(app, args)
    assert repeat.exit_code == 0 and repeat.stderr == ""
    assert _stable(repeat.stdout) == _stable(after.stdout)
    _body(repo, _GOOD.replace("[packages]", f"[{section}]"))
    restored = runner.invoke(app, args)
    assert restored.exit_code == old_exit and restored.stderr == ""
    assert _stable(restored.stdout) == _stable(before.stdout)


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
def test_independent_warning_keeps_entire_finding_and_exit_one(
    tmp_path: Path, severity: str
) -> None:
    """A41: unchanged exits must not conceal the real pin-finding delta."""
    repo = _repo(tmp_path, severity, mixed=True)
    args = ["audit", str(repo), "--format", "json", "--fail-on", "warning"]
    _body(repo, _GOOD)
    before = runner.invoke(app, args)
    assert before.exit_code == 1 and before.stderr == ""
    assert _report(before.stdout) == _expected_report(
        repo, [_pin("fail", severity), _python_warning()]
    )
    _body(repo, _BAD)
    after = runner.invoke(app, args)
    assert after.exit_code == 1 and after.stderr == ""
    assert _report(after.stdout) == _expected_report(repo, [_python_warning(), _pin("skipped")])


@pytest.mark.parametrize("alias", [False, True])
def test_ignore_and_alias_preserve_full_info_suppression_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: bool
) -> None:
    """A41: FAIL-only CRITICAL promotion never rewrites a new SKIP to CRITICAL."""
    if alias:
        monkeypatch.setattr(LlmCriticalDepsPinnedRule, "aliases", ("env.previous_pin",))
        monkeypatch.setitem(registry._ALIASES, "env.previous_pin", _PIN)
    repo = _repo(tmp_path, "CRITICAL")
    (repo / ".reprollm/config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        f"    - rule: {'env.previous_pin' if alias else _PIN}\n      reason: {_REASON}\n",
        encoding="utf-8",
    )
    _body(repo, _BAD)
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 0 and result.stderr == ""
    assert _report(result.stdout) == _expected_report(
        repo, [_pin("skipped", suppressed=True, alias=alias)]
    )


@pytest.mark.parametrize("show_skipped", [False, True])
@pytest.mark.parametrize("show_passed", [False, True])
@pytest.mark.parametrize("verbose", [False, True])
def test_complete_text_visibility_without_new_diagnostics(
    tmp_path: Path, show_skipped: bool, show_passed: bool, verbose: bool
) -> None:
    """A40: Explicit field type failures add no diagnostic or value prose."""
    repo = _repo(tmp_path)
    _body(repo, _BAD)
    flags = ["--show-skipped"] if show_skipped else []
    flags += ["--show-passed"] if show_passed else []
    args = [*(["--verbose"] if verbose else []), "audit", str(repo), "--fail-on", "warning", *flags]
    expected = (
        "ReproLLM audit · level 1 · profiles: core\n\n"
        "Next steps (in the audited repository)\n"
        "  Coverage: 1 skipped check; this experiment was not fully checked. "
        "Inspect them with `reprollm audit . --show-skipped`.\n\n"
    )
    if show_skipped:
        expected += (
            "INFO (1)\n  - env.llm_critical_deps_pinned      skipped: "
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established\n\n"
        )
    expected += "0 passed · 0 suppressed · 1 skipped"
    if not show_skipped and not show_passed:
        expected += "        (use --show-passed / --show-skipped)"
    expected += (
        "\nFindings: PASS\nResult: exit 0 (--fail-on warning; no finding reaches the threshold)\n"
    )
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert result.stdout == expected
    assert result.stderr == ""
    complete = runner.invoke(app, [*args, "--format", "json"])
    assert complete.exit_code == 0
    assert complete.stderr == ""
    assert _report(complete.stdout) == _expected_report(repo, [_pin("skipped")])


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
@pytest.mark.parametrize("credit", [False, True])
def test_no_use_and_exact_credit_keep_engine_python_empty_result_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str, credit: bool
) -> None:
    """A35: an extraction failure does not create use, aggregate PASS, or Python coverage."""
    repo = _repo(tmp_path)
    if coverage != "complete":
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
    valid = 'torch="==2"' if credit else 'requests=">=2"'
    _body(repo, f"[packages]\n{valid}\npython={{version=false}}\n")
    expected = _pin("pass" if credit else "no-use")
    if credit and coverage != "complete":
        expected.update(
            severity="INFO",
            status="skipped",
            message=(
                "Python candidate analysis incomplete: parsed 1 of 2 candidate files; selected 1 "
                "(limit 1); no rule-wide PASS is established."
                if coverage == "gap"
                else "Python candidate coverage is unavailable; no rule-wide PASS is established."
            ),
        )
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [expected])


def _expected_export(state: str, *, mixed: bool = False, selected: str | None = None) -> str:
    # The full export/init byte oracles predate D-M-PF; never derive them from output.
    return _export_expected(state, mixed=mixed, selected=selected).replace(
        "pep621", "pipfile-version"
    )


@pytest.mark.parametrize("mixed", [False, True])
def test_entire_default_export_repeats_across_roots_and_preserves_historical_bytes(
    tmp_path: Path, mixed: bool
) -> None:
    """A40/A43: all export bytes and archived report/run/snapshot hashes are compared."""
    outputs: list[bytes] = []
    audits: list[str] = []
    for location in ("first", "different-root"):
        repo = _repo(tmp_path / location, mixed=mixed)
        _body(repo, _GOOD)
        output = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert output.read_bytes() == _expected_export("fail", mixed=mixed).encode("utf-8")
        audit = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
        assert audit.exit_code == 0 and audit.stderr == ""
        assert _report(audit.stdout) == _expected_report(
            repo, [_pin("fail"), *([_python_warning()] if mixed else [])]
        )
        historical_run = {
            "schema_version": 1,
            "reprollm_version": "0.7.0",
            "run_id": "historical",
            "status": "completed",
            "command": {"argv": ["python", "old.py"], "cwd": "."},
            "started_at": "2026-10-01T00:00:00Z",
            "ended_at": "2026-10-01T00:00:01Z",
            "duration_seconds": 1.0,
            "exit_code": 0,
        }
        RunRecord.model_validate(historical_run)
        history = repo / "history"
        historical = {
            "audit.json": audit.stdout.encode(),
            "REPRODUCIBILITY.md": output.read_bytes(),
            "run.json": (json.dumps(historical_run, sort_keys=True) + "\n").encode(),
            "snapshots/reprollm.yaml": (repo / "reprollm.yaml").read_bytes(),
        }
        for name, content in historical.items():
            path = history / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        old_hashes = {
            name: hashlib.sha256(content).hexdigest() for name, content in historical.items()
        }
        _body(repo, _BAD)
        for _ in range(2):
            result = runner.invoke(app, ["export", str(repo), "--output", str(output)])
            assert result.exit_code == 0 and result.stderr == "", result.output
            assert output.read_bytes() == _expected_export("skipped", mixed=mixed).encode("utf-8")
            outputs.append(output.read_bytes())
            current = runner.invoke(
                app, ["audit", str(repo), "--format", "json", "--fail-on", "never"]
            )
            assert current.exit_code == 0 and current.stderr == ""
            assert _report(current.stdout) == _expected_report(
                repo, [*([_python_warning()] if mixed else []), _pin("skipped")]
            )
            audits.append(_stable(current.stdout))
        assert {name: (history / name).read_bytes() for name in historical} == historical
        assert {
            name: hashlib.sha256((history / name).read_bytes()).hexdigest() for name in historical
        } == old_hashes
    assert all(output == outputs[0] for output in outputs)
    assert all(audit == audits[0] for audit in audits)


def _detection() -> dict[str, Any]:
    return {
        "profiles": [
            {
                "profile": "inference",
                "confidence": "medium",
                "shipped": True,
                "evidence": [_evidence("Pipfile", "dependency vllm", kind="detection", line=3)],
            }
        ],
        "hints": {
            "providers": [],
            "backends": [],
            "datasets": False,
            "adapter": False,
            "trust_remote_code": False,
            "hf_ids": [],
        },
    }


@pytest.mark.parametrize("explicit", [False, True])
def test_full_init_files_detection_hints_l1_and_default_export(
    tmp_path: Path, explicit: bool
) -> None:
    """A42: successful sibling signals retain all generated manifest/config bytes."""
    selected = "manual" if explicit else "inference"
    generated: list[dict[str, bytes]] = []
    for invalid in (False, True):
        repo = _repo(tmp_path / ("bad" if invalid else "good"))
        (repo / "reprollm.yaml").unlink()
        for profile in ("inference", "manual"):
            (repo / f".reprollm/profiles/{profile}.yaml").write_text(
                f"schema_version: 1\nname: {profile}\ndescription: Isolated init profile.\n"
                "extends: [core]\nrules: []\n"
                + ("detect: {dependencies: [vllm]}\n" if profile == "inference" else ""),
                encoding="utf-8",
            )
        value = "false" if invalid else '">=2"'
        text = f'[packages]\ntorch=">=2"\nvllm="==1"\nrequests={{version={value}}}\n'
        _body(repo, text)
        assert AuditContext(repo).detection.model_dump(mode="json") == _detection()
        result = runner.invoke(
            app, ["init", str(repo), *(["--profiles", "manual"] if explicit else [])]
        )
        assert result.exit_code == 0 and result.stderr == "", result.output
        expected_files = {
            "reprollm.yaml": _manifest(selected).replace("pep621", "pipfile-version"),
            ".reprollm/config.yaml": _CONFIG,
            ".reprollm/project-rules.yaml": _PROJECT_RULES,
        }
        actual = {name: (repo / name).read_bytes() for name in expected_files}
        assert actual == {name: text.encode() for name, text in expected_files.items()}
        generated.append(actual)
        assert (repo / "Pipfile").read_text(encoding="utf-8") == text
        audit = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
        assert audit.exit_code == (0 if invalid else 1) and audit.stderr == "", audit.output
        assert _report(audit.stdout) == _expected_report(
            repo,
            [_pin("skipped" if invalid else "fail")],
            selected=selected,
            detected=_detection()["profiles"],
        )
        output = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert output.read_bytes() == _expected_export(
            "skipped" if invalid else "fail", selected=selected
        ).encode("utf-8")
    assert generated[0] == generated[1]


@pytest.mark.parametrize("section", ["packages", "dev-packages"])
@pytest.mark.parametrize(
    "value", ['"2.5.1"', '""', '"bad !!!"', "false", "[{version=false}]", '{git="public"}']
)
def test_excluded_entry_values_keep_full_existing_failure_and_exit(
    tmp_path: Path, section: str, value: str
) -> None:
    """A07-A16/A41: absent exact is never sufficient evidence for the new fact."""
    repo = _repo(tmp_path)
    _body(repo, f'[{section}]\ntorch=">=2"\nrequests={value}\n')
    ctx = AuditContext(repo)
    assert ctx.deps.declaration_read_issues == {}
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 1 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [_pin("fail")])
