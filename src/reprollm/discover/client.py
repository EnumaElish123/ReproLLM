"""OpenAI-compatible chat-completion client for discover (spec §20.3, M7-T04).

One request at temperature 0 in JSON mode when supported (retried once
without it when the endpoint rejects the field). Invalid candidate JSON gets
exactly one retry with the validation error appended; a second failure raises
:class:`DiscoverError` carrying the raw response text (the caller saves it and
exits 3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from reprollm.schemas.discover_candidates import Candidate

_TIMEOUT = 120.0


class DiscoverError(Exception):
    """The discovery request failed or produced unusable output."""

    def __init__(self, message: str, raw_text: str = "") -> None:
        super().__init__(message)
        self.raw_text = raw_text


@dataclass(frozen=True)
class DiscoverResponse:
    model: str
    raw_text: str
    candidates: list[Candidate]


def request_candidates(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_content: str,
    transport: httpx.Client | None = None,
) -> DiscoverResponse:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    def call(with_json_mode: bool) -> tuple[str, str]:
        body: dict[str, Any] = {
            "model": model,
            "temperature": 0,
            "messages": messages,
        }
        if with_json_mode:
            body["response_format"] = {"type": "json_object"}
        response = _post(url, headers, body, transport)
        try:
            document = response.json()
        except ValueError as exc:
            raise DiscoverError(f"non-JSON HTTP response: {response.text[:200]}") from exc
        return document["choices"][0]["message"]["content"], document.get("model", model)

    raw_text = ""
    json_mode = True
    invalid_responses = 0
    for attempt in range(3):
        try:
            raw_text, _served = call(json_mode)
        except DiscoverError as exc:
            if json_mode and "response_format" in str(exc) and attempt == 0:
                json_mode = False  # endpoint rejects JSON mode; retry without
                continue
            raise
        candidates, error = _parse(raw_text)
        if candidates is not None:
            return DiscoverResponse(model=model, raw_text=raw_text, candidates=candidates)
        # An unsupported JSON mode is not a candidate-validation attempt.
        invalid_responses += 1
        if invalid_responses == 2:
            raise DiscoverError(f"invalid candidate JSON: {error}", raw_text=raw_text)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Your previous reply was not valid JSON for the schema: {error}. "
                    "Reply again with JSON only."
                ),
            }
        )
    raise DiscoverError("unreachable", raw_text=raw_text)  # pragma: no cover


def _post(
    url: str, headers: dict[str, str], body: dict[str, Any], transport: httpx.Client | None
) -> httpx.Response:
    client = transport
    owned = False
    if client is None:
        client = httpx.Client(timeout=_TIMEOUT)
        owned = True
    try:
        response = client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise DiscoverError(f"request failed: {type(exc).__name__}") from exc
    finally:
        if owned:
            client.close()
    if response.status_code >= 400:
        raise DiscoverError(f"HTTP {response.status_code}: {response.text[:200]}")
    return response


def _parse(raw: str) -> tuple[list[Candidate] | None, Exception | None]:
    try:
        payload = json.loads(raw)
        raw_list = payload["candidates"]
        if not isinstance(raw_list, list):
            raise ValueError("'candidates' must be a list")
        # The model proposes content only; ids are computed locally in
        # candidates.finalize, so parse with a placeholder id.
        candidates = [Candidate.model_validate({**item, "id": "pending"}) for item in raw_list]
        return candidates, None
    except Exception as exc:  # noqa: BLE001 - surfaced as DiscoverError context
        return None, exc
