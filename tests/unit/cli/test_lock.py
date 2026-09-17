from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from reprollm.cli.main import app, cli
from reprollm.core.yaml_io import load_lock
from tests.unit.lock.conftest import hf_mock as hf_mock

runner = CliRunner()


def _strip_volatile(value):
    if isinstance(value, dict):
        return {
            key: _strip_volatile(item)
            for key, item in value.items()
            if key not in {"generated_at", "resolved_at", "observed_at"}
        }
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def test_lock_online_writes_valid_document(materialize, hf_mock, stub_run_cmd) -> None:
    del hf_mock
    root = materialize("hf_vllm_eval", manifest="complete")
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")

    result = runner.invoke(app, ["lock", str(root)])

    assert result.exit_code == 0, result.output
    lock = load_lock(root / "reprollm.lock")
    assert lock.resolution.mode == "online"
    assert lock.models["primary"].revision.confidence.value == "exact"
    assert lock.datasets["eval"].revision.confidence.value == "exact"
    assert "Wrote reprollm.lock" in result.output
    assert "Resolved:" in result.output


def test_lock_offline_never_uses_http(materialize, stub_run_cmd) -> None:
    root = materialize("hf_vllm_eval", manifest="complete")
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")

    result = runner.invoke(app, ["lock", str(root), "--offline"])

    assert result.exit_code == 0, result.output
    lock = load_lock(root / "reprollm.lock")
    assert lock.resolution.mode == "offline"
    assert lock.models["primary"].revision.source == "offline"
    assert "Unresolved:" in result.output
    assert "models.primary.revision" in result.output


def test_lock_api_summary_lists_unpinnable_model(materialize, stub_run_cmd) -> None:
    root = materialize("openai_judge_eval", manifest="complete")
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")

    result = runner.invoke(app, ["lock", str(root)])

    assert result.exit_code == 0, result.output
    assert "1 unpinnable (models.primary)" in result.output
    assert "Unpinnable:" in result.output
    assert "models.primary" in result.output


def test_lock_check_missing_fresh_manifest_and_project_rules(
    materialize, hf_mock, stub_run_cmd, monkeypatch: pytest.MonkeyPatch
) -> None:
    del hf_mock
    root = materialize("hf_vllm_eval", manifest="complete")
    missing = runner.invoke(app, ["lock", str(root), "--check"])
    assert missing.exit_code == 1
    assert "missing" in missing.output

    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")
    assert runner.invoke(app, ["lock", str(root)]).exit_code == 0
    fresh = runner.invoke(app, ["lock", str(root), "--check"])
    assert fresh.exit_code == 0, fresh.output
    assert "up to date" in fresh.output

    import reprollm.cli.lock as lock_cli

    original_build_lock = lock_cli.build_lock
    monkeypatch.setattr(
        lock_cli,
        "build_lock",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("check resolved network")),
    )
    (root / "reprollm.yaml").write_text(
        (root / "reprollm.yaml").read_text(encoding="utf-8") + "\n# changed\n",
        encoding="utf-8",
    )
    stale_manifest = runner.invoke(app, ["lock", str(root), "--check"])
    assert stale_manifest.exit_code == 1
    assert "reprollm.yaml changed" in stale_manifest.output

    # Restore the exact manifest bytes, refresh, then add accepted project rules.
    text = (root / "reprollm.yaml").read_text(encoding="utf-8").removesuffix("\n# changed\n")
    (root / "reprollm.yaml").write_text(text, encoding="utf-8")
    monkeypatch.setattr(lock_cli, "build_lock", original_build_lock)
    assert runner.invoke(app, ["lock", str(root)]).exit_code == 0
    rules = root / ".reprollm/project-rules.yaml"
    rules.parent.mkdir(exist_ok=True)
    rules.write_text("schema_version: 1\nrules: []\n", encoding="utf-8")
    stale_rules = runner.invoke(app, ["lock", str(root), "--check"])
    assert stale_rules.exit_code == 1
    assert "project-rules.yaml changed" in stale_rules.output


def test_two_lock_runs_only_change_volatile_timestamps(materialize, stub_run_cmd) -> None:
    root = materialize("openai_judge_eval", manifest="complete")
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")

    first = runner.invoke(app, ["lock", str(root)])
    assert first.exit_code == 0, first.output
    one = yaml.safe_load((root / "reprollm.lock").read_text(encoding="utf-8"))
    second = runner.invoke(app, ["lock", str(root)])
    assert second.exit_code == 0, second.output
    two = yaml.safe_load((root / "reprollm.lock").read_text(encoding="utf-8"))

    assert _strip_volatile(one) == _strip_volatile(two)


def test_lock_without_manifest_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr("sys.argv", ["reprollm", "lock", str(tmp_path)])
    with pytest.raises(SystemExit) as caught:
        cli()
    captured = capsys.readouterr()

    assert caught.value.code == 2
    assert "run `reprollm init`" in captured.err
    assert not (tmp_path / "reprollm.lock").exists()


def test_lock_help_exposes_all_m4_options() -> None:
    result = runner.invoke(app, ["lock", "--help"])
    assert result.exit_code == 0
    for option in ("--offline", "--check", "--verify-api", "--hash-large-files"):
        assert option in result.output


def test_lock_file_is_yaml_not_json(materialize, stub_run_cmd) -> None:
    root = materialize("openai_judge_eval", manifest="complete")
    stub_run_cmd.on("nvidia-smi", returncode=127, stderr="not found")
    result = runner.invoke(app, ["lock", str(root)])
    assert result.exit_code == 0, result.output
    text = (root / "reprollm.lock").read_text(encoding="utf-8")
    assert text.startswith("schema_version: 1\n")
    with pytest.raises(json.JSONDecodeError):
        json.loads(text)
