"""Text reporter (spec §21): grouped by severity, CRITICAL first.

Symbols are the fixed set from the spec; ``ascii_symbols`` swaps them for
ASCII-safe alternatives under ``--no-color`` / non-TTY / ``NO_COLOR``.
"""

from __future__ import annotations

from reprollm.schemas.finding import AuditReport, Finding, FindingStatus, Severity

_SYMBOLS_UNICODE = {
    Severity.CRITICAL: "✖",
    Severity.WARNING: "▲",
    Severity.INFO: "ℹ",
    Severity.PASS: "✔",
    "muted": "–",
}
_SYMBOLS_ASCII = {
    Severity.CRITICAL: "X",
    Severity.WARNING: "!",
    Severity.INFO: "i",
    Severity.PASS: "+",
    "muted": "-",
}

_GROUP_ORDER = (Severity.CRITICAL, Severity.WARNING, Severity.INFO, Severity.PASS)
_GROUP_TITLES = {
    Severity.CRITICAL: "CRITICAL",
    Severity.WARNING: "WARNING",
    Severity.INFO: "INFO",
    Severity.PASS: "PASS",
}


def _visible(finding: Finding, *, show_passed: bool, show_skipped: bool) -> bool:
    if finding.status == FindingStatus.PASS:
        return show_passed
    if finding.status == FindingStatus.SKIPPED:
        return show_skipped
    return True


def _symbol(kind: Severity | str, ascii_symbols: bool) -> str:
    table = _SYMBOLS_ASCII if ascii_symbols else _SYMBOLS_UNICODE
    return table[kind]


def _evidence_lines(finding: Finding) -> list[str]:
    lines: list[str] = []
    for item in finding.evidence:
        location = item.field or item.path or ""
        note = item.note or ""
        if location and note:
            lines.append(f"      {location} ({note})")
        elif location or note:
            lines.append(f"      {location}{note}")
    return lines


def _finding_lines(finding: Finding, *, ascii_symbols: bool) -> list[str]:
    if finding.status == FindingStatus.SKIPPED:
        symbol = _symbol("muted", ascii_symbols)
        return [f"  {symbol} {finding.rule_id}      skipped: {finding.message}"]
    if finding.status == FindingStatus.SUPPRESSED:
        symbol = _symbol("muted", ascii_symbols)
        return [
            f"  {symbol} {finding.rule_id}      suppressed: {finding.message} "
            f"(reason: {finding.suppressed_reason})"
        ]
    symbol = _symbol(finding.severity, ascii_symbols)
    return [
        f"  {symbol} {finding.rule_id}      {finding.message}",
        *_evidence_lines(finding),
        f"      fix: {finding.fix_hint}",
    ]


def _warning_groups(members: list[Finding]) -> list[list[Finding]]:
    groups: list[list[Finding]] = []
    repeated: dict[tuple[str, str], list[Finding]] = {}
    for finding in members:
        if finding.status != FindingStatus.FAIL:
            groups.append([finding])
            continue
        key = (finding.rule_id, finding.fix_hint)
        if key not in repeated:
            repeated[key] = []
            groups.append(repeated[key])
        repeated[key].append(finding)
    return sorted(groups, key=lambda group: group[0].rule_id)


def _warning_group_lines(group: list[Finding], *, ascii_symbols: bool) -> list[str]:
    finding = group[0]
    symbol = _symbol(Severity.WARNING, ascii_symbols)
    examples = group[:3]
    lines = [f"  {symbol} {finding.rule_id} — {len(group)} findings ({len(examples)} shown)"]
    for example in examples:
        lines.append(f"      {example.message}")
        lines.extend(_evidence_lines(example))
    lines.append(f"      fix: {finding.fix_hint}")
    lines.append("      Use --details for every finding; --format json preserves all evidence.")
    return lines


def render_audit_text(
    report: AuditReport,
    *,
    fail_on: str,
    exit_code: int,
    details: bool = False,
    show_passed: bool = False,
    show_skipped: bool = False,
    ascii_symbols: bool = False,
) -> str:
    lines: list[str] = []
    profiles = ", ".join(report.profiles.resolved) or "core"
    lines.append(f"ReproLLM audit · level {report.level} · profiles: {profiles}")
    lines.append("")

    for group in _GROUP_ORDER:
        members = [
            f
            for f in report.findings
            if f.severity == group
            and _visible(f, show_passed=show_passed, show_skipped=show_skipped)
        ]
        if not members:
            continue
        lines.append(f"{_GROUP_TITLES[group]} ({len(members)})")
        entries = (
            _warning_groups(members)
            if group == Severity.WARNING and not details
            else [[finding] for finding in members]
        )
        for entry in entries:
            if len(entry) > 1:
                lines.extend(_warning_group_lines(entry, ascii_symbols=ascii_symbols))
            else:
                lines.extend(_finding_lines(entry[0], ascii_symbols=ascii_symbols))
        lines.append("")

    summary = report.summary
    counts_line = (
        f"{summary.pass_} passed · {summary.suppressed} suppressed · {summary.skipped} skipped"
    )
    if not (show_passed or show_skipped):
        counts_line += "        (use --show-passed / --show-skipped)"
    lines.append(counts_line)

    if summary.critical or summary.warning:
        lines.append(f"Findings: FAIL ({summary.critical} critical, {summary.warning} warning)")
    else:
        lines.append("Findings: PASS")

    if fail_on == "never":
        reason = "finding-based failure disabled"
    elif exit_code:
        reason = "findings reach the threshold"
    else:
        reason = "no finding reaches the threshold"
    lines.append(f"Result: exit {exit_code} (--fail-on {fail_on}; {reason})")

    if report.level == 0:
        detected = [
            entry
            for entry in report.profiles.detected
            if entry.shipped and entry.confidence in ("high", "medium")
        ]
        if detected:
            names = ", ".join(f"{entry.profile} ({entry.confidence})" for entry in detected)
            profile_list = ",".join(entry.profile for entry in detected)
            lines.append("")
            lines.append(
                f"Detected profiles: {names} — run: reprollm init --profiles {profile_list}"
            )
    return "\n".join(lines) + "\n"
