"""Manifest-to-lock resolution orchestration (spec §4.3)."""

from __future__ import annotations

import importlib.metadata
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

import httpx

from reprollm.core import envinfo, proc
from reprollm.core.hashing import sha256_file, sha256_text
from reprollm.lock.api_resolver import resolve_api_model
from reprollm.lock.hf_client import HfClient
from reprollm.lock.hf_resolver import resolve_hf_dataset, resolve_hf_model
from reprollm.lock.local_resolver import resolve_local_dataset, resolve_local_model
from reprollm.schemas.lock import (
    Confidence,
    DatasetLock,
    EnvironmentLock,
    EvaluationLock,
    FileEntry,
    GpuEnvLock,
    InferenceLock,
    MetricLock,
    ModelLock,
    PromptLock,
    Provenance,
)
from reprollm.schemas.manifest import Generation, Manifest, MetricSpec, Privacy, Training

_BACKEND_DISTRIBUTIONS = {
    "vllm": "vllm",
    "transformers": "transformers",
    "sglang": "sglang",
    "openai": "openai",
}
_CUDA_VERSION = re.compile(r"CUDA Version:\s*([0-9.]+)")


@dataclass(frozen=True)
class ResolvedManifest:
    """Resolved lock sections; document metadata is added by the lock writer."""

    models: dict[str, ModelLock]
    datasets: dict[str, DatasetLock]
    prompts: dict[str, PromptLock]
    files: list[FileEntry]
    generation: Generation | None
    inference: InferenceLock | None
    training: Training | None
    evaluation: EvaluationLock | None
    privacy: Privacy | None
    environment: EnvironmentLock

    def as_lock_fields(self) -> dict[str, object]:
        return {
            "models": self.models,
            "datasets": self.datasets,
            "prompts": self.prompts,
            "files": self.files,
            "generation": self.generation,
            "inference": self.inference,
            "training": self.training,
            "evaluation": self.evaluation,
            "privacy": self.privacy,
            "environment": self.environment,
        }


def resolve_manifest(
    root: Path,
    manifest: Manifest,
    *,
    http: httpx.Client,
    offline: bool = False,
    verify_api: bool = False,
    hash_large_files: bool = False,
    now: datetime | None = None,
) -> ResolvedManifest:
    """Resolve every lockable manifest field without writing any files."""
    timestamp = now or datetime.now(timezone.utc).replace(microsecond=0)
    client = HfClient(http, token=None)
    models: dict[str, ModelLock] = {}
    for role, model_spec in sorted(manifest.models.items()):
        if model_spec.provider == "huggingface":
            models[role] = resolve_hf_model(
                root, model_spec, client=client, offline=offline, now=timestamp
            )
        elif model_spec.provider == "local":
            models[role] = resolve_local_model(
                root,
                model_spec,
                hash_large_files=hash_large_files,
                now=timestamp,
                field_path=f"models.{role}.id",
            )
        else:
            models[role] = resolve_api_model(
                model_spec,
                http=http,
                verify_api=verify_api and not offline,
                now=timestamp,
            )

    datasets: dict[str, DatasetLock] = {}
    for role, dataset_spec in sorted(manifest.datasets.items()):
        if dataset_spec.provider == "huggingface":
            datasets[role] = resolve_hf_dataset(
                dataset_spec, client=client, offline=offline, now=timestamp
            )
        elif dataset_spec.provider == "local":
            datasets[role] = resolve_local_dataset(root, dataset_spec, now=timestamp)
        else:
            datasets[role] = DatasetLock(
                provider=dataset_spec.provider or "other",
                id=dataset_spec.id or "",
                revision=_declared_or_unresolved(dataset_spec.revision),
                subset=dataset_spec.subset,
                split=dataset_spec.split,
            )

    return ResolvedManifest(
        models=models,
        datasets=datasets,
        prompts=_resolve_prompts(root, manifest),
        files=_resolve_files(root, manifest),
        generation=manifest.generation.model_copy(deep=True) if manifest.generation else None,
        inference=_resolve_inference(manifest, timestamp),
        training=manifest.training.model_copy(deep=True) if manifest.training else None,
        evaluation=_resolve_evaluation(root, manifest, timestamp),
        privacy=manifest.privacy.model_copy(deep=True) if manifest.privacy else None,
        environment=_resolve_environment(),
    )


def _resolve_prompts(root: Path, manifest: Manifest) -> dict[str, PromptLock]:
    prompts: dict[str, PromptLock] = {}
    for role, spec in sorted(manifest.prompts.items()):
        if spec.path is not None:
            path = _safe_project_file(root, spec.path)
            if path is None:
                continue
            prompts[role] = PromptLock(
                path=spec.path,
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        elif spec.text is not None:
            prompts[role] = PromptLock(text_sha256=sha256_text(spec.text))
    return prompts


def _resolve_files(root: Path, manifest: Manifest) -> list[FileEntry]:
    candidates: set[str] = set()
    if manifest.execution is not None:
        candidates.update(manifest.execution.config_files or [])
    for binding in manifest.bindings.values():
        if binding.config:
            candidates.add(binding.config.split(":", 1)[0])
    if manifest.training is not None and manifest.training.deepspeed is not None:
        candidates.add(manifest.training.deepspeed.config)
    for model in manifest.models.values():
        if model.chat_template is not None:
            candidates.add(model.chat_template.path)
    if manifest.evaluation is not None:
        for value in (manifest.evaluation.definitions or {}).values():
            if _safe_project_file(root, value) is not None:
                candidates.add(value)
    if manifest.privacy is not None and manifest.privacy.threat_model:
        value = manifest.privacy.threat_model
        if _safe_project_file(root, value) is not None:
            candidates.add(value)

    files: list[FileEntry] = []
    for relative in sorted(candidates):
        path = _safe_project_file(root, relative)
        if path is None:
            continue
        files.append(
            FileEntry(path=relative, sha256=sha256_file(path), size_bytes=path.stat().st_size)
        )
    return files


def _resolve_inference(manifest: Manifest, now: datetime) -> InferenceLock | None:
    spec = manifest.inference
    if spec is None:
        return None
    backend = spec.backend or "other"
    distribution = _BACKEND_DISTRIBUTIONS.get(backend)
    version = (
        _installed_version(distribution, declared=spec.version, now=now)
        if distribution is not None
        else _declared_or_unresolved(spec.version, source="unsupported_backend")
    )
    return InferenceLock(
        backend=backend,
        version=version,
        mode=spec.mode,
        dtype=spec.dtype,
        tensor_parallel_size=spec.tensor_parallel_size,
        gpu_memory_utilization=spec.gpu_memory_utilization,
        quantization=spec.quantization,
        max_model_len=spec.max_model_len,
        kv_cache_dtype=spec.kv_cache_dtype,
        params=spec.params,
    )


def _resolve_evaluation(root: Path, manifest: Manifest, now: datetime) -> EvaluationLock | None:
    spec = manifest.evaluation
    if spec is None:
        return None
    metrics = [_resolve_metric(root, metric, now) for metric in spec.metrics]
    return EvaluationLock(
        metrics=metrics,
        aggregation=spec.aggregation,
        repetitions=spec.repetitions,
        thresholds=spec.thresholds,
        definitions=spec.definitions,
        query_budget=spec.query_budget,
        judge=spec.judge.model_dump(mode="python") if spec.judge is not None else None,
    )


def _resolve_metric(root: Path, metric: MetricSpec, now: datetime) -> MetricLock:
    implementation = metric.implementation
    if implementation is None:
        return MetricLock(name=metric.name)
    path = _safe_project_file(root, implementation)
    if path is not None:
        return MetricLock(
            name=metric.name,
            implementation=implementation,
            implementation_sha256=sha256_file(path),
        )
    package, separator, declared = implementation.partition("==")
    return MetricLock(
        name=metric.name,
        implementation=implementation,
        implementation_version=_installed_version(
            package,
            declared=declared if separator else None,
            now=now,
        ),
    )


def _installed_version(distribution: str, *, declared: str | None, now: datetime) -> Provenance:
    try:
        version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return Provenance(
            value=None,
            source="importlib_metadata",
            confidence=Confidence.UNRESOLVED,
            note=f"distribution not installed: {distribution}",
        )
    note = (
        f"declared {declared}, installed {version}"
        if declared is not None and declared != version
        else None
    )
    return Provenance(
        value=version,
        source="importlib_metadata",
        confidence=Confidence.EXACT,
        resolved_at=now,
        note=note,
    )


def _resolve_environment() -> EnvironmentLock:
    platform = cast(Literal["linux", "darwin", "windows"], envinfo.platform_name())
    return EnvironmentLock(
        python=envinfo.python_version(),
        platform=platform,
        packages=dict(sorted(envinfo.installed_versions().items())),
        gpu=_resolve_gpu(),
    )


def _resolve_gpu() -> GpuEnvLock:
    drivers = proc.run_cmd(
        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
        timeout=10,
    )
    if drivers.returncode != 0:
        return GpuEnvLock(source="unavailable")
    values = sorted({line.strip() for line in drivers.stdout.splitlines() if line.strip()})
    header = proc.run_cmd(["nvidia-smi"], timeout=10)
    match = _CUDA_VERSION.search(header.stdout) if header.returncode == 0 else None
    return GpuEnvLock(
        driver=values[0] if values else None,
        cuda_driver_max=match.group(1) if match else None,
        source="nvidia_smi",
    )


def _declared_or_unresolved(
    value: str | None, *, source: str = "provider_no_pinning"
) -> Provenance:
    if value is not None:
        return Provenance(value=value, source="manifest", confidence=Confidence.DECLARED)
    return Provenance(
        value=None,
        source=source,
        confidence=Confidence.UNRESOLVED,
    )


def _safe_project_file(root: Path, relative: str) -> Path | None:
    candidate = Path(relative)
    if candidate.is_absolute():
        return None
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved if resolved.is_file() else None
