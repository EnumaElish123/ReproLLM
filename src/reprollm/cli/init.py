"""``reprollm init`` — command wiring only (M2F-T09).

Argument parsing, Typer prompting, and output; planning/rendering/writes
live in :mod:`reprollm.core.manifest_scaffold`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from reprollm.cli.scan_diagnostics import show_scan_diagnostics
from reprollm.core.errors import UserError
from reprollm.core.init_guidance import (
    MANUAL_FIELDS,
    InvalidAnswer,
    answer_privacy,
    check_interactive_plan,
    field_guidance,
    field_label,
    missing_required_fields,
    validate_answer,
)
from reprollm.core.manifest_scaffold import (
    InitPlan,
    check_scaffold_paths,
    plan_init,
    render_manifest,
    select_tasks,
    validate_init_command,
    write_scaffold,
)


def _prompt_required(
    plan: InitPlan, values: dict[str, Any], root: Path, selected: list[str], command: str | None
) -> None:
    """Retry one invalid answer while keeping all accepted fields in memory."""
    privacy = answer_privacy(root)
    check_interactive_plan(plan, values, selected, command, privacy)
    typer.echo(
        "Use the values from your experiment. Press Enter to keep a detected/current "
        "value or leave it unknown; do not guess."
    )
    for field_path in plan.required_fields:
        if field_path == "project.name":
            continue
        if field_path == "execution.command" and field_path in values:
            continue
        label = field_label(field_path, privacy)
        if field_path == "evaluation.metrics" and selected:
            typer.echo(
                "  evaluation.metrics: task names selected; verify metric names and implementations"
            )
            continue
        typer.echo(f"  {label}: {field_guidance(field_path)}")
        if field_path in MANUAL_FIELDS:
            typer.echo(f"  {label}: edit manually in reprollm.yaml")
            continue
        current = values.get(field_path)
        if current is None and field_path == "models.primary.id" and plan.primary_detection:
            current = plan.primary_detection[0]
        while True:
            try:
                answer = typer.prompt(
                    f"  {label}",
                    default=str(current) if current is not None else "",
                    show_default=current is not None,
                )
            except typer.Abort:
                raise UserError(
                    f"Input cancelled for {label}; rerun init --interactive "
                    "or edit reprollm.yaml manually"
                ) from None
            if not str(answer).strip() or answer == current:
                break
            try:
                value = validate_answer(
                    plan,
                    values,
                    field_path,
                    str(answer),
                    selected_tasks=selected,
                    saved_command=command,
                    privacy=privacy,
                )
            except InvalidAnswer as exc:
                typer.echo(str(exc), err=True)
                continue
            values[field_path] = value
            break


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
    command: Annotated[
        str | None,
        typer.Option(
            "--command", help="Save an experiment command in execution.command; do not run it."
        ),
    ] = None,
    task: Annotated[
        list[str] | None, typer.Option("--task", help="Select an exact task candidate; repeatable.")
    ] = None,
    list_tasks: Annotated[
        bool,
        typer.Option("--list-tasks", help="List all safe task candidates without writing files."),
    ] = False,
) -> None:
    """Create reprollm.yaml and .reprollm/ from detected experiment signals.

    Reports Python file limits on stderr.
    """
    root = path.resolve()
    if not root.is_dir():
        raise UserError(f"{path} is not an existing directory")
    if list_tasks and (
        interactive or task is not None or force or profiles is not None or command is not None
    ):
        raise UserError(
            "--list-tasks cannot be combined with --interactive, --task, --force, --profiles "
            "or --command"
        )
    if not list_tasks:
        check_scaffold_paths(root, force=force)
    values: dict[str, Any] = {}
    if command is not None:
        values["execution.command"] = validate_init_command(root, command)

    override = None
    if profiles is not None:
        override = [name.strip() for name in profiles.split(",") if name.strip()]
    plan = plan_init(root, profiles_override=override)
    if list_tasks:
        show_scan_diagnostics(plan.diagnostics)
        for name in plan.task_names:
            typer.echo(name)
        return

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
        _prompt_required(plan, values, root, selected, command)

    manifest_text = render_manifest(plan, values, selected_tasks=selected, saved_command=command)
    remaining = missing_required_fields(plan, manifest_text)
    privacy = answer_privacy(root)
    show_scan_diagnostics(plan.diagnostics)
    write_scaffold(root, manifest_text, force=force)

    display_path = "reprollm.yaml" if plan.project_name_defaulted else str(root / "reprollm.yaml")
    if plan.profiles:
        typer.echo(f"Created {display_path} (profiles: {', '.join(plan.profiles)})")
    else:
        typer.echo(
            f"Created {display_path} (no profiles detected; "
            "pass --profiles or edit experiment.profiles)"
        )
    if plan.project_name_defaulted:
        typer.echo("Set project.name in reprollm.yaml; init used the safe default 'experiment'.")
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
    typer.echo(f"{len(remaining)} required fields still need values in reprollm.yaml.")
    if remaining:
        typer.echo("Remaining: " + ", ".join(field_label(field, privacy) for field in remaining))
        typer.echo("Next: fill the listed fields in reprollm.yaml, then run `reprollm audit .`")
    else:
        typer.echo(
            "Next: review reprollm.yaml, then run `reprollm audit .`; "
            "declarations are not verification."
        )
    if command is not None:
        typer.echo(
            "Saved execution.command. Preview with `reprollm run --dry-run`, "
            "then execute with `reprollm run` from this project."
        )
