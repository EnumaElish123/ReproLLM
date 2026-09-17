"""Shared helpers for deterministic Level 2 lock rules."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import Rule
from reprollm.schemas.finding import Evidence, Finding, FindingStatus, Severity
from reprollm.schemas.lock import Provenance
from reprollm.schemas.manifest import PromptSpec


class LockRule(Rule):
    min_level = 2

    def applies(self, ctx: AuditContext) -> bool:
        return ctx.lock is not None

    def skip_reason(self, ctx: AuditContext) -> str:
        return "no lock" if ctx.lock is None else "no applicable locked declarations"

    def passed(
        self,
        ctx: AuditContext,
        *,
        message: str,
        evidence: list[Evidence],
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            aliases=list(self.aliases),
            category=self.category,
            severity=Severity.PASS,
            status=FindingStatus.PASS,
            level=ctx.level,
            message=message,
            evidence=evidence,
            fix_hint=self.fix_hint,
        )


def provenance_evidence(
    field: str,
    provenance: Provenance,
    *,
    expected: object = "confidence: exact",
) -> Evidence:
    """Preserve resolution origin without exposing environment credentials."""
    return Evidence(
        kind="lock",
        field=field,
        value=provenance.value,
        expected=expected,
        note=f"source={provenance.source}; note={provenance.note or 'none'}",
    )


def prompt_hash_field(role: str, prompt: PromptSpec) -> str:
    suffix = "sha256" if prompt.path is not None else "text_sha256"
    return f"prompts.{role}.{suffix}"
