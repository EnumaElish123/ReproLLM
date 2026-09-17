"""Closed-source API provider resolution (spec §4.3)."""

from __future__ import annotations

import os
import re
from datetime import datetime

import httpx

from reprollm.schemas.lock import Confidence, ModelLock, Provenance
from reprollm.schemas.manifest import ModelSpec

_SNAPSHOT_SUFFIX = re.compile(r"(?:-\d{4}-\d{2}-\d{2}|@\d{8})$")
_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "anthropic": "https://api.anthropic.com/v1",
}
_KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def resolve_api_model(
    spec: ModelSpec,
    *,
    http: httpx.Client,
    verify_api: bool,
    now: datetime,
) -> ModelLock:
    """Classify an API model alias and optionally verify its existence."""
    provider = spec.provider or "other"
    model_id = spec.id or ""
    pinnability = "snapshot_alias" if _SNAPSHOT_SUFFIX.search(model_id) else "unpinnable"
    note: str | None = None
    if verify_api:
        key_name = _KEY_NAMES.get(provider)
        api_key = os.getenv(key_name) if key_name is not None else None
        if not api_key:
            note = "verify skipped: no api key"
        else:
            note = _verify_model(http, provider, model_id, spec, api_key)
    return ModelLock(
        provider=provider,
        id=model_id,
        pinnability=pinnability,
        revision=Provenance(
            value=None,
            source="provider_no_pinning",
            confidence=Confidence.UNRESOLVED,
            note=note,
        ),
        observed_at=now,
        dtype=spec.dtype,
        quantization=spec.quantization,
        trust_remote_code=spec.trust_remote_code,
    )


def _verify_model(
    http: httpx.Client,
    provider: str,
    model_id: str,
    spec: ModelSpec,
    api_key: str,
) -> str:
    configured = spec.endpoint.base_url if spec.endpoint is not None else None
    base_url = (configured or _DEFAULT_BASE_URLS.get(provider, "")).rstrip("/")
    if not base_url:
        return "verify skipped: no provider endpoint"
    if provider == "anthropic":
        headers = {
            "x-api-key": api_key,
            "anthropic-version": spec.endpoint.api_version
            if spec.endpoint is not None and spec.endpoint.api_version
            else "2023-06-01",
        }
    else:
        headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = http.get(
            f"{base_url}/models/{model_id}",
            headers=headers,
            timeout=10.0,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        return f"verify error: {type(exc).__name__}"
    if response.status_code == 404:
        return "not_found"
    if response.status_code < 400:
        return "exists"
    return f"verify error: HTTP {response.status_code}"
