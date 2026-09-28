"""Discover payload collection with redaction gating (spec §20.2, M7-T03).

Deterministic, offline, and safe by construction: only allowlisted file
kinds are read, every text passes §16.2 redaction, and any file whose
redaction count is non-zero is dropped entirely and listed. No network
and no LLM is involved in collection.
"""

from __future__ import annotations

import ast
import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

from reprollm.core.redaction import is_forbidden_file, redact_text
from reprollm.core.scanner import RepoScanner
from reprollm.schemas.config import DiscoverConfig

#: Per-file read cap (spec §20.2).
MAX_FILE_BYTES = 64 * 1024

#: Repository tree entry cap (spec §20.2).
MAX_TREE_ENTRIES = 2000

#: Directory prefixes never collected (spec §20.2).
_EXCLUDED_DIRS = {"data", "datasets", "checkpoints", "outputs", "wandb", ".reprollm", ".git"}

#: Priority order for the character budget: README → configs (small→large)
#: → AST snippets → tree.
_KIND_PRIORITY = ("readme", "config", "snippet", "tree")


@dataclass(frozen=True)
class CollectedFile:
    path: str
    text: str
    chars: int


@dataclass
class Payload:
    files: list[CollectedFile] = field(default_factory=list)
    tree: list[str] = field(default_factory=list)
    dropped_files: list[str] = field(default_factory=list)
    truncated_files: list[str] = field(default_factory=list)
    total_chars: int = 0

    def render(self) -> str:
        """The user-message content sent to the model (deterministic)."""
        parts: list[str] = []
        for entry in self.tree:
            parts.append(entry)
        parts.append("")
        for collected in self.files:
            parts.append(f"----- FILE: {collected.path} -----")
            parts.append(collected.text)
            parts.append("")
        return "\n".join(parts)


def _is_readme(path: str) -> bool:
    name = path.rsplit("/", 1)[-1].lower()
    return name.startswith("readme") and path.count("/") <= 1


def _is_config(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix not in {".yaml", ".yml", ".json", ".toml"}:
        return False
    if Path(path).name.lower() in {
        "uv.lock",
        "poetry.lock",
        "pipfile.lock",
        "conda-lock.yml",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    }:
        return False
    return path.count("/") <= 1  # top-level configs only


def _excluded(path: str) -> bool:
    if is_forbidden_file(path):
        return True
    first = path.split("/", 1)[0]
    return first in _EXCLUDED_DIRS


def _argparse_snippets(scanner: RepoScanner, paths: list[str]) -> list[tuple[str, int, str]]:
    """Source segments of argparse.add_argument / @dataclass / hydra-omegaconf
    class definitions (spec §20.2), extracted deterministically."""
    snippets: list[tuple[str, int, str]] = []
    for path in sorted(p for p in paths if p.endswith(".py")):
        text = scanner.read_text(path)
        if text is None:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        lines = text.splitlines()
        for node in ast.walk(tree):
            target: ast.AST | None = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "add_argument":
                    target = node
            elif isinstance(node, ast.ClassDef) and _interesting_class(node):
                target = node
            if target is None:
                continue
            lineno = int(getattr(target, "lineno", 1) or 1)
            end_line = int(getattr(target, "end_lineno", lineno) or lineno)
            start = max(0, lineno - 1)
            end = min(len(lines), end_line)
            segment = "\n".join(lines[start:end])
            if segment.strip():
                snippets.append((path, lineno, segment))
    snippets.sort()
    return snippets


def _interesting_class(node: ast.ClassDef) -> bool:
    """@dataclass-decorated or hydra/omegaconf-derived configuration classes."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
            return True
    for base in node.bases:
        if isinstance(base, ast.Attribute) and base.attr in {"config", "dataclass"}:
            return True
        if isinstance(base, ast.Name) and base.id in {"OmegaConf", "DictConfig"}:
            return True
    return False


def collect(root: Path, scanner: RepoScanner, config: DiscoverConfig) -> Payload:
    """Build the discover payload under ``config.max_chars`` (M7-T03)."""
    payload = Payload()
    files = [p for p in scanner.files() if not _excluded(p)]

    readmes = sorted(p for p in files if _is_readme(p))
    configs = sorted((p for p in files if _is_config(p)), key=lambda p: (len(p), p))
    python = [p for p in files if p.endswith(".py") and p.count("/") <= 3]

    budget = config.max_chars

    def take(path: str, kind: str) -> None:
        nonlocal budget
        raw = scanner.read_text(path, max_bytes=MAX_FILE_BYTES)
        if raw is None:
            return
        if len(raw.encode("utf-8")) > MAX_FILE_BYTES:
            payload.truncated_files.append(path)
            return
        safe, redactions = redact_text(raw)
        if redactions > 0:
            payload.dropped_files.append(path)  # secrets never leave the machine
            return
        if len(safe) > budget:
            payload.truncated_files.append(path)
            return
        budget -= len(safe)
        payload.files.append(CollectedFile(path, safe, len(safe)))
        del kind

    for path in readmes:
        take(path, "readme")
    for path in configs:
        take(path, "config")

    snippet_budget = max(0, budget)
    for path, lineno, segment in _argparse_snippets(scanner, python):
        snippet_path = f"{path}#L{lineno}"
        safe, redactions = redact_text(segment)
        if redactions > 0:
            payload.dropped_files.append(snippet_path)
            continue
        if len(safe) > snippet_budget:
            payload.truncated_files.append(snippet_path)
            continue
        snippet_budget -= len(safe)
        budget -= len(safe)
        payload.files.append(CollectedFile(snippet_path, safe, len(safe)))

    tree = sorted(files)[:MAX_TREE_ENTRIES]
    tree_text = "\n".join(tree)
    if len(tree_text) <= budget:
        payload.tree = tree
        payload.total_chars = config.max_chars - budget + len(tree_text)
    else:
        keep: list[str] = []
        running = 0
        for entry in tree:
            if running + len(entry) + 1 > budget:
                break
            keep.append(entry)
            running += len(entry) + 1
        payload.tree = keep
        payload.total_chars = config.max_chars
    return payload


def dry_run_report(payload: Payload) -> str:
    lines = ["Discover dry run — nothing is sent:", ""]
    lines.append(f"Total characters: {payload.total_chars}")
    lines.append(f"Files included ({len(payload.files)}):")
    for collected in payload.files:
        lines.append(f"  {collected.path}  ({collected.chars} chars)")
    if payload.dropped_files:
        lines.append(f"Dropped (redaction triggered): {len(payload.dropped_files)}")
        for path in payload.dropped_files:
            lines.append(f"  {path}")
    if payload.truncated_files:
        lines.append(f"Truncated (size/budget): {len(payload.truncated_files)}")
        for path in payload.truncated_files:
            lines.append(f"  {path}")
    lines.append(f"Tree entries: {len(payload.tree)}")
    return "\n".join(lines) + "\n"


def matches_include(patterns: list[str] | None, path: str) -> bool:
    if not patterns:
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)
