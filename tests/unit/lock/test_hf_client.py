from __future__ import annotations

import httpx
import pytest
import respx

from reprollm.lock.hf_client import (
    FileTooLarge,
    HfClient,
    HfForbidden,
    HfNetworkError,
)


def test_model_and_dataset_info_use_minimal_fixture(hf_mock: respx.MockRouter) -> None:
    with httpx.Client() as http:
        client = HfClient(http, token=None)
        model = client.model_info("Qwen/Qwen3-32B")
        dataset = client.dataset_info("cais/mmlu")

    assert model.sha == "8fa23e7c1a0000000000000000000000000000aa"
    assert model.siblings == ["config.json", "tokenizer.json", "tokenizer_config.json"]
    assert dataset.sha == "b77a9100b00000000000000000000000000000bb"


def test_fetch_file_reads_small_fixture(hf_mock: respx.MockRouter) -> None:
    with httpx.Client() as http:
        content = HfClient(http, token=None).fetch_file(
            "model",
            "Qwen/Qwen3-32B",
            "8fa23e7c1a0000000000000000000000000000aa",
            "config.json",
        )

    assert b'"model_type": "qwen3"' in content


def test_retries_server_and_connection_errors_with_required_backoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    effects: list[httpx.Response | Exception] = [
        httpx.Response(503),
        httpx.ConnectError("temporary failure"),
        httpx.Response(
            200,
            json={"sha": "607a30d783dfa663caf39e06633721c8d4cfcd7e", "siblings": []},
        ),
    ]
    calls: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        effect = effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect

    router.get("https://huggingface.co/api/models/gpt2/revision/main").mock(side_effect=respond)
    delays: list[float] = []
    monkeypatch.setattr("reprollm.lock.hf_client.time.sleep", delays.append)

    with router, httpx.Client() as http:
        info = HfClient(http, token=None).model_info("gpt2")

    assert info.sha == "607a30d783dfa663caf39e06633721c8d4cfcd7e"
    assert len(calls) == 3
    assert delays == [0.5, 1.5]


def test_stops_after_two_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    calls: list[httpx.Request] = []

    def fail(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectError("still offline")

    router.get("https://huggingface.co/api/models/gpt2/revision/main").mock(side_effect=fail)
    monkeypatch.setattr("reprollm.lock.hf_client.time.sleep", lambda _delay: None)

    with router, httpx.Client() as http, pytest.raises(HfNetworkError) as caught:
        HfClient(http, token=None).model_info("gpt2")

    assert caught.value.source == "network_error"
    assert len(calls) == 3


def test_forbidden_error_never_contains_token(
    hf_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = "hf_super_secret_value"
    monkeypatch.setenv("HF_TOKEN", token)

    with httpx.Client() as http, pytest.raises(HfForbidden) as caught:
        HfClient(http, token=None).model_info("meta-llama/Llama-3.1-8B-Instruct")

    request = hf_mock.calls[-1].request
    assert request.headers["Authorization"] == f"Bearer {token}"
    assert caught.value.source == "hf_api_forbidden"
    assert token not in str(caught.value)
    assert token not in repr(caught.value)


def test_empty_token_does_not_add_authorization(hf_mock: respx.MockRouter) -> None:
    with httpx.Client() as http:
        HfClient(http, token="   ").model_info("gpt2")

    assert "Authorization" not in hf_mock.calls[-1].request.headers


def test_hf_endpoint_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_ENDPOINT", "https://hf-mirror.example.test/")
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    router.get("https://hf-mirror.example.test/api/models/gpt2/revision/main").mock(
        return_value=httpx.Response(200, json={"sha": "abc123", "siblings": []})
    )

    with router, httpx.Client() as http:
        info = HfClient(http, token=None).model_info("gpt2")

    assert info.sha == "abc123"


@pytest.mark.parametrize("content_length", [9, None])
def test_fetch_file_enforces_size_limit(content_length: int | None) -> None:
    headers = {} if content_length is None else {"Content-Length": str(content_length)}
    router = respx.MockRouter(assert_all_called=False, assert_all_mocked=True)
    router.get("https://huggingface.co/gpt2/resolve/abc/config.json").mock(
        return_value=httpx.Response(200, headers=headers, content=b"123456789")
    )

    with router, httpx.Client() as http, pytest.raises(FileTooLarge):
        HfClient(http, token=None).fetch_file("model", "gpt2", "abc", "config.json", max_bytes=8)
