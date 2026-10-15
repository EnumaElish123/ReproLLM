"""Machine-identity removal at the run persistence boundary (§5.1 R-10).

The normative secret patterns remain in core.redaction. This layer additionally
makes captured paths portable and removes the current machine's identity.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from reprollm.core.persistence import redact_keyed_values
from reprollm.run.contextual_text import redact_contextual_text
from reprollm.schemas.run_record import Observation

# An absolute path starts at a segment boundary: not after a word char,
# separator, glob star, or the "<" of a closing token (</s>, </think>).
# Without the star/angle exclusions, "…**/*.json" loses its "/…" suffix and
# "</s>" stop tokens become "<<REDACTED:path>>" in captured snapshots.
# Dot exclusion belongs only to POSIX: .C:\file and .\\server must still redact.
# A lone slash is also an operator/separator. A UNC host starts with a literal
# name, not the punctuation escapes in GSM8K's serialized regular expressions.
_ABSOLUTE_PATH = re.compile(
    r"""(?<![\w:/\\*<])(?:[A-Za-z]:[\\/]"""
    r"""|(?<!\.)/+(?=[^/\\\s"'<>;,\)\]}>])"""
    r"""|\\\\(?=[.$-]*\w[\w.$-]*(?:[\\/]|(?=[\s"'<>;,\)\]}>]|$))|[.?][\\/]))"""
    r"""[^\s"'<>;,\)\]}>]*"""
)
_LOCAL_URI = re.compile(r"""(?i)\bfile:[/\\]{2}[^\s"'<>;,\)\]}>]*""")
_TEMPLATE_SUFFIX = re.compile(r"\{[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\}$")


def _division_spans(text: str) -> list[tuple[int, int]]:
    """Locate only parsed Python operators, including f-string expressions.

    Literal strings and comments remain subject to the full path policy.
    AST columns are UTF-8 byte offsets, unlike tokenize's character offsets.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def position(line: int, column: int) -> int:
        return offsets[line - 1] + len(lines[line - 1].encode("utf-8")[:column].decode("utf-8"))

    spans = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.BinOp, ast.AugAssign)) or not isinstance(
            node.op, (ast.Div, ast.FloorDiv)
        ):
            continue
        left = node.left if isinstance(node, ast.BinOp) else node.target
        right = node.right if isinstance(node, ast.BinOp) else node.value
        if left.end_lineno is None or left.end_col_offset is None:
            continue
        start = position(left.end_lineno, left.end_col_offset)
        end = position(right.lineno, right.col_offset)
        gap = text[start:end]
        gap_lines = gap.splitlines(keepends=True)
        try:
            for token in tokenize.generate_tokens(io.StringIO(gap).readline):
                if token.type == tokenize.OP and token.string in {"/", "//", "/=", "//="}:
                    at = start + sum(map(len, gap_lines[: token.start[0] - 1])) + token.start[1]
                    spans.append((at, at + len(token.string)))
                    break
        except (tokenize.TokenError, IndentationError):
            continue
    return sorted(set(spans))


class RunPrivacy:
    def __init__(self, root: Path, *, hostname: str, username: str) -> None:
        self.root = root.resolve()
        self.identities = [
            (re.compile(r"(?<![\w])" + re.escape(value) + r"(?![\w])"), kind)
            for value, kind in ((hostname, "hostname"), (username, "username"))
            if value
        ]

    def text(
        self,
        value: str,
        *,
        manifest: bool = False,
        keys: tuple[str, ...] = (),
        python_source: bool = False,
    ) -> tuple[str, int]:
        result, count = redact_contextual_text(value, manifest=manifest, keys=keys)
        result, replaced = _LOCAL_URI.subn("<REDACTED:path>", result)
        count += replaced

        redacted_until = 0

        def path(match: re.Match[str]) -> str:
            nonlocal count, redacted_until
            prefix = match.string[: match.start()]
            suffix = _TEMPLATE_SUFFIX.search(prefix)
            if match[0].startswith("/") and suffix and suffix.start() >= redacted_until:
                return match[0]
            if (
                match[0] == "/INST"
                and prefix.endswith("[")
                and match.string[match.end() :].startswith("]")
            ):
                return match[0]
            count += 1
            try:
                relative = Path(match[0]).relative_to(self.root)
                if ".." not in relative.parts:
                    return relative.as_posix()
            except ValueError:
                pass
            redacted_until = match.end()
            return "<REDACTED:path>"

        # Only captured .py files opt in. Arbitrary argv/config strings must
        # not gain a path-redaction exemption by resembling Python arithmetic.
        spans = _division_spans(result) if python_source else []
        pieces: list[str] = []
        cursor = 0
        for start, end in [*spans, (len(result), len(result))]:
            redacted_until = 0
            safe = _ABSOLUTE_PATH.sub(path, result[cursor:start])
            pieces.extend((safe, result[start:end]))
            cursor = end
        result = "".join(pieces)
        for pattern, kind in self.identities:
            result, replaced = pattern.subn(f"<REDACTED:{kind}>", result)
            count += replaced
        return result, count

    def value(self, value: Any, keys: tuple[str, ...] = ()) -> Any:
        if isinstance(value, Observation):
            context = (*keys, value.source.key)
            if value.source.type == "config":
                context = (*context, *value.source.key.split("."))
            return {
                "value": self.value(value.value, context),
                "source": self.value(value.source),
            }
        if isinstance(value, BaseModel):
            return {key: self.value(item) for key, item in value}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, str):
            return self.text(value, keys=keys)[0]
        if isinstance(value, list):
            return [self.value(item, keys) for item in value]
        if isinstance(value, dict):
            return {
                self.text(str(key))[0]: self.value(item, (*keys, str(key)))
                for key, item in value.items()
            }
        return redact_keyed_values(value, keys)
