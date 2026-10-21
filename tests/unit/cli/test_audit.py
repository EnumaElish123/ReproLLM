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
