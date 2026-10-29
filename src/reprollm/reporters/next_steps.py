"""Bounded, read-only guidance derived from the existing audit report (UXR03)."""

from __future__ import annotations

from reprollm.core.paths import is_relative_project_path
from reprollm.core.redaction import redact_text
from reprollm.schemas.finding import AuditReport, Finding, FindingStatus, Severity

_LIMIT = 3
_INITIALIZATION = "env.reprollm_initialized"
_RANK = {Severity.CRITICAL: 0, Severity.WARNING: 2, Severity.INFO: 3}


def _safe_text(value: str, limit: int = 240) -> str:
    # Sanitize before truncation, so shortening cannot hide part of a secret pattern.
    value = redact_text(value)[0]
    escapes = {"\n": r"\n", "\r": r"\r", "\t": r"\t"}
    parts: list[str] = []
    for char in value:
        if char in escapes:
            parts.append(escapes[char])
        elif char.isprintable():
            parts.append(char)
        elif ord(char) <= 0xFFFF:
            parts.append(f"\\u{ord(char):04x}")
        else:
            parts.append(f"\\U{ord(char):08x}")
    text = "".join(parts)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _location(group: list[Finding]) -> str:
    locations = {
        item.field or item.path
        for finding in group
        for item in finding.evidence
        if (item.field or item.path) and is_relative_project_path(item.field or item.path or "")
    }
    # Existing rule evidence is authoritative; never copy values or free-form notes.
    return _safe_text(min(location for location in locations if location), 100) if locations else ""


def _groups(report: AuditReport) -> list[list[Finding]]:
    groups: dict[tuple[Severity, str, str], list[Finding]] = {}
    for finding in report.findings:
        if finding.status == FindingStatus.FAIL and finding.severity in _RANK:
            groups.setdefault((finding.severity, finding.rule_id, finding.fix_hint), []).append(
                finding
            )

    def order(group: list[Finding]) -> tuple[int, str, str]:
        first = group[0]
        rank = _RANK[first.severity]
        if first.rule_id == _INITIALIZATION and report.documents.manifest is None:
            rank = min(rank, 1)
        return rank, first.rule_id, first.fix_hint

    return sorted(groups.values(), key=order)


def _guidance(group: list[Finding], report: AuditReport) -> str:
    finding = group[0]
    location = _location(group)
    hint = finding.fix_hint.strip() or (
        "Review the evidence for this rule below and update the reported field or file."
    )
    if finding.rule_id == _INITIALIZATION and report.documents.manifest is None:
        location = "reprollm.yaml"
        hint = "Run `reprollm init --interactive` to create the experiment declaration."
    count = f" ({len(group)} findings)" if len(group) > 1 else ""
    target = f" at {location}" if location else ""
    return (
        f"[{finding.severity.value}] {_safe_text(finding.rule_id, 80)}{count}{target}: "
        f"{_safe_text(hint)}"
    )


def _workflow(report: AuditReport) -> str:
    if report.documents.manifest is None:
        ignored_initialization = any(
            finding.rule_id == _INITIALIZATION and finding.status == FindingStatus.SUPPRESSED
            for finding in report.findings
        )
        if ignored_initialization:
            return "Review the suppressed findings below before choosing another action."
        return "Create reprollm.yaml: `reprollm init --interactive`."
    if report.documents.lock is None:
        return (
            "Create reprollm.lock: `reprollm lock --offline`; "
            "remote identities may remain unresolved."
        )
    if report.documents.runs == 0:
        return (
            "If execution.command is configured in reprollm.yaml, "
            "preview it with `reprollm run --dry-run`."
        )
    return "Review recorded runs with `reprollm runs list`, then export with `reprollm export .`."


def next_step_lines(report: AuditReport) -> list[str]:
    """Render at most three actions without changing findings or interpreting their prose."""
    groups = _groups(report)
    actions = [_guidance(group, report) for group in groups[:_LIMIT]]
    skipped = sum(finding.status == FindingStatus.SKIPPED for finding in report.findings)
    if not actions and not skipped:
        actions = [_workflow(report)]
    lines = ["Next steps (in the audited repository)"]
    lines.extend(f"  {index}. {action}" for index, action in enumerate(actions, 1))
    if len(groups) > _LIMIT:
        lines.append("  Review the remaining findings below after these actions.")
    if skipped:
        noun = "check" if skipped == 1 else "checks"
        lines.append(
            f"  Coverage: {skipped} skipped {noun}; this experiment was not fully checked. "
            "Inspect them with `reprollm audit . --show-skipped`."
        )
    return lines
