"""Sanitize decoded JSON strings while retaining untouched lexical source spans."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

_LIMIT = 1_048_576
_NODE_LIMIT = 10_000
_DEPTH_LIMIT = 64
_STRING = re.compile(r'"(?:\\.|[^"\\])*"', re.DOTALL)


class _Object(list[tuple[str, Any]]):
    """Retain duplicate mapping keys for the aggregate structure limit."""


def _invalid_constant(value: str) -> None:
    raise ValueError("non-JSON capture constant")


def _load(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_Object, parse_constant=_invalid_constant)


def _documents(text: str) -> list[Any] | None:
    try:
        return [_load(text)]
    except RecursionError:
        raise ValueError("capture structure limit exceeded") from None
    except ValueError:
        pass

    # Split on the JSONL record delimiter only. Other Unicode line separators
    # are legal literal characters within a JSON string.
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    if len(lines) < 2 or any(not line.strip(" \r\t") for line in lines):
        return None
    documents = []
    for line in lines:
        try:
            documents.append(_load(line))
        except RecursionError:
            raise ValueError("capture structure limit exceeded") from None
        except ValueError:
            return None
    return documents


def _check_limits(text: str, documents: list[Any]) -> None:
    if len(text) > _LIMIT or len(text.encode("utf-8")) > _LIMIT:
        raise ValueError("capture structure size limit exceeded")
    pending = [(document, 0) for document in documents]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if visited > _NODE_LIMIT or depth > _DEPTH_LIMIT:
            raise ValueError("capture structure limit exceeded")
        if isinstance(value, _Object):
            for key, item in value:
                pending.extend(((key, depth + 1), (item, depth + 1)))
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)


def redact_json_strings(
    text: str, sanitize: Callable[[str], tuple[str, int]]
) -> tuple[str, int] | None:
    """Recognize complete JSON or JSONL before touching any decoded string.

    The caller owns scalar privacy policy, secret-key context and any recursive
    interpretation of serialized strings. A recognized document must not later
    be scanned as raw escape syntax: ``A:\\n`` is a role label plus a newline
    after JSON decoding, while ``A:\\\\new`` contains a genuine drive path.
    """
    documents = _documents(text)
    if documents is None:
        return None
    _check_limits(text, documents)
    replacements = []
    count = 0
    for match in _STRING.finditer(text):
        original = json.loads(match[0])
        safe, replaced = sanitize(original)
        count += replaced
        if safe != original:
            replacements.append((match.start(), match.end(), json.dumps(safe, ensure_ascii=False)))
    for start, end, safe in reversed(replacements):
        text = text[:start] + safe + text[end:]
    return text, count
