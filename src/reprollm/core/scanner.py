"""RepoScanner: cached repository file listing (spec §11).

Minimal M1 implementation: deterministic listing with the mandatory skip rules
(``.git``, ``.reprollm/runs``, caches, virtualenvs, files > 2 MiB, gitignored
paths). Completed in M2-T01 with glob/config helpers and performance work.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

from reprollm.core import git as git_mod
from reprollm.core.git import GitInfo
from reprollm.core.hashing import is_text_file

#: Files larger than this are never listed (spec §11).
MAX_FILE_BYTES = 2 * 1024 * 1024

#: Directory names always skipped when walking without git.
SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".tox",
    "dist",
    "build",
    ".eggs",
}

#: Virtualenv markers: a directory containing one of these is skipped.
_VENV_MARKERS = ("pyvenv.cfg",)

#: Hard skip below the repository root regardless of listing mode.
_HARD_SKIP_PREFIX = ".reprollm/runs/"


class RepoScanner:
    def __init__(self, root: Path, git: GitInfo) -> None:
        self.root = root
        self.git = git
        self._files: list[str] | None = None

    def files(self) -> list[str]:
        """Relative POSIX paths of repository files, sorted (cached)."""
        if self._files is None:
            candidates = git_mod.ls_files(self.root) if self.git.is_repo else self._walk()
            self._files = sorted(
                path
                for path in candidates
                if not path.startswith(_HARD_SKIP_PREFIX) and self._size_of(path) is not None
            )
        return self._files

    def exists(self, rel_path: str) -> bool:
        return (self.root / rel_path).is_file()

    def size(self, rel_path: str) -> int | None:
        return self._size_of(rel_path)

    def read_text(self, rel_path: str, max_bytes: int = 512 * 1024) -> str | None:
        """UTF-8 content up to ``max_bytes``; ``None`` for binary/missing/oversize."""
        target = self.root / rel_path
        if not target.is_file() or target.stat().st_size > max_bytes:
            return None
        if not is_text_file(target, max_bytes):
            return None
        return target.read_text(encoding="utf-8")

    def glob(self, pattern: str) -> list[str]:
        return [p for p in self.files() if fnmatch.fnmatch(p, pattern)]

    def _size_of(self, rel_path: str) -> int | None:
        target = self.root / rel_path
        try:
            if not target.is_file():  # excludes directories and broken symlinks
                return None
            stat = target.stat()
        except OSError:
            return None
        return stat.st_size if stat.st_size <= MAX_FILE_BYTES else None

    def _walk(self) -> list[str]:
        found: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            kept: list[str] = []
            for name in sorted(dirnames):
                full = Path(dirpath) / name
                if name in SKIP_DIR_NAMES:
                    continue
                if any((full / marker).exists() for marker in _VENV_MARKERS):
                    continue
                kept.append(name)
            dirnames[:] = kept
            for name in filenames:
                rel = (Path(dirpath) / name).relative_to(self.root).as_posix()
                if rel.startswith(_HARD_SKIP_PREFIX):
                    continue
                found.append(rel)
        return found
