"""Checklist mappings must describe actual merged values and rendered evidence."""

from __future__ import annotations

import pytest

from reprollm.export.exporter import build_input, enrich_for_checklist, render_checklist_mapping
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.state import Leaf, State


@pytest.fixture
def manifest() -> Manifest:
    return Manifest.model_validate(
        {
            "schema_version": 1,
            "project": {"name": "fake-checklist"},
            "experiment": {"profiles": ["llm_judge", "privacy"]},
            "models": {"grader": {"provider": "openai", "id": "fake-grader"}},
            "datasets": {"eval": {"provider": "local", "id": "data", "split": "heldout"}},
            "prompts": {"judge": {"text": "Fake rubric.", "format": "plain"}},
            "generation": {"seed": 7},
            "evaluation": {
                "metrics": [{"name": "accuracy", "implementation": "score.py"}],
                "repetitions": 3,
                "judge": {"model_ref": "grader", "prompt_ref": "judge"},
            },
            "privacy": {
                "threat_model": "Declared observer.",
                "mechanism": {"name": "declared-mechanism"},
            },
        }
    )


def _mapping(manifest: Manifest, venue: str, state: State | None = None) -> str:
    data = build_input(
        manifest, None, None, state or State.from_manifest(manifest), reprollm_version="0.6.1"
    )
    enrich_for_checklist(data, manifest, None)
    return render_checklist_mapping(data, venue=venue)


def _line(document: str, text: str) -> str:
    return next(line for line in document.splitlines() if text in line)


def test_declared_dataset_split_is_not_labeled_missing(manifest: Manifest) -> None:
    mapping = _mapping(manifest, "neurips")
    assert "split: heldout" in _line(mapping, "Datasets / splits")


def test_repetitions_comes_from_evaluation_not_seed(manifest: Manifest) -> None:
    line = _line(_mapping(manifest, "neurips"), "Hyperparameters / runs")
    assert "repetitions: 3" in line
    assert "repetitions: 7" not in line


def test_judge_identity_uses_referenced_role(manifest: Manifest) -> None:
    line = _line(_mapping(manifest, "neurips"), "LLM judge")
    assert "models.grader" in line
    assert "models.judge" not in line


def test_privacy_mapping_supplies_values_without_nonexistent_section(manifest: Manifest) -> None:
    line = _line(_mapping(manifest, "neurips"), "Attack/defense")
    assert "Declared observer." in line
    assert "declared-mechanism" in line
    assert "Privacy section above" not in line


def test_acl_metrics_and_split_are_present_in_mapping(manifest: Manifest) -> None:
    line = _line(_mapping(manifest, "acl"), "C1 Tasks and evaluation")
    assert "accuracy" in line
    assert "heldout" in line
    assert "Metrics listed above" not in line


def test_acl_does_not_claim_details_absent_from_default_tables(manifest: Manifest) -> None:
    mapping = _mapping(manifest, "acl")
    assert "preprocessing" not in _line(mapping, "B6 Data usage")
    assert "dtype" not in _line(mapping, "B9 Model / LLM details")
    assert "quantization" not in _line(mapping, "B9 Model / LLM details")
    assert "adapter" not in _line(mapping, "B9 Model / LLM details")
    assert "few-shot" not in _line(mapping, "C3 Prompt details")
    assert "format:" in _line(mapping, "C3 Prompt details")


@pytest.mark.parametrize("venue", ["neurips", "acl"])
def test_metrics_summary_respects_effective_state(manifest: Manifest, venue: str) -> None:
    flat = State.from_manifest(manifest).flatten()
    flat["evaluation.metrics"] = Leaf(
        value=[{"name": "observed-score", "implementation": "score.py"}],
        source="run",
        confidence="observed",
    )
    state = State.from_flat(flat)
    mapping = _mapping(manifest, venue, state)
    line = _line(mapping, "Evaluation metrics / protocol" if venue == "neurips" else "C1 Tasks")
    assert "observed-score" in line
    assert "accuracy" not in line


def test_protocol_and_privacy_values_respect_effective_state(manifest: Manifest) -> None:
    flat = State.from_manifest(manifest).flatten()
    for path, value in {
        "evaluation.repetitions": 5,
        "datasets.eval.split": "observed-split",
        "evaluation.judge.model_ref": "primary",
        "models.primary.id": "observed-judge",
        "privacy.threat_model": "Observed observer.",
        "privacy.mechanism.name": "observed-mechanism",
    }.items():
        flat[path] = Leaf(value=value, source="run", confidence="observed")
    mapping = _mapping(manifest, "neurips", State.from_flat(flat))
    assert "repetitions: 5" in _line(mapping, "Hyperparameters / runs")
    assert "split: observed-split" in _line(mapping, "Datasets / splits")
    assert "models.primary" in _line(mapping, "LLM judge")
    assert "observed-judge" in _line(mapping, "LLM judge")
    privacy = _line(mapping, "Attack/defense")
    assert "Observed observer." in privacy and "observed-mechanism" in privacy


@pytest.mark.parametrize(
    "observed_metrics", [1, 1.5, False, None, "unavailable", {"name": "value"}]
)
def test_non_list_observed_metrics_do_not_crash_or_reuse_manifest(
    manifest: Manifest, observed_metrics: object
) -> None:
    flat = State.from_manifest(manifest).flatten()
    flat["evaluation.metrics"] = Leaf(value=observed_metrics, source="run", confidence="observed")
    mapping = _mapping(manifest, "neurips", State.from_flat(flat))
    metrics = _line(mapping, "Evaluation metrics / protocol")
    assert "Metrics: not declared" in metrics
    assert "accuracy" not in metrics


def test_empty_effective_metric_list_does_not_reuse_manifest(manifest: Manifest) -> None:
    flat = State.from_manifest(manifest).flatten()
    flat["evaluation.metrics"] = Leaf(value=[], source="run", confidence="observed")
    metrics = _line(_mapping(manifest, "acl", State.from_flat(flat)), "C1 Tasks")
    assert "Metrics: not declared" in metrics
    assert "accuracy" not in metrics


@pytest.mark.parametrize("evaluation", [None, {"metrics": []}])
def test_absent_judge_configuration_is_explicitly_not_covered(
    manifest: Manifest, evaluation: dict[str, object] | None
) -> None:
    content = manifest.model_dump(mode="json")
    content["evaluation"] = evaluation
    content["privacy"] = None
    mapping = _mapping(Manifest.model_validate(content), "neurips")
    assert "*not covered* (no judge configuration)" in _line(mapping, "LLM judge")
    assert "*not covered* (no privacy configuration)" in _line(mapping, "Attack/defense")


def test_new_inline_privacy_evidence_uses_existing_redaction_gate(manifest: Manifest) -> None:
    fake_key = "sk-" + "a" * 40
    flat = State.from_manifest(manifest).flatten()
    flat["privacy.threat_model"] = Leaf(
        value=f"Fake validation credential: {fake_key}", source="run", confidence="observed"
    )
    mapping = _mapping(manifest, "neurips", State.from_flat(flat))
    privacy = _line(mapping, "Attack/defense")
    assert fake_key not in privacy
    assert "<REDACTED:openai>" in privacy


def test_effective_metric_list_uses_only_named_metric_objects(manifest: Manifest) -> None:
    flat = State.from_manifest(manifest).flatten()
    flat["evaluation.metrics"] = Leaf(
        value=[
            "item",
            1,
            None,
            {},
            {"name": None},
            {"name": 7},
            {"name": {"value": 1}},
            {"name": "observed-score"},
        ],
        source="run",
        confidence="observed",
    )
    metrics = _line(
        _mapping(manifest, "neurips", State.from_flat(flat)), "Evaluation metrics / protocol"
    )
    assert (
        metrics == "| 4.1–4.3 Evaluation metrics / protocol | Metrics: observed-score; "
        "generation parameters above |"
    )
