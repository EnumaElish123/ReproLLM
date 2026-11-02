"""Public cancellation types require no process observation or signal support."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"))


@pytest.mark.parametrize(
    "value", [None, {}, [], {"phase": []}, {"phase": {"bad": "value"}}, {"phase": 9}]
)
def test_public_projection_refuses_untyped_phase(value):
    result = importlib.import_module("skill_run_cancel").public_summary(value)
    assert result["phase"] == "unknown"
