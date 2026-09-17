"""Hugging Face model, dataset, tokenizer, and adapter resolution."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from reprollm.core.hashing import sha256_bytes, sha256_file
from reprollm.lock.hf_client import HfClient, HfError, RepoInfo
from reprollm.lock.local_resolver import is_local_path, resolve_local_adapter
from reprollm.schemas.lock import (
    AdapterLock,
    ChatTemplateLock,
    Confidence,
    DatasetLock,
    ModelLock,
    Provenance,
    TokenizerLock,
)
from reprollm.schemas.manifest import AdapterSpec, DatasetSpec, ModelSpec


def resolve_hf_model(
    root: Path,
    spec: ModelSpec,
    *,
    client: HfClient,
    offline: bool,
    now: datetime,
) -> ModelLock:
    model_id = spec.id or ""
    model_revision, model_info = _resolve_repo(
        client,
        "model",
        model_id,
        spec.revision,
        offline=offline,
        now=now,
    )

    tokenizer_id = spec.tokenizer.id if spec.tokenizer and spec.tokenizer.id else model_id
    tokenizer_declared = spec.tokenizer.revision if spec.tokenizer else None
    model_requested = spec.revision or "main"
    tokenizer_requested = tokenizer_declared or (
        model_requested if tokenizer_id == model_id else "main"
    )
    if tokenizer_id == model_id and tokenizer_requested == model_requested:
        tokenizer_revision, tokenizer_info = model_revision.model_copy(deep=True), model_info
    else:
        tokenizer_revision, tokenizer_info = _resolve_repo(
            client,
            "model",
            tokenizer_id,
            tokenizer_declared,
            offline=offline,
            now=now,
        )

    if spec.chat_template is not None:
        chat_template = _custom_chat_template(root, spec.chat_template.path, now)
    else:
        chat_template = _remote_chat_template(
            client,
            tokenizer_id,
            tokenizer_revision,
            tokenizer_info,
            offline=offline,
            now=now,
        )
    config_hash = _remote_file_hash(
        client,
        model_id,
        model_revision,
        model_info,
        "config.json",
        now,
    )
    adapter = (
        _resolve_adapter(root, spec.adapter, client=client, offline=offline, now=now)
        if spec.adapter is not None
        else None
    )
    return ModelLock(
        provider="huggingface",
        id=model_id,
        pinnability="exact",
        revision=model_revision,
        tokenizer=TokenizerLock(id=tokenizer_id, revision=tokenizer_revision),
        chat_template=chat_template,
        config_sha256=config_hash,
        adapter=adapter,
        dtype=spec.dtype,
        quantization=spec.quantization,
        trust_remote_code=spec.trust_remote_code,
    )


def resolve_hf_dataset(
    spec: DatasetSpec,
    *,
    client: HfClient,
    offline: bool,
    now: datetime,
) -> DatasetLock:
    dataset_id = spec.id or ""
    revision, _ = _resolve_repo(
        client,
        "dataset",
        dataset_id,
        spec.revision,
        offline=offline,
        now=now,
    )
    return DatasetLock(
        provider="huggingface",
        id=dataset_id,
        revision=revision,
        subset=spec.subset,
        split=spec.split,
    )


def _resolve_repo(
    client: HfClient,
    kind: Literal["model", "dataset"],
    repo_id: str,
    declared_revision: str | None,
    *,
    offline: bool,
    now: datetime,
) -> tuple[Provenance, RepoInfo | None]:
    if offline:
        if declared_revision is not None:
            return (
                Provenance(
                    value=declared_revision,
                    source="manifest",
                    confidence=Confidence.DECLARED,
                ),
                None,
            )
        return (
            Provenance(
                value=None,
                source="offline",
                confidence=Confidence.UNRESOLVED,
                note="offline mode; run reprollm lock with network access",
            ),
            None,
        )
    if not repo_id:
        return (
            Provenance(
                value=None,
                source="manifest_missing",
                confidence=Confidence.UNRESOLVED,
                note="repository id is not declared",
            ),
            None,
        )
    try:
        info = (
            client.model_info(repo_id, declared_revision or "main")
            if kind == "model"
            else client.dataset_info(repo_id, declared_revision or "main")
        )
    except HfError as exc:
        return (
            Provenance(
                value=None,
                source=exc.source,
                confidence=Confidence.UNRESOLVED,
                note=type(exc).__name__,
            ),
            None,
        )
    return (
        Provenance(
            value=info.sha,
            source="hf_api",
            confidence=Confidence.EXACT,
            resolved_at=now,
        ),
        info,
    )


def _remote_chat_template(
    client: HfClient,
    repo_id: str,
    revision: Provenance,
    info: RepoInfo | None,
    *,
    offline: bool,
    now: datetime,
) -> ChatTemplateLock:
    if (
        info is None
        or revision.confidence != Confidence.EXACT
        or not isinstance(revision.value, str)
    ):
        return ChatTemplateLock(
            sha256=Provenance(
                value=None,
                source="offline" if offline else revision.source,
                confidence=Confidence.UNRESOLVED,
                note=revision.note or "chat template repository revision is unresolved",
            ),
            status="present",
        )
    if "chat_template.jinja" in info.siblings:
        provenance = _fetch_hash(client, repo_id, revision.value, "chat_template.jinja", now=now)
        return ChatTemplateLock(sha256=provenance, status="present")
    if "tokenizer_config.json" in info.siblings:
        try:
            content = client.fetch_file("model", repo_id, revision.value, "tokenizer_config.json")
            payload = json.loads(content.decode("utf-8"))
            value = payload.get("chat_template") if isinstance(payload, dict) else None
        except (HfError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            source = exc.source if isinstance(exc, HfError) else "hf_file:tokenizer_config.json"
            return ChatTemplateLock(
                sha256=Provenance(
                    value=None,
                    source=source,
                    confidence=Confidence.UNRESOLVED,
                    note=type(exc).__name__,
                ),
                status="present",
            )
        if value is not None:
            serialized = (
                value
                if isinstance(value, str)
                else json.dumps(value, sort_keys=True, ensure_ascii=False)
            )
            return ChatTemplateLock(
                sha256=Provenance(
                    value=sha256_bytes(serialized.encode("utf-8")),
                    source="hf_file:tokenizer_config.json",
                    confidence=Confidence.EXACT,
                    resolved_at=now,
                ),
                status="present",
            )
    return ChatTemplateLock(
        sha256=Provenance(
            value=None,
            source="hf_api",
            confidence=Confidence.EXACT,
            resolved_at=now,
            note="model has no chat template",
        ),
        status="absent",
    )


def _custom_chat_template(root: Path, relative: str, now: datetime) -> ChatTemplateLock:
    path = _safe_project_file(root, relative)
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


def _remote_file_hash(
    client: HfClient,
    repo_id: str,
    revision: Provenance,
    info: RepoInfo | None,
    filename: str,
    now: datetime,
) -> Provenance | None:
    if info is None:
        if revision.confidence == Confidence.UNRESOLVED:
            return Provenance(
                value=None,
                source=revision.source,
                confidence=Confidence.UNRESOLVED,
                note=revision.note,
            )
        return None
    if filename not in info.siblings or not isinstance(revision.value, str):
        return None
    return _fetch_hash(client, repo_id, revision.value, filename, now=now)


def _fetch_hash(
    client: HfClient, repo_id: str, sha: str, filename: str, *, now: datetime
) -> Provenance:
    try:
        content = client.fetch_file("model", repo_id, sha, filename)
    except HfError as exc:
        return Provenance(
            value=None,
            source=exc.source,
            confidence=Confidence.UNRESOLVED,
            note=type(exc).__name__,
        )
    return Provenance(
        value=sha256_bytes(content),
        source=f"hf_file:{filename}",
        confidence=Confidence.EXACT,
        resolved_at=now,
    )


def _resolve_adapter(
    root: Path,
    spec: AdapterSpec,
    *,
    client: HfClient,
    offline: bool,
    now: datetime,
) -> AdapterLock:
    if spec.provider == "peft" and is_local_path(root, spec.id):
        return resolve_local_adapter(root, spec.id, now=now)
    if spec.provider != "peft":
        return AdapterLock(
            id=spec.id,
            revision=Provenance(
                value=spec.revision,
                source="manifest" if spec.revision else "provider_no_pinning",
                confidence=(Confidence.DECLARED if spec.revision else Confidence.UNRESOLVED),
            ),
        )
    revision, info = _resolve_repo(
        client,
        "model",
        spec.id,
        spec.revision,
        offline=offline,
        now=now,
    )
    return AdapterLock(
        id=spec.id,
        revision=revision,
        config_sha256=_remote_file_hash(
            client, spec.id, revision, info, "adapter_config.json", now
        ),
    )


def _safe_project_file(root: Path, relative: str) -> Path | None:
    path = Path(relative)
    if path.is_absolute():
        return None
    resolved_root = root.resolve()
    resolved = (resolved_root / path).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved if resolved.is_file() else None
