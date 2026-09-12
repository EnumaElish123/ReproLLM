"""M3-T08 complete/gaps Level 1 fixture contracts."""

import json
from pathlib import Path

import jsonschema
import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import FIXTURES_ROOT, assert_json_snapshot, materialize_repo, run_git

runner = CliRunner()
NAMES = ["hf_vllm_eval", "openai_judge_eval", "privacy_custom_params"]
EXPECTED_GAPS_FAILURES = {
    "hf_vllm_eval": {
        "code.remote_recorded",
        "env.llm_critical_deps_pinned",
        "env.lockfile_present",
        "env.python_version_declared",
        "exec.run_recorded",
        "gen.params_declared",
        "gen.stop_declared",
    },
    "openai_judge_eval": {
        "code.remote_recorded",
        "env.llm_critical_deps_pinned",
        "env.lockfile_present",
        "exec.profile_detection_mismatch",
        "exec.run_recorded",
        "judge.params_declared",
    },
    "privacy_custom_params": {
        "code.remote_recorded",
        "env.lockfile_present",
        "env.secret_files_ignored",
        "exec.profile_detection_mismatch",
        "exec.run_recorded",
        "model.trust_remote_code_declared",
        "privacy.mechanism_declared",
    },
}


def audit_json(repo: Path) -> dict[str, object]:
    result = runner.invoke(app, ["audit", str(repo), "--format", "json", "--fail-on", "never"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)


@pytest.mark.parametrize("name", NAMES)
def test_complete_is_clean_and_has_no_actionable_findings(tmp_path: Path, name: str) -> None:
    repo = materialize_repo(name, tmp_path, manifest="complete")
    assert run_git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout == b""
    report = audit_json(repo)
    assert report["level"] == 1
    assert report["summary"]["critical"] == 0
    assert report["summary"]["warning"] == 0
    assert report["summary"]["suppressed"] == 0


@pytest.mark.parametrize("name", NAMES)
def test_gaps_have_the_independently_reviewed_failure_set(tmp_path: Path, name: str) -> None:
    repo = materialize_repo(name, tmp_path, manifest="gaps")
    report = audit_json(repo)
    failures = {f["rule_id"] for f in report["findings"] if f["status"] == "fail"}
    assert failures == EXPECTED_GAPS_FAILURES[name]
    by_id = {f["rule_id"]: f for f in report["findings"]}
    if name == "hf_vllm_eval":
        assert by_id["gen.params_declared"]["severity"] == "CRITICAL"
        assert by_id["gen.seed_declared"]["status"] == "skipped"
    elif name == "openai_judge_eval":
        assert by_id["judge.params_declared"]["severity"] == "CRITICAL"
        assert by_id["model.dtype_declared"]["status"] == "skipped"
    else:
        assert by_id["privacy.mechanism_declared"]["severity"] == "CRITICAL"
        assert by_id["model.trust_remote_code_declared"]["severity"] == "WARNING"


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("variant", ["complete", "gaps"])
def test_level_one_snapshot_and_schema(tmp_path: Path, name: str, variant: str) -> None:
    repo = materialize_repo(name, tmp_path, manifest=variant)
    report = audit_json(repo)
    schema = json.loads(
        (Path(__file__).resolve().parents[3] / "schemas/audit_report.schema.json").read_text()
    )
    jsonschema.validate(report, schema)
    assert_json_snapshot(
        report,
        FIXTURES_ROOT / "repos" / name / "expected" / f"audit_L1_{variant}.json",
    )


def test_complete_overlay_is_variant_scoped(tmp_path: Path) -> None:
    plain = materialize_repo("hf_vllm_eval", tmp_path / "plain")
    gaps = materialize_repo("hf_vllm_eval", tmp_path / "gaps", manifest="gaps")
    complete = materialize_repo("hf_vllm_eval", tmp_path / "complete", manifest="complete")
    assert "vllm>=0.10" in (plain / "requirements.txt").read_text()
    assert "vllm>=0.10" in (gaps / "requirements.txt").read_text()
    assert "vllm==0.10.0" in (complete / "requirements.txt").read_text()
    assert not (plain / ".python-version").exists()
    assert (complete / ".python-version").read_text().strip() == "3.11"


def test_privacy_complete_secret_is_ignored_before_commit(tmp_path: Path) -> None:
    gaps = materialize_repo("privacy_custom_params", tmp_path / "gaps", manifest="gaps")
    complete = materialize_repo("privacy_custom_params", tmp_path / "complete", manifest="complete")
    assert run_git(gaps, "ls-files", ".env").stdout.strip() == b".env"
    assert run_git(complete, "ls-files", ".env").stdout == b""
    assert run_git(complete, "check-ignore", ".env").stdout.strip() == b".env"
