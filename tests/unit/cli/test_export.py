"""M7-T01: ``reprollm export`` — snapshots, degradation, determinism, privacy."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from reprollm.cli.main import app
from tests.conftest import materialize_repo

runner = CliRunner()

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "repos"
POSITIVE = ["hf_vllm_eval", "openai_judge_eval", "privacy_custom_params"]

_VOLATILE = {
    "reprollm_version": "0.4.0",
    "run_id": None,  # per-fixture below
}


def _assemble(tmp_path: Path, name: str, *, with_run: bool = True) -> Path:
    """Materialize the fixture, then add manifest/lock/run from expected/."""
    repo = materialize_repo(name, tmp_path / name)
    base = FIXTURES / name / "expected"
    manifests = FIXTURES / name / "manifests"
    if (manifests / "complete.yaml").is_file():
        (repo / "reprollm.yaml").write_text(
            (manifests / "complete.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
    if (base / "lock.yaml").is_file():
        (repo / "reprollm.lock").write_text(
            (base / "lock.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
    if with_run and (base / "run.json").is_file():
        run_id = f"20260101T000000Z-{name[:6]}"
        run_dir = repo / ".reprollm" / "runs" / run_id
        run_dir.mkdir(parents=True)
        record = json.loads((base / "run.json").read_text(encoding="utf-8"))
        # expected/run.json is a comparison snapshot with volatile fields
        # stripped; restore the shape a real record has.
        record.setdefault("reprollm_version", "0.4.0")
        record["run_id"] = run_id
        env = record.setdefault("environment", {})
        env.setdefault("os", "Linux-test")
        env.setdefault("python", "3.12.14")
        env.setdefault(
            "hostname_sha256",
            "sha256:" + "0" * 64,
        )
        (run_dir / "run.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8", newline="\n"
        )
        (run_dir / "manifest.yaml").write_text(
            (repo / "reprollm.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
            newline="\n",
        )
        if (repo / "reprollm.lock").is_file():
            (run_dir / "lock.yaml").write_text(
                (repo / "reprollm.lock").read_text(encoding="utf-8"),
                encoding="utf-8",
                newline="\n",
            )
    from tests.conftest import commit_all

    commit_all(repo)
    return repo


def test_export_snapshots_with_run(tmp_path: Path) -> None:
    for name in POSITIVE:
        repo = _assemble(tmp_path, name)
        result = runner.invoke(app, ["export", str(repo)])
        assert result.exit_code == 0, (name, result.output)
        generated = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
        expected_path = FIXTURES / name / "expected" / "REPRODUCIBILITY.md"
        if os.environ.get("REPROLLM_UPDATE_SNAPSHOTS") == "1":
            expected_path.write_text(generated, encoding="utf-8")
        else:
            assert generated == expected_path.read_text(encoding="utf-8"), name


def test_export_without_run_states_so(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "hf_vllm_eval", with_run=False)
    result = runner.invoke(app, ["export", str(repo)])
    assert result.exit_code == 0, result.output
    document = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "No run record exists" in document
    assert "`reprollm run -- <command>`" in document


def test_export_deterministic(tmp_path: Path) -> None:
    """Same *inputs* → byte-identical output (spec §19). The exported file
    itself must not be part of the input: remove it between runs, otherwise
    the embedded audit honestly reports the tree it made dirty."""
    repo = _assemble(tmp_path, "hf_vllm_eval")
    assert runner.invoke(app, ["export", str(repo)]).exit_code == 0
    first = (repo / "REPRODUCIBILITY.md").read_bytes()
    (repo / "REPRODUCIBILITY.md").unlink()
    assert runner.invoke(app, ["export", str(repo)]).exit_code == 0
    second = (repo / "REPRODUCIBILITY.md").read_bytes()
    assert first == second


def test_export_contains_no_machine_identity(tmp_path: Path) -> None:
    import getpass
    import socket

    repo = _assemble(tmp_path, "openai_judge_eval")
    assert runner.invoke(app, ["export", str(repo)]).exit_code == 0
    document = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert str(tmp_path) not in document
    assert "/home/" not in document
    assert socket.gethostname() not in document
    assert getpass.getuser() not in document


def test_export_embeds_real_audit_summary(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "hf_vllm_eval")
    result = runner.invoke(app, ["export", str(repo)])
    assert result.exit_code == 0, result.output
    document = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "Audit summary" in document
    assert "critical" in document
    # warnings present in the audit must appear verbatim
    assert "env.llm_critical_deps_pinned" in document


def test_export_no_lock_marks_not_locked(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "hf_vllm_eval", with_run=False)
    (repo / "reprollm.lock").unlink()
    result = runner.invoke(app, ["export", str(repo)])
    assert result.exit_code == 0, result.output
    document = (repo / "REPRODUCIBILITY.md").read_text(encoding="utf-8")
    assert "not locked" in document


def test_export_requires_manifest(tmp_path: Path, monkeypatch) -> None:

    from reprollm.cli.main import cli

    repo = _assemble(tmp_path, "hf_vllm_eval")
    (repo / "reprollm.yaml").unlink()
    monkeypatch.setattr("sys.argv", ["reprollm", "export", str(repo)])
    with pytest.raises(SystemExit) as excinfo:
        cli()
    assert excinfo.value.code == 2


def test_export_run_prefix_selection_and_ambiguity(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "hf_vllm_eval")
    run_id = next((repo / ".reprollm" / "runs").iterdir()).name
    result = runner.invoke(app, ["export", str(repo), "--run", run_id[:8]])
    assert result.exit_code == 0, result.output
    result = runner.invoke(app, ["export", str(repo), "--run", "2026"])
    assert result.exit_code in (0, 2)  # prefix may match; ambiguous prefixes fail


def test_export_output_option(tmp_path: Path) -> None:
    repo = _assemble(tmp_path, "hf_vllm_eval")
    result = runner.invoke(app, ["export", str(repo), "--output", "docs/REPRO.md"])
    assert result.exit_code == 0, result.output
    assert (repo / "docs" / "REPRO.md").is_file()
