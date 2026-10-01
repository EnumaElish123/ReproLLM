"""Candidate post-processing (spec §20.4, M7-T04).

Deterministic and defensive: evidence whose path is not among the collected
inputs lowers the candidate's confidence to ``low`` instead of being trusted.
"""

from __future__ import annotations

from datetime import datetime

from reprollm.schemas.discover_candidates import (
    Candidate,
    DiscoverCandidates,
    candidate_id,
)


def finalize(
    raw_candidates: list[Candidate],
    *,
    model: str,
    reprollm_version: str,
    input_files: list[str],
    dropped_files: list[str],
    truncated_files: list[str],
    generated_at: datetime,
) -> DiscoverCandidates:
    from datetime import timezone

    allowed = {_strip_locator(path) for path in input_files}
    finalized: list[Candidate] = []
    for raw in raw_candidates:
        evidence = [
            item.model_copy(update={"path": _strip_locator(item.path)}) for item in raw.evidence
        ]
        trustable = all(
            item.path is None or _strip_locator(item.path) in allowed for item in evidence
        )
        confidence = raw.confidence if trustable else "low"
        first_path = next((item.path for item in evidence if item.path), None)
        evidence = [item for item in evidence if item.path is None or item.path in allowed]
        finalized.append(
            raw.model_copy(
                update={
                    "id": candidate_id(raw.kind, raw.name, first_path),
                    "confidence": confidence,
                    "evidence": evidence,
                }
            )
        )
    finalized.sort(key=lambda c: (c.kind, c.name, c.id))
    return DiscoverCandidates(
        reprollm_version=reprollm_version,
        generated_at=generated_at.replace(tzinfo=timezone.utc, microsecond=0),
        model=model,
        input_files=sorted(input_files),
        dropped_files=sorted(dropped_files),
        truncated_files=sorted(truncated_files),
        candidates=finalized,
    )


def _strip_locator(path: str | None) -> str | None:
    """Snippets carry ``path#L12`` locators; evidence compares bare paths."""
    if path is None:
        return None
    return path.split("#L", 1)[0]
