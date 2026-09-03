"""Shared test infrastructure.

Currently: deterministic git helpers for inline repos. M1-T08 extends this with the
session-wide respx guard, the ``run_cmd`` stub, ``materialize_repo``, and the JSON
snapshot assertion (spec §22).
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

#: Fixed identity/dates so fixture commits are byte-deterministic (spec §22 T-03).
GIT_TEST_ENV: Mapping[str, str] = {
    "GIT_AUTHOR_NAME": "ReproLLM Test",
    "GIT_AUTHOR_EMAIL": "test@reprollm.dev",
    "GIT_COMMITTER_NAME": "ReproLLM Test",
    "GIT_COMMITTER_EMAIL": "test@reprollm.dev",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}


def run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    env = {
        **os.environ,
        **GIT_TEST_ENV,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
    }
    return subprocess.run(
        ["git", *args],  # noqa: S603 - test helper with fixed argv
        cwd=cwd,
        capture_output=True,
        check=True,
        env=env,
    )


def make_git_repo(path: Path, *, branch: str = "main") -> Path:
    """Create an empty git repository on ``branch`` (works on git < 2.28)."""
    path.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True, env=env)
    subprocess.run(
        ["git", "symbolic-ref", "HEAD", f"refs/heads/{branch}"],
        cwd=path,
        capture_output=True,
        check=True,
        env=env,
    )
    return path


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """An empty git repository on ``main``."""
    return make_git_repo(tmp_path / "repo")
