"""Dataset declarations (spec §12.5, M3-T02)."""

from __future__ import annotations

from typing import ClassVar

from reprollm.core.context import AuditContext
from reprollm.core.registry import register_rule
from reprollm.rules._presence import PresenceRule
from reprollm.rules._stubs import LevelTwoStubRule
from reprollm.schemas.finding import Finding, Severity


@register_rule
class RevisionPinnedRule(LevelTwoStubRule):
    id = "dataset.revision_pinned"
    category = "dataset"
    default_severity = Severity.WARNING
    description = "Every Hugging Face dataset has an exact resolved revision."
    fix_hint = "Run `reprollm lock` to resolve datasets.<role>.revision in reprollm.lock."


@register_rule
class LocalFilesHashedRule(LevelTwoStubRule):
    id = "dataset.local_files_hashed"
    category = "dataset"
    default_severity = Severity.CRITICAL
    description = "Every declared local dataset file has a recorded hash."
    fix_hint = "Run `reprollm lock` to hash datasets.<role>.files in reprollm.lock."


@register_rule
class DeclaredRule(PresenceRule):
    id = "dataset.declared"
    category = "dataset"
    default_severity = Severity.INFO
    description = "At least one dataset role is declared."
    fix_hint = "Declare datasets.<role> in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        return [self.field_result(ctx, "datasets", bool(ctx.manifest.datasets))]


class _DatasetRule(PresenceRule):
    category = "dataset"

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.manifest is not None and bool(ctx.manifest.datasets)


class _HfFieldRule(_DatasetRule):
    field: ClassVar[str]

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        return [
            self.field_result(
                ctx, f"datasets.{role}.{self.field}", getattr(dataset, self.field) is not None
            )
            if dataset.provider == "huggingface"
            else self.skipped_field(
                ctx, f"datasets.{role}.{self.field}", "only required for Hugging Face datasets"
            )
            for role, dataset in sorted(ctx.manifest.datasets.items())
        ]


@register_rule
class SplitDeclaredRule(_HfFieldRule):
    id = "dataset.split_declared"
    field = "split"
    default_severity = Severity.WARNING
    description = "Every Hugging Face dataset has a declared split."
    fix_hint = "Set datasets.<role>.split in reprollm.yaml."


@register_rule
class SubsetDeclaredRule(_HfFieldRule):
    id = "dataset.subset_declared"
    field = "subset"
    default_severity = Severity.INFO
    description = "Every Hugging Face dataset has a declared subset."
    fix_hint = "Set datasets.<role>.subset in reprollm.yaml."


@register_rule
class PreprocessingDeclaredRule(_DatasetRule):
    id = "dataset.preprocessing_declared"
    default_severity = Severity.WARNING
    description = "Every dataset has declared preprocessing."
    fix_hint = "Set datasets.<role>.preprocessing in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        return [
            self.field_result(
                ctx, f"datasets.{role}.preprocessing", dataset.preprocessing is not None
            )
            for role, dataset in sorted(ctx.manifest.datasets.items())
        ]


@register_rule
class SamplingSeedDeclaredRule(_DatasetRule):
    id = "dataset.sampling_seed_declared"
    default_severity = Severity.WARNING
    description = "Every dataset with a sample count has a sampling seed."
    fix_hint = "Set datasets.<role>.sampling.seed in reprollm.yaml."

    def check(self, ctx: AuditContext) -> list[Finding]:
        assert ctx.manifest is not None
        findings: list[Finding] = []
        for role, dataset in sorted(ctx.manifest.datasets.items()):
            field = f"datasets.{role}.sampling.seed"
            sampling = dataset.sampling
            if sampling is None or sampling.n is None:
                findings.append(self.skipped_field(ctx, field, "no sampling.n is declared"))
            else:
                findings.append(self.field_result(ctx, field, sampling.seed is not None))
        return findings
