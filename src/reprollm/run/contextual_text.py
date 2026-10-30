"""Apply existing secret patterns with capture context and preserve safe source bytes."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, time
from typing import Any

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
from yaml.tokens import ScalarToken

from reprollm.core._toml import tomllib
from reprollm.core.persistence import redact_keyed_values
from reprollm.core.redaction import redact_lines, redact_text

_QUOTED = r'"(?:\\.|[^"\\])*"' + r"|'(?:''|[^'])*'"
_KEY_AT_START = re.compile(rf"(?P<key>{_QUOTED}|[\w.-]+)\s*[:=]\s*")
_KEY_SCAN = re.compile(rf"(?P<key>{_QUOTED}|(?<![\w.-])[\w.-]+)\s*[:=]\s*")
_DOCUMENT = re.compile(rf"^(?:---\s*)?(?:[\[{{]|(?:{_QUOTED}|[\w.-]+)\s*:|-(?:\s|$))")
_LIMIT = 1_048_576
_NODE_LIMIT = 10_000
_DEPTH_LIMIT = 64
_PROBE = "captureContextProbe123"
_TOML_PART = r'"(?:\\.|[^"\\])*"|\'[^\'\n]*\'|[A-Za-z0-9_-]+'
_TOML_PATH = rf"(?:{_TOML_PART})(?:[ \t]*\.[ \t]*(?:{_TOML_PART}))*"
_TOML_HEADER = re.compile(rf"\[(?P<array>\[)?[ \t]*(?P<key>{_TOML_PATH})[ \t]*\](?(array)\])")
_TOML_ASSIGN = re.compile(rf"(?P<key>{_TOML_PATH})[ \t]*=[ \t]*")
_TOML_DOCUMENT = re.compile(rf"(?m)^[ \t]*(?:\[\[?[ \t]*(?:{_TOML_PATH})|(?:{_TOML_PATH})[ \t]*=)")


class _UnsafeCapture(ValueError):
    pass


def _search_key(text: str, cursor: int) -> re.Match[str] | None:
    # Preserve a suffix at the caller's cursor; later word interiors cannot be first matches.
    return _KEY_AT_START.match(text, cursor) or _KEY_SCAN.search(text, cursor)


def _secret_key(key: str) -> bool:
    return bool(redact_keyed_values(_PROBE, (key,)) != _PROBE)


def _decode(raw: str) -> str:
    if raw.startswith('"'):
        try:
            return str(json.loads(raw))
        except ValueError:
            return str(yaml.safe_load(raw))
    if raw.startswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


def _encoded(safe: str, raw: str) -> str:
    if raw.startswith("'"):
        return "'" + safe.replace("'", "''") + "'"
    # Double quotes work in both JSON and YAML, including formerly numeric leaves.
    result = json.dumps(safe, ensure_ascii=False)
    return result + ("\n" if raw.endswith("\n") else "")


def _has_unsafe_context(text: str) -> bool:
    probe = text.replace('\\"', '"').replace("\\'", "'")
    for match in _KEY_SCAN.finditer(probe):
        try:
            key = _decode(match["key"])
        except (ValueError, yaml.YAMLError):
            continue
        tail = probe[match.end() :]
        if redact_keyed_values(tail, (key,)) != tail:
            return True
    return False


def _pem_safe(text: str) -> str:
    if "-----BEGIN " not in text or "PRIVATE KEY-----" not in text:
        return text
    protected, originals, _ = shield_contextual_keys(text)
    safe = "".join(redact_lines(protected.splitlines(keepends=True)))
    for marker, original in originals.items():
        safe = safe.replace(marker, original)
    return safe


def _gap_safe(text: str, *, patterns: bool = True) -> str:
    replacements = []
    index = 0
    while index < len(text):
        if text[index] in "\"'":
            index = _value_end(text, index)
        elif text[index] == "#":
            end = text.find("\n", index)
            end = len(text) if end < 0 else end
            safe = redact_text(_fragments(_pem_safe(text[index:end]), 0)[0])[0]
            if safe != text[index:end]:
                replacements.append((index, end, safe))
            index = end
        else:
            index += 1
    for start, end, safe in reversed(replacements):
        text = text[:start] + safe + text[end:]
    return redact_text(text)[0] if patterns else text


def _toml_path(raw: str) -> tuple[str, ...]:
    value: Any = tomllib.loads(raw + " = 0")
    keys = []
    while isinstance(value, dict) and len(value) == 1:
        key, value = next(iter(value.items()))
        keys.append(key)
    return tuple(keys)


def _toml_safe(value: Any, keys: tuple[str, ...], visited: list[int], depth: int = 0) -> Any:
    visited[0] += 1
    if visited[0] > _NODE_LIMIT or depth > _DEPTH_LIMIT:
        raise _UnsafeCapture("capture structure limit exceeded")
    if isinstance(value, dict):
        if any(redact_text(_fragments(key, 0)[0])[0] != key for key in value):
            raise _UnsafeCapture("cannot sanitize captured table key")
        return {
            key: _toml_safe(item, (*keys, key), visited, depth + 1) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_toml_safe(item, keys, visited, depth + 1) for item in value]
    safe = redact_keyed_values(_pem_safe(value) if isinstance(value, str) else value, keys)
    if isinstance(safe, str):
        safe = _fragments(safe, 0)[0]
        return redact_text(safe)[0]
    return safe


def _toml_encoded(value: Any) -> str:
    if isinstance(value, dict):
        return (
            "{"
            + ", ".join(
                f"{json.dumps(key, ensure_ascii=False)} = {_toml_encoded(item)}"
                for key, item in value.items()
            )
            + "}"
        )
    if isinstance(value, list):
        return "[" + ", ".join(_toml_encoded(item) for item in value) + "]"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return repr(value)
    raise _UnsafeCapture("unsupported capture scalar")


def _toml_value_end(text: str, start: int) -> int:
    if text[start] in "\"'":
        quote = text[start]
        if text.startswith(quote * 3, start):
            index = start + 3
            while index < len(text):
                if quote == '"' and text[index] == "\\":
                    index += 2
                elif text.startswith(quote * 3, index):
                    index += 3
                    while index < len(text) and text[index] == quote:
                        index += 1
                    return index
                else:
                    index += 1
            raise _UnsafeCapture("unfinished capture scalar")
        return _value_end(text, start)
    if text[start] in "[{":
        stack = [text[start]]
        index = start + 1
        while stack and index < len(text):
            char = text[index]
            if char in "\"'":
                index = _toml_value_end(text, index)
                continue
            if char == "#":
                newline = text.find("\n", index)
                index = len(text) if newline < 0 else newline + 1
                continue
            if char in "[{":
                stack.append(char)
            elif char in "]}" and (stack.pop(), char) not in {("[", "]"), ("{", "}")}:
                raise _UnsafeCapture("invalid capture structure")
            index += 1
        if stack:
            raise _UnsafeCapture("unfinished capture structure")
        return index
    index = start
    while index < len(text) and text[index] not in "\n#":
        index += 1
    while index > start and text[index - 1].isspace():
        index -= 1
    return index


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _toml(text: str, keys: tuple[str, ...]) -> tuple[str, int] | None:
    if not _TOML_DOCUMENT.search(text):
        return None
    if len(text) > _LIMIT or len(text.encode("utf-8")) > _LIMIT:
        raise _UnsafeCapture("capture structure size limit exceeded")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        if any(_secret_key(key) for key in keys):
            raise _UnsafeCapture("cannot sanitize secret capture assignment") from None
        for line in text.splitlines():
            header = _TOML_HEADER.match(line.lstrip())
            if header and any(_secret_key(key) for key in _toml_path(header["key"])):
                raise _UnsafeCapture("cannot sanitize secret capture table") from None
        return None
    expected = _toml_safe(data, keys, [0])
    replacements: list[tuple[int, int, str]] = []
    cursor = 0
    table: tuple[str, ...] = ()
    value_spans: list[tuple[int, int]] = []
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue
        if text[cursor] == "#":
            newline = text.find("\n", cursor)
            cursor = len(text) if newline < 0 else newline + 1
            continue
        header = _TOML_HEADER.match(text, cursor)
        if header:
            table = _toml_path(header["key"])
            cursor = header.end()
            continue
        assignment = _TOML_ASSIGN.match(text, cursor)
        if assignment is None:
            raise _UnsafeCapture("unsupported capture assignment")
        start = assignment.end()
        end = _toml_value_end(text, start)
        raw = text[start:end]
        original = tomllib.loads("value = " + raw)["value"]
        safe = _toml_safe(original, (*keys, *table, *_toml_path(assignment["key"])), [0])
        if _canonical(safe) != _canonical(original):
            replacements.append((start, end, _toml_encoded(safe)))
        else:
            safe_raw = _gap_safe(raw, patterns=False)
            if safe_raw != raw:
                replacements.append((start, end, safe_raw))
        value_spans.append((start, end))
        cursor = end
    cursor = 0
    for start, end in value_spans:
        gap = text[cursor:start]
        safe = _gap_safe(gap)
        if safe != gap:
            replacements.append((cursor, start, safe))
        cursor = end
    safe = _gap_safe(text[cursor:])
    if safe != text[cursor:]:
        replacements.append((cursor, len(text), safe))
    for start, end, safe in sorted(replacements, reverse=True):
        text = text[:start] + safe + text[end:]
    if _canonical(tomllib.loads(text)) != _canonical(expected):
        raise _UnsafeCapture("cannot verify sanitized capture structure")
    return text, len(replacements)


def _toml_patch(text: str, keys: tuple[str, ...]) -> tuple[str, int]:
    if not text.startswith(("diff --git ", "@@ ")):
        return text, 0
    contexts: dict[str, tuple[str, ...] | None] = {"+": None, "-": None, " ": None}
    toml_file = False
    lines = []
    count = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            contexts = {"+": None, "-": None, " ": None}
            toml_file = bool(re.search(r'\.toml(?:"|$)', line.rstrip()))
        prefix = line[:1]
        if prefix in contexts and not line.startswith(("+++", "---")):
            fragment = line[1:]
            header = _TOML_HEADER.match(fragment.lstrip())
            if header:
                header_context = _toml_path(header["key"])
                if prefix == " ":
                    contexts = {kind: header_context for kind in contexts}
                else:
                    contexts[prefix] = header_context
            elif _TOML_ASSIGN.match(fragment.lstrip()):
                context = contexts[prefix]
                if toml_file and context is None and prefix in {"+", "-"}:
                    raise _UnsafeCapture("missing capture table context")
                safe = _toml(fragment, (*keys, *(context or ())))
                if safe is not None:
                    fragment, replaced = safe
                    line = prefix + fragment
                    count += replaced
        lines.append(line)
    return "".join(lines), count


def _tree(
    text: str, keys: tuple[str, ...], depth: int, *, manifest: bool = False
) -> tuple[str, int]:
    if len(text) > _LIMIT or len(text.encode("utf-8")) > _LIMIT:
        raise ValueError("capture structure size limit exceeded")
    node = yaml.compose(text, Loader=yaml.SafeLoader)
    if node is None:
        return text, 0
    replacements: dict[tuple[int, int], str] = {}
    scalar_spans: set[tuple[int, int]] = set()
    literals = {
        token.end_mark.index: token.start_mark.index
        for token in yaml.scan(text, Loader=yaml.SafeLoader)
        if isinstance(token, ScalarToken)
    }
    visited = 0

    def visit(
        current: Node,
        context: tuple[str, ...],
        ancestors: frozenset[int],
        path: tuple[str, ...],
    ) -> None:
        nonlocal visited
        visited += 1
        if visited > _NODE_LIMIT or len(ancestors) > _DEPTH_LIMIT:
            raise ValueError("capture structure limit exceeded")
        if id(current) in ancestors:
            raise ValueError("cyclic capture structure")
        ancestors = ancestors | {id(current)}
        if isinstance(current, MappingNode):
            for key, value in current.value:
                raw_key = key.value if isinstance(key, ScalarNode) else ""
                visit(key, (), ancestors, (*path, raw_key))
                child_context = () if manifest and path == ("bindings",) else (*context, raw_key)
                visit(value, child_context, ancestors, (*path, raw_key))
        elif isinstance(current, SequenceNode):
            for value in current.value:
                visit(value, context, ancestors, path)
        elif isinstance(current, ScalarNode):
            original = current.value
            safe = redact_text(str(redact_keyed_values(_pem_safe(original), context)))[0]
            safe, _ = _fragments(safe, depth + 1)
            end = current.end_mark.index
            start = literals.get(end, current.start_mark.index)
            scalar_spans.add((start, end))
            if safe != original:
                replacements[start, end] = _encoded(safe, text[start:end])

    visit(node, keys, frozenset(), ())
    cursor = 0
    for start, end in sorted(scalar_spans):
        if start > cursor:
            original = text[cursor:start]
            safe = _gap_safe(original)
            if safe != original:
                replacements[cursor, start] = safe
        cursor = max(cursor, end)
    original = text[cursor:]
    safe = _gap_safe(original)
    if safe != original:
        replacements[cursor, len(text)] = safe
    for (start, end), safe in sorted(replacements.items(), reverse=True):
        text = text[:start] + safe + text[end:]
    return text, len(replacements)


def _value_end(text: str, start: int) -> int:
    first = text[start]
    if first in "\"'":
        index = start + 1
        while index < len(text):
            if first == '"' and text[index] == "\\":
                index += 2
            elif text[index] == first:
                if first == "'" and text[index : index + 2] == "''":
                    index += 2
                else:
                    return index + 1
            else:
                index += 1
        raise ValueError("unfinished capture string")
    if first in "[{":
        stack = [first]
        index = start + 1
        while index < len(text):
            char = text[index]
            if char in "\"'":
                index = _value_end(text, index)
                continue
            if char in "[{":
                stack.append(char)
            elif char in "]}":
                if not stack or (stack.pop(), char) not in {("[", "]"), ("{", "}")}:
                    raise ValueError("invalid capture structure")
                if not stack:
                    return index + 1
            index += 1
        raise ValueError("unfinished capture structure")
    index = start
    while index < len(text) and not text[index].isspace() and text[index] not in ",;{}[]":
        index += 1
    return index


def _fragments(text: str, depth: int) -> tuple[str, int]:
    if depth > 8:
        raise ValueError("nested capture text limit exceeded")
    replacements: list[tuple[int, int, str]] = []
    cursor = 0
    while match := _search_key(text, cursor):
        key = _decode(match["key"])
        start = match.end()
        if start >= len(text):
            if _secret_key(key):
                raise _UnsafeCapture("missing secret capture value")
            break
        prefix = text[match.start() : start]
        if "\n" in prefix and text[start] not in "[{\"'":
            if _secret_key(key):
                raise _UnsafeCapture("ambiguous secret capture structure")
            cursor = start
            continue
        try:
            end = _value_end(text, start)
            raw = text[start:end]
            if raw.startswith(("{", "[")):
                safe, _ = _tree(raw, (key,), depth + 1)
            else:
                original = _decode(raw)
                safe = str(redact_keyed_values(_pem_safe(original), (key,)))
                safe, _ = _fragments(safe, depth + 1)
                if safe == original:
                    safe = raw
                elif raw.startswith(("'", '"')) or (match["key"].startswith('"') and ":" in prefix):
                    safe = _encoded(safe, raw)
        except _UnsafeCapture:
            raise
        except (ValueError, yaml.YAMLError):
            if _secret_key(key) or _has_unsafe_context(text[start:]):
                raise _UnsafeCapture("cannot sanitize secret capture value") from None
            cursor = start
            continue
        if safe != raw:
            replacements.append((start, end, safe))
        cursor = max(end, start + 1)
    for start, end, safe in reversed(replacements):
        text = text[:start] + safe + text[end:]
    return text, len(replacements)


def redact_contextual_text(
    text: str, *, manifest: bool = False, keys: tuple[str, ...] = ()
) -> tuple[str, int]:
    if _DOCUMENT.match(text.lstrip()):
        try:
            return _tree(text, keys, 0, manifest=manifest)
        except yaml.YAMLError:
            # Patch and output fragments can be incomplete documents. Their
            # supported scalar forms still receive exact contextual handling.
            pass
    toml = _toml(text, keys)
    if toml is not None:
        return toml
    text, patch_count = _toml_patch(text, keys)
    original = text
    text = _pem_safe(text)
    pem_count = int(text != original)
    result, count = _fragments(text, 0)
    contextual = str(redact_keyed_values(result, keys))
    count += contextual != result
    result = contextual
    protected, originals, key_count = shield_contextual_keys(result)
    safe, replaced = redact_text(protected)
    for marker, original in originals.items():
        safe = safe.replace(marker, original)
    return safe, patch_count + pem_count + count + key_count + (replaced if safe != result else 0)


class CaptureLineContext:
    """Carry YAML parent fields across line-buffered output without saving text."""

    def __init__(self) -> None:
        self.parents: list[tuple[int, str]] = []
        self.table: tuple[str, ...] = ()

    def keys(self, line: str) -> tuple[str, ...]:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            return ()
        indent = len(line) - len(stripped)
        sequence = stripped.startswith("- ") or stripped.strip() == "-"
        while self.parents and (
            indent < self.parents[-1][0] or (indent == self.parents[-1][0] and not sequence)
        ):
            self.parents.pop()
        header = _TOML_HEADER.match(stripped)
        if header and not self.parents:
            self.table = _toml_path(header["key"])
            return ()
        inherited = (*self.table, *(key for _, key in self.parents))
        match = _KEY_AT_START.match(stripped.removeprefix("- "))
        if match and stripped.removeprefix("- ")[match.end() :].strip() in {
            "",
            "|",
            "|-",
            "|+",
            ">",
            ">-",
            ">+",
        }:
            self.parents.append((indent, _decode(match["key"])))
        return inherited


def shield_contextual_keys(text: str) -> tuple[str, dict[str, str], int]:
    """Shield key syntax while the existing stream pass handles raw PEM markers."""
    prefix = "__REPROLLM_CAPTURE_KEY_"
    while prefix in text:
        prefix = "_" + prefix
    originals: dict[str, str] = {}
    count = 0

    def shield(match: re.Match[str]) -> str:
        nonlocal count
        if not _secret_key(_decode(match["key"])):
            return match[0]
        marker = f"{prefix}{len(originals)}__"
        # Restoring a key must never restore a pattern-bearing value embedded in it.
        safe, replaced = redact_text(match["key"])
        originals[marker] = safe
        count += replaced if safe != match["key"] else 0
        return marker + match[0][len(match["key"]) :]

    protected = _KEY_SCAN.sub(shield, text)
    return protected, originals, count
