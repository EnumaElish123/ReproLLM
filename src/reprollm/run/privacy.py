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

from reprollm.core.redaction import redact_text

_ABSOLUTE_PATH = re.compile(r"""(?<![\w:/\\])(?:[A-Za-z]:[\\/]|/|\\\\)[^\s"'<>;,\)\]}]*""")


class RunPrivacy:
    def __init__(self, root: Path, *, hostname: str, username: str) -> None:
        self.root = root.resolve()
        self.identities = [
            (re.compile(r"(?<![\w])" + re.escape(value) + r"(?![\w])"), kind)
            for value, kind in ((hostname, "hostname"), (username, "username"))
            if value
        ]

    def text(self, value: str) -> tuple[str, int]:
        result, count = redact_text(value)

        def path(match: re.Match[str]) -> str:
            try:
                relative = Path(match[0]).relative_to(self.root)
                if ".." not in relative.parts:
                    return relative.as_posix()
            except ValueError:
                pass
            return "<REDACTED:path>"

        result, replaced = _ABSOLUTE_PATH.subn(path, result)
        count += replaced
        for pattern, kind in self.identities:
            result, replaced = pattern.subn(f"<REDACTED:{kind}>", result)
            count += replaced
        return result, count

    def value(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return {key: self.value(item) for key, item in value}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, str):
            return self.text(value)[0]
        if isinstance(value, list):
            return [self.value(item) for item in value]
        if isinstance(value, dict):
            return {self.text(str(key))[0]: self.value(item) for key, item in value.items()}
        return value
