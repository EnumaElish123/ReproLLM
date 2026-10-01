"""Shared static framework signals; repository commands are never executed."""

from __future__ import annotations

import re
import shlex
from collections.abc import Iterator
from pathlib import PurePosixPath

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode

from reprollm.core.pyscan import PyScanResult, scan_python
from reprollm.core.scanner import RepoScanner
from reprollm.schemas.finding import Evidence

_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*=")
_PYTHON = re.compile(r"python(?:\d+(?:\.\d+)*)?")


def scalar_string(node: Node | None) -> str | None:
    if (
        isinstance(node, ScalarNode)
        and node.tag == "tag:yaml.org,2002:str"
        and isinstance(node.value, str)
    ):
        return node.value
    return None


def task_mapping(scanner: RepoScanner, path: str) -> dict[str, Node] | None:
    text = scanner.read_text(path)
    if text is None:
        return None
    try:
        # Compose reads nodes without constructing values or importing !function
        # references. A custom tag elsewhere cannot hide a static task name.
        node = yaml.compose(text, Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        return None
    if not isinstance(node, MappingNode):
        return None
    return {name: value for key, value in node.value if (name := scalar_string(key)) is not None}


def import_evidence(
    scanner: RepoScanner, module: str, pyscan: PyScanResult | None = None
) -> list[Evidence]:
    scanned = pyscan if pyscan is not None else scan_python(scanner)
    hits = [info for info in scanned.imports if info.module.split(".", 1)[0] == module]
    if not hits:
        return []
    hit = hits[0]
    return [Evidence(kind="detection", path=hit.path, line=hit.line, note=f"import {module}")]


def _commands(text: str) -> list[list[str]]:
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    commands: list[list[str]] = [[]]
    for token in tokens:
        if token and set(token) <= set(";&|()"):
            commands.append([])
        else:
            commands[-1].append(token)
    return commands


def _entry(tokens: list[str]) -> list[str]:
    while tokens and (_ASSIGNMENT.match(tokens[0]) or tokens[0] == "env"):
        tokens = tokens[1:]
    if tokens[:2] in (["uv", "run"], ["poetry", "run"]):
        tokens = tokens[2:]
    return tokens


def _logical_lines(text: str) -> Iterator[tuple[int, str]]:
    pending = ""
    start = 1
    for line_number, line in enumerate(text.splitlines(), 1):
        if not pending:
            start = line_number
        if line.rstrip().endswith("\\"):
            pending += line.rstrip()[:-1] + " "
            continue
        yield start, pending + line
        pending = ""
    if pending:
        yield start, pending


def cli_evidence(
    scanner: RepoScanner,
    entries: tuple[tuple[str, ...], ...],
    *,
    module: str | None = None,
) -> list[Evidence]:
    evidence: list[Evidence] = []
    for path in scanner.files():
        if not (path.endswith(".sh") or PurePosixPath(path).name == "Makefile"):
            continue
        text = scanner.read_text(path)
        if text is None:
            continue
        for line_number, line in _logical_lines(text):
            for command in _commands(line):
                command = _entry(command)
                if not command:
                    continue
                name = PurePosixPath(command[0].lstrip("@-")).name
                direct = next(
                    (entry for entry in entries if (name, *command[1 : len(entry)]) == entry),
                    None,
                )
                via_module = bool(
                    module and _PYTHON.fullmatch(name) and command[1:3] == ["-m", module]
                )
                if direct is not None or via_module:
                    label = " ".join(direct) if direct is not None else module
                    evidence.append(
                        Evidence(
                            kind="detection", path=path, line=line_number, note=f"CLI: {label}"
                        )
                    )
    return evidence
