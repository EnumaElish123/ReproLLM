"""Prompt declarations and explicit file references (spec §12.7, M3-T03)."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.rules._stubs import LevelTwoStubRule
from reprollm.schemas.finding import Evidence, Finding, Severity


@register_rule
class HashedRule(LevelTwoStubRule):
    id = "prompt.hashed"
    category = "prompt"
    default_severity = Severity.WARNING
    description = "Every prompt role has a recorded content hash."
    fix_hint = "Run `reprollm lock` to hash prompts.<role> in reprollm.lock."


@register_rule
class DeclaredRule(PresenceRule):
    id = "prompt.declared"
    category = "prompt"
    default_severity = Severity.WARNING
    description = "At least one prompt role is declared."
    fix_hint = "Declare prompts.<role>.path or prompts.<role>.text in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        return [self.field_result(ctx, "prompts", bool(ctx.manifest.prompts))]


@register_rule
class FileExistsRule(PresenceRule):
    id = "prompt.file_exists"
    category = "prompt"
    default_severity = Severity.CRITICAL
    description = "Every referenced prompt file exists."
    fix_hint = "Set prompts.<role>.path to an existing file in reprollm.yaml."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and bool(ctx.manifest.prompts)

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        findings: list[Finding] = []
        for role, prompt in sorted(ctx.manifest.prompts.items()):
            field = f"prompts.{role}.path"
            if prompt.text is not None:
                findings.append(self.field_result(ctx, f"prompts.{role}.text", True))
            elif prompt.path is None:
                findings.append(self.skipped_field(ctx, field, "no prompt source is declared"))
            else:
                exists = ctx.fs.exists(prompt.path)
                finding = self.field_result(
                    ctx,
                    field,
                    exists,
                    message=f"{field}: referenced file {'exists' if exists else 'is missing'}",
                )
                finding.evidence[0].note = (
                    "referenced file exists" if exists else "referenced file missing"
                )
                finding.evidence.append(Evidence(kind="file", path=prompt.path))
                finding.fix_hint = f"Set {field} to an existing file in reprollm.yaml."
                findings.append(finding)
        return findings


@register_rule
class FewShotDeclaredRule(PresenceRule):
    id = "prompt.few_shot_declared"
    category = "prompt"
    default_severity = Severity.INFO
    description = "Few-shot configuration is explicitly declared."
    fix_hint = "Set prompts.<role>.few_shot in reprollm.yaml; use n: 0 for zero-shot prompts."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        if any(prompt.few_shot is not None for prompt in ctx.manifest.prompts.values()):
            return []
        return [
            self.finding(
                ctx,
                message="prompts has no few_shot declaration",
                evidence=[
                    Evidence(kind="field", field=f"prompts.{role}.few_shot", note="absent")
                    for role in sorted(ctx.manifest.prompts)
                ]
                or [Evidence(kind="field", field="prompts", note="empty")],
            )
        ]
