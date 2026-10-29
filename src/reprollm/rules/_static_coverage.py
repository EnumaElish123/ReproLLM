"""Internal findings for explicitly observed static-analysis gaps."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from reprollm.schemas.finding import Evidence, Finding, FindingStatus, Severity

if TYPE_CHECKING:
    from reprollm.core.context import AuditContext
    from reprollm.core.registry import Rule
    from reprollm.core.scanner import StaticScanGap


LISTING_PASS_REASON = (
    "Repository listing is incomplete in the captured eligible view; "
    "no rule-wide PASS is established."
)
PROFILE_PASS_REASON = (
    "Static profile detection is incomplete in the captured eligible view; "
    "no rule-wide PASS is established."
)


def skipped_for_gaps(
    rule: Rule,
    ctx: AuditContext,
    gaps: Sequence[StaticScanGap],
    *,
    message: str,
    evidence: Sequence[Evidence] = (),
) -> Finding:
    return Finding(
        rule_id=rule.id,
        aliases=list(rule.aliases),
        category=rule.category,
        severity=Severity.INFO,
        status=FindingStatus.SKIPPED,
        level=ctx.level,
        message=message,
        evidence=[
            *evidence,
            *[
                Evidence(
                    kind="file",
                    path=path,
                    note=f"{scope} analysis incomplete in the captured eligible view",
                )
                for scope, path in sorted(
                    {(gap.scope, gap.path) for gap in gaps},
                    key=lambda item: (item[0], item[1] or ""),
                )
            ],
        ],
        fix_hint=rule.fix_hint,
    )
