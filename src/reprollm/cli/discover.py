"""``reprollm discover`` — experimental LLM-assisted discovery (spec §20, M7-T04).

Opt-in via ``--experimental`` or ``config.discover.enabled``. Shows exactly
what would be sent and requires ``--yes`` (or interactive confirmation).
``--paper`` is rejected in Beta. ``--dry-run`` prints the payload report and
sends nothing.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer

from reprollm import __version__
from reprollm.core.config import load_config
from reprollm.core.errors import UserError
from reprollm.core.paths import find_root
from reprollm.discover.collector import collect, dry_run_report
from reprollm.schemas.config import DiscoverConfig

app = typer.Typer(help="Experimental LLM-assisted discovery.", no_args_is_help=True)


def _endpoint_credentials(config: DiscoverConfig) -> tuple[str, str, str]:
    missing = [
        name
        for name in (config.base_url_env, config.api_key_env, config.model_env)
        if not os.environ.get(name)
    ]
    if missing:
        raise UserError(
            "discover requires "
            + ", ".join(missing)
            + " to be set (configure via .reprollm/config.yaml)"
        )
    return (
        os.environ[config.base_url_env],
        os.environ[config.api_key_env],
        os.environ[config.model_env],
    )


@app.command()
def discover(
    path: Annotated[Path, typer.Argument(help="Repository to analyze (default: .)")] = Path("."),
    experimental: Annotated[
        bool, typer.Option("--experimental", help="Acknowledge the experiment.")
    ] = False,
    yes: Annotated[bool, typer.Option("--yes", help="Send without confirmation.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print the payload report; send nothing.")
    ] = False,
    paper: Annotated[str | None, typer.Option("--paper", help="Reserved for post-Beta.")] = None,
    max_chars: Annotated[int | None, typer.Option(help="Payload budget override.")] = None,
) -> None:
    """Propose project-rule candidates from repository content (JSON only)."""
    if paper is not None:
        raise UserError("Paper analysis is not available in Beta.")
    root = find_root(path)
    config = load_config(root)
    discover_config = config.discover if config else None
    if discover_config is None:
        from reprollm.schemas.config import DiscoverConfig

        discover_config = DiscoverConfig()
    if not (experimental or discover_config.enabled):
        raise UserError(
            "discover is experimental; pass --experimental or set "
            "discover.enabled: true in .reprollm/config.yaml"
        )
    if max_chars is not None:
        if max_chars < 1:
            raise UserError("--max-chars must be positive")
        discover_config = discover_config.model_copy(update={"max_chars": max_chars})

    from reprollm.core.context import AuditContext

    ctx = AuditContext(root, level=0)
    payload = collect(root, ctx.fs, discover_config)
    report = dry_run_report(payload)

    if dry_run:
        typer.echo(report, nl=False)
        return

    base_url, api_key, model = _endpoint_credentials(discover_config)

    typer.echo(report, nl=False)
    if yes:
        pass
    elif not sys_stdin_is_tty():
        raise UserError("non-interactive session: pass --yes to send the payload")
    else:
        if not typer.confirm(
            f"Send these {len(payload.files)} files ({payload.total_chars} chars) "
            f"to {model} at {base_url}?",
            default=False,
        ):
            typer.echo("Aborted; nothing was sent.")
            return

    from reprollm.discover.candidates import finalize
    from reprollm.discover.client import DiscoverError, request_candidates

    system_prompt = (files("reprollm.discover") / "prompts" / "system.md").read_text(
        encoding="utf-8"
    )
    manifest_fields = _manifest_field_list(root)
    user_content = (
        payload.render()
        + "\n\nAlready-declared manifest fields (do not re-suggest):\n"
        + (", ".join(manifest_fields) or "(none)")
    )
    try:
        response = request_candidates(
            base_url=base_url,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_content=user_content,
        )
    except DiscoverError as exc:
        raw_dir = root / ".reprollm" / "discover"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.raw.txt"
        raw_path.write_text(exc.raw_text or user_content, encoding="utf-8")
        from reprollm.core.errors import InternalError

        raise InternalError(
            f"discovery request failed ({exc}); raw response saved to {raw_path}"
        ) from None

    document = finalize(
        response.candidates,
        model=model,
        reprollm_version=__version__,
        input_files=[f.path for f in payload.files],
        dropped_files=payload.dropped_files,
        truncated_files=payload.truncated_files,
        generated_at=datetime.now(timezone.utc),
    )
    out_dir = root / ".reprollm" / "discover"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(document.model_dump_json(indent=2) + "\n", encoding="utf-8")

    typer.echo(f"\nWrote {len(document.candidates)} candidates → {out_path}")
    for candidate in document.candidates:
        typer.echo(
            f"  {candidate.id}  {candidate.kind}  {candidate.confidence}  "
            f"{candidate.suggested_field}"
        )
    typer.echo("Next: `reprollm rules accept <id>` to accept a candidate.")


def _manifest_field_list(root: Path) -> list[str]:
    from reprollm.core.yaml_io import load_manifest

    manifest_path = root / "reprollm.yaml"
    if not manifest_path.is_file():
        return []

    def walk(node: object, prefix: str) -> list[str]:
        if not isinstance(node, dict):
            return [prefix] if prefix else []
        flat: list[str] = []
        for key, value in node.items():
            flat.extend(walk(value, f"{prefix}.{key}" if prefix else str(key)))
        return flat

    try:
        manifest = load_manifest(manifest_path)
    except UserError:
        return []
    return walk(manifest.custom, "custom")


def sys_stdin_is_tty() -> bool:
    import sys

    return sys.stdin.isatty()
