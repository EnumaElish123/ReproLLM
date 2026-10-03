"""UX3-T04 fixed newest successful pairs, historical inputs and diff policies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from reprollm.cli import diff as diff_cli
from reprollm.cli.main import app
from reprollm.run import reader, wrapper
from reprollm.schemas.run_record import RunRecord
from tests.unit.cli.test_diff import run_pair
from tests.unit.cli.test_run_navigation import save_record

runner = CliRunner()


@pytest.fixture(autouse=True)
def local_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reprollm.yaml").write_text(
        "schema_version: 1\nproject: {name: navigation}\nexperiment: {profiles: []}\n"
    )


def report(*arguments: str, exit_code: int = 0) -> dict[str, Any]:
    result = runner.invoke(app, ["diff", *arguments, "--format", "json"])
    assert result.exit_code == exit_code, (result.output, result.exception)
    assert result.stderr == ""
    return json.loads(result.stdout)


def selection_matrix(root: Path) -> list[RunRecord]:
    rows = [
        (None, "baseline", "completed", 0),
        ("00", "baseline", "completed", 0),
        ("01", "baseline", "completed", 9),
        ("02", "baseline", "failed", 127),
        ("03", "baseline", "interrupted", -2),
        ("04", "baseline", "running", None),
        ("05", "baseline", "completed", None),
        ("06", "other", "completed", 0),
        ("07", "baseline", "completed", 0),
        ("07", "baseline", "completed", 0),
        ("08", "other", "completed", 0),
    ]
    return [
        save_record(
            root,
            index,
            started_at=f"2026-10-01T10:00:{second}Z" if second is not None else None,
            name=name,
            status=status,
            exit_code=exit_code,
            temperature=index / 10,
        )
        for index, (second, name, status, exit_code) in enumerate(rows)
    ]


@pytest.mark.parametrize(
    ("arguments", "older", "newer"),
    [([], 9, 10), (["--name", "baseline"], 8, 9), (["--name", "other"], 7, 10)],
)
def test_latest_pair_direction_full_ids_and_text_selection(
    tmp_path: Path, arguments: list[str], older: int, newer: int
) -> None:
    records = selection_matrix(tmp_path)
    result = report("--latest-successful", *arguments)
    assert result["a"] == {"kind": "run", "ref": records[older].run_id}
    assert result["b"] == {"kind": "run", "ref": records[newer].run_id}
    temperature = next(
        change for change in result["changes"] if change["path"] == "generation.temperature"
    )
    assert (temperature["a"], temperature["b"]) == (older / 10, newer / 10)
    text = runner.invoke(app, ["diff", "--latest-successful", *arguments, "--no-color"])
    assert text.exit_code == 0 and text.stderr == ""
    assert f"a: run {records[older].run_id}" in text.stdout
    assert f"b: run {records[newer].run_id}" in text.stdout


@pytest.mark.parametrize("label", ["", " 基线 ", "*", "Baseline"])
def test_recent_names_are_exact_and_empty_is_not_null(tmp_path: Path, label: str) -> None:
    a = save_record(tmp_path, 1, name=label)
    b = save_record(tmp_path, 2, name=label)
    save_record(tmp_path, 3, name=None)
    save_record(tmp_path, 4, name=f"{label}-more")
    result = report("--latest-successful", "--name", label)
    assert result["a"]["ref"] == a.run_id and result["b"]["ref"] == b.run_id


@pytest.mark.parametrize("count", [0, 1])
@pytest.mark.parametrize("named", [False, True])
def test_insufficient_successes_exit_two_never_widen_or_echo_names(
    tmp_path: Path, count: int, named: bool
) -> None:
    selector = "PRIVATE_SELECTOR_VALUE"
    for index in range(count):
        save_record(tmp_path, index, name=selector)
    if named:
        save_record(tmp_path, 5, name="other")
        save_record(tmp_path, 6, name="other")
    save_record(tmp_path, 7, name=selector, status="running", exit_code=0)
    save_record(tmp_path, 8, name=selector, status="completed", exit_code=None)
    save_record(tmp_path, 9, name=selector, status="failed", exit_code=0)
    arguments = ["--name", selector] if named else []
    result = runner.invoke(app, ["diff", "--latest-successful", *arguments, "--format", "json"])
    assert result.exit_code == 2 and result.stdout == ""
    assert str(count) in result.stderr and "reprollm runs list --outcome success" in result.stderr
    assert selector not in result.stderr and str(tmp_path) not in result.stderr


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["first"],
        ["--name", "baseline"],
        ["first", "second", "--name", "baseline"],
        ["first", "--latest-successful"],
        ["first", "second", "--latest-successful"],
    ],
)
def test_invalid_mode_fails_before_input_reads(
    monkeypatch: pytest.MonkeyPatch, arguments: list[str]
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("invalid mode read input or root")

    monkeypatch.setattr(diff_cli, "load_input", forbidden)
    monkeypatch.setattr(diff_cli, "find_root", forbidden)
    result = runner.invoke(app, ["diff", *arguments, "--format", "json"])
    assert result.exit_code == 2 and result.stdout == ""
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("problem", ["missing", "invalid", "escape"])
def test_selected_bad_snapshot_never_falls_back_to_third(tmp_path: Path, problem: str) -> None:
    a, b = run_pair(tmp_path)
    save_record(tmp_path, 0, started_at="2026-09-30T10:00:00Z")
    path = tmp_path / ".reprollm/runs" / b / "manifest.yaml"
    if problem == "missing":
        path.unlink()
    elif problem == "invalid":
        path.write_text("[PRIVATE_SNAPSHOT_PAYLOAD")
    else:
        outside = tmp_path / "outside.yaml"
        path.rename(outside)
        try:
            path.symlink_to(outside)
        except OSError:
            pytest.skip("symlink creation unavailable")
    result = runner.invoke(app, ["diff", "--latest-successful", "--format", "json"])
    assert result.exit_code == 2 and result.stdout == ""
    assert "snapshot" in result.stderr
    assert "PRIVATE_SNAPSHOT_PAYLOAD" not in result.stderr and str(tmp_path) not in result.stderr
    assert (tmp_path / ".reprollm/runs" / a / "manifest.yaml").is_file()


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_current_directory_id_paths_cannot_shadow_selected_runs(tmp_path: Path, kind: str) -> None:
    a = save_record(tmp_path, 1, temperature=0.1)
    b = save_record(tmp_path, 2, temperature=0.7)
    for record in (a, b):
        shadow = tmp_path / record.run_id
        if kind == "file":
            shadow.write_text("[PRIVATE_SHADOW_PAYLOAD")
        else:
            shadow.mkdir()
            (shadow / "run.json").write_text("[PRIVATE_SHADOW_PAYLOAD")
    result = report("--latest-successful")
    assert result["a"]["ref"] == a.run_id and result["b"]["ref"] == b.run_id
    assert result["summary"]["highest"] == "HIGH"


def test_selection_reads_each_record_once_and_uses_selected_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = save_record(tmp_path, 1, temperature=0.1)
    b = save_record(tmp_path, 2, temperature=0.7)
    original = reader._read
    calls: list[str] = []

    def mutate_after_read(root: Path, folder: Path) -> tuple[RunRecord, str]:
        calls.append(folder.name)
        record, raw = original(root, folder)
        (folder / "run.json").write_text("[PRIVATE_SECOND_READ_PAYLOAD")
        return record, raw

    monkeypatch.setattr(reader, "_read", mutate_after_read)
    result = report("--latest-successful")
    assert calls == [a.run_id, b.run_id]
    assert result["a"]["ref"] == a.run_id and result["b"]["ref"] == b.run_id


@pytest.mark.parametrize("problem", ["corrupt", "missing", "schema", "mismatch"])
def test_corrupt_newest_record_is_warned_and_skipped(tmp_path: Path, problem: str) -> None:
    a = save_record(tmp_path, 1)
    b = save_record(tmp_path, 2)
    bad = save_record(tmp_path, 3)
    path = tmp_path / ".reprollm/runs" / bad.run_id / "run.json"
    if problem == "corrupt":
        path.write_text('{"private":"PRIVATE_RECORD_PAYLOAD",')
    elif problem == "missing":
        path.unlink()
    else:
        data = json.loads(path.read_text())
        data["schema_version" if problem == "schema" else "run_id"] = (
            999 if problem == "schema" else b.run_id
        )
        path.write_text(json.dumps(data))
    result = runner.invoke(app, ["diff", "--latest-successful", "--format", "json"])
    assert result.exit_code == 0
    document = json.loads(result.stdout)
    assert document["a"]["ref"] == a.run_id and document["b"]["ref"] == b.run_id
    assert result.stderr.startswith("warning: ") and bad.run_id in result.stderr
    assert "PRIVATE_RECORD_PAYLOAD" not in result.stderr and str(tmp_path) not in result.stderr


def test_shortcut_equivalent_to_explicit_pair_and_thresholds(tmp_path: Path) -> None:
    a = save_record(tmp_path, 1, temperature=0.1)
    b = save_record(tmp_path, 2, temperature=0.7)
    whole = report("--latest-successful")
    assert whole == report(a.run_id, b.run_id)
    assert report("--latest-successful") == whole
    filtered = report(
        "--latest-successful", "--min-severity", "HIGH", "--fail-on", "HIGH", exit_code=1
    )
    assert filtered["summary"] == whole["summary"]
    assert [change["path"] for change in filtered["changes"]] == ["generation.temperature"]
    path = tmp_path / ".reprollm/runs" / b.run_id / "run.json"
    value = json.loads(path.read_text())
    value["bindings_observed"]["generation.temperature"][0]["value"] = 0.1
    value["bindings_observed"]["custom.setting"] = [
        {"value": 1, "source": {"type": "cli", "key": "--setting"}}
    ]
    path.write_text(json.dumps(value))
    filtered = report(
        "--latest-successful", "--min-severity", "HIGH", "--fail-on", "MEDIUM", exit_code=1
    )
    assert filtered["changes"] == [] and filtered["summary"]["highest"] == "MEDIUM"


def test_captured_manifest_and_current_profile_override_are_preserved(tmp_path: Path) -> None:
    a, b = run_pair(tmp_path)
    (tmp_path / "reprollm.yaml").write_text("[BROKEN_LIVE_MANIFEST")
    profiles = tmp_path / ".reprollm/profiles"
    profiles.mkdir()
    (profiles / "inference.yaml").write_text(
        "schema_version: 1\nname: inference\ndescription: test\n"
        'drift_overrides: {"generation.temperature": LOW}\n'
    )
    result = report("--latest-successful")
    assert result == report(a, b)
    change = next(
        change for change in result["changes"] if change["path"] == "generation.temperature"
    )
    assert (change["a"], change["b"], change["severity"]) == (1.0, 0.7, "LOW")


def test_commands_read_only_no_experiment_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    save_record(tmp_path, 1, temperature=0.1)
    save_record(tmp_path, 2, temperature=0.7)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("inspection launched an experiment")

    monkeypatch.setattr(wrapper, "execute", forbidden)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    result = runner.invoke(app, ["runs", "list", "--json", "--outcome", "success", "--limit", "1"])
    assert result.exit_code == 0
    report("--latest-successful")
    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after
