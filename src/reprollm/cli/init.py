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
    select_tasks,
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
    task: Annotated[
        list[str] | None, typer.Option("--task", help="Select an exact task candidate; repeatable.")
    ] = None,
    list_tasks: Annotated[
        bool,
        typer.Option("--list-tasks", help="List all safe task candidates without writing files."),
    ] = False,
) -> None:
    """Create reprollm.yaml and .reprollm/ from detected experiment signals."""
    root = path.resolve()
    if not root.is_dir():
        raise UserError(f"{path} is not an existing directory")
    if list_tasks and (interactive or task is not None or force or profiles is not None):
        raise UserError(
            "--list-tasks cannot be combined with --interactive, --task, --force or --profiles"
        )

    override = None
    if profiles is not None:
        override = [name.strip() for name in profiles.split(",") if name.strip()]
    plan = plan_init(root, profiles_override=override)
    if list_tasks:
        for name in plan.task_names:
            typer.echo(name)
        return

    values: dict[str, Any] = {}
    if interactive:
        choices = (
            ", ".join(
                f"{entry.profile} ({entry.confidence})"
                for entry in plan.detection.profiles
                if entry.shipped
            )
            or "none"
        )
        typer.echo(f"Detected profile candidates: {choices}")
        selected_profiles = str(
            typer.prompt(
                "Profiles for this experiment (comma-separated)", default=",".join(plan.profiles)
            )
        )
        override = [name.strip() for name in selected_profiles.split(",") if name.strip()]
        if override:
            plan = plan_init(root, profiles_override=override)
        elif plan.profiles:
            raise UserError("select at least one detected profile or use --profiles explicitly")
    selected = select_tasks(plan, task or [])
    if interactive:
        if plan.task_names and "evaluation.metrics" in plan.required_fields:
            typer.echo(
                f"Task candidates: {len(plan.task_names)}. "
                "List with: reprollm init PATH --list-tasks"
            )
            while True:
                name = str(
                    typer.prompt(
                        "Task name (empty finishes selection)", default="", show_default=False
                    )
                )
                if not name:
                    break
                selected = select_tasks(plan, [*selected, name])
        _prompt_required(plan, values)

    manifest_text = render_manifest(plan, values, selected_tasks=selected)
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
    source = "selected" if override is not None else "detected"
    typer.echo(f"Applied {source} profiles: {', '.join(plan.profiles) or 'none'}.")
    typer.echo("Review experiment.profiles; use --profiles to select this experiment's profiles.")
    typer.echo(
        f"Task candidates: {len(plan.task_names)}; selected: {len(selected)}. "
        "List with: reprollm init PATH --list-tasks"
    )
    if "evaluation.metrics" in plan.required_fields and not selected:
        typer.echo(
            "No task is declared in evaluation.metrics. Select with --task NAME, "
            "or edit metrics manually."
        )
    typer.echo("Next: fill the TODO fields, then run `reprollm audit .`")
