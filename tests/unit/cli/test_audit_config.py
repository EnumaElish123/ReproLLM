"""Config precedence and visible, traceable suppression (M3-T07)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core import registry
from reprollm.core.engine import run_audit
from reprollm.core.yaml_io import dump_yaml
from reprollm.reporters.text import render_audit_text
from reprollm.schemas.finding import FindingStatus, Severity
from tests.conftest import materialize_repo

runner = CliRunner()


def config(repo: Path, **audit: object) -> None:
    folder = repo / ".reprollm"
    folder.mkdir(exist_ok=True)
    (folder / "config.yaml").write_text(dump_yaml({"audit": audit}), encoding="utf-8")


def test_dirty_tree_suppression_changes_exit_and_summary(tmp_path: Path) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    ignores = [
        {"rule": "code.clean_tree", "reason": "intentional local edit"},
        {"rule": "env.python_version_declared", "reason": "provided by the experiment runner"},
    ]
    config(repo, fail_on="warning", ignore=ignores)
    before = runner.invoke(app, ["audit", str(repo), "--format", "json"])
    assert before.exit_code == 1
    assert json.loads(before.output)["summary"]["warning"] == 1
    config(
        repo,
        fail_on="warning",
        ignore=[*ignores, {"rule": "code.no_untracked", "reason": "scratch outputs"}],
    )
    after = runner.invoke(app, ["audit", str(repo), "--format", "json"])
    assert after.exit_code == 0, after.output
    report = json.loads(after.output)
    assert report["summary"]["warning"] == 0
    assert report["summary"]["suppressed"] == 3
    finding = next(f for f in report["findings"] if f["rule_id"] == "code.no_untracked")
    assert finding["status"] == "suppressed" and finding["severity"] == "INFO"
    assert finding["suppressed_reason"] == "scratch outputs"
    assert any(
        e["note"] == "suppressed: original severity WARNING; reason: scratch outputs"
        for e in finding["evidence"]
    )


def test_alias_suppresses_canonical_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    monkeypatch.setitem(registry._ALIASES, "code.old_untracked", "code.no_untracked")
    config(repo, ignore=[{"rule": "code.old_untracked", "reason": "legacy config"}])
    finding = next(f for f in run_audit(repo).findings if f.rule_id == "code.no_untracked")
    assert finding.status == FindingStatus.SUPPRESSED
    assert finding.suppressed_reason == "legacy config"


def test_duplicate_alias_entries_suppress_once_with_first_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    monkeypatch.setitem(registry._ALIASES, "code.old_untracked", "code.no_untracked")
    config(
        repo,
        ignore=[
            {"rule": "code.old_untracked", "reason": "first explanation"},
            {"rule": "code.no_untracked", "reason": "second explanation"},
        ],
    )
    report = run_audit(repo)
    finding = next(f for f in report.findings if f.rule_id == "code.no_untracked")
    assert report.summary.suppressed == 1
    assert finding.suppressed_reason == "first explanation"
    assert len([e for e in finding.evidence if e.note and e.note.startswith("suppressed:")]) == 1


@pytest.mark.parametrize("reason", [None, "", " \t\n"])
def test_missing_or_blank_reason_exits_two_and_names_rule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    reason: str | None,
) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    entry = {"rule": "code.no_untracked"}
    if reason is not None:
        entry["reason"] = reason
    config(repo, ignore=[entry])
    monkeypatch.setattr("sys.argv", ["reprollm", "audit", str(repo)])
    with pytest.raises(SystemExit) as error:
        cli()
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "code.no_untracked" in message
    assert "audit.ignore" in message and "reason" in message
    assert "Traceback" not in message


def test_suppression_preserves_profile_severity_and_all_roles(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    (repo / "reprollm.yaml").write_text(
        dump_yaml(
            {
                "project": {"name": "suppression"},
                "experiment": {"profiles": ["evaluation"]},
                "generation": {"temperature": 0.7},
                "models": {"primary": {"id": "org/model"}, "judge": {"id": "org/judge"}},
            }
        ),
        encoding="utf-8",
    )
    config(
        repo,
        ignore=[
            {"rule": "gen.seed_declared", "reason": "provider cannot seed"},
            {"rule": "model.dtype_declared", "reason": "external precision contract"},
        ],
    )
    report = run_audit(repo)
    seed = next(f for f in report.findings if f.rule_id == "gen.seed_declared")
    assert seed.status == FindingStatus.SUPPRESSED
    assert seed.severity_origin == "profile:evaluation"
    assert any(
        e.note == "suppressed: original severity CRITICAL; reason: provider cannot seed"
        for e in seed.evidence
    )
    dtypes = [f for f in report.findings if f.rule_id == "model.dtype_declared"]
    assert len(dtypes) == 2
    assert all(f.status == FindingStatus.SUPPRESSED for f in dtypes)


def test_suppression_includes_pass_and_skipped_but_does_not_add_findings(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    config(
        repo,
        ignore=[
            {"rule": "code.git_repo", "reason": "handled by runner"},
            {"rule": "code.submodules_initialized", "reason": "no submodules"},
            {"rule": "model.primary_declared", "reason": "not selected at L0"},
            {"rule": "project.future", "reason": "not registered"},
        ],
    )
    report = run_audit(repo)
    assert report.summary.suppressed == 2
    assert not any(
        f.rule_id in {"model.primary_declared", "project.future"} for f in report.findings
    )
    by_id = {f.rule_id: f for f in report.findings}
    for rule_id, original in [("code.git_repo", "PASS"), ("code.submodules_initialized", "INFO")]:
        finding = by_id[rule_id]
        assert (finding.status, finding.severity) == (FindingStatus.SUPPRESSED, Severity.INFO)
        assert any(e.note and f"original severity {original};" in e.note for e in finding.evidence)


def test_cli_fail_on_overrides_config(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    config(repo, fail_on="warning")
    assert runner.invoke(app, ["audit", str(repo)]).exit_code == 1
    assert runner.invoke(app, ["audit", str(repo), "--fail-on", "critical"]).exit_code == 0
    assert runner.invoke(app, ["audit", str(repo), "--fail-on", "never"]).exit_code == 0
    config(repo, fail_on="never")
    assert runner.invoke(app, ["audit", str(repo), "--fail-on", "warning"]).exit_code == 1


def test_show_passed_config_and_explicit_flags(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    config(repo, show_passed=True)
    assert "PASS (" in runner.invoke(app, ["audit", str(repo)]).output
    assert "PASS (" not in runner.invoke(app, ["audit", str(repo), "--no-show-passed"]).output
    config(repo, show_passed=False)
    assert "PASS (" not in runner.invoke(app, ["audit", str(repo)]).output
    assert "PASS (" in runner.invoke(app, ["audit", str(repo), "--show-passed"]).output
    result = runner.invoke(app, ["audit", str(repo), "--format", "json"])
    assert any(f["status"] == "pass" for f in json.loads(result.output)["findings"])


def test_suppressed_is_visible_in_info_without_show_skipped(tmp_path: Path) -> None:
    repo = materialize_repo("dirty_tree", tmp_path)
    config(repo, ignore=[{"rule": "code.no_untracked", "reason": "scratch outputs"}])
    report = run_audit(repo)
    for ascii_symbols, symbol in [(False, "–"), (True, "-")]:
        text = render_audit_text(report, ascii_symbols=ascii_symbols)
        assert f"{symbol} code.no_untracked" in text
        assert "suppressed:" in text and "scratch outputs" in text
        assert text.index("INFO (") < text.index(f"{symbol} code.no_untracked")
        assert "code.submodules_initialized" not in text


def test_config_is_loaded_from_target_not_invocation_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path / "target")
    config(repo, fail_on="warning")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    config(elsewhere, fail_on="never")
    monkeypatch.chdir(elsewhere)
    assert runner.invoke(app, ["audit", str(repo)]).exit_code == 1
