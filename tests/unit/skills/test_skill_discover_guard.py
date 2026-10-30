"""A19/A20: native discovery sends remain inside one explicit cost grant."""

from __future__ import annotations

import dataclasses
import gzip
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
from skill_discover_guard import (  # noqa: E402
    Approval,
    BudgetError,
    DiscoverDeadline,
    GuardedClient,
    Ledger,
    PricePolicy,
    identity,
)

from reprollm.discover.client import DiscoverError, request_candidates  # noqa: E402

ENDPOINT = "https://api.deepseek.com/chat/completions"
MESSAGES = [{"role": "system", "content": "JSON rules"}, {"role": "user", "content": "x=1"}]
KEY = "sk-synthetic-private-credential-never-send-in-messages"
pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned paid workers"),
]


@pytest.fixture(autouse=True)
def isolated_mock_routes():
    respx.reset()
    with respx.mock(assert_all_called=False):
        yield


def policy(**changes):
    return dataclasses.replace(
        PricePolicy(
            endpoint=ENDPOINT,
            model="deepseek-flash",
            served_models=("deepseek-flash", "DeepSeek-V4.1-Flash-1017"),
            input_tokens=1048576,
            output_tokens=65536,
            miss_nano=2000,
            hit_nano=40,
            output_nano=8000,
            output_basis="native-default",
            evidence_sha256="e" * 64,
            expires_at=time.time() + 3600,
        ),
        **changes,
    )


def approval(price, **changes):
    return dataclasses.replace(
        Approval(
            approval_id="a" * 32,
            helper_sha256="b" * 64,
            source_sha256="c" * 64,
            messages_sha256=identity(MESSAGES),
            policy_sha256=price.fingerprint,
            budget_nano=4_000_000_000,
            max_attempts=1,
            expires_at=time.time() + 1800,
        ),
        **changes,
    )


def client(tmp_path, *, price=None, grant=None, check=None, **kwargs):
    price = price or policy()
    grant = grant or approval(price)
    ledger = Ledger(tmp_path / "ledger.json", grant, "1" * 32)
    return GuardedClient(
        policy=price,
        approval=grant,
        messages=MESSAGES,
        api_key=KEY,
        ledger=ledger,
        check_current=check or (lambda: None),
        **kwargs,
    )


def native(transport):
    return request_candidates(
        base_url="https://api.deepseek.com",
        api_key=KEY,
        model="deepseek-flash",
        system_prompt=MESSAGES[0]["content"],
        user_content=MESSAGES[1]["content"],
        transport=transport,
    )


def response(content='{"candidates":[]}', usage=None, **extra):
    return httpx.Response(
        200,
        json={
            "model": "deepseek-flash",
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            **({"usage": usage} if usage is not None else {}),
            **extra,
        },
    )


def test_native_body_preserved_reserve_durable_before_delegate(tmp_path):
    def send(request):
        record = json.loads((tmp_path / "ledger.json").read_bytes())
        assert record["attempts"][0]["held_nano"] == 2_621_440_000
        assert record["attempts"][0]["outcome"] == "unknown"
        assert json.loads(request.content) == {
            "model": "deepseek-flash",
            "temperature": 0,
            "messages": MESSAGES,
            "response_format": {"type": "json_object"},
        }
        assert request.headers["Authorization"] == "Bearer " + KEY
        return response()

    route = respx.post(ENDPOINT).mock(side_effect=send)
    with client(tmp_path) as transport:
        assert native(transport).candidates == []
        assert transport.ledger.summary()["held_nano"] == 2_621_440_000
    assert route.call_count == 1
    raw = (tmp_path / "ledger.json").read_text(encoding="utf-8")
    assert KEY not in raw and ENDPOINT not in raw and "x=1" not in raw


@pytest.mark.parametrize("kind", ["invalid", "mode400", "mode500"])
def test_native_retry_denied_before_second_paid_post(tmp_path, kind):
    first = (
        response("invalid")
        if kind == "invalid"
        else httpx.Response(500 if kind == "mode500" else 400, text="response_format rejected")
    )
    route = respx.post(ENDPOINT).mock(return_value=first)
    with client(tmp_path) as transport, pytest.raises(BudgetError, match="attempt_limit"):
        native(transport)
    assert route.call_count == 1


def test_original_three_post_fallback_and_validation_are_not_reimplemented(tmp_path):
    price = policy()
    grant = approval(price, max_attempts=3, budget_nano=8_000_000_000)
    route = respx.post(ENDPOINT).mock(
        side_effect=[httpx.Response(500, text="response_format"), response("invalid"), response()]
    )
    with client(tmp_path, price=price, grant=grant) as transport:
        assert native(transport).candidates == []
        assert transport.ledger.summary()["held_nano"] == 7_864_320_000
    assert route.call_count == 3
    bodies = [json.loads(call.request.content) for call in route.calls]
    assert "response_format" not in bodies[1] and "response_format" not in bodies[2]
    assert len(bodies[2]["messages"]) == 3
    assert bodies[2]["messages"][:2] == MESSAGES
    assert bodies[2]["messages"][2]["role"] == "user"


def test_error_body_choices_do_not_consume_native_candidate_validation_attempt(tmp_path):
    def replies():
        return [
            httpx.Response(
                500,
                json={
                    "error": "response_format rejected",
                    "choices": [{"message": {"content": "invalid"}}],
                },
            ),
            response("invalid"),
            response(),
        ]

    route = respx.post(ENDPOINT).mock(side_effect=replies())
    with httpx.Client() as original:
        assert native(original).candidates == []
    original_bodies = [json.loads(call.request.content) for call in route.calls]
    assert len(original_bodies) == 3
    route.reset()
    route.mock(side_effect=replies())
    price = policy()
    grant = approval(price, max_attempts=3, budget_nano=8_000_000_000)
    with client(tmp_path, price=price, grant=grant) as guarded:
        assert native(guarded).candidates == []
    assert route.call_count == 3
    assert [json.loads(call.request.content) for call in route.calls] == original_bodies


@pytest.mark.parametrize("content", [None, {}, True])
def test_native_nonstring_content_validation_retry_is_preserved(tmp_path, content):
    route = respx.post(ENDPOINT).mock(side_effect=[response(content), response()])
    with httpx.Client() as original:
        assert native(original).candidates == []
    expected = [json.loads(call.request.content) for call in route.calls]
    route.reset()
    route.mock(side_effect=[response(content), response()])
    price = policy()
    grant = approval(price, max_attempts=3, budget_nano=8_000_000_000)
    with client(tmp_path, price=price, grant=grant) as guarded:
        assert native(guarded).candidates == []
    assert [json.loads(call.request.content) for call in route.calls] == expected


@pytest.mark.parametrize("change", ["budget", "expiry", "policy", "messages", "key", "source"])
def test_invalid_grant_or_changed_input_never_delegates(tmp_path, change):
    price = policy()
    grant = approval(price)
    check = None
    if change == "budget":
        grant = dataclasses.replace(grant, budget_nano=2_621_439_999)
    elif change == "expiry":
        grant = dataclasses.replace(grant, expires_at=time.time() - 1)
    elif change == "policy":
        price = dataclasses.replace(price, output_nano=8001)
    elif change == "messages":
        grant = dataclasses.replace(grant, messages_sha256="d" * 64)
    elif change == "key":
        grant = dataclasses.replace(grant, messages_sha256=identity(MESSAGES))
    else:

        def check():
            raise BudgetError("source_changed")

    route = respx.post(ENDPOINT).mock(return_value=response())
    with (
        pytest.raises(BudgetError),
        client(tmp_path, price=price, grant=grant, check=check) as transport,
    ):
        if change == "key":
            transport.post(
                ENDPOINT,
                json={
                    "model": "deepseek-flash",
                    "temperature": 0,
                    "messages": MESSAGES + [{"role": "user", "content": KEY}],
                },
            )
        else:
            native(transport)
    assert route.call_count == 0


@pytest.mark.parametrize(
    "usage, expected",
    [
        (
            {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "prompt_cache_hit_tokens": 20,
                "prompt_cache_miss_tokens": 80,
            },
            240800,
        ),
        ({"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}, 280000),
        ({"prompt_tokens": True, "completion_tokens": 10, "total_tokens": 11}, 2621440000),
        ({"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 111}, 2621440000),
        (
            {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "prompt_cache_hit_tokens": 20,
                "prompt_cache_miss_tokens": 81,
            },
            2621440000,
        ),
    ],
)
def test_typed_usage_only_releases_conservative_reservation(tmp_path, usage, expected):
    respx.post(ENDPOINT).mock(return_value=response(usage=usage))
    with client(tmp_path) as transport:
        native(transport)
        summary = transport.ledger.summary()
    assert summary["held_nano"] == expected
    assert summary["cost_is_estimate"] is True


def test_timeout_holds_reserve_and_new_client_cannot_replay(tmp_path):
    route = respx.post(ENDPOINT).mock(side_effect=httpx.ReadTimeout("private response"))
    price = policy()
    grant = approval(price)
    with (
        client(tmp_path, price=price, grant=grant) as transport,
        pytest.raises(DiscoverError, match="ReadTimeout"),
    ):
        native(transport)
    with client(tmp_path, price=price, grant=grant) as transport:
        with pytest.raises(BudgetError, match="already_submitted"):
            native(transport)
        assert transport.ledger.summary()["held_nano"] == 2621440000
    assert route.call_count == 1


@pytest.mark.parametrize(
    "body",
    [
        {"model": "other", "temperature": 0, "messages": MESSAGES},
        {"model": "deepseek-flash", "temperature": 1, "messages": MESSAGES},
        {
            "model": "deepseek-flash",
            "temperature": 0,
            "messages": MESSAGES,
            "thinking": {"type": "disabled"},
        },
    ],
)
def test_actual_wire_body_not_only_caller_preview_is_checked(tmp_path, body):
    route = respx.post(ENDPOINT).mock(return_value=response())
    with client(tmp_path) as transport, pytest.raises(BudgetError):
        transport.post(ENDPOINT, json=body)
    assert route.call_count == 0


def test_same_approval_cannot_be_reused_by_a_second_operation(tmp_path):
    price = policy()
    grant = approval(price)
    first = Ledger(tmp_path / "ledger.json", grant, "1" * 32)
    first.reserve(price.reserve_nano, 0)
    second = Ledger(tmp_path / "ledger.json", grant, "2" * 32)
    with pytest.raises(BudgetError, match="state_invalid"):
        second.reserve(price.reserve_nano, 0)
    assert first.summary()["attempt_count"] == 1


def test_wall_deadline_interrupts_a_trickling_provider_and_preserves_charge(tmp_path):
    entered = False

    def delayed(request):
        nonlocal entered
        entered = True
        time.sleep(0.5)
        return response()

    route = respx.post(ENDPOINT).mock(side_effect=delayed)
    with client(tmp_path) as transport:
        transport.started = time.monotonic() - 399.95
        started = time.monotonic()
        with pytest.raises(DiscoverDeadline):
            native(transport)
        assert time.monotonic() - started < 0.5
        held = transport.ledger.summary()["held_nano"]
        assert held == 2621440000 if entered else held in {0, 2621440000}
    assert route.call_count <= 1


@pytest.mark.parametrize("encoding", ["literal", "unicode-escaped", "backslash"])
def test_truncated_credential_validation_error_is_never_sent_as_continuation(
    tmp_path, monkeypatch, encoding
):
    secret = (
        "sk-private-" + ("\\" if encoding == "backslash" else "") + "A" * 160 + "-sensitive-tail"
    )
    monkeypatch.setattr(sys.modules[__name__], "KEY", secret)
    candidate = {
        "kind": "parameter",
        "name": "repeat",
        "suggested_field": "custom.repeat",
        "suggested_severity": "WARNING",
        "confidence": secret,
        "rationale": "public",
        "evidence": [],
    }
    price = policy()
    grant = approval(price, max_attempts=3, budget_nano=8_000_000_000)
    content = json.dumps({"candidates": [candidate]})
    if encoding == "unicode-escaped":
        escaped = '"' + "".join(f"\\u{ord(char):04x}" for char in secret) + '"'
        content = content.replace(json.dumps(secret), escaped)
    route = respx.post(ENDPOINT).mock(side_effect=[response(content), response()])
    with client(tmp_path, price=price, grant=grant) as transport, pytest.raises(BudgetError):
        native(transport)
    assert route.call_count == 1
    assert secret not in (tmp_path / "ledger.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("first", ["timeout", "completed"])
def test_same_client_cannot_repeat_a_finished_or_uncertain_native_call(tmp_path, first):
    price = policy()
    grant = approval(price, max_attempts=3, budget_nano=8_000_000_000)
    route = respx.post(ENDPOINT).mock(
        side_effect=[
            httpx.ReadTimeout("uncertain") if first == "timeout" else response(),
            response(),
        ]
    )
    with client(tmp_path, price=price, grant=grant) as transport:
        if first == "timeout":
            with pytest.raises(DiscoverError):
                native(transport)
        else:
            native(transport)
        with pytest.raises(BudgetError, match="already_submitted"):
            native(transport)
    assert route.call_count == 1


def test_httpx_auth_flow_cannot_make_hidden_additional_sends(tmp_path):
    class TwoSendAuth(httpx.Auth):
        def auth_flow(self, request):
            yield request
            yield request

    route = respx.post(ENDPOINT).mock(return_value=response())
    with client(tmp_path) as transport, pytest.raises(BudgetError):
        transport.post(
            ENDPOINT,
            json={
                "model": "deepseek-flash",
                "temperature": 0,
                "messages": MESSAGES,
                "response_format": {"type": "json_object"},
            },
            auth=TwoSendAuth(),
        )
    assert route.call_count == 0


def test_encoded_response_is_not_inflated_before_memory_bound(tmp_path):
    class Encoded(httpx.SyncByteStream):
        def __iter__(self):
            yield gzip.compress(b"x" * (16 * 1024 * 1024))

    route = respx.post(ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            stream=Encoded(),
            headers={"content-encoding": "gzip"},
        )
    )
    with client(tmp_path) as transport, pytest.raises(BudgetError, match="encoded_response"):
        native(transport)
    assert route.call_count == 1
    assert transport.ledger.summary()["held_nano"] == 2621440000


def test_explicit_zero_price_http_endpoint_retains_native_compatible_local_use(tmp_path):
    endpoint = "http://127.0.0.1:7777/v1/chat/completions"
    price = policy(endpoint=endpoint, miss_nano=0, hit_nano=0, output_nano=0)
    grant = approval(price, budget_nano=0)
    route = respx.post(endpoint).mock(return_value=response())
    with client(tmp_path, price=price, grant=grant) as transport:
        result = request_candidates(
            base_url="http://127.0.0.1:7777/v1",
            api_key=KEY,
            model=price.model,
            system_prompt=MESSAGES[0]["content"],
            user_content=MESSAGES[1]["content"],
            transport=transport,
        )
        assert result.candidates == []
        assert transport.ledger.summary()["held_nano"] == 0
    assert route.call_count == 1


def test_global_approval_capacity_is_atomic_for_concurrent_claims(tmp_path):
    for index in range(255):
        (tmp_path / f"existing-{index}.json").write_bytes(b"{}")
    price = policy()

    def claim(letter):
        grant = approval(price, approval_id=letter * 32)
        ledger = Ledger(tmp_path / (grant.approval_id + ".json"), grant, letter * 32)
        try:
            ledger.claim()
        except BudgetError:
            return "capacity"
        return "claimed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(claim, ["a", "b"]))
    assert sorted(results) == ["capacity", "claimed"]
    assert len(list(tmp_path.glob("*.json"))) == 256


def test_approved_provider_identity_is_hashed_in_private_state(tmp_path):
    provider_identity = "selected-machine-identity"
    price = policy(served_models=(provider_identity,))
    grant = approval(price)
    respx.post(ENDPOINT).mock(return_value=response(model=provider_identity))
    with client(tmp_path, price=price, grant=grant) as transport:
        native(transport)
        observation = transport.ledger.summary()["attempts"][0]
    assert observation["served_model_sha256"] == identity(provider_identity)
    assert observation["served_model_matches_policy"]
    assert provider_identity not in (tmp_path / "ledger.json").read_text(encoding="utf-8")


def test_declared_attempt_limit_requires_its_full_worst_case_budget_before_claim(tmp_path):
    price = policy()
    grant = approval(price, max_attempts=3, budget_nano=price.reserve_nano)
    route = respx.post(ENDPOINT).mock(return_value=response())
    with (
        pytest.raises(BudgetError, match="budget_insufficient"),
        client(tmp_path, price=price, grant=grant) as transport,
    ):
        native(transport)
    assert route.call_count == 0 and not (tmp_path / "ledger.json").exists()
