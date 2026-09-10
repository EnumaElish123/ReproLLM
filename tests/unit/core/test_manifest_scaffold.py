"""M2F-T09: pure tests for the init scaffold service (F-10)."""

from pathlib import Path

import pytest

from reprollm.core.errors import UserError
from reprollm.core.manifest_scaffold import (
    parse_scalar,
    plan_init,
    render_manifest,
    write_scaffold,
)
from reprollm.schemas.finding import DetectionResult
from tests.conftest import materialize_repo


def test_plan_init_uses_detected_high_medium(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    plan = plan_init(repo, profiles_override=None)
    assert plan.profiles == ["evaluation", "inference"]
    assert "models.primary.id" in plan.required_fields
    assert plan.primary_detection is not None
    assert plan.primary_detection[0] == "Qwen/Qwen3-32B"


def test_plan_init_explicit_profiles_override(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    plan = plan_init(repo, profiles_override=["privacy"])
    assert plan.profiles == ["privacy"]


def test_plan_init_rejects_unknown_profile(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    with pytest.raises(UserError, match="unknown profile"):
        plan_init(repo, profiles_override=["nope"])


def test_render_manifest_is_stable(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    plan = plan_init(repo, profiles_override=None)
    first = render_manifest(plan, {})
    second = render_manifest(plan, {})
    assert first == second
    assert "id: Qwen/Qwen3-32B" in first
    assert "profiles: [evaluation, inference]" in first


def test_parse_scalar_numeric_fields() -> None:
    assert parse_scalar("generation.temperature", "0.7") == 0.7
    assert parse_scalar("generation.max_tokens", "512") == 512
    assert parse_scalar("generation.temperature", "warm") == "warm"
    assert parse_scalar("models.primary.id", "org/model") == "org/model"


def test_write_scaffold_creates_files_once(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    plan = plan_init(repo, profiles_override=None)
    text = render_manifest(plan, {})
    result = write_scaffold(repo, text, force=False)
    assert result.manifest_written is True
    assert (repo / "reprollm.yaml").is_file()
    assert (repo / ".reprollm" / "config.yaml").is_file()
    assert (repo / ".reprollm" / "project-rules.yaml").is_file()

    # second run without force refuses and touches nothing
    (repo / ".reprollm" / "config.yaml").write_text("# custom\n")
    with pytest.raises(UserError, match="--force"):
        write_scaffold(repo, text, force=False)
    result = write_scaffold(repo, text, force=True)
    assert result.manifest_written is True
    # dotdir files are never overwritten, even with --force
    assert (repo / ".reprollm" / "config.yaml").read_text(encoding="utf-8") == "# custom\n"


def test_write_scaffold_validates_generated_manifest(tmp_path: Path) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path)
    with pytest.raises(UserError, match="validation"):
        write_scaffold(repo, "project: {}\n", force=False)
    assert not (repo / "reprollm.yaml").exists()  # broken file removed


def test_detection_result_smoke() -> None:
    detection = DetectionResult.model_validate(
        {
            "profiles": [
                {"profile": "inference", "confidence": "high"},
                {"profile": "rag", "confidence": "low", "shipped": False},
            ]
        }
    )
    assert [p.profile for p in detection.profiles if p.shipped] == ["inference"]
