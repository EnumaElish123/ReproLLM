"""Read-only listing and inspection of saved runs."""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from reprollm.core.paths import find_root
from reprollm.run.reader import list_runs, read_run

app = typer.Typer(help="Inspect recorded runs.", no_args_is_help=True)


@app.command(name="list")
def list_command(
    as_json: Annotated[bool, typer.Option("--json", help="Emit run summaries as JSON.")] = False,
) -> None:
    records, warnings = list_runs(find_root(Path.cwd()))
    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)
    rows = [
        {
            "run_id": record.run_id,
            "started_at": record.model_dump(mode="json")["started_at"],
            "status": record.status.value,
            "exit_code": record.exit_code,
            "duration_seconds": record.duration_seconds,
            "name": record.name,
            "dirty": record.code.dirty,
        }
        for record in records
    ]
    if as_json:
        typer.echo(json.dumps(rows, indent=2, sort_keys=True, ensure_ascii=False))
        return
    table = Table("Run ID", "Started", "Status", "Exit", "Duration", "Name", "Dirty")
    for record in records:
        cells = [
            record.run_id,
            str(record.started_at or "—"),
            record.status.value,
            str(record.exit_code) if record.exit_code is not None else "—",
            f"{record.duration_seconds:.1f} s" if record.duration_seconds is not None else "—",
            record.name or "—",
            "yes" if record.code.dirty else "no",
        ]
        table.add_row(*(Text(cell) for cell in cells))
    Console().print(table)


@app.command(name="show")
def show(
    run_id: Annotated[str, typer.Argument(help="Run ID or unique prefix.")],
    as_json: Annotated[
        bool, typer.Option("--json", help="Print run.json exactly as saved.")
    ] = False,
) -> None:
    record, raw = read_run(find_root(Path.cwd()), run_id)
    if as_json:
        typer.echo(raw, nl=False)
        return
    typer.echo(f"Run {record.run_id}" + (f" — {record.name}" if record.name else ""))
    typer.echo(
        f"Status: {record.status.value}; exit {record.exit_code}; "
        f"{record.duration_seconds or 0:.1f} s"
    )
    typer.echo(f"Command: {shlex.join(record.command.argv)}")
    typer.echo(f"Working directory: {record.command.cwd}")
    typer.echo(f"Code: {record.code.commit or 'unavailable'}; dirty={record.code.dirty}")
    if record.environment is not None:
        typer.echo(
            f"Environment: {record.environment.platform}; Python {record.environment.python}"
        )
        for package, version in sorted(record.environment.packages.items()):
            typer.echo(f"  {package}: {version}")
    if record.hardware is not None:
        typer.echo(f"GPU source: {record.hardware.source}")
        for gpu in record.hardware.gpus:
            typer.echo(f"  {gpu.index}: {gpu.name}, {gpu.memory_mib} MiB")
    for file in record.files:
        typer.echo(f"File: {file.path} {file.sha256}")
    for field, observations in sorted(record.bindings_observed.items()):
        for observation in observations:
            source = observation.source
            location = f"{source.path}:" if source.path else ""
            value = json.dumps(observation.value, sort_keys=True, ensure_ascii=False)
            typer.echo(f"Binding: {field} · {source.type}({location}{source.key}) = {value}")
    for warning in record.warnings:
        typer.echo(f"Warning: {warning}")
