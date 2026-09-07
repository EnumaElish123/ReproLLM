"""audit CLI tests: snapshots, exit codes, schema validation (spec §1)."""

import json
from pathlib import Path

import jsonschema
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import assert_json_snapshot, make_git_repo, materialize_repo

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


def test_audit_text_snapshot_no_color(monkeypatch, tmp_path: Path) -> None:
    for name in ("not_a_git_repo", "hf_vllm_eval"):
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
    assert "Result: FAIL (1 critical, 1 warning)" in result.output
