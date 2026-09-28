"""End-to-end snapshot fidelity: run → snapshot → State → paired diff.

Regression for the 2026-09-27 lm-eval finding: path redaction corrupted
``generation.stop`` closing tokens and relative artifact globs inside the
manifest/lock snapshots, and equal corruption on both sides of an A/B pair
masked a genuine stop-token change in ``reprollm diff``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from reprollm.diff.differ import diff_states
from reprollm.diff.severity import SeverityResolver
from reprollm.diff.state import from_run
from reprollm.run import wrapper
from reprollm.schemas.run_record import HardwareInfo

MANIFEST_WITH_STOP = """\
schema_version: 1
project:
  name: stop-fidelity
experiment:
  profiles: [inference]
generation:
  temperature: 0.0
  top_p: 1.0
  max_tokens: 32
  stop: ["</s>"]
inference:
  backend: vllm
artifacts:
  outputs: ["outputs/current/**/*.json"]
"""

MANIFEST_OTHER_STOP = MANIFEST_WITH_STOP.replace('stop: ["</s>"]', 'stop: ["</think>"]')


@pytest.fixture(autouse=True)
def bounded_metadata(monkeypatch: pytest.MonkeyPatch, stub_run_cmd: Any) -> None:
    stub_run_cmd.on("git", returncode=128)
    monkeypatch.setattr(wrapper, "capture_hardware", lambda: HardwareInfo(cpu_count=2))
    monkeypatch.setattr(wrapper.envinfo, "installed_versions", lambda: {})
    monkeypatch.setattr(wrapper.socket, "gethostname", lambda: "fid-host")
    monkeypatch.setattr(wrapper.getpass, "getuser", lambda: "fid-user")


def _run(root: Path) -> Any:
    record = wrapper.execute(
        [sys.executable, "-c", "pass"],
        root=root,
        cwd=root,
        run_dir=wrapper.create_run_dir(root),
        capture_output=False,
        env_capture="allowlist",
        extra_allowlist=[],
        snapshot=True,
    )
    return record, root / ".reprollm" / "runs" / record.run_id


def _write_manifest(repo: Path, text: str) -> None:
    (repo / "reprollm.yaml").write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "exp"
    (repo / "outputs").mkdir(parents=True)
    (repo / "eval.py").write_text("print('hi')\n", encoding="utf-8")
    _write_manifest(repo, MANIFEST_WITH_STOP)
    return repo


def test_manifest_snapshot_preserves_stop_and_globs(repo: Path) -> None:
    record, run_dir = _run(repo)
    snapshot = (run_dir / "manifest.yaml").read_text(encoding="utf-8")
    assert 'stop: ["</s>"]' in snapshot
    assert "outputs/current/**/*.json" in snapshot
    assert "<REDACTED:path>" not in snapshot

    # artifacts do not participate in the State tree (spec §17); their
    # fidelity is the snapshot itself, asserted above. generation does:
    state = from_run(record, run_dir=run_dir)
    flat = state.flatten()
    assert flat["generation.stop"].value == ["</s>"]


def test_lock_snapshot_also_preserves_stop(repo: Path) -> None:
    (repo / "reprollm.lock").write_text(
        MANIFEST_WITH_STOP.replace(
            "experiment:\n  profiles: [inference]\n",
            "schema_version: 1\n",
        ),
        encoding="utf-8",
    )
    record, run_dir = _run(repo)
    snapshot = (run_dir / "lock.yaml").read_text(encoding="utf-8")
    assert 'stop: ["</s>"]' in snapshot


def test_stop_change_is_visible_in_paired_diff(repo: Path) -> None:
    """Equal-corruption masking: a real </s> → </think> change must surface."""
    _write_manifest(repo, MANIFEST_WITH_STOP)
    record_a, dir_a = _run(repo)

    _write_manifest(repo, MANIFEST_OTHER_STOP)
    record_b, dir_b = _run(repo)

    diff = diff_states(
        from_run(record_a, run_dir=dir_a),
        from_run(record_b, run_dir=dir_b),
        SeverityResolver(),
    )
    stop_changes = [c for c in diff.changes if c.path == "generation.stop"]
    assert stop_changes, "a stop-token change must not be hidden by redaction"
    change = stop_changes[0]
    assert change.a == ["</s>"]
    assert change.b == ["</think>"]


def test_secret_redaction_still_applies_to_snapshots(repo: Path) -> None:
    _write_manifest(
        repo,
        MANIFEST_WITH_STOP.replace(
            "inference:\n  backend: vllm",
            "inference:\n  backend: vllm\n  params:\n    api_key: sk-abcdefgh12345678ZZZZ",
        ),
    )
    record, run_dir = _run(repo)
    snapshot = (run_dir / "manifest.yaml").read_text(encoding="utf-8")
    assert "sk-abcd" not in snapshot
    assert "<REDACTED:" in snapshot  # secret removal survives the tightening
    # and the neighboring experiment values stay intact
    assert 'stop: ["</s>"]' in snapshot


def test_absolute_paths_still_portable_in_snapshot(repo: Path) -> None:
    _write_manifest(
        repo,
        MANIFEST_WITH_STOP.replace(
            "artifacts:",
            f"custom:\n  cache: {repo / 'outputs'}\nartifacts:",
        ),
    )
    record, run_dir = _run(repo)
    snapshot = (run_dir / "manifest.yaml").read_text(encoding="utf-8")
    assert str(repo) not in snapshot  # absolute in-root path relativized
    assert "cache: outputs" in snapshot
