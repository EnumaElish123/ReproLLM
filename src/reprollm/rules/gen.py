"""Generation and inference declarations (spec §12.6, M3-T03)."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.schemas.finding import Finding, Severity


@register_rule
class ParamsDeclaredRule(PresenceRule):
    id = "gen.params_declared"
    category = "gen"
    default_severity = Severity.WARNING
    description = "Generation temperature, top_p and max_tokens are declared."
    fix_hint = (
        "Set generation.temperature, generation.top_p and generation.max_tokens in reprollm.yaml."
    )

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        generation = ctx.manifest.generation
        return self.required_fields(
            ctx,
            {
                f"generation.{field}": getattr(generation, field)
                if generation is not None
                else None
                for field in ("temperature", "top_p", "max_tokens")
            },
        )


@register_rule
class SeedDeclaredRule(PresenceRule):
    id = "gen.seed_declared"
    category = "gen"
    default_severity = Severity.WARNING
    description = "Sampled generation has a declared random seed."
    fix_hint = "Set generation.seed in reprollm.yaml when sampling is enabled."

    def applies(self, ctx: AuditContext) -> bool:
        generation = ctx.manifest.generation if ctx.manifest is not None else None
        return generation is not None and (
            generation.do_sample is True
            or (generation.temperature is not None and generation.temperature > 0)
        )

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None and ctx.manifest.generation is not None
        return [self.field_result(ctx, "generation.seed", ctx.manifest.generation.seed is not None)]


@register_rule
class BackendDeclaredRule(PresenceRule):
    id = "gen.backend_declared"
    category = "gen"
    default_severity = Severity.WARNING
    description = "The inference backend is declared."
    fix_hint = "Set inference.backend in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        inference = ctx.manifest.inference
        return [
            self.field_result(
                ctx, "inference.backend", inference is not None and inference.backend is not None
            )
        ]


@register_rule
class BackendConfigDeclaredRule(PresenceRule):
    id = "gen.backend_config_declared"
    category = "gen"
    default_severity = Severity.WARNING
    description = "The vLLM backend configuration is declared."
    fix_hint = (
        "Set inference.dtype, inference.tensor_parallel_size, inference.quantization "
        "and inference.gpu_memory_utilization in reprollm.yaml."
    )

    def applies(self, ctx: AuditContext) -> bool:
        inference = ctx.manifest.inference if ctx.manifest is not None else None
        return inference is not None and inference.backend == "vllm"

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None and ctx.manifest.inference is not None
        return [
            self.field_result(
                ctx, f"inference.{field}", getattr(ctx.manifest.inference, field) is not None
            )
            for field in ("dtype", "gpu_memory_utilization", "quantization", "tensor_parallel_size")
        ]


@register_rule
class StopDeclaredRule(PresenceRule):
    id = "gen.stop_declared"
    category = "gen"
    default_severity = Severity.INFO
    description = "Generation stop sequences are explicitly declared."
    fix_hint = "Set generation.stop in reprollm.yaml; use [] when no stop sequences are needed."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        generation = ctx.manifest.generation
        return [
            self.field_result(
                ctx, "generation.stop", generation is not None and generation.stop is not None
            )
        ]
