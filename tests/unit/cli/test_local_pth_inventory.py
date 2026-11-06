"""Issue #15: offline lock refresh and existing diff/freshness contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core.yaml_io import load_lock
from tests.conftest import CmdStub

runner = CliRunner()
PAYLOAD_A = b"\x00pth A\xff"
PAYLOAD_B = b"\x00pth B\xff"
HASH_A = "sha256:d1d69f8f6d5f40cd46c059e7827bfa8ae283e71fabbd72ef7f0c9cef744ade72"
HASH_B = "sha256:37d078a35c41dfd068db2163fda5ef7627722b396111f9a938aaccde55b99775"


@pytest.fixture(autouse=True)
def isolated_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stub_run_cmd: CmdStub
) -> None:
    monkeypatch.chdir(tmp_path)
    stub_run_cmd.on("git", returncode=128)
    stub_run_cmd.on("nvidia-smi", returncode=127)


def make_project(root: Path, declaration: str) -> Path:
    directory = root / "weights"
    directory.mkdir()
    weight = directory / "classifier.pth"
    weight.write_bytes(PAYLOAD_A)
    if declaration == "directory-config":
        (directory / "config.json").write_bytes(b"{}")
    model_id = "weights/classifier.pth" if declaration == "file" else "weights"
    (root / "reprollm.yaml").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": {"name": "pth-acceptance"},
                "experiment": {"profiles": []},
                "models": {"primary": {"provider": "local", "id": model_id}},
            }
        ),
        encoding="utf-8",
    )
    return weight


def lock_offline() -> None:
    result = runner.invoke(app, ["lock", ".", "--offline"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert result.stderr == ""


@pytest.mark.parametrize("declaration", ["directory", "directory-config", "file"])
def test_offline_lock_records_pth_without_changing_inputs(tmp_path: Path, declaration: str) -> None:
    weight = make_project(tmp_path, declaration)
    manifest_bytes = (tmp_path / "reprollm.yaml").read_bytes()
    lock_offline()
    lock = load_lock(tmp_path / "reprollm.lock")
    assert lock.resolution.mode == "offline"
    model = lock.models["primary"]
    assert model.local is not None
    assert model.local.weights.model_dump() == {
        "hashed": True,
        "total_size_bytes": 7,
        "sha256": HASH_A,
    }
    assert weight.read_bytes() == PAYLOAD_A
    assert (tmp_path / "reprollm.yaml").read_bytes() == manifest_bytes


@pytest.mark.parametrize("declaration", ["directory", "directory-config", "file"])
def test_check_remains_declaration_freshness_without_rehashing(
    tmp_path: Path, declaration: str
) -> None:
    weight = make_project(tmp_path, declaration)
    lock_offline()
    saved = (tmp_path / "reprollm.lock").read_bytes()
    weight.write_bytes(PAYLOAD_B)
    result = runner.invoke(app, ["lock", ".", "--check", "--offline"])
    assert result.exit_code == 0, (result.output, result.exception)
    assert "up to date" in result.stdout
    assert (tmp_path / "reprollm.lock").read_bytes() == saved
    assert weight.read_bytes() == PAYLOAD_B


@pytest.mark.parametrize("declaration", ["directory", "directory-config", "file"])
@pytest.mark.parametrize("threshold", ["HIGH", "MEDIUM"])
def test_relocking_pth_uses_existing_diff_severity_and_exit_policy(
    tmp_path: Path, declaration: str, threshold: str
) -> None:
    weight = make_project(tmp_path, declaration)
    lock_offline()
    before = tmp_path / "before.lock"
    before.write_bytes((tmp_path / "reprollm.lock").read_bytes())
    weight.write_bytes(PAYLOAD_B)
    lock_offline()
    after = tmp_path / "after.lock"
    after.write_bytes((tmp_path / "reprollm.lock").read_bytes())
    expected_changes: list[dict[str, Any]] = [
        {
            "path": "models.primary.local.weights.sha256",
            "status": "changed",
            "a": HASH_A,
            "b": HASH_B,
            "severity": "MEDIUM",
            "note": None,
        }
    ]
    if declaration != "directory-config":
        expected_changes.insert(
            0,
            {
                "path": "models.primary.revision",
                "status": "changed",
                "a": HASH_A,
                "b": HASH_B,
                "severity": "HIGH",
                "note": None,
            },
        )
    args = ["diff", "before.lock", "after.lock", "--format", "json", "--fail-on", threshold]
    result = runner.invoke(app, args)
    expected_exit = 0 if declaration == "directory-config" and threshold == "HIGH" else 1
    assert result.exit_code == expected_exit, (result.output, result.exception)
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["changes"] == expected_changes
    assert report["summary"]["counts"]["MEDIUM"] == 1
    assert report["summary"]["counts"]["HIGH"] == (declaration != "directory-config")
    assert runner.invoke(app, args).stdout == result.stdout
    same = runner.invoke(
        app, ["diff", "before.lock", "before.lock", "--format", "json", "--fail-on", "LOW"]
    )
    assert same.exit_code == 0, same.output
    assert json.loads(same.stdout)["changes"] == []
    assert before.read_bytes() != after.read_bytes()
