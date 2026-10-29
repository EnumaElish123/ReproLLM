"""D-M-CS CS-A29-A35/A37: complete public CLI consumer acceptance."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
from reprollm.schemas.lock import Lock
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
_GOOD = "dependencies:\n- requests>=2\n"
_BAD = "dependencies:\n- requests==2.5.*\n"
_REASON = "Reviewed captured native Conda specifier."


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _repo(tmp_path: Path, severity: str | None = "WARNING", mixed: bool = False) -> Path:
    repo = make_git_repo(tmp_path / "conda-specifier")
    profiles = repo / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated native Conda specifier consumers.",
                "rules": [_PIN] + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {} if severity is None else {_PIN: severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: conda-specifier}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "train.py").write_text("import torch\n", encoding="utf-8")
    return repo


def _body(repo: Path, text: str, newline: str | None = None) -> None:
    with (repo / "environment.yml").open("w", encoding="utf-8", newline=newline) as stream:
        stream.write(text)
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


def _skipped_pin() -> dict[str, Any]:
    return {
        "rule_id": _PIN,
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 1,
        "message": (
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established"
        ),
        "evidence": [
            _evidence("train.py", "imported", line=1),
            _evidence("environment.yml", "torch possible exact declaration unverified"),
        ],
        "fix_hint": (
            "Review torch declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


def _failed_pin(severity: str | None = "WARNING") -> dict[str, Any]:
    finding = _skipped_pin()
    finding.update(
        severity="WARNING" if severity is None else severity,
        status="fail",
        severity_origin="default" if severity is None else "profile:core",
        message="torch is used but not pinned to an exact version (suggestion: torch==<version>)",
        fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
        evidence=[_evidence("train.py", "imported", line=1)],
    )
    return finding


def test_wildcard_specifier_keeps_complete_skip_report_and_warning_exit_zero(
    tmp_path: Path,
) -> None:
    """CS-A30/A31: nonexact noncritical wildcard conservatively affects imported torch."""
    repo = _repo(tmp_path)
    _body(repo, _BAD)
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [_skipped_pin()])


@pytest.mark.parametrize(
    ("severity", "threshold", "before_exit"),
    [
        pytest.param(None, "warning", 1, id="default-warning"),
        pytest.param("WARNING", "warning", 1, id="warning-warning"),
        pytest.param("CRITICAL", "critical", 1, id="critical-critical"),
        pytest.param("WARNING", "critical", 0, id="warning-critical"),
        pytest.param("CRITICAL", "warning", 1, id="critical-warning"),
        pytest.param("WARNING", "never", 0, id="warning-never"),
        pytest.param("CRITICAL", "never", 0, id="critical-never"),
    ],
)
def test_complete_json_thresholds_repeat_and_restore(
    tmp_path: Path, severity: str | None, threshold: str, before_exit: int
) -> None:
    """CS-A29-A31: profile promotion is FAIL-only; never and default origins stay intact."""
    repo = _repo(tmp_path, severity)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]
    _body(repo, _GOOD)
    before = runner.invoke(app, args)
    assert before.exit_code == before_exit and before.stderr == "", before.output
    assert _report(before.stdout) == _expected_report(repo, [_failed_pin(severity)])
    _body(repo, _BAD)
    after = runner.invoke(app, args)
    assert after.exit_code == 0 and after.stderr == "", after.output
    assert _report(after.stdout) == _expected_report(repo, [_skipped_pin()])
    repeated = runner.invoke(app, args)
    assert repeated.exit_code == 0 and repeated.stderr == "", repeated.output
    assert _stable(repeated.stdout) == _stable(after.stdout)
    _body(repo, _GOOD)
    restored = runner.invoke(app, args)
    assert restored.exit_code == before_exit and restored.stderr == "", restored.output
    assert _stable(restored.stdout) == _stable(before.stdout)


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
def test_independent_warning_keeps_full_finding_and_exit_one(tmp_path: Path, severity: str) -> None:
    """CS-A30: an unrelated qualifying failure must not conceal or erase the target delta."""
    repo = _repo(tmp_path, severity, mixed=True)
    args = ["audit", str(repo), "--format", "json", "--fail-on", "warning"]
    _body(repo, _GOOD)
    before = runner.invoke(app, args)
    assert before.exit_code == 1 and before.stderr == "", before.output
    assert _report(before.stdout) == _expected_report(
        repo, [_failed_pin(severity), _python_warning()]
    )
    _body(repo, _BAD)
    after = runner.invoke(app, args)
    assert after.exit_code == 1 and after.stderr == "", after.output
    assert _report(after.stdout) == _expected_report(repo, [_python_warning(), _skipped_pin()])


@pytest.mark.parametrize("severity", [None, "CRITICAL"], ids=["no-override", "critical-override"])
def test_ignore_preserves_original_info_cause_and_complete_suppression_evidence(
    tmp_path: Path, severity: str | None
) -> None:
    """CS-A29: ignoring an already-SKIPPED target keeps its INFO rather than a promotion."""
    repo = _repo(tmp_path, severity)
    (repo / ".reprollm/config.yaml").write_text(
        f"schema_version: 1\naudit:\n  ignore:\n    - rule: {_PIN}\n      reason: {_REASON}\n",
        encoding="utf-8",
    )
    _body(repo, _BAD)
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 0 and result.stderr == "", result.output
    expected = _skipped_pin()
    expected["evidence"].append(
        _evidence(
            ".reprollm/config.yaml",
            f"suppressed: original severity INFO; reason: {_REASON}",
            kind="field",
            field="audit.ignore",
        )
    )
    expected.update(severity="INFO", status="suppressed", suppressed_reason=_REASON)
    assert _report(result.stdout) == _expected_report(repo, [expected])


@pytest.mark.parametrize("show_skipped", [False, True])
@pytest.mark.parametrize("details", [False, True])
@pytest.mark.parametrize("verbose", [False, True])
def test_complete_default_and_detailed_text_preserves_same_unsupported_diagnostic(
    tmp_path: Path, show_skipped: bool, details: bool, verbose: bool
) -> None:
    """CS-A32: the same old ordinal diagnostic accompanies either complete finding."""
    repo = _repo(tmp_path)
    flags = ["--show-skipped"] if show_skipped else []
    flags += ["--details"] if details else []
    args = [*(["--verbose"] if verbose else []), "audit", str(repo), "--fail-on", "warning"]
    diagnostic = "scan: environment.yml:1: unsupported conda declaration\n" if verbose else ""
    hint = "" if show_skipped else "        (use --show-passed / --show-skipped)"
    before_text = (
        "ReproLLM audit · level 1 · profiles: core\n\n"
        "Next steps (in the audited repository)\n"
        "  1. [WARNING] env.llm_critical_deps_pinned at train.py: "
        "Pin torch exactly, e.g. `torch==<version>`.\n\n"
        "WARNING (1)\n"
        "  ! env.llm_critical_deps_pinned      torch is used but not pinned to an exact "
        "version (suggestion: torch==<version>)\n"
        "      train.py (imported)\n"
        "      fix: Pin torch exactly, e.g. `torch==<version>`.\n\n"
        f"0 passed · 0 suppressed · 0 skipped{hint}\n"
        "Findings: FAIL (0 critical, 1 warning)\n"
        "Result: exit 1 (--fail-on warning; findings reach the threshold)\n"
    )
    after_text = (
        "ReproLLM audit · level 1 · profiles: core\n\n"
        "Next steps (in the audited repository)\n"
        "  Coverage: 1 skipped check; this experiment was not fully checked. "
        "Inspect them with `reprollm audit . --show-skipped`.\n\n"
    )
    if show_skipped:
        after_text += (
            "INFO (1)\n  - env.llm_critical_deps_pinned      skipped: "
            "torch is used; a dependency declaration body could not be read or parsed, "
            "so missing pin evidence is not established\n\n"
        )
    after_text += (
        f"0 passed · 0 suppressed · 1 skipped{hint}\nFindings: PASS\n"
        "Result: exit 0 (--fail-on warning; no finding reaches the threshold)\n"
    )
    _body(repo, _GOOD)
    before = runner.invoke(app, [*args, *flags])
    assert before.exit_code == 1 and before.stderr == diagnostic, before.output
    assert before.stdout == before_text
    _body(repo, _BAD)
    after = runner.invoke(app, [*args, *flags])
    assert after.exit_code == 0 and after.stderr == diagnostic, after.output
    assert after.stdout == after_text
    complete = runner.invoke(app, [*args, *flags, "--format", "json"])
    assert complete.exit_code == 0 and complete.stderr == diagnostic, complete.output
    assert _report(complete.stdout) == _expected_report(repo, [_skipped_pin()])


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
@pytest.mark.parametrize("mixed", [False, True], ids=["isolated", "independent-warning"])
def test_complete_github_annotations_drop_only_target_failure(
    tmp_path: Path, severity: str, mixed: bool
) -> None:
    """CS-A33: actual GitHub output loses the pin annotation but retains other findings."""
    repo = _repo(tmp_path, severity, mixed=mixed)
    args = ["audit", str(repo), "--format", "github", "--fail-on", "warning"]
    python_annotation = (
        "::warning title=WARNING%3A env.python_version_declared::"
        "no Python version requirement is declared — fix: Add `requires-python` to "
        "pyproject.toml, a .python-version file, or a `python=3.x` entry in environment.yml.\n"
    )
    before_annotation = (
        "::error title=CRITICAL%3A env.llm_critical_deps_pinned,file=train.py,line=1::"
        if severity == "CRITICAL"
        else "::warning title=WARNING%3A env.llm_critical_deps_pinned,file=train.py,line=1::"
    )
    before_annotation += (
        "torch is used but not pinned to an exact version (suggestion: torch==<version>) "
        "— fix: Pin torch exactly, e.g. `torch==<version>`.\n"
    )
    before_text = before_annotation + (python_annotation if mixed else "")
    before_text += (
        "::notice title=ReproLLM audit::Level 1 · profiles: core · "
        f"{int(severity == 'CRITICAL')} critical, "
        f"{int(severity == 'WARNING') + int(mixed)} warning, 0 info, 0 passed\n\n"
    )
    after_text = (python_annotation if mixed else "") + (
        "::notice title=ReproLLM audit::Level 1 · profiles: core · "
        f"0 critical, {int(mixed)} warning, 0 info, 0 passed\n\n"
    )
    _body(repo, _GOOD)
    before = runner.invoke(app, args)
    assert before.exit_code == 1 and before.stderr == "", before.output
    assert before.stdout == before_text
    _body(repo, _BAD)
    after = runner.invoke(app, args)
    assert after.exit_code == int(mixed) and after.stderr == "", after.output
    assert after.stdout == after_text
    complete = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert complete.exit_code == int(mixed) and complete.stderr == "", complete.output
    assert _report(complete.stdout) == _expected_report(
        repo, [*([_python_warning()] if mixed else []), _skipped_pin()]
    )


def test_complete_github_suppressed_skip_retains_existing_notice(tmp_path: Path) -> None:
    """CS-A29/A33: suppression remains annotated, unlike an unsuppressed SKIP."""
    repo = _repo(tmp_path, "CRITICAL")
    (repo / ".reprollm/config.yaml").write_text(
        f"schema_version: 1\naudit:\n  ignore:\n    - rule: {_PIN}\n      reason: {_REASON}\n",
        encoding="utf-8",
    )
    _body(repo, _BAD)
    result = runner.invoke(app, ["audit", str(repo), "--format", "github", "--fail-on", "warning"])
    expected = (
        "::notice title=INFO%3A env.llm_critical_deps_pinned,file=train.py,line=1::"
        "torch is used; a dependency declaration body could not be read or parsed, "
        "so missing pin evidence is not established — fix: Review torch declarations and "
        "failed dependency source files; restore readable, valid declaration bodies before "
        "deciding that exact pin evidence is absent.\n"
        "::notice title=ReproLLM audit::Level 1 · profiles: core · "
        "0 critical, 0 warning, 0 info, 0 passed\n\n"
    )
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert result.stdout == expected


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param("requests>=2", id="legacy-greater-equal"),
        pytest.param("requests<=2", id="legacy-less-equal"),
        pytest.param("requests!=2", id="legacy-not-equal"),
        pytest.param("requests>2", id="legacy-greater"),
        pytest.param("requests<2", id="legacy-less"),
        pytest.param("requests~=2", id="legacy-compatible"),
        pytest.param("requests", id="bare"),
        pytest.param("requests=2.5.1", id="prefix"),
        pytest.param("requests==2.5.1", id="numeric-exact"),
        pytest.param("requests=2.5.1=cpu_0", id="literal-build"),
    ],
)
def test_legacy_supported_controls_keep_complete_warning(tmp_path: Path, entry: str) -> None:
    """CS-A09/A10: a diagnostic or a nonexact value alone never adds CS uncertainty."""
    repo = _repo(tmp_path)
    _body(repo, f"dependencies:\n- {entry}\n")
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 1 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [_failed_pin()])


@pytest.mark.parametrize("state", ["no-use", "exact-complete", "exact-partial"])
def test_no_use_and_positive_credit_keep_real_engine_empty_result_policy(
    tmp_path: Path, state: str
) -> None:
    """CS-A28: a real Python syntax gap retains the existing empty-result PASS veto."""
    repo = _repo(tmp_path)
    if state == "no-use":
        (repo / "train.py").write_text("pass\n", encoding="utf-8")
    else:
        (repo / "requirements.txt").write_text("torch==2.5.1\n", encoding="utf-8")
        if state == "exact-partial":
            (repo / "train.py").write_text("broken =\n", encoding="utf-8")
    _body(repo, _BAD)
    expected = {
        "rule_id": _PIN,
        "aliases": [],
        "category": "env",
        "severity": "PASS" if state == "exact-complete" else "INFO",
        "status": "pass" if state == "exact-complete" else "skipped",
        "level": 1,
        "message": (
            "no LLM-critical package is declared or imported"
            if state == "no-use"
            else "Python candidate analysis incomplete: parsed 0 of 1 candidate files; selected 1 "
            "(limit 500); no rule-wide PASS is established."
            if state == "exact-partial"
            else "Every LLM-critical dependency in use is pinned to an exact version."
        ),
        "evidence": [],
        "fix_hint": "Pin the package exactly (see the message for the suggested version).",
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [expected])


def _snapshot(repo: Path, names: list[str]) -> dict[str, bytes]:
    return {name: (repo / name).read_bytes() for name in names}


def _expected_export(state: str, *, mixed: bool = False, selected: str | None = None) -> str:
    return _export_expected(state, mixed=mixed, selected=selected).replace(
        "pep621", "conda-specifier"
    )


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize("mixed", [False, True], ids=["isolated", "independent-warning"])
def test_complete_export_bytes_repeat_across_roots_and_preserve_written_history(
    tmp_path: Path, mixed: bool, newline: str
) -> None:
    """CS-A31/A34/A37: preserve actual written bytes, including platform newline variants."""
    exports: list[bytes] = []
    audits: list[str] = []
    for location in ("first", "different-root"):
        repo = _repo(tmp_path / location, mixed=mixed)
        _body(repo, _GOOD, newline)
        output = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert output.read_bytes() == _expected_export("fail", mixed=mixed).encode("utf-8")
        before_audit = runner.invoke(
            app, ["audit", str(repo), "--format", "json", "--fail-on", "never"]
        )
        assert before_audit.exit_code == 0 and before_audit.stderr == "", before_audit.output
        assert _report(before_audit.stdout) == _expected_report(
            repo, [_failed_pin(), *([_python_warning()] if mixed else [])]
        )
        old_run = {
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
        RunRecord.model_validate(old_run)
        history = {
            "history/audit.json": before_audit.stdout.encode("utf-8"),
            "history/REPRODUCIBILITY.md": output.read_bytes(),
            "history/run.json": (json.dumps(old_run, sort_keys=True) + "\n").encode("utf-8"),
            "history/snapshots/reprollm.yaml": (repo / "reprollm.yaml").read_bytes(),
        }
        for name, content in history.items():
            target = repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        history_before = _snapshot(repo, list(history))
        _body(repo, _BAD, newline)
        input_names = [
            "environment.yml",
            "train.py",
            "reprollm.yaml",
            ".reprollm/profiles/core.yaml",
        ]
        inputs_before = _snapshot(repo, input_names)
        assert newline.encode("ascii") in inputs_before["environment.yml"]
        for _ in range(2):
            result = runner.invoke(app, ["export", str(repo), "--output", str(output)])
            assert result.exit_code == 0 and result.stderr == "", result.output
            assert output.read_bytes() == _expected_export("skipped", mixed=mixed).encode("utf-8")
            exports.append(output.read_bytes())
            current = runner.invoke(
                app, ["audit", str(repo), "--format", "json", "--fail-on", "never"]
            )
            assert current.exit_code == 0 and current.stderr == "", current.output
            assert _report(current.stdout) == _expected_report(
                repo, [*([_python_warning()] if mixed else []), _skipped_pin()]
            )
            audits.append(_stable(current.stdout))
        assert _snapshot(repo, list(history)) == history_before
        assert _snapshot(repo, input_names) == inputs_before
    assert all(value == exports[0] for value in exports)
    assert all(value == audits[0] for value in audits)


def _detection() -> dict[str, Any]:
    return {
        "profiles": [
            {
                "profile": "inference",
                "confidence": "medium",
                "shipped": True,
                "evidence": [
                    _evidence("environment.yml", "dependency vllm", kind="detection", line=2)
                ],
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


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize("explicit", [False, True], ids=["detected-profile", "explicit-profile"])
def test_complete_init_files_detection_hints_and_followup_consumers_preserve_inputs(
    tmp_path: Path, explicit: bool, newline: str
) -> None:
    """CS-A35/A37: actual init files remain equal across valid/uncertain source records."""
    selected = "manual" if explicit else "inference"
    generated: list[dict[str, bytes]] = []
    for unsupported in (False, True):
        repo = _repo(tmp_path / ("unsupported" if unsupported else "range"))
        (repo / "reprollm.yaml").unlink()
        for profile in ("inference", "manual"):
            (repo / f".reprollm/profiles/{profile}.yaml").write_text(
                f"schema_version: 1\nname: {profile}\ndescription: Isolated init profile.\n"
                "extends: [core]\nrules: []\n"
                + ("detect: {dependencies: [vllm]}\n" if profile == "inference" else ""),
                encoding="utf-8",
            )
        entry = "requests==2.5.*" if unsupported else "requests>=2"
        _body(repo, f"dependencies:\n- {entry}\n- vllm==1\n", newline)
        input_names = [
            "environment.yml",
            "train.py",
            ".reprollm/profiles/core.yaml",
            ".reprollm/profiles/inference.yaml",
            ".reprollm/profiles/manual.yaml",
        ]
        inputs_before = _snapshot(repo, input_names)
        assert newline.encode("ascii") in inputs_before["environment.yml"]
        assert AuditContext(repo).detection.model_dump(mode="json") == _detection()
        result = runner.invoke(
            app, ["init", str(repo), *(["--profiles", "manual"] if explicit else [])]
        )
        assert result.exit_code == 0 and result.stderr == "", result.output
        expected = {
            "reprollm.yaml": _manifest(selected).replace("pep621", "conda-specifier"),
            ".reprollm/config.yaml": _CONFIG,
            ".reprollm/project-rules.yaml": _PROJECT_RULES,
        }
        actual = _snapshot(repo, list(expected))
        assert actual == {name: value.encode("utf-8") for name, value in expected.items()}
        generated.append(actual)
        audit = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
        assert audit.exit_code == (0 if unsupported else 1) and audit.stderr == "", audit.output
        assert _report(audit.stdout) == _expected_report(
            repo,
            [_skipped_pin() if unsupported else _failed_pin()],
            selected=selected,
            detected=_detection()["profiles"],
        )
        output = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert output.read_bytes() == _expected_export(
            "skipped" if unsupported else "fail", selected=selected
        ).encode("utf-8")
        assert _snapshot(repo, input_names) == inputs_before
    assert generated[0] == generated[1]


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param("==hf_" + "S" * 40, id="synthetic-token"),
        pytest.param(" /home/CS_FAKE_USER/CS_FAKE_MACHINE/private", id="synthetic-machine-path"),
    ],
)
def test_complete_persisted_report_and_export_do_not_disclose_discarded_suffix(
    tmp_path: Path, suffix: str
) -> None:
    """CS-A08: only fixed placeholder/source evidence survives the real public commands."""
    repo = _repo(tmp_path)
    _body(repo, f"dependencies:\n- requests{suffix}\n")
    inputs_before = _snapshot(repo, ["environment.yml", "train.py", "reprollm.yaml"])
    report_path = repo / "report.json"
    result = runner.invoke(
        app,
        [
            "audit",
            str(repo),
            "--format",
            "json",
            "--output",
            str(report_path),
            "--fail-on",
            "warning",
        ],
    )
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert result.stdout == f"Wrote audit report to {report_path} (0 critical, 0 warning)\n"
    assert _report(report_path.read_text(encoding="utf-8")) == _expected_report(
        repo, [_skipped_pin()]
    )
    output = repo / "REPRODUCIBILITY.md"
    exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
    assert exported.exit_code == 0 and exported.stderr == "", exported.output
    assert output.read_bytes() == _expected_export("skipped").encode("utf-8")
    for content in (report_path.read_text(encoding="utf-8"), output.read_text(encoding="utf-8")):
        assert suffix not in content
        assert "CS_FAKE_USER" not in content and "CS_FAKE_MACHINE" not in content
    assert _snapshot(repo, list(inputs_before)) == inputs_before


def _selected_export_expected(state: str) -> str:
    return (
        _expected_export(state)
        .replace("statement — conda-specifier", "statement — captured-experiment")
        .replace(
            "from the current manifest and available lockfile.",
            "from the selected run's recorded observations and available manifest/lock snapshots.",
        )
        .replace(
            "### Generation parameters\n\n\n",
            "### Generation parameters\n\n"
            "- `max_tokens`: 17\n- `temperature`: 0.25\n- `top_p`: 0.9\n\n",
        )
        .replace(
            "- commit: `unknown`\n- branch: unknown\n- dirty: unknown\n- remote: not recorded\n",
            f"- commit: `{'a' * 40}`\n- branch: static-fixture\n- dirty: False\n"
            "- remote: https://example.invalid/static.git\n",
        )
        .replace(
            "No run record exists for this experiment. Wrap the command with\n"
            "`reprollm run -- <command>` to record what actually executed.\n",
            "Input observation phase: unknown (legacy run record).\n\n"
            "- command: `python recorded.py`\n- run id: `20261001T000000Z-abcdef`\n"
            "- started: 2026-10-01 00:00:00+00:00 · ended: 2026-10-01 00:00:01+00:00 · "
            "duration: 1.0 s\n- exit code: 0 (completed)\n",
        )
        .replace(
            "None recorded by ReproLLM.\n",
            "- Child Python and packages are unverified.\n"
            "- Input consumption by the child is unverified.\n",
        )
        .replace("lock n/a,\nrun record n/a.", "lock 1,\nrun record 1.")
    )


def test_selected_static_run_and_nonempty_lock_preserve_complete_export_sources(
    tmp_path: Path,
) -> None:
    """CS-A34: consume a typed static record, without claiming a newly executed child."""
    repo = _repo(tmp_path)
    current_manifest = (
        "schema_version: 1\nproject: {name: conda-specifier}\nexperiment: {profiles: []}\n"
        "generation: {temperature: 1.5, top_p: 0.3}\n"
    )
    captured_manifest = (
        "schema_version: 1\nproject: {name: captured-experiment}\nexperiment: {profiles: []}\n"
        "generation: {temperature: 0.75, top_p: 0.9}\n"
    )
    (repo / "reprollm.yaml").write_bytes(current_manifest.encode("utf-8"))
    captured_lock = {
        "schema_version": 1,
        "reprollm_version": "0.7.0",
        "generated_at": "2026-10-01T00:00:00Z",
        "manifest_sha256": "sha256:"
        + hashlib.sha256(captured_manifest.encode("utf-8")).hexdigest(),
        "resolution": {"mode": "offline"},
        "generation": {"max_tokens": 17},
    }
    Lock.model_validate(captured_lock)
    working_lock = {
        **captured_lock,
        "manifest_sha256": "sha256:" + hashlib.sha256(current_manifest.encode("utf-8")).hexdigest(),
        "generation": {"max_tokens": 99},
    }
    Lock.model_validate(working_lock)
    lock_text = yaml.safe_dump(captured_lock, sort_keys=False)
    (repo / "reprollm.lock").write_bytes(yaml.safe_dump(working_lock).encode("utf-8"))
    run_name = ".reprollm/runs/20261001T000000Z-abcdef"
    run_dir = repo / run_name
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.yaml").write_bytes(captured_manifest.encode("utf-8"))
    (run_dir / "lock.yaml").write_bytes(lock_text.encode("utf-8"))
    record = {
        "schema_version": 1,
        "reprollm_version": "0.7.0",
        "run_id": "20261001T000000Z-abcdef",
        "status": "completed",
        "command": {"argv": ["python", "recorded.py"], "cwd": "."},
        "started_at": "2026-10-01T00:00:00Z",
        "ended_at": "2026-10-01T00:00:01Z",
        "duration_seconds": 1.0,
        "exit_code": 0,
        "code": {
            "commit": "a" * 40,
            "branch": "static-fixture",
            "dirty": False,
            "remote": "https://example.invalid/static.git",
        },
        "manifest": {
            "path": "reprollm.yaml",
            "sha256": "sha256:" + hashlib.sha256(captured_manifest.encode("utf-8")).hexdigest(),
            "snapshot": "manifest.yaml",
        },
        "lock": {
            "path": "reprollm.lock",
            "sha256": "sha256:" + hashlib.sha256(lock_text.encode("utf-8")).hexdigest(),
            "snapshot": "lock.yaml",
        },
        "bindings_observed": {
            "generation.temperature": [
                {"source": {"type": "cli", "key": "--temperature"}, "value": 0.25}
            ]
        },
    }
    RunRecord.model_validate(record)
    (run_dir / "run.json").write_bytes((json.dumps(record, sort_keys=True) + "\n").encode("utf-8"))
    names = [
        "reprollm.yaml",
        "reprollm.lock",
        "train.py",
        ".reprollm/profiles/core.yaml",
        f"{run_name}/run.json",
        f"{run_name}/manifest.yaml",
        f"{run_name}/lock.yaml",
    ]
    before = _snapshot(repo, names)
    for state, body in (("fail", _GOOD), ("skipped", _BAD)):
        _body(repo, body)
        environment_before = (repo / "environment.yml").read_bytes()
        output = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(
            app, ["export", str(repo), "--run", "20261001T000000Z-abcdef", "--output", str(output)]
        )
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert output.read_bytes() == _selected_export_expected(state).encode("utf-8")
        finding = _failed_pin() if state == "fail" else _skipped_pin()
        finding["level"] = 2
        expected = _expected_report(repo, [finding])
        expected["level"] = 2
        expected["documents"].update(
            {
                "lock": "sha256:"
                + hashlib.sha256((repo / "reprollm.lock").read_bytes()).hexdigest(),
                "runs": 1,
            }
        )
        audited = runner.invoke(
            app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"]
        )
        assert audited.exit_code == int(state == "fail") and audited.stderr == "", audited.output
        assert _report(audited.stdout) == expected
        assert _snapshot(repo, names) == before
        assert (repo / "environment.yml").read_bytes() == environment_before
