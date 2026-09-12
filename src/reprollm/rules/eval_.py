"""Evaluation declarations (spec §12.8, M3-T04)."""

from __future__ import annotations

import re
from typing import ClassVar

from packaging.version import InvalidVersion, Version
from pydantic import TypeAdapter, ValidationError

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.schemas.finding import Evidence, Finding, Severity
from reprollm.schemas.manifest import RelPath

_REL_PATH = TypeAdapter(RelPath)
_PACKAGE_PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*==([^/\\\s]+)")


def _is_package_pin(value: str) -> bool:
    match = _PACKAGE_PIN.fullmatch(value)
    if match is None:
        return False
    try:
        Version(match.group(1))
    except InvalidVersion:
        return False
    return True


@register_rule
class MetricsDeclaredRule(PresenceRule):
    id = "eval.metrics_declared"
    category = "eval"
    default_severity = Severity.WARNING
    description = "Evaluation metrics are declared."
    fix_hint = "Declare evaluation.metrics in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        evaluation = ctx.manifest.evaluation
        return [
            self.field_result(
                ctx, "evaluation.metrics", evaluation is not None and bool(evaluation.metrics)
            )
        ]


class _MetricsRule(PresenceRule):
    category = "eval"
    default_severity = Severity.WARNING

    def applies(self, ctx: AuditContext) -> bool:
        evaluation = ctx.manifest.evaluation if ctx.manifest is not None else None
        return evaluation is not None and bool(evaluation.metrics)


@register_rule
class MetricImplementationReferencedRule(_MetricsRule):
    id = "eval.metric_implementation_referenced"
    description = "Each metric references its implementation."
    fix_hint = (
        "Set evaluation.metrics.<index>.implementation to a relative file "
        "or pkg==version in reprollm.yaml."
    )

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None and ctx.manifest.evaluation is not None
        findings: list[Finding] = []
        for index, metric in enumerate(ctx.manifest.evaluation.metrics):
            field = f"evaluation.metrics.{index}.implementation"
            reference = metric.implementation
            if reference is None:
                findings.append(self.field_result(ctx, field, False))
                continue
            # §3's declaration grammar is a repository file or pkg==version.
            # Bare-package resolution belongs to the M4 lock contract (§4.3).
            try:
                path = _REL_PATH.validate_python(reference)
                if "://" in path:
                    raise ValueError("URL is not a repository-relative file")
            except (ValidationError, ValueError):
                finding = self.field_result(
                    ctx,
                    field,
                    False,
                    message=f"{field} is not a valid repository-relative file reference",
                )
                finding.evidence[0].note = "invalid repository-relative file reference"
            else:
                exists = ctx.fs.exists(path)
                if not exists and _is_package_pin(reference):
                    finding = self.field_result(ctx, field, True)
                    finding.evidence[0].note = "package reference declared"
                else:
                    finding = self.field_result(
                        ctx,
                        field,
                        exists,
                        message=f"{field}: referenced file {'exists' if exists else 'is missing'}",
                    )
                    finding.evidence[0].note = (
                        "referenced file exists" if exists else "referenced file missing"
                    )
                    finding.evidence.append(Evidence(kind="file", path=path))
            finding.fix_hint = (
                f"Set {field} to an existing relative file or pkg==version in reprollm.yaml."
            )
            findings.append(finding)
        return findings


class _MetricMetadataRule(_MetricsRule):
    field: ClassVar[str]

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None and ctx.manifest.evaluation is not None
        return [
            self.field_result(
                ctx,
                f"evaluation.{self.field}",
                getattr(ctx.manifest.evaluation, self.field) is not None,
            )
        ]


@register_rule
class AggregationDeclaredRule(_MetricMetadataRule):
    id = "eval.aggregation_declared"
    field = "aggregation"
    description = "The metric aggregation method is declared."
    fix_hint = "Set evaluation.aggregation in reprollm.yaml."


@register_rule
class RepetitionsDeclaredRule(_MetricMetadataRule):
    id = "eval.repetitions_declared"
    field = "repetitions"
    description = "The number of evaluation repetitions is declared."
    fix_hint = "Set evaluation.repetitions in reprollm.yaml."


@register_rule
class DefinitionsDeclaredRule(PresenceRule):
    id = "eval.definitions_declared"
    category = "eval"
    default_severity = Severity.WARNING
    description = "Refusal or attack success is defined for safety evaluation."
    fix_hint = "Set evaluation.definitions.refusal or evaluation.definitions.asr in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        evaluation = ctx.manifest.evaluation
        definitions = evaluation.definitions if evaluation is not None else None
        present = definitions is not None and bool({"refusal", "asr"} & definitions.keys())
        finding = self.field_result(
            ctx,
            "evaluation.definitions",
            present,
            message="evaluation.definitions "
            + ("declares refusal or asr" if present else "lacks refusal and asr"),
        )
        finding.evidence[0].note = (
            "refusal or asr declared" if present else "neither refusal nor asr is declared"
        )
        finding.fix_hint = self.fix_hint
        return [finding]


@register_rule
class QueryBudgetDeclaredRule(PresenceRule):
    id = "eval.query_budget_declared"
    category = "eval"
    default_severity = Severity.WARNING
    description = "The evaluation query budget is declared."
    fix_hint = "Set evaluation.query_budget in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        evaluation = ctx.manifest.evaluation
        return [
            self.field_result(
                ctx,
                "evaluation.query_budget",
                evaluation is not None and evaluation.query_budget is not None,
            )
        ]
