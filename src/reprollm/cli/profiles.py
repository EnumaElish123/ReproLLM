"""``reprollm profiles list|show`` — inspect profiles (spec §1)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from reprollm.core.errors import UserError
from reprollm.core.paths import find_root
from reprollm.profiles import loader

app = typer.Typer(help="Inspect experiment profiles.", no_args_is_help=True)


@app.command("list")
def list_profiles(
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    """List available profiles (built-ins plus user overrides)."""
    root = find_root(Path.cwd())
    rows = []
    for name in loader.known_profile_names(root):
        profile = loader.load_profile(root, name)
        source = "user" if loader.user_profile_path(root, name).is_file() else "built-in"
        rows.append({"name": name, "source": source, "description": profile.description})
    if json_output:
        import json

        typer.echo(json.dumps(rows, indent=2))
        return
    width = max(len(row["name"]) for row in rows) if rows else 0
    for row in rows:
        typer.echo(f"{row['name']:<{width}}  [{row['source']}]  {row['description']}")


@app.command("show")
def show(
    name: Annotated[str, typer.Argument(help="Profile name.")],
) -> None:
    """Show a profile's inheritance chain, rules, and required fields."""
    root = find_root(Path.cwd())
    if name not in loader.known_profile_names(root):
        known = ", ".join(loader.known_profile_names(root))
        raise UserError(f"unknown profile {name!r} (known profiles: {known})")

    chain = loader.inheritance_chain(root, name)
    resolved = loader.resolve([name], root)
    profile = loader.load_profile(root, name)

    typer.echo(f"profile: {name}")
    source = "user" if loader.user_profile_path(root, name).is_file() else "built-in"
    typer.echo(f"source:  {source}")
    typer.echo(f"description: {profile.description}")
    typer.echo(f"extends: {', '.join(profile.extends) if profile.extends else '(none)'}")
    typer.echo(f"chain:  {' → '.join(reversed(chain))}")
    typer.echo("")
    typer.echo(f"rules ({len(resolved.rules)}):")
    for rule_id in resolved.rules:
        typer.echo(f"  {rule_id}")
    typer.echo("")
    typer.echo("required fields:")
    for field_path in resolved.required_fields:
        typer.echo(f"  {field_path}")
    if resolved.severity_overrides:
        typer.echo("")
        typer.echo("severity overrides:")
        for rule_id, severity in sorted(resolved.severity_overrides.items()):
            typer.echo(f"  {rule_id}: {severity}")
