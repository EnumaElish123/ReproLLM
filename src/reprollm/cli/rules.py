"""``reprollm rules`` — manage project rules (spec §7, M7-T02).

Only this command writes ``.reprollm/project-rules.yaml``. ``rules accept`` /
``rules ignore`` arrive with discover in M7-T04.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer

from reprollm.core.errors import UserError
from reprollm.core.paths import find_root, repo_paths
from reprollm.core.project_rules import load_project_rules
from reprollm.core.yaml_io import dump_yaml
from reprollm.schemas.project_rules import (
    ProjectRule,
    ProjectRuleBindings,
    ProjectRules,
)

app = typer.Typer(help="Manage project-specific rules.", no_args_is_help=True)


def _write_rules(root: Path, document: ProjectRules) -> None:
    paths = repo_paths(root)
    target = paths.project_rules
    payload = document.model_dump(mode="json")
    text = dump_yaml(payload)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".yaml.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(target)
    except OSError as exc:
        raise UserError(f"cannot write {target}: {exc.strerror or type(exc).__name__}") from exc


def _unique_id(document: ProjectRules, base: str) -> str:
    existing = {rule.id for rule in document.rules}
    if base not in existing:
        return base
    suffix = 2
    while f"{base}_{suffix}" in existing:
        suffix += 1
    return f"{base}_{suffix}"


@app.command("list")
def list_rules(
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
) -> None:
    """List accepted project rules (pending discover candidates arrive in M7-T04)."""
    root = find_root(Path.cwd())
    document = load_project_rules(root)
    rules = document.rules if document else []
    if json_output:
        typer.echo(json.dumps([rule.model_dump(mode="json") for rule in rules], indent=2))
        return
    if not rules:
        typer.echo("No project rules accepted. Add one with `reprollm rules add`.")
        return
    typer.echo(f"{len(rules)} project rule(s):")
    for rule in rules:
        bindings = ""
        if rule.bindings is not None:
            parts = [
                f"{key}={getattr(rule.bindings, key)}"
                for key in ("cli", "config", "env")
                if getattr(rule.bindings, key) is not None
            ]
            bindings = " [" + ", ".join(parts) + "]" if parts else ""
        typer.echo(
            f"  {rule.id}  {rule.severity}  {rule.field}{bindings}\n    reason: {rule.reason}"
        )


@app.command("add")
def add(
    field: Annotated[str, typer.Option("--field", help="Manifest field path, e.g. custom.alpha.")],
    severity: Annotated[str, typer.Option("--severity", help="CRITICAL | WARNING | INFO.")],
    reason: Annotated[str, typer.Option("--reason", help="Why this field matters (required).")],
    rule_id: Annotated[
        str | None, typer.Option("--id", help="Rule id; default project.<last segment>.")
    ] = None,
    cli: Annotated[str | None, typer.Option("--cli", help="CLI flag binding.")] = None,
    config: Annotated[
        str | None, typer.Option("--config", help="Config binding 'path:dotted.key'.")
    ] = None,
    env: Annotated[str | None, typer.Option("--env", help="Environment variable binding.")] = None,
) -> None:
    """Append a manual project rule to .reprollm/project-rules.yaml."""
    if severity not in {"CRITICAL", "WARNING", "INFO"}:
        raise UserError(f"severity must be CRITICAL, WARNING, or INFO (got {severity!r})")
    if not reason.strip():
        raise UserError("--reason is required and must be non-empty")
    root = find_root(Path.cwd())
    paths = repo_paths(root)
    document = load_project_rules(root) or ProjectRules()

    identifier = rule_id or f"project.{field.rsplit('.', 1)[-1]}"
    identifier = _unique_id(document, identifier)
    bindings = (
        ProjectRuleBindings(cli=cli, config=config, env=env)
        if any(value is not None for value in (cli, config, env))
        else None
    )
    try:
        rule = ProjectRule(
            id=identifier,
            field=field,
            severity=severity,
            reason=reason.strip(),
            source="manual",
            accepted_at=datetime.now(timezone.utc).replace(microsecond=0),
            bindings=bindings,
        )
    except ValueError as exc:
        raise UserError(f"invalid project rule: {exc}") from exc

    document.rules.append(rule)
    _write_rules(root, document)
    typer.echo(f"Added {identifier} ({severity}) for {field} → {paths.project_rules}")
    typer.echo("Run `reprollm lock` again: its project_rules_sha256 must be refreshed.")
