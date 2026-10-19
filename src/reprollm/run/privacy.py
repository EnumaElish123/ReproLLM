"""Machine-identity removal at the run persistence boundary (§5.1 R-10).

The normative secret patterns remain in core.redaction. This layer additionally
makes captured paths portable and removes the current machine's identity.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from reprollm.core.persistence import redact_keyed_values
from reprollm.run.contextual_text import redact_contextual_text
from reprollm.run.json_text import redact_json_strings
from reprollm.run.python_text import redact_python_source
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
        return self._text(value, manifest=manifest, keys=keys, python_source=python_source)

    def _text(
        self,
        value: str,
        *,
        manifest: bool = False,
        keys: tuple[str, ...] = (),
        python_source: bool = False,
        depth: int = 0,
    ) -> tuple[str, int]:
        if depth > 8:
            raise ValueError("nested capture text limit exceeded")
        if python_source and not keys:
            source = redact_python_source(
                value,
                lambda scalar, context: self._text(scalar, keys=context, depth=depth + 1),
            )
            if source is not None:
                return source
        result, count = redact_contextual_text(value, manifest=manifest, keys=keys)
        structured = redact_json_strings(result, lambda scalar: self._text(scalar, depth=depth + 1))
        if structured is not None and any(char in result for char in '"[{'):
            safe, replaced = structured
            return safe, count + replaced
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

        result = _ABSOLUTE_PATH.sub(path, result)
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
