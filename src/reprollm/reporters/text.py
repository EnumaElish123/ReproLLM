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
    if finding.status in (FindingStatus.SKIPPED, FindingStatus.SUPPRESSED):
        return show_skipped
    return True


def _symbol(kind: Severity | str, ascii_symbols: bool) -> str:
    table = _SYMBOLS_ASCII if ascii_symbols else _SYMBOLS_UNICODE
    return table[kind]


def render_audit_text(
    report: AuditReport,
    *,
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
        for finding in members:
            if finding.status == FindingStatus.SKIPPED:
                symbol = _symbol("muted", ascii_symbols)
                lines.append(f"  {symbol} {finding.rule_id}      skipped: {finding.message}")
                continue
            if finding.status == FindingStatus.SUPPRESSED:
                symbol = _symbol("muted", ascii_symbols)
                lines.append(f"  {symbol} {finding.rule_id}      suppressed: {finding.message}")
                continue
            symbol = _symbol(finding.severity, ascii_symbols)
            lines.append(f"  {symbol} {finding.rule_id}      {finding.message}")
            for item in finding.evidence:
                location = item.field or item.path or ""
                note = item.note or ""
                if location and note:
                    lines.append(f"      {location} ({note})")
                elif location or note:
                    lines.append(f"      {location}{note}")
            lines.append(f"      fix: {finding.fix_hint}")
        lines.append("")

    summary = report.summary
    counts_line = (
        f"{summary.pass_} passed · {summary.suppressed} suppressed · {summary.skipped} skipped"
    )
    if not (show_passed or show_skipped):
        counts_line += "        (use --show-passed / --show-skipped)"
    lines.append(counts_line)

    if summary.critical:
        detail = f"{summary.critical} critical"
        if summary.warning:
            detail += f", {summary.warning} warning"
        lines.append(f"Result: FAIL ({detail})")
    elif summary.warning:
        lines.append(f"Result: FAIL ({summary.warning} warning)")
    else:
        lines.append("Result: PASS")

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
