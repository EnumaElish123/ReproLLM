"""Key context for the existing normative persisted-value secret patterns."""

from __future__ import annotations

from typing import Any

from reprollm.core.redaction import redact_text


def redact_keyed_values(value: Any, keys: tuple[str, ...] = ()) -> Any:
    """Apply §16.2 to leaves with their enclosing raw mapping keys.

    Containers retain their structure and unchanged scalars retain their types.
    Callers must pass data values, rather than transport metadata whose keys can
    describe a secret without containing its value.
    """
    if isinstance(value, dict):
        return {key: redact_keyed_values(item, (*keys, str(key))) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_keyed_values(item, keys) for item in value]
    original = str(value)
    safe = original
    for key in keys:
        prefix = f"{key}=\n"
        safe_prefix = redact_text(prefix)[0]
        redacted = redact_text(prefix + safe)[0]
        safe = (
            redacted[len(safe_prefix) :]
            if redacted.startswith(safe_prefix)
            else "<REDACTED:generic_kv>"
        )
    return value if safe == original else safe
