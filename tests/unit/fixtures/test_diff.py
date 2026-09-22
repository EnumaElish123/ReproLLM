"""M6-T06: reviewed semantic drift scenarios, including actual wrapper captures."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import jsonschema
import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.git import inspect_git
from reprollm.core.yaml_io import load_manifest
from reprollm.lock.writer import build_lock, write_lock
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo
from tests.conftest import FIXTURES_ROOT, SNAPSHOT_IGNORE, assert_json_snapshot, run_git
from tests.unit.diff.test_state import saved_run, snapshot_dir
from tests.unit.fixtures.test_level_two import LockedRepo
from tests.unit.fixtures.test_level_two import locked_repo as locked_repo
from tests.unit.lock.conftest import hf_mock as hf_mock
from tests.unit.lock.helpers import NOW as LOCK_NOW
from tests.unit.rules.test_runtime_consistency import NOW

EXPECTED = FIXTURES_ROOT / "repos/hf_vllm_eval/expected"
SCHEMA = Path(__file__).resolve().parents[3] / "schemas/diff_report.schema.json"
runner = CliRunner()


def report(a: str, b: str) -> dict:
    result = runner.invoke(app, ["diff", a, b, "--format", "json"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert result.stderr == ""
    data = json.loads(result.stdout)
    jsonschema.validate(data, json.loads(SCHEMA.read_text(encoding="utf-8")))
    return data


def snapshots(name: str, a: str, b: str, data: dict) -> None:
    assert_json_snapshot(data, EXPECTED / f"diff_{name}.json")
    result = runner.invoke(app, ["--no-color", "diff", a, b])
    assert result.exit_code == 0 and result.stderr == "", result.output
    path = EXPECTED / f"diff_{name}.txt"
    if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
        path.write_text(result.stdout, encoding="utf-8")
    assert result.stdout == path.read_text(encoding="utf-8")


def test_prompt_and_temperature_drift_from_real_captures(
    locked_repo: LockedRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = locked_repo("hf_vllm_eval")
    monkeypatch.chdir(root)
    # Ignore recorder-owned files without altering the committed fixture tree.
    with (root / ".git/info/exclude").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n.reprollm/\n")
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: "fixture-user")
    monkeypatch.setattr(wrapper, "_now", lambda: NOW)
    monkeypatch.setattr(wrapper, "time", SimpleNamespace(monotonic=lambda: 10.0))
    ids = []
    for index, temperature in enumerate(("1.0", "0.7")):
        if index:
            with (root / "prompts/system.txt").open("a", encoding="utf-8", newline="\n") as stream:
                stream.write("Answer concisely.\n")
            with httpx.Client() as http:
                lock = build_lock(
                    root,
                    load_manifest(root / "reprollm.yaml"),
                    http=http,
                    offline=False,
                    verify_api=False,
                    hash_large_files=False,
                    now=LOCK_NOW,
                )
            write_lock(
                root / "reprollm.lock", lock.model_copy(update={"reprollm_version": "0.2.0"})
            )
            # A changed commit is meaningful only if the changed inputs were committed.
            run_git(root, "add", "prompts/system.txt", "reprollm.lock")
            run_git(root, "commit", "-m", "change prompt and record lock")
        suffix = "a1b2c3" if not index else "d4e5f6"
        git = inspect_git(root)
        monkeypatch.setattr(wrapper, "inspect_git", lambda root, git=git: git)
        monkeypatch.setattr(wrapper.secrets, "token_hex", lambda size, suffix=suffix: suffix)
        with monkeypatch.context() as isolated:
            env = {key: value for key, value in os.environ.items() if key.upper() == "SYSTEMROOT"}
            env.update(PATH=str(Path(sys.executable).parent), CUDA_VISIBLE_DEVICES="0")
            isolated.setattr(os, "environ", env)
            result = runner.invoke(
                app,
                [
                    "run",
                    "--",
                    "python",
                    "-c",
                    "pass",
                    "--config",
                    "configs/eval.yaml",
                    "--temperature",
                    temperature,
                ],
            )
        assert result.exit_code == 0, result.output
        run_id = f"{NOW:%Y%m%dT%H%M%SZ}-{suffix}"
        ids.append(run_id)
        captured = json.loads((root / ".reprollm/runs" / run_id / "run.json").read_text())
        assert not captured["warnings"] and captured["code"]["dirty"] is False
        if not index:
            assert_json_snapshot(
                captured,
                EXPECTED / "run.json",
                (
                    *SNAPSHOT_IGNORE,
                    "run_id",
                    "started_at",
                    "ended_at",
                    "duration_seconds",
                    "hostname_sha256",
                    "packages",
                    "os",
                    "python",
                    "hardware",
                ),
            )
    data = report(*ids)
    changes = {item["path"]: item for item in data["changes"]}
    assert {path: item["severity"] for path, item in changes.items()} == {
        "prompts.system.sha256": "HIGH",
        "prompts.system.size_bytes": "MEDIUM",
        "files.prompts/system.txt.sha256": "HIGH",
        "generation.temperature": "HIGH",
        "code.commit": "MEDIUM",
        "command.argv": "MEDIUM",
        "run_id": "NONE",
    }
    assert (changes["generation.temperature"]["a"], changes["generation.temperature"]["b"]) == (
        1.0,
        0.7,
    )
    assert changes["code.commit"]["note"] == "code changed"
    assert data["summary"]["highest"] == "HIGH"
    snapshots("a_prompt_temperature", *ids, data)


def test_single_model_revision_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    original = (EXPECTED / "lock.yaml").read_text(encoding="utf-8")
    (tmp_path / "a.lock").write_text(original, encoding="utf-8")
    before = "8fa23e7c1a0000000000000000000000000000aa"
    (tmp_path / "b.lock").write_text(original.replace(before, "b" * 40, 1), encoding="utf-8")
    data = report("a.lock", "b.lock")
    assert data["changes"] == [
        {
            "path": "models.primary.revision",
            "status": "changed",
            "a": before,
            "b": "b" * 40,
            "severity": "HIGH",
            "note": None,
        }
    ]
    snapshots("b_revision", "a.lock", "b.lock", data)


@pytest.mark.parametrize("scenario", ["c_identical", "d_torch_patch"])
def test_identical_and_patch_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str
) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("a", "b"):
        folder = snapshot_dir(tmp_path)
        folder.rename(tmp_path / name)
        run = saved_run()
        if name == "b":
            assert run.environment is not None
            run.environment.packages["torch"] = "2.8.1"
        (tmp_path / name / "run.json").write_text(run.model_dump_json(), encoding="utf-8")
    a, b = "a/run.json", "a/run.json" if scenario == "c_identical" else "b/run.json"
    data = report(a, b)
    if scenario == "c_identical":
        assert data["changes"] == [] and data["summary"]["highest"] == "NONE"
    else:
        # Normative §18.1: MEDIUM_HIGH minus one level is MEDIUM, not LOW.
        assert data["changes"] == [
            {
                "path": "environment.packages.torch",
                "status": "changed",
                "a": "2.8.0",
                "b": "2.8.1",
                "severity": "MEDIUM",
                "note": None,
            }
        ]
        assert data["summary"]["highest"] == "MEDIUM"
    snapshots(scenario, a, b, data)
