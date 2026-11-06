"""Issue #15: opaque .pth directory inventory and unchanged local-lock boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from reprollm.lock import local_resolver
from reprollm.lock.local_resolver import resolve_local_model
from reprollm.schemas.manifest import ModelSpec

from .helpers import NOW

PAYLOAD_A = b"\x00pth A\xff"
PAYLOAD_B = b"\x00pth B\xff"
PTH_A = "sha256:d1d69f8f6d5f40cd46c059e7827bfa8ae283e71fabbd72ef7f0c9cef744ade72"
PTH_B = "sha256:37d078a35c41dfd068db2163fda5ef7627722b396111f9a938aaccde55b99775"
EMPTY = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
CONFIG = "sha256:827d56ad113e9d1530e6cb1e899f8a2f99bcb7e2336107590c11d0546d7115b8"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("classifier.pth", PTH_A),
        (
            "classifier.PTH",
            "sha256:89025d5af0f5d0c23781f339db13cc8d4daaf57e89f70569eabeec8dead7e963",
        ),
        (
            "nested/classifier.PtH",
            "sha256:5eb48423daa9243079cf8275c11cc8be24ad6dc6c9eb26ab5f6fd33c759ad644",
        ),
        (
            "classifier.pt",
            "sha256:958dd6b742602cc0ad4b1b02c62fa71df22b849faea5876b7a4b3e9d30d605dc",
        ),
        (
            "classifier.bin",
            "sha256:54acc39667db47735da92b15ec5822520d283c02c815ae5908a612e31d93eb81",
        ),
        (
            "classifier.gguf",
            "sha256:9e683c63b27294ec0a9705842b6dc64914fdec4f32b6a1220218f1ea7d24d521",
        ),
        (
            "classifier.safetensors",
            "sha256:79dd7e1371f8af62585ebf78c6b1d89e2ad2f639e95451b04f65bd42649c18da",
        ),
    ],
)
def test_directory_inventory_hashes_opaque_bytes_and_preserves_old_suffixes(
    tmp_path: Path, name: str, expected: str
) -> None:
    path = tmp_path / "weights" / name
    path.parent.mkdir(parents=True)
    path.write_bytes(PAYLOAD_A)
    spec = ModelSpec(provider="local", id="weights")

    first = resolve_local_model(tmp_path, spec, hash_large_files=False, now=NOW)
    assert first.local is not None
    assert first.local.weights.model_dump() == {
        "hashed": True,
        "total_size_bytes": 7,
        "sha256": expected,
    }
    assert first.local.config_sha256 is None
    assert first.revision.value == expected

    path.write_bytes(PAYLOAD_B)
    second = resolve_local_model(tmp_path, spec, hash_large_files=False, now=NOW)
    assert second.local is not None
    assert second.local.weights.total_size_bytes == 7
    assert second.local.weights.sha256 not in {None, expected, EMPTY}
    assert second.revision.value == second.local.weights.sha256
    assert path.read_bytes() == PAYLOAD_B


def test_fixed_metadata_remains_revision_authority_when_pth_changes(tmp_path: Path) -> None:
    directory = tmp_path / "weights"
    directory.mkdir()
    (directory / "config.json").write_bytes(b"{}")
    path = directory / "classifier.pth"
    path.write_bytes(PAYLOAD_A)
    spec = ModelSpec(provider="local", id="weights")
    first = resolve_local_model(tmp_path, spec, hash_large_files=False, now=NOW)
    path.write_bytes(PAYLOAD_B)
    second = resolve_local_model(tmp_path, spec, hash_large_files=False, now=NOW)

    assert first.local is not None and second.local is not None
    assert first.local.weights.sha256 == PTH_A
    assert second.local.weights.sha256 == PTH_B
    assert first.local.config_sha256 == second.local.config_sha256
    assert first.local.config_sha256 is not None
    assert first.local.config_sha256.value == CONFIG
    assert first.revision == second.revision
    assert first.revision.value == CONFIG
    assert first.chat_template == second.chat_template


def test_mixed_recursive_inventory_is_independent_of_creation_order(tmp_path: Path) -> None:
    entries = [
        ("z.bin", b"b"),
        ("nested/c.pth", b"c"),
        ("a.safetensors", b"a"),
        ("m.gguf", b"m"),
        ("p.pt", b"p"),
    ]
    expected = "sha256:a53d4ee6a1f680689538e3048caacffbcccedd406d8ec3f08943b7319a1a2189"
    for directory_name, rows in (("forward", entries), ("reverse", list(reversed(entries)))):
        directory = tmp_path / directory_name
        for name, payload in rows:
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        (directory / "ignored.pth.tmp").write_bytes(b"ignored")
        (directory / "folder.pth").mkdir()
        lock = resolve_local_model(
            tmp_path,
            ModelSpec(provider="local", id=directory_name),
            hash_large_files=False,
            now=NOW,
        )
        assert lock.local is not None
        assert lock.local.weights.model_dump() == {
            "hashed": True,
            "total_size_bytes": 5,
            "sha256": expected,
        }


@pytest.mark.parametrize("content", ["empty", "unsupported", "directory"])
def test_zero_weight_inventory_policy_is_unchanged(tmp_path: Path, content: str) -> None:
    directory = tmp_path / "weights"
    directory.mkdir()
    if content == "unsupported":
        (directory / "classifier.pth.tmp").write_bytes(PAYLOAD_A)
    elif content == "directory":
        (directory / "classifier.pth").mkdir()
    lock = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id="weights"),
        hash_large_files=False,
        now=NOW,
    )
    assert lock.local is not None
    assert lock.local.weights.model_dump() == {
        "hashed": True,
        "total_size_bytes": 0,
        "sha256": EMPTY,
    }
    assert lock.revision.value == EMPTY


@pytest.mark.parametrize("explicit_file", [False, True], ids=["directory", "file-control"])
@pytest.mark.parametrize("force_hash", [False, True], ids=["default", "forced"])
@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (3, "sha256:ef3db0e5ebf066376c18968c699d6d30097a30ed989e153e62e250002f2e1792"),
        (4, "sha256:a7d45779b61a03a135c6f4fbf979772d6f7fca19298f9012ff2e8c974cdad20a"),
        (5, "sha256:26f61cfbaa6eaa2084cd528560bb0bf866cc7a6d08c0e0d25094bd341d96201e"),
    ],
)
def test_pth_threshold_boundary_and_explicit_file_compatibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    explicit_file: bool,
    force_hash: bool,
    size: int,
    expected: str,
) -> None:
    monkeypatch.setattr(local_resolver, "MAX_AUTO_HASH_BYTES", 4)
    directory = tmp_path / "weights"
    directory.mkdir()
    (directory / "classifier.pth").write_bytes(b"x" * size)
    identifier = "weights/classifier.pth" if explicit_file else "weights"
    lock = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id=identifier),
        hash_large_files=force_hash,
        now=NOW,
    )
    expected_hash = expected if force_hash or size <= 4 else None
    assert lock.local is not None
    assert lock.local.weights.model_dump() == {
        "hashed": expected_hash is not None,
        "total_size_bytes": size,
        "sha256": expected_hash,
    }
    assert lock.revision.value == expected_hash


@pytest.mark.parametrize("with_config", [False, True])
def test_pth_addition_can_cross_total_threshold_for_existing_weights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_config: bool
) -> None:
    monkeypatch.setattr(local_resolver, "MAX_AUTO_HASH_BYTES", 4)
    directory = tmp_path / "weights"
    directory.mkdir()
    (directory / "old.bin").write_bytes(b"abc")
    if with_config:
        (directory / "config.json").write_bytes(b"{}")
    spec = ModelSpec(provider="local", id="weights")
    old = resolve_local_model(tmp_path, spec, hash_large_files=False, now=NOW)
    assert old.local is not None and old.local.weights.hashed
    assert old.local.weights.total_size_bytes == 3

    (directory / "new.pth").write_bytes(b"de")
    limited = resolve_local_model(tmp_path, spec, hash_large_files=False, now=NOW)
    forced = resolve_local_model(tmp_path, spec, hash_large_files=True, now=NOW)
    assert limited.local is not None and forced.local is not None
    assert limited.local.weights.model_dump() == {
        "hashed": False,
        "total_size_bytes": 5,
        "sha256": None,
    }
    expected = "sha256:383a6dae2efa793defff640e756d3421c0d45db31247e7fcaaf3a1897fce0e2c"
    assert forced.local.weights.model_dump() == {
        "hashed": True,
        "total_size_bytes": 5,
        "sha256": expected,
    }
    assert limited.revision.value == (CONFIG if with_config else None)
    assert forced.revision.value == (CONFIG if with_config else expected)
