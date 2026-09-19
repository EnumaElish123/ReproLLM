"""Repository path constants and root discovery (spec §2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from reprollm.core import proc
from reprollm.core.errors import UserError

MANIFEST = "reprollm.yaml"
LOCK = "reprollm.lock"
DOTDIR = ".reprollm"
CONFIG = ".reprollm/config.yaml"
PROJECT_RULES = ".reprollm/project-rules.yaml"
USER_PROFILES_DIR = ".reprollm/profiles"
RUNS_DIR = ".reprollm/runs"
DISCOVER_DIR = ".reprollm/discover"


def is_relative_project_path(value: str) -> bool:
    """Check the portable persisted-path boundary without accessing the filesystem."""
    return bool(value.strip()) and not (
        value.startswith(("/", "\\"))
        or "\\" in value
        or PureWindowsPath(value).drive
        or ".." in value.split("/")
    )


def resolve_project_file(root: Path, relative: str) -> Path | None:
    """Resolve a regular file while rejecting traversal and symlink escapes."""
    if not is_relative_project_path(relative):
        return None
    try:
        resolved_root = root.resolve()
        candidate = (resolved_root / relative).resolve()
        candidate.relative_to(resolved_root)
        return candidate if candidate.is_file() else None
    except (OSError, RuntimeError, ValueError):
        return None


@dataclass(frozen=True)
class RepoPaths:
    """Resolved paths of ReproLLM artifacts inside a repository."""

    root: Path
    manifest: Path
    lock: Path
    config: Path
    project_rules: Path
    runs: Path

    @property
    def dotdir(self) -> Path:
        return self.root / DOTDIR


def repo_paths(root: Path) -> RepoPaths:
    return RepoPaths(
        root=root,
        manifest=root / MANIFEST,
        lock=root / LOCK,
        config=root / CONFIG,
        project_rules=root / PROJECT_RULES,
        runs=root / RUNS_DIR,
    )


def find_root(start: Path) -> Path:
    """Repository root: nearest ancestor with ``reprollm.yaml``, else the git
    toplevel, else ``start`` itself (spec §1)."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / MANIFEST).is_file():
            return candidate
    result = proc.run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=start)
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    return start


def display_target(requested: Path, root: Path) -> str:
    """Persisted-safe display form of the audited path (M2F-T01, spec §0).

    ``"."`` when the target is the repository root, otherwise a repository-
    relative POSIX path. Symlinks are resolved before comparison; a target
    outside the root is a user error — never persist an absolute path.
    """
    resolved = requested.resolve()
    root = root.resolve()
    if resolved == root:
        return "."
    try:
        relative = resolved.relative_to(root)
    except ValueError:
        raise UserError(
            f"target {requested} resolves outside the repository root {root}; "
            "audit a path inside the repository"
        ) from None
    return relative.as_posix()
