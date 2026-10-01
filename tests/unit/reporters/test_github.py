"""Workflow commands must survive the GitHub runner's V2 parser (M9-T02)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from reprollm.reporters.github import render_audit_github
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


def _decode(text: str, *, property_value: bool = False) -> str:
    replacements = [("%0D", "\r"), ("%0A", "\n")]
    if property_value:
        replacements.extend([("%3A", ":"), ("%2C", ",")])
    # ActionCommand.cs decodes percent last so an escaped literal remains literal.
    replacements.append(("%25", "%"))
    for escaped, original in replacements:
        text = text.replace(escaped, original)
    return text


def _parse_workflow_command(line: str) -> tuple[str, dict[str, str], str]:
    """Read output using actions/runner's ActionCommand.TryParseV2 grammar."""
    assert line.startswith("::")
    header, data = line[2:].split("::", 1)
    command, _, raw_properties = header.partition(" ")
    properties = {}
    for entry in raw_properties.split(","):
        name, _, value = entry.partition("=")
        if name and value:
            properties[name] = _decode(value, property_value=True)
    return command, properties, _decode(data)


def _render_finding(
    evidence: list[Evidence],
    *,
    severity: Severity = Severity.CRITICAL,
    message: str = "Pin the revision.",
    fix_hint: str = "Run reprollm lock.",
) -> list[str]:
    finding = Finding(
        rule_id="model.revision_pinned",
        category="model",
        severity=severity,
        status=FindingStatus.FAIL,
        level=1,
        message=message,
        evidence=evidence,
        fix_hint=fix_hint,
    )
    report = AuditReport(
        reprollm_version="0.6.0",
        generated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        target=".",
        level=1,
        profiles=ProfilesSection(resolved=["core"]),
        documents=DocumentsSection(),
        summary=Summary(),
        findings=[finding],
    )
    return render_audit_github(report).splitlines()


@pytest.mark.parametrize(
    ("severity", "command"),
    [(Severity.CRITICAL, "error"), (Severity.WARNING, "warning"), (Severity.INFO, "notice")],
)
def test_runner_parses_title_file_and_line_as_separate_properties(
    severity: Severity, command: str
) -> None:
    lines = _render_finding(
        [Evidence(kind=EvidenceKind.FILE, path="configs/model.yaml", line=12)],
        severity=severity,
    )
    actual_command, properties, data = _parse_workflow_command(lines[0])
    assert actual_command == command
    assert properties == {
        "title": f"{severity.value}: model.revision_pinned",
        "file": "configs/model.yaml",
        "line": "12",
    }
    assert data == "Pin the revision. — fix: Run reprollm lock."


@pytest.mark.parametrize(
    ("evidence", "expected_location"),
    [
        (
            [
                Evidence(kind=EvidenceKind.FIELD, field="model", line=9),
                Evidence(kind=EvidenceKind.FILE, path="configs/model.yaml", line=34),
            ],
            {"file": "configs/model.yaml", "line": "34"},
        ),
        (
            [
                Evidence(kind=EvidenceKind.FILE, path="configs/model.yaml"),
                Evidence(kind=EvidenceKind.FILE, path="scripts/load.py", line=77),
            ],
            {"file": "configs/model.yaml"},
        ),
        (
            [
                Evidence(kind=EvidenceKind.FILE, path="configs/model.yaml", line=12),
                Evidence(kind=EvidenceKind.FILE, path="scripts/load.py", line=77),
            ],
            {"file": "configs/model.yaml", "line": "12"},
        ),
        ([Evidence(kind=EvidenceKind.FIELD, field="model", line=9)], {}),
    ],
)
def test_annotation_location_comes_from_one_evidence(
    evidence: list[Evidence], expected_location: dict[str, str]
) -> None:
    _, properties, _ = _parse_workflow_command(_render_finding(evidence)[0])
    assert {key: value for key, value in properties.items() if key != "title"} == expected_location


def test_runner_round_trips_escaped_properties_and_message_without_new_commands() -> None:
    path = "configs/a%,:literal%0A\r\n.yaml"
    message = "literal %0A\r\n::error file=other.py,line=1::unexpected"
    fix_hint = "Keep 100%\r\ncertainty."
    lines = _render_finding(
        [Evidence(kind=EvidenceKind.FILE, path=path, line=7)],
        message=message,
        fix_hint=fix_hint,
    )
    assert len(lines) == 2
    command, properties, data = _parse_workflow_command(lines[0])
    assert command == "error"
    assert properties == {
        "title": "CRITICAL: model.revision_pinned",
        "file": path,
        "line": "7",
    }
    assert data == f"{message} — fix: {fix_hint}"
