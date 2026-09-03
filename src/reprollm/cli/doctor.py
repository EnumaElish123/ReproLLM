"""``reprollm doctor`` — environment diagnostics (spec §1).

Exit code: 1 when a required check (Python, git) reports ``missing``; else 0.
Network is only touched with the explicit ``--check-network`` flag (D-03).
"""

from __future__ import annotations

import json
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import httpx
import typer

from reprollm import __version__
from reprollm.core import proc
from reprollm.core.envinfo import installed_versions, python_version
from reprollm.schemas.config import Config

#: The only network probe doctor performs, opt-in (D-03).
NETWORK_PROBE_URL = "https://huggingface.co/api/models/gpt2"

#: git versions below this are usable but unsupported (H7 recommends ≥ 2.30).
MIN_GIT_VERSION = (2, 30, 0)

REQUIRED_PYTHON = (3, 10)


class CheckStatus(str, Enum):
    OK = "ok"
    WARN = "warn"
    MISSING = "missing"


def _check_python() -> tuple[CheckStatus, str]:
    if sys.version_info >= REQUIRED_PYTHON:
        return CheckStatus.OK, f"Python {python_version()}"
    return CheckStatus.MISSING, f"Python {python_version()} (< 3.10 unsupported)"


def _check_git() -> tuple[CheckStatus, str]:
    result = proc.run_cmd(["git", "--version"])
    if result.returncode == proc.NOT_FOUND:
        return CheckStatus.MISSING, "git not found on PATH"
    version = result.stdout.strip().removeprefix("git version ")
    try:
        parsed = tuple(int(part) for part in version.split(".")[:3])
        if parsed < MIN_GIT_VERSION:
            return CheckStatus.WARN, f"git {version} (>= 2.30 recommended)"
    except ValueError:
        return CheckStatus.WARN, f"git version unparsable: {version!r}"
    return CheckStatus.OK, f"git {version}"


def _check_nvidia_smi() -> tuple[CheckStatus, str]:
    result = proc.run_cmd(["nvidia-smi", "-L"])
    if result.returncode == proc.NOT_FOUND:
        return CheckStatus.WARN, "nvidia-smi not found; GPU capture unavailable"
    return CheckStatus.OK, "nvidia-smi available"


def _check_uv() -> tuple[CheckStatus, str]:
    if shutil.which("uv"):
        return CheckStatus.OK, "uv available"
    return CheckStatus.WARN, "uv not found (recommended for lockfile detection)"


def _check_llm_packages() -> tuple[CheckStatus, str]:
    versions = installed_versions()
    if not versions:
        return CheckStatus.OK, "no LLM-critical packages installed"
    rendered = ", ".join(f"{name} {version}" for name, version in sorted(versions.items()))
    return CheckStatus.OK, rendered


def _check_documents(root: Path) -> tuple[CheckStatus, str]:
    """Validate reprollm.yaml / .reprollm/config.yaml when present."""
    from reprollm.core.paths import find_root, repo_paths
    from reprollm.core.yaml_io import load_manifest, load_yaml

    paths = repo_paths(find_root(root))
    notes: list[str] = []
    if paths.manifest.is_file():
        try:
            load_manifest(paths.manifest)
            notes.append("reprollm.yaml valid")
        except Exception as exc:  # UserError with the field paths
            notes.append(f"reprollm.yaml INVALID: {exc}")
    if paths.config.is_file():
        try:
            Config.model_validate(load_yaml(paths.config))
            notes.append(".reprollm/config.yaml valid")
        except Exception as exc:
            notes.append(f".reprollm/config.yaml INVALID: {exc}")
    if not notes:
        return CheckStatus.OK, f"no reprollm documents in {paths.root.name}/ (Level 0)"
    joined = "; ".join(notes)
    status = CheckStatus.WARN if "INVALID" in joined else CheckStatus.OK
    return status, joined


def _check_network() -> tuple[CheckStatus, str]:
    try:
        response = httpx.head(NETWORK_PROBE_URL, timeout=10)
    except httpx.HTTPError as exc:
        return CheckStatus.WARN, f"{NETWORK_PROBE_URL}: {type(exc).__name__}"
    if response.status_code < 400:
        return CheckStatus.OK, f"{NETWORK_PROBE_URL}: HTTP {response.status_code}"
    return CheckStatus.WARN, f"{NETWORK_PROBE_URL}: HTTP {response.status_code}"


def run_checks(root: Path, *, check_network: bool) -> list[dict[str, str]]:
    checks: list[tuple[str, tuple[CheckStatus, str]]] = [
        ("python", _check_python()),
        ("git", _check_git()),
        ("nvidia-smi", _check_nvidia_smi()),
        ("uv", _check_uv()),
        ("llm-critical-packages", _check_llm_packages()),
        ("reprollm-documents", _check_documents(root)),
    ]
    if check_network:
        checks.append(("network", _check_network()))
    return [
        {"name": name, "status": status.value, "detail": detail}
        for name, (status, detail) in checks
    ]


def _exit_code(checks: list[dict[str, str]]) -> int:
    required = {"python", "git"}
    return 1 if any(c["status"] == "missing" and c["name"] in required for c in checks) else 0


_SYMBOLS = {"ok": "✔", "warn": "▲", "missing": "✖"}
_SYMBOLS_ASCII = {"ok": "+", "warn": "!", "missing": "X"}


def doctor(
    json_output: Annotated[bool, typer.Option("--json", help="Emit JSON.")] = False,
    check_network: Annotated[
        bool, typer.Option("--check-network", help="Probe the Hugging Face Hub (network).")
    ] = False,
    no_color: Annotated[bool, typer.Option("--no-color")] = False,
) -> None:
    """Diagnose the local environment for ReproLLM."""
    checks = run_checks(Path.cwd(), check_network=check_network)
    code = _exit_code(checks)

    if json_output:
        typer.echo(
            json.dumps(
                {"reprollm_version": __version__, "checks": checks},
                indent=2,
            )
        )
        raise typer.Exit(code)

    symbols = _SYMBOLS_ASCII if no_color else _SYMBOLS
    width = max(len(check["name"]) for check in checks)
    typer.echo(f"reprollm {__version__} doctor")
    for check in checks:
        typer.echo(f"  {symbols[check['status']]} {check['name']:<{width}}  {check['detail']}")
    if code == 0:
        typer.echo("Environment OK.")
    else:
        typer.echo("Environment has missing required tools (see above).")
    raise typer.Exit(code)
