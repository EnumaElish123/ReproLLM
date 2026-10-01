"""Provider capabilities consumed by profile detection and metadata capture."""

from __future__ import annotations

from dataclasses import dataclass

from reprollm.core.pyscan import PyScanResult
from reprollm.core.scanner import RepoScanner
from reprollm.integrations.base import Integration
from reprollm.integrations.huggingface import HuggingFaceIntegration
from reprollm.integrations.inspect_ai import InspectAIIntegration
from reprollm.integrations.lighteval import LightEvalIntegration
from reprollm.integrations.lm_eval import LmEvalIntegration
from reprollm.integrations.openai_ import OpenAIIntegration
from reprollm.integrations.peft import PeftIntegration
from reprollm.integrations.transformers_ import TransformersIntegration
from reprollm.integrations.vllm import VllmIntegration
from reprollm.schemas.finding import DetectionHints, Evidence, HfIdHint

CAPTURED_PACKAGES = frozenset(
    {
        "transformers",
        "tokenizers",
        "accelerate",
        "vllm",
        "openai",
        "peft",
        "lm_eval",
        "lighteval",
        "inspect_ai",
    }
)


def provider_integrations() -> tuple[Integration, ...]:
    return (
        HuggingFaceIntegration(),
        TransformersIntegration(),
        VllmIntegration(),
        OpenAIIntegration(),
        PeftIntegration(),
    )


@dataclass(frozen=True)
class ProviderDetection:
    hints: DetectionHints
    trainer_evidence: list[Evidence]


def detect_providers(scanner: RepoScanner, pyscan: PyScanResult) -> ProviderDetection:
    detected = {
        integration.name: integration.detect(scanner, pyscan=pyscan)
        for integration in provider_integrations()
    }
    hf = detected["huggingface"]
    api = detected["openai"]
    backends = detected["vllm"]
    ids = [
        HfIdHint(value=evidence.value, path=evidence.path, line=evidence.line)
        for evidence in hf
        if evidence.note == "HF repository id"
        and isinstance(evidence.value, str)
        and evidence.path is not None
        and evidence.line is not None
    ]
    return ProviderDetection(
        hints=DetectionHints(
            providers=[
                name
                for name in ("openai", "anthropic")
                if any(e.note == f"import {name}" for e in api)
            ]
            + (["openrouter"] if any(e.note == "provider openrouter" for e in api) else []),
            backends=[
                name
                for name in ("vllm", "sglang")
                if any(e.note == f"import {name}" for e in backends)
            ],
            datasets=any(e.note == "import datasets" for e in hf),
            adapter=bool(detected["peft"]),
            trust_remote_code=pyscan.trust_remote_code,
            hf_ids=ids,
        ),
        trainer_evidence=[
            evidence
            for evidence in detected["transformers"]
            if evidence.note == "from transformers import Trainer|Seq2SeqTrainer|TrainingArguments"
        ],
    )


def capture_versions() -> dict[str, str]:
    integrations = (
        *provider_integrations(),
        LmEvalIntegration(),
        LightEvalIntegration(),
        InspectAIIntegration(),
    )
    versions: dict[str, str] = {}
    for integration in integrations:
        versions.update(
            {
                name: version
                for name, version in integration.capture().items()
                if version != "not installed"
            }
        )
    return versions
