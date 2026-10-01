"""Provider interfaces are consumed by detection, lock and runtime metadata (§14)."""

from __future__ import annotations

import builtins
import importlib
import importlib.metadata
from pathlib import Path

import httpx
import pytest
import respx

from reprollm.core import envinfo
from reprollm.core.context import AuditContext
from reprollm.core.pyscan import scan_python
from reprollm.integrations.base import Integration, ResolverIntegration
from reprollm.profiles.detect import run_detection
from tests.unit.lock.helpers import NOW, manifest

_PROVIDERS = (
    ("huggingface", "HuggingFaceIntegration"),
    ("transformers_", "TransformersIntegration"),
    ("vllm", "VllmIntegration"),
    ("openai_", "OpenAIIntegration"),
    ("peft", "PeftIntegration"),
)


def _provider(module: str, name: str):
    implementation = getattr(importlib.import_module(f"reprollm.integrations.{module}"), name, None)
    assert implementation is not None, f"{module} must implement {name}"
    return implementation


@pytest.mark.parametrize("module,name", _PROVIDERS)
def test_provider_implements_detection_capture_and_optional_task_hints(
    module: str, name: str
) -> None:
    implementation = _provider(module, name)()

    assert isinstance(implementation, Integration)
    assert implementation.name


def test_resolution_is_an_optional_capability() -> None:
    for module, name in _PROVIDERS:
        instance = _provider(module, name)()
        assert isinstance(instance, ResolverIntegration) == (module != "transformers_")
    for module, name in (
        ("lm_eval", "LmEvalIntegration"),
        ("lighteval", "LightEvalIntegration"),
        ("inspect_ai", "InspectAIIntegration"),
    ):
        assert not isinstance(_provider(module, name)(), ResolverIntegration)


def test_provider_detection_and_capture_never_import_target_libraries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "worker.py").write_text(
        "import datasets, transformers, vllm, peft, openai\n", encoding="utf-8"
    )
    ctx = AuditContext(tmp_path, level=0)
    scanned = scan_python(ctx.fs)
    original = builtins.__import__
    forbidden = set(envinfo.LLM_CRITICAL_PACKAGES) | {"huggingface_hub"}

    def guarded_import(name, *args, **kwargs):
        assert name.split(".", 1)[0] not in forbidden, f"target import: {name}"
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    for module, name in _PROVIDERS:
        integration = _provider(module, name)()
        integration.detect(ctx.fs, pyscan=scanned)
        integration.capture()
    envinfo.installed_versions()


def test_profile_detection_consumes_cached_provider_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "worker.py").write_text(
        "import openai, anthropic, vllm, sglang, datasets, peft\n"
        "from transformers import Trainer\n"
        'Model.from_pretrained("org/model", trust_remote_code=True)\n',
        encoding="utf-8",
    )
    ctx = AuditContext(tmp_path, level=0)
    scanned = scan_python(ctx.fs)
    detected: list[str] = []
    for module, name in _PROVIDERS:
        cls = _provider(module, name)
        original = cls.detect

        def track(self, scanner, *, pyscan=None, original=original):
            assert pyscan is scanned, "reuse the bounded AST scan"
            detected.append(self.name)
            return original(self, scanner, pyscan=pyscan)

        monkeypatch.setattr(cls, "detect", track)

    result = run_detection(ctx.fs, scanned, ctx.deps)

    assert set(detected) == {"huggingface", "transformers", "vllm", "openai", "peft"}
    assert result.hints.model_dump() == {
        "providers": ["openai", "anthropic"],
        "backends": ["vllm", "sglang"],
        "datasets": True,
        "adapter": True,
        "trust_remote_code": True,
        "hf_ids": [{"value": "org/model", "path": "worker.py", "line": 3}],
    }
    finetuning = next(profile for profile in result.profiles if profile.profile == "finetuning")
    assert any(
        evidence.note == "from transformers import Trainer|Seq2SeqTrainer|TrainingArguments"
        and evidence.path == "worker.py"
        and evidence.line == 2
        and evidence.field is None
        and evidence.value is None
        for evidence in finetuning.evidence
    )


def test_default_metadata_capture_consumes_integrations_without_recursion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    versions = {
        "torch": "2.8.0",
        "transformers": "4.55.0",
        "tokenizers": "0.21.0",
        "accelerate": "1.10.0",
        "peft": "0.17.0",
        "vllm": "0.10.0",
        "openai": "1.100.0",
        "lm_eval": "0.4.9",
        "inspect-ai": "0.3.0",
    }

    def version(name: str) -> str:
        if name not in versions:
            raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]

    monkeypatch.setattr(importlib.metadata, "version", version)
    captured: list[str] = []
    implementations = list(_PROVIDERS) + [
        ("lm_eval", "LmEvalIntegration"),
        ("lighteval", "LightEvalIntegration"),
        ("inspect_ai", "InspectAIIntegration"),
    ]
    for module, name in implementations:
        cls = _provider(module, name)
        original = cls.capture

        def track(self, original=original):
            assert self.name not in captured, "metadata capture must not recurse"
            captured.append(self.name)
            return original(self)

        monkeypatch.setattr(cls, "capture", track)

    actual = envinfo.installed_versions()

    expected = {
        name: versions[envinfo.distribution_name(name)]
        for name in envinfo.LLM_CRITICAL_PACKAGES
        if envinfo.distribution_name(name) in versions
    }
    assert list(actual.items()) == list(expected.items())
    assert set(captured) == {
        "huggingface",
        "transformers",
        "vllm",
        "openai",
        "peft",
        "lm_eval",
        "lighteval",
        "inspect_ai",
    }
    captured.clear()
    assert envinfo.installed_versions(["torch"]) == {"torch": "2.8.0"}
    assert captured == [], "explicit package capture stays a metadata-only leaf"


def test_offline_lock_consumes_resolvers_without_constructing_http_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    from reprollm.lock.resolver import resolve_manifest

    resolved: list[str] = []
    for module, name in (item for item in _PROVIDERS if item[0] != "transformers_"):
        cls = _provider(module, name)
        original = cls.resolve

        def track(self, value, *, offline, http, original=original):
            assert offline is True
            assert http is None
            resolved.append(self.name)
            return original(self, value, offline=offline, http=http)

        monkeypatch.setattr(cls, "resolve", track)

    def forbid_client(*args, **kwargs):
        raise AssertionError("offline lock must not construct an HTTP client")

    monkeypatch.setattr(httpx, "Client", forbid_client)
    stub_run_cmd.on("nvidia-smi", returncode=127)
    value = manifest(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "org/model",
                "revision": "base-revision",
                "adapter": {
                    "provider": "peft",
                    "type": "lora",
                    "id": "org/adapter",
                    "revision": "adapter-revision",
                },
            },
            "judge": {"provider": "openai", "id": "gpt-4o-2024-08-06"},
        },
        datasets={
            "eval": {"provider": "huggingface", "id": "org/data", "revision": "data-revision"}
        },
        inference={"backend": "vllm"},
    )

    result = resolve_manifest(tmp_path, value, http=None, offline=True, verify_api=True, now=NOW)

    assert sorted(resolved) == ["huggingface", "openai", "peft", "vllm"]
    assert result.models["primary"].revision.value == "base-revision"
    assert result.models["primary"].adapter is not None
    assert result.models["primary"].adapter.revision.value == "adapter-revision"
    assert result.datasets["eval"].revision.value == "data-revision"
    assert result.models["judge"].pinnability == "snapshot_alias"
    assert result.models["judge"].observed_at == NOW
    assert result.inference is not None and result.inference.backend == "vllm"


def test_existing_offline_lock_path_never_constructs_http_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    from reprollm.lock.resolver import resolve_manifest

    def forbid_client(*args, **kwargs):
        raise AssertionError("offline lock must not construct an HTTP client")

    monkeypatch.setattr(httpx, "Client", forbid_client)
    stub_run_cmd.on("nvidia-smi", returncode=127)
    value = manifest(models={"primary": {"provider": "huggingface", "id": "org/base"}})

    result = resolve_manifest(tmp_path, value, http=None, offline=True, now=NOW)

    assert result.models["primary"].revision.source == "offline"


def test_standalone_hf_helper_keeps_its_adapter_resolution(tmp_path: Path) -> None:
    from reprollm.lock.hf_resolver import resolve_hf_model

    value = manifest(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "org/base",
                "revision": "base-revision",
                "adapter": {
                    "provider": "peft",
                    "type": "lora",
                    "id": "org/adapter",
                    "revision": "adapter-revision",
                },
            }
        }
    )

    result = resolve_hf_model(tmp_path, value.models["primary"], client=None, offline=True, now=NOW)

    assert result.adapter is not None
    assert result.adapter.id == "org/adapter"
    assert result.adapter.revision.value == "adapter-revision"
    assert result.adapter.revision.source == "manifest"


@respx.mock
def test_hf_resolution_consumes_peft_once_without_duplicate_hub_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd
) -> None:
    from reprollm.lock.resolver import resolve_manifest

    cls = _provider("peft", "PeftIntegration")
    original = cls.resolve
    calls: list[str] = []

    def track(self, value, *, offline, http):
        calls.append(self.name)
        return original(self, value, offline=offline, http=http)

    monkeypatch.setattr(cls, "resolve", track)
    monkeypatch.setenv("HF_ENDPOINT", "https://huggingface.co")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
    base = respx.get("https://huggingface.co/api/models/org/base/revision/main").mock(
        return_value=httpx.Response(200, json={"sha": "base-sha", "siblings": []})
    )
    adapter = respx.get("https://huggingface.co/api/models/org/adapter/revision/main").mock(
        return_value=httpx.Response(200, json={"sha": "adapter-sha", "siblings": []})
    )
    stub_run_cmd.on("nvidia-smi", returncode=127)
    value = manifest(
        models={
            "primary": {
                "provider": "huggingface",
                "id": "org/base",
                "adapter": {"provider": "peft", "type": "lora", "id": "org/adapter"},
            }
        }
    )

    with httpx.Client() as http:
        result = resolve_manifest(tmp_path, value, http=http, now=NOW)

    assert calls == ["peft"]
    assert base.call_count == adapter.call_count == 1
    assert result.models["primary"].adapter is not None
    assert result.models["primary"].adapter.revision.value == "adapter-sha"
