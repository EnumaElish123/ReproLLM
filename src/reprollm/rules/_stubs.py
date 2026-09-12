"""Metadata-only Level 2 placeholders selected by profiles during M3-T06."""

from __future__ import annotations

from reprollm.core.context import AuditContext
from reprollm.core.registry import Rule
from reprollm.schemas.finding import Finding


class LevelTwoStubRule(Rule):
    """The engine skips these rules until their owning milestone implements them."""

    min_level = 2
    stub = True

    def check(self, ctx: AuditContext) -> list[Finding]:
        return []
