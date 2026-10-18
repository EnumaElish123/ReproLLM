"""VOPT-01: exercise pytest's real selection, including addopts overrides."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("platform", ["ubuntu-latest", "macos-latest", "windows-latest"])
def test_regular_ci_keeps_fast_tests_and_excludes_performance(
    tmp_path: Path, platform: str
) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/quality.yml").read_text())
    row = next(
        item
        for item in workflow["jobs"]["quality"]["strategy"]["matrix"]["include"]
        if item["os"] == platform
    )
    marker = row.get("pytest-marker-filter")
    selected = _collect(tmp_path, ["-m", marker] if marker else [])
    expected = {"test_fast", "test_security"}
    if platform != "windows-latest":
        expected.add("test_linux")
    assert selected == expected


def test_nightly_keeps_both_performance_tests(tmp_path: Path) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/nightly.yml").read_text())
    command = next(
        step["run"]
        for step in workflow["jobs"]["slow"]["steps"]
        if "tests/perf" in step.get("run", "")
    )
    argv = shlex.split(command)
    assert _collect(tmp_path, ["-m", argv[argv.index("-m") + 1]]) == {
        "test_slow",
        "test_slow_linux",
    }


def _collect(tmp_path: Path, selection: list[str]) -> set[str]:
    # The real project addopts must participate: a command-line -m replaces it.
    sample = tmp_path / "test_selection.py"
    sample.write_text(
        "import pytest\n"
        "def test_fast(): pass\n"
        "@pytest.mark.security\ndef test_security(): pass\n"
        "@pytest.mark.linux_only\ndef test_linux(): pass\n"
        "@pytest.mark.slow\ndef test_slow(): pass\n"
        "@pytest.mark.slow\n@pytest.mark.linux_only\ndef test_slow_linux(): pass\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(ROOT / "pyproject.toml"),
            "--confcutdir",
            str(tmp_path),
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            *selection,
            str(sample),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return {line.split("::")[-1] for line in result.stdout.splitlines() if "::test_" in line}
