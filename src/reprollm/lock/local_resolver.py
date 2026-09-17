"""Local model and dataset hashing (spec §4.3)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from reprollm.core.errors import UserError
from reprollm.core.hashing import sha256_bytes, sha256_file
from reprollm.schemas.lock import (
    AdapterLock,
    ChatTemplateLock,
    Confidence,
    DatasetFileLock,
    DatasetLock,
    LocalModelLock,
    ModelLock,
    Provenance,
    WeightsLock,
)
from reprollm.schemas.manifest import DatasetSpec, ModelSpec

MAX_AUTO_HASH_BYTES = 100 * 1024 * 1024
_MODEL_METADATA_FILES = ("config.json", "tokenizer_config.json", "tokenizer.json")
_WEIGHT_SUFFIXES = {".safetensors", ".bin", ".gguf", ".pt"}


def resolve_local_model(
    root: Path,
    spec: ModelSpec,
    *,
    hash_large_files: bool,
    now: datetime,
    field_path: str = "models.<role>.id",
) -> ModelLock:
    relative = spec.id or ""
    target = _safe_existing_path(root, relative, field_path)
    if target.is_dir():
        metadata = [target / name for name in _MODEL_METADATA_FILES if (target / name).is_file()]
        weights = sorted(
            (
                path
                for path in target.rglob("*")
                if path.is_file() and path.suffix.lower() in _WEIGHT_SUFFIXES
            ),
            key=lambda path: path.relative_to(target).as_posix(),
        )
        config_hash = _aggregate_hash(metadata, target) if metadata else None
        chat_template = _local_chat_template(root, spec, target, now)
    else:
        metadata = []
        weights = [target]
        config_hash = None
        chat_template = _custom_or_absent_chat_template(root, spec, now)

    total_size = sum(path.stat().st_size for path in weights)
    should_hash = hash_large_files or total_size <= MAX_AUTO_HASH_BYTES
    weights_hash = (
        _aggregate_hash(weights, target if target.is_dir() else target.parent)
        if should_hash
        else None
    )
    local = LocalModelLock(
        path=relative,
        config_sha256=(
            Provenance(
                value=config_hash,
                source="filesystem:config_files",
                confidence=Confidence.EXACT,
                resolved_at=now,
                note=", ".join(path.name for path in metadata),
            )
            if config_hash is not None
            else None
        ),
        weights=WeightsLock(
            hashed=should_hash,
            total_size_bytes=total_size,
            sha256=weights_hash,
        ),
    )
    return ModelLock(
        provider="local",
        id=relative,
        pinnability="exact",
        revision=Provenance(
            value=config_hash or weights_hash,
            source="filesystem",
            confidence=Confidence.EXACT,
            resolved_at=now,
        ),
        chat_template=chat_template,
        local=local,
        dtype=spec.dtype,
        quantization=spec.quantization,
        trust_remote_code=spec.trust_remote_code,
    )


def resolve_local_dataset(root: Path, spec: DatasetSpec, *, now: datetime) -> DatasetLock:
    files: list[DatasetFileLock] = []
    for relative in sorted(set(spec.files or [])):
        path = _safe_optional_file(root, relative)
        if path is None:
            continue
        files.append(
            DatasetFileLock(
                path=relative,
                sha256=sha256_file(path),
                size_bytes=path.stat().st_size,
            )
        )
    return DatasetLock(
        provider="local",
        id=spec.id or "",
        revision=Provenance(
            value=None,
            source="filesystem",
            confidence=Confidence.EXACT,
            resolved_at=now,
        ),
        subset=spec.subset,
        split=spec.split,
        files=files or None,
    )


def resolve_local_adapter(root: Path, adapter_id: str, *, now: datetime) -> AdapterLock:
    """Resolve a PEFT adapter directory without importing PEFT."""
    target = _safe_existing_path(root, adapter_id, "models.<role>.adapter.id")
    config = target / "adapter_config.json" if target.is_dir() else target
    config_hash = sha256_file(config) if config.is_file() else None
    return AdapterLock(
        id=adapter_id,
        revision=Provenance(
            value=config_hash,
            source="filesystem",
            confidence=Confidence.EXACT,
            resolved_at=now,
        ),
        config_sha256=(
            Provenance(
                value=config_hash,
                source="filesystem:adapter_config.json",
                confidence=Confidence.EXACT,
                resolved_at=now,
            )
            if config_hash is not None
            else None
        ),
    )


def is_local_path(root: Path, value: str) -> bool:
    try:
        candidate = _safe_candidate(root, value)
    except UserError:
        return False
    return candidate.exists()


def _local_chat_template(
    root: Path, spec: ModelSpec, model_dir: Path, now: datetime
) -> ChatTemplateLock:
    if spec.chat_template is not None:
        return _custom_or_absent_chat_template(root, spec, now)
    tokenizer_config = model_dir / "tokenizer_config.json"
    if tokenizer_config.is_file():
        try:
            value = json.loads(tokenizer_config.read_text(encoding="utf-8")).get("chat_template")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            value = None
        if value is not None:
            serialized = (
                value
                if isinstance(value, str)
                else json.dumps(value, sort_keys=True, ensure_ascii=False)
            )
            return ChatTemplateLock(
                sha256=Provenance(
                    value=sha256_bytes(serialized.encode("utf-8")),
                    source="filesystem:tokenizer_config.json",
                    confidence=Confidence.EXACT,
                    resolved_at=now,
                ),
                status="present",
            )
    return _absent_chat_template(now)


def _custom_or_absent_chat_template(root: Path, spec: ModelSpec, now: datetime) -> ChatTemplateLock:
    if spec.chat_template is None:
        return _absent_chat_template(now)
    relative = spec.chat_template.path
    path = _safe_optional_file(root, relative)
    if path is None:
        return ChatTemplateLock(
            sha256=Provenance(
                value=None,
                source="filesystem",
                confidence=Confidence.UNRESOLVED,
                note=f"missing file: {relative}",
            ),
            status="custom_file",
        )
    return ChatTemplateLock(
        sha256=Provenance(
            value=sha256_file(path),
            source="filesystem",
            confidence=Confidence.EXACT,
            resolved_at=now,
        ),
        status="custom_file",
    )


def _absent_chat_template(now: datetime) -> ChatTemplateLock:
    return ChatTemplateLock(
        sha256=Provenance(
            value=None,
            source="filesystem",
            confidence=Confidence.EXACT,
            resolved_at=now,
            note="model has no chat template",
        ),
        status="absent",
    )


def _aggregate_hash(paths: list[Path], base: Path) -> str:
    """Hash a sorted, path-delimited set without loading large files at once."""
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(base).as_posix()):
        relative = path.relative_to(base).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(len(chunk).to_bytes(8, "big"))
                digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _safe_candidate(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise UserError(f"local path {relative!r} must be relative to the project root")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        raise UserError(f"local path {relative!r} resolves outside the project root") from None
    return resolved


def _safe_existing_path(root: Path, relative: str, field_path: str) -> Path:
    target = _safe_candidate(root, relative)
    if not target.exists():
        raise UserError(
            f"{field_path} points to missing local model {relative!r}; "
            "fix the path in reprollm.yaml"
        )
    return target


def _safe_optional_file(root: Path, relative: str) -> Path | None:
    try:
        target = _safe_candidate(root, relative)
    except UserError:
        return None
    return target if target.is_file() else None
