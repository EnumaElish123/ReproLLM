"""D-M-CE CE-A31-A36: public CLI and consumer acceptance."""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.context import AuditContext
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
_BAD = "dependencies:\n- conda-forge::requests==2.5.1\n"
_REASON = "Reviewed captured native Conda omission."


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _repo(tmp_path: Path, severity: str = "WARNING", mixed: bool = False) -> Path:
    repo = make_git_repo(tmp_path / "conda-omission")
    profiles = repo / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated native Conda omission consumers.",
                "rules": [_PIN] + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {_PIN: severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: conda-omission}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "train.py").write_text("import torch\n", encoding="utf-8")
    return repo


def _body(repo: Path, text: str) -> None:
    (repo / "environment.yml").write_text(text, encoding="utf-8")
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


def _failed_pin(severity: str = "WARNING") -> dict[str, Any]:
    finding = _skipped_pin()
    finding.update(
        severity=severity,
        status="fail",
        severity_origin="profile:core",
        message="torch is used but not pinned to an exact version (suggestion: torch==<version>)",
        fix_hint="Pin torch exactly, e.g. `torch==<version>`.",
        evidence=[_evidence("train.py", "imported", line=1)],
    )
    return finding


def test_channel_omission_keeps_entire_skip_report_and_warning_exit_zero(tmp_path: Path) -> None:
    """CE-A31/A32: unrelated native omission changes an isolated real audit outcome."""
    repo = _repo(tmp_path)
    _body(repo, _BAD)
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 0 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [_skipped_pin()])


@pytest.mark.parametrize(
    "omitted",
    [
        pytest.param("conda-forge::requests==2.5.1", id="channel-prefix"),
        pytest.param("*", id="no-name-match"),
    ],
)
@pytest.mark.parametrize(
    ("severity", "threshold", "before_exit"),
    [
        ("WARNING", "warning", 1),
        ("CRITICAL", "critical", 1),
        ("WARNING", "critical", 0),
        ("CRITICAL", "warning", 1),
        ("WARNING", "never", 0),
        ("CRITICAL", "never", 0),
    ],
)
def test_entire_json_thresholds_repeat_and_restore(
    tmp_path: Path, omitted: str, severity: str, threshold: str, before_exit: int
) -> None:
    """CE-A31/A32/A34: exact reports expose global relaxation and preserve thresholds."""
    repo = _repo(tmp_path, severity)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]
    _body(repo, _GOOD)
    before = runner.invoke(app, args)
    assert before.exit_code == before_exit and before.stderr == "", before.output
    assert _report(before.stdout) == _expected_report(repo, [_failed_pin(severity)])
    _body(repo, f"dependencies:\n- {omitted!r}\n")
    after = runner.invoke(app, args)
    assert after.exit_code == 0 and after.stderr == "", after.output
    assert _report(after.stdout) == _expected_report(repo, [_skipped_pin()])
    repeat = runner.invoke(app, args)
    assert repeat.exit_code == 0 and repeat.stderr == ""
    assert _stable(repeat.stdout) == _stable(after.stdout)
    _body(repo, _GOOD)
    restored = runner.invoke(app, args)
    assert restored.exit_code == before_exit and restored.stderr == ""
    assert _stable(restored.stdout) == _stable(before.stdout)


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
def test_independent_warning_keeps_entire_finding_and_exit_one(
    tmp_path: Path, severity: str
) -> None:
    """CE-A32: the pin relaxation does not hide a separate qualifying failure."""
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


def test_suppression_preserves_info_cause_despite_critical_override(tmp_path: Path) -> None:
    """CE-A32: FAIL-only severity promotion never rewrites the new SKIP."""
    repo = _repo(tmp_path, "CRITICAL")
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
@pytest.mark.parametrize("show_passed", [False, True])
@pytest.mark.parametrize("verbose", [False, True])
def test_entire_text_visibility_preserves_original_ordinal_diagnostic(
    tmp_path: Path, show_skipped: bool, show_passed: bool, verbose: bool
) -> None:
    """CE-A31: text can show PASS; verbose keeps the old list ordinal, not YAML line 2."""
    repo = _repo(tmp_path)
    _body(repo, _BAD)
    flags = ["--show-skipped"] if show_skipped else []
    flags += ["--show-passed"] if show_passed else []
    args = [*(["--verbose"] if verbose else []), "audit", str(repo), "--fail-on", "warning"]
    expected = "ReproLLM audit · level 1 · profiles: core\n\n"
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
    diagnostic = "scan: environment.yml:1: unsupported conda declaration\n" if verbose else ""
    result = runner.invoke(app, [*args, *flags])
    assert result.exit_code == 0, result.output
    assert result.stdout == expected
    assert result.stderr == diagnostic
    complete = runner.invoke(app, [*args, *flags, "--format", "json"])
    assert complete.exit_code == 0 and complete.stderr == diagnostic, complete.output
    assert _report(complete.stdout) == _expected_report(repo, [_skipped_pin()])


@pytest.mark.parametrize("credit", [False, True], ids=["no-known-use", "captured-exact"])
def test_omission_adds_no_use_and_never_revokes_positive_credit(
    tmp_path: Path, credit: bool
) -> None:
    """CE-A34: the public engine preserves current applicability and positive credit."""
    repo = _repo(tmp_path)
    if credit:
        (repo / "requirements.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    else:
        (repo / "train.py").write_text("", encoding="utf-8")
    _body(repo, _BAD)
    expected = {
        "rule_id": _PIN,
        "aliases": [],
        "category": "env",
        "severity": "PASS" if credit else "INFO",
        "status": "pass" if credit else "skipped",
        "level": 1,
        "message": (
            "Every LLM-critical dependency in use is pinned to an exact version."
            if credit
            else "no LLM-critical package is declared or imported"
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


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("dependencies: ['requests>=2']\n", id="numeric-range"),
        pytest.param("dependencies: ['requests==2.4.*']\n", id="retained-wildcard"),
        pytest.param("dependencies: ['https://example.invalid/pkg.whl']\n", id="url-head"),
        pytest.param("dependencies: ['requests /file']\n", id="spaced-slash"),
        pytest.param(
            "dependencies: [{other: ['conda-forge::requests']}]\n", id="unknown-installer"
        ),
    ],
)
def test_excluded_entries_keep_entire_current_warning_and_exit_one(
    tmp_path: Path, body: str
) -> None:
    """CE-A36: the accepted policy does not become a general Conda syntax validator."""
    repo = _repo(tmp_path)
    _body(repo, body)
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
    assert result.exit_code == 1 and result.stderr == "", result.output
    assert _report(result.stdout) == _expected_report(repo, [_failed_pin()])


def _expected_export(state: str, *, mixed: bool = False, selected: str | None = None) -> str:
    return _export_expected(state, mixed=mixed, selected=selected).replace(
        "pep621", "conda-omission"
    )


@pytest.mark.parametrize("mixed", [False, True], ids=["isolated", "independent-warning"])
def test_default_export_full_bytes_repeat_across_roots_and_preserve_history(
    tmp_path: Path, mixed: bool
) -> None:
    """CE-A31/A34: the previous notable warning disappears without changing history."""
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
        assert audit.exit_code == 0 and audit.stderr == "", audit.output
        assert _report(audit.stdout) == _expected_report(
            repo, [_failed_pin(), *([_python_warning()] if mixed else [])]
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
        historical = {
            "audit.json": audit.stdout.encode(),
            "REPRODUCIBILITY.md": output.read_bytes(),
            "run.json": (json.dumps(historical_run, sort_keys=True) + "\n").encode(),
            "snapshots/reprollm.yaml": (repo / "reprollm.yaml").read_bytes(),
        }
        history = repo / "history"
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
            assert current.exit_code == 0 and current.stderr == "", current.output
            assert _report(current.stdout) == _expected_report(
                repo, [*([_python_warning()] if mixed else []), _skipped_pin()]
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


@pytest.mark.parametrize("explicit", [False, True], ids=["detected-profile", "explicit-profile"])
def test_init_detection_hints_and_complete_generated_files_keep_captured_inventory(
    tmp_path: Path, explicit: bool
) -> None:
    """CE-A33: retained native siblings supply identical init files; omitted text adds none."""
    selected = "manual" if explicit else "inference"
    generated: list[dict[str, bytes]] = []
    for omitted in (False, True):
        repo = _repo(tmp_path / ("omitted" if omitted else "retained"))
        (repo / "reprollm.yaml").unlink()
        for profile in ("inference", "manual"):
            (repo / f".reprollm/profiles/{profile}.yaml").write_text(
                f"schema_version: 1\nname: {profile}\ndescription: Isolated init profile.\n"
                "extends: [core]\nrules: []\n"
                + ("detect: {dependencies: [vllm]}\n" if profile == "inference" else ""),
                encoding="utf-8",
            )
        entry = "conda-forge::requests==2.5.1" if omitted else "requests>=2"
        body = f"dependencies:\n- {entry}\n- vllm==1\n"
        _body(repo, body)
        assert AuditContext(repo).detection.model_dump(mode="json") == _detection()
        result = runner.invoke(
            app, ["init", str(repo), *(["--profiles", "manual"] if explicit else [])]
        )
        assert result.exit_code == 0 and result.stderr == "", result.output
        expected_files = {
            "reprollm.yaml": _manifest(selected).replace("pep621", "conda-omission"),
            ".reprollm/config.yaml": _CONFIG,
            ".reprollm/project-rules.yaml": _PROJECT_RULES,
        }
        actual = {name: (repo / name).read_bytes() for name in expected_files}
        assert actual == {name: text.encode("utf-8") for name, text in expected_files.items()}
        generated.append(actual)
        assert (repo / "environment.yml").read_text(encoding="utf-8") == body
        audit = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
        assert audit.exit_code == (0 if omitted else 1) and audit.stderr == "", audit.output
        assert _report(audit.stdout) == _expected_report(
            repo,
            [_skipped_pin() if omitted else _failed_pin()],
            selected=selected,
            detected=_detection()["profiles"],
        )
        output = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert output.read_bytes() == _expected_export(
            "skipped" if omitted else "fail", selected=selected
        ).encode("utf-8")
    assert generated[0] == generated[1]
