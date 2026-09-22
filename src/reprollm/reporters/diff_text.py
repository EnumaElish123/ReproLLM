"""Human-readable semantic drift grouped by experiment section (§18)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from reprollm.diff.differ import section_rank
from reprollm.schemas.diff_report import DiffChange, DiffReport

_HASH = re.compile(r"(?<![A-Za-z0-9])(?:sha256:)?[a-fA-F0-9]{40,64}(?![A-Za-z0-9])")


def _value(value: Any) -> str:
    text = (
        value if isinstance(value, str) else json.dumps(value, sort_keys=True, ensure_ascii=False)
    )
    text = text.replace("\n", r"\n").replace("\r", r"\r")
    return _HASH.sub(
        lambda match: (
            ("sha256:" if match[0].startswith("sha256:") else "")
            + match[0].removeprefix("sha256:")[:12]
        ),
        text,
    )


def render_diff_text(report: DiffReport) -> str:
    lines = [f"a: {report.a.kind} {report.a.ref}", f"b: {report.b.kind} {report.b.ref}"]
    if report.filtered_below is not None:
        lines.append(f"Showing {report.filtered_below} and above; summary includes all changes.")
    grouped: dict[str, list[DiffChange]] = defaultdict(list)
    for change in report.changes:
        grouped[change.path.split(".", 1)[0]].append(change)
    for section in sorted(grouped, key=section_rank):
        lines.extend(["", section])
        for change in grouped[section]:
            before = "<absent>" if change.status == "added" else _value(change.a)
            after = "<absent>" if change.status == "removed" else _value(change.b)
            lines.append(f"  {change.path}  {before} → {after}  [{change.severity}]")
            if change.note:
                lines.append(f"    {change.note}")
    highest = report.summary.highest
    prefix = f"Highest drift: {highest} ({report.summary.counts[highest]} changes). "
    if highest == "HIGH":
        verdict = prefix + "These runs are not directly comparable."
    elif highest in ("MEDIUM_HIGH", "MEDIUM"):
        verdict = prefix + "Results may differ; review the changes above."
    else:
        verdict = "No reproducibility-relevant drift detected."
    return "\n".join([*lines, "", verdict]) + "\n"
