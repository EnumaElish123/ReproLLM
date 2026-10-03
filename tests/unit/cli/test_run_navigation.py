"""UX3-T04 exact filters, outcome semantics and unchanged inspection output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.errors import UserError
from reprollm.run import reader
from reprollm.schemas.run_record import CommandInfo, RunRecord, RunStatus
from tests.conftest import CmdStub

runner = CliRunner()


def save_record(
    root: Path,
    index: int,
    *,
    name: str | None = "baseline",
    status: str = "completed",
    exit_code: int | None = 0,
    started_at: str | None = "2026-10-01T10:00:00Z",
    temperature: float | None = None,
) -> RunRecord:
    record = RunRecord(
        reprollm_version="0.6.1",
        run_id=f"20261001T100000Z-{index:06x}",
        name=name,
        status=RunStatus(status),
        exit_code=exit_code,
        started_at=started_at,
        duration_seconds=1.0,
        command=CommandInfo(argv=["python", "eval.py"], cwd="."),
    )
    if temperature is not None:
        data = record.model_dump()
        data["bindings_observed"] = {
            "generation.temperature": [
                {"value": temperature, "source": {"type": "cli", "key": "--temperature"}}
            ]
        }
        record = RunRecord.model_validate(data)
    folder = root / ".reprollm/runs" / record.run_id
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return record


@pytest.fixture(autouse=True)
def local_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: navigation}\nexperiment: {profiles: []}\n"
    )


def listing(*arguments: str) -> tuple[list[dict[str, Any]], str]:
    result = runner.invoke(app, ["runs", "list", "--json", *arguments])
    assert result.exit_code == 0, (result.output, result.exception)
    return json.loads(result.stdout), result.stderr


def ids(*arguments: str) -> list[str]:
    rows, warnings = listing(*arguments)
    assert warnings == ""
    return [row["run_id"] for row in rows]


def test_default_json_bytes_and_table_contract(tmp_path: Path) -> None:
    first = save_record(tmp_path, 1, name="first")
    second = save_record(tmp_path, 2, name=None, status="running", exit_code=None)
    expected = [
        {
            "run_id": second.run_id,
            "started_at": "2026-10-01T10:00:00Z",
            "status": "running",
            "exit_code": None,
            "duration_seconds": 1.0,
            "name": None,
            "dirty": False,
        },
        {
            "run_id": first.run_id,
            "started_at": "2026-10-01T10:00:00Z",
            "status": "completed",
            "exit_code": 0,
            "duration_seconds": 1.0,
            "name": "first",
            "dirty": False,
        },
    ]
    result = runner.invoke(app, ["runs", "list", "--json"])
    assert result.exit_code == 0 and result.stderr == ""
    assert result.stdout == json.dumps(expected, indent=2, sort_keys=True) + "\n"
    table = runner.invoke(app, ["runs", "list"], env={"COLUMNS": "140"})
    assert table.exit_code == 0 and table.stderr == ""
    assert all(
        heading in table.stdout
        for heading in ("Run ID", "Started", "Status", "Exit", "Duration", "Name", "Dirty")
    )
    assert second.run_id in table.stdout and first.run_id in table.stdout
    assert "1.0 s" in table.stdout and "first" in table.stdout
    assert runner.invoke(app, ["runs", "list"], env={"COLUMNS": "140"}).stdout == table.stdout


@pytest.mark.parametrize(
    "label", ["baseline", "Baseline", " baseline ", "基线", "", "*", "20261001"]
)
def test_exact_labels_preserve_duplicates_and_null_distinction(tmp_path: Path, label: str) -> None:
    labels = [
        "baseline",
        "Baseline",
        "baseline-more",
        " baseline ",
        "基线",
        "",
        None,
        "*",
        "20261001",
    ]
    records = [save_record(tmp_path, index, name=name) for index, name in enumerate(labels, 1)]
    duplicate = save_record(tmp_path, 20, name=label)
    expected = [
        duplicate.run_id,
        *[record.run_id for record in reversed(records) if record.name == label],
    ]
    assert ids("--name", label) == expected


@pytest.mark.parametrize(
    ("status", "exit_code", "outcome"),
    [
        ("completed", 0, "success"),
        ("completed", 2, "failure"),
        ("completed", -9, "failure"),
        ("completed", None, None),
        ("failed", 0, "failure"),
        ("failed", None, "failure"),
        ("interrupted", 0, "failure"),
        ("interrupted", None, "failure"),
        ("running", 0, None),
        ("running", None, None),
        ("running", 2, None),
    ],
)
def test_status_and_derived_outcome_matrix(
    tmp_path: Path, status: str, exit_code: int | None, outcome: str | None
) -> None:
    record = save_record(tmp_path, 1, status=status, exit_code=exit_code)
    assert ids("--status", status) == [record.run_id]
    for choice in ("success", "failure"):
        assert ids("--outcome", choice) == ([record.run_id] if outcome == choice else [])


def test_all_filters_intersect_before_limit(tmp_path: Path) -> None:
    wanted = save_record(tmp_path, 1)
    newer = save_record(tmp_path, 2)
    save_record(tmp_path, 3, exit_code=9)
    save_record(tmp_path, 4, name="other")
    save_record(tmp_path, 5, status="running", exit_code=0)
    assert ids(
        "--name", "baseline", "--status", "completed", "--outcome", "success", "--limit", "1"
    ) == [newer.run_id]
    assert ids("--name", "baseline", "--outcome", "success") == [newer.run_id, wanted.run_id]
    assert ids("--status", "running", "--outcome", "success") == []
    assert ids("--name", "no matches") == []


@pytest.mark.parametrize(
    "arguments",
    [
        ["--status", "done"],
        ["--status", "COMPLETED"],
        ["--outcome", "unknown"],
        ["--outcome", "Success"],
        ["--limit", "0"],
        ["--limit", "-1"],
        ["--limit", "1.0"],
        ["--limit", "many"],
    ],
)
def test_bad_selectors_fail_before_reading_storage(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("invalid option scanned records")

    monkeypatch.setattr("reprollm.cli.runs.list_runs", forbidden)
    result = runner.invoke(app, ["runs", "list", "--json", *arguments])
    assert result.exit_code == 2
    assert result.stdout == ""


def test_start_time_order_utc_naive_ties_and_missing_oldest(tmp_path: Path) -> None:
    missing = save_record(tmp_path, 99, started_at=None)
    early = save_record(tmp_path, 98, started_at="2026-10-01T09:59:59Z")
    offset = save_record(tmp_path, 2, started_at="2026-10-01T12:00:00+02:00")
    naive = save_record(tmp_path, 3, started_at="2026-10-01T10:00:00")
    utc = save_record(tmp_path, 1)
    newer = save_record(tmp_path, 0, started_at="2026-10-01T10:00:01Z")
    expected = [newer.run_id, naive.run_id, offset.run_id, utc.run_id, early.run_id, missing.run_id]
    assert ids() == expected
    assert ids("--limit", "3") == expected[:3]
    first = runner.invoke(app, ["runs", "list", "--json"]).stdout
    assert runner.invoke(app, ["runs", "list", "--json"]).stdout == first


@pytest.mark.parametrize("problem", ["corrupt", "missing", "new_schema", "mismatch", "escape"])
def test_limit_does_not_hide_safe_corruption_warnings(tmp_path: Path, problem: str) -> None:
    valid = save_record(tmp_path, 2)
    bad = save_record(tmp_path, 1)
    path = tmp_path / ".reprollm/runs" / bad.run_id / "run.json"
    if problem == "corrupt":
        path.write_text('{"private":"PRIVATE_RECORD_PAYLOAD",')
    elif problem == "missing":
        path.unlink()
    elif problem == "escape":
        outside = tmp_path.parent / f"{tmp_path.name}-outside-run.json"
        path.rename(outside)
        try:
            path.symlink_to(outside)
        except OSError:
            pytest.skip("symlink creation unavailable")
    else:
        data = json.loads(path.read_text())
        data["schema_version" if problem == "new_schema" else "run_id"] = (
            999 if problem == "new_schema" else valid.run_id
        )
        path.write_text(json.dumps(data))
    rows, warnings = listing("--name", "baseline", "--outcome", "success", "--limit", "1")
    assert [row["run_id"] for row in rows] == [valid.run_id]
    assert warnings.startswith("warning: ") and bad.run_id in warnings
    assert "PRIVATE_RECORD_PAYLOAD" not in warnings and str(tmp_path) not in warnings
    rows, warnings = listing("--name", "missing", "--limit", "1")
    assert rows == [] and warnings.startswith("warning: ")


def test_empty_list_retains_empty_outputs() -> None:
    assert listing("--outcome", "success") == ([], "")
    result = runner.invoke(app, ["runs", "list", "--name", "missing"])
    assert result.exit_code == 0 and "Run ID" in result.stdout
    assert "warning" not in result.stderr


def test_show_raw_json_unique_prefix_and_ambiguity_unchanged(tmp_path: Path) -> None:
    first = save_record(tmp_path, 1, name="duplicate")
    second = save_record(tmp_path, 2, name="duplicate")
    path = tmp_path / ".reprollm/runs" / first.run_id / "run.json"
    result = runner.invoke(app, ["runs", "show", first.run_id[:-1], "--json"])
    assert isinstance(result.exception, UserError) and "ambiguous" in str(result.exception)
    result = runner.invoke(app, ["runs", "show", first.run_id, "--json"])
    assert result.exit_code == 0 and result.stdout == path.read_text()
    assert set(ids("--name", "duplicate")) == {first.run_id, second.run_id}
    assert isinstance(runner.invoke(app, ["runs", "show", "duplicate"]).exception, UserError)


def test_manifestless_subdirectory_uses_existing_git_root_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub
) -> None:
    record = save_record(tmp_path, 1)
    (tmp_path / "reprollm.yaml").unlink()
    subdir = tmp_path / "subdirectory"
    subdir.mkdir()
    monkeypatch.chdir(subdir)
    stub_run_cmd.on("git", "rev-parse", "--show-toplevel", stdout=str(tmp_path))
    assert ids("--outcome", "success") == [record.run_id]
    assert stub_run_cmd.calls == [("git", "rev-parse", "--show-toplevel")]


def test_invalid_run_store_remains_usage_error(tmp_path: Path) -> None:
    (tmp_path / ".reprollm").mkdir()
    (tmp_path / ".reprollm/runs").write_text("not a directory")
    with pytest.raises(UserError, match="must be a directory"):
        reader.list_runs(tmp_path)
