"""R04-A public run/State evidence separates recorder metadata from child metadata."""

from __future__ import annotations

import importlib.metadata
import json
import os
import sys
import venv
from pathlib import Path

import pytest

from reprollm.core.envinfo import LLM_CRITICAL_PACKAGES, distribution_name
from reprollm.run.wrapper import create_run_dir, execute
from reprollm.schemas.state import State
from tests.conftest import CmdStub


def test_child_venv_metadata_does_not_become_verified_recorder_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stub_run_cmd: CmdStub,
) -> None:
    child_env = tmp_path / "child-env"
    venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt").create(child_env)
    if os.name == "nt":
        child_python = child_env / "Scripts" / "python.exe"
        site_packages = child_env / "Lib" / "site-packages"
    else:
        child_python = child_env / "bin" / "python"
        python_tag = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = child_env / "lib" / python_tag
        site_packages /= "site-packages"
    dist_info = site_packages / "torch-0.0.123.dist-info"
    dist_info.mkdir(parents=True)
    (dist_info / "METADATA").write_bytes(b"Metadata-Version: 2.1\nName: torch\nVersion: 0.0.123\n")

    root = tmp_path / "project"
    root.mkdir()
    (root / "reprollm.yaml").write_bytes(
        b"schema_version: 1\nproject: {name: recorder-env}\nexperiment: {profiles: []}\n"
    )
    real_version = importlib.metadata.version
    recorder_packages = {distribution_name(name) for name in LLM_CRITICAL_PACKAGES}

    def empty_recorder_metadata(name: str) -> str:
        if name in recorder_packages:
            raise importlib.metadata.PackageNotFoundError(name)
        return real_version(name)

    monkeypatch.setattr(importlib.metadata, "version", empty_recorder_metadata)
    monkeypatch.setenv("OMP_NUM_THREADS", "2")
    stub_run_cmd.on("git", returncode=128)
    stub_run_cmd.on("nvidia-smi", returncode=1)
    child_code = (
        "import importlib.metadata,importlib.util,json,os,pathlib; "
        "os.environ['OMP_NUM_THREADS']='3'; "
        "pathlib.Path('witness.json').write_text(json.dumps({"
        "'schema_version':1,'torch':importlib.metadata.version('torch'),"
        "'torch_importable':importlib.util.find_spec('torch') is not None,"
        "'omp_threads':os.environ['OMP_NUM_THREADS']"
        "}),encoding='utf-8')"
    )
    run_dir = create_run_dir(root)
    record = execute(
        [str(child_python), "-c", child_code],
        root=root,
        cwd=root,
        run_dir=run_dir,
        capture_output=False,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
    )

    # The witness is generated independently by the real child interpreter.
    assert json.loads((root / "witness.json").read_bytes()) == {
        "schema_version": 1,
        "torch": "0.0.123",
        "torch_importable": False,
        "omp_threads": "3",
    }
    assert record.exit_code == 0 and record.warnings == []
    assert record.environment is not None and record.environment.packages == {}
    assert record.environment.env["OMP_NUM_THREADS"] == "2"

    state = State.from_run(record, run_dir=run_dir)
    restored = State.model_validate_json(state.model_dump_json())
    remerged = State.merge(run=restored)
    for projected in (state, restored, remerged):
        environment = projected.flatten()
        python = environment["environment.python"]
        assert python.source == "run" and python.confidence == "observed"
        # The proposed typed context distinguishes source, phase and verification.
        context = getattr(python, "context", None)
        assert context is not None, "recorder metadata must carry typed source/phase context"
        assert context.subject == "recorder"
        assert context.phase == "post_child"
        assert context.verification == "unverified"
        host_context = getattr(environment["environment.platform"], "context", None)
        assert host_context is not None and host_context.subject == "host"
        assert host_context.phase == "post_child"
        inherited_context = getattr(environment["environment.env.OMP_NUM_THREADS"], "context", None)
        assert inherited_context is not None
        assert inherited_context.subject == "inherited_environment"
        assert inherited_context.phase == "pre_child"
        assert "environment.packages.torch" not in environment
        assert not any(path.startswith("environment.child.") for path in environment)
