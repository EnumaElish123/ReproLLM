"""Release-blocking leakage corpus through the real run command (M5-T07)."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import socket
import sys
from pathlib import Path

import pytest
import yaml
from tests.conftest import commit_all, make_git_repo
from typer.testing import CliRunner

from reprollm.cli.main import app
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo


@pytest.mark.security
@pytest.mark.parametrize("mode", ["allowlist", "all"])
def test_no_leaks_across_every_run_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    username, hostname = getpass.getuser(), socket.gethostname()
    root = make_git_repo(tmp_path / "experiment")
    openai = "sk-" + "FAKE" * 12
    hf = "hf_" + "FAKE" * 6
    password = "hunter2hunter2"
    aws = "syntheticAwsSecretForLeakageCorpus012345678"
    env = {name: value for name, value in os.environ.items() if name.upper() == "SYSTEMROOT"}
    env.update(
        PATH=os.defpath,
        OPENAI_API_KEY=openai,
        HF_TOKEN=hf,
        MY_SERVICE_PASSWORD=password,
        AWS_SECRET_ACCESS_KEY=aws,
        CUDA_VISIBLE_DEVICES="0",
    )
    # Never pass the test runner's real credentials into the child, including in all mode.
    monkeypatch.setattr(os, "environ", env)
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: username)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    (root / "configs").mkdir()
    config = root / "configs/eval.yaml"
    config.write_text(
        yaml.safe_dump(
            {"temperature": 0.0, "api_key": openai, "identity": f"{username} {hostname} {root}"}
        ),
        encoding="utf-8",
    )
    (root / ".env").write_text(f"OPENAI_API_KEY={openai}\n", encoding="utf-8")
    (root / "settings.py").write_text('password = "placeholder"\n', encoding="utf-8")
    (root / "reprollm.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "project": {"name": "leakage-gold"},
                "experiment": {"profiles": []},
                "generation": {"temperature": 0.0},
                "execution": {"config_files": ["configs/eval.yaml"]},
                "bindings": {"generation.temperature": {"config": "configs/eval.yaml:temperature"}},
            }
        ),
        encoding="utf-8",
    )
    (root / "reprollm.lock").write_text(
        "schema_version: 1\nreprollm_version: 0.1.1\n"
        "generated_at: 2026-10-05T09:30:00Z\nmanifest_sha256: sha256:fixture\n"
        "resolution: {mode: offline}\n",
        encoding="utf-8",
    )
    commit_all(root)
    (root / "settings.py").write_text(f'password = "{password}"\n', encoding="utf-8")
    monkeypatch.chdir(root)
    result = CliRunner().invoke(
        app,
        [
            "run",
            "--capture-output",
            "--env-capture",
            mode,
            "--",
            sys.executable,
            "-c",
            "import os,sys; print(os.environ['HF_TOKEN']); "
            "print(os.environ['OPENAI_API_KEY'], file=sys.stderr)",
            "--api-key",
            openai,
            "--config",
            "configs/eval.yaml",
            ".env",
        ],
    )
    assert result.exit_code == 0, result.output
    (folder,) = (root / ".reprollm/runs").iterdir()
    record = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    assert record["warnings"] == []
    captured = record["environment"]["env"]
    assert captured["OPENAI_API_KEY"] == captured["HF_TOKEN"] == {"present": True}
    assert captured["AWS_SECRET_ACCESS_KEY"] == {"present": True}
    assert captured["CUDA_VISIBLE_DEVICES"] == "0"
    if mode == "allowlist":
        assert "MY_SERVICE_PASSWORD" not in captured
    else:
        assert captured["MY_SERVICE_PASSWORD"] == {"present": True}
    forbidden = next(item for item in record["files"] if item["path"] == ".env")
    assert forbidden["redacted"] is True and forbidden["snapshot"] is None
    inputs = next(item for item in record["files"] if item["path"] == "configs/eval.yaml")
    assert inputs["sha256"] == "sha256:" + hashlib.sha256(config.read_bytes()).hexdigest()
    assert inputs["redacted"] and inputs["snapshot"]
    patch = (folder / "patch.diff").read_text(encoding="utf-8")
    assert record["code"]["dirty"] and "<REDACTED:generic_kv>" in patch
    assert "<REDACTED:huggingface>" in (folder / "stdout.log").read_text()
    assert "<REDACTED:openai>" in (folder / "stderr.log").read_text()
    assert (folder / record["manifest"]["snapshot"]).is_file()
    assert (folder / record["lock"]["snapshot"]).is_file()
    for artifact in sorted(folder.rglob("*")):
        if artifact.is_file():
            content = artifact.read_bytes()
            for private in (openai, hf, password, aws, username, hostname, str(root)):
                assert private.encode() not in content, artifact.relative_to(folder)


def test_security_gate_precedes_distribution_build() -> None:
    root = Path(__file__).resolve().parents[2]
    workflows = {
        name: yaml.safe_load((root / ".github/workflows" / name).read_text())
        for name in ("ci.yml", "quality.yml", "release.yml")
    }
    for name in ("ci.yml", "release.yml"):
        caller = workflows[name]["jobs"]["quality"]
        assert caller["uses"] == "./.github/workflows/quality.yml"
        assert "if" not in caller and not caller.get("continue-on-error", False)
    quality = workflows["quality.yml"]["jobs"]["quality"]
    assert "if" not in quality and not quality.get("continue-on-error", False)
    security = next(step for step in quality["steps"] if "-m security" in step.get("run", ""))
    assert "if" not in security and not security.get("continue-on-error", False)

    release = workflows["release.yml"]["jobs"]
    build = release["build"]
    assert set(build["needs"]) == {"prepare", "quality"}
    assert "if" not in build and not build.get("continue-on-error", False)
    assert any(step.get("run") == "uv build" for step in build["steps"])
    publish = release["publish"]
    assert set(publish["needs"]) == {"prepare", "quality", "build"}
    assert all(
        f"needs.{job}.result == 'success'" in publish["if"]
        for job in ("prepare", "quality", "build")
    )
