"""SK13 worker protocol validation is separate from CLI or child outcomes."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[3] / "skills/reprollm/scripts"
sys.path.insert(0, str(SCRIPTS))
from skill_request import Reply, encode_reply  # noqa: E402
from skill_runtime_frame import FrameError, validate_frame  # noqa: E402


def frame(**changes: Any) -> dict[str, Any]:
    value = Reply("audit", data={"findings": [{"status": "skipped", "value": False}]}).as_dict()
    value.update(changes)
    return value


def wire(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode()


@pytest.mark.parametrize(
    "code,invocation,gate,complete",
    [
        (0, "handled_result", False, True),
        (1, "handled_result", True, True),
        (2, "user_error", None, False),
        (3, "internal_error", None, False),
    ],
)
def test_normal_cli_results_preserve_all_fields(
    code: int,
    invocation: str,
    gate: bool | None,
    complete: bool,
) -> None:
    expected = frame(
        cli_exit_code=code,
        invocation=invocation,
        gate_failed=gate,
        complete=complete,
        diagnostics=[{"code": "cli_stderr", "text": "safe diagnostic"}],
    )
    actual = validate_frame(wire(expected), expected_action="audit")
    assert actual.as_dict() == expected
    assert actual.child_exit_code is None


def test_original_json_data_is_preserved_without_coercion() -> None:
    expected = {
        "zero": 0,
        "fraction": 0.25,
        "false": False,
        "null": None,
        "unicode": "研究",
        "nested": [1, {}],
    }
    actual = validate_frame(encode_reply(Reply("audit", data=expected)), expected_action="audit")
    assert actual.data == expected
    assert type(actual.data["zero"]) is int and type(actual.data["false"]) is bool


@pytest.mark.parametrize(
    "changes",
    [
        {"schema_version": True},
        {"schema_version": 2},
        {"schema_version": "1"},
        {"action": "doctor"},
        {"action": None},
        {"action": 1},
        {"invocation": "success"},
        {"invocation": False},
        {"cli_exit_code": True},
        {"cli_exit_code": "1"},
        {"cli_exit_code": 1.0},
        {"child_exit_code": False},
        {"child_exit_code": []},
        {"gate_failed": 1},
        {"gate_failed": "yes"},
        {"complete": "yes"},
        {"complete": 1},
        {"needs_input": 0},
        {"needs_authorization": None},
        {"questions": "question"},
        {"questions": [1]},
        {"diagnostics": "warning"},
        {"diagnostics": ["warning"]},
        {"next_cursor": 1},
        {"next_cursor": "../../private/file"},
        {"next_cursor": "x" * 4097},
        {"next_cursor": "abc\n"},
        {"snapshot": 1},
        {"snapshot": "secret"},
        {"future_field": True},
    ],
)
def test_malformed_fixed_fields_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(FrameError, match="^invalid_worker_frame$"):
        validate_frame(wire(frame(**changes)), expected_action="audit")


def test_missing_frame_fields_cannot_be_supplied_by_dataclass_defaults() -> None:
    value = frame()
    for key in value:
        incomplete = copy.deepcopy(value)
        incomplete.pop(key)
        with pytest.raises(FrameError):
            validate_frame(wire(incomplete), expected_action="audit")


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json",
        b"[]",
        b"true",
        b"null",
        b"\xff",
        b'{"action":"audit","action":"doctor"}',
    ],
)
def test_invalid_or_ambiguous_json_is_rejected(raw: bytes) -> None:
    with pytest.raises(FrameError):
        validate_frame(raw, expected_action="audit")


@pytest.mark.parametrize("data", [float("nan"), {"n": float("inf")}, [float("-inf")]])
def test_nonfinite_nested_data_is_not_valid_json(data: Any) -> None:
    with pytest.raises(FrameError):
        validate_frame(wire(frame(data=data)), expected_action="audit")


@pytest.mark.parametrize("invocation", ["user_error", "internal_error"])
def test_none_action_only_represents_an_explicit_error_frame(invocation: str) -> None:
    expected = Reply(
        None, invocation=invocation, complete=False, diagnostics=[{"code": "invalid_json_request"}]
    ).as_dict()
    assert validate_frame(wire(expected), expected_action="audit").as_dict() == expected
    for update in (
        {"data": {}},
        {"complete": True},
        {"cli_exit_code": 2},
        {"gate_failed": False},
        {"child_exit_code": 7},
        {"snapshot": "a" * 64},
        {"next_cursor": "a" * 64 + ":items:0"},
    ):
        with pytest.raises(FrameError):
            validate_frame(wire({**expected, **update}), expected_action="audit")


def test_valid_snapshot_cursor_and_child_outcome_are_kept_separate() -> None:
    expected = frame(
        child_exit_code=-15,
        cli_exit_code=None,
        gate_failed=None,
        complete=False,
        snapshot="a" * 64,
        next_cursor="a" * 64 + ":fragment:65536",
    )
    assert validate_frame(wire(expected), expected_action="audit").as_dict() == expected
