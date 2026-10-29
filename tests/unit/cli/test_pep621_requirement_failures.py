"""D-M-P P29-P35: complete consumer oracles, written before implementation."""

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
from reprollm.core import registry
from reprollm.core.context import AuditContext
from reprollm.core.pyscan import PyScanResult
from reprollm.rules.env import LlmCriticalDepsPinnedRule
from reprollm.schemas.finding import AuditReport
from reprollm.schemas.run_record import RunRecord
from tests.conftest import commit_all, make_git_repo

runner = CliRunner()
_PIN = "env.llm_critical_deps_pinned"
_HINT = "Pin the package exactly (see the message for the suggested version)."
_PASS = "Every LLM-critical dependency in use is pinned to an exact version."
_NO_USE = "no LLM-critical package is declared or imported"
_REASON = "Reviewed captured PEP 621 failure."
_BAD = '[project]\ndependencies=["torch>=2", "bad !!!"]\n'
_GOOD = '[project]\ndependencies=["torch>=2"]\n'
_DIAGNOSTIC = "scan: pyproject.toml:2: bad !!!\n"


@pytest.fixture(autouse=True)
def fixed_installed_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})


def _repo(tmp_path: Path, severity: str = "WARNING", mixed: bool = False) -> Path:
    repo = make_git_repo(tmp_path / "pep621")
    profiles = repo / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated PEP 621 consumers.",
                "rules": [_PIN] + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {_PIN: severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: pep621}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    return repo


def _body(repo: Path, text: str) -> None:
    (repo / "pyproject.toml").write_text(text, encoding="utf-8")
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
    state: str,
    severity: str = "WARNING",
    *,
    package: str = "torch",
    suppressed: bool = False,
    alias: bool = False,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "rule_id": _PIN,
        "aliases": ["env.previous_pin"] if alias else [],
        "category": "env",
        "severity": "PASS" if state == "pass" else "INFO",
        "status": "skipped" if state == "no-use" else state,
        "level": 1,
        "message": _PASS if state == "pass" else _NO_USE,
        "evidence": [],
        "fix_hint": _HINT,
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    if state in {"fail", "skipped"}:
        finding["evidence"] = [_evidence("pyproject.toml", "declared as >=2", line=2, value=">=2")]
    if state == "fail":
        finding.update(
            severity=severity,
            severity_origin="profile:core",
            message=(
                f"{package} is used but not pinned to an exact version "
                f"(suggestion: {package}==<version>)"
            ),
            fix_hint=f"Pin {package} exactly, e.g. `{package}==<version>`.",
        )
    elif state == "skipped":
        finding.update(
            message=(
                f"{package} is used; a dependency declaration body could not be read or parsed, "
                "so missing pin evidence is not established"
            ),
            fix_hint=(
                f"Review {package} declarations and failed dependency source files; restore "
                "readable, valid declaration bodies before deciding that exact pin evidence "
                "is absent."
            ),
        )
        finding["evidence"].append(
            _evidence("pyproject.toml", f"{package} possible exact declaration unverified")
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
    findings: list[dict[str, Any]],
    *,
    selected: str | None = None,
    detected: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "reprollm_version": __version__,
        "target": ".",
        "level": 1,
        "profiles": {
            "declared": [selected] if selected else [],
            "resolved": ["core", selected] if selected else ["core"],
            "detected": detected or [],
        },
        "documents": {
            "manifest": "sha256:"
            + hashlib.sha256((repo / "reprollm.yaml").read_bytes()).hexdigest(),
            "lock": None,
            "runs": 0,
        },
        "summary": {
            "critical": sum(f["severity"] == "CRITICAL" for f in findings),
            "warning": sum(f["severity"] == "WARNING" for f in findings),
            "info": sum(f["severity"] == "INFO" and f["status"] == "fail" for f in findings),
            "pass": sum(f["status"] == "pass" for f in findings),
            "suppressed": sum(f["status"] == "suppressed" for f in findings),
            "skipped": sum(f["status"] == "skipped" for f in findings),
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
def test_full_reports_and_thresholds_change_on_failure_then_restore(
    tmp_path: Path, severity: str, threshold: str, old_exit: int
) -> None:
    repo = _repo(tmp_path, severity)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]
    _body(repo, _GOOD)
    before = runner.invoke(app, args)
    assert before.exit_code == old_exit, before.output
    assert before.stderr == ""
    assert _report(before.stdout) == _expected_report(repo, [_pin("fail", severity)])
    _body(repo, _BAD)
    after = runner.invoke(app, args)
    assert after.exit_code == 0, after.output
    assert after.stderr == ""
    assert _report(after.stdout) == _expected_report(repo, [_pin("skipped")])
    repeat = runner.invoke(app, args)
    assert repeat.exit_code == 0 and repeat.stderr == ""
    assert _stable(after.stdout) == _stable(repeat.stdout)
    _body(repo, _GOOD)
    restored = runner.invoke(app, args)
    assert restored.exit_code == old_exit and restored.stderr == ""
    assert _stable(restored.stdout) == _stable(before.stdout)


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
def test_independent_warning_keeps_failure_and_entire_finding(
    tmp_path: Path, severity: str
) -> None:
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
def test_suppression_retains_body_evidence_and_original_info_even_with_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: bool
) -> None:
    if alias:
        # The released rule has no alias; isolate the existing compatibility contract.
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
def test_default_and_explicit_text_visibility_and_original_verbose_diagnostic(
    tmp_path: Path, show_skipped: bool, show_passed: bool, verbose: bool
) -> None:
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
    assert result.stderr == (_DIAGNOSTIC if verbose else "")
    complete = runner.invoke(app, [*args, "--format", "json"])
    assert complete.exit_code == 0
    assert complete.stderr == (_DIAGNOSTIC if verbose else "")
    assert _report(complete.stdout) == _expected_report(repo, [_pin("skipped")])


@pytest.mark.parametrize("coverage", ["complete", "gap", "unavailable", "inconsistent"])
@pytest.mark.parametrize("credit", [False, True])
def test_no_use_and_credited_empty_result_preserve_python_veto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coverage: str, credit: bool
) -> None:
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
    valid = '"torch==2", ' if credit else '"requests>=2", '
    _body(repo, f'[project]\ndependencies=[{valid}"vllm ???"]\n')
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
    assert result.exit_code == 0, result.output
    assert _report(result.stdout) == _expected_report(repo, [expected])
    # The injected internal assessment adds no diagnostic prose or scan warning.
    assert result.stderr == ""


def _export_expected(state: str, *, selected: str | None = None, mixed: bool = False) -> str:
    warning = int(state == "fail") + int(mixed)
    profile = f"Declared profiles: {selected}.\n" if selected else ""
    notable = ""
    if state == "fail":
        notable += (
            "- **WARNING** `env.llm_critical_deps_pinned`: torch is used but not pinned "
            "to an exact version (suggestion: torch==&lt;version&gt;)\n"
        )
    if mixed:
        notable += (
            "- **WARNING** `env.python_version_declared`: "
            "no Python version requirement is declared\n"
        )
    return (
        f"# Reproducibility statement — pep621\n\n"
        f"Generated by [ReproLLM](https://github.com/EnumaElish123/ReproLLM) {__version__}\n"
        "from the current manifest and available lockfile.\n"
        f"{profile}\n"
        "## Experiment identity\n\n"
        "Evidence labels distinguish declared manifest values, locked values with their\n"
        "recorded confidence, and observed run values. A run does not establish execution\n"
        "of fields without an observed value.\n\n"
        "### Models\n\n"
        "| Role | Provider | ID | Revision | Pinnability | Tokenizer | Chat template |\n"
        "|---|---|---|---|---|---|---|\n\n"
        "### Datasets\n\n"
        "| Role | Provider | ID | Revision | Content fingerprint |\n"
        "|---|---|---|---|---|\n\n"
        "### Prompts\n\n| Role | Source | SHA-256 |\n|---|---|---|\n\n"
        "### Generation parameters\n\n\n"
        "### Inference backend\n\n\n"
        "## Code\n\n- commit: `unknown`\n- branch: unknown\n- dirty: unknown\n"
        "- remote: not recorded\n\n"
        "## Environment\n\n- Python evidence: not captured.\n"
        "- Inherited environment: not captured.\n- Python: unknown\n\n"
        "## Hardware\n\n- Collector evidence: not captured.\n"
        "Hardware information was not captured.\n\n"
        "## Execution\n\nNo run record exists for this experiment. Wrap the command with\n"
        "`reprollm run -- <command>` to record what actually executed.\n\n"
        "## Audit summary\n\n"
        "Audit scope: the current working tree and its available documents, including the\n"
        "latest valid run when available. This summary is computed at export time; it is\n"
        "not a separate audit of a selected historical run.\n\n"
        f"0 critical · {warning} warning ·\n0 info · 0 passed.\n\n{notable}\n"
        "## Known limitations\n\nNone recorded by ReproLLM.\n\n---\n\n"
        f"Exported with reprollm {__version__} ·\nschema versions: manifest 1,\n"
        "lock n/a,\nrun record n/a.\nCommit this file with your paper artifact.\n"
    )


@pytest.mark.parametrize("mixed", [False, True])
def test_full_default_export_preserves_independent_warning_and_historical_bytes(
    tmp_path: Path, mixed: bool
) -> None:
    exports: list[bytes] = []
    audits: list[str] = []
    for prefix in ("first", "different-location"):
        repo = _repo(tmp_path / prefix, mixed=mixed)
        _body(repo, _GOOD)
        output = repo / "REPRODUCIBILITY.md"
        before = runner.invoke(app, ["export", str(repo), "--output", str(output)])
        assert before.exit_code == 0 and before.stderr == "", before.output
        assert output.read_text(encoding="utf-8") == _export_expected("fail", mixed=mixed)
        audit = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
        assert audit.exit_code == 0 and audit.stderr == ""
        assert _report(audit.stdout) == _expected_report(
            repo, [_pin("fail"), *([_python_warning()] if mixed else [])]
        )
        history = repo / "history"
        history.mkdir()
        archived_run = {
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
        RunRecord.model_validate(archived_run)
        # Archived valid legacy records are preserved, not selected as a current run.
        historical = {
            "audit.json": audit.stdout.encode(),
            "REPRODUCIBILITY.md": output.read_bytes(),
            "run.json": (json.dumps(archived_run, sort_keys=True) + "\n").encode(),
            "snapshots/reprollm.yaml": (repo / "reprollm.yaml").read_bytes(),
        }
        for name, content in historical.items():
            path = history / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        _body(repo, _BAD)
        for _ in range(2):
            result = runner.invoke(app, ["export", str(repo), "--output", str(output)])
            assert result.exit_code == 0 and result.stderr == ""
            assert output.read_text(encoding="utf-8") == _export_expected("skipped", mixed=mixed)
            exports.append(output.read_bytes())
            current = runner.invoke(
                app, ["audit", str(repo), "--format", "json", "--fail-on", "never"]
            )
            assert current.exit_code == 0 and current.stderr == ""
            assert _report(current.stdout) == _expected_report(
                repo, [*([_python_warning()] if mixed else []), _pin("skipped")]
            )
            audits.append(_stable(current.stdout))
        assert {name: (history / name).read_bytes() for name in historical} == historical
    assert all(value == exports[0] for value in exports)
    assert all(value == audits[0] for value in audits)


def _detection(imported: bool = False) -> dict[str, Any]:
    return {
        "profiles": [
            {
                "profile": "inference",
                "confidence": "high" if imported else "medium",
                "shipped": True,
                "evidence": [
                    _evidence(
                        "app.py" if imported else "pyproject.toml",
                        "import vllm" if imported else "dependency vllm",
                        kind="detection",
                        line=1 if imported else 2,
                    )
                ],
            }
        ],
        "hints": {
            "providers": [],
            "backends": ["vllm"] if imported else [],
            "datasets": False,
            "adapter": False,
            "trust_remote_code": False,
            "hf_ids": [],
        },
    }


@pytest.mark.parametrize("imported", [False, True])
def test_failed_strings_do_not_change_full_detection_or_invent_profiles(
    tmp_path: Path, imported: bool
) -> None:
    repo = _repo(tmp_path)
    if imported:
        (repo / "app.py").write_text("import vllm\n", encoding="utf-8")
    for invalid in (False, True):
        tail = ', "peft ???", "openai !!!"' if invalid else ""
        _body(repo, f'[project]\ndependencies=["vllm>=2"{tail}]\n')
        assert AuditContext(repo).detection.model_dump(mode="json") == _detection(imported)


_EXAMPLES = [
    "models:\n  primary:\n    provider: huggingface\n    id: org/model\n    revision: <commit sha>",
    "datasets:\n  eval:\n    provider: huggingface\n    id: cais/mmlu\n    split: test",
    "prompts:\n  system:\n    path: prompts/system.txt\n    format: plain",
    "generation:\n  temperature: 0.0\n  top_p: 1.0\n  max_tokens: 2048\n  seed: 42",
    "inference:\n  backend: vllm  # vllm | transformers | sglang | openai | other\n"
    "  dtype: bfloat16\n  tensor_parallel_size: 1",
    "training:\n  method: lora\n  learning_rate: 0.0001\n  batch_size: 8",
    "evaluation:\n  metrics:\n    - {name: accuracy, implementation: eval.py}\n"
    "  aggregation: mean\n  repetitions: 1",
    "privacy:\n  threat_model: honest-but-curious server\n"
    "  mechanism: {name: orthogonal_noise, params: {alpha: 0.25}}",
    "execution:\n  command: python eval.py --config configs/eval.yaml\n"
    "  seed: 42\n  config_files: [configs/eval.yaml]",
]
_CONFIG = """# .reprollm/config.yaml — tool configuration (spec §8).
# CLI flags override this file; this file overrides defaults.

schema_version: 1

audit:
  fail_on: critical   # critical | warning | never
  ignore: []          # e.g. [{rule: code.no_untracked, reason: "generated notebooks"}]
  show_passed: false

run:
  env_capture: allowlist   # allowlist | all
  capture_output: false
  snapshot_max_bytes: 1048576
  extra_env_allowlist: []  # extra exact env names or prefixes ending with "_"

discover:
  enabled: false           # must also pass --experimental on the CLI
  base_url_env: REPROLLM_LLM_BASE_URL
  api_key_env: REPROLLM_LLM_API_KEY
  model_env: REPROLLM_LLM_MODEL
  max_chars: 60000
"""
_PROJECT_RULES = """# .reprollm/project-rules.yaml — repository-specific accepted rules (spec §7).
# Add rules with `reprollm rules add` (M7) or edit manually.
schema_version: 1
rules: []
ignored_candidates: []
"""


def _manifest(selected: str) -> str:
    return (
        "# reprollm.yaml — what this experiment intends to run (spec §3).\n"
        "# Generated by `reprollm init` from detected signals.\n"
        "# Keys marked TODO are required by your profiles; commented blocks are examples.\n"
        "# Detected values are candidates; verify that each one has the right experiment role.\n"
        "# The manifest stays loadable: `reprollm audit .` validates it.\n\n"
        "schema_version: 1\n\nproject:\n  name: pep621\n\n"
        f"experiment:\n  profiles: [{selected}]\n\n\n"
        "# --- Example sections (uncomment and edit what applies) ----------------------\n"
        + "".join(
            "\n" + "\n".join("# " + line for line in block.splitlines()) + "\n\n"
            for block in _EXAMPLES
        )
        + "\n"
    )


@pytest.mark.parametrize("explicit", [False, True])
def test_default_and_explicit_init_keep_all_files_but_l1_and_export_change(
    tmp_path: Path, explicit: bool
) -> None:
    selected = "manual" if explicit else "inference"
    outputs: list[dict[str, bytes]] = []
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
        tail = ', "bad !!!"' if invalid else ""
        _body(repo, f'[project]\ndependencies=["torch>=2", "vllm==1"{tail}]\n')
        assert AuditContext(repo).detection.model_dump(mode="json") == _detection()
        result = runner.invoke(
            app, ["init", str(repo), *(["--profiles", "manual"] if explicit else [])]
        )
        assert result.exit_code == 0 and result.stderr == "", result.output
        expected_files = {
            "reprollm.yaml": _manifest(selected),
            ".reprollm/config.yaml": _CONFIG,
            ".reprollm/project-rules.yaml": _PROJECT_RULES,
        }
        actual = {name: (repo / name).read_bytes() for name in expected_files}
        assert actual == {name: value.encode() for name, value in expected_files.items()}
        outputs.append(actual)
        audit = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])
        assert audit.exit_code == (0 if invalid else 1) and audit.stderr == "", audit.output
        assert _report(audit.stdout) == _expected_report(
            repo,
            [_pin("skipped" if invalid else "fail")],
            selected=selected,
            detected=_detection()["profiles"],
        )
        export = repo / "REPRODUCIBILITY.md"
        exported = runner.invoke(app, ["export", str(repo), "--output", str(export)])
        assert exported.exit_code == 0 and exported.stderr == "", exported.output
        assert export.read_text(encoding="utf-8") == _export_expected(
            "skipped" if invalid else "fail", selected=selected
        )
    assert outputs[0] == outputs[1]
