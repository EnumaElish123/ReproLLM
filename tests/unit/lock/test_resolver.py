from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path

import httpx
import pytest
import yaml

from reprollm.core.yaml_io import dump_yaml
from reprollm.lock.resolver import resolve_manifest
from reprollm.schemas.lock import Confidence, Lock, ResolutionMode

from .helpers import NOW, manifest, resolve


def _without_volatile(value):
    if isinstance(value, dict):
        return {
            key: _without_volatile(item)
            for key, item in value.items()
            if key not in {"generated_at", "resolved_at", "observed_at", "reprollm_version"}
        }
    if isinstance(value, list):
        return [_without_volatile(item) for item in value]
    return value


def _fake_versions(monkeypatch: pytest.MonkeyPatch, versions: dict[str, str]) -> None:
    def fake_version(name: str) -> str:
        if name in versions:
            return versions[name]
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", fake_version)


def test_prompts_files_metrics_backend_and_environment_are_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    for relative, content in {
        "prompts/system.txt": "system",
        "templates/chat.jinja": "{{ messages }}",
        "configs/eval.yaml": "temperature: 0",
        "configs/binding.json": "{}",
        "configs/ds.json": "{}",
        "definitions/refusal.txt": "refusal definition",
        "privacy/threat.txt": "threat model",
        "metrics/custom.py": "def score(): return 1",
        "data/items.jsonl": "{}\n",
    }.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    _fake_versions(monkeypatch, {"vllm": "0.10.0", "torch": "2.8.0"})
    stub_run_cmd.on(
        "nvidia-smi",
        "--query-gpu=driver_version",
        "--format=csv,noheader",
        stdout="560.35.03\n560.35.03\n",
    )
    stub_run_cmd.on(
        "nvidia-smi",
        stdout="NVIDIA-SMI 560.35.03 Driver Version: 560.35.03 CUDA Version: 12.6\n",
    )
    value = manifest(
        models={
            "primary": {
                "provider": "local",
                "id": "models/tiny.gguf",
                "chat_template": {"path": "templates/chat.jinja"},
            }
        },
        datasets={"eval": {"provider": "local", "id": "data", "files": ["data/items.jsonl"]}},
        prompts={
            "system": {"path": "prompts/system.txt"},
            "inline": {"text": "hello"},
            "missing": {"path": "prompts/missing.txt"},
        },
        generation={"temperature": 0.0},
        inference={"backend": "vllm", "mode": "offline", "params": {"worker": "ray"}},
        training={
            "method": "full",
            "deepspeed": {"config": "configs/ds.json"},
        },
        evaluation={
            "metrics": [
                {"name": "custom", "implementation": "metrics/custom.py"},
                {"name": "package", "implementation": "torch==2.8.0"},
                {"name": "unknown", "implementation": "not-installed"},
            ],
            "definitions": {
                "refusal": "definitions/refusal.txt",
                "asr": "Literal definition text",
            },
        },
        privacy={"threat_model": "privacy/threat.txt"},
        execution={"config_files": ["configs/eval.yaml"]},
        bindings={"generation.temperature": {"config": "configs/binding.json:sampling.temp"}},
    )
    (tmp_path / "models").mkdir()
    (tmp_path / "models/tiny.gguf").write_bytes(b"gguf")

    result = resolve(tmp_path, value)

    assert sorted(result.prompts) == ["inline", "system"]
    assert result.prompts["system"].sha256 is not None
    assert result.prompts["inline"].text_sha256 is not None
    assert [entry.path for entry in result.files] == [
        "configs/binding.json",
        "configs/ds.json",
        "configs/eval.yaml",
        "definitions/refusal.txt",
        "privacy/threat.txt",
        "templates/chat.jinja",
    ]
    assert result.inference is not None
    assert result.inference.version.value == "0.10.0"
    assert result.inference.version.confidence == Confidence.EXACT
    assert result.evaluation is not None
    metrics = {item.name: item for item in result.evaluation.metrics}
    assert metrics["custom"].implementation_sha256 is not None
    assert metrics["package"].implementation_version is not None
    assert metrics["package"].implementation_version.value == "2.8.0"
    assert metrics["unknown"].implementation_version is not None
    assert metrics["unknown"].implementation_version.confidence == Confidence.UNRESOLVED
    assert result.environment.packages == {"torch": "2.8.0", "vllm": "0.10.0"}
    assert result.environment.gpu.model_dump() == {
        "driver": "560.35.03",
        "cuda_driver_max": "12.6",
        "source": "nvidia_smi",
    }


def test_unavailable_gpu_and_unsupported_backend_are_explicit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    _fake_versions(monkeypatch, {})
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")

    result = resolve(tmp_path, manifest(inference={"backend": "other"}))

    assert result.inference is not None
    assert result.inference.version.confidence == Confidence.UNRESOLVED
    assert result.environment.gpu.source == "unavailable"


def test_offline_resolution_matches_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stub_run_cmd,
) -> None:
    _fake_versions(monkeypatch, {})
    monkeypatch.setattr("reprollm.core.envinfo.python_version", lambda: "3.11.9")
    monkeypatch.setattr("reprollm.core.envinfo.platform_name", lambda: "linux")
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")
    value = manifest(
        models={
            "declared": {
                "provider": "huggingface",
                "id": "org/model",
                "revision": "v1",
            },
            "unknown": {"provider": "huggingface", "id": "org/unknown"},
        },
        datasets={"eval": {"provider": "huggingface", "id": "org/data", "revision": "v2"}},
    )
    with httpx.Client() as http:
        sections = resolve_manifest(tmp_path, value, http=http, offline=True, now=NOW)
    lock = Lock(
        reprollm_version="0.1.1",
        generated_at=NOW,
        manifest_sha256="sha256:manifest",
        resolution=ResolutionMode(mode="offline"),
        **sections.as_lock_fields(),
    )
    expected_path = Path(__file__).parent / "expected/offline_lock.yaml"
    if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(dump_yaml(lock), encoding="utf-8")
        return
    expected = yaml.safe_load(expected_path.read_text(encoding="utf-8"))
    assert _without_volatile(lock.model_dump(mode="json")) == _without_volatile(expected)
