"""``project.*`` rules generated from ``.reprollm/project-rules.yaml`` (§12.13).

Instances are created per audit from the accepted declarations — they are never
registered in the global builtin registry, so accepted rules cannot shadow or
collide with shipped rule IDs (the ``project.`` prefix is reserved by the
schema pattern).
"""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.schemas.finding import Evidence, Finding, FindingStatus, Severity
from reprollm.schemas.project_rules import ProjectRule as ProjectRuleSpec

_SEVERITY = {
    "CRITICAL": Severity.CRITICAL,
    "WARNING": Severity.WARNING,
    "INFO": Severity.INFO,
}


class GeneratedProjectRule:
    """One accepted declaration; FAIL when its field is absent/null.

    Deliberately not a :class:`~reprollm.core.registry.Rule` subclass: builtin
    rules carry ClassVar identity, while generated rules are per-audit
    instances built from accepted declarations. The engine executes them on a
    dedicated path with the same applies/check/skip_reason contract.
    """

    category = "project"
    min_level = 1

    def __init__(self, spec: ProjectRuleSpec) -> None:
        self.spec = spec
        self.id: str = spec.id
        self.default_severity: Severity = _SEVERITY[spec.severity]
        self.description: str = f"{spec.field} is declared (accepted: {spec.reason})"
        self.fix_hint: str = f"Set {spec.field} in reprollm.yaml (reason: {spec.reason})"

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None

    def skip_reason(self, ctx: AuditContext) -> str | None:
        return "no manifest (Level 0)" if ctx.manifest is None else None

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        if _field_value(ctx.manifest.model_dump(), self.spec.field) is not None:
            return []
        return [
            self.finding(
                ctx,
                message=f"{self.spec.field} is accepted for this project but missing or null",
                evidence=[
                    Evidence(
                        kind="field",
                        field=self.spec.field,
                        note=f"accepted: {self.spec.reason}",
                    )
                ],
            )
        ]

    def finding(
        self,
        ctx: AuditContext,
        *,
        message: str,
        evidence: list[Evidence] | None = None,
        severity: Severity | None = None,
        fix_hint: str | None = None,
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            aliases=[],
            category=self.category,
            severity=severity or self.default_severity,
            status=FindingStatus.FAIL,
            level=ctx.level,
            message=message,
            evidence=evidence or [],
            fix_hint=fix_hint or self.fix_hint,
            severity_origin="project_rule",
        )


def _field_value(data: dict[str, object], dotted: str) -> object:
    node: object = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def generated_rules(specs: list[ProjectRuleSpec]) -> list[GeneratedProjectRule]:
    return [GeneratedProjectRule(spec) for spec in specs]
