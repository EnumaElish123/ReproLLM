"""A01-B assertions keep independent consumption and full drift evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts import a01_local_replay

from tests.conftest import CmdStub
from tests.unit.test_distribution import _wheel
from tests.unit.test_lm_eval_replay import RECIPE, _prepare, _probe


@pytest.fixture
def capture(tmp_path: Path, stub_run_cmd: CmdStub):
    stub_run_cmd.on("git", returncode=128)
    stub_run_cmd.on("nvidia-smi", returncode=1)
    _prepare(tmp_path)
    record, directory, receipt = _probe(tmp_path)
    return record.model_dump(mode="json"), directory, receipt


def test_capture_verifies_receipt_and_original_snapshot_bytes(capture) -> None:
    record, directory, receipt = capture
    checks = a01_local_replay.verify_capture(record, directory, receipt, RECIPE, 32)
    assert checks["consumed_cap"] == 32
    assert checks["input_snapshot_files_checked"] == 4
    assert checks["recorder_consumption"] == "unverified"


@pytest.mark.parametrize("defect", ["receipt-cap", "receipt-hash", "snapshot"])
def test_capture_rejects_forged_consumption_or_changed_snapshot(capture, defect: str) -> None:
    record, directory, receipt = capture
    if defect == "receipt-cap":
        receipt["configuration"]["gen_kwargs"]["max_gen_toks"] = 48
    elif defect == "receipt-hash":
        receipt["input_sha256"] = "0" * 64
    else:
        reference = next(item for item in record["files"] if item["path"] == "validation/eval.yaml")
        (directory / reference["snapshot"]).write_bytes(b"different bytes")
    with pytest.raises(ValueError):
        a01_local_replay.verify_capture(record, directory, receipt, RECIPE, 32)


def test_consumption_receipt_precedes_input_rewrite(tmp_path: Path, stub_run_cmd: CmdStub) -> None:
    stub_run_cmd.on("git", returncode=128)
    stub_run_cmd.on("nvidia-smi", returncode=1)
    _prepare(tmp_path)
    record, directory, receipt = _probe(tmp_path, rewrite=True)
    checks = a01_local_replay.verify_capture(
        record.model_dump(mode="json"), directory, receipt, RECIPE, 32, rewrite=True
    )
    assert checks["consumed_cap"] == 32
    assert checks["input_change"] == "changed"


def test_portability_check_rejects_private_identity(tmp_path: Path) -> None:
    (tmp_path / "evidence.json").write_text(
        json.dumps({"schema_version": 1, "private": "synthetic-local-user"}), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        a01_local_replay.assert_portable(tmp_path, ["synthetic-local-user"])


@pytest.mark.parametrize(
    "value",
    [
        r"\\synthetic-host\share\file",
        "/root/synthetic/file",
        "ghp_" + "a" * 24,
        "api_key=" + "synthetic-value" * 2,
        "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
        "-----BEGIN PRIVATE KEY-----\nsynthetic\n-----END PRIVATE KEY-----",
        "https://synthetic-user:synthetic-password@example.invalid/",
    ],
)
def test_portability_rejects_spec_secret_classes_and_machine_paths(
    tmp_path: Path, value: str
) -> None:
    (tmp_path / "evidence.json").write_text(
        json.dumps({"schema_version": 1, "value": value}), encoding="utf-8"
    )
    with pytest.raises(ValueError):
        a01_local_replay.assert_portable(tmp_path, [])


def test_portability_preserves_public_regex_and_relative_windows_path(tmp_path: Path) -> None:
    (tmp_path / "public.yaml").write_bytes((RECIPE / "upstream/gsm8k.yaml").read_bytes())
    (tmp_path / "safe.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "relative": r"<PATH>\NVIDIA Corporation\tools",
                "source": {"key": "gen_kwargs.max_gen_toks"},
            }
        ),
        encoding="utf-8",
    )
    a01_local_replay.assert_portable(tmp_path, [])


def test_portability_rejects_plain_text_unc_path(tmp_path: Path) -> None:
    (tmp_path / "plain.txt").write_text(r"\\synthetic-host\share\file", encoding="utf-8")
    with pytest.raises(ValueError, match="absolute_path_in_evidence"):
        a01_local_replay.assert_portable(tmp_path, [])


def test_duplicate_drift_path_cannot_hide_an_incorrect_cap() -> None:
    with pytest.raises(ValueError):
        a01_local_replay.verify_delta(
            {
                "changes": [
                    {"path": "generation.max_tokens", "a": 32, "b": 47, "severity": "HIGH"},
                    {"path": "generation.max_tokens", "a": 32, "b": 48, "severity": "HIGH"},
                    {"path": "files.validation/eval.yaml.sha256", "severity": "HIGH"},
                    {"path": "code.commit", "severity": "MEDIUM"},
                ]
            }
        )


@pytest.mark.parametrize(
    "reference", ["../outside", "files/../../outside", "/outside", "C:\\outside"]
)
def test_snapshot_reference_cannot_escape_package(tmp_path: Path, reference: str) -> None:
    with pytest.raises(ValueError, match="snapshot_path"):
        a01_local_replay.local_snapshot(tmp_path, reference)


@pytest.mark.parametrize("defect", [None, "missing-target", "wrong-cap", "unexpected-drift"])
def test_complete_drift_is_asserted_independently(defect: str | None) -> None:
    changes = [
        {"path": "generation.max_tokens", "a": 32, "b": 48, "severity": "HIGH"},
        {"path": "files.validation/eval.yaml.sha256", "severity": "HIGH"},
        {"path": "code.commit", "severity": "MEDIUM"},
    ]
    if defect == "missing-target":
        changes.pop(0)
    elif defect == "wrong-cap":
        changes[0]["b"] = 47
    elif defect == "unexpected-drift":
        changes.append({"path": "models.primary.id", "severity": "HIGH"})
    if defect is None:
        assert len(a01_local_replay.verify_delta({"changes": changes})) == 3
    else:
        with pytest.raises(ValueError):
            a01_local_replay.verify_delta({"changes": changes})


def test_wrong_wheel_hash_is_rejected_before_creating_environment(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wheel = _wheel(tmp_path)
    manifest = tmp_path / "build-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_commit": "a" * 40,
                "version": "0.7.0",
                "artifacts": [{"filename": wheel.name, "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )
    work = tmp_path / "private"
    result = a01_local_replay.main(
        [
            "--wheel",
            str(wheel),
            "--build-manifest",
            str(manifest),
            "--work-root",
            str(work),
            "--output-dir",
            str(tmp_path / "public"),
        ]
    )
    assert result == 1
    assert json.loads(capsys.readouterr().out)["status"] == "FAIL"
    assert not work.exists()


def test_disposable_clone_preserves_input_bytes_and_clears_shell_injection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = []
    monkeypatch.setenv("PYTHONPATH", "synthetic-private-path")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-private-key")
    monkeypatch.setattr(
        a01_local_replay.subprocess, "run", lambda command, **kwargs: seen.append((command, kwargs))
    )
    a01_local_replay.clone_seed(tmp_path / "seed", tmp_path / "case")
    command, options = seen[0]
    assert command[:3] == ["git", "-c", "core.autocrlf=false"]
    assert "OPENAI_API_KEY" not in options["env"] and "PYTHONPATH" not in options["env"]
    assert options["env"]["GIT_CONFIG_GLOBAL"] == a01_local_replay.os.devnull
