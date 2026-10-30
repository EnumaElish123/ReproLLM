"""SK16 online lock uses the existing owned-worker protocol without new effects."""

from __future__ import annotations

import dataclasses
import sys

import httpx
import pytest
from tests.unit.skills import test_skill_operations as contract

Grants = contract.Grants
Request = contract.Request

pytestmark = [
    pytest.mark.linux_only,
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux owned worker lifecycle"),
]


@pytest.fixture
def setup(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Preparing/simulating an online operation must not construct an HTTP client")

    monkeypatch.setattr(httpx, "Client", forbidden)
    return contract.setup.__wrapped__(tmp_path, monkeypatch)


@pytest.mark.parametrize("preview", [False, True])
def test_online_without_large_hash_prepares_no_job_and_replay_never_relaunches(setup, preview):
    request = Request(
        "lock",
        str(setup["root"]),
        {"preview": preview},
        Grants(write=not preview, network=True),
    )
    prepared = contract.start(setup, request)
    token = contract.operation_id(prepared)
    assert prepared.data["operation"]["state"] == "PREPARED"
    assert prepared.data["operation"]["kind"] == "lock"
    assert not prepared.data["operation"]["execution_started"]
    assert setup["launches"] == []
    request = dataclasses.replace(request, options={**request.options, "operation_id": token})
    started = contract.start(setup, request)
    assert contract.operation_id(started) == token and len(setup["launches"]) == 1
    replay = contract.start(setup, request)
    assert contract.operation_id(replay) == token and len(setup["launches"]) == 1


def test_network_grant_revocation_before_launch_preserves_prepared_claim(setup):
    request = Request("lock", str(setup["root"]), {}, Grants(write=True, network=True))
    token = contract.operation_id(contract.start(setup, request))
    path = contract.record_path(setup, token)
    before = path.read_bytes()
    denied = contract.start(
        setup,
        dataclasses.replace(
            request,
            options={"operation_id": token},
            grants=Grants(write=True),
        ),
    )
    assert denied.invocation == "blocked" and denied.needs_authorization
    assert path.read_bytes() == before and setup["launches"] == []


def test_online_check_remains_short_and_creates_no_operation(setup):
    request = Request("lock", str(setup["root"]), {"check": True})
    result = contract.start(setup, request)
    assert result.invocation == "blocked"
    assert {"code": "operation_kind_unavailable"} in result.diagnostics
    assert not setup["home"].exists() and setup["launches"] == []
