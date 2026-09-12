"""Shared field evidence for deterministic Level 1 declarations."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import Rule
from reprollm.schemas.finding import Evidence, Finding, FindingStatus, Severity


class PresenceRule(Rule):
    min_level = 1

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None

    def skip_reason(self, ctx: AuditContext) -> str:
        return "no manifest" if ctx.manifest is None else "no applicable declarations"

    def required_fields(self, ctx: AuditContext, fields: dict[str, object]) -> list[Finding]:
        missing = sorted(field for field, value in fields.items() if value is None)
        if not missing:
            return []
        return [
            self.finding(
                ctx,
                message="Missing fields: " + ", ".join(missing),
                evidence=[Evidence(kind="field", field=field, note="absent") for field in missing],
                fix_hint="Set " + ", ".join(missing) + " in reprollm.yaml.",
            )
        ]

    def field_result(
        self,
        ctx: AuditContext,
        field: str,
        present: bool,
        *,
        source: str | None = None,
        message: str | None = None,
    ) -> Finding:
        evidence = [Evidence(kind="field", field=field, note="declared" if present else "absent")]
        if source is not None and source != field:
            evidence[0].note = f"satisfied by {source}"
            evidence.append(Evidence(kind="field", field=source, note="declared"))
        return Finding(
            rule_id=self.id,
            aliases=list(self.aliases),
            category=self.category,
            severity=Severity.PASS if present else self.default_severity,
            status=FindingStatus.PASS if present else FindingStatus.FAIL,
            level=ctx.level,
            message=message or f"{field} is {'declared' if present else 'missing'}",
            evidence=evidence,
            fix_hint=f"Set {field} in reprollm.yaml.",
        )

    def skipped_field(self, ctx: AuditContext, field: str, reason: str) -> Finding:
        return Finding(
            rule_id=self.id,
            aliases=list(self.aliases),
            category=self.category,
            severity=Severity.INFO,
            status=FindingStatus.SKIPPED,
            level=ctx.level,
            message=f"{field}: {reason}",
            evidence=[Evidence(kind="field", field=field, note=reason)],
            fix_hint=self.fix_hint,
        )
