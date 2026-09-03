"""Repository path constants and root discovery (spec §2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reprollm.core import proc

MANIFEST = "reprollm.yaml"
LOCK = "reprollm.lock"
DOTDIR = ".reprollm"
CONFIG = ".reprollm/config.yaml"
PROJECT_RULES = ".reprollm/project-rules.yaml"
USER_PROFILES_DIR = ".reprollm/profiles"
RUNS_DIR = ".reprollm/runs"
DISCOVER_DIR = ".reprollm/discover"


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
