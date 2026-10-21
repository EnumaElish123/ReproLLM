"""audit CLI tests: snapshots, exit codes, schema validation (spec §1)."""

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import scanner as scanner_mod
from tests.conftest import assert_json_snapshot, commit_all, make_git_repo, materialize_repo

runner = CliRunner()

FIXTURES_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "repos"

#: Fixtures with a committed audit_L0.json golden snapshot.
L0_SNAPSHOT_FIXTURES = [
    "hf_vllm_eval",
    "openai_judge_eval",
    "privacy_custom_params",
    "not_a_git_repo",
    "dirty_tree",
    "no_deps_file",
]


def _coverage_cli_repo(tmp_path: Path) -> Path:
    repo = make_git_repo(tmp_path / "coverage")
    profiles = repo / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Focused public CLI coverage regression.",
                "rules": [
                    "code.git_repo",
                    "code.git_commit",
                    "code.clean_tree",
                    "code.no_untracked",
                    "env.llm_critical_deps_pinned",
                    "exec.profile_detection_mismatch",
                ],
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: coverage}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "requirements.txt").write_text("torch==2.5.1\n", encoding="utf-8")
    (repo / "a.py").write_text("value = 1\n", encoding="utf-8")
    (repo / "z.py").write_text("import vllm\n", encoding="utf-8")
    commit_all(repo)
    return repo


def _coverage_cli_json(stdout: str) -> dict[str, Any]:
    report, end = json.JSONDecoder().raw_decode(stdout)
    assert stdout[end:].strip() == ""
    assert isinstance(report, dict)
    schema_path = Path(__file__).resolve().parents[3] / "schemas" / "audit_report.schema.json"
    jsonschema.validate(report, json.loads(schema_path.read_text(encoding="utf-8")))
    assert set(report) == {
        "schema_version",
        "reprollm_version",
        "generated_at",
        "target",
        "level",
        "profiles",
        "documents",
        "summary",
        "findings",
    }
    assert report["schema_version"] == 1
    return report


def test_audit_incomplete_empty_rules_skip_in_one_unchanged_json_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    assert result.stderr == (
        "scan: Python analysis incomplete: parsed 1 of 2 candidate files; "
        "selected 1 (limit 1), omitted 1. Missing signals may be in unanalysed files.\n"
    )
    report = _coverage_cli_json(result.stdout)
    by_id = {finding["rule_id"]: finding for finding in report["findings"]}
    assert set(by_id) == {
        "code.git_repo",
        "code.git_commit",
        "code.clean_tree",
        "code.no_untracked",
        "env.llm_critical_deps_pinned",
        "exec.profile_detection_mismatch",
    }
    for rule_id in ["env.llm_critical_deps_pinned", "exec.profile_detection_mismatch"]:
        finding = by_id[rule_id]
        assert finding["status"] == "skipped"
        assert finding["severity"] == "INFO"
        assert finding["message"] == (
            "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
            "selected 1 (limit 1); no rule-wide PASS is established."
        )
        assert finding["evidence"] == []
        assert finding["severity_origin"] == "default"
        assert finding["suppressed_reason"] is None
    assert all(
        finding["status"] == "pass" for rid, finding in by_id.items() if rid.startswith("code.")
    )
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }


@pytest.mark.parametrize("fail_on", ["critical", "warning", "never"])
def test_audit_gap_only_has_no_failing_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_on: str
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", fail_on])

    assert result.exit_code == 0, result.output
    report = _coverage_cli_json(result.stdout)
    assert len(report["findings"]) == 6
    assert all(finding["status"] in {"pass", "skipped"} for finding in report["findings"])
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }


@pytest.mark.parametrize(("fail_on", "exit_code"), [("critical", 0), ("warning", 1), ("never", 0)])
def test_audit_known_warning_still_controls_thresholds_with_an_independent_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fail_on: str, exit_code: int
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "requirements.txt").write_text("torch>=2.5.1\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", fail_on])

    assert result.exit_code == exit_code, result.output
    report = _coverage_cli_json(result.stdout)
    failures = [finding for finding in report["findings"] if finding["status"] == "fail"]
    assert len(failures) == 1
    assert failures[0]["rule_id"] == "env.llm_critical_deps_pinned"
    assert failures[0]["severity"] == "WARNING"
    assert failures[0]["evidence"][0]["path"] == "requirements.txt"
    assert report["summary"] == {
        "critical": 0,
        "warning": 1,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 1,
    }


def test_audit_gap_suppression_and_critical_overrides_preserve_execution_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    profile_path = repo / ".reprollm" / "profiles" / "core.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["severity_overrides"] = {
        "env.llm_critical_deps_pinned": "CRITICAL",
        "exec.profile_detection_mismatch": "CRITICAL",
    }
    profile_path.write_text(yaml.safe_dump(profile), encoding="utf-8")
    (repo / ".reprollm" / "config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed bounded dependency scan.\n",
        encoding="utf-8",
    )
    commit_all(repo)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    report = _coverage_cli_json(result.stdout)
    by_id = {finding["rule_id"]: finding for finding in report["findings"]}
    ignored = by_id["env.llm_critical_deps_pinned"]
    assert ignored["status"] == "suppressed"
    assert ignored["severity"] == "INFO"
    assert ignored["severity_origin"] == "default"
    assert ignored["suppressed_reason"] == "Reviewed bounded dependency scan."
    assert ignored["evidence"] == [
        {
            "kind": "field",
            "path": ".reprollm/config.yaml",
            "field": "audit.ignore",
            "line": None,
            "value": None,
            "expected": None,
            "note": (
                "suppressed: original severity INFO; reason: Reviewed bounded dependency scan."
            ),
        }
    ]
    skipped = by_id["exec.profile_detection_mismatch"]
    assert skipped["status"] == "skipped"
    assert skipped["severity"] == "INFO"
    assert skipped["severity_origin"] == "default"
    assert skipped["evidence"] == []
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 1,
        "skipped": 1,
    }


def test_audit_gap_text_hides_details_until_show_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    args = ["audit", str(repo), "--no-color"]

    default = runner.invoke(app, args)
    shown = runner.invoke(app, [*args, "--show-skipped"])

    assert default.exit_code == shown.exit_code == 0
    assert default.stderr == shown.stderr
    assert default.stderr.count("scan: Python analysis incomplete:") == 1
    assert "4 passed · 0 suppressed · 2 skipped" in default.stdout
    assert "4 passed · 0 suppressed · 2 skipped" in shown.stdout
    assert "Findings: PASS" in default.stdout
    assert "Findings: PASS" in shown.stdout
    for rule_id in ["env.llm_critical_deps_pinned", "exec.profile_detection_mismatch"]:
        assert rule_id not in default.stdout
        assert (
            f"{rule_id}      skipped: Python candidate analysis incomplete: "
            "parsed 1 of 2 candidate files; selected 1 (limit 1); "
            "no rule-wide PASS is established."
        ) in shown.stdout
    assert "Python candidate analysis incomplete:" not in default.stdout
    assert "scan: " not in shown.stdout


def test_audit_parse_only_gap_skips_without_count_limit_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _coverage_cli_repo(tmp_path)
    (repo / "z.py").write_text("def f(:\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = _coverage_cli_json(result.stdout)
    gaps = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert [finding["rule_id"] for finding in gaps] == [
        "env.llm_critical_deps_pinned",
        "exec.profile_detection_mismatch",
    ]
    assert all(
        finding["message"]
        == (
            "Python candidate analysis incomplete: parsed 1 of 2 candidate files; "
            "selected 2 (limit 2); no rule-wide PASS is established."
        )
        for finding in gaps
    )
    verbose = runner.invoke(
        app, ["-v", "audit", str(repo), "--format", "json", "--fail-on", "warning"]
    )
    assert verbose.exit_code == 0, verbose.output
    assert verbose.stderr == "scan: z.py:1: syntax error; skipped\n"
    verbose_report = _coverage_cli_json(verbose.stdout)
    report.pop("generated_at")
    verbose_report.pop("generated_at")
    assert verbose_report == report


def _invoke_audit_json(monkeypatch, repo: Path) -> object:
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", ".", "--format", "json"])
    assert result.exit_code in (0, 1), result.output
    return json.loads(result.output)


def test_audit_l0_json_snapshots(monkeypatch, tmp_path: Path) -> None:
    for name in L0_SNAPSHOT_FIXTURES:
        repo = materialize_repo(name, tmp_path)
        report = _invoke_audit_json(monkeypatch, repo)
        assert_json_snapshot(report, FIXTURES_ROOT / name / "expected" / "audit_L0.json")


def test_audit_json_validates_against_exported_schema(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    report = _invoke_audit_json(monkeypatch, repo)
    schema_path = Path(__file__).resolve().parents[3] / "schemas" / "audit_report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)


def test_audit_exit_codes(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.chdir(repo)
    assert runner.invoke(app, ["audit", "."]).exit_code == 0

    broken = materialize_repo("not_a_git_repo", tmp_path / "broken")
    monkeypatch.chdir(broken)
    assert runner.invoke(app, ["audit", "."]).exit_code == 1
    assert runner.invoke(app, ["audit", ".", "--fail-on", "never"]).exit_code == 0


def test_audit_unborn_repository_fails_git_commit(monkeypatch, tmp_path: Path) -> None:
    repo = make_git_repo(tmp_path / "unborn")
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", ".", "--format", "json"])
    assert result.exit_code == 1
    report = json.loads(result.output)
    by_id = {f["rule_id"]: f for f in report["findings"]}
    assert by_id["code.git_repo"]["status"] == "pass"
    assert by_id["code.git_commit"]["status"] == "fail"
    assert by_id["code.git_commit"]["severity"] == "CRITICAL"


def test_audit_output_writes_file(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    monkeypatch.chdir(repo)
    out = tmp_path / "report.json"
    result = runner.invoke(app, ["audit", ".", "--format", "json", "--output", str(out)])
    assert result.exit_code == 0
    document = json.loads(out.read_text(encoding="utf-8"))
    assert document["level"] == 0
    assert "Wrote audit report" in result.output


#: All six fixtures have --no-color text snapshots.
TEXT_SNAPSHOT_FIXTURES = L0_SNAPSHOT_FIXTURES


def test_audit_text_snapshot_no_color(monkeypatch, tmp_path: Path) -> None:
    for name in TEXT_SNAPSHOT_FIXTURES:
        repo = materialize_repo(name, tmp_path / name)
        monkeypatch.chdir(repo)
        result = runner.invoke(app, ["audit", ".", "--no-color", "--show-skipped"])
        assert result.exit_code in (0, 1), result.output
        text = result.output
        assert text.startswith("ReproLLM audit · level 0 · profiles: core")
        expected_path = FIXTURES_ROOT / name / "expected" / "audit_L0.txt"
        import os

        if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            expected_path.write_text(text, encoding="utf-8")
        else:
            assert expected_path.exists()
            assert text == expected_path.read_text(encoding="utf-8")


def test_audit_text_fail_result_line(monkeypatch, tmp_path: Path) -> None:
    repo = materialize_repo("not_a_git_repo", tmp_path)
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["audit", ".", "--no-color"])
    assert "Findings: FAIL (1 critical, 1 warning)" in result.output
    assert "Result: exit 1 (--fail-on critical; findings reach the threshold)" in result.output


_PROFILE_ABSENCE_MESSAGE = (
    "declared profile 'inference' has no detection evidence in the analysed inputs; "
    "Python candidate analysis is incomplete or unavailable, so absence is not established"
)


def _declared_profile_absence_repo(tmp_path: Path, severity: str = "CRITICAL") -> Path:
    repo = _coverage_cli_repo(tmp_path)
    core_path = repo / ".reprollm" / "profiles" / "core.yaml"
    core = yaml.safe_load(core_path.read_text(encoding="utf-8"))
    core["severity_overrides"] = {"exec.profile_detection_mismatch": severity}
    core_path.write_text(yaml.safe_dump(core), encoding="utf-8")
    (core_path.parent / "inference.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "inference",
                "description": "Isolate declared-profile absence without other required rules.",
                "rules": [],
                "detect": {"imports": ["vllm"]},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: coverage}\nexperiment: {profiles: [inference]}\n",
        encoding="utf-8",
    )
    (repo / "z.py").write_text("value = 2\n", encoding="utf-8")
    commit_all(repo)
    return repo


@pytest.mark.parametrize("severity", ["WARNING", "CRITICAL"])
@pytest.mark.parametrize("fail_on", ["warning", "critical", "never"])
def test_audit_unverified_profile_absence_cannot_trigger_an_overridden_failure_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, severity: str, fail_on: str
) -> None:
    repo = _declared_profile_absence_repo(tmp_path, severity)
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", fail_on]
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)

    gap = runner.invoke(app, args)
    repeated = runner.invoke(app, args)

    assert gap.exit_code == repeated.exit_code == 0, gap.output
    assert (
        gap.stderr
        == repeated.stderr
        == (
            "scan: Python analysis incomplete: parsed 1 of 2 candidate files; "
            "selected 1 (limit 1), omitted 1. Missing signals may be in unanalysed files.\n"
        )
    )
    report = _coverage_cli_json(gap.stdout)
    second = _coverage_cli_json(repeated.stdout)
    report.pop("generated_at")
    second.pop("generated_at")
    assert report == second
    (finding,) = [
        f for f in report["findings"] if f["rule_id"] == "exec.profile_detection_mismatch"
    ]
    assert finding["message"] == _PROFILE_ABSENCE_MESSAGE
    assert (finding["status"], finding["severity"], finding["severity_origin"]) == (
        "skipped",
        "INFO",
        "default",
    )
    assert finding["evidence"] == [
        {
            "kind": "field",
            "path": None,
            "field": "experiment.profiles",
            "line": None,
            "value": None,
            "expected": None,
            "note": "inference declared; detection absence unverified",
        }
    ]
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)

    complete = runner.invoke(app, args)

    expected_exit = int(fail_on == "warning" or (fail_on == "critical" and severity == "CRITICAL"))
    assert complete.exit_code == expected_exit, complete.output
    assert complete.stderr == ""
    complete_report = _coverage_cli_json(complete.stdout)
    (failure,) = [f for f in complete_report["findings"] if f["status"] == "fail"]
    assert failure["rule_id"] == "exec.profile_detection_mismatch"
    assert failure["severity"] == severity
    assert failure["severity_origin"] == "profile:core"
    assert (
        failure["message"]
        == "declared profile 'inference' has no detection evidence in this repository"
    )
    assert failure["evidence"][0]["note"] == "inference declared, nothing detected"
    assert complete_report["summary"] == {
        "critical": int(severity == "CRITICAL"),
        "warning": int(severity == "WARNING"),
        "info": 0,
        "pass": 5,
        "suppressed": 0,
        "skipped": 0,
    }
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    } == before


def test_audit_profile_absence_skip_does_not_hide_a_positive_critical_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _declared_profile_absence_repo(tmp_path)
    (repo / "a.py").write_text("import peft\n", encoding="utf-8")
    (repo / "z.py").write_text("import vllm\n", encoding="utf-8")
    (repo / "requirements.txt").write_text("torch==2.5.1\npeft==0.1\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "critical"])

    assert result.exit_code == 1, result.output
    assert result.stderr.count("scan: Python analysis incomplete:") == 1
    report = _coverage_cli_json(result.stdout)
    findings = [f for f in report["findings"] if f["rule_id"] == "exec.profile_detection_mismatch"]
    assert len(findings) == 2
    failure, skipped = findings
    assert (failure["status"], failure["severity"], failure["severity_origin"]) == (
        "fail",
        "CRITICAL",
        "profile:core",
    )
    assert failure["message"] == (
        "detected profile 'finetuning' (high confidence) is not declared in experiment.profiles"
    )
    assert failure["evidence"][0]["path"] == "a.py"
    assert failure["evidence"][0]["line"] == 1
    assert failure["evidence"][0]["note"] == "import peft"
    assert (skipped["status"], skipped["severity"], skipped["severity_origin"]) == (
        "skipped",
        "INFO",
        "default",
    )
    assert skipped["message"] == _PROFILE_ABSENCE_MESSAGE
    assert skipped["evidence"][0]["note"] == "inference declared; detection absence unverified"
    assert report["summary"] == {
        "critical": 1,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 0,
        "skipped": 2,
    }


def test_audit_profile_absence_skip_obeys_existing_text_and_suppression_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _declared_profile_absence_repo(tmp_path)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    args = ["audit", str(repo), "--no-color", "--fail-on", "warning"]

    hidden = runner.invoke(app, args)
    shown = runner.invoke(app, [*args, "--show-skipped"])

    assert hidden.exit_code == shown.exit_code == 0
    assert hidden.stderr == shown.stderr
    assert hidden.stderr.count("scan: Python analysis incomplete:") == 1
    assert "exec.profile_detection_mismatch" not in hidden.stdout
    assert (
        f"exec.profile_detection_mismatch      skipped: {_PROFILE_ABSENCE_MESSAGE}" in shown.stdout
    )
    assert "4 passed · 0 suppressed · 2 skipped" in hidden.stdout
    output = tmp_path / "declared-export.md"

    exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])

    assert exported.exit_code == 0, exported.output
    assert exported.stderr == hidden.stderr
    assert exported.stderr.count("scan: Python analysis incomplete:") == 1
    assert "0 critical · 0 warning ·\n0 info · 4 passed." in output.read_text(encoding="utf-8")
    (repo / ".reprollm" / "config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: exec.profile_detection_mismatch\n"
        "      reason: Reviewed incomplete profile evidence.\n",
        encoding="utf-8",
    )
    commit_all(repo)

    ignored = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "critical"])

    assert ignored.exit_code == 0, ignored.output
    report = _coverage_cli_json(ignored.stdout)
    (finding,) = [
        f for f in report["findings"] if f["rule_id"] == "exec.profile_detection_mismatch"
    ]
    assert finding["status"] == "suppressed"
    assert finding["severity"] == "INFO"
    assert finding["severity_origin"] == "default"
    assert finding["message"] == _PROFILE_ABSENCE_MESSAGE
    assert finding["suppressed_reason"] == "Reviewed incomplete profile evidence."
    assert finding["evidence"][0]["note"] == "inference declared; detection absence unverified"
    assert finding["evidence"][1]["field"] == "audit.ignore"
    assert finding["evidence"][1]["note"] == (
        "suppressed: original severity INFO; reason: Reviewed incomplete profile evidence."
    )
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 4,
        "suppressed": 1,
        "skipped": 1,
    }


_DEPENDENCY_FORMAT_CREDIT_MESSAGE = (
    "torch is used; Python analysis is incomplete or unavailable and a captured format "
    "lock lists the package, so missing pin evidence is not established"
)
_DEPENDENCY_FORMAT_CREDIT_DIAGNOSTIC = (
    "scan: Python analysis incomplete: parsed 1 of 2 candidate files; "
    "selected 1 (limit 1), omitted 1. Missing signals may be in unanalysed files.\n"
)


def _dependency_format_credit_repo(tmp_path: Path, severity: str = "CRITICAL") -> Path:
    repo = make_git_repo(tmp_path / "format-credit")
    profiles = repo / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated dependency format-lock credit controls.",
                "rules": ["env.llm_critical_deps_pinned"],
                "severity_overrides": {"env.llm_critical_deps_pinned": severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: format-credit}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "requirements.txt").write_text("torch>=2\n", encoding="utf-8")
    (repo / "a.py").write_text("value = 1\n", encoding="utf-8")
    nested = repo / "nested"
    nested.mkdir()
    (nested / "z.py").write_text("import torch\n", encoding="utf-8")
    # An unpaired lock makes the complete-view WARNING an independent control.
    (nested / "uv.lock").write_text(
        '[[package]]\nname = "torch"\nversion = "2.5.1"\n', encoding="utf-8"
    )
    commit_all(repo)
    return repo


@pytest.mark.parametrize(
    ("severity", "threshold", "mixed", "complete_exit"),
    [
        ("WARNING", "never", False, 0),
        ("WARNING", "critical", False, 0),
        ("WARNING", "warning", False, 1),
        ("CRITICAL", "never", False, 0),
        ("CRITICAL", "critical", False, 1),
        ("CRITICAL", "warning", False, 1),
        ("CRITICAL", "critical", True, 1),
    ],
    ids=[
        "warning-never",
        "warning-critical",
        "warning-warning",
        "critical-never",
        "critical-critical",
        "critical-warning",
        "mixed-critical",
    ],
)
def test_dependency_possible_credit_skip_preserves_failure_threshold_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    severity: str,
    threshold: str,
    mixed: bool,
    complete_exit: int,
) -> None:
    repo = _dependency_format_credit_repo(tmp_path, severity)
    if mixed:
        (repo / "requirements.txt").write_text("torch>=2\nnumpy>=1\n", encoding="utf-8")
        commit_all(repo)
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]

    result = runner.invoke(app, args)

    assert result.exit_code == int(mixed), result.output
    assert result.stderr == _DEPENDENCY_FORMAT_CREDIT_DIAGNOSTIC
    report = _coverage_cli_json(result.stdout)
    skipped = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert len(skipped) == 1
    finding = skipped[0]
    assert (finding["rule_id"], finding["severity"], finding["severity_origin"]) == (
        "env.llm_critical_deps_pinned",
        "INFO",
        "default",
    )
    assert finding["message"] == _DEPENDENCY_FORMAT_CREDIT_MESSAGE
    assert finding["evidence"] == [
        {
            "kind": "file",
            "path": "requirements.txt",
            "field": None,
            "line": 1,
            "value": ">=2",
            "expected": None,
            "note": "declared as >=2",
        },
        {
            "kind": "file",
            "path": "nested/uv.lock",
            "field": None,
            "line": None,
            "value": None,
            "expected": None,
            "note": "torch listed; import-origin credit unverified",
        },
    ]
    assert report["summary"] == {
        "critical": int(mixed),
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }
    if mixed:
        failure, skip = report["findings"]
        assert failure["message"].startswith("numpy is used but not pinned")
        assert (failure["status"], failure["severity"], failure["severity_origin"]) == (
            "fail",
            "CRITICAL",
            "profile:core",
        )
        assert skip == finding
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)

    complete = runner.invoke(app, args)

    assert complete.exit_code == complete_exit, complete.output
    assert complete.stderr == ""
    complete_report = _coverage_cli_json(complete.stdout)
    assert len(complete_report["findings"]) == 1 + int(mixed)
    assert all(
        finding["status"] == "fail"
        and finding["severity"] == severity
        and finding["severity_origin"] == "profile:core"
        for finding in complete_report["findings"]
    )
    assert complete_report["summary"] == {
        "critical": (1 + int(mixed)) * int(severity == "CRITICAL"),
        "warning": (1 + int(mixed)) * int(severity == "WARNING"),
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 0,
    }
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    } == before


def test_dependency_credit_skip_obeys_json_text_export_and_suppression_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _dependency_format_credit_repo(tmp_path)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 1)
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", "warning"]

    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == second.exit_code == 0
    assert first.stderr == second.stderr == _DEPENDENCY_FORMAT_CREDIT_DIAGNOSTIC
    first_json, second_json = _coverage_cli_json(first.stdout), _coverage_cli_json(second.stdout)
    assert len(first_json["findings"]) == len(second_json["findings"]) == 1
    assert first_json["findings"][0]["message"] == _DEPENDENCY_FORMAT_CREDIT_MESSAGE
    first_json.pop("generated_at")
    second_json.pop("generated_at")
    assert first_json == second_json
    text_args = ["audit", str(repo), "--no-color", "--fail-on", "warning"]

    hidden = runner.invoke(app, text_args)
    shown = runner.invoke(app, [*text_args, "--show-skipped"])

    assert hidden.exit_code == shown.exit_code == 0
    assert hidden.stderr == shown.stderr == _DEPENDENCY_FORMAT_CREDIT_DIAGNOSTIC
    assert _DEPENDENCY_FORMAT_CREDIT_MESSAGE not in hidden.stdout
    assert _DEPENDENCY_FORMAT_CREDIT_MESSAGE in shown.stdout
    assert "0 passed · 0 suppressed · 1 skipped" in hidden.stdout
    output = tmp_path / "dependency-credit-export.md"

    exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])

    assert exported.exit_code == 0, exported.output
    assert exported.stderr == _DEPENDENCY_FORMAT_CREDIT_DIAGNOSTIC
    document = output.read_text(encoding="utf-8")
    assert "0 critical · 0 warning ·\n0 info · 0 passed." in document
    assert "env.llm_critical_deps_pinned" not in document
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    } == before
    (repo / ".reprollm" / "config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed incomplete import-origin evidence.\n",
        encoding="utf-8",
    )
    commit_all(repo)

    ignored = runner.invoke(app, args)

    assert ignored.exit_code == 0, ignored.output
    assert ignored.stderr == _DEPENDENCY_FORMAT_CREDIT_DIAGNOSTIC
    report = _coverage_cli_json(ignored.stdout)
    (finding,) = report["findings"]
    assert (finding["status"], finding["severity"], finding["severity_origin"]) == (
        "suppressed",
        "INFO",
        "default",
    )
    assert finding["message"] == _DEPENDENCY_FORMAT_CREDIT_MESSAGE
    assert finding["suppressed_reason"] == "Reviewed incomplete import-origin evidence."
    assert len(finding["evidence"]) == 3
    assert finding["evidence"][1]["path"] == "nested/uv.lock"
    assert finding["evidence"][2]["field"] == "audit.ignore"
    assert finding["evidence"][2]["note"] == (
        "suppressed: original severity INFO; reason: Reviewed incomplete import-origin evidence."
    )
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 1,
        "skipped": 0,
    }


def test_dependency_credit_selected_parse_failure_below_file_limit_has_no_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.core.context import AuditContext

    repo = _dependency_format_credit_repo(tmp_path)
    (repo / "a.py").write_text("def broken(:\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr(scanner_mod, "MAX_PYTHON_FILES", 2)
    scan = AuditContext(repo).pyscan
    assert (
        scan.python_candidate_count,
        scan.python_selected_count,
        scan.python_parsed_count,
        scan.python_file_limit,
    ) == (2, 2, 1, 2)

    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "warning"])

    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = _coverage_cli_json(result.stdout)
    assert report["findings"] == [
        {
            "rule_id": "env.llm_critical_deps_pinned",
            "aliases": [],
            "category": "env",
            "severity": "INFO",
            "status": "skipped",
            "level": 1,
            "message": _DEPENDENCY_FORMAT_CREDIT_MESSAGE,
            "evidence": [
                {
                    "kind": "file",
                    "path": "requirements.txt",
                    "field": None,
                    "line": 1,
                    "value": ">=2",
                    "expected": None,
                    "note": "declared as >=2",
                },
                {
                    "kind": "file",
                    "path": "nested/uv.lock",
                    "field": None,
                    "line": None,
                    "value": None,
                    "expected": None,
                    "note": "torch listed; import-origin credit unverified",
                },
            ],
            "fix_hint": (
                "Review torch declarations and format-lock origins; complete Python analysis "
                "before deciding that exact pin evidence is absent."
            ),
            "profile_origin": [],
            "severity_origin": "default",
            "suppressed_reason": None,
        }
    ]
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }


_ASSOCIATED_LOCK_CONTENT_MESSAGE = (
    "torch is used; an associated format lock could not be read or parsed, "
    "so missing pin evidence is not established"
)


def _associated_failed_lock_repo(tmp_path: Path, severity: str = "CRITICAL") -> Path:
    repo = make_git_repo(tmp_path / "failed-lock")
    profiles = repo / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated associated lock contents regression.",
                "rules": ["env.llm_critical_deps_pinned"],
                "severity_overrides": {"env.llm_critical_deps_pinned": severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: failed-lock}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "failed-lock"\ndependencies = ["torch>=2"]\n', encoding="utf-8"
    )
    (repo / "uv.lock").write_text("[broken\n", encoding="utf-8")
    commit_all(repo)
    return repo


@pytest.mark.parametrize(
    ("severity", "threshold", "mixed", "readable_empty_exit"),
    [
        ("WARNING", "never", False, 0),
        ("WARNING", "critical", False, 0),
        ("WARNING", "warning", False, 1),
        ("CRITICAL", "never", False, 0),
        ("CRITICAL", "critical", False, 1),
        ("CRITICAL", "warning", False, 1),
        ("CRITICAL", "critical", True, 1),
    ],
    ids=[
        "warning-never",
        "warning-critical",
        "warning-warning",
        "critical-never",
        "critical-critical",
        "critical-warning",
        "mixed-critical",
    ],
)
def test_failed_associated_lock_skip_preserves_cli_failure_thresholds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    severity: str,
    threshold: str,
    mixed: bool,
    readable_empty_exit: int,
) -> None:
    repo = _associated_failed_lock_repo(tmp_path, severity)
    if mixed:
        (repo / "requirements.txt").write_text("numpy>=1\n", encoding="utf-8")
        commit_all(repo)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]

    result = runner.invoke(app, args)

    assert result.exit_code == int(mixed), result.output
    assert result.stderr == ""
    report = _coverage_cli_json(result.stdout)
    skipped = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert len(skipped) == 1
    assert skipped[0] == {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 1,
        "message": _ASSOCIATED_LOCK_CONTENT_MESSAGE,
        "evidence": [
            {
                "kind": "file",
                "path": "pyproject.toml",
                "field": None,
                "line": 3,
                "value": ">=2",
                "expected": None,
                "note": "declared as >=2",
            },
            {
                "kind": "file",
                "path": "uv.lock",
                "field": None,
                "line": None,
                "value": None,
                "expected": None,
                "note": "torch associated; lock package contents unverified",
            },
        ],
        "fix_hint": (
            "Review torch declarations and associated format-lock files; restore readable, "
            "valid lock contents before deciding that exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    assert report["summary"] == {
        "critical": int(mixed),
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }
    if mixed:
        (warning,) = [finding for finding in report["findings"] if finding["status"] == "fail"]
        assert warning["message"] == (
            "numpy is used but not pinned to an exact version (suggestion: numpy==<version>)"
        )
        assert (warning["severity"], warning["severity_origin"]) == ("CRITICAL", "profile:core")
    (repo / "uv.lock").write_text("", encoding="utf-8")
    commit_all(repo)

    readable_empty = runner.invoke(app, args)

    assert readable_empty.exit_code == readable_empty_exit, readable_empty.output
    assert readable_empty.stderr == ""
    empty_report = _coverage_cli_json(readable_empty.stdout)
    assert len(empty_report["findings"]) == 1 + int(mixed)
    assert all(
        finding["status"] == "fail"
        and finding["severity"] == severity
        and finding["severity_origin"] == "profile:core"
        for finding in empty_report["findings"]
    )
    assert empty_report["summary"] == {
        "critical": (1 + int(mixed)) * int(severity == "CRITICAL"),
        "warning": (1 + int(mixed)) * int(severity == "WARNING"),
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 0,
    }


def test_failed_associated_lock_skip_preserves_json_text_export_and_suppression(
    tmp_path: Path,
) -> None:
    repo = _associated_failed_lock_repo(tmp_path)
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", "critical"]

    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == second.exit_code == 0
    assert first.stderr == second.stderr == ""
    first_report = _coverage_cli_json(first.stdout)
    second_report = _coverage_cli_json(second.stdout)
    first_report.pop("generated_at")
    second_report.pop("generated_at")
    assert first_report == second_report
    assert first_report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }
    text_args = ["audit", str(repo), "--no-color", "--fail-on", "critical"]

    hidden = runner.invoke(app, text_args)
    shown = runner.invoke(app, [*text_args, "--show-skipped"])

    assert hidden.exit_code == shown.exit_code == 0
    assert hidden.stderr == shown.stderr == ""
    assert _ASSOCIATED_LOCK_CONTENT_MESSAGE not in hidden.stdout
    assert _ASSOCIATED_LOCK_CONTENT_MESSAGE in shown.stdout
    assert "Findings: PASS" in hidden.stdout
    assert "0 passed · 0 suppressed · 1 skipped" in hidden.stdout
    output = tmp_path / "failed-lock-export.md"

    exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])

    assert exported.exit_code == 0, exported.output
    assert exported.stderr == ""
    document = output.read_text(encoding="utf-8")
    assert "0 critical · 0 warning ·\n0 info · 0 passed." in document
    assert "env.llm_critical_deps_pinned" not in document
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    } == before
    (repo / ".reprollm" / "config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed associated lock read uncertainty.\n",
        encoding="utf-8",
    )
    commit_all(repo)

    ignored = runner.invoke(app, args)

    assert ignored.exit_code == 0, ignored.output
    assert ignored.stderr == ""
    report = _coverage_cli_json(ignored.stdout)
    (finding,) = report["findings"]
    assert (finding["status"], finding["severity"], finding["severity_origin"]) == (
        "suppressed",
        "INFO",
        "default",
    )
    assert finding["message"] == _ASSOCIATED_LOCK_CONTENT_MESSAGE
    assert finding["suppressed_reason"] == "Reviewed associated lock read uncertainty."
    assert len(finding["evidence"]) == 3
    assert finding["evidence"][1]["path"] == "uv.lock"
    assert finding["evidence"][2]["field"] == "audit.ignore"
    assert finding["evidence"][2]["note"] == (
        "suppressed: original severity INFO; reason: Reviewed associated lock read uncertainty."
    )
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 1,
        "skipped": 0,
    }


# --- R07-C D-S: public CLI retains D-F visibility and threshold contracts ---


@pytest.mark.parametrize(
    ("severity", "threshold", "mixed", "restored_exit"),
    [
        ("WARNING", "never", False, 0),
        ("WARNING", "critical", False, 0),
        ("WARNING", "warning", False, 1),
        ("CRITICAL", "never", False, 0),
        ("CRITICAL", "critical", False, 1),
        ("CRITICAL", "warning", False, 1),
        ("CRITICAL", "critical", True, 1),
    ],
)
def test_structural_lock_skip_keeps_cli_override_thresholds_and_other_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    severity: str,
    threshold: str,
    mixed: bool,
    restored_exit: int,
) -> None:
    repo = _associated_failed_lock_repo(tmp_path, severity)
    (repo / "uv.lock").write_text("package = [{}]\n", encoding="utf-8")
    if mixed:
        (repo / "requirements.txt").write_text("numpy>=1\n", encoding="utf-8")
    commit_all(repo)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]

    result = runner.invoke(app, args)

    assert result.exit_code == int(mixed), result.output
    assert result.stderr == ""
    report = _coverage_cli_json(result.stdout)
    (skipped,) = [finding for finding in report["findings"] if finding["status"] == "skipped"]
    assert skipped == {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 1,
        "message": _ASSOCIATED_LOCK_CONTENT_MESSAGE,
        "evidence": [
            {
                "kind": "file",
                "path": "pyproject.toml",
                "field": None,
                "line": 3,
                "value": ">=2",
                "expected": None,
                "note": "declared as >=2",
            },
            {
                "kind": "file",
                "path": "uv.lock",
                "field": None,
                "line": None,
                "value": None,
                "expected": None,
                "note": "torch associated; lock package contents unverified",
            },
        ],
        "fix_hint": (
            "Review torch declarations and associated format-lock files; restore readable, "
            "valid lock contents before deciding that exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }
    assert report["summary"] == {
        "critical": int(mixed),
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }
    if mixed:
        (warning,) = [finding for finding in report["findings"] if finding["status"] == "fail"]
        assert warning["message"] == (
            "numpy is used but not pinned to an exact version (suggestion: numpy==<version>)"
        )
        assert (warning["severity"], warning["severity_origin"]) == ("CRITICAL", "profile:core")
    (repo / "uv.lock").write_text("package = []\n", encoding="utf-8")
    commit_all(repo)

    restored = runner.invoke(app, args)

    assert restored.exit_code == restored_exit, restored.output
    assert restored.stderr == ""
    restored_report = _coverage_cli_json(restored.stdout)
    assert len(restored_report["findings"]) == 1 + int(mixed)
    assert all(
        finding["status"] == "fail"
        and finding["severity"] == severity
        and finding["severity_origin"] == "profile:core"
        for finding in restored_report["findings"]
    )
    assert restored_report["summary"] == {
        "critical": (1 + int(mixed)) * int(severity == "CRITICAL"),
        "warning": (1 + int(mixed)) * int(severity == "WARNING"),
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 0,
    }


def test_structural_lock_skip_keeps_json_text_export_and_suppression_contracts(
    tmp_path: Path,
) -> None:
    repo = _associated_failed_lock_repo(tmp_path)
    (repo / "uv.lock").write_text("package = [{}]\n", encoding="utf-8")
    commit_all(repo)
    before = {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", "critical"]

    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == second.exit_code == 0
    assert first.stderr == second.stderr == ""
    first_report = _coverage_cli_json(first.stdout)
    second_report = _coverage_cli_json(second.stdout)
    first_report.pop("generated_at")
    second_report.pop("generated_at")
    assert first_report == second_report
    (skipped,) = first_report["findings"]
    assert skipped["message"] == _ASSOCIATED_LOCK_CONTENT_MESSAGE
    assert (skipped["status"], skipped["severity"]) == ("skipped", "INFO")
    assert first_report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }
    text_args = ["audit", str(repo), "--no-color", "--fail-on", "critical"]

    hidden = runner.invoke(app, text_args)
    shown = runner.invoke(app, [*text_args, "--show-skipped"])

    assert hidden.exit_code == shown.exit_code == 0
    assert hidden.stderr == shown.stderr == ""
    assert _ASSOCIATED_LOCK_CONTENT_MESSAGE not in hidden.stdout
    assert _ASSOCIATED_LOCK_CONTENT_MESSAGE in shown.stdout
    assert "Findings: PASS" in hidden.stdout
    assert "0 passed · 0 suppressed · 1 skipped" in hidden.stdout
    output = tmp_path / "structural-lock-export.md"

    exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])

    assert exported.exit_code == 0, exported.output
    assert exported.stderr == ""
    document = output.read_text(encoding="utf-8")
    assert "0 critical · 0 warning ·\n0 info · 0 passed." in document
    assert "env.llm_critical_deps_pinned" not in document
    assert {
        path.relative_to(repo): path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(repo).parts
    } == before
    (repo / ".reprollm" / "config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed associated lock structure uncertainty.\n",
        encoding="utf-8",
    )
    commit_all(repo)

    ignored = runner.invoke(app, args)

    assert ignored.exit_code == 0, ignored.output
    assert ignored.stderr == ""
    ignored_report = _coverage_cli_json(ignored.stdout)
    (finding,) = ignored_report["findings"]
    assert (finding["status"], finding["severity"], finding["severity_origin"]) == (
        "suppressed",
        "INFO",
        "default",
    )
    assert finding["message"] == _ASSOCIATED_LOCK_CONTENT_MESSAGE
    assert finding["suppressed_reason"] == "Reviewed associated lock structure uncertainty."
    assert len(finding["evidence"]) == 3
    assert finding["evidence"][1]["path"] == "uv.lock"
    assert finding["evidence"][2]["field"] == "audit.ignore"
    assert finding["evidence"][2]["note"] == (
        "suppressed: original severity INFO; reason: "
        "Reviewed associated lock structure uncertainty."
    )
    assert ignored_report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 1,
        "skipped": 0,
    }


# --- R07-C D-M: declaration-body uncertainty reaches audit and export -------


_DECLARATION_BODY_CLI_MESSAGE = (
    "torch is used; a dependency declaration body could not be read or parsed, "
    "so missing pin evidence is not established"
)


def _declaration_body_cli_repo(
    tmp_path: Path, severity: str = "CRITICAL", mixed: bool = False, body: str = "[broken\n"
) -> Path:
    repo = make_git_repo(tmp_path / "declaration-body")
    profiles = repo / ".reprollm" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "core.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "name": "core",
                "description": "Isolated captured declaration-body uncertainty.",
                "rules": ["env.llm_critical_deps_pinned"]
                + (["env.python_version_declared"] if mixed else []),
                "severity_overrides": {"env.llm_critical_deps_pinned": severity},
            }
        ),
        encoding="utf-8",
    )
    (repo / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: declaration-body}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    (repo / "requirements.txt").write_text("torch>=2\n", encoding="utf-8")
    (repo / "unrelated").mkdir()
    (repo / "unrelated/pyproject.toml").write_text(body, encoding="utf-8")
    commit_all(repo)
    return repo


def _expected_declaration_body_cli_skip() -> dict[str, Any]:
    return {
        "rule_id": "env.llm_critical_deps_pinned",
        "aliases": [],
        "category": "env",
        "severity": "INFO",
        "status": "skipped",
        "level": 1,
        "message": _DECLARATION_BODY_CLI_MESSAGE,
        "evidence": [
            {
                "kind": "file",
                "path": "requirements.txt",
                "field": None,
                "line": 1,
                "value": ">=2",
                "expected": None,
                "note": "declared as >=2",
            },
            {
                "kind": "file",
                "path": "unrelated/pyproject.toml",
                "field": None,
                "line": None,
                "value": None,
                "expected": None,
                "note": "torch possible exact declaration unverified",
            },
        ],
        "fix_hint": (
            "Review torch declarations and failed dependency source files; restore readable, "
            "valid declaration bodies before deciding that exact pin evidence is absent."
        ),
        "profile_origin": [],
        "severity_origin": "default",
        "suppressed_reason": None,
    }


@pytest.mark.parametrize(
    "body",
    [
        "[broken\n",
        "project=42\n",
        "tool=false\n",
        '[project]\noptional-dependencies={bad=false, good=["requests==2.1"]}\n',
    ],
    ids=["body-syntax", "structure-project", "structure-tool", "structure-partial-group"],
)
@pytest.mark.parametrize(
    ("severity", "threshold", "mixed", "restored_exit"),
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
def test_declaration_body_skip_keeps_overrides_thresholds_and_independent_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    severity: str,
    threshold: str,
    mixed: bool,
    restored_exit: int,
    body: str,
) -> None:
    repo = _declaration_body_cli_repo(tmp_path, severity, mixed, body)
    monkeypatch.setattr("reprollm.rules.env.installed_versions", lambda: {})
    args = ["audit", str(repo), "--format", "json", "--fail-on", threshold]

    failed_body = runner.invoke(app, args)

    assert failed_body.exit_code == int(mixed), failed_body.output
    assert failed_body.stderr == ""
    report = _coverage_cli_json(failed_body.stdout)
    (skipped,) = [f for f in report["findings"] if f["rule_id"] == "env.llm_critical_deps_pinned"]
    assert skipped == _expected_declaration_body_cli_skip()
    assert report["summary"] == {
        "critical": 0,
        "warning": int(mixed),
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 1,
    }
    if mixed:
        (warning,) = [f for f in report["findings"] if f["status"] == "fail"]
        assert warning["rule_id"] == "env.python_version_declared"
        assert warning["severity"] == "WARNING"
        assert warning["message"] == "no Python version requirement is declared"
    (repo / "unrelated/pyproject.toml").write_text("[project]\n", encoding="utf-8")
    commit_all(repo)

    restored = runner.invoke(app, args)

    assert restored.exit_code == restored_exit, restored.output
    assert restored.stderr == ""
    restored_report = _coverage_cli_json(restored.stdout)
    (pinned,) = [
        f for f in restored_report["findings"] if f["rule_id"] == "env.llm_critical_deps_pinned"
    ]
    assert (pinned["status"], pinned["severity"], pinned["severity_origin"]) == (
        "fail",
        severity,
        "profile:core",
    )
    assert pinned["message"] == (
        "torch is used but not pinned to an exact version (suggestion: torch==<version>)"
    )
    assert pinned["evidence"] == _expected_declaration_body_cli_skip()["evidence"][:1]
    assert restored_report["summary"] == {
        "critical": int(severity == "CRITICAL"),
        "warning": int(severity == "WARNING") + int(mixed),
        "info": 0,
        "pass": 0,
        "suppressed": 0,
        "skipped": 0,
    }


@pytest.mark.parametrize(
    "body",
    [
        "[broken\n",
        "project=42\n",
        "tool=false\n",
        '[project]\noptional-dependencies={bad=false, good=["requests==2.1"]}\n',
    ],
    ids=["body-syntax", "structure-project", "structure-tool", "structure-partial-group"],
)
def test_declaration_body_skip_preserves_full_json_text_export_and_suppression(
    tmp_path: Path,
    body: str,
) -> None:
    repo = _declaration_body_cli_repo(tmp_path, body=body)
    before = {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    }
    args = ["audit", str(repo), "--format", "json", "--fail-on", "critical"]

    first = runner.invoke(app, args)
    second = runner.invoke(app, args)

    assert first.exit_code == second.exit_code == 0
    assert first.stderr == second.stderr == ""
    a = _coverage_cli_json(first.stdout)
    b = _coverage_cli_json(second.stdout)
    a.pop("generated_at")
    b.pop("generated_at")
    assert a == b
    assert a["findings"] == [_expected_declaration_body_cli_skip()]
    hidden = runner.invoke(app, ["audit", str(repo), "--no-color", "--fail-on", "critical"])
    shown = runner.invoke(
        app, ["audit", str(repo), "--no-color", "--show-skipped", "--fail-on", "critical"]
    )
    assert hidden.exit_code == shown.exit_code == 0
    assert hidden.stderr == shown.stderr == ""
    assert _DECLARATION_BODY_CLI_MESSAGE not in hidden.stdout
    assert _DECLARATION_BODY_CLI_MESSAGE in shown.stdout
    assert "Findings: PASS" in hidden.stdout
    assert "0 passed · 0 suppressed · 1 skipped" in hidden.stdout
    output = tmp_path / "declaration-body-export.md"

    exported = runner.invoke(app, ["export", str(repo), "--output", str(output)])

    assert exported.exit_code == 0, exported.output
    assert exported.stderr == ""
    document = output.read_text(encoding="utf-8")
    assert "0 critical · 0 warning ·\n0 info · 0 passed." in document
    assert "env.llm_critical_deps_pinned" not in document
    assert {
        p.relative_to(repo): p.read_bytes()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts
    } == before
    (repo / ".reprollm/config.yaml").write_text(
        "schema_version: 1\naudit:\n  ignore:\n"
        "    - rule: env.llm_critical_deps_pinned\n"
        "      reason: Reviewed declaration body uncertainty.\n",
        encoding="utf-8",
    )
    commit_all(repo)

    ignored = runner.invoke(app, args)

    assert ignored.exit_code == 0, ignored.output
    assert ignored.stderr == ""
    report = _coverage_cli_json(ignored.stdout)
    (finding,) = report["findings"]
    expected = _expected_declaration_body_cli_skip()
    expected.update(status="suppressed", suppressed_reason="Reviewed declaration body uncertainty.")
    expected["evidence"].append(
        {
            "kind": "field",
            "path": ".reprollm/config.yaml",
            "field": "audit.ignore",
            "line": None,
            "value": None,
            "expected": None,
            "note": (
                "suppressed: original severity INFO; reason: Reviewed declaration body uncertainty."
            ),
        }
    )
    assert finding == expected
    assert report["summary"] == {
        "critical": 0,
        "warning": 0,
        "info": 0,
        "pass": 0,
        "suppressed": 1,
        "skipped": 0,
    }
