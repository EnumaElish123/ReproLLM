"""M6-T01 projection, provenance, precedence and snapshot containment contracts."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from tests.conftest import FIXTURES_ROOT, assert_json_snapshot

from reprollm.core.errors import UserError
from reprollm.core.yaml_io import load_lock, load_manifest
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import Leaf, State

REPOS = FIXTURES_ROOT / "repos"
FIXTURE_NAMES = ("hf_vllm_eval", "openai_judge_eval", "privacy_custom_params")


def saved_run(name: str = "hf_vllm_eval") -> RunRecord:
    data = json.loads((REPOS / name / "expected/run.json").read_text())
    # M5's runtime golden intentionally omits host/clock fields. Supply fixed
    # values here so the State golden exercises those fields on every platform.
    data.update(
        reprollm_version="0.1.1",
        run_id="20261001T100000Z-abcdef",
        started_at="2026-10-01T10:00:00Z",
        ended_at="2026-10-01T10:00:01Z",
        duration_seconds=1.0,
    )
    data.setdefault("environment", {}).update(
        os="Linux",
        python="3.11.9",
        hostname_sha256="sha256:" + "a" * 64,
        packages={"torch": "2.8.0", "vllm": "0.10.0"},
    )
    return RunRecord.model_validate(data)


def snapshot_dir(tmp_path: Path, name: str = "hf_vllm_eval") -> Path:
    folder = tmp_path / name
    folder.mkdir()
    shutil.copyfile(REPOS / name / "manifests/complete.yaml", folder / "manifest.yaml")
    shutil.copyfile(REPOS / name / "expected/lock.yaml", folder / "lock.yaml")
    return folder


def flat_json(state: State) -> dict:
    return {path: leaf.model_dump(mode="json") for path, leaf in state.flatten().items()}


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_three_document_projections(name: str, tmp_path: Path) -> None:
    manifest = load_manifest(REPOS / name / "manifests/complete.yaml")
    lock = load_lock(REPOS / name / "expected/lock.yaml")
    run = saved_run(name)
    run_dir = snapshot_dir(tmp_path, name)
    states = {
        "manifest": State.from_manifest(manifest),
        "lock": State.from_lock(lock),
        "run": State.from_run(run, run_dir=run_dir),
    }
    for state in states.values():
        assert list(state.flatten()) == sorted(state.flatten())
        assert State.model_validate_json(state.model_dump_json()).flatten() == state.flatten()
    assert_json_snapshot(
        {key: flat_json(value) for key, value in states.items()},
        REPOS / name / "expected/state_flat.json",
        ignore=(),
    )


def test_manifest_and_lock_have_distinct_provenance() -> None:
    manifest = State.from_manifest(load_manifest(REPOS / "hf_vllm_eval/manifests/complete.yaml"))
    lock = State.from_lock(load_lock(REPOS / "hf_vllm_eval/expected/lock.yaml"))
    assert manifest.flatten()["generation.temperature"] == Leaf(
        value=0.0, source="manifest", detail=None, confidence="declared"
    )
    revision = lock.flatten()["models.primary.revision"]
    assert revision.source == "lock" and revision.confidence == "exact"
    assert revision.detail == "hf_api" and isinstance(revision.value, str)
    unresolved = lock.flatten()["inference.version"]
    assert unresolved.value is None and unresolved.confidence == "unresolved"
    assert lock.flatten()["environment.python"].value == "3.11.9"
    assert "generated_at" not in lock.flatten()
    assert not any("resolved_at" in key for key in lock.flatten())
    assert "generation.stop" in manifest.flatten()  # empty lists are declarations
    assert "generation.top_k" not in manifest.flatten()  # absent is not null


def test_merge_keeps_every_source_and_does_not_mutate_inputs(tmp_path: Path) -> None:
    manifest = load_manifest(REPOS / "hf_vllm_eval/manifests/complete.yaml")
    lock = load_lock(REPOS / "hf_vllm_eval/expected/lock.yaml")
    data = saved_run().model_dump()
    data.update(manifest=None, lock=None)
    data["bindings_observed"]["generation.temperature"].append(
        {"source": {"type": "env", "key": "TEMPERATURE"}, "value": "0.25"}
    )
    run = RunRecord.model_validate(data)
    before = run.model_dump_json()
    state = State.merge(manifest, lock, run)
    leaf = state.flatten()["generation.temperature"]
    assert leaf.value == 1.0 and leaf.detail == "cli:--temperature"
    assert [(x.value, x.source, x.detail) for x in leaf.alternatives] == [
        (0.0, "run", "config:configs/eval.yaml:sampling.temperature"),
        ("0.25", "run", "env:TEMPERATURE"),
        (0.0, "lock", None),
        (0.0, "manifest", None),
    ]
    assert run.model_dump_json() == before
    assert State.merge(None, None, None).flatten() == {}
    assert State.merge(manifest).flatten() == State.from_manifest(manifest).flatten()


def test_run_uses_embedded_snapshots_and_preserves_whole_file_key(tmp_path: Path) -> None:
    folder = snapshot_dir(tmp_path)
    data = saved_run().model_dump()
    data["files"][0]["path"] = "configs/eval.v2.yaml"
    run = RunRecord.model_validate(data)
    state = State.from_run(run, run_dir=folder)
    flat = state.flatten()
    assert flat["generation.temperature"].value == 1.0
    assert [x.source for x in flat["generation.temperature"].alternatives] == [
        "run",
        "lock",
        "manifest",
    ]
    assert flat["models.primary.revision"].confidence == "exact"
    assert flat["datasets.eval.sampling.n"].value == 100
    assert flat["files.configs/eval.v2.yaml.sha256"].source == "run"
    assert "configs/eval.v2.yaml" in state.files.root
    assert state.profiles == ["inference", "evaluation"]
    # The current project manifest is irrelevant to a historical run.
    (tmp_path / "reprollm.yaml").write_text("broken: [")
    assert State.from_run(run, run_dir=folder).flatten() == flat


@pytest.mark.parametrize("snapshot", ["../manifest.yaml", "/manifest.yaml", "missing.yaml"])
def test_snapshot_cannot_escape_or_silently_disappear(tmp_path: Path, snapshot: str) -> None:
    folder = snapshot_dir(tmp_path)
    data = saved_run().model_dump()
    data["manifest"]["snapshot"] = snapshot
    with pytest.raises(UserError, match="manifest snapshot"):
        State.from_run(RunRecord.model_validate(data), run_dir=folder)


def test_corrupt_snapshot_error_does_not_echo_contents(tmp_path: Path) -> None:
    folder = snapshot_dir(tmp_path)
    (folder / "manifest.yaml").write_text("password: PRIVATE_BAD_YAML\nx: [")
    with pytest.raises(UserError) as error:
        State.from_run(saved_run(), run_dir=folder)
    assert "PRIVATE_BAD_YAML" not in str(error.value)
    assert str(tmp_path) not in str(error.value)
    with pytest.raises(UserError, match="run directory"):
        State.from_run(saved_run())


def test_gpu_indices_and_list_values_are_semantic_leaves() -> None:
    run = RunRecord.model_validate(
        {
            "schema_version": 1,
            "reprollm_version": "0.1.1",
            "run_id": "test",
            "status": "completed",
            "command": {"argv": ["python", "-c", "pass"], "cwd": "."},
            "hardware": {
                "cpu_count": 2,
                "gpus": [{"index": 3, "name": "Test GPU", "memory_mib": 10, "uuid_sha256": "hash"}],
            },
        }
    )
    flat = State.from_run(run).flatten()
    assert flat["hardware.gpus.3.name"].value == "Test GPU"
    assert flat["command.argv"].value == ["python", "-c", "pass"]
    assert flat["code.dirty"].value is False


def test_default_fallback_and_deterministic_equal_rank_order() -> None:
    default = State.from_flat(
        {"generation.seed": Leaf(value=42, source="default", detail=None, confidence="declared")}
    )
    manifest = State.from_flat(
        {"generation.seed": Leaf(value=7, source="manifest", detail=None, confidence="declared")}
    )
    merged = State.merge(default, manifest)
    assert merged.flatten()["generation.seed"].value == 7
    assert merged.flatten()["generation.seed"].alternatives[0].value == 42


def test_yaml_date_in_custom_data_has_json_stable_projection(tmp_path: Path) -> None:
    path = tmp_path / "reprollm.yaml"
    path.write_text(
        "schema_version: 1\nproject: {name: test}\nexperiment: {profiles: []}\n"
        "custom: {dataset_date: 2026-01-01, captured_at: 2026-01-01T12:00:00Z}\n"
    )
    manifest = load_manifest(path)
    state = State.merge(manifest)
    assert state.flatten()["custom.dataset_date"].value == "2026-01-01"
    assert isinstance(state.flatten()["custom.captured_at"].value, str)
    assert State.model_validate_json(state.model_dump_json()).flatten() == state.flatten()
