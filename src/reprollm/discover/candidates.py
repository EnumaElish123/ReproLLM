"""Candidate post-processing (spec §20.4, M7-T04).

Deterministic and defensive: evidence whose path is not among the collected
inputs lowers the candidate's confidence to ``low`` instead of being trusted.
"""

from __future__ import annotations

import getpass
import re
import socket
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

from reprollm.core.redaction import redact_text
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.discover_candidates import (
    Candidate,
    CandidateSuggestedBindings,
    DiscoverCandidates,
    candidate_id,
)

_LOCATOR = re.compile(r"#L[0-9]+$")


def sanitize_response_text(
    value: str, privacy: RunPrivacy, *, secret_values: tuple[str, ...] = ()
) -> tuple[str, int]:
    """Also remove credentials echoed by an endpoint using an unfamiliar key format."""
    count = 0
    for secret in sorted(set(secret_values), key=lambda item: (-len(item), item)):
        if secret:
            count += value.count(secret)
            value = value.replace(secret, "<REDACTED:credential>")
    safe, redactions = privacy.text(value)
    return safe, count + redactions


def _safe_relative_config_binding(
    value: str, privacy: RunPrivacy, *, secret_values: tuple[str, ...]
) -> bool:
    # Check the original before removing dot segments: an endpoint can echo a
    # credential containing './', and normalization must not hide that echo.
    if (
        "<REDACTED:" in value
        or any(secret and secret in value for secret in secret_values)
        or redact_text(value)[1]
        or any(pattern.search(value) for pattern, _kind in privacy.identities)
    ):
        return False
    path, separator, key = value.partition(":")
    if not path or not separator or not key or "\\" in path or PureWindowsPath(value).drive:
        return False
    relative = PurePosixPath(path)
    if relative.is_absolute() or ".." in relative.parts:
        return False
    safe, redactions = sanitize_response_text(
        f"{relative.as_posix()}:{key}", privacy, secret_values=secret_values
    )
    return redactions == 0 and "<REDACTED:" not in safe


def finalize(
    raw_candidates: list[Candidate],
    *,
    model: str,
    reprollm_version: str,
    input_files: list[str],
    dropped_files: list[str],
    truncated_files: list[str],
    generated_at: datetime,
    privacy: RunPrivacy | None = None,
    secret_values: tuple[str, ...] = (),
) -> DiscoverCandidates:
    if privacy is None:
        privacy = RunPrivacy(Path.cwd(), hostname=socket.gethostname(), username=getpass.getuser())

    def safe_text(value: str) -> tuple[str, int]:
        return sanitize_response_text(value, privacy, secret_values=secret_values)

    def safe_paths(paths: list[str]) -> list[str]:
        cleaned = [safe_text(path)[0] for path in paths]
        return sorted(path for path in cleaned if "<REDACTED:" not in path)

    inputs = safe_paths(input_files)
    # A real filename may itself end in #L12. Only generated snippet locators
    # should lose that suffix, so exact collected files take precedence.
    actual_files = {
        path
        for path in inputs
        if not Path(path).is_absolute()
        and ".." not in Path(path).parts
        and (privacy.root / path).is_file()
    }
    allowed = {_strip_locator(path, actual_files) for path in inputs}

    finalized: list[Candidate] = []
    for raw in raw_candidates:
        field, field_redactions = safe_text(raw.suggested_field)
        if field_redactions or "<REDACTED:" in field:
            continue
        name, name_redactions = safe_text(raw.name)
        trustable = name_redactions == 0 and "<REDACTED:" not in name
        first_path: str | None = None
        evidence = []
        for item in raw.evidence:
            path = _strip_locator(item.path, actual_files)
            safe_path = safe_text(path)[0] if path is not None else None
            if first_path is None and safe_path:
                first_path = safe_path
            if path is not None and path not in allowed:
                trustable = False
                continue
            evidence.append(
                item.model_copy(
                    update={
                        "path": safe_path,
                        "snippet": safe_text(item.snippet)[0] if item.snippet is not None else None,
                    }
                )
            )
        bindings = None
        if raw.suggested_bindings is not None:
            cleaned_bindings: dict[str, str | None] = {}
            for key, value in raw.suggested_bindings.model_dump().items():
                if value is None:
                    cleaned_bindings[key] = None
                    continue
                safe, redactions = safe_text(value)
                if (
                    (redactions or "<REDACTED:" in safe)
                    and key == "config"
                    and _safe_relative_config_binding(value, privacy, secret_values=secret_values)
                ):
                    cleaned_bindings[key] = value
                elif redactions or "<REDACTED:" in safe:
                    cleaned_bindings[key] = None
                    trustable = False
                else:
                    cleaned_bindings[key] = safe
            if any(value is not None for value in cleaned_bindings.values()):
                bindings = CandidateSuggestedBindings.model_validate(cleaned_bindings)
        finalized.append(
            raw.model_copy(
                update={
                    "id": candidate_id(raw.kind, name, first_path),
                    "name": name,
                    "suggested_field": field,
                    "rationale": safe_text(raw.rationale)[0],
                    "confidence": raw.confidence if trustable else "low",
                    "evidence": evidence,
                    "suggested_bindings": bindings,
                }
            )
        )
    finalized.sort(key=lambda c: (c.kind, c.name, c.id))
    return DiscoverCandidates(
        reprollm_version=safe_text(reprollm_version)[0],
        generated_at=generated_at.replace(tzinfo=timezone.utc, microsecond=0),
        model=safe_text(model)[0],
        input_files=inputs,
        dropped_files=safe_paths(dropped_files),
        truncated_files=safe_paths(truncated_files),
        candidates=finalized,
    )


def _strip_locator(path: str | None, actual_files: set[str]) -> str | None:
    """Snippets carry ``path#L12`` locators; evidence compares bare paths."""
    if path is None or path in actual_files:
        return path
    return _LOCATOR.sub("", path)
