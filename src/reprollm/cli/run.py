"""CLI wiring for deterministic runtime capture."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from reprollm.core.config import load_config
from reprollm.core.errors import UserError
from reprollm.core.paths import MANIFEST, RUNS_DIR, find_root
from reprollm.run.wrapper import create_run_dir, execute


class EnvCapture(str, Enum):
    ALLOWLIST = "allowlist"
    ALL = "all"


def run(
    command: Annotated[
        list[str] | None, typer.Argument(help="Command and arguments after --.")
    ] = None,
    name: Annotated[str | None, typer.Option("--name", help="Optional run label.")] = None,
    capture_output: Annotated[
        bool | None, typer.Option("--capture-output", help="Tee redacted stdout/stderr logs.")
    ] = None,
    env_capture: Annotated[
        EnvCapture | None, typer.Option("--env-capture", help="Environment capture policy.")
    ] = None,
    no_snapshot: Annotated[
        bool, typer.Option("--no-snapshot", help="Hash input files without copying their contents.")
    ] = False,
    cwd: Annotated[
        Path | None, typer.Option("--cwd", help="Working directory for the child command.")
    ] = None,
) -> None:
    """Execute a command and record its runtime state."""
    if not command:
        raise UserError("run requires a command after --")
    working = (cwd or Path.cwd()).resolve()
    if not working.is_dir():
        raise UserError("--cwd must name an existing directory")
    root = find_root(working)
    config = load_config(root).run
    if not (root / MANIFEST).is_file():
        typer.echo("warning: no reprollm.yaml; bindings and declared files unavailable", err=True)
    mode = config.env_capture
    if env_capture is not None:
        mode = "all" if env_capture == EnvCapture.ALL else "allowlist"
    record = execute(
        command,
        root=root,
        cwd=working,
        run_dir=create_run_dir(root),
        name=name,
        capture_output=config.capture_output if capture_output is None else capture_output,
        env_capture=mode,
        extra_allowlist=config.extra_env_allowlist,
        snapshot=not no_snapshot,
        max_bytes=config.snapshot_max_bytes,
    )
    for warning in record.warnings:
        if not warning.startswith("no reprollm.yaml;"):
            typer.echo(f"warning: {warning}", err=True)
    count = sum(len(items) for items in record.bindings_observed.values())
    warnings = f"{len(record.warnings)} warning" + ("" if len(record.warnings) == 1 else "s")
    typer.echo(
        f"Recorded run {record.run_id} (exit {record.exit_code}, "
        f"{record.duration_seconds or 0:.1f} s, {len(record.files)} files hashed, "
        f"{count} bindings observed, {warnings}) → {RUNS_DIR}/{record.run_id}"
    )
    raise typer.Exit(record.exit_code or 0)
