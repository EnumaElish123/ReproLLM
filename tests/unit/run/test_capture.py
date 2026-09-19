"""M5-T03 file containment, original hashes and redacted snapshots."""

import hashlib
from pathlib import Path

import pytest

from reprollm.core.errors import UserError
from reprollm.run.capture import (
    FileRef,
    collect_outputs,
    declared_files,
    hash_and_snapshot,
    resolve_argv_files,
)
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.run_record import RunFileOrigin


def test_argv_resolves_files_relative_to_cwd_and_deduplicates(tmp_path: Path) -> None:
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/eval.yaml").write_text("value: 1")
    (tmp_path / "work").mkdir()
    found = resolve_argv_files(
        [
            "python",
            "--config=../configs/eval.yaml",
            "../configs/eval.yaml",
            "../missing",
            "../configs",
            str(tmp_path.parent / "outside"),
        ],
        tmp_path,
        tmp_path / "work",
    )
    assert found == [FileRef("configs/eval.yaml", RunFileOrigin.ARGV)]


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.yaml"
    outside.write_text("private: material")
    link = root / "escape.yaml"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    assert resolve_argv_files(["escape.yaml"], root, root) == []
    assert (
        hash_and_snapshot(
            [FileRef("escape.yaml", RunFileOrigin.DECLARED)],
            root / "run",
            root=root,
            snapshot=True,
            max_bytes=1024,
        )
        == []
    )


def test_declared_file_sources_include_prompts_and_binding_configs() -> None:
    manifest = Manifest.model_validate(
        {
            "schema_version": 1,
            "project": {"name": "test"},
            "experiment": {"profiles": []},
            "execution": {"config_files": ["configs/eval.yaml"]},
            "bindings": {"generation.temperature": {"config": "configs/bound.json:temperature"}},
            "prompts": {"system": {"path": "prompts/system.txt"}},
            "training": {"deepspeed": {"config": "configs/ds.json"}},
            "models": {
                "primary": {
                    "provider": "huggingface",
                    "id": "org/model",
                    "chat_template": {"path": "chat.jinja"},
                }
            },
            "evaluation": {"definitions": {"refusal": "rules/refusal.py"}},
            "privacy": {"threat_model": "threat.md"},
        }
    )
    found = declared_files(manifest)
    assert [f.path for f in found] == [
        "chat.jinja",
        "configs/bound.json",
        "configs/ds.json",
        "configs/eval.yaml",
        "prompts/system.txt",
        "rules/refusal.py",
        "threat.md",
    ]
    assert all(f.origin == RunFileOrigin.DECLARED for f in found)


def test_snapshot_hashes_original_bytes_but_persists_only_redacted_text(tmp_path: Path) -> None:
    original = b'password = "hunter2hunter2"\n'
    (tmp_path / "config.yaml").write_bytes(original)
    run = tmp_path / "run"
    refs = [
        FileRef("config.yaml", RunFileOrigin.ARGV),
        FileRef("config.yaml", RunFileOrigin.DECLARED),
    ]
    found = hash_and_snapshot(refs, run, root=tmp_path, snapshot=True, max_bytes=1024)
    assert len(found) == 1
    record = found[0]
    digest = hashlib.sha256(original).hexdigest()
    assert record.sha256 == "sha256:" + digest
    assert record.size_bytes == len(original)
    assert record.origin == RunFileOrigin.DECLARED
    assert record.redacted is True and record.snapshot == "files/" + digest
    assert (run / record.snapshot).read_text() == 'password = "<REDACTED:generic_kv>"\n'
    assert (tmp_path / "config.yaml").read_bytes() == original


def test_forbidden_binary_oversized_and_disabled_snapshots(tmp_path: Path) -> None:
    contents = {
        ".env": b"hidden",
        "data.bin": b"\0secret",
        "bad.bin": b"\xff",
        "large.txt": b"x" * 40,
        ".env.example": b"safe=1",
    }
    for name, data in contents.items():
        (tmp_path / name).write_bytes(data)
    refs = [FileRef(name, RunFileOrigin.ARGV) for name in contents]
    found = {
        f.path: f
        for f in hash_and_snapshot(
            refs, tmp_path / "run", root=tmp_path, snapshot=True, max_bytes=16
        )
    }
    assert found[".env"].redacted and found[".env"].snapshot is None
    for name in ("data.bin", "bad.bin", "large.txt"):
        assert found[name].snapshot is None
    assert found[".env.example"].snapshot is not None
    disabled = hash_and_snapshot(
        refs, tmp_path / "no-snapshot", root=tmp_path, snapshot=False, max_bytes=100
    )
    assert all(f.snapshot is None for f in disabled)
    assert not (tmp_path / "no-snapshot").exists()


def test_many_files_disable_snapshots_with_warning(tmp_path: Path) -> None:
    refs = []
    for index in range(201):
        name = f"file-{index}.txt"
        (tmp_path / name).write_text(str(index))
        refs.append(FileRef(name, RunFileOrigin.ARGV))
    warnings = []
    found = hash_and_snapshot(
        refs, tmp_path / "run", root=tmp_path, snapshot=True, max_bytes=1024, warnings=warnings
    )
    assert len(found) == 201 and all(f.snapshot is None for f in found)
    assert any("200" in warning for warning in warnings)


def test_outputs_are_sorted_deduplicated_and_only_hashed(tmp_path: Path) -> None:
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs/result.json").write_text('{"score":1}')
    found = collect_outputs(tmp_path, ["outputs/*", "outputs/result.json", "../*"])
    assert len(found) == 1
    assert found[0].path == "outputs/result.json"
    assert found[0].sha256 == "sha256:" + hashlib.sha256(b'{"score":1}').hexdigest()
    assert found[0].size_bytes == 11


def test_symlink_to_forbidden_file_inside_root_is_hash_only(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("private: material")
    try:
        (tmp_path / "safe.yaml").symlink_to(tmp_path / ".env")
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    found = hash_and_snapshot(
        [FileRef("safe.yaml", RunFileOrigin.ARGV)],
        tmp_path / "run",
        root=tmp_path,
        snapshot=True,
        max_bytes=1024,
    )
    assert len(found) == 1 and found[0].redacted and found[0].snapshot is None


def test_snapshot_destination_cannot_follow_symlink_outside_run(tmp_path: Path) -> None:
    (tmp_path / "input.txt").write_text("text")
    run = tmp_path / "run"
    run.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (run / "files").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links unavailable on this runner")
    with pytest.raises(UserError, match="snapshot destination"):
        hash_and_snapshot(
            [FileRef("input.txt", RunFileOrigin.ARGV)],
            run,
            root=tmp_path,
            snapshot=True,
            max_bytes=1024,
        )
    assert list(outside.iterdir()) == []
