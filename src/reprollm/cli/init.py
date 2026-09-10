"""``reprollm init`` — command wiring only (M2F-T09).

Argument parsing, Typer prompting, and output; planning/rendering/writes
live in :mod:`reprollm.core.manifest_scaffold`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from reprollm.core.errors import UserError
from reprollm.core.manifest_scaffold import (
    InitPlan,
    parse_scalar,
    plan_init,
    render_manifest,
    write_scaffold,
)

_COMMENTED_OR_LIST = (
    "evaluation.definitions.refusal",
    "evaluation.definitions.asr",
    "privacy.mechanism.name",
    "evaluation.metrics",
)


def _prompt_required(plan: InitPlan, values: dict[str, Any]) -> None:
    """--interactive: prompt for every scalar required field (empty keeps null)."""
    for field_path in plan.required_fields:
        if field_path == "project.name":
            continue  # already set from the directory name
        if field_path in _COMMENTED_OR_LIST:
            typer.echo(f"  {field_path}: edit manually in reprollm.yaml")
            continue
        current = values.get(field_path)
        answer = typer.prompt(
            f"  {field_path}",
            default=str(current) if current is not None else "",
            show_default=current is not None,
        )
        if str(answer).strip():
            values[field_path] = parse_scalar(field_path, str(answer))
        else:
            values[field_path] = current


def init(
    path: Annotated[Path, typer.Argument(help="Directory to initialize (default: .)")] = Path("."),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing manifest.")] = False,
    interactive: Annotated[
        bool, typer.Option("--interactive", help="Prompt for required fields.")
    ] = False,
    profiles: Annotated[
        str | None,
        typer.Option("--profiles", help="Comma-separated profile names (default: detected)."),
    ] = None,
) -> None:
    """Create reprollm.yaml and .reprollm/ from detected experiment signals."""
    root = path.resolve()
    if not root.is_dir():
        raise UserError(f"{path} is not an existing directory")

    override = None
    if profiles is not None:
        override = [name.strip() for name in profiles.split(",") if name.strip()]
    plan = plan_init(root, profiles_override=override)

    values: dict[str, Any] = {}
    if interactive:
        _prompt_required(plan, values)

    manifest_text = render_manifest(plan, values)
    write_scaffold(root, manifest_text, force=force)

    if plan.profiles:
        typer.echo(
            f"Created {root / 'reprollm.yaml'} (profiles: {', '.join(plan.profiles)}; "
            f"{len(plan.required_fields)} required fields to fill)"
        )
    else:
        typer.echo(
            f"Created {root / 'reprollm.yaml'} (no profiles detected; "
            "pass --profiles or edit experiment.profiles)"
        )
    typer.echo("Next: fill the TODO fields, then run `reprollm audit .`")
