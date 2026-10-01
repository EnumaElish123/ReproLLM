"""Shared metadata-only lock resolution; never imports a target package."""

from __future__ import annotations

import importlib.metadata
from datetime import datetime

from reprollm.schemas.lock import Confidence, InferenceLock, Provenance
from reprollm.schemas.manifest import Manifest

_BACKEND_DISTRIBUTIONS = {
    "vllm": "vllm",
    "transformers": "transformers",
    "sglang": "sglang",
    "openai": "openai",
}


def installed_version(distribution: str, *, declared: str | None, now: datetime) -> Provenance:
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


def resolve_inference(manifest: Manifest, now: datetime) -> InferenceLock | None:
    spec = manifest.inference
    if spec is None:
        return None
    backend = spec.backend or "other"
    distribution = _BACKEND_DISTRIBUTIONS.get(backend)
    if distribution is not None:
        version = installed_version(distribution, declared=spec.version, now=now)
    else:
        version = Provenance(
            value=spec.version,
            source="manifest" if spec.version is not None else "unsupported_backend",
            confidence=Confidence.DECLARED if spec.version is not None else Confidence.UNRESOLVED,
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
