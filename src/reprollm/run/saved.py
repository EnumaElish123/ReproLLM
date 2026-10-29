"""Select a bounded saved invocation before allocating any runtime artifacts."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

import yaml

from reprollm.core.configread import MAX_CONFIG_BYTES
from reprollm.core.errors import UserError
from reprollm.core.paths import MANIFEST, resolve_project_file
from reprollm.core.redaction import is_forbidden_file
from reprollm.core.saved_command import parse_saved_command
from reprollm.schemas.manifest import Manifest


@dataclass(frozen=True)
class SavedInvocation:
    argv: list[str]
    cwd: Path


def _manifest_root(start: Path) -> Path:
    for root in (start, *start.parents):
        candidate = root / MANIFEST
        if candidate.exists() or candidate.is_symlink():
            return root
    raise UserError(
        "no reprollm.yaml for saved execution.command; run `reprollm init --command "
        "'python train.py'` or pass a command after --"
    )


def _manifest(root: Path) -> Manifest:
    path = resolve_project_file(root, MANIFEST)
    if path is None or is_forbidden_file(path.name):
        raise UserError("reprollm.yaml must be a permitted regular file inside the repository")
    try:
        with path.open("rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise UserError("reprollm.yaml must be a regular file")
            data = stream.read(MAX_CONFIG_BYTES + 1)
        if len(data) > MAX_CONFIG_BYTES:
            raise UserError("reprollm.yaml exceeds the 2 MiB saved-command limit; reduce this file")
        value = yaml.safe_load(data.decode("utf-8"))
        return Manifest.model_validate({} if value is None else value)
    except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
        raise UserError(
            f"cannot read reprollm.yaml ({type(exc).__name__}); repair this file "
            "or upgrade ReproLLM for a newer schema_version"
        ) from None


def load_saved_invocation(cwd: Path | None) -> SavedInvocation:
    """Use the manifest's cwd by default, preserving an explicit CLI cwd override."""
    try:
        start = (cwd if cwd is not None else Path.cwd()).resolve()
        if not start.is_dir():
            raise UserError("--cwd must name an existing directory")
        root = _manifest_root(start)
        manifest = _manifest(root)
        execution = manifest.execution
        if execution is None or execution.command is None:
            raise UserError(
                "execution.command is missing; set it in reprollm.yaml or pass a command after --"
            )
        argv = parse_saved_command(execution.command)
        working = start if cwd is not None else (root / (execution.cwd or ".")).resolve()
        if not working.is_dir() or not working.is_relative_to(root):
            raise UserError("execution.cwd must name an existing directory inside the repository")
        if _manifest_root(working) != root:
            raise UserError("execution.cwd must not select a different nested reprollm.yaml")
        return SavedInvocation(argv=argv, cwd=working)
    except (OSError, RuntimeError):
        raise UserError(
            "cannot inspect execution.command or execution.cwd; check paths and permissions"
        ) from None
