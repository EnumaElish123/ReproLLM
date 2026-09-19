"""Thin semantic diff CLI (§1, §18)."""

from __future__ import annotations

import getpass
import json
import socket
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import typer

from reprollm.core.errors import UserError
from reprollm.core.paths import find_root
from reprollm.diff.differ import diff_states
from reprollm.diff.inputs import load_input
from reprollm.diff.severity import SEVERITIES, SeverityResolver
from reprollm.profiles.loader import resolve
from reprollm.reporters.diff_privacy import sanitize_report
from reprollm.reporters.diff_text import render_diff_text
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.diff_report import DiffReport
from reprollm.schemas.profile import DriftSeverity


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


def _report(a: str, b: str, root: Path) -> DiffReport:
    left, right = load_input(a, root), load_input(b, root)
    names = list(dict.fromkeys([*left.state.profiles, *right.state.profiles]))
    try:
        profiles = resolve(names, root)
    except UserError:
        raise UserError(
            "invalid diff profiles; inspect experiment.profiles and .reprollm/profiles"
        ) from None
    report = diff_states(
        left.state, right.state, SeverityResolver(profile_overrides=profiles.drift_overrides)
    )
    report.a, report.b = left.source, right.source
    return report


def diff(
    a: Annotated[str, typer.Argument(help="Run ID/prefix, run.json, run directory, or lock file.")],
    b: Annotated[str, typer.Argument(help="Second run or lock input.")],
    format: Annotated[OutputFormat, typer.Option("--format")] = OutputFormat.TEXT,
    min_severity: Annotated[
        Literal["LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH"] | None,
        typer.Option("--min-severity", help="Filter displayed changes; preserve the full summary."),
    ] = None,
    fail_on: Annotated[
        DriftSeverity | None,
        typer.Option("--fail-on", help="Exit 1 for drift at or above this level."),
    ] = None,
    no_color: Annotated[bool, typer.Option("--no-color", help="Disable colored output.")] = False,
) -> None:
    """Explain semantic differences between two captured experiments."""
    del no_color  # This renderer emits plain text on every output surface.
    try:
        root = find_root(Path.cwd())
        report = _report(a, b, root)
    except UserError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from None
    failed = fail_on is not None and any(
        SEVERITIES.index(change.severity) >= SEVERITIES.index(fail_on) for change in report.changes
    )
    if min_severity is not None:
        report.changes = [
            change
            for change in report.changes
            if SEVERITIES.index(change.severity) >= SEVERITIES.index(min_severity)
        ]
        report.filtered_below = min_severity
    # Compare raw values first: two distinct secrets may redact to the same marker.
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())
    report = sanitize_report(report, privacy)
    if format == OutputFormat.JSON:
        typer.echo(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False)
        )
    else:
        typer.echo(render_diff_text(report), nl=False)
    raise typer.Exit(1 if failed else 0)
