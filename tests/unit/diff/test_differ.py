"""M6-T03 semantic comparisons, ordering, summary and alternative-source notes."""

from __future__ import annotations

from reprollm.diff.differ import diff_states
from reprollm.diff.severity import SeverityResolver
from reprollm.schemas.state import Leaf, State


def state(values: dict) -> State:
    return State.from_flat(
        {
            key: Leaf(value=value, source="run", confidence="observed")
            for key, value in values.items()
        }
    )


def test_statuses_and_normalized_equality() -> None:
    a = state(
        {
            "generation.seed": "42",
            "generation.temperature": 0.0,
            "models.primary.id": "old",
            "code.branch": "main",
            "custom.null": None,
        }
    )
    b = state(
        {
            "generation.seed": 42,
            "generation.temperature": 0.7,
            "models.judge.id": "new",
            "code.branch": "main",
        }
    )
    report = diff_states(a, b, SeverityResolver())
    changes = {change.path: change for change in report.changes}
    assert set(changes) == {
        "generation.temperature",
        "models.primary.id",
        "models.judge.id",
        "custom.null",
    }
    assert changes["generation.temperature"].status == "changed"
    assert (changes["models.primary.id"].status, changes["models.primary.id"].b) == (
        "removed",
        None,
    )
    assert (changes["models.judge.id"].status, changes["models.judge.id"].a) == ("added", None)
    assert changes["custom.null"].status == "removed"  # present null differs from absence
    assert report.summary.same == 2
    assert report.summary.highest == "HIGH"
    assert report.summary.counts == {"HIGH": 3, "MEDIUM_HIGH": 0, "MEDIUM": 1, "LOW": 0, "NONE": 0}


def test_severity_then_section_then_path_order() -> None:
    values = {
        "generation.top_p": 0.5,
        "generation.temperature": 0.1,
        "models.primary.id": "id",
        "datasets.eval.id": "data",
        "prompts.system.sha256": "h",
        "files.a.b/c.yaml.sha256": "h",
        "hardware.driver": "old",
        "run_id": "old",
        "code.commit": "old",
        "environment.packages.torch": "2.8.0",
    }
    a = state(dict(reversed(list(values.items()))))
    b = state({key: "new" for key in values})
    report = diff_states(a, b, SeverityResolver())
    assert [change.path for change in report.changes] == [
        "models.primary.id",
        "datasets.eval.id",
        "prompts.system.sha256",
        "files.a.b/c.yaml.sha256",
        "generation.temperature",
        "generation.top_p",
        "environment.packages.torch",
        "code.commit",
        "hardware.driver",
        "run_id",
    ]
    assert (
        report.model_dump_json()
        == diff_states(state(values), b, SeverityResolver()).model_dump_json()
    )


def test_alternatives_are_notes_only_and_never_extra_changes() -> None:
    a = state({"generation.temperature": 0.7, "generation.seed": 42})
    b = state({"generation.temperature": 0.9, "generation.seed": 42})
    a.flatten()["generation.temperature"].alternatives = [
        Leaf(value=0.0, source="manifest", confidence="declared")
    ]
    b.flatten()["generation.temperature"].alternatives = [
        Leaf(value="0.9", source="lock", confidence="declared")
    ]
    b.flatten()["generation.seed"].alternatives = [
        Leaf(value=999, source="manifest", confidence="declared")
    ]
    report = diff_states(a, b, SeverityResolver())
    assert len(report.changes) == 1
    assert report.changes[0].note == "a has inconsistent sources (see audit)"
    assert report.summary.same == 1
    b.flatten()["generation.temperature"].alternatives[0].value = 0.1
    assert diff_states(a, b, SeverityResolver()).changes[0].note == (
        "a has inconsistent sources (see audit); b has inconsistent sources (see audit)"
    )


def test_dirty_note_composes_with_inconsistent_sources() -> None:
    a = state({"code.commit": "a", "code.dirty": True})
    b = state({"code.commit": "b", "code.dirty": False})
    a.flatten()["code.commit"].alternatives = [
        Leaf(value="other", source="lock", confidence="declared")
    ]
    report = diff_states(a, b, SeverityResolver())
    change = next(change for change in report.changes if change.path == "code.commit")
    assert change.severity == "HIGH"
    assert change.note == "working tree was dirty on a; a has inconsistent sources (see audit)"


def test_identical_empty_and_none_only_states() -> None:
    for a in (State(), state({"generation.seed": 42})):
        report = diff_states(a, a, SeverityResolver())
        assert report.summary.highest == "NONE" and report.changes == []
        assert report.summary.same == len(a.flatten())
    report = diff_states(state({"run_id": "a"}), state({"run_id": "b"}), SeverityResolver())
    assert report.summary.highest == "NONE" and report.summary.counts["NONE"] == 1


def test_missing_boolean_and_list_values_do_not_coerce_incorrectly() -> None:
    a = state({"custom.value": True, "generation.stop": ["1", "false"]})
    b = state({"custom.value": 1, "generation.stop": [1, False]})
    report = diff_states(a, b, SeverityResolver())
    assert [change.path for change in report.changes] == ["custom.value"]
    assert report.summary.same == 1
