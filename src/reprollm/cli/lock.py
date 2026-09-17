"""``reprollm lock`` command wiring (spec §§1 and 4)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import httpx
import typer

from reprollm.core.errors import UserError
from reprollm.core.paths import find_root, repo_paths
from reprollm.core.yaml_io import load_manifest
from reprollm.lock.writer import build_lock, check_lock, summarize_lock, write_lock


def lock(
    path: Annotated[Path, typer.Argument(help="Repository to lock (default: .)")] = Path("."),
    offline: Annotated[
        bool, typer.Option("--offline", help="Resolve without making network requests.")
    ] = False,
    check: Annotated[
        bool, typer.Option("--check", help="Check whether the current lock is fresh.")
    ] = False,
    verify_api: Annotated[
        bool,
        typer.Option("--verify-api", help="Verify API model existence when credentials exist."),
    ] = False,
    hash_large_files: Annotated[
        bool,
        typer.Option("--hash-large-files", help="Hash local model weights over 100 MiB."),
    ] = False,
) -> None:
    """Resolve declared experiment state into reprollm.lock."""
    root = find_root(path)
    paths = repo_paths(root)
    if not paths.manifest.is_file():
        raise UserError(f"{paths.manifest} is missing; run `reprollm init` first")
    manifest = load_manifest(paths.manifest)
    if check:
        reasons = check_lock(root)
        if reasons:
            typer.echo("Lock check failed:")
            for reason in reasons:
                typer.echo(f"  - {reason}")
            raise typer.Exit(1)
        typer.echo("reprollm.lock is up to date")
        return

    with httpx.Client() as http:
        document = build_lock(
            root,
            manifest,
            http=http,
            offline=offline,
            verify_api=verify_api,
            hash_large_files=hash_large_files,
        )
    write_lock(paths.lock, document)
    typer.echo("Wrote reprollm.lock")
    typer.echo(summarize_lock(document).render())
