"""Compare effective values; preserve audit-only disagreements as notes (§18)."""

from __future__ import annotations

from reprollm import __version__
from reprollm.core.bindings import values_equal
from reprollm.diff.severity import SEVERITIES, SeverityResolver
from reprollm.schemas.diff_report import DiffChange, DiffReport, DiffSource, DiffSummary
from reprollm.schemas.profile import DriftSeverity
from reprollm.schemas.state import Leaf, State

SECTION_ORDER = (
    "models",
    "datasets",
    "prompts",
    "files",
    "generation",
    "inference",
    "training",
    "evaluation",
    "privacy",
    "custom",
    "code",
    "environment",
    "hardware",
    "command",
    "execution",
)


def section_rank(path: str) -> tuple[int, str]:
    section = path.split(".", 1)[0]
    return (
        SECTION_ORDER.index(section) if section in SECTION_ORDER else len(SECTION_ORDER),
        section,
    )


def _inconsistent(leaf: Leaf) -> bool:
    return any(
        not values_equal(leaf.value, item.value) or _inconsistent(item)
        for item in leaf.alternatives
    )


def _source(state: State) -> DiffSource:
    if state.run_id is not None:
        return DiffSource(kind="run", ref=str(state.run_id.value))
    return DiffSource(kind="lock", ref="reprollm.lock")


def diff_states(a: State, b: State, resolver: SeverityResolver) -> DiffReport:
    left, right = a.flatten(), b.flatten()
    changes: list[DiffChange] = []
    same = 0
    counts: dict[DriftSeverity, int] = {severity: 0 for severity in reversed(SEVERITIES)}
    dirty_a = "code.dirty" in left and left["code.dirty"].value is True
    dirty_b = "code.dirty" in right and right["code.dirty"].value is True
    for path in sorted(left.keys() | right.keys()):
        before, after = left.get(path), right.get(path)
        if before is not None and after is not None and values_equal(before.value, after.value):
            same += 1
            continue
        a_value = before.value if before is not None else None
        b_value = after.value if after is not None else None
        resolution = resolver.resolve(path, a_value, b_value, dirty_a=dirty_a, dirty_b=dirty_b)
        notes = [resolution.note] if resolution.note else []
        for side, leaf in (("a", before), ("b", after)):
            if leaf is not None and _inconsistent(leaf):
                notes.append(f"{side} has inconsistent sources (see audit)")
        changes.append(
            DiffChange(
                path=path,
                status="added" if before is None else "removed" if after is None else "changed",
                a=a_value,
                b=b_value,
                severity=resolution.severity,
                note="; ".join(notes) or None,
            )
        )
        counts[resolution.severity] += 1
    changes.sort(
        key=lambda item: (-SEVERITIES.index(item.severity), section_rank(item.path), item.path)
    )
    highest = next((severity for severity in reversed(SEVERITIES) if counts[severity]), "NONE")
    return DiffReport(
        reprollm_version=__version__,
        a=_source(a),
        b=_source(b),
        changes=changes,
        summary=DiffSummary(highest=highest, counts=counts, same=same),
    )
