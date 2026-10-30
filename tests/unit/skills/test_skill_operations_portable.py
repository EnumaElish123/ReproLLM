"""Untested background platforms reject work without installing or changing state."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
import skill_operations as operations  # noqa: E402
from skill_request import Grants, Request  # noqa: E402


@pytest.mark.parametrize("platform", ["win32", "darwin"])
def test_unsupported_start_and_query_never_install_or_create_state(tmp_path, monkeypatch, platform):
    monkeypatch.setattr(operations.sys, "platform", platform)
    home = tmp_path / "not-created"

    def forbidden(*a, **kw):
        pytest.fail("Unsupported background work must not acquire an environment lease")

    request = Request(
        "lock", str(tmp_path), {"offline": True, "hash_large_files": True}, Grants(write=True)
    )
    result = operations.start(
        request,
        home=home,
        root=tmp_path,
        identity="a" * 64,
        manager=object(),
        environment_name="b" * 32,
        lease_factory=forbidden,
    )
    assert result.invocation == "blocked" and not home.exists()
    result = operations.control(
        Request("operation.status", str(tmp_path), {"operation_id": "c" * 32}),
        home=home,
        root=tmp_path,
    )
    assert result is not None and result.invocation == "blocked" and not home.exists()
    assert {"code": "operation_platform_unavailable"} in result.diagnostics
