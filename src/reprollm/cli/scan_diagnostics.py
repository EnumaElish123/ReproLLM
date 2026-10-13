"""CLI-only presentation of Python file-budget coverage and existing diagnostics."""

from __future__ import annotations

import re
from collections.abc import Iterable

import typer

_COVERAGE = re.compile(
    r"Python analysis incomplete: parsed (?P<parsed>[0-9]+) of "
    r"(?P<candidate>[0-9]+) candidate files; selected (?P<selected>[0-9]+) "
    r"\(limit (?P<limit>[0-9]+)\), omitted (?P<omitted>[0-9]+)\. "
    r"(?:[0-9]+ selected files were not parsed\. )?"
    r"Missing signals may be in unanalysed files\."
)
_LEGACY_LIMIT = re.compile(
    r"python file scan truncated to (?P<limit>[0-9]+) of (?P<candidate>[0-9]+) files"
)


def show_scan_diagnostics(
    entries: Iterable[str], *, verbose: bool = False, include_existing: bool = False
) -> None:
    """Show trusted fixed-form coverage; preserve audit's other visibility rules."""
    unique = tuple(dict.fromkeys(entries))
    # File-origin warnings can start with any text. Whole-message matching keeps
    # an untrusted path from impersonating the fixed, default coverage summary.
    coverage = {entry: match for entry in unique if (match := _COVERAGE.fullmatch(entry))}
    covered_budgets = {(m.group("limit"), m.group("candidate")) for m in coverage.values()}
    for entry in unique:
        if entry in coverage:
            typer.echo(f"scan: {entry}", err=True)
        elif include_existing:
            if entry.startswith("run: "):
                typer.echo(f"warning: {entry}", err=True)
            elif verbose:
                old = _LEGACY_LIMIT.fullmatch(entry)
                if (
                    old is not None
                    and (old.group("limit"), old.group("candidate")) in covered_budgets
                ):
                    continue
                typer.echo(f"scan: {entry}", err=True)
