"""Retain native binding context until audit findings have made their decisions."""

from __future__ import annotations

import copy
import importlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from reprollm.core.context import AuditContext
    from reprollm.core.registry import Rule
    from reprollm.schemas.finding import Finding
    from reprollm.schemas.state import Leaf

ResultT = TypeVar("ResultT")
DisplaySanitizer = Callable[[Any, list[dict[str, Any]]], Any]


class _BindingFormatter(Protocol):
    def __call__(
        self,
        rule: Rule,
        ctx: AuditContext,
        field: str,
        observations: list[Leaf],
        *,
        locked: Any = None,
        include_lock: bool = False,
    ) -> Finding: ...


class _ConsistencyModule(Protocol):
    _binding_finding: _BindingFormatter


def _field_value(value: Any, field: str, sanitize: DisplaySanitizer) -> Any:
    projected = sanitize(
        {
            "bindings_observed": {
                field: [{"value": value, "source": {"type": "config", "key": field}}]
            }
        },
        [],
    )
    fields = projected["bindings_observed"]
    if len(fields) != 1:
        raise ValueError("private audit declaration projection is incomplete")
    return next(iter(fields.values()))[0]["value"]


def _leaves(leaf: Leaf) -> Iterator[Leaf]:
    yield leaf
    for alternative in leaf.alternatives:
        yield from _leaves(alternative)


def _project_finding(
    formatter: _BindingFormatter,
    rule: Rule,
    ctx: AuditContext,
    field: str,
    observations: list[Leaf],
    sanitize: DisplaySanitizer,
    *,
    locked: Any,
    include_lock: bool,
) -> tuple[Finding, int]:
    from skill_diff_display import project_leaf_value

    from reprollm.core.bindings import values_equal

    # The native callers have already evaluated all raw disagreement conditions.
    raw = formatter(rule, ctx, field, observations, locked=locked, include_lock=include_lock)
    latest = ctx.latest_run
    state = ctx.state
    if latest is None or state is None:
        raise ValueError("private audit source context is unavailable")
    changes = 0
    private_observations = []
    for observation in observations:
        value, changed = project_leaf_value(
            observation.value,
            field,
            observation,
            (latest,),
            sanitize,
        )
        private_observations.append(observation.model_copy(update={"value": value}, deep=True))
        changes += changed

    # Only the formatter reads this isolated declaration view; no rule checks or
    # engine comparisons see redacted values or mutated native source objects.
    private_ctx = copy.copy(ctx)
    private_state = state.model_copy(deep=True)
    primary = private_state.flatten().get(field)
    if primary is not None:
        for leaf in _leaves(primary):
            if leaf.source in {"manifest", "lock"}:
                value = _field_value(leaf.value, field, sanitize)
                changes += not values_equal(value, leaf.value)
                leaf.value = value
    private_ctx.state = private_state
    private_locked = _field_value(locked, field, sanitize) if include_lock else locked
    changes += not values_equal(private_locked, locked)
    if not changes:
        return raw, 0
    rendered = formatter(
        rule,
        private_ctx,
        field,
        private_observations,
        locked=private_locked,
        include_lock=include_lock,
    )
    if rendered.message == raw.message and rendered.evidence == raw.evidence:
        return raw, 0
    # Severity/project overrides, suppression, ordering and summary are still
    # performed by the original engine after this formatter returns.
    return raw.model_copy(
        update={"message": rendered.message, "evidence": rendered.evidence}, deep=True
    ), changes


@contextmanager
def private_binding_reports(sanitize: DisplaySanitizer) -> Iterator[list[dict[str, Any]]]:
    """Privately render bindings for one isolated native audit/export invocation.

    This binding is only a display seam. Native rule checks, State, engine and
    value comparisons remain untouched, and no user file is read or rewritten.
    """
    module = cast(_ConsistencyModule, importlib.import_module("reprollm.rules.consistency"))
    original = module._binding_finding
    diagnostics: list[dict[str, Any]] = []
    total = 0

    def private_finding(
        rule: Rule,
        ctx: AuditContext,
        field: str,
        observations: list[Leaf],
        *,
        locked: Any = None,
        include_lock: bool = False,
    ) -> Finding:
        nonlocal total
        finding, changed = _project_finding(
            original,
            rule,
            ctx,
            field,
            observations,
            sanitize,
            locked=locked,
            include_lock=include_lock,
        )
        total += changed
        return finding

    module._binding_finding = private_finding
    try:
        yield diagnostics
    finally:
        module._binding_finding = original
        if total:
            diagnostics.append({"code": "display_value_transformation", "count": total})


def invoke_private_audit(
    argv: list[str],
    root: Path,
    *,
    invoke_cli: Callable[[list[str], Path], ResultT],
    sanitize: DisplaySanitizer,
) -> tuple[ResultT, list[dict[str, Any]]]:
    """Use original audit rules and every original output renderer exactly once."""
    with private_binding_reports(sanitize) as diagnostics:
        result = invoke_cli(argv, root)
    return result, diagnostics
