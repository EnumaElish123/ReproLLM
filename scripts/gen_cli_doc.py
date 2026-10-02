"""Generate docs/cli.md from typer --help output (M8-T02, CI-checked freshness)."""

from __future__ import annotations

import difflib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELP_PROGRAM = """\
from functools import partial

import typer.rich_utils
from rich.console import Console

from reprollm.cli.main import app

typer.rich_utils.Console = partial(Console, legacy_windows=False)
typer.rich_utils.FORCE_TERMINAL = False
typer.rich_utils.COLOR_SYSTEM = None
typer.rich_utils.MAX_WIDTH = 80
app(prog_name="reprollm")
"""


def _help(args: list[str]) -> str:
    import os

    # Typer forces terminal styling under GitHub Actions even with piped stdout.
    # Only the captured child needs a plain terminal and a fixed wrap width.
    terminal_flags = {"GITHUB_ACTIONS", "FORCE_COLOR", "PY_COLORS", "TTY_COMPATIBLE"}
    env = {key: value for key, value in os.environ.items() if key not in terminal_flags}
    env.update(
        {
            "COLUMNS": "80",
            "LINES": "24",
            "TERMINAL_WIDTH": "80",
            "TERM": "dumb",
            "NO_COLOR": "1",
            "PYTHONIOENCODING": "utf-8",
        }
    )
    # Console-script names and Rich's legacy Windows fallback differ by host.
    # Render the same Typer app in isolation with canonical documentation styling.
    result = subprocess.run(
        [sys.executable, "-c", HELP_PROGRAM, *args, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        env=env,
    )
    return "\n".join(line.rstrip() for line in result.stdout.splitlines()) + "\n"


def main(check: bool = False) -> int:
    sections: list[str] = [
        "# CLI reference",
        "",
        "Generated from `--help`; regenerate with `scripts/gen_cli_doc.py`.",
        "",
    ]
    sections.append("## reprollm")
    sections.append("```text")
    sections.append(_help([]).rstrip())
    sections.append("```")
    for command in (
        "audit",
        "init",
        "lock",
        "run",
        "runs list",
        "runs show",
        "diff",
        "export",
        "discover",
        "doctor",
        "profiles list",
        "profiles show",
        "rules list",
        "rules add",
        "rules accept",
        "rules ignore",
        "schema export",
    ):
        sections.append(f"## reprollm {command}")
        sections.append("```text")
        sections.append(_help(command.split()).rstrip())
        sections.append("```")
        sections.append("")
    body = "\n".join(sections) + "\n"
    target = ROOT / "docs" / "cli.md"
    if check:
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != body:
            print("docs/cli.md is stale; regenerate with scripts/gen_cli_doc.py")
            print(
                "".join(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        body.splitlines(keepends=True),
                        fromfile="docs/cli.md",
                        tofile="generated/cli.md",
                    )
                ),
                end="",
            )
            return 1
        print("docs/cli.md fresh")
        return 0
    target.write_text(body, encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check="--check" in sys.argv))
