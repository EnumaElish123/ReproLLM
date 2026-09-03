"""Git state inspection via the git CLI (always through :mod:`reprollm.core.proc`).

Consumers call ``proc.run_cmd`` through this module reference so tests can stub it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from reprollm.core import proc
from reprollm.core.proc import CmdResult

#: ``https://user:pass@host/...`` → ``https://host/...`` (credentials never persisted).
_CREDENTIALS_RE = re.compile(r"://[^/@:\s]+:[^/@\s]+@")


@dataclass(frozen=True)
class SubmoduleStatus:
    path: str
    initialized: bool


@dataclass(frozen=True)
class GitInfo:
    is_repo: bool
    toplevel: Path | None = None
    commit: str | None = None
    branch: str | None = None
    modified: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    submodules: list[SubmoduleStatus] = field(default_factory=list)
    remote_origin: str | None = None

    @property
    def dirty(self) -> bool:
        return bool(self.modified)


def _git(root: Path, *args: str) -> CmdResult:
    return proc.run_cmd(["git", *args], cwd=root)


def strip_credentials(url: str) -> str:
    return _CREDENTIALS_RE.sub("://", url)


def inspect_git(root: Path) -> GitInfo:
    """Collect repository state: commit, branch, dirty files, submodules, origin."""
    if _git(root, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return GitInfo(is_repo=False)

    toplevel_result = _git(root, "rev-parse", "--show-toplevel")
    toplevel = Path(toplevel_result.stdout.strip()) if toplevel_result.returncode == 0 else None

    head = _git(root, "rev-parse", "HEAD")
    commit = head.stdout.strip() if head.returncode == 0 else None

    # ``branch --show-current`` also works on an unborn branch; fall back to
    # ``rev-parse --abbrev-ref`` (prints "HEAD" when detached).
    branch_result = _git(root, "branch", "--show-current")
    if branch_result.returncode != 0 or not branch_result.stdout.strip():
        branch_result = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    branch = branch_result.stdout.strip() or None

    modified: list[str] = []
    untracked: list[str] = []
    status = _git(root, "status", "--porcelain")
    if status.returncode == 0:
        for line in status.stdout.splitlines():
            if len(line) < 4:
                continue
            code = line[:2]
            path = line[3:].strip().strip('"')
            if "->" in path:
                path = path.split("->", 1)[1].strip().strip('"')
            if code == "??":
                untracked.append(path)
            else:
                modified.append(path)

    submodules: list[SubmoduleStatus] = []
    if toplevel is not None and (toplevel / ".gitmodules").is_file():
        submodules = _submodule_status(root)

    remote = _git(root, "remote", "get-url", "origin")
    remote_origin = strip_credentials(remote.stdout.strip()) if remote.returncode == 0 else None

    return GitInfo(
        is_repo=True,
        toplevel=toplevel,
        commit=commit,
        branch=branch,
        modified=sorted(modified),
        untracked=sorted(untracked),
        submodules=submodules,
        remote_origin=remote_origin,
    )


def _submodule_status(root: Path) -> list[SubmoduleStatus]:
    result = _git(root, "submodule", "status")
    if result.returncode != 0:
        return []
    statuses: list[SubmoduleStatus] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        initialized = not line.startswith("-")
        # Format: "<space|-><sha> <path> (<describe>)"
        parts = line.lstrip("- ").split()
        if len(parts) >= 2:
            statuses.append(SubmoduleStatus(path=parts[1], initialized=initialized))
    return statuses


def check_ignore(root: Path, paths: list[str]) -> set[str]:
    """Return the subset of ``paths`` ignored by git (empty set outside a repo)."""
    if not paths:
        return set()
    result = _git(root, "check-ignore", "--", *paths)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def ls_files(root: Path, include_untracked: bool = True) -> list[str]:
    """List tracked files (and non-ignored untracked ones), sorted, ``-z`` safe."""
    args = ["ls-files", "-z", "--cached"]
    if include_untracked:
        args += ["--others", "--exclude-standard"]
    result = _git(root, *args)
    if result.returncode != 0:
        return []
    return sorted({p for p in result.stdout.split("\0") if p})
