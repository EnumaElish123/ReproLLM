"""Rule registry (D-07): ``@register_rule`` classes with stable IDs (D-08)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from reprollm.core.errors import InternalError
from reprollm.schemas.finding import Evidence, Finding, FindingStatus, Severity

if TYPE_CHECKING:
    # Type-only import: keeps the registry importable from context's graph.
    from reprollm.core.context import AuditContext

#: ``<category>.<snake_name>`` (D-08); category must match the prefix.
_RULE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class Rule:
    """Base class for deterministic audit rules.

    ``check`` returns findings for the FAIL case (zero findings ⇒ PASS is
    synthesized by the engine). A rule may emit a severity lower than its
    ``default_severity`` (e.g. provider-specific downgrades); the engine applies
    profile overrides on top (spec §11 step 6).
    """

    id: ClassVar[str]
    category: ClassVar[str]
    default_severity: ClassVar[Severity]
    min_level: ClassVar[int]
    description: ClassVar[str]
    fix_hint: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()

    def applies(self, ctx: AuditContext) -> bool:
        return True

    def skip_reason(self, ctx: AuditContext) -> str | None:
        """Optional human-readable reason shown when the rule is skipped."""
        return None

    def check(self, ctx: AuditContext) -> list[Finding]:  # pragma: no cover - interface
        raise NotImplementedError

    def finding(
        self,
        ctx: AuditContext,
        *,
        message: str,
        evidence: list[Evidence] | None = None,
        severity: Severity | None = None,
    ) -> Finding:
        """Build a FAIL finding for this rule at the context's audit level."""
        level = ctx.level
        return Finding(
            rule_id=self.id,
            aliases=list(self.aliases),
            category=self.category,
            severity=severity or self.default_severity,
            status=FindingStatus.FAIL,
            level=level,
            message=message,
            evidence=evidence or [],
            fix_hint=self.fix_hint,
        )


_REGISTRY: dict[str, type[Rule]] = {}
_ALIASES: dict[str, str] = {}


def register_rule(cls: type[Rule]) -> type[Rule]:
    if not getattr(cls, "id", ""):
        raise InternalError(f"rule {cls.__name__} has no id")
    if not _RULE_ID_RE.match(cls.id):
        raise InternalError(f"rule id {cls.id!r} must be '<category>.<snake_name>'")
    if cls.id.split(".", 1)[0] != cls.category:
        raise InternalError(
            f"rule {cls.id!r} category mismatch: id prefix must equal category {cls.category!r}"
        )
    if cls.id in _REGISTRY:
        raise InternalError(f"duplicate rule id {cls.id!r}")
    for field_name in ("default_severity", "description", "fix_hint"):
        if not getattr(cls, field_name, None):
            raise InternalError(f"rule {cls.id!r} is missing {field_name}")
    _REGISTRY[cls.id] = cls
    for alias in cls.aliases:
        if alias in _ALIASES or alias in _REGISTRY:
            raise InternalError(f"duplicate rule alias {alias!r}")
        _ALIASES[alias] = cls.id
    return cls


def get_rule(id_or_alias: str) -> type[Rule] | None:
    if id_or_alias in _REGISTRY:
        return _REGISTRY[id_or_alias]
    canonical = _ALIASES.get(id_or_alias)
    if canonical is not None:
        return _REGISTRY[canonical]
    return None


def all_rules() -> list[type[Rule]]:
    return [_REGISTRY[key] for key in sorted(_REGISTRY)]


def known_rule_ids() -> set[str]:
    """All IDs plus aliases (used to validate profile rule lists)."""
    return set(_REGISTRY) | set(_ALIASES)
