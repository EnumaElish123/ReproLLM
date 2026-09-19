"""M4-T06: reviewed lock and Level 2 contracts, with no installed LLM stack."""

from __future__ import annotations

import importlib.metadata
import json
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx
import jsonschema
import pytest
import respx
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.core import proc
from reprollm.core.yaml_io import dump_yaml, load_manifest
from reprollm.lock.writer import build_lock, write_lock
from reprollm.schemas.lock import Lock
from tests.conftest import (
    FIXTURES_ROOT,
    SNAPSHOT_IGNORE,
    _strip_ignored,
    assert_json_snapshot,
    commit_all,
    materialize_repo,
)
from tests.unit.lock.conftest import hf_mock as hf_mock
from tests.unit.lock.helpers import NOW

NAMES = ("hf_vllm_eval", "openai_judge_eval", "privacy_custom_params")
runner = CliRunner()
LockedRepo = Callable[[str], tuple[Path, Lock, dict[str, Any]]]


@pytest.fixture
def locked_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hf_mock: respx.MockRouter
) -> LockedRepo:
    # Fix the machine-dependent inputs while retaining real fixture Git state.
    versions = {"transformers": "4.57.0", "datasets": "3.2.0", "openai": "1.99.0"}

    def version(name: str) -> str:
        if name in versions:
            return versions[name]
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", version)
    monkeypatch.setattr("reprollm.core.envinfo.python_version", lambda: "3.11.9")
    monkeypatch.setattr("reprollm.core.envinfo.platform_name", lambda: "linux")
    for key in ("HF_ENDPOINT", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    run_cmd = proc.run_cmd

    def no_gpu(
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        timeout: float = 30,
        env: Mapping[str, str] | None = None,
    ) -> proc.CmdResult:
        if argv[0] == "nvidia-smi":
            return proc.CmdResult(proc.NOT_FOUND, "", "not found")
        return run_cmd(argv, cwd=cwd, timeout=timeout, env=env)

    monkeypatch.setattr(proc, "run_cmd", no_gpu)

    def make(name: str) -> tuple[Path, Lock, dict[str, Any]]:
        root = materialize_repo(name, tmp_path, manifest="complete")
        with httpx.Client() as http:
            lock = build_lock(
                root,
                load_manifest(root / "reprollm.yaml"),
                http=http,
                offline=False,
                verify_api=False,
                hash_large_files=False,
                now=NOW,
            )
        # The version is fixed because Git commit and document hashes include it.
        lock = lock.model_copy(update={"reprollm_version": "0.2.0"})
        write_lock(root / "reprollm.lock", lock)
        commit_all(root, "record fixture lock")
        result = runner.invoke(app, ["audit", str(root), "--format", "json", "--fail-on", "never"])
        assert result.exit_code == 0, result.output
        return root, lock, json.loads(result.output)

    return make


@pytest.mark.parametrize("name", NAMES)
def test_level_two_provider_outcomes(locked_repo: LockedRepo, name: str) -> None:
    _, lock, report = locked_repo(name)
    assert report["level"] == 2
    findings = report["findings"]
    actionable = sorted(
        (item["rule_id"], item["severity"])
        for item in findings
        if item["status"] == "fail" and item["severity"] in {"CRITICAL", "WARNING"}
    )
    expected = {
        "hf_vllm_eval": [("gen.backend_version_locked", "WARNING")],
        "openai_judge_eval": [("model.revision_pinned", "WARNING")],
        "privacy_custom_params": [
            ("model.chat_template_hashed", "WARNING"),
            ("model.revision_pinned", "CRITICAL"),
            ("model.tokenizer_pinned", "WARNING"),
        ],
    }
    assert actionable == expected[name]
    by_id = {item["rule_id"]: item for item in findings}
    for rule in ("consistency.lock_fresh", "consistency.file_hashes", "prompt.hashed"):
        assert by_id[rule]["status"] == "pass"
    if name == "hf_vllm_eval":
        assert lock.models["primary"].revision.confidence.value == "exact"
        assert lock.datasets["eval"].revision.confidence.value == "exact"
        assert lock.inference.version.confidence.value == "unresolved"
        assert "vllm" not in lock.environment.packages
    elif name == "openai_judge_eval":
        revisions = [item for item in findings if item["rule_id"] == "model.revision_pinned"]
        assert {(item["evidence"][0]["field"], item["severity"]) for item in revisions} == {
            ("models.primary.pinnability", "WARNING"),
            ("models.judge.pinnability", "INFO"),
        }
        assert by_id["dataset.local_files_hashed"]["status"] == "pass"
        assert by_id["judge.prompt_hashed"]["status"] == "pass"
        assert lock.models["judge"].pinnability == "snapshot_alias"
    else:
        assert lock.models["primary"].revision.source == "hf_api_forbidden"
        assert "HF_TOKEN" in by_id["model.revision_pinned"]["fix_hint"]
        assert "hf_api_forbidden" in json.dumps(by_id["model.revision_pinned"]["evidence"])


@pytest.mark.parametrize("name", NAMES)
def test_level_two_snapshots_and_schemas(locked_repo: LockedRepo, name: str) -> None:
    root, lock, report = locked_repo(name)
    schema_dir = Path(__file__).resolve().parents[3] / "schemas"
    for document, schema_name in ((lock.model_dump(mode="json"), "lock"), (report, "audit_report")):
        schema = json.loads((schema_dir / f"{schema_name}.schema.json").read_text(encoding="utf-8"))
        jsonschema.validate(document, schema)
    expected_dir = FIXTURES_ROOT / "repos" / name / "expected"
    lock_path = expected_dir / "lock.yaml"
    if os.getenv("REPROLLM_UPDATE_SNAPSHOTS") == "1":
        lock_path.write_text(dump_yaml(lock), encoding="utf-8")
    else:
        expected = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        assert _strip_ignored(lock.model_dump(mode="json"), SNAPSHOT_IGNORE) == _strip_ignored(
            expected, SNAPSHOT_IGNORE
        )
    assert_json_snapshot(report, expected_dir / "audit_L2.json")
    assert str(root) not in json.dumps(report)
