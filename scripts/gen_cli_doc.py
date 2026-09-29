"""Generate docs/cli.md from typer --help output (M8-T02, CI-checked freshness)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _help(args: list[str]) -> str:
    import os
    import shutil

    exe = shutil.which("reprollm")
    assert exe, "reprollm console script not on PATH"
    env = {**os.environ, "COLUMNS": "80", "LINES": "24"}  # fixed wrap = portable doc
    result = subprocess.run(
        [exe, *args, "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    return result.stdout


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
            return 1
        print("docs/cli.md fresh")
        return 0
    target.write_text(body, encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(check="--check" in sys.argv))
