"""The paid grant parser is portable, finite and does not create an HTTP client."""

from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
from skill_discover_guard import BudgetError, parse_grant  # noqa: E402
from tests.unit.skills.test_skill_discover_guard import approval, policy  # noqa: E402


def grant():
    price = policy()
    return {
        "schema_version": 1,
        "currency": "CNY",
        "policy": {**dataclasses.asdict(price), "served_models": list(price.served_models)},
        "approval": dataclasses.asdict(approval(price)),
    }


def test_exact_approved_policy_and_user_grant_round_trip_without_client(monkeypatch):
    monkeypatch.setattr(httpx.Client, "__init__", lambda *a, **kw: pytest.fail("parse made Client"))
    raw = grant()
    before = copy.deepcopy(raw)
    price, accepted = parse_grant(raw)
    assert accepted.policy_sha256 == price.fingerprint
    assert price.reserve_nano == 2621440000
    assert raw == before


@pytest.mark.parametrize(
    "section, field, value",
    [
        (None, "schema_version", True),
        (None, "schema_version", 1.0),
        (None, "currency", "USD"),
        (None, "unknown", "not accepted"),
        ("approval", "budget_nano", True),
        ("approval", "max_attempts", True),
        ("approval", "max_attempts", 4),
        ("approval", "source_sha256", None),
        ("approval", "expires_at", float("inf")),
        ("policy", "endpoint", "https://user:secret@api.deepseek.com/chat/completions"),
        ("policy", "endpoint", "http://api.deepseek.com/chat/completions"),
        ("policy", "input_tokens", True),
        ("policy", "output_tokens", -1),
        ("policy", "output_basis", "silently-disable-thinking"),
        ("policy", "served_models", "deepseek-flash"),
        ("policy", "output_nano", 8001),
    ],
)
def test_invalid_or_changed_price_grant_is_rejected_without_effects(section, field, value):
    raw = grant()
    (raw if section is None else raw[section])[field] = value
    with pytest.raises(BudgetError):
        parse_grant(raw)


@pytest.mark.parametrize("action", ["discover", "discover.preview"])
def test_unsupported_paper_needs_no_project_installation_or_network_grant(action):
    from reprollm_skill import handle

    def forbidden(request):
        pytest.fail("unsupported paper analysis must not prepare or execute a tool")

    reply = handle(
        json.dumps(
            {
                "schema_version": 1,
                "action": action,
                "options": {"paper": "public-paper"},
            }
        ).encode(),
        executor=forbidden,
        available_actions=frozenset({action}),
    )
    assert reply.invocation == "user_error" and reply.cli_exit_code == 2
    assert not reply.needs_authorization and not reply.needs_input
    assert any("Paper" in item.get("text", "") for item in reply.diagnostics)
