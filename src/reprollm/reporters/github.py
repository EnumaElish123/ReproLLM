"""GitHub Actions workflow-command reporter (M9-T02, spec M9).

Emits ``::error``/``::warning``/``::notice`` annotations that GitHub renders
inline on PRs, plus a human-readable summary block. Designed for any CI that
speaks workflow commands — no ReproLLM Action installation required.

Escaping follows the workflow-commands spec: ``%`` → ``%25``, ``\\r`` →
``%0D``, ``\\n`` → ``%0A`` in message; ``%`` → ``%25``, ``\\r`` → ``%0D``,
``\\n`` → ``%0A``, ``:`` → ``%3A``, ``,`` → ``%2C`` in properties.
"""

from __future__ import annotations

from reprollm.schemas.finding import AuditReport, Finding, FindingStatus, Severity

_SEVERITY_COMMAND = {
    Severity.CRITICAL: "::error",
    Severity.WARNING: "::warning",
    Severity.INFO: "::notice",
}


def _escape_data(text: str) -> str:
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(text: str) -> str:
    return (
        text.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _annotation(finding: Finding) -> str:
    command = _SEVERITY_COMMAND.get(finding.severity, "::notice")
    title = f"{finding.severity.value}: {finding.rule_id}"
    properties: list[str] = [f"title={_escape_property(title)}"]

    # Attach file/line when evidence carries a path so the annotation renders
    # inline on the PR diff.
    first_path = next((e.path for e in finding.evidence if e.path), None)
    first_line = next((e.line for e in finding.evidence if e.line is not None), None)
    if first_path:
        properties.append(f"file={_escape_property(first_path)}")
        if first_line is not None:
            properties.append(f"line={first_line}")

    message = finding.message
    if finding.fix_hint:
        message = f"{message} — fix: {finding.fix_hint}"
    return f"{command} {' '.join(properties)}::{_escape_data(message)}"


def render_audit_github(report: AuditReport) -> str:
    lines: list[str] = []

    for finding in report.findings:
        if finding.status in (FindingStatus.FAIL, FindingStatus.SUPPRESSED):
            lines.append(_annotation(finding))

    summary = report.summary
    profiles = ", ".join(report.profiles.resolved)
    lines.append(
        f"::notice title=ReproLLM audit::"
        f"Level {report.level} · profiles: {profiles} · "
        f"{summary.critical} critical, {summary.warning} warning, "
        f"{summary.info} info, {summary.pass_} passed"
    )
    return "\n".join(lines) + "\n"
