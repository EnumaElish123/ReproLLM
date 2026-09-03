"""Audit level detection (D-12): which documents exist decides the depth."""

from __future__ import annotations

from reprollm.core.paths import RepoPaths


def count_runs(paths: RepoPaths) -> int:
    """Run records present under ``.reprollm/runs`` (M5 writes them)."""
    if not paths.runs.is_dir():
        return 0
    return sum(
        1 for entry in paths.runs.iterdir() if entry.is_dir() and (entry / "run.json").is_file()
    )


def detect_level(paths: RepoPaths) -> int:
    """0 = no manifest, 1 = manifest, 2 = manifest + lock and/or run records."""
    if not paths.manifest.is_file():
        return 0
    if paths.lock.is_file() or count_runs(paths) > 0:
        return 2
    return 1
