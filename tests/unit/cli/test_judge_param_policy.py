"""R08-A: real CLI captures isolate direct judge drift and preserve old evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.run import wrapper
from tests.conftest import CmdStub
from tests.unit.diff.test_state import saved_run, snapshot_dir

runner = CliRunner()
FIELD = "evaluation.judge.params.max_tokens"
CHILD = (
    "import argparse,json; "
    "p=argparse.ArgumentParser(); "
    "p.add_argument('--cap',type=int); "
    "args=p.parse_args(); "
    "print(json.dumps({'consumed_cap':args.cap},sort_keys=True))"
)
METADATA = {"run_id", "started_at", "ended_at", "duration_seconds"}


@pytest.fixture(autouse=True)
def bounded_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub
) -> None:
    monkeypatch.chdir(tmp_path)
    stub_run_cmd.on("git", returncode=0)
    stub_run_cmd.on("git", "rev-parse", "--is-inside-work-tree", stdout="true\n")
    stub_run_cmd.on("git", "rev-parse", "--show-toplevel", stdout=f"{tmp_path}\n")
    stub_run_cmd.on("git", "rev-parse", "HEAD", stdout="a" * 40 + "\n")
    stub_run_cmd.on("git", "branch", "--show-current", stdout="fixture\n")
    stub_run_cmd.on("nvidia-smi", returncode=1)
    monkeypatch.setattr(wrapper.envinfo, "installed_versions", lambda: {})


def files_below(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def prepare_project(root: Path, base_profile: str, override: str | None) -> None:
    profile: dict[str, Any] = {
        "schema_version": 1,
        "name": "judge_policy",
        "description": "Exercise inherited judge policy through the CLI",
        "extends": [base_profile],
        "drift_overrides": {} if override is None else {FIELD: override},
    }
    profiles = root / ".reprollm/profiles"
    profiles.mkdir(parents=True)
    (profiles / "judge_policy.yaml").write_text(
        yaml.safe_dump(profile, sort_keys=True), encoding="utf-8", newline="\n"
    )
    manifest = {
        "schema_version": 1,
        "project": {"name": "judge-policy-cli"},
        "experiment": {"profiles": ["judge_policy"]},
        "models": {"judge": {"provider": "openai", "id": "fixture-judge"}},
        "prompts": {"judge": {"text": "Compare the two synthetic answers."}},
        "evaluation": {"judge": {"model_ref": "judge", "prompt_ref": "judge"}},
        "bindings": {FIELD: {"cli": "--cap"}},
    }
    # No declared cap or config binding may mask an absent CLI observation.
    (root / "reprollm.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8", newline="\n"
    )


def capture(root: Path, cap: int | None) -> tuple[Path, dict[str, Any]]:
    before = set(root.glob(".reprollm/runs/*/run.json"))
    args = [sys.executable, "-I", "-X", "utf8", "-c", CHILD]
    if cap is not None:
        args.extend(["--cap", str(cap)])
    result = runner.invoke(app, ["run", "--capture-output", "--", *args])
    assert result.exit_code == 0, (result.output, result.exception)
    created = set(root.glob(".reprollm/runs/*/run.json")) - before
    assert len(created) == 1
    path = created.pop()
    record = json.loads(path.read_bytes())
    consumed = json.loads((path.parent / "stdout.log").read_text(encoding="utf-8"))
    assert consumed == {"consumed_cap": cap}
    assert record["status"] == "completed" and record["exit_code"] == 0
    assert record["schema_version"] == 2
    assert record["code"]["commit"] == "a" * 40 and not record["code"]["dirty"]
    assert record["hardware"]["source"] == "unavailable"
    assert record["files"] == [] and record["lock"] is None
    assert record["input_capture"]["consumption"] == "unverified"
    observations = record["bindings_observed"].get(FIELD, [])
    assert [item["value"] for item in observations] == ([] if cap is None else [cap])
    assert all(item["source"]["type"] == "cli" for item in observations)
    return path, record


def diff_json(a: Path, b: Path, *extra: str, exit_code: int = 0) -> tuple[dict[str, Any], str]:
    result = runner.invoke(app, ["diff", str(a), str(b), "--format", "json", *extra])
    assert result.exit_code == exit_code, (result.output, result.exception)
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["schema_version"] == 1
    return report, result.stdout


@pytest.mark.parametrize("base_profile", ["judge_only", "llm_judge"])
@pytest.mark.parametrize("override", [None, "LOW", "NONE"], ids=["default", "LOW", "NONE"])
@pytest.mark.parametrize(
    ("before", "after", "status"),
    [(256, 384, "changed"), (None, 384, "added"), (256, None, "removed")],
)
def test_cli_judge_cap_policy_matrix(
    tmp_path: Path,
    stub_run_cmd: CmdStub,
    base_profile: str,
    override: str | None,
    before: int | None,
    after: int | None,
    status: str,
) -> None:
    prepare_project(tmp_path, base_profile, override)
    declarations = files_below(tmp_path)
    a, left = capture(tmp_path, before)
    b, right = capture(tmp_path, after)
    for name, raw in declarations.items():
        assert (tmp_path / name).read_bytes() == raw
    assert left["manifest"] == right["manifest"]
    assert (a.parent / "manifest.yaml").read_bytes() == declarations["reprollm.yaml"]
    assert (b.parent / "manifest.yaml").read_bytes() == declarations["reprollm.yaml"]
    assert any(call[0] == "nvidia-smi" for call in stub_run_cmd.calls)
    recorded = files_below(tmp_path)
    severity = override or "HIGH"
    expected_high_exit = 1 if severity == "HIGH" else 0

    report, raw = diff_json(a, b)
    changes = {change["path"]: change for change in report["changes"]}
    assert len(changes) == len(report["changes"])
    assert changes[FIELD]["a"] == before and changes[FIELD]["b"] == after
    assert changes[FIELD]["status"] == status
    assert changes[FIELD]["severity"] == severity
    assert changes["command.argv"]["severity"] == "MEDIUM"
    assert changes["command.argv"]["a"] == left["command"]["argv"]
    assert changes["command.argv"]["b"] == right["command"]["argv"]
    assert set(changes) <= {FIELD, "command.argv", *METADATA}
    assert {p for p, c in changes.items() if c["severity"] != "NONE"} == (
        {"command.argv"} if severity == "NONE" else {FIELD, "command.argv"}
    )
    assert {p for p, c in changes.items() if c["severity"] == "HIGH"} == (
        {FIELD} if severity == "HIGH" else set()
    )
    assert all(changes[p]["severity"] == "NONE" for p in changes.keys() & METADATA)
    expected_counts = {"HIGH": 0, "MEDIUM_HIGH": 0, "MEDIUM": 1, "LOW": 0, "NONE": 0}
    expected_counts[severity] += 1
    expected_counts["NONE"] += len(changes.keys() & METADATA)
    assert report["summary"]["counts"] == expected_counts
    assert report["summary"]["highest"] == ("HIGH" if severity == "HIGH" else "MEDIUM")
    assert diff_json(a, b)[1] == raw

    gated, _ = diff_json(a, b, "--fail-on", "HIGH", exit_code=expected_high_exit)
    assert gated == report
    filtered, _ = diff_json(
        a, b, "--min-severity", "HIGH", "--fail-on", "HIGH", exit_code=expected_high_exit
    )
    assert filtered["summary"] == report["summary"]
    assert filtered["filtered_below"] == "HIGH"
    assert filtered["changes"] == ([changes[FIELD]] if severity == "HIGH" else [])
    hidden, _ = diff_json(a, b, "--min-severity", "HIGH", "--fail-on", "MEDIUM", exit_code=1)
    assert hidden == filtered
    same, _ = diff_json(a, a, "--fail-on", "LOW")
    assert same["changes"] == [] and same["summary"]["highest"] == "NONE"
    assert all(count == 0 for count in same["summary"]["counts"].values())
    assert files_below(tmp_path) == recorded


def test_legacy_judge_runs_get_current_policy_without_rewriting_history(tmp_path: Path) -> None:
    # These are synthetic version-1 fixtures, not a claim of a past live judge run.
    ids = ["20261001T100000Z-111111", "20261001T100001Z-222222"]
    paths = []
    commands = []
    for run_id, cap in zip(ids, (256, 384), strict=True):
        directory = tmp_path / ".reprollm/runs" / run_id
        directory.parent.mkdir(parents=True, exist_ok=True)
        snapshot_dir(tmp_path, name="openai_judge_eval").rename(directory)
        data = saved_run("openai_judge_eval").model_dump(mode="json")
        data["run_id"] = run_id
        data["command"]["argv"].extend(["--cap", str(cap)])
        commands.append(data["command"]["argv"])
        data["bindings_observed"][FIELD] = [
            {"value": cap, "source": {"type": "cli", "key": "--cap"}}
        ]
        path = directory / "run.json"
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
        paths.append(path)
    archived = {
        "schema_version": 1,
        "reprollm_version": "0.1.1",
        "a": {"kind": "run", "ref": ids[0]},
        "b": {"kind": "run", "ref": ids[1]},
        "summary": {
            "highest": "MEDIUM",
            "counts": {"HIGH": 0, "MEDIUM_HIGH": 0, "MEDIUM": 2, "LOW": 0, "NONE": 1},
            "same": 0,
        },
        "changes": [
            {"path": FIELD, "status": "changed", "a": 256, "b": 384, "severity": "MEDIUM"},
            {
                "path": "command.argv",
                "status": "changed",
                "a": commands[0],
                "b": commands[1],
                "severity": "MEDIUM",
            },
            {
                "path": "run_id",
                "status": "changed",
                "a": ids[0],
                "b": ids[1],
                "severity": "NONE",
            },
        ],
    }
    history = tmp_path / "historical-diff.json"
    history.write_text(json.dumps(archived, indent=2) + "\n", encoding="utf-8", newline="\n")
    originals = files_below(tmp_path)

    report, _ = diff_json(*paths)
    target = next(change for change in report["changes"] if change["path"] == FIELD)
    assert (target["a"], target["b"], target["severity"]) == (256, 384, "HIGH")
    assert {c["path"] for c in report["changes"] if c["severity"] != "NONE"} == {
        FIELD,
        "command.argv",
    }
    for run_id, path in zip(ids, paths, strict=True):
        shown = runner.invoke(app, ["runs", "show", run_id, "--json"])
        assert shown.exit_code == 0, (shown.output, shown.exception)
        assert shown.stdout.encode("utf-8") == originals[path.relative_to(tmp_path).as_posix()]
    assert json.loads(history.read_bytes())["changes"][0]["severity"] == "MEDIUM"
    assert files_below(tmp_path) == originals
