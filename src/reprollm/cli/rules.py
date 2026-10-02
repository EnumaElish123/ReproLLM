"""``reprollm rules`` — manage project rules (spec §7, M7-T02).

This command group owns ``.reprollm/project-rules.yaml`` and reports the latest
discovery candidates (M7-T04).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

import typer

from reprollm.core.errors import UserError
from reprollm.core.paths import find_root, repo_paths
from reprollm.core.project_rules import load_project_rules
from reprollm.core.rule_lifecycle import (
    ARCHIVE_DIR,
    archive_state,
    display_value,
    load_archive,
    read_rules,
    remove_rule,
    restore_rule,
)
from reprollm.core.yaml_io import dump_yaml
from reprollm.schemas.discover_candidates import DiscoverCandidates
from reprollm.schemas.project_rules import (
    IgnoredCandidate,
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
        temporary.write_text(text, encoding="utf-8", newline="\n")
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
    candidates: Annotated[
        bool, typer.Option("--candidates", help="Inspect full latest candidates and their status.")
    ] = False,
) -> None:
    """List accepted project rules and the latest discovery candidates."""
    root = find_root(Path.cwd())
    document = read_rules(root)
    rules = document.rules if document else []
    if candidates:
        records = _candidate_records(root, document or ProjectRules())
        if json_output:
            typer.echo(json.dumps(display_value(root, records), indent=2, ensure_ascii=False))
        elif not records:
            typer.echo("No discovery candidates found under .reprollm/discover.")
        else:
            for record in records:
                typer.echo(json.dumps(display_value(root, record), indent=2, ensure_ascii=False))
        return
    if json_output:
        typer.echo(json.dumps([rule.model_dump(mode="json") for rule in rules], indent=2))
        return
    if not rules:
        typer.echo("No project rules accepted. Add one with `reprollm rules add`.")
    else:
        typer.echo(f"{len(rules)} project rule(s):")
    ignored = {entry.candidate_id for entry in (document.ignored_candidates if document else [])}
    accepted = {rule.candidate_id for rule in rules if rule.candidate_id is not None}
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
    discover_dir = root / ".reprollm" / "discover"
    if discover_dir.is_dir():
        try:
            _path, latest = _latest_discovery(root)
        except UserError:
            latest = None
        if latest is not None:
            for candidate in latest.candidates:
                state = (
                    "accepted"
                    if candidate.id in accepted
                    else "ignored"
                    if candidate.id in ignored
                    else "pending"
                )
                typer.echo(
                    f"  candidate {candidate.id}  {candidate.kind}  [{state}]  "
                    f"{candidate.suggested_field}"
                )
    archive_dir = root / ARCHIVE_DIR
    if archive_dir.is_symlink() or archive_dir.parent.is_symlink():
        raise UserError(f"{ARCHIVE_DIR} must not contain symlinks")
    if archive_dir.is_dir():
        for archive_path in sorted(archive_dir.glob("*.json")):
            archive = load_archive(root, archive_path.stem)
            state = archive_state(document or ProjectRules(), archive)
            typer.echo(f"  archive {archive.archive_id}  [{state}]  {archive.rule.id}")


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


def _latest_discovery(root: Path) -> tuple[Path, DiscoverCandidates]:
    import glob

    directory = root / ".reprollm" / "discover"
    if directory.is_symlink() or directory.parent.is_symlink():
        raise UserError(".reprollm/discover must not contain symlinks")
    runs = sorted(glob.glob(str(root / ".reprollm" / "discover" / "*.json")))
    if not runs:
        raise UserError(
            "no discovery results under .reprollm/discover; run "
            "`reprollm discover --experimental` first"
        )
    path = Path(runs[-1])
    if path.is_symlink():
        raise UserError("discovery candidate files must not be symlinks")
    try:
        document = DiscoverCandidates.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError) as exc:
        raise UserError(
            f"cannot read latest .reprollm/discover candidate file ({type(exc).__name__}); fix it"
        ) from None
    return path, document


def _candidate_records(root: Path, current: ProjectRules) -> list[dict[str, Any]]:
    directory = root / ".reprollm" / "discover"
    if not directory.exists() and not directory.is_symlink():
        return []
    if directory.is_symlink() or directory.parent.is_symlink():
        raise UserError(".reprollm/discover must not contain symlinks")
    if directory.is_dir() and not any(directory.glob("*.json")):
        return []
    path, document = _latest_discovery(root)
    accepted = {rule.candidate_id for rule in current.rules if rule.candidate_id is not None}
    ignored = {entry.candidate_id for entry in current.ignored_candidates}
    return [
        {
            "candidate": candidate.model_dump(mode="json"),
            "status": "accepted"
            if candidate.id in accepted
            else "ignored"
            if candidate.id in ignored
            else "pending",
            "source": path.relative_to(root).as_posix(),
        }
        for candidate in sorted(document.candidates, key=lambda item: item.id)
    ]


@app.command("show")
def show(
    identifier: Annotated[str, typer.Argument(help="Rule, candidate, or archive id.")],
) -> None:
    """Inspect a complete rule, latest candidate, or immutable recovery copy."""
    root = find_root(Path.cwd())
    current = read_rules(root)
    if identifier.startswith("ra-"):
        archive = load_archive(root, identifier)
        payload: dict[str, Any] = {
            "kind": "archive",
            "archive": archive.model_dump(mode="json"),
            "source": f"{ARCHIVE_DIR}/{archive.archive_id}.json",
            "state": archive_state(current, archive),
            "note": "Archive is a recovery copy; state is derived from current project rules.",
        }
    elif identifier.startswith("project."):
        rule = next((rule for rule in current.rules if rule.id == identifier), None)
        if rule is None:
            raise UserError("unknown active rule; inspect `reprollm rules list`")
        payload = {
            "kind": "rule",
            "rule": rule.model_dump(mode="json"),
            "source": ".reprollm/project-rules.yaml",
        }
    else:
        record = next(
            (
                record
                for record in _candidate_records(root, current)
                if record["candidate"]["id"] == identifier
            ),
            None,
        )
        if record is None:
            raise UserError("unknown latest candidate; inspect `reprollm rules list --candidates`")
        payload = {"kind": "candidate", **record}
    typer.echo(json.dumps(display_value(root, payload), indent=2, ensure_ascii=False))


@app.command("remove")
def remove(
    rule_id: Annotated[str, typer.Argument(help="Active project rule id.")],
    reason: Annotated[str, typer.Option("--reason", help="Why this rule is no longer active.")],
) -> None:
    """Save an immutable recovery copy before removing an active rule."""
    root = find_root(Path.cwd())
    archive = remove_rule(root, rule_id, reason)
    typer.echo(f"Removed {rule_id}; recovery copy: {archive.archive_id}.")
    typer.echo(f"Restore with `reprollm rules restore {archive.archive_id}`.")
    typer.echo("Run `reprollm lock` again: its project_rules_sha256 must be refreshed.")


@app.command("restore")
def restore(archive_id: Annotated[str, typer.Argument(help="Recovery archive id.")]) -> None:
    """Restore the complete original rule without overwriting an active rule."""
    root = find_root(Path.cwd())
    rule = restore_rule(root, archive_id)
    typer.echo(f"Restored {rule.id} from {archive_id}; original source and bindings retained.")
    typer.echo("Run `reprollm lock` again: its project_rules_sha256 must be refreshed.")


@app.command("accept")
def accept(
    candidate_id: Annotated[str, typer.Argument(help="Candidate id, e.g. c-3f9a1b.")],
    severity: Annotated[
        str | None, typer.Option("--severity", help="Override the suggested severity.")
    ] = None,
    field: Annotated[
        str | None, typer.Option("--field", help="Override the suggested field path.")
    ] = None,
) -> None:
    """Accept a discovered candidate as a project rule (source: discover)."""
    root = find_root(Path.cwd())
    _path, document = _latest_discovery(root)
    candidate = document.by_id(candidate_id)
    if candidate is None:
        known = ", ".join(c.id for c in document.candidates) or "none"
        raise UserError(f"unknown candidate {candidate_id!r} (known: {known})")
    chosen_severity = severity or candidate.suggested_severity
    if chosen_severity not in {"CRITICAL", "WARNING", "INFO"}:
        raise UserError(f"severity must be CRITICAL, WARNING, or INFO (got {chosen_severity!r})")
    chosen_field = field or candidate.suggested_field

    paths = repo_paths(root)
    current = load_project_rules(root) or ProjectRules()
    if any(rule.candidate_id == candidate_id for rule in current.rules):
        raise UserError(f"candidate {candidate_id!r} was already accepted")
    if any(rule.id == f"project.{candidate.name}" for rule in current.rules):
        identifier = _unique_id(current, f"project.{candidate.name}")
    else:
        identifier = f"project.{candidate.name}"
    bindings = None
    if candidate.suggested_bindings is not None:
        bindings = ProjectRuleBindings(
            cli=candidate.suggested_bindings.cli,
            config=candidate.suggested_bindings.config,
            env=candidate.suggested_bindings.env,
        )
    current.rules.append(
        ProjectRule(
            id=identifier,
            field=chosen_field,
            severity=chosen_severity,
            reason=candidate.rationale,
            source="discover",
            candidate_id=candidate_id,
            accepted_at=datetime.now(timezone.utc).replace(microsecond=0),
            bindings=bindings,
        )
    )
    _write_rules(root, current)
    typer.echo(
        f"Accepted {candidate_id} → {identifier} ({chosen_severity}) for {chosen_field} "
        f"→ {paths.project_rules}"
    )
    typer.echo("Run `reprollm lock` again: its project_rules_sha256 must be refreshed.")


@app.command("ignore")
def ignore(
    candidate_id: Annotated[str, typer.Argument(help="Candidate id to ignore.")],
    reason: Annotated[
        str | None, typer.Option("--reason", help="Why this candidate is rejected.")
    ] = None,
) -> None:
    """Record a candidate as ignored so future discoveries mark it."""
    root = find_root(Path.cwd())
    current = load_project_rules(root) or ProjectRules()
    accepted = next((rule for rule in current.rules if rule.candidate_id == candidate_id), None)
    if accepted is not None:
        raise UserError(
            f"candidate is already accepted as {accepted.id}; use "
            f"`reprollm rules remove {accepted.id} --reason REASON` to deactivate it"
        )
    _path, document = _latest_discovery(root)
    if document.by_id(candidate_id) is None:
        known = ", ".join(c.id for c in document.candidates) or "none"
        raise UserError(f"unknown candidate {candidate_id!r} (known: {known})")
    if any(entry.candidate_id == candidate_id for entry in current.ignored_candidates):
        raise UserError(f"candidate {candidate_id!r} is already ignored")
    current.ignored_candidates.append(
        IgnoredCandidate(
            candidate_id=candidate_id,
            ignored_at=datetime.now(timezone.utc).replace(microsecond=0),
            reason=reason,
        )
    )
    _write_rules(root, current)
    typer.echo(f"Ignored {candidate_id} → {repo_paths(root).project_rules}")
