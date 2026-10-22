"""M2F-T09: pure tests for the init scaffold service (F-10)."""

import os
from pathlib import Path
from typing import Any

import pytest
import yaml

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
    assert "detected candidate; verify role:" in first
    assert "Detected values are candidates" in first
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
    assert not (repo / ".reprollm").exists()


@pytest.mark.parametrize("stage", ["temp_write", "config_write", "rules_write", "replace"])
@pytest.mark.parametrize("existing_dotdir", [False, True])
@pytest.mark.parametrize("existing_manifest", [False, True])
def test_write_scaffold_io_failure_preserves_existing_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    existing_dotdir: bool,
    existing_manifest: bool,
) -> None:
    repo = materialize_repo("hf_vllm_eval", tmp_path, manifest="complete")
    manifest = repo / "reprollm.yaml"
    manifest.chmod(0o640)
    old = (manifest.read_bytes(), manifest.stat().st_mode)
    if not existing_manifest:
        manifest.unlink()
    dotdir = repo / ".reprollm"
    if existing_dotdir:
        dotdir.mkdir()
        (dotdir / "sentinel").write_bytes(b"keep\n")
        if stage != "config_write":
            (dotdir / "config.yaml").write_bytes(b"# existing config\n")
            (dotdir / "config.yaml").chmod(0o640)
    before = {p.relative_to(repo): (p.read_bytes(), p.stat().st_mode) for p in dotdir.glob("*")}
    text = "schema_version: 1\nproject: {name: updated}\nexperiment: {profiles: [inference]}\n"
    real_open = Path.open
    real_fdopen = os.fdopen

    class FailingWrite:
        def __init__(self, stream: Any) -> None:
            self.stream = stream

        def __enter__(self) -> "FailingWrite":
            self.stream.__enter__()
            return self

        def __exit__(self, *args: Any) -> Any:
            return self.stream.__exit__(*args)

        def write(self, text: str) -> int:
            self.stream.write(text[:8])
            raise OSError("injected write failure")

    def failing_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        stream = real_open(path, *args, **kwargs)
        target = "config.yaml" if stage == "config_write" else "project-rules.yaml"
        if stage in {"config_write", "rules_write"} and path.name == target:
            return FailingWrite(stream)
        return stream

    def failing_fdopen(*args: Any, **kwargs: Any) -> Any:
        return FailingWrite(real_fdopen(*args, **kwargs))

    def failing_replace(*args: Any, **kwargs: Any) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(Path, "open", failing_open)
    if stage == "temp_write":
        monkeypatch.setattr(os, "fdopen", failing_fdopen)
    if stage == "replace":
        monkeypatch.setattr(os, "replace", failing_replace)
    with pytest.raises(UserError, match="reprollm.yaml"):
        write_scaffold(repo, text, force=True)
    if existing_manifest:
        assert (manifest.read_bytes(), manifest.stat().st_mode) == old
    else:
        assert not manifest.exists()
    assert {
        p.relative_to(repo): (p.read_bytes(), p.stat().st_mode) for p in dotdir.glob("*")
    } == before
    assert dotdir.exists() == existing_dotdir
    assert not list(repo.glob(".reprollm.yaml.*.tmp"))


@pytest.mark.parametrize(
    "text",
    [
        "schema_version: 1\nproject: {name: valid}\nexperiment: {profiles: []}\nCANARY_SECRET: [",
        "schema_version: 1\nproject: {name: /private/CANARY_SECRET}\nexperiment: {profiles: []}\n",
        "schema_version: 1\nproject: {name: valid}\nexperiment: {profiles: []}\n"
        "CANARY_SECRET: bad\n",
        "schema_version: 1\nproject: {name: valid}\nexperiment: {profiles: []}\n# \ud800\n",
    ],
)
def test_scaffold_validation_errors_are_safe_and_write_nothing(tmp_path: Path, text: str) -> None:
    with pytest.raises(UserError) as error:
        write_scaffold(tmp_path, text, force=False)
    assert "reprollm.yaml" in str(error.value)
    assert "CANARY_SECRET" not in str(error.value)
    assert str(tmp_path) not in str(error.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are unavailable on Windows")
def test_force_success_preserves_existing_file_modes(tmp_path: Path) -> None:
    manifest = tmp_path / "reprollm.yaml"
    manifest.write_bytes(b"# hand edited\n")
    dotdir = tmp_path / ".reprollm"
    dotdir.mkdir()
    auxiliary = [dotdir / "config.yaml", dotdir / "project-rules.yaml"]
    for path in auxiliary:
        path.write_bytes(b"# keep\n")
        path.chmod(0o640)
    manifest.chmod(0o640)
    before = {path: (path.read_bytes(), path.stat().st_mode) for path in auxiliary}
    text = "schema_version: 1\nproject: {name: updated}\nexperiment: {profiles: []}\n"
    write_scaffold(tmp_path, text, force=True)
    assert manifest.read_text() == text
    assert manifest.stat().st_mode & 0o777 == 0o640
    assert {path: (path.read_bytes(), path.stat().st_mode) for path in auxiliary} == before


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


@pytest.mark.parametrize("override", [False, True])
def test_inline_comments_feed_builtin_init_fields_and_keep_explicit_selection(
    tmp_path: Path, override: bool
) -> None:
    root = tmp_path / "comments"
    root.mkdir()
    (root / "requirements.txt").write_text("vllm>=2 # use\npeft>=0.1 # use\n", encoding="utf-8")
    selected = ["inference"] if override else ["finetuning", "inference"]
    plan = plan_init(root, profiles_override=["inference"] if override else None)
    assert plan.project_name == "comments"
    assert plan.project_name_defaulted is False
    assert plan.profiles == selected
    assert plan.required_fields == [
        "project.name",
        "models.primary.id",
        *([] if override else ["training.method", "training.learning_rate", "datasets.train.id"]),
        "inference.backend",
        "generation.temperature",
        "generation.max_tokens",
    ]
    assert plan.primary_detection is None
    assert plan.other_detections == plan.task_names == plan.task_sources == plan.diagnostics == []
    assert plan.detection.model_dump(mode="json") == {
        "profiles": [
            {
                "profile": name,
                "confidence": "medium",
                "shipped": True,
                "evidence": [
                    {
                        "kind": "detection",
                        "path": "requirements.txt",
                        "field": None,
                        "line": line,
                        "value": None,
                        "expected": None,
                        "note": f"dependency {package}",
                    }
                ],
            }
            for name, package, line in [("finetuning", "peft", 2), ("inference", "vllm", 1)]
        ],
        "hints": {
            "providers": [],
            "backends": [],
            "datasets": False,
            "adapter": False,
            "trust_remote_code": False,
            "hf_ids": [],
        },
    }
    expected: dict[str, Any] = {
        "schema_version": 1,
        "project": {"name": "comments"},
        "experiment": {"profiles": selected},
        "models": {"primary": {"id": None}},
        "generation": {"temperature": None, "max_tokens": None},
        "inference": {"backend": None},
    }
    if not override:
        expected.update(
            datasets={"train": {"id": None}}, training={"method": None, "learning_rate": None}
        )
    first, repeated = render_manifest(plan, {}), render_manifest(plan, {})
    assert first == repeated
    assert yaml.safe_load(first) == expected
    assert "from detected signals" in first
    write_scaffold(root, first, force=False)
    assert (root / "reprollm.yaml").read_text(encoding="utf-8") == first
    assert yaml.safe_load((root / ".reprollm/project-rules.yaml").read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "rules": [],
        "ignored_candidates": [],
    }
