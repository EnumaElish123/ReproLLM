"""D-39: every run reader rejects future schemas with safe upgrade guidance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from reprollm.cli.main import cli
from reprollm.core.errors import UserError
from reprollm.diff.inputs import load_input
from reprollm.run.codec import parse_run_record
from reprollm.run.reader import list_runs, read_run

CANARY = "S3B_PRIVATE_FUTURE_PAYLOAD"


def _project(root: Path, version: int) -> tuple[str, Path, bytes]:
    (root / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: reader}\nexperiment: {profiles: []}\n",
        encoding="utf-8",
    )
    run_id = "20261014T000000Z-000001"
    folder = root / ".reprollm/runs" / run_id
    folder.mkdir(parents=True)
    raw = (
        json.dumps(
            {
                "schema_version": version,
                "reprollm_version": "0.6.1",
                "run_id": run_id,
                "status": "completed",
                "exit_code": 0,
                "command": {"argv": ["python", "child.py"], "cwd": "."},
                "future_payload": {"secret": CANARY, "machine_path": str(root)},
            },
            sort_keys=True,
        )
        + "\n"
    ).encode()
    path = folder / "run.json"
    path.write_bytes(raw)
    return run_id, path, raw


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize("selected", [False, True])
def test_export_future_run_is_safe_upgrade_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    version: int,
    selected: bool,
) -> None:
    run_id, path, raw = _project(tmp_path, version)
    monkeypatch.chdir(tmp_path)
    arguments = ["reprollm", "export"]
    if selected:
        arguments.extend(["--run", run_id])
    monkeypatch.setattr("sys.argv", arguments)

    with pytest.raises(SystemExit) as failure:
        cli()

    output = capsys.readouterr()
    assert failure.value.code == 2
    assert output.out == ""
    assert f"newer schema_version {version}" in output.err
    assert "upgrade ReproLLM" in output.err
    assert CANARY not in output.err
    assert str(tmp_path) not in output.err
    assert "Traceback" not in output.err
    assert not (tmp_path / "REPRODUCIBILITY.md").exists()
    assert path.read_bytes() == raw


@pytest.mark.parametrize("version", [2, 3])
@pytest.mark.parametrize("reader", ["run-id", "diff-json", "diff-folder"])
def test_future_version_guidance_survives_each_input_reader(
    tmp_path: Path, version: int, reader: str
) -> None:
    run_id, path, raw = _project(tmp_path, version)

    with pytest.raises(UserError) as failure:
        if reader == "run-id":
            read_run(tmp_path, run_id)
        else:
            load_input(str(path if reader == "diff-json" else path.parent), tmp_path)

    message = str(failure.value)
    assert f"newer schema_version {version}" in message
    assert "upgrade ReproLLM" in message
    assert CANARY not in message
    assert str(tmp_path) not in message
    assert path.read_bytes() == raw


@pytest.mark.parametrize("version", [2, 3])
def test_listing_keeps_future_run_upgrade_warning_and_valid_legacy_record(
    tmp_path: Path, version: int
) -> None:
    _, future_path, future_raw = _project(tmp_path, version)
    legacy_id = "20261014T000000Z-000000"
    legacy = future_path.parent.parent / legacy_id
    legacy.mkdir()
    legacy_raw = json.dumps(
        {
            "schema_version": 1,
            "reprollm_version": "0.6.1",
            "run_id": legacy_id,
            "status": "completed",
            "exit_code": 0,
            "command": {"argv": ["python", "child.py"], "cwd": "."},
        }
    )
    (legacy / "run.json").write_text(legacy_raw, encoding="utf-8")

    records, warnings = list_runs(tmp_path)

    assert [record.run_id for record in records] == [legacy_id]
    assert len(warnings) == 1
    assert f"newer schema_version {version}" in warnings[0]
    assert "upgrade ReproLLM" in warnings[0]
    assert CANARY not in warnings[0]
    assert str(tmp_path) not in warnings[0]
    assert future_path.read_bytes() == future_raw
    assert (legacy / "run.json").read_text(encoding="utf-8") == legacy_raw


@pytest.mark.parametrize("raw", ["{" + CANARY, "null", "[]", json.dumps({"private": CANARY})])
def test_invalid_run_payload_is_a_safe_user_error(raw: str) -> None:
    with pytest.raises(UserError) as failure:
        parse_run_record(raw)
    assert failure.value.exit_code == 2
    assert "run.json" in str(failure.value)
    assert CANARY not in str(failure.value)


def test_legacy_raw_inspection_and_observation_order_remain_unchanged(tmp_path: Path) -> None:
    run_id, path, _ = _project(tmp_path, 1)
    data = json.loads(path.read_bytes())
    data.pop("future_payload")
    data["bindings_observed"] = {
        "generation.temperature": [
            {"value": 0.1, "source": {"type": "cli", "key": "--temperature"}},
            {"value": 0.9, "source": {"type": "cli", "key": "--temperature"}},
        ]
    }
    raw = json.dumps(data, indent=3) + "\n"
    path.write_text(raw, encoding="utf-8")

    record, original = read_run(tmp_path, run_id)

    assert original == raw
    assert record.schema_version == 1
    assert [item.value for item in record.bindings_observed["generation.temperature"]] == [0.1, 0.9]
    assert path.read_text(encoding="utf-8") == raw


@pytest.mark.parametrize("version", [True, 1.0, False, 1.5, "1", CANARY, None, [], {}])
def test_provided_schema_version_is_an_integer_not_a_coerced_value(version: Any) -> None:
    raw = json.dumps(
        {
            "schema_version": version,
            "reprollm_version": "0.6.1",
            "run_id": "20261014T000000Z-000001",
            "status": "completed",
            "command": {"argv": ["python", "child.py"], "cwd": "."},
        }
    )
    with pytest.raises(UserError) as failure:
        parse_run_record(raw)
    assert "schema_version must be an integer" in str(failure.value)
    assert CANARY not in str(failure.value)


def test_missing_legacy_schema_version_retains_existing_version_one_default() -> None:
    raw = json.dumps(
        {
            "reprollm_version": "0.3.0",
            "run_id": "20261014T000000Z-000001",
            "status": "completed",
            "command": {"argv": ["python", "child.py"], "cwd": "."},
        }
    )
    assert parse_run_record(raw).schema_version == 1
