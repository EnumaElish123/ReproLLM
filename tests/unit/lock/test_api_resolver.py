from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
import respx

from reprollm.lock.api_resolver import resolve_api_model
from reprollm.schemas.lock import Confidence
from reprollm.schemas.manifest import ModelSpec

NOW = datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("provider", "model_id", "expected"),
    [
        ("openai", "gpt-4o", "unpinnable"),
        ("openai", "gpt-4o-2024-08-06", "snapshot_alias"),
        ("openrouter", "vendor/model@20240806", "snapshot_alias"),
        ("anthropic", "claude-3-opus", "unpinnable"),
    ],
)
def test_api_pinnability_is_classified_without_network(
    provider: str, model_id: str, expected: str
) -> None:
    spec = ModelSpec.model_validate({"provider": provider, "id": model_id})
    with httpx.Client() as http:
        lock = resolve_api_model(spec, http=http, verify_api=False, now=NOW)

    assert lock.pinnability == expected
    assert lock.observed_at == NOW
    assert lock.revision.confidence == Confidence.UNRESOLVED
    assert lock.revision.source == "provider_no_pinning"


def test_verify_api_without_key_records_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    spec = ModelSpec(provider="openai", id="gpt-4o")
    with httpx.Client() as http:
        lock = resolve_api_model(spec, http=http, verify_api=True, now=NOW)

    assert lock.revision.note == "verify skipped: no api key"


def test_verify_api_uses_endpoint_and_key_without_persisting_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "sk-test-secret-value-that-must-not-persist"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    seen_headers: list[httpx.Headers] = []
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)

    def respond(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers)
        return httpx.Response(200, json={"id": "gpt-4o"})

    router.get("https://gateway.example.test/v1/models/gpt-4o").mock(side_effect=respond)
    spec = ModelSpec.model_validate(
        {
            "provider": "openai",
            "id": "gpt-4o",
            "endpoint": {"base_url": "https://gateway.example.test/v1"},
        }
    )
    with router, httpx.Client() as http:
        lock = resolve_api_model(spec, http=http, verify_api=True, now=NOW)

    assert seen_headers[0]["Authorization"] == f"Bearer {secret}"
    assert lock.revision.note == "exists"
    assert secret not in lock.model_dump_json()


def test_verify_api_404_records_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    router.get("https://api.anthropic.com/v1/models/claude-unknown").mock(
        return_value=httpx.Response(404)
    )
    spec = ModelSpec(provider="anthropic", id="claude-unknown")
    with router, httpx.Client() as http:
        lock = resolve_api_model(spec, http=http, verify_api=True, now=NOW)

    assert lock.revision.note == "not_found"
