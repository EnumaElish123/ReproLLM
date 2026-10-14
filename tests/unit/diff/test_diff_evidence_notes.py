"""Diff scopes recorded environment and input evidence (R04-A, spec §18)."""

from __future__ import annotations

import pytest

from reprollm.diff.differ import diff_states
from reprollm.diff.severity import SeverityResolver
from reprollm.reporters.diff_text import render_diff_text
from reprollm.schemas.state import EvidenceContext, Leaf, State


def test_changed_recorder_packages_keep_severity_and_report_capture_scope() -> None:
    before = State.from_flat(
        {
            "environment.packages.torch": Leaf(
                value="2.5.1",
                source="lock",
                confidence="declared",
                context=EvidenceContext(subject="recorder", phase="lock_resolution"),
            )
        }
    )
    after = State.from_flat(
        {
            "environment.packages.torch": Leaf(
                value="2.6.0",
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="recorder", phase="post_child"),
            )
        }
    )
    report = diff_states(before, after, SeverityResolver())
    assert len(report.changes) == 1
    assert report.changes[0].severity == "MEDIUM_HIGH"
    assert report.changes[0].note == (
        "a: recorder/lock_resolution; child unverified; b: recorder/post_child; child unverified"
    )


def test_self_diff_compares_recorded_values_without_verifying_child() -> None:
    recorded = State.from_flat(
        {
            "run_id": Leaf(value="20261014T000000Z-aaaaaa", source="run", confidence="observed"),
            "generation.temperature": Leaf(
                value=0.1,
                source="run",
                confidence="observed",
                detail="config:config.json:temperature",
                context=EvidenceContext(subject="input_file", phase="pre_child"),
            ),
        }
    )
    report = diff_states(recorded, recorded, SeverityResolver())
    assert report.changes == [] and report.summary.same == 2
    text = render_diff_text(report)
    assert "No reproducibility-relevant drift in recorded values." in text
    assert "Child environment and input consumption are unverified." in text


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        ("environment.python", None),
        ("hardware.driver", None),
        ("files.config.json.sha256", None),
        ("generation.temperature", "config:config.json:temperature"),
    ],
)
def test_missing_legacy_context_stays_unknown_in_changed_evidence(
    path: str, detail: str | None
) -> None:
    before = State.from_flat(
        {path: Leaf(value="1", source="run", confidence="observed", detail=detail)}
    )
    after = State.from_flat(
        {path: Leaf(value="2", source="run", confidence="observed", detail=detail)}
    )
    report = diff_states(before, after, SeverityResolver())
    assert len(report.changes) == 1
    assert report.changes[0].note == (
        "a: unknown/unknown; child unverified; b: unknown/unknown; child unverified"
    )


def test_context_changes_do_not_add_experimental_drift() -> None:
    before = State.from_flat(
        {
            "environment.python": Leaf(
                value="3.12.14",
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="unknown", phase="unknown"),
            )
        }
    )
    after = State.from_flat(
        {
            "environment.python": Leaf(
                value="3.12.14",
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="recorder", phase="post_child"),
            )
        }
    )
    report = diff_states(before, after, SeverityResolver())
    assert report.changes == []
    assert report.summary.same == 1 and report.summary.highest == "NONE"
    assert sum(report.summary.counts.values()) == 0


def test_legacy_input_and_new_baseline_are_compared_as_qualified_values() -> None:
    before = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=0.9,
                source="run",
                detail="config:config.json:temperature",
                confidence="observed",
                context=EvidenceContext(subject="input_file", phase="unknown"),
            )
        }
    )
    after = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=0.1,
                source="run",
                detail="config:config.json:temperature",
                confidence="observed",
                context=EvidenceContext(subject="input_file", phase="pre_child"),
            )
        }
    )
    report = diff_states(before, after, SeverityResolver())
    change = report.changes[0]
    assert (change.a, change.b, change.severity) == (0.9, 0.1, "HIGH")
    assert change.note == (
        "a: input_file/unknown; child unverified; b: input_file/pre_child; child unverified"
    )
    assert report.summary.counts["HIGH"] == 1


@pytest.mark.parametrize("added", [True, False])
def test_absent_side_does_not_invent_capture_context(added: bool) -> None:
    populated = State.from_flat(
        {
            "environment.env.OMP_NUM_THREADS": Leaf(
                value="2",
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="inherited_environment", phase="pre_child"),
            )
        }
    )
    report = diff_states(
        State() if added else populated,
        populated if added else State(),
        SeverityResolver(),
    )
    change = report.changes[0]
    assert change.status == ("added" if added else "removed")
    assert change.note == (
        "b: inherited_environment/pre_child; child unverified"
        if added
        else "a: inherited_environment/pre_child; child unverified"
    )


def test_source_conflict_note_is_retained_beside_input_context() -> None:
    before = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=0.1,
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="input_file", phase="pre_child"),
                alternatives=[Leaf(value=0.0, source="manifest", confidence="declared")],
            )
        }
    )
    after = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=0.2,
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="input_file", phase="pre_child"),
            )
        }
    )
    report = diff_states(before, after, SeverityResolver())
    assert len(report.changes) == 1 and report.changes[0].severity == "HIGH"
    assert report.changes[0].note == (
        "a has inconsistent sources (see audit); a: input_file/pre_child; child unverified; "
        "b: input_file/pre_child; child unverified"
    )


@pytest.mark.security
def test_context_note_does_not_echo_arbitrary_location_detail() -> None:
    detail = "config:/private/synthetic-host/api_key=syntheticScopeCanaryABC123"
    before = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=0.1, source="run", confidence="observed", detail=detail
            )
        }
    )
    after = State.from_flat(
        {
            "generation.temperature": Leaf(
                value=0.2, source="run", confidence="observed", detail=detail
            )
        }
    )
    report = diff_states(before, after, SeverityResolver())
    assert report.changes[0].note == (
        "a: unknown/unknown; child unverified; b: unknown/unknown; child unverified"
    )
    assert "syntheticScopeCanaryABC123" not in report.model_dump_json()
    assert "/private/" not in report.model_dump_json()


def test_unscoped_declaration_does_not_receive_invented_context() -> None:
    before = State.from_flat(
        {"models.primary.id": Leaf(value="old", source="manifest", confidence="declared")}
    )
    after = State.from_flat(
        {"models.primary.id": Leaf(value="new", source="manifest", confidence="declared")}
    )
    assert diff_states(before, after, SeverityResolver()).changes[0].note is None


def test_context_note_survives_state_json_round_trip_without_schema_extension() -> None:
    before = State.from_flat(
        {
            "environment.python": Leaf(
                value="3.10.21",
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="recorder", phase="post_child"),
            )
        }
    )
    after = State.from_flat(
        {
            "environment.python": Leaf(
                value="3.12.14",
                source="run",
                confidence="observed",
                context=EvidenceContext(subject="recorder", phase="post_child"),
            )
        }
    )
    original = diff_states(before, after, SeverityResolver())
    restored = diff_states(
        State.model_validate_json(before.model_dump_json()),
        State.model_validate_json(after.model_dump_json()),
        SeverityResolver(),
    )
    assert restored.model_dump_json() == original.model_dump_json()
    assert set(restored.model_dump()["changes"][0]) == {
        "path",
        "status",
        "a",
        "b",
        "severity",
        "note",
    }


def test_filtered_text_keeps_highest_verdict_and_verification_limit() -> None:
    before = State.from_flat(
        {"generation.temperature": Leaf(value=0.1, source="run", confidence="observed")}
    )
    after = State.from_flat(
        {"generation.temperature": Leaf(value=0.2, source="run", confidence="observed")}
    )
    report = diff_states(before, after, SeverityResolver())
    report.filtered_below = "HIGH"
    report.changes = []
    text = render_diff_text(report)
    assert "Highest drift: HIGH (1 changes). These runs are not directly comparable." in text
    assert "Showing HIGH and above; summary includes all changes." in text
    assert "Child environment and input consumption are unverified." in text
