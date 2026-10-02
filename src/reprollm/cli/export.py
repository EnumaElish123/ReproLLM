"""``reprollm export`` — write REPRODUCIBILITY.md (spec §19, M7-T01)."""

from __future__ import annotations

import getpass
import socket
from pathlib import Path
from typing import Annotated

import typer

from reprollm import __version__
from reprollm.core.engine import run_audit
from reprollm.core.errors import UserError
from reprollm.core.paths import LOCK, MANIFEST, find_root
from reprollm.core.yaml_io import load_manifest, load_yaml
from reprollm.diff.state import _snapshots, observed_state
from reprollm.run.privacy import RunPrivacy
from reprollm.schemas.lock import Lock
from reprollm.schemas.run_record import RunRecord
from reprollm.schemas.state import State

app = typer.Typer(help="Export REPRODUCIBILITY.md.", no_args_is_help=True)

LATEST_RUN_GLOB = ".reprollm/runs/*/run.json"


def _latest_run(root: Path) -> RunRecord | None:
    runs = sorted(root.glob(LATEST_RUN_GLOB))
    if not runs:
        return None
    import json

    try:
        return RunRecord.model_validate(json.loads(runs[-1].read_text(encoding="utf-8")))
    except Exception as exc:  # noqa: BLE001 - report the exact broken record
        raise UserError(f"cannot load {runs[-1]}: {exc}; fix or remove the run directory") from exc


def _load_lock(root: Path) -> Lock | None:
    path = root / LOCK
    if not path.is_file():
        return None
    from pydantic import ValidationError

    try:
        return Lock.model_validate(load_yaml(path))
    except ValidationError as exc:
        raise UserError(f"invalid lock {path}:\n{exc}") from exc


def _select_run(root: Path, requested: str | None) -> tuple[RunRecord | None, Path | None]:
    """The selected run record plus its directory (needed for its snapshots)."""
    if requested is None:
        runs = sorted(root.glob(LATEST_RUN_GLOB))
        if not runs:
            return None, None
        chosen = runs[-1]
    else:
        matches = [
            p
            for p in sorted(root.glob(LATEST_RUN_GLOB))
            if p.parent.name == requested or p.parent.name.startswith(requested)
        ]
        if not matches:
            raise UserError(f"no run record matches {requested!r} under {root / '.reprollm/runs'}")
        if len({p.parent.name for p in matches}) > 1:
            candidates = ", ".join(p.parent.name for p in matches)
            raise UserError(f"run prefix {requested!r} is ambiguous: {candidates}")
        chosen = matches[-1]
    import json

    record = RunRecord.model_validate(json.loads(chosen.read_text(encoding="utf-8")))
    return record, chosen.parent


@app.command()
def export(
    path: Annotated[Path, typer.Argument(help="Repository to export (default: .)")] = Path("."),
    run: Annotated[
        str | None, typer.Option("--run", help="Run ID or unique prefix (default: latest).")
    ] = None,
    output: Annotated[
        Path, typer.Option("--output", help="Output file (default: REPRODUCIBILITY.md).")
    ] = Path("REPRODUCIBILITY.md"),
    template: Annotated[
        str, typer.Option("--template", help="Checklist mapping: default | neurips | acl | acm.")
    ] = "default",
) -> None:
    """Write REPRODUCIBILITY.md from manifest + lock + the selected run."""
    if template not in ("default", "neurips", "acl", "acm"):
        raise typer.BadParameter(
            f"unknown template {template!r}; choose default, neurips, acl, or acm"
        )
    root = find_root(path)
    if not (root / MANIFEST).is_file():
        raise UserError(f"no reprollm.yaml under {root}; run `reprollm init` first")

    run_record, run_dir = _select_run(root, run)
    if run_record is not None:
        # Same-ranked current declarations must not replace a selected run's own evidence.
        manifest, lock = _snapshots(run_record, run_dir)
        state = State.merge(manifest, lock, observed_state(run_record))
    else:
        manifest = load_manifest(root / MANIFEST)
        lock = _load_lock(root)
        state = State.merge(manifest, lock)

    from reprollm.export.exporter import build_input, render

    audit_report = run_audit(root, target=".")
    data = build_input(
        manifest, lock, run_record, state, reprollm_version=__version__, audit_report=audit_report
    )
    privacy = RunPrivacy(root, hostname=socket.gethostname(), username=getpass.getuser())

    def portable_text(value: str) -> str:
        return privacy.text(value)[0]

    document = render(data, sanitize=portable_text)

    if template != "default":
        from reprollm.export.exporter import enrich_for_checklist, render_checklist_mapping

        enrich_for_checklist(data, manifest, lock)
        document += "\n" + render_checklist_mapping(data, venue=template, sanitize=portable_text)

    target = output if output.is_absolute() else root / output
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(document, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise UserError(f"cannot write {target}: {exc.strerror or type(exc).__name__}") from exc
    typer.echo(
        f"Wrote {target} ({len(data.models)} models, "
        f"{'run ' + run_record.run_id if run_record else 'no run'}) — "
        "commit this file with your paper artifact"
    )
