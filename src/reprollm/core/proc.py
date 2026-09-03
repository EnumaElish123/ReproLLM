"""``run_cmd`` — the single subprocess gateway (spec §22 T-05).

All ``git`` / ``nvidia-smi`` invocations go through this function so tests can
monkeypatch ``reprollm.core.proc.run_cmd`` with canned results. The only other
allowed subprocess user is ``run/wrapper.py`` (child process execution, M5).
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: Exit code reported when the binary does not exist (mirrors shell convention).
NOT_FOUND = 127

#: Exit code reported when the command exceeds its timeout.
TIMEOUT = 124


@dataclass(frozen=True)
class CmdResult:
    returncode: int
    stdout: str
    stderr: str


def run_cmd(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float = 30,
    env: Mapping[str, str] | None = None,
) -> CmdResult:
    """Run ``argv`` without a shell and capture output; never raises for exit codes."""
    try:
        completed = subprocess.run(
            list(argv),
            cwd=None if cwd is None else str(cwd),
            capture_output=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except FileNotFoundError:
        return CmdResult(NOT_FOUND, "", f"command not found: {argv[0]}")
    except subprocess.TimeoutExpired as exc:
        return CmdResult(TIMEOUT, "", f"timeout after {timeout}s: {' '.join(argv)} ({exc})")
    return CmdResult(
        returncode=completed.returncode,
        stdout=completed.stdout.decode("utf-8", errors="replace"),
        stderr=completed.stderr.decode("utf-8", errors="replace"),
    )
