"""UXR03: concise actions without changing audit evidence or exit policy."""

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
    Finding,
    FindingStatus,
    ProfilesSection,
    Severity,
    Summary,
)


def finding(
    rule: str = "model.revision_pinned",
    severity: Severity = Severity.CRITICAL,
    status: FindingStatus = FindingStatus.FAIL,
    hint: str = "Set models.primary.revision in reprollm.yaml.",
    location: str = "models.primary.revision",
) -> Finding:
    return Finding(
        rule_id=rule,
        category="model",
        severity=severity,
        status=status,
        level=1,
        message="Original finding message.",
        fix_hint=hint,
        evidence=[Evidence(kind="field", field=location)],
    )


def report(
    findings: list[Finding],
    *,
    manifest: str | None = "manifest-hash",
    lock: str | None = None,
    runs: int = 0,
    level: int = 1,
) -> AuditReport:
    return AuditReport(
        reprollm_version="0.7.0",
        generated_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
        target=".",
        level=level,
        profiles=ProfilesSection(resolved=["core"]),
        documents=DocumentsSection(manifest=manifest, lock=lock, runs=runs),
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
            skipped=sum(f.status == FindingStatus.SKIPPED for f in findings),
            suppressed=sum(f.status == FindingStatus.SUPPRESSED for f in findings),
        ),
        findings=findings,
    )


def render(value: AuditReport, *, details: bool = False) -> str:
    return render_audit_text(
        value, fail_on="never", exit_code=0, ascii_symbols=True, details=details
    )


def actions(text: str) -> str:
    assert "Next steps (in the audited repository)\n" in text
    return text.split("Next steps (in the audited repository)\n", 1)[1].split("\n\n", 1)[0]


def test_next_steps_precede_findings_and_prioritize_critical_then_initialization() -> None:
    value = report(
        [
            finding("env.llm_critical_deps_pinned", Severity.WARNING, hint="Pin torch exactly."),
            finding("env.reprollm_initialized", Severity.INFO, hint="Run init."),
            finding(
                "env.secret_files_ignored",
                Severity.CRITICAL,
                hint="Remove the tracked secret file.",
            ),
            finding("exec.seed_declared", Severity.WARNING, hint="Set execution.seed."),
        ],
        manifest=None,
        level=0,
    )
    text = render(value)
    section = actions(text)
    assert text.index("Next steps") < text.index("CRITICAL (1)")
    assert section.index("env.secret_files_ignored") < section.index("env.reprollm_initialized")
    assert section.index("env.reprollm_initialized") < section.index("env.llm_critical_deps_pinned")
    assert "reprollm init --interactive" in section
    assert "exec.seed_declared" not in section
    assert (
        sum(
            line.startswith("  ") and line.lstrip()[:2] in {"1.", "2.", "3."}
            for line in section.splitlines()
        )
        == 3
    )
    assert "remaining findings" in section


def test_repeated_findings_have_one_action_and_stable_target() -> None:
    first = finding(
        "env.llm_critical_deps_pinned",
        Severity.WARNING,
        hint="Pin packages exactly.",
        location="dependencies.z",
    )
    second = first.model_copy(update={"evidence": [Evidence(kind="field", field="dependencies.a")]})
    section = actions(render(report([first, second, first])))
    assert section.count("env.llm_critical_deps_pinned") == 1
    assert "3 findings" in section and "dependencies.a" in section
    assert section == actions(render(report([second, first, first])))


def test_different_fixes_and_severities_are_separate_actions() -> None:
    values = [
        finding(hint="First fix."),
        finding(hint="Second fix."),
        finding(severity=Severity.WARNING),
    ]
    section = actions(render(report(values)))
    assert section.count("model.revision_pinned") == 3
    assert section.index("First fix.") < section.index("Second fix.") < section.index("[WARNING]")


@pytest.mark.parametrize(
    "status", [FindingStatus.PASS, FindingStatus.SUPPRESSED, FindingStatus.SKIPPED]
)
def test_non_fail_findings_never_become_fix_actions(status: FindingStatus) -> None:
    value = report([finding(status=status)], lock="lock-hash", runs=1)
    section = actions(render(value))
    assert "model.revision_pinned" not in section
    assert "Set models.primary.revision" not in section
    if status == FindingStatus.SKIPPED:
        assert "skipped" in section and "--show-skipped" in section
        assert "reprollm export" not in section
    assert "Findings: PASS\n" in render(value)


def test_skipped_coverage_note_is_present_even_when_skipped_rows_hidden() -> None:
    value = report([finding(), finding("env.coverage", Severity.INFO, FindingStatus.SKIPPED)])
    section = actions(render(value))
    assert "1 skipped" in section and "not fully checked" in section
    assert "--show-skipped" in section
    assert "env.coverage" not in section


@pytest.mark.parametrize(
    ("manifest", "lock", "runs", "expected"),
    [
        (None, None, 0, "reprollm init --interactive"),
        ("manifest-hash", None, 0, "reprollm lock --offline"),
        ("manifest-hash", "lock-hash", 0, "reprollm run --dry-run"),
        ("manifest-hash", "lock-hash", 1, "reprollm export ."),
    ],
)
def test_no_failure_workflow_follows_documents_not_forced_level(
    manifest: str | None,
    lock: str | None,
    runs: int,
    expected: str,
) -> None:
    section = actions(render(report([], manifest=manifest, lock=lock, runs=runs, level=0)))
    assert expected in section
    if manifest is not None:
        assert "reprollm init" not in section
    if lock is None and manifest is not None:
        assert "unresolved" in section
    if runs == 0 and lock is not None:
        assert "execution.command" in section


def test_dependency_lock_warning_does_not_suggest_reprollm_lock() -> None:
    section = actions(
        render(
            report(
                [
                    finding(
                        "env.lockfile_present",
                        Severity.WARNING,
                        hint="Create an exact dependency lockfile.",
                    )
                ]
            )
        )
    )
    assert "Create an exact dependency lockfile." in section
    assert "reprollm lock" not in section


def test_suppressed_initialization_does_not_reintroduce_the_same_action() -> None:
    value = report(
        [finding("env.reprollm_initialized", Severity.INFO, FindingStatus.SUPPRESSED)],
        manifest=None,
    )
    section = actions(render(value))
    assert "reprollm init" not in section


def test_missing_hint_has_actionable_fallback_and_bounded_guidance() -> None:
    empty = finding("project.missing", hint="")
    long = finding("project.long", Severity.WARNING, hint="x" * 4000)
    section = actions(render(report([empty, long])))
    assert "Review the evidence" in section
    assert "project.missing" in section and "project.long" in section
    assert len(section) < 1000
    assert "..." in section


@pytest.mark.security
def test_next_steps_redact_secrets_and_escape_controls_without_copying_evidence_values() -> None:
    secret = "sk-" + "A" * 24
    value = finding(
        hint=f"Set field using {secret}\n  2. forged\x1b[2J\u202e", location="custom.name\nnew-line"
    )
    value.evidence.extend(
        [
            Evidence(kind="file", path="/private/absolute/path"),
            Evidence(kind="field", field="custom.safe", value="VALUE_CANARY", note="NOTE_CANARY"),
        ]
    )
    section = actions(render(report([value])))
    assert secret not in section and "<REDACTED:openai>" in section
    assert "\x1b" not in section and "\u202e" not in section
    assert "\n  2. forged" not in section
    assert "/private/absolute/path" not in section
    assert "VALUE_CANARY" not in section and "NOTE_CANARY" not in section
    assert "\\n" in section and "\\u202e" in section


@pytest.mark.parametrize("details", [False, True])
def test_text_actions_do_not_mutate_complete_evidence(details: bool) -> None:
    value = report([finding(), finding("eval.metric", Severity.WARNING)])
    original = value.model_dump(mode="json")
    machine_json = audit_report_to_json(value)
    github = render_audit_github(value)
    text = render(value, details=details)
    assert text.count("Next steps") == 1
    assert text.count("      fix:") == 2
    assert value.model_dump(mode="json") == original
    assert audit_report_to_json(value) == machine_json
    assert render_audit_github(value) == github


@pytest.mark.parametrize("output_format", ["json", "github"])
def test_cli_machine_formats_have_no_actions_and_keep_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_format: str,
) -> None:
    value = report([finding()])
    monkeypatch.setattr("reprollm.cli.audit.run_audit", lambda *args, **kwargs: value)
    result = CliRunner().invoke(
        app, ["audit", str(tmp_path), "--format", output_format, "--fail-on", "critical"]
    )
    expected = (
        audit_report_to_json(value) if output_format == "json" else render_audit_github(value)
    )
    assert result.exit_code == 1 and result.output == expected + "\n"
    assert "Next steps" not in result.output
