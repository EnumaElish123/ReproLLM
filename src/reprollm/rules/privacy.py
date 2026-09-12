"""Privacy experiment declarations (spec §12.11, M3-T05)."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.schemas.finding import Finding, Severity


@register_rule
class ThreatModelDeclaredRule(PresenceRule):
    id = "privacy.threat_model_declared"
    category = "privacy"
    default_severity = Severity.CRITICAL
    description = "The privacy threat model is declared."
    fix_hint = "Set privacy.threat_model in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        privacy = ctx.manifest.privacy
        return [
            self.field_result(
                ctx,
                "privacy.threat_model",
                privacy is not None and privacy.threat_model is not None,
            )
        ]


@register_rule
class MechanismDeclaredRule(PresenceRule):
    id = "privacy.mechanism_declared"
    category = "privacy"
    default_severity = Severity.CRITICAL
    description = "The privacy mechanism has a name and nonempty parameters."
    fix_hint = "Set privacy.mechanism.name and nonempty privacy.mechanism.params in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        privacy = ctx.manifest.privacy
        mechanism = privacy.mechanism if privacy is not None else None
        findings = self.required_fields(
            ctx,
            {
                "privacy.mechanism.name": mechanism.name if mechanism is not None else None,
                "privacy.mechanism.params": mechanism.params
                if mechanism is not None and mechanism.params
                else None,
            },
        )
        if findings:
            for item in findings[0].evidence:
                if item.field == "privacy.mechanism.params":
                    item.note = "empty or absent; declare mechanism parameters"
            findings[0].fix_hint = self.fix_hint
        return findings


@register_rule
class MetricsDeclaredRule(PresenceRule):
    id = "privacy.metrics_declared"
    category = "privacy"
    default_severity = Severity.WARNING
    description = "Privacy metrics are declared."
    fix_hint = "Declare privacy.metrics in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        privacy = ctx.manifest.privacy
        return [
            self.field_result(ctx, "privacy.metrics", privacy is not None and bool(privacy.metrics))
        ]


@register_rule
class AttackConfigDeclaredRule(PresenceRule):
    id = "privacy.attack_config_declared"
    category = "privacy"
    default_severity = Severity.WARNING
    description = "The declared privacy attack has a method and query budget."
    fix_hint = "Set privacy.attack.method and privacy.attack.query_budget in reprollm.yaml."

    def applies(self, ctx: AuditContext) -> bool:
        privacy = ctx.manifest.privacy if ctx.manifest is not None else None
        return privacy is not None and privacy.attack is not None

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None and ctx.manifest.privacy is not None
        attack = ctx.manifest.privacy.attack
        assert attack is not None
        return self.required_fields(
            ctx,
            {
                "privacy.attack.method": attack.method,
                "privacy.attack.query_budget": attack.query_budget,
            },
        )
