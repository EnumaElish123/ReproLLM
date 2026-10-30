"""Discovery shares the owned worker protocol, never the short CLI timeout."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/reprollm/scripts"))
import skill_operations as operations  # noqa: E402
import skill_runtime as runtime  # noqa: E402
from skill_request import Grants, Request  # noqa: E402
from tests.unit.skills import test_skill_operations as contract  # noqa: E402
from tests.unit.skills.test_skill_discover_guard import approval, policy  # noqa: E402

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned worker lifecycle"),
]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    return contract.setup.__wrapped__(tmp_path, monkeypatch)


def approved(root):
    price = policy()
    grant = approval(price)
    return Request(
        "discover",
        str(root),
        {"experimental": True},
        Grants(
            write=True,
            network=True,
            paid_discover={
                "schema_version": 1,
                "currency": "CNY",
                "policy": {**dataclasses.asdict(price), "served_models": list(price.served_models)},
                "approval": dataclasses.asdict(grant),
            },
        ),
    )


def test_discover_routes_to_long_worker_but_preview_to_original_collector(setup):
    assert runtime.long_operation(approved(setup["root"]))
    assert not runtime.long_operation(Request("discover.preview", str(setup["root"])))
    assert {"discover", "discover.preview"}.issubset(runtime.AVAILABLE_ACTIONS)


def test_preparation_is_zero_send_start_replay_and_status_preserve_owned_identity(setup):
    request = approved(setup["root"])
    prepared = contract.start(setup, request)
    token = contract.operation_id(prepared)
    assert prepared.data["operation"]["kind"] == "discover"
    assert prepared.data["operation"]["state"] == "PREPARED"
    assert setup["launches"] == []
    request = dataclasses.replace(request, options={**request.options, "operation_id": token})
    started = contract.start(setup, request)
    assert contract.operation_id(started) == token and len(setup["launches"]) == 1
    replay = contract.start(setup, request)
    assert contract.operation_id(replay) == token and len(setup["launches"]) == 1
    assert (
        contract.control(setup, "operation.status", token).data["operation"]["kind"] == "discover"
    )


def test_missing_cost_approval_never_creates_or_launches_an_operation(setup):
    request = dataclasses.replace(approved(setup["root"]), grants=Grants(write=True, network=True))
    reply = contract.start(setup, request)
    assert reply.invocation == "blocked" and reply.needs_authorization
    assert not setup["home"].exists() and setup["launches"] == []


def test_result_frame_cannot_switch_native_action(setup):
    value = contract.Reply("discover", cli_exit_code=0, data={"candidates": []}).as_dict()
    assert operations._safe_reply(value, expected_action="discover").action == "discover"
    with pytest.raises(ValueError):
        operations._safe_reply(value, expected_action="lock")


def test_unknown_operation_status_and_result_retain_global_reserved_cost(setup):
    from skill_discover_guard import Ledger, parse_grant

    request = approved(setup["root"])
    prepared = contract.start(setup, request)
    token = contract.operation_id(prepared)
    assert prepared.data["budget"]["attempt_count"] == 0
    price, accepted = parse_grant(request.grants.paid_discover)
    directory = setup["home"] / "operations/discovery-budgets"
    operations._directory(directory)
    ledger = Ledger(directory / (accepted.approval_id + ".json"), accepted, token)
    ledger.claim()
    ledger.reserve(price.reserve_nano, 0)
    contract.edit_record(setup, token, state="UNKNOWN", execution_started=True)
    for action in ("operation.status", "operation.cancel", "operation.result"):
        reply = contract.control(setup, action, token)
        assert reply.data["budget"]["held_nano"] == 2621440000
        assert reply.data["budget"]["attempt_count_basis"] == "reserved_or_submitted"
        assert reply.data["budget"]["confirmed_response_count"] == 0
        assert reply.data["budget"]["charge_uncertain"]
    assert setup["launches"] == [] and ledger.summary()["attempt_count"] == 1
