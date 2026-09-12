"""LLM-as-a-judge declarations (spec §12.9, M3-T04)."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.rules._stubs import LevelTwoStubRule
from reprollm.schemas.finding import Finding, Severity
from reprollm.schemas.manifest import JudgeSpec


@register_rule
class PromptHashedRule(LevelTwoStubRule):
    id = "judge.prompt_hashed"
    category = "judge"
    default_severity = Severity.WARNING
    description = "The declared judge prompt has a recorded content hash."
    fix_hint = "Run `reprollm lock` to hash the evaluation.judge.prompt_ref role in reprollm.lock."


@register_rule
class PinnabilityRecordedRule(LevelTwoStubRule):
    id = "judge.pinnability_recorded"
    category = "judge"
    default_severity = Severity.WARNING
    description = "The declared judge model has an explicit pinnability record."
    fix_hint = (
        "Run `reprollm lock` to record pinnability for evaluation.judge.model_ref in reprollm.lock."
    )


def _judge(ctx: AuditContext) -> JudgeSpec | None:
    assert ctx.manifest is not None
    evaluation = ctx.manifest.evaluation
    return evaluation.judge if evaluation is not None else None


@register_rule
class ModelDeclaredRule(PresenceRule):
    id = "judge.model_declared"
    category = "judge"
    default_severity = Severity.CRITICAL
    description = "The judge model role is declared."
    fix_hint = (
        "Declare models.judge or the role named by evaluation.judge.model_ref in reprollm.yaml."
    )

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        judge = _judge(ctx)
        role = judge.model_ref if judge is not None else "judge"
        return [self.field_result(ctx, f"models.{role}", role in ctx.manifest.models)]


@register_rule
class PromptDeclaredRule(PresenceRule):
    id = "judge.prompt_declared"
    category = "judge"
    default_severity = Severity.CRITICAL
    description = "The judge prompt role is declared."
    fix_hint = (
        "Declare prompts.judge or the role named by evaluation.judge.prompt_ref in reprollm.yaml."
    )

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        judge = _judge(ctx)
        role = judge.prompt_ref if judge is not None else "judge"
        return [self.field_result(ctx, f"prompts.{role}", role in ctx.manifest.prompts)]


@register_rule
class ParamsDeclaredRule(PresenceRule):
    id = "judge.params_declared"
    category = "judge"
    default_severity = Severity.CRITICAL
    description = "Judge temperature and max_tokens are declared."
    fix_hint = (
        "Set evaluation.judge.params.temperature and evaluation.judge.params.max_tokens "
        "in reprollm.yaml."
    )

    def check(self, ctx: AuditContext) -> list[Finding]:
        judge = _judge(ctx)
        return self.required_fields(
            ctx,
            {
                f"evaluation.judge.params.{field}": getattr(judge.params, field)
                if judge is not None
                else None
                for field in ("temperature", "max_tokens")
            },
        )


@register_rule
class RepetitionsDeclaredRule(PresenceRule):
    id = "judge.repetitions_declared"
    category = "judge"
    default_severity = Severity.WARNING
    description = "The number of judge repetitions is declared."
    fix_hint = "Set evaluation.judge.repetitions in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        judge = _judge(ctx)
        return [
            self.field_result(
                ctx,
                "evaluation.judge.repetitions",
                judge is not None and judge.repetitions is not None,
            )
        ]
