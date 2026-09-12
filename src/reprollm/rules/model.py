"""Model identity declarations (spec §12.4, M3-T01)."""

from __future__ import annotations

from typing import ClassVar

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.schemas.finding import Evidence, Finding, Severity

_API_PROVIDERS = frozenset({"openai", "openrouter", "anthropic"})


@register_rule
class PrimaryDeclaredRule(PresenceRule):
    id = "model.primary_declared"
    category = "model"
    default_severity = Severity.CRITICAL
    description = "The primary model identity is declared."
    fix_hint = "Set models.primary.id in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        model = ctx.manifest.models.get("primary")
        return [
            self.field_result(ctx, "models.primary.id", model is not None and model.id is not None)
        ]


@register_rule
class ProviderKnownRule(PresenceRule):
    id = "model.provider_known"
    category = "model"
    default_severity = Severity.WARNING
    description = "Every model uses a known provider."
    fix_hint = "Set models.<role>.provider to a supported provider in reprollm.yaml."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and bool(ctx.manifest.models)

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        findings: list[Finding] = []
        for role, model in sorted(ctx.manifest.models.items()):
            field = f"models.{role}.provider"
            if model.provider is None:
                findings.append(self.skipped_field(ctx, field, "provider is not declared"))
                continue
            finding = self.field_result(
                ctx,
                field,
                model.provider != "other",
                message=f"models.{role}.provider is "
                + (
                    "'other'; provider-specific resolution is unavailable"
                    if model.provider == "other"
                    else "a known provider"
                ),
            )
            if model.provider == "other":
                finding.evidence[0].note = "unsupported provider"
            findings.append(finding)
        return findings


class _ModelInferenceField(PresenceRule):
    category = "model"
    field: ClassVar[str]

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and bool(ctx.manifest.models)

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        inference = ctx.manifest.inference
        fallback = getattr(inference, self.field) if inference is not None else None
        findings: list[Finding] = []
        for role, model in sorted(ctx.manifest.models.items()):
            field = f"models.{role}.{self.field}"
            if model.provider in _API_PROVIDERS:
                findings.append(self.skipped_field(ctx, field, "not required for API models"))
                continue
            value = getattr(model, self.field)
            source = f"inference.{self.field}" if value is None and fallback is not None else None
            findings.append(
                self.field_result(
                    ctx, field, value is not None or fallback is not None, source=source
                )
            )
        return findings


@register_rule
class DtypeDeclaredRule(_ModelInferenceField):
    id = "model.dtype_declared"
    field = "dtype"
    default_severity = Severity.WARNING
    description = "Every non-API model has a declared dtype."
    fix_hint = "Set models.<role>.dtype or inference.dtype in reprollm.yaml."


@register_rule
class QuantizationDeclaredRule(_ModelInferenceField):
    id = "model.quantization_declared"
    field = "quantization"
    default_severity = Severity.INFO
    description = "Every non-API model has declared quantization."
    fix_hint = "Set models.<role>.quantization or inference.quantization in reprollm.yaml."


@register_rule
class AdapterDeclaredRule(PresenceRule):
    id = "model.adapter_declared"
    category = "model"
    default_severity = Severity.WARNING
    description = "The detected adapter is declared on a model."
    fix_hint = "Set models.<role>.adapter in reprollm.yaml to describe the detected adapter."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and ctx.detection.hints.adapter

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        if any(model.adapter is not None for model in ctx.manifest.models.values()):
            return []
        return [
            self.finding(
                ctx,
                message="models has no adapter declaration despite detected adapter use",
                evidence=[
                    Evidence(kind="field", field=f"models.{role}.adapter", note="absent")
                    for role in sorted(ctx.manifest.models)
                ]
                or [Evidence(kind="field", field="models", note="empty")],
            )
        ]


@register_rule
class TrustRemoteCodeDeclaredRule(PresenceRule):
    id = "model.trust_remote_code_declared"
    category = "model"
    default_severity = Severity.WARNING
    description = "Detected remote-code trust is explicitly declared."
    fix_hint = "Set models.<role>.trust_remote_code: true in reprollm.yaml for the relevant model."

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and ctx.detection.hints.trust_remote_code

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        if any(model.trust_remote_code is True for model in ctx.manifest.models.values()):
            return []
        return [
            self.finding(
                ctx,
                message="models has no trust_remote_code: true declaration despite detected use",
                evidence=[
                    Evidence(
                        kind="field",
                        field=f"models.{role}.trust_remote_code",
                        note="not declared true",
                    )
                    for role in sorted(ctx.manifest.models)
                ]
                or [Evidence(kind="field", field="models", note="empty")],
            )
        ]
