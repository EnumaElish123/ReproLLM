"""Skill bootstrap tests have the same offline boundary as product tests."""

from __future__ import annotations

from typing import NoReturn
from urllib.request import OpenerDirector

import pytest


@pytest.fixture(autouse=True)
def reject_unmocked_bootstrap_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args: object, **kwargs: object) -> NoReturn:
        pytest.fail("Skill tests must mock bootstrap downloads; network is forbidden.")

    monkeypatch.setattr(OpenerDirector, "open", reject)
