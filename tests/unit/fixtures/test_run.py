"""M5-T05 end-to-end run contract on the locked vLLM evaluation fixture."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import jsonschema
import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.git import inspect_git
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo
from tests.conftest import FIXTURES_ROOT, SNAPSHOT_IGNORE, assert_json_snapshot
from tests.unit.fixtures.test_level_two import LockedRepo
from tests.unit.fixtures.test_level_two import locked_repo as locked_repo
from tests.unit.lock.conftest import hf_mock as hf_mock
from tests.unit.rules.test_runtime_consistency import NOW


def test_locked_fixture_run_snapshot(
    locked_repo: LockedRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, _ = locked_repo("hf_vllm_eval")
    git = inspect_git(root)
    monkeypatch.setattr(wrapper, "inspect_git", lambda root: git)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: "fixture-user")
    monkeypatch.setattr(wrapper, "_now", lambda: NOW)
    monkeypatch.setattr(wrapper.secrets, "token_hex", lambda size: "a1b2c3")
    monkeypatch.chdir(root)
    with monkeypatch.context() as isolated:
        env = {key: value for key, value in os.environ.items() if key.upper() == "SYSTEMROOT"}
        env.update(PATH=str(Path(sys.executable).parent), CUDA_VISIBLE_DEVICES="0")
        isolated.setattr(os, "environ", env)
        result = CliRunner().invoke(
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
                "1.0",
            ],
        )
    assert result.exit_code == 0, result.output
    (path,) = (root / ".reprollm/runs").glob("*/run.json")
    actual = json.loads(path.read_text())
    observations = actual["bindings_observed"]["generation.temperature"]
    assert [(o["source"]["type"], o["value"]) for o in observations] == [
        ("cli", 1.0),
        ("config", 0.0),
    ]
    schema_dir = Path(__file__).resolve().parents[3] / "schemas"
    jsonschema.validate(actual, json.loads((schema_dir / "run_record.schema.json").read_text()))
    assert str(root) not in path.read_text()
    ignore = (
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
    )
    assert_json_snapshot(actual, FIXTURES_ROOT / "repos/hf_vllm_eval/expected/run.json", ignore)

    audited = CliRunner().invoke(app, ["audit", "--format", "json"])
    assert audited.exit_code == 1, audited.output
    report = json.loads(audited.stdout)
    by_id = {finding["rule_id"]: finding for finding in report["findings"]}
    assert by_id["consistency.generation_params"]["severity"] == "CRITICAL"
    assert [e["value"] for e in by_id["consistency.generation_params"]["evidence"]] == [
        0.0,
        1.0,
        0.0,
    ]
    for name in ("exec.run_recorded", "consistency.env_vs_lock", "consistency.model_identity"):
        assert by_id[name]["status"] == "pass"
    jsonschema.validate(report, json.loads((schema_dir / "audit_report.schema.json").read_text()))
    assert_json_snapshot(
        report, FIXTURES_ROOT / "repos/hf_vllm_eval/expected/audit_L2_after_run.json"
    )
