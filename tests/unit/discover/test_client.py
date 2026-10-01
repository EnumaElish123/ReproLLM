"""M7-T04: JSON-mode fallback does not consume the schema-validation retry."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from reprollm.discover.client import DiscoverError, DiscoverResponse, request_candidates

_URL = "https://llm.example.com/v1/chat/completions"


def _completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _request() -> DiscoverResponse:
    return request_candidates(
        base_url="https://llm.example.com/v1",
        api_key="fake-test-key",
        model="test-model",
        system_prompt="Return candidate JSON.",
        user_content="Public source.",
    )


@pytest.mark.parametrize("reject_json_mode", [False, True])
@pytest.mark.parametrize("invalid", ["not json", '{"candidates": "not a list"}'])
@respx.mock
def test_one_validation_retry_succeeds_after_optional_json_mode_fallback(
    reject_json_mode: bool, invalid: str
) -> None:
    valid = '{"candidates": []}'
    responses = [_completion(invalid), _completion(valid)]
    if reject_json_mode:
        responses.insert(0, httpx.Response(400, text="response_format is unsupported"))
    route = respx.post(_URL).mock(side_effect=responses)

    result = _request()

    assert result.candidates == []
    assert result.raw_text == valid
    assert route.call_count == (3 if reject_json_mode else 2)
    bodies = [json.loads(call.request.content) for call in route.calls]
    assert bodies[0]["response_format"] == {"type": "json_object"}
    if reject_json_mode:
        assert all("response_format" not in body for body in bodies[1:])
    assert len(bodies[-1]["messages"]) == 3
    assert "not valid JSON for the schema" in bodies[-1]["messages"][-1]["content"]
    assert bodies[-1]["messages"][:2] == bodies[0]["messages"]


@pytest.mark.parametrize("reject_json_mode", [False, True])
@respx.mock
def test_two_invalid_responses_stop_and_preserve_last_raw(reject_json_mode: bool) -> None:
    last_raw = "second invalid response"
    responses = [_completion("first invalid response"), _completion(last_raw)]
    if reject_json_mode:
        responses.insert(0, httpx.Response(400, text="response_format is unsupported"))
    route = respx.post(_URL).mock(side_effect=responses)

    with pytest.raises(DiscoverError, match="invalid candidate JSON") as excinfo:
        _request()

    assert excinfo.value.raw_text == last_raw
    assert route.call_count == (3 if reject_json_mode else 2)


@respx.mock
def test_json_mode_rejection_is_retried_only_once() -> None:
    route = respx.post(_URL).mock(
        return_value=httpx.Response(400, text="response_format is unsupported")
    )

    with pytest.raises(DiscoverError, match="HTTP 400"):
        _request()

    assert route.call_count == 2


@respx.mock
def test_unrelated_http_failure_does_not_use_validation_retry() -> None:
    route = respx.post(_URL).mock(return_value=httpx.Response(429, text="Rate limited"))

    with pytest.raises(DiscoverError, match="HTTP 429"):
        _request()

    assert route.call_count == 1
