"""The new run format distinguishes baseline bytes from an unchecked final state."""

from __future__ import annotations

import copy
import json

import pytest

from reprollm.core.errors import UserError
from reprollm.run.codec import parse_run_record


def new_record() -> dict:
    return {
        "schema_version": 2,
        "reprollm_version": "0.7.0",
        "run_id": "20261014T010000Z-abcdef",
        "status": "running",
        "command": {"argv": ["python"], "cwd": "."},
        "input_capture": {
            "baseline_phase": "pre_child",
            "check_phase": "post_child",
            "consumption": "unverified",
            "checks": [
                {
                    "path": "config.json",
                    "origin": "declared",
                    "before": {
                        "availability": "present",
                        "sha256": "sha256:" + "a" * 64,
                        "size_bytes": 21,
                    },
                    "after": {"availability": "unavailable", "sha256": None, "size_bytes": None},
                    "change": "unknown",
                }
            ],
        },
    }


def test_new_schema_roundtrip_preserves_unverified_baseline() -> None:
    parsed = parse_run_record(json.dumps(new_record()))
    assert parsed.schema_version == 2
    assert parsed.input_capture.consumption == "unverified"
    assert parsed.input_capture.checks[0].before.sha256 == "sha256:" + "a" * 64
    assert parsed.input_capture.checks[0].after.availability == "unavailable"
    assert parse_run_record(parsed.model_dump_json()) == parsed


@pytest.mark.parametrize(
    "path", ["/private/config.json", "../config.json", "a/../b", "C:\\private\\config.json"]
)
def test_input_checks_refuse_paths_outside_project(path: str) -> None:
    data = new_record()
    data["input_capture"]["checks"][0]["path"] = path
    with pytest.raises(UserError):
        parse_run_record(json.dumps(data))


def test_duplicate_baseline_paths_are_rejected() -> None:
    data = new_record()
    data["input_capture"]["checks"].append(copy.deepcopy(data["input_capture"]["checks"][0]))
    with pytest.raises(UserError):
        parse_run_record(json.dumps(data))


def test_unchecked_final_input_cannot_be_claimed_unchanged() -> None:
    data = new_record()
    data["input_capture"]["checks"][0]["change"] = "unchanged"
    with pytest.raises(UserError):
        parse_run_record(json.dumps(data))


def test_file_reference_must_match_its_recorded_baseline() -> None:
    data = new_record()
    data["files"] = [
        {
            "path": "config.json",
            "origin": "declared",
            "sha256": "sha256:" + "b" * 64,
            "size_bytes": 21,
        }
    ]
    with pytest.raises(UserError):
        parse_run_record(json.dumps(data))
