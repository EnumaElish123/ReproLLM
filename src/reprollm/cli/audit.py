"""``reprollm audit`` — run the deterministic rules engine (spec §1)."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from reprollm.core.paths import display_target, find_root
from reprollm.reporters.json_ import audit_report_to_json
from reprollm.reporters.text import render_audit_text
from reprollm.schemas.finding import SEVERITY_RANK, AuditReport, FindingStatus, Severity

app = typer.Typer(help="Run the reproducibility audit.", no_args_is_help=True)


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


class FailOn(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    NEVER = "never"


class LevelChoice(str, Enum):
    AUTO = "auto"
    L0 = "0"
    L1 = "1"
    L2 = "2"


_FAIL_ON_RANK: dict[FailOn, int | None] = {
    FailOn.CRITICAL: SEVERITY_RANK[Severity.CRITICAL],
    FailOn.WARNING: SEVERITY_RANK[Severity.WARNING],
    FailOn.NEVER: None,
}


def _exit_code(report: AuditReport, fail_on: FailOn) -> int:
    threshold = _FAIL_ON_RANK[fail_on]
    if threshold is None:
        return 0
    return 1 if _max_fail_rank(report) >= threshold else 0


def _max_fail_rank(report: AuditReport) -> int:
    ranks = [SEVERITY_RANK[f.severity] for f in report.findings if f.status == FindingStatus.FAIL]
    return max(ranks, default=0)


@app.command()
def audit(
    path: Annotated[Path, typer.Argument(help="Repository to audit (default: .)")] = Path("."),
    format: Annotated[OutputFormat, typer.Option("--format", help="Output format.")] = (
        OutputFormat.TEXT
    ),
    output: Annotated[
        Path | None, typer.Option("--output", help="Write the report to a file.")
    ] = None,
    fail_on: Annotated[
        FailOn, typer.Option("--fail-on", help="Exit 1 when findings reach this severity.")
    ] = FailOn.CRITICAL,
    level: Annotated[
        LevelChoice, typer.Option("--level", help="Force a lower audit level.")
    ] = LevelChoice.AUTO,
    profiles: Annotated[
        str | None,
        typer.Option("--profiles", help="Comma-separated profile names overriding the manifest."),
    ] = None,
    show_passed: Annotated[bool, typer.Option("--show-passed")] = False,
    show_skipped: Annotated[bool, typer.Option("--show-skipped")] = False,
    no_color: Annotated[bool, typer.Option("--no-color", help="Plain ASCII output.")] = False,
) -> None:
    """Audit a repository and print findings (exit 1 at/above --fail-on)."""
    profile_list: list[str] | None = None
    if profiles is not None:
        profile_list = [name.strip() for name in profiles.split(",") if name.strip()]
        if not profile_list:
            raise UserError("--profiles requires at least one profile name")

    root = find_root(path)
    forced_level = None if level == LevelChoice.AUTO else int(level.value)
    report = run_audit(
        root,
        level=forced_level,
        profile_names=profile_list,
        target=display_target(path, root),
    )

    if format == OutputFormat.JSON:
        if output is None:
            typer.echo(audit_report_to_json(report))
        else:
            try:
                output.write_text(audit_report_to_json(report), encoding="utf-8")
            except OSError as exc:
                raise UserError(
                    f"cannot write the audit report to {output}: "
                    f"{exc.strerror or type(exc).__name__}"
                ) from exc
            typer.echo(
                f"Wrote audit report to {output} "
                f"({report.summary.critical} critical, {report.summary.warning} warning)"
            )
    else:
        if output is not None:
            raise UserError("--output requires --format json")
        use_ascii = no_color or not sys.stdout.isatty() or os.environ.get("NO_COLOR") is not None
        typer.echo(
            render_audit_text(
                report,
                show_passed=show_passed,
                show_skipped=show_skipped,
                ascii_symbols=use_ascii,
            ),
            nl=False,
        )

    raise typer.Exit(_exit_code(report, fail_on))
