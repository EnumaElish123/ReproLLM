"""R04-B: retained input baselines do not become post-child file values."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import IO, Any

import pytest
import yaml

from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import CommandInfo, InputCapture, RunRecord, RunStatus


def _capture(
    root: Path,
    *,
    files: list[str],
    bindings: dict[str, dict[str, str]] | None = None,
    argv: list[str] | None = None,
    snapshot: bool = True,
    max_bytes: int = 1_048_576,
    privacy: RunPrivacy | None = None,
) -> tuple[RunRecord, Path]:
    from reprollm.run.input_capture import capture_inputs

    data = {
        "schema_version": 1,
        "project": {"name": "input-checks"},
        "experiment": {"profiles": []},
        "execution": {"config_files": files},
        "bindings": bindings or {},
    }
    manifest_bytes = yaml.safe_dump(data).encode()
    (root / "reprollm.yaml").write_bytes(manifest_bytes)
    manifest = Manifest.model_validate(data)
    record = RunRecord(
        schema_version=2,
        reprollm_version="0.7.0",
        run_id="input-checks",
        status=RunStatus.RUNNING,
        command=CommandInfo(argv=argv or ["python"], cwd="."),
        input_capture=InputCapture(),
    )
    run_dir = root / ".reprollm/runs" / record.run_id
    run_dir.mkdir(parents=True)
    capture_inputs(
        record,
        root=root,
        cwd=root,
        run_dir=run_dir,
        argv=record.command.argv,
        env={},
        privacy=privacy or RunPrivacy(root, hostname="fixture-host", username="fixture-user"),
        manifest=manifest,
        project_rules=None,
        snapshot=snapshot,
        max_bytes=max_bytes,
        document_data={"reprollm.yaml": manifest_bytes},
    )
    return record, run_dir


def test_input_baseline_survives_config_rewrite_and_post_recheck(tmp_path: Path) -> None:
    from reprollm.run.input_capture import capture_inputs, recheck_inputs
    from reprollm.schemas.run_record import CommandInfo, InputCapture, RunRecord, RunStatus

    original = b'{"temperature": 0.1}\n'
    rewritten = b'{"temperature": 0.9}\n'
    manifest_bytes = (
        b"schema_version: 1\nproject: {name: input-baseline}\n"
        b"experiment: {profiles: []}\ngeneration: {temperature: 0.1}\n"
        b"execution: {config_files: [config.json]}\n"
        b"bindings:\n  generation.temperature: {config: 'config.json:temperature'}\n"
    )
    (tmp_path / "reprollm.yaml").write_bytes(manifest_bytes)
    (tmp_path / "config.json").write_bytes(original)
    manifest = Manifest.model_validate(yaml.safe_load(manifest_bytes))
    record = RunRecord(
        schema_version=2,
        reprollm_version="0.7.0",
        run_id="20261014T000000Z-000001",
        status=RunStatus.RUNNING,
        command=CommandInfo(argv=["python", "child.py", "--config=config.json"], cwd="."),
        input_capture=InputCapture(),
    )
    run_dir = tmp_path / ".reprollm/runs" / record.run_id
    run_dir.mkdir(parents=True)
    privacy = RunPrivacy(tmp_path, hostname="fixture-host", username="fixture-user")

    capture_inputs(
        record,
        root=tmp_path,
        cwd=tmp_path,
        run_dir=run_dir,
        argv=record.command.argv,
        env={},
        privacy=privacy,
        manifest=manifest,
        project_rules=None,
        snapshot=True,
        max_bytes=1_048_576,
        document_data={"reprollm.yaml": manifest_bytes},
    )

    assert record.input_capture is not None
    assert record.input_capture.baseline_phase == "pre_child"
    assert record.input_capture.check_phase == "post_child"
    assert record.input_capture.consumption == "unverified"
    checks = record.input_capture.checks
    assert [check.path for check in checks] == ["config.json", "reprollm.lock", "reprollm.yaml"]
    config = checks[0]
    assert config.before.availability == "present"
    assert config.before.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert config.before.size_bytes == len(original)
    assert config.after.availability == "unavailable"
    assert config.change == "unknown"
    captured_file = next(file for file in record.files if file.path == "config.json")
    assert captured_file.sha256 == config.before.sha256
    assert captured_file.snapshot is not None
    assert (run_dir / captured_file.snapshot).read_bytes() == original
    assert record.bindings_observed["generation.temperature"][0].value == 0.1

    (tmp_path / "config.json").write_bytes(rewritten)
    recheck_inputs(record, root=tmp_path)

    config = record.input_capture.checks[0]
    assert config.before.sha256 == "sha256:" + hashlib.sha256(original).hexdigest()
    assert config.after.availability == "present"
    assert config.after.sha256 == "sha256:" + hashlib.sha256(rewritten).hexdigest()
    assert config.after.size_bytes == len(rewritten)
    assert config.change == "changed"
    assert record.bindings_observed["generation.temperature"][0].value == 0.1
    assert captured_file.sha256 == config.before.sha256
    assert (run_dir / captured_file.snapshot).read_bytes() == original


@pytest.mark.parametrize(
    ("size", "snapshot", "max_bytes", "observed", "copied"),
    [
        (1_048_576, True, 1_048_576, True, True),
        (1_048_577, True, 1_048_576, True, False),
        (2_097_152, False, 1_048_576, True, False),
        # The existing contextual snapshot parser also enforces a 1 MiB safety cap.
        (2_097_153, True, 3_145_728, False, False),
    ],
)
def test_config_observation_limit_is_independent_of_snapshot_policy(
    tmp_path: Path,
    size: int,
    snapshot: bool,
    max_bytes: int,
    observed: bool,
    copied: bool,
) -> None:
    prefix = b'{"temperature": 0.1}'
    raw = prefix + b" " * (size - len(prefix))
    (tmp_path / "config.json").write_bytes(raw)
    record, run_dir = _capture(
        tmp_path,
        files=["config.json"],
        snapshot=snapshot,
        max_bytes=max_bytes,
        bindings={"generation.temperature": {"config": "config.json:temperature"}},
    )
    file = next(item for item in record.files if item.path == "config.json")
    assert file.sha256 == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert file.size_bytes == size
    assert (file.snapshot is not None) is copied
    if copied:
        assert file.snapshot is not None
        assert (run_dir / file.snapshot).read_bytes() == raw
    if observed:
        assert record.bindings_observed["generation.temperature"][0].value == 0.1
    else:
        assert "generation.temperature" not in record.bindings_observed
        assert any("2 MiB" in warning for warning in record.warnings)
    assert record.manifest is not None
    assert (run_dir / record.manifest.snapshot).is_file()


def test_forbidden_symlink_target_is_hash_only_and_never_observed(tmp_path: Path) -> None:
    raw = b'{"temperature": 0.1, "password": "PrivateCanaryValue"}\n'
    (tmp_path / ".env").write_bytes(raw)
    try:
        (tmp_path / "config.json").symlink_to(tmp_path / ".env")
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    record, run_dir = _capture(
        tmp_path,
        files=["config.json"],
        bindings={"generation.temperature": {"config": "config.json:temperature"}},
    )
    file = next(item for item in record.files if item.path == "config.json")
    assert file.sha256 == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert file.redacted and file.snapshot is None
    assert record.bindings_observed == {}
    assert "PrivateCanaryValue" not in record.model_dump_json()
    assert not (run_dir / "files").exists()


def test_201_files_keep_all_fingerprints_and_config_without_file_copies(tmp_path: Path) -> None:
    files = [f"input-{index:03}.txt" for index in range(200)] + ["config.json"]
    for name in files:
        (tmp_path / name).write_bytes(b'{"temperature": 0.1}\n')
    record, run_dir = _capture(
        tmp_path,
        files=files,
        bindings={"generation.temperature": {"config": "config.json:temperature"}},
    )
    assert len(record.files) == 201
    assert all(file.snapshot is None for file in record.files)
    assert record.input_capture is not None
    checks = record.input_capture.checks
    assert len(checks) == 203
    assert [check.path for check in checks] == sorted(check.path for check in checks)
    assert all(check.before.availability == "present" for check in checks if check.path in files)
    assert record.bindings_observed["generation.temperature"][0].value == 0.1
    assert not (run_dir / "files").exists()
    assert sum("200" in warning for warning in record.warnings) == 1


def test_manifest_config_uses_preloader_bytes_without_reopening_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from reprollm.run.input_capture import capture_inputs
    from reprollm.schemas.run_record import CommandInfo, InputCapture, RunRecord, RunStatus

    original = (
        b"schema_version: 1\nproject: {name: document-baseline}\n"
        b"experiment: {profiles: []}\ngeneration: {temperature: 0.1}\n"
        b"bindings:\n  generation.temperature: {config: 'reprollm.yaml:generation.temperature'}\n"
    )
    source = tmp_path / "reprollm.yaml"
    source.write_bytes(original.replace(b"0.1", b"0.9"))
    manifest = Manifest.model_validate(yaml.safe_load(original))
    record = RunRecord(
        schema_version=2,
        reprollm_version="0.7.0",
        run_id="document-baseline",
        status=RunStatus.RUNNING,
        command=CommandInfo(argv=["python"], cwd="."),
        input_capture=InputCapture(),
    )
    run_dir = tmp_path / ".reprollm/runs" / record.run_id
    run_dir.mkdir(parents=True)
    original_open = Path.open
    opened: list[Path] = []

    def watch_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == source:
            opened.append(path)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", watch_open)
    capture_inputs(
        record,
        root=tmp_path,
        cwd=tmp_path,
        run_dir=run_dir,
        argv=["python"],
        env={},
        privacy=RunPrivacy(tmp_path, hostname="fixture-host", username="fixture-user"),
        manifest=manifest,
        project_rules=None,
        snapshot=True,
        max_bytes=1_048_576,
        document_data={"reprollm.yaml": original},
    )
    assert opened == []
    assert record.manifest is not None
    file = next(item for item in record.files if item.path == "reprollm.yaml")
    expected = "sha256:" + hashlib.sha256(original).hexdigest()
    assert file.sha256 == record.manifest.sha256 == expected
    assert record.input_capture is not None
    check = next(item for item in record.input_capture.checks if item.path == "reprollm.yaml")
    assert check.origin == "manifest" and check.before.sha256 == expected
    assert record.bindings_observed["generation.temperature"][0].value == 0.1


def test_recheck_freezes_path_set_and_distinguishes_creation_removal_and_change(
    tmp_path: Path,
) -> None:
    from reprollm.run.input_capture import recheck_inputs

    (tmp_path / "removed.txt").write_bytes(b"before")
    (tmp_path / "changed.txt").write_bytes(b"before")
    (tmp_path / "same.txt").write_bytes(b"same")
    record, _ = _capture(
        tmp_path,
        files=["created.txt", "removed.txt", "changed.txt", "same.txt"],
        argv=["python", "--config=argv-created.txt", "changed.txt"],
        snapshot=False,
    )
    assert record.input_capture is not None
    before = {check.path: check.before.model_dump() for check in record.input_capture.checks}
    (tmp_path / "created.txt").write_bytes(b"created")
    (tmp_path / "removed.txt").unlink()
    (tmp_path / "changed.txt").write_bytes(b"after")
    (tmp_path / "argv-created.txt").write_bytes(b"ignored")
    (tmp_path / "new-unmentioned.txt").write_bytes(b"ignored")
    (tmp_path / "reprollm.lock").write_bytes(b"invalid lock syntax: [:]\n")
    recheck_inputs(record, root=tmp_path)
    checks = {check.path: check for check in record.input_capture.checks}
    assert set(checks) == set(before)
    assert {name: check.before.model_dump() for name, check in checks.items()} == before
    assert checks["created.txt"].change == "created"
    assert checks["removed.txt"].change == "removed"
    assert checks["changed.txt"].change == "changed"
    assert checks["same.txt"].change == "unchanged"
    assert checks["reprollm.lock"].change == "created"
    assert checks["changed.txt"].origin == "declared"
    assert record.lock is None


def test_unavailable_inputs_never_open_external_targets_and_recheck_stays_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from reprollm.run.input_capture import recheck_inputs

    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "private.json"
    raw = b'{"temperature": 0.9, "password": "ExternalCanaryValue"}\n'
    outside.write_bytes(raw)
    (root / "non-file.json").mkdir()
    (root / "will-escape.json").write_bytes(b'{"temperature": 0.1}\n')
    try:
        (root / "escape.json").symlink_to(outside)
        (root / "loop.json").symlink_to(root / "loop.json")
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    original_open = Path.open
    outside_opens: list[Path] = []

    def watch_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == outside:
            outside_opens.append(path)
            raise AssertionError("external file opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", watch_open)
    record, _ = _capture(
        root,
        files=["escape.json", "non-file.json", "loop.json", "will-escape.json"],
        bindings={"generation.temperature": {"config": "escape.json:temperature"}},
    )
    assert record.input_capture is not None
    checks = {check.path: check for check in record.input_capture.checks}
    for name in ("escape.json", "non-file.json", "loop.json"):
        assert checks[name].before.availability == "unavailable"
    (root / "will-escape.json").unlink()
    (root / "will-escape.json").symlink_to(outside)
    recheck_inputs(record, root=root)
    checks = {check.path: check for check in record.input_capture.checks}
    for name in ("escape.json", "non-file.json", "loop.json", "will-escape.json"):
        assert checks[name].after.availability == "unavailable"
        assert checks[name].change == "unknown"
    assert outside_opens == []
    assert record.bindings_observed == {}
    assert "ExternalCanaryValue" not in record.model_dump_json()
    monkeypatch.setattr(Path, "open", original_open)
    assert outside.read_bytes() == raw


def test_one_snapshot_failure_keeps_original_hash_binding_and_other_file_copies(
    tmp_path: Path,
) -> None:
    class FailingPrivacy(RunPrivacy):
        def text(
            self,
            value: str,
            *,
            manifest: bool = False,
            keys: tuple[str, ...] = (),
        ) -> tuple[str, int]:
            if "SnapshotFailure" in value:
                raise ValueError("PrivateDiagnosticCanary")
            return super().text(value, manifest=manifest, keys=keys)

    bad = b'{"temperature": 0.1, "label": "SnapshotFailure"}\n'
    good = b'{"temperature": 0.2}\n'
    (tmp_path / "a-bad.json").write_bytes(bad)
    (tmp_path / "z-good.json").write_bytes(good)
    record, run_dir = _capture(
        tmp_path,
        files=["a-bad.json", "z-good.json"],
        bindings={"generation.temperature": {"config": "a-bad.json:temperature"}},
        privacy=FailingPrivacy(tmp_path, hostname="fixture-host", username="fixture-user"),
    )
    assert [file.path for file in record.files] == ["a-bad.json", "z-good.json"]
    failed, safe = record.files
    assert failed.sha256 == "sha256:" + hashlib.sha256(bad).hexdigest()
    assert failed.snapshot is None
    assert safe.snapshot is not None and (run_dir / safe.snapshot).read_bytes() == good
    assert record.bindings_observed["generation.temperature"][0].value == 0.1
    assert "input file snapshot unavailable" in record.warnings
    assert "PrivateDiagnosticCanary" not in record.model_dump_json()


def test_unreadable_config_is_unavailable_not_missing_and_does_not_abort_safe_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocked = tmp_path / "blocked.json"
    blocked.write_bytes(b'{"temperature": 0.1}\n')
    (tmp_path / "safe.txt").write_bytes(b"safe\n")
    original_open = Path.open

    def deny_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == blocked:
            raise PermissionError("PrivateDiagnosticCanary")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_open)
    record, run_dir = _capture(
        tmp_path,
        files=["blocked.json", "safe.txt"],
        bindings={"generation.temperature": {"config": "blocked.json:temperature"}},
    )
    assert record.input_capture is not None
    check = next(item for item in record.input_capture.checks if item.path == "blocked.json")
    assert check.before.availability == "unavailable" and check.change == "unknown"
    assert [file.path for file in record.files] == ["safe.txt"]
    assert record.files[0].snapshot is not None
    assert (run_dir / record.files[0].snapshot).read_bytes() == b"safe\n"
    assert record.bindings_observed == {}
    assert "PrivateDiagnosticCanary" not in record.model_dump_json()
