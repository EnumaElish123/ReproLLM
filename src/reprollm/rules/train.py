"""Training declarations (spec §12.10, M3-T05)."""

from __future__ import annotations

from typing import ClassVar

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.schemas.finding import Evidence, Finding, Severity


class _TrainingFieldRule(PresenceRule):
    category = "train"
    default_severity = Severity.WARNING
    field: ClassVar[str]

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        training = ctx.manifest.training
        return [
            self.field_result(
                ctx,
                f"training.{self.field}",
                training is not None and getattr(training, self.field) is not None,
            )
        ]


@register_rule
class MethodDeclaredRule(_TrainingFieldRule):
    id = "train.method_declared"
    field = "method"
    description = "The training method is declared."
    fix_hint = "Set training.method in reprollm.yaml."


@register_rule
class HyperparametersDeclaredRule(PresenceRule):
    id = "train.hyperparameters_declared"
    category = "train"
    default_severity = Severity.CRITICAL
    description = "Learning rate, batch size and training duration are declared."
    fix_hint = (
        "Set training.learning_rate, training.batch_size and either training.epochs "
        "or training.max_steps in reprollm.yaml."
    )

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        training = ctx.manifest.training
        fields: dict[str, object] = {
            f"training.{field}": getattr(training, field) if training is not None else None
            for field in ("learning_rate", "batch_size")
        }
        duration_missing = training is None or (
            training.epochs is None and training.max_steps is None
        )
        if duration_missing:
            fields.update({"training.epochs": None, "training.max_steps": None})
        findings = self.required_fields(ctx, fields)
        if findings and duration_missing:
            missing = sorted(
                field
                for field, value in fields.items()
                if value is None and field not in {"training.epochs", "training.max_steps"}
            )
            missing.append("training.epochs or training.max_steps")
            findings[0].message = "Missing fields: " + ", ".join(missing)
            findings[0].fix_hint = "Set " + ", ".join(missing) + " in reprollm.yaml."
            for item in findings[0].evidence:
                if item.field in {"training.epochs", "training.max_steps"}:
                    item.note = "declare at least one of training.epochs or training.max_steps"
        return findings


@register_rule
class OptimizerDeclaredRule(PresenceRule):
    id = "train.optimizer_declared"
    category = "train"
    default_severity = Severity.WARNING
    description = "The optimizer and scheduler are declared."
    fix_hint = "Set training.optimizer and training.scheduler in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        training = ctx.manifest.training
        return self.required_fields(
            ctx,
            {
                f"training.{field}": getattr(training, field) if training is not None else None
                for field in ("optimizer", "scheduler")
            },
        )


@register_rule
class PrecisionDeclaredRule(_TrainingFieldRule):
    id = "train.precision_declared"
    field = "precision"
    description = "Training precision is declared."
    fix_hint = "Set training.precision in reprollm.yaml."


@register_rule
class LoraConfigCompleteRule(PresenceRule):
    id = "train.lora_config_complete"
    category = "train"
    default_severity = Severity.CRITICAL
    description = "One adapter declares LoRA rank, alpha and target_modules together."
    fix_hint = (
        "Set models.<role>.adapter.rank, models.<role>.adapter.alpha and "
        "models.<role>.adapter.target_modules on the same adapter in reprollm.yaml."
    )

    def applies(self, ctx: AuditContext) -> bool:
        training = ctx.manifest.training if ctx.manifest is not None else None
        return training is not None and training.method in {"lora", "qlora"}

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        evidence: list[Evidence] = []
        for role, model in sorted(ctx.manifest.models.items()):
            if model.adapter is None:
                evidence.append(
                    Evidence(kind="field", field=f"models.{role}.adapter", note="absent")
                )
                continue
            missing = [
                field
                for field in ("alpha", "rank", "target_modules")
                if getattr(model.adapter, field) is None
            ]
            if not missing:
                return []
            evidence.extend(
                Evidence(kind="field", field=f"models.{role}.adapter.{field}", note="absent")
                for field in missing
            )
        return [
            self.finding(
                ctx,
                message="models has no single adapter with rank, alpha and target_modules declared",
                evidence=evidence or [Evidence(kind="field", field="models", note="empty")],
            )
        ]
