from __future__ import annotations

from pathlib import Path

import pytest

from reprollm.core.errors import UserError
from reprollm.lock import local_resolver
from reprollm.lock.local_resolver import resolve_local_dataset, resolve_local_model
from reprollm.schemas.lock import Confidence
from reprollm.schemas.manifest import DatasetSpec, ModelSpec

from .helpers import NOW


def test_local_directory_hashes_metadata_and_small_weights(tmp_path: Path) -> None:
    model_dir = tmp_path / "models/tiny"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text('{"type": "tiny"}', encoding="utf-8")
    (model_dir / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (model_dir / "tokenizer.json").write_text('{"version": "1"}', encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"weights")

    lock = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id="models/tiny"),
        hash_large_files=False,
        now=NOW,
    )

    assert lock.local is not None
    assert lock.local.config_sha256 is not None
    assert lock.local.config_sha256.confidence == Confidence.EXACT
    assert lock.local.weights.hashed is True
    assert lock.local.weights.total_size_bytes == 7
    assert lock.local.weights.sha256 is not None
    first_metadata_hash = lock.local.config_sha256.value

    (model_dir / "tokenizer.json").write_text('{"version": "2"}', encoding="utf-8")
    changed = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id="models/tiny"),
        hash_large_files=False,
        now=NOW,
    )
    assert changed.local is not None
    assert changed.local.config_sha256 is not None
    assert changed.local.config_sha256.value != first_metadata_hash


def test_large_local_weights_record_size_without_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(local_resolver, "MAX_AUTO_HASH_BYTES", 4)
    model_dir = tmp_path / "models/large"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.bin").write_bytes(b"12345")

    skipped = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id="models/large"),
        hash_large_files=False,
        now=NOW,
    )
    hashed = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id="models/large"),
        hash_large_files=True,
        now=NOW,
    )

    assert skipped.local is not None and hashed.local is not None
    assert skipped.local.weights.model_dump() == {
        "hashed": False,
        "total_size_bytes": 5,
        "sha256": None,
    }
    assert hashed.local.weights.hashed is True
    assert hashed.local.weights.sha256 is not None


def test_single_local_model_file_is_hashed(tmp_path: Path) -> None:
    path = tmp_path / "models/tiny.gguf"
    path.parent.mkdir()
    path.write_bytes(b"gguf")

    lock = resolve_local_model(
        tmp_path,
        ModelSpec(provider="local", id="models/tiny.gguf"),
        hash_large_files=False,
        now=NOW,
    )

    assert lock.local is not None
    assert lock.local.weights.total_size_bytes == 4
    assert lock.local.weights.hashed is True


def test_missing_or_escaping_local_model_is_actionable(tmp_path: Path) -> None:
    with pytest.raises(UserError, match=r"models\.primary\.id|local model"):
        resolve_local_model(
            tmp_path,
            ModelSpec(provider="local", id="models/missing"),
            hash_large_files=False,
            now=NOW,
            field_path="models.primary.id",
        )


def test_local_dataset_hashes_existing_declared_files_and_omits_missing(tmp_path: Path) -> None:
    data = tmp_path / "data/items.jsonl"
    data.parent.mkdir()
    data.write_text('{"x": 1}\n', encoding="utf-8")
    spec = DatasetSpec.model_validate(
        {
            "provider": "local",
            "id": "data",
            "files": ["data/missing.jsonl", "data/items.jsonl"],
        }
    )

    lock = resolve_local_dataset(tmp_path, spec, now=NOW)

    assert lock.revision.source == "filesystem"
    assert lock.files is not None
    assert [item.path for item in lock.files] == ["data/items.jsonl"]
