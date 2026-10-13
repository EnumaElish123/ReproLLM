"""RepoScanner: cached repository file listing (spec §11, M2-T01).

Two listing modes: ``git ls-files --cached --others --exclude-standard -z``
inside git repositories (respects ``.gitignore``), otherwise an ``os.walk``
with a built-in ignore list. Both modes additionally drop ``.reprollm/runs/**``
and files larger than 2 MiB. Results are sorted and cached; reads are cached
per path. Static analysis uses a separate candidate view with the same
environment/generated-directory exclusions in both listing modes, while
Git and security checks retain the existing file facts.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path, PureWindowsPath

from reprollm.core import git as git_mod
from reprollm.core.git import GitInfo

#: Files larger than this are never listed (spec §11).
MAX_FILE_BYTES = 2 * 1024 * 1024

#: Maximum read size for text content (AST and keyword scanning cap, spec §13).
MAX_READ_BYTES = 512 * 1024

#: Cap on Python files scanned (spec §13); beyond this files are skipped.
MAX_PYTHON_FILES = 500

#: Static candidate exclusions, also pruned by the fallback walker.
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
    ".venv",
    "venv",
    "*.egg-info",
}

#: Virtualenv marker: nested directories containing this are excluded.
_VENV_MARKER = "pyvenv.cfg"

#: Hard skip below the repository root regardless of listing mode.
_HARD_SKIP_PREFIX = ".reprollm/runs/"

#: Config-file extensions scanned for keyword detection (§13).
_CONFIG_EXTENSIONS = {".yaml", ".yml", ".json", ".toml"}

#: Lockfile basenames excluded from the config-file listing.
_LOCKFILE_NAMES = {
    "uv.lock",
    "poetry.lock",
    "pipfile.lock",
    "conda-lock.yml",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
}


class ContentPathError(ValueError):
    """A fixed, path-free reason that a static content path cannot be read."""


def content_source_path(rel_path: str) -> str | None:
    """A normalized, project-relative diagnostic source, without filesystem reads."""
    if "\x00" in rel_path or Path(rel_path).is_absolute() or PureWindowsPath(rel_path).anchor:
        return None
    parts: list[str] = []
    for part in Path(rel_path).parts:
        if part == "..":
            if not parts:
                return None
            parts.pop()
        elif part != ".":
            parts.append(part)
    return Path(*parts).as_posix() if parts else None


def resolve_content_path(root: Path, rel_path: str) -> Path:
    """Resolve static content before opening it; internal ``..`` is permitted.

    Read the resolved target to avoid following the input alias again. Any
    resolved path component, including the final target, can still be replaced
    after validation; this is not a descriptor-based filesystem sandbox.
    """
    if Path(rel_path).is_absolute() or PureWindowsPath(rel_path).anchor:
        raise ContentPathError("absolute paths are not allowed")
    if "\x00" in rel_path:
        raise ContentPathError("invalid path")
    try:
        resolved_root = root.resolve()
        target = (resolved_root / rel_path).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise ContentPathError("cannot resolve path") from exc
    if not target.is_relative_to(resolved_root):
        raise ContentPathError("path resolves outside project root")
    return target


class RepoScanner:
    def __init__(self, root: Path, git: GitInfo) -> None:
        self.root = root
        self.git = git
        self.warnings: list[str] = []
        self._files: list[str] | None = None
        self._analysis_files: list[str] | None = None
        self._text_cache: dict[str, tuple[Path, str | None]] = {}
        self._dirs: set[str] | None = None

    # --- listing -----------------------------------------------------------

    def files(self) -> list[str]:
        """Relative POSIX paths of repository files, sorted (cached)."""
        if self._files is None:
            candidates = git_mod.ls_files(self.root) if self.git.is_repo else self._walk()
            self._files = sorted(
                path
                for path in candidates
                if not path.startswith(_HARD_SKIP_PREFIX) and self._size_of(path) is not None
            )
        return list(self._files)

    def glob(self, pattern: str) -> list[str]:
        """Files whose full relative path matches ``pattern`` (fnmatch)."""
        return [p for p in self.files() if fnmatch.fnmatch(p, pattern)]

    def analysis_files(self) -> list[str]:
        """Static candidates, excluding environments and caches before any budget."""
        if self._analysis_files is None:
            self._analysis_files = [
                path for path in self.files() if self.is_analysis_candidate(path)
            ]
        return list(self._analysis_files)

    def is_analysis_candidate(self, rel_path: str) -> bool:
        """Check a relative candidate, including explicit requirements children."""
        source = content_source_path(rel_path)
        if source is None or source.startswith(_HARD_SKIP_PREFIX):
            return False
        if any(self._skip_name(name) for name in Path(source).parts[:-1]):
            return False
        try:
            target = resolve_content_path(self.root, source)
            resolved_source = target.relative_to(self.root.resolve()).as_posix()
        except ContentPathError:
            # Keep unsafe aliases visible to the existing read boundary and its
            # fixed diagnostics, without inspecting markers outside the root.
            return True
        if resolved_source.startswith(_HARD_SKIP_PREFIX):
            return False
        for candidate in dict.fromkeys((source, resolved_source)):
            parent = Path()
            for name in Path(candidate).parts[:-1]:
                parent /= name
                try:
                    directory = resolve_content_path(self.root, parent.as_posix())
                except ContentPathError:
                    return False
                if self._skip_dir(directory, name):
                    return False
        return True

    def exists(self, rel_path: str) -> bool:
        return (self.root / rel_path).is_file()

    def size(self, rel_path: str) -> int | None:
        return self._size_of(rel_path)

    def read_text(self, rel_path: str, max_bytes: int = MAX_READ_BYTES) -> str | None:
        """UTF-8 content up to ``max_bytes``; ``None`` for binary/missing/oversize.

        The current resolved target is checked even on cache hits. Only the
        default cap is cached, and retargeted aliases cannot reuse old text.
        """
        try:
            target = resolve_content_path(self.root, rel_path)
        except ContentPathError as exc:
            self._read_warning(rel_path, str(exc))
            return None
        try:
            if not target.is_file():
                self._read_warning(rel_path, "not a regular file")
                return None
            if target.stat().st_size > max_bytes:
                return None
        except OSError:
            self._read_warning(rel_path, "cannot inspect file")
            return None
        if max_bytes != MAX_READ_BYTES:
            return self._read_text_uncached(target, rel_path, max_bytes)
        cached = self._text_cache.get(rel_path)
        if cached is None or cached[0] != target:
            cached = (target, self._read_text_uncached(target, rel_path, max_bytes))
            self._text_cache[rel_path] = cached
        return cached[1]

    def python_files(self) -> list[str]:
        """Python sources, capped at :data:`MAX_PYTHON_FILES` (excess recorded once)."""
        sources = [p for p in self.analysis_files() if p.endswith(".py")]
        if len(sources) > MAX_PYTHON_FILES:
            warning = f"python file scan truncated to {MAX_PYTHON_FILES} of {len(sources)} files"
            if warning not in self.warnings:  # repeated access must not duplicate (M2F-T07)
                self.warnings.append(warning)
            sources = sources[:MAX_PYTHON_FILES]
        return sources

    def readme_files(self) -> list[str]:
        """``README*`` (case-insensitive) at the root and in first-level subdirs."""
        return sorted(
            path
            for path in self.analysis_files()
            if len(path.split("/")) <= 2 and path.rsplit("/", 1)[-1].lower().startswith("readme")
        )

    def config_files(self) -> list[str]:
        """YAML/JSON/TOML config files, excluding lockfiles and ``.reprollm/``."""
        return sorted(
            p
            for p in self.analysis_files()
            if Path(p).suffix.lower() in _CONFIG_EXTENSIONS
            and Path(p).name.lower() not in _LOCKFILE_NAMES
            and not p.startswith(".reprollm/")
        )

    def dir_names(self) -> set[str]:
        """Static candidate directory names, including safe empty walk directories."""
        if self._dirs is None:
            names: set[str] = set()
            for path in self.analysis_files():
                parent = path.rsplit("/", 1)[0] if "/" in path else ""
                while parent:
                    names.add(parent.rsplit("/", 1)[-1].lower())
                    parent = parent.rsplit("/", 1)[0] if "/" in parent else ""
            if not self.git.is_repo:
                names.update(self._walk_dirs())
            self._dirs = names
        return set(self._dirs)

    # --- internals ---------------------------------------------------------

    def _read_text_uncached(self, target: Path, rel_path: str, max_bytes: int) -> str | None:
        try:
            with target.open("rb") as stream:
                data = stream.read(max_bytes + 1)
        except OSError:
            self._read_warning(rel_path, "cannot read file")
            return None
        if len(data) > max_bytes or b"\x00" in data:
            return None
        try:
            return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError:
            return None

    def _read_warning(self, rel_path: str, reason: str) -> None:
        source = content_source_path(rel_path) or "repository content"
        warning = f"{source}: {reason}; skipped"
        if warning not in self.warnings:
            self.warnings.append(warning)

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
            dirnames[:] = sorted(
                name for name in dirnames if not self._skip_dir(Path(dirpath) / name, name)
            )
            for name in filenames:
                rel = (Path(dirpath) / name).relative_to(self.root).as_posix()
                if not rel.startswith(_HARD_SKIP_PREFIX):
                    found.append(rel)
        return found

    def _walk_dirs(self) -> set[str]:
        names: set[str] = set()
        for dirpath, dirnames, _filenames in os.walk(self.root):
            dirnames[:] = sorted(
                name
                for name in dirnames
                if self.is_analysis_candidate(
                    ((Path(dirpath) / name).relative_to(self.root) / "candidate").as_posix()
                )
            )
            names.update(name.lower() for name in dirnames)
        return names

    @staticmethod
    def _skip_name(name: str) -> bool:
        if name in SKIP_DIR_NAMES and "*" not in name:
            return True
        return any(fnmatch.fnmatch(name, p) for p in SKIP_DIR_NAMES if "*" in p)

    def _skip_dir(self, path: Path, name: str) -> bool:
        if RepoScanner._skip_name(name):
            return True
        try:
            marker = path / _VENV_MARKER
            return marker.is_symlink() or marker.exists()
        except OSError:
            # An uninspectable environment marker cannot grant scan eligibility.
            try:
                source = path.relative_to(self.root.resolve()).as_posix()
            except (OSError, RuntimeError, ValueError):
                source = "repository content"
            self._read_warning(source, "cannot inspect environment marker")
            return True
