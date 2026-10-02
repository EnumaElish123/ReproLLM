"""Narrow applicability shared by audit and init (spec §§3.2, 6.1, 12.4)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from reprollm.profiles.loader import user_profile_path


def judge_only_exception(root: Path, declared: Sequence[str], resolved: Sequence[str]) -> bool:
    """Require explicit opt-in and an entirely shipped, compatible profile closure."""
    names = set(resolved)
    return (
        "judge_only" in declared
        and {"core", "judge_only"} <= names <= {"core", "judge_only", "privacy"}
        and not any(user_profile_path(root, name).is_file() for name in sorted(names))
    )
