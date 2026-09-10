"""``reprollm doctor`` — output rendering and exit code only (M2F-T09)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from reprollm import __version__
from reprollm.core.diagnostics import exit_code, run_checks

_SYMBOLS = {"ok": "✔", "warn": "▲", "missing": "✖"}
_SYMBOLS_ASCII = {"ok": "+", "warn": "!", "missing": "X"}


def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    check_network: Annotated[
        bool, typer.Option("--check-network", help="Probe the Hugging Face Hub (network).")
    ] = False,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
) -> None:
    """Diagnose the local environment for ReproLLM."""
    checks = run_checks(Path.cwd(), check_network=check_network)
    code = exit_code(checks)

    if json_output:
        typer.echo(
            json.dumps(
                {"reprollm_version": __version__, "checks": checks},
                indent=2,
            )
        )
        raise typer.Exit(code)

    symbols = _SYMBOLS_ASCII if no_color else _SYMBOLS
    width = max(len(check["name"]) for check in checks)
    typer.echo(f"reprollm {__version__} doctor")
    for check in checks:
        typer.echo(f"  {symbols[check['status']]} {check['name']:<{width}}  {check['detail']}")
    if code == 0:
        typer.echo("Environment OK.")
    else:
        typer.echo("Environment has missing required tools (see above).")
    raise typer.Exit(code)
