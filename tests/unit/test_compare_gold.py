"""VOPT-03: the comparison CLI must fail closed on every semantic delta."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _run(tmp_path: Path, expected: Any, actual: Any, *flags: str) -> tuple[int, dict[str, Any]]:
    left, right = tmp_path / "expected.json", tmp_path / "actual.json"
    left.write_text(json.dumps(expected), encoding="utf-8")
    right.write_text(json.dumps(actual), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/compare_gold.py"), str(left), str(right), *flags],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.stdout, result.stderr
    assert left.read_text() == json.dumps(expected), "gold was modified"
    assert right.read_text() == json.dumps(actual), "observation was modified"
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    assert str(tmp_path) not in result.stdout
    return result.returncode, report


def test_identical_documents_pass_with_hashes_not_duplicate_payloads(tmp_path: Path) -> None:
    document = {"schema_version": 1, "findings": [{"rule_id": "code.git_repo"}]}
    code, report = _run(tmp_path, document, document)
    assert code == 0
    assert report["status"] == "PASS"
    assert report["differences"] == []
    assert report["expected_sha256"] == hashlib.sha256(json.dumps(document).encode()).hexdigest()
    assert report["expected_sha256"] == report["actual_sha256"]
    assert "findings" not in report


def test_equal_counts_do_not_hide_any_nested_gold_delta(tmp_path: Path) -> None:
    expected = {
        "schema_version": 1,
        "summary": {"warning": 1},
        "findings": [{"rule_id": "env.x", "hint": "Pin it", "line": 12}],
        "hints": {"providers": ["a", "b"], "adapter": True},
        "removed": None,
    }
    actual = copy.deepcopy(expected)
    actual["findings"][0].update(hint="Different hint", line=13)
    actual["hints"] = {"providers": ["b", "a"], "adapter": 1}
    del actual["removed"]
    actual["added"] = None
    code, report = _run(tmp_path, expected, actual)
    assert code == 1
    assert report["status"] == "FAIL"
    assert {(item["pointer"], item["kind"]) for item in report["differences"]} == {
        ("/findings/0/hint", "value"),
        ("/findings/0/line", "value"),
        ("/hints/providers/0", "value"),
        ("/hints/providers/1", "value"),
        ("/hints/adapter", "type"),
        ("/removed", "missing"),
        ("/added", "unexpected"),
    }


def test_lists_keep_order_length_and_nested_metadata(tmp_path: Path) -> None:
    expected = {"schema_version": 1, "items": [{"generated_at": "a"}, "tail"]}
    actual = {"schema_version": 1, "items": [{"generated_at": "b"}]}
    code, report = _run(tmp_path, expected, actual)
    assert code == 1
    assert {item["pointer"] for item in report["differences"]} == {
        "/items/0/generated_at",
        "/items/1",
    }


def _audit() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "reprollm_version": "0.1.0",
        "generated_at": "2026-01-01T00:00:00Z",
        "target": ".",
        "level": 0,
        "profiles": {"declared": [], "detected": []},
        "documents": {"manifest": None, "lock": None, "runs": 0},
        "summary": {
            "critical": 0,
            "warning": 0,
            "info": 0,
            "pass": 0,
            "suppressed": 0,
            "skipped": 0,
        },
        "findings": [],
    }


def test_audit_metadata_requires_explicit_opt_in(tmp_path: Path) -> None:
    expected = _audit()
    actual = {**expected, "generated_at": "2026-02-01T00:00:00Z", "reprollm_version": "0.2.0"}
    assert _run(tmp_path, expected, actual)[0] == 1
    code, report = _run(tmp_path, expected, actual, "--audit-metadata")
    assert code == 0
    assert report["ignored_root_fields"] == ["generated_at", "reprollm_version"]
    actual["target"] = "different"
    assert _run(tmp_path, expected, actual, "--audit-metadata")[0] == 1


def test_metadata_mode_does_not_normalize_or_fill_missing_report_fields(tmp_path: Path) -> None:
    expected = _audit()
    actual = copy.deepcopy(expected)
    del actual["summary"]["pass"]
    assert _run(tmp_path, expected, actual, "--audit-metadata")[0] == 1


@pytest.mark.parametrize(
    "document", [None, [], {}, {"schema_version": True}, {"schema_version": 2}]
)
def test_invalid_documents_are_not_passing_comparisons(tmp_path: Path, document: Any) -> None:
    code, report = _run(tmp_path, document, document)
    assert code == 2
    assert report["status"] == "INVALID_INPUT"


def test_audit_metadata_mode_rejects_non_audit_documents(tmp_path: Path) -> None:
    code, report = _run(tmp_path, {"schema_version": 1}, {"schema_version": 1}, "--audit-metadata")
    assert code == 2
    assert report["status"] == "INVALID_INPUT"


@pytest.mark.parametrize(
    "content",
    [
        "{",
        '{"schema_version":1,"x":1,"x":2}',
        '{"schema_version":1,"x":NaN}',
        '{"schema_version":1,"x":1e999}',
    ],
)
def test_bad_json_produces_safe_machine_readable_failure(tmp_path: Path, content: str) -> None:
    path = tmp_path / "sensitive-filename.json"
    path.write_text(content)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/compare_gold.py"), str(path), str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "INVALID_INPUT"
    assert str(path) not in result.stdout + result.stderr


def test_comparison_does_not_copy_sensitive_values_or_keys(tmp_path: Path) -> None:
    planted = "sk-" + "a" * 32
    left = {"schema_version": 1, "api_key": planted, planted: False}
    right = {"schema_version": 1, "api_key": "changed", planted: True}
    code, report = _run(tmp_path, left, right)
    assert code == 1
    assert len(report["differences"]) == 2
    assert planted not in json.dumps(report)


def test_missing_file_is_reported_without_traceback_or_path(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/compare_gold.py"), str(path), str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "INVALID_INPUT"
    assert str(path) not in result.stdout + result.stderr


def test_distinct_json_numbers_do_not_collapse_through_float_rounding(tmp_path: Path) -> None:
    expected, actual = tmp_path / "expected.json", tmp_path / "actual.json"
    expected.write_text('{"schema_version":1,"score":1.0000000000000001}')
    actual.write_text('{"schema_version":1,"score":1.0}')
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/compare_gold.py"), str(expected), str(actual)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["differences"] == [{"pointer": "/score", "kind": "value"}]
