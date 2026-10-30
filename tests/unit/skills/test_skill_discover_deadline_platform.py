"""Reject Windows deadline use before resolving POSIX signal attributes."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"))
import skill_discover_guard as guard  # noqa: E402


def test_windows_deadline_refuses_before_posix_signal_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unsupported deadline touched a POSIX signal interface")

    monkeypatch.setattr(guard, "sys", SimpleNamespace(platform="win32"), raising=False)
    monkeypatch.setattr(guard.signal, "setitimer", forbidden, raising=False)
    monkeypatch.setattr(guard.signal, "getitimer", forbidden, raising=False)
    monkeypatch.setattr(guard.signal, "signal", forbidden)
    with (
        pytest.raises(guard.BudgetError, match="discover_deadline_platform_unavailable"),
        guard._deadline(1),
    ):
        pytest.fail("unsupported deadline entered provider work")
