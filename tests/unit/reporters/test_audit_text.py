"""UX-T04 text grouping must preserve evidence and the selected exit policy."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.reporters.github import render_audit_github
from reprollm.reporters.json_ import audit_report_to_json
from reprollm.reporters.text import render_audit_text
from reprollm.schemas.finding import (
    AuditReport,
    DocumentsSection,
    Evidence,
    EvidenceKind,
    Finding,
    FindingStatus,
    ProfilesSection,
    Severity,
    Summary,
)

runner = CliRunner()


def _warning(index: int, *, rule_id: str = "eval.metric_implementation_referenced") -> Finding:
    return Finding(
        rule_id=rule_id,
        category="eval",
        severity=Severity.WARNING,
        status=FindingStatus.FAIL,
        level=1,
        message=f"Metric {index} has no implementation.",
        evidence=[
            Evidence(kind=EvidenceKind.FIELD, field=f"evaluation.metrics.{index}.implementation"),
            Evidence(kind=EvidenceKind.FILE, path=f"metrics/metric_{index}.py", note="declared"),
        ],
        fix_hint="Set evaluation.metrics.<index>.implementation in reprollm.yaml.",
    )


def _report(findings: list[Finding]) -> AuditReport:
    return AuditReport(
        reprollm_version="0.6.1",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        target=".",
        level=1,
        profiles=ProfilesSection(resolved=["core", "evaluation"]),
        documents=DocumentsSection(manifest="reprollm.yaml"),
        summary=Summary(
            critical=sum(
                f.status == FindingStatus.FAIL and f.severity == Severity.CRITICAL for f in findings
            ),
            warning=sum(
                f.status == FindingStatus.FAIL and f.severity == Severity.WARNING for f in findings
            ),
            info=sum(
                f.status == FindingStatus.FAIL and f.severity == Severity.INFO for f in findings
            ),
            pass_=sum(f.status == FindingStatus.PASS for f in findings),
            suppressed=sum(f.status == FindingStatus.SUPPRESSED for f in findings),
            skipped=sum(f.status == FindingStatus.SKIPPED for f in findings),
        ),
        findings=findings,
    )


def _render(report: AuditReport, *, details: bool = False) -> str:
    return render_audit_text(
        report, fail_on="never", exit_code=0, details=details, ascii_symbols=True
    )


@pytest.mark.parametrize("count", [2, 3, 4, 13123])
def test_warning_groups_keep_counts_three_examples_and_one_fix(count: int) -> None:
    report = _report([_warning(index) for index in range(count)])
    original = audit_report_to_json(report)
    text = _render(report)
    assert (
        f"! eval.metric_implementation_referenced — {count} findings ({min(count, 3)} shown)"
        in text
    )
    for index in range(min(count, 3)):
        assert f"Metric {index} has no implementation." in text
        assert f"evaluation.metrics.{index}.implementation" in text
        assert f"metrics/metric_{index}.py (declared)" in text
    assert "Metric 3 has no implementation." not in text
    assert text.count("fix: Set evaluation.metrics.<index>.implementation") == 1
    assert "Use --details for every finding; --format json preserves all evidence." in text
    assert f"Findings: FAIL (0 critical, {count} warning)" in text
    assert audit_report_to_json(report) == original


def test_single_warning_remains_an_individual_row() -> None:
    text = _render(_report([_warning(0)]))
    assert "! eval.metric_implementation_referenced      Metric 0 has no implementation." in text
    assert "shown)" not in text
    assert "Use --details" not in text


def test_group_order_is_by_rule_and_examples_keep_report_order() -> None:
    report = _report([_warning(8, rule_id="eval.z_rule"), _warning(4), _warning(1), _warning(2)])
    text = _render(report)
    assert text.index("! eval.metric_implementation_referenced") < text.index("! eval.z_rule")
    assert text.index("Metric 4") < text.index("Metric 1") < text.index("Metric 2")


def test_grouping_keeps_different_fixes_severities_and_statuses_separate() -> None:
    first, second = _warning(0), _warning(1)
    different_fix = _warning(2).model_copy(update={"fix_hint": "Use a package version."})
    critical = _warning(3).model_copy(update={"severity": Severity.CRITICAL})
    info = _warning(4).model_copy(update={"severity": Severity.INFO})
    passed = _warning(5).model_copy(update={"status": FindingStatus.PASS})
    skipped = _warning(6).model_copy(update={"status": FindingStatus.SKIPPED})
    suppressed = [
        _warning(index).model_copy(
            update={"status": FindingStatus.SUPPRESSED, "suppressed_reason": reason}
        )
        for index, reason in [(7, "first reason"), (8, "second reason")]
    ]
    report = _report([first, second, different_fix, critical, info, passed, skipped, *suppressed])
    text = render_audit_text(
        report,
        fail_on="critical",
        exit_code=1,
        ascii_symbols=True,
        show_passed=True,
        show_skipped=True,
    )
    assert "— 2 findings (2 shown)" in text
    assert text.count("findings (") == 1
    assert "fix: Use a package version." in text
    assert "X eval.metric_implementation_referenced      Metric 3" in text
    assert "i eval.metric_implementation_referenced      Metric 4" in text
    assert "! eval.metric_implementation_referenced      Metric 5" in text
    assert "- eval.metric_implementation_referenced      skipped: Metric 6" in text
    assert "(reason: first reason)" in text and "(reason: second reason)" in text
    assert "1 passed · 2 suppressed · 1 skipped" in text
    assert "Findings: FAIL (1 critical, 3 warning)" in text


@pytest.mark.parametrize("details", [False, True])
def test_compact_and_expanded_text_are_deterministic_and_machine_evidence_is_unchanged(
    details: bool,
) -> None:
    report = _report([_warning(index) for index in range(7)])
    before_json = audit_report_to_json(report)
    before_github = render_audit_github(report)
    text = _render(report, details=details)
    assert text == _render(report, details=details)
    assert audit_report_to_json(report) == before_json
    assert render_audit_github(report) == before_github
    if details:
        assert "shown)" not in text
        assert "Use --details" not in text
        assert text.count("! eval.metric_implementation_referenced      ") == 7
        assert text.count("fix: ") == 7
        assert text.index("Metric 0") < text.index("Metric 6")
        assert "metrics/metric_6.py (declared)" in text


@pytest.mark.parametrize(
    ("status", "severity", "show_option"),
    [
        (FindingStatus.PASS, Severity.PASS, "show_passed"),
        (FindingStatus.SKIPPED, Severity.INFO, "show_skipped"),
    ],
)
@pytest.mark.parametrize("details", [False, True])
def test_visibility_flags_and_fixed_symbols_work_in_both_modes(
    status: FindingStatus, severity: Severity, show_option: str, details: bool
) -> None:
    finding = _warning(0).model_copy(update={"status": status, "severity": severity})
    report = _report([finding])
    assert "eval.metric_implementation_referenced" not in _render(report, details=details)
    options = {show_option: True}
    text = render_audit_text(report, fail_on="critical", exit_code=0, details=details, **options)
    assert f"{'✔' if status == FindingStatus.PASS else '–'} eval.metric" in text


@pytest.mark.parametrize(
    ("severities", "config_threshold", "flag_threshold", "expected_exit", "reason"),
    [
        ([Severity.WARNING], None, None, 0, "no finding reaches the threshold"),
        ([Severity.WARNING], None, "warning", 1, "findings reach the threshold"),
        ([Severity.CRITICAL], None, "never", 0, "finding-based failure disabled"),
        ([Severity.WARNING], "warning", None, 1, "findings reach the threshold"),
        ([Severity.WARNING], "warning", "critical", 0, "no finding reaches the threshold"),
        ([Severity.CRITICAL], "never", None, 0, "finding-based failure disabled"),
    ],
)
def test_cli_result_explains_effective_threshold_and_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    severities: list[Severity],
    config_threshold: str | None,
    flag_threshold: str | None,
    expected_exit: int,
    reason: str,
) -> None:
    report = _report(
        [
            _warning(index).model_copy(update={"severity": severity})
            for index, severity in enumerate(severities)
        ]
    )
    monkeypatch.setattr("reprollm.cli.audit.run_audit", lambda *args, **kwargs: report)
    if config_threshold:
        (tmp_path / ".reprollm").mkdir()
        (tmp_path / ".reprollm" / "config.yaml").write_text(
            f"schema_version: 1\naudit:\n  fail_on: {config_threshold}\n", encoding="utf-8"
        )
    args = ["audit", str(tmp_path)]
    if flag_threshold:
        args.extend(["--fail-on", flag_threshold])
    result = runner.invoke(app, args)
    assert result.exit_code == expected_exit, result.output
    threshold = flag_threshold or config_threshold or "critical"
    assert f"Result: exit {expected_exit} (--fail-on {threshold}; {reason})" in result.output
    assert "Findings: FAIL" in result.output


@pytest.mark.parametrize(
    "statuses", [[FindingStatus.PASS], [FindingStatus.SUPPRESSED, FindingStatus.SKIPPED]]
)
def test_pass_and_suppressed_skipped_only_reports_explain_pass(
    statuses: list[FindingStatus],
) -> None:
    report = _report(
        [
            _warning(index).model_copy(
                update={"status": status, "severity": Severity.INFO, "suppressed_reason": "handled"}
            )
            for index, status in enumerate(statuses)
        ]
    )
    assert "Findings: PASS\n" in _render(report)
    assert "Result: exit 0 (--fail-on never; finding-based failure disabled)" in _render(report)


@pytest.mark.parametrize("output_format", ["json", "github"])
@pytest.mark.parametrize("threshold", ["critical", "warning", "never"])
def test_cli_details_preserves_complete_machine_formats_and_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output_format: str, threshold: str
) -> None:
    report = _report([_warning(index) for index in range(5)])
    monkeypatch.setattr("reprollm.cli.audit.run_audit", lambda *args, **kwargs: report)
    args = ["audit", str(tmp_path), "--format", output_format, "--fail-on", threshold]
    default = runner.invoke(app, args)
    details = runner.invoke(app, [*args, "--details"])
    assert default.exit_code == details.exit_code == (1 if threshold == "warning" else 0)
    assert default.output == details.output
    expected = (
        audit_report_to_json(report) if output_format == "json" else render_audit_github(report)
    )
    assert default.output == expected + "\n"


def test_cli_details_expands_text_without_changing_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = _report([_warning(index) for index in range(5)])
    monkeypatch.setattr("reprollm.cli.audit.run_audit", lambda *args, **kwargs: report)
    args = ["audit", str(tmp_path), "--fail-on", "warning"]
    compact = runner.invoke(app, args)
    expanded = runner.invoke(app, [*args, "--details"])
    assert compact.exit_code == expanded.exit_code == 1
    assert "5 findings (3 shown)" in compact.output
    assert "Metric 4 has no implementation." not in compact.output
    assert "Metric 4 has no implementation." in expanded.output
    assert "shown)" not in expanded.output
