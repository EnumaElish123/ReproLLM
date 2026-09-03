"""``reprollm schema export`` — write JSON Schema files for persisted documents (spec §23).

The committed ``schemas/`` directory must always match a fresh export; CI fails on
drift. Output is deterministic: sorted keys, 2-space indent, trailing newline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

from reprollm.schemas.config import Config
from reprollm.schemas.diff_report import DiffReport
from reprollm.schemas.discover_candidates import DiscoverCandidates
from reprollm.schemas.finding import AuditReport
from reprollm.schemas.lock import Lock
from reprollm.schemas.manifest import Manifest
from reprollm.schemas.profile import Profile
from reprollm.schemas.project_rules import ProjectRules
from reprollm.schemas.run_record import RunRecord

app = typer.Typer(help="Export JSON Schemas.", no_args_is_help=True)

_ID_BASE = "https://reprollm.dev/schemas"

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "manifest": Manifest,
    "lock": Lock,
    "run_record": RunRecord,
    "profile": Profile,
    "project_rules": ProjectRules,
    "config": Config,
    "audit_report": AuditReport,
    "diff_report": DiffReport,
    "discover_candidates": DiscoverCandidates,
}


def model_schema_text(model: type[BaseModel], name: str) -> str:
    """Render one model as a stable JSON Schema document with an ``$id``."""
    schema = model.model_json_schema()
    schema["$id"] = f"{_ID_BASE}/{name}.schema.json"
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


@app.command()
def export(
    out: Annotated[
        Path, typer.Option(file_okay=False, help="Directory to write *.schema.json files into.")
    ] = Path("schemas"),
) -> None:
    """Write all exported JSON Schema files listed in spec §23."""
    out.mkdir(parents=True, exist_ok=True)
    for name, model in sorted(SCHEMA_MODELS.items()):
        target = out / f"{name}.schema.json"
        target.write_text(model_schema_text(model, name), encoding="utf-8")
    typer.echo(f"Wrote {len(SCHEMA_MODELS)} schema files to {out}")
