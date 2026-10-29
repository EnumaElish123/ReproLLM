"""Parse a saved argv string without silently applying shell semantics."""

from __future__ import annotations

import re
import shlex
import unicodedata

from reprollm.core.errors import UserError

_SYNTAX_HINT = (
    "execution.command must be one executable and its arguments with POSIX quoting; "
    "put shell operations in a script or pass an explicit command after --"
)
_SHELL_CHARACTERS = "|&;<>()$`*?[]#~{}"
_ESCAPABLE = " \\\"'" + _SHELL_CHARACTERS
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def parse_saved_command(command: str) -> list[str]:
    """Preserve quoted literals while rejecting unsupported implicit shell behavior."""
    if any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for char in command):
        raise UserError(_SYNTAX_HINT)
    quote: str | None = None
    index = 0
    while index < len(command):
        char = command[index]
        if quote == "'":
            if char == "'":
                quote = None
        elif quote == '"':
            if char == '"':
                quote = None
            elif char in "$`":
                raise UserError(_SYNTAX_HINT)
            elif char == "\\" and index + 1 < len(command) and command[index + 1] in '\\"':
                index += 1
        elif char in "'\"":
            quote = char
        elif char == "\\":
            if index + 1 >= len(command) or command[index + 1] not in _ESCAPABLE:
                raise UserError(
                    "execution.command contains an unsupported unquoted backslash; "
                    "use forward slashes or single-quote paths"
                )
            index += 1
        elif char in _SHELL_CHARACTERS:
            raise UserError(_SYNTAX_HINT)
        index += 1
    try:
        argv = shlex.split(command, comments=False, posix=True)
    except ValueError:
        raise UserError(_SYNTAX_HINT) from None
    if not argv or not argv[0].strip():
        raise UserError(
            "execution.command is empty; set it in reprollm.yaml or pass a command after --"
        )
    if _ASSIGNMENT.match(argv[0]):
        raise UserError(_SYNTAX_HINT)
    return argv
