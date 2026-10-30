"""Validate the worker transport frame without altering its business JSON data."""

from __future__ import annotations

import dataclasses
import json
import math
import re
from typing import Any

from skill_request import MAX_REPLY_BYTES, Reply

_FIELDS = frozenset(field.name for field in dataclasses.fields(Reply))
_INVOCATIONS = frozenset({"handled_result", "user_error", "internal_error", "blocked"})
_CURSOR = re.compile(r"([0-9a-f]{64}):(items|fragment):[0-9]{1,12}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class FrameError(ValueError):
    """A fixed diagnostic that excludes untrusted worker values and exceptions."""

    def __init__(self) -> None:
        super().__init__("invalid_worker_frame")


def _require(condition: bool) -> None:
    if not condition:
        raise FrameError


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        _require(key not in value)
        value[key] = item
    return value


def _constant(value: str) -> None:
    raise FrameError


def _finite(value: Any, depth: int = 0) -> None:
    _require(depth <= 128)
    if isinstance(value, float):
        _require(math.isfinite(value))
    elif isinstance(value, dict):
        for child in value.values():
            _finite(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _finite(child, depth + 1)


def validate_frame(raw: bytes, *, expected_action: str) -> Reply:
    """Accept one complete frame from the expected worker, without coercion."""
    try:
        _require(len(raw) <= MAX_REPLY_BYTES)
        value = json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)
        _require(isinstance(value, dict) and set(value) == _FIELDS)
        _require(type(value["schema_version"]) is int and value["schema_version"] == 1)
        _require(isinstance(value["invocation"], str) and value["invocation"] in _INVOCATIONS)
        for field in ("complete", "needs_input", "needs_authorization"):
            _require(type(value[field]) is bool)
        for field in ("cli_exit_code", "child_exit_code"):
            _require(value[field] is None or type(value[field]) is int)
        _require(value["gate_failed"] is None or type(value["gate_failed"]) is bool)
        _require(isinstance(value["diagnostics"], list))
        _require(all(isinstance(item, dict) for item in value["diagnostics"]))
        _require(isinstance(value["questions"], list))
        _require(all(isinstance(item, str) for item in value["questions"]))
        snapshot, cursor = value["snapshot"], value["next_cursor"]
        _require(
            snapshot is None or isinstance(snapshot, str) and bool(_SHA256.fullmatch(snapshot))
        )
        _require(cursor is None or isinstance(cursor, str) and len(cursor) <= 4096)
        if cursor is not None:
            match = _CURSOR.fullmatch(cursor)
            _require(match is not None)
            assert match is not None
            _require(snapshot == match[1] and not value["complete"])
        if value["action"] is None:
            _require(value["invocation"] in {"user_error", "internal_error"})
            _require(not value["complete"] and value["data"] is None)
            _require(
                all(
                    value[field] is None
                    for field in (
                        "cli_exit_code",
                        "gate_failed",
                        "child_exit_code",
                        "next_cursor",
                        "snapshot",
                    )
                )
            )
        else:
            _require(isinstance(value["action"], str) and value["action"] == expected_action)
        _finite(value)
        return Reply(**value)
    except (UnicodeError, ValueError, TypeError, KeyError, RecursionError):
        raise FrameError from None
