"""Scan a directory for machine identity or secret leakage (M8-T07).

Exit 1 on any hit; prints file, pattern, and a redacted excerpt. Usable on any
run directory, examples/, or exported artifacts.
"""

from __future__ import annotations

import getpass
import re
import socket
import sys
from pathlib import Path

PATTERNS: list[tuple[str, str]] = [
    ("openai-key", r"sk-[A-Za-z0-9]{20,}"),
    ("hf-token", r"hf_[A-Za-z0-9]{20,}"),
    ("aws-key", r"AKIA[0-9A-Z]{16}"),
    ("jwt", r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\."),
]
IDENTITY = [
    ("hostname", re.escape(socket.gethostname())),
    ("username", r"(?<![\w])" + re.escape(getpass.getuser()) + r"(?![\w])"),
    ("home-path", r"/home/[a-z]+/"),
    ("mnt-path", r"/mnt/[a-z_]+/"),
]


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root)
        for name, pattern in PATTERNS:
            for match in re.finditer(pattern, text):
                findings.append(f"{rel}: {name} …{match.group(0)[:8]}…")
        for name, pattern in IDENTITY:
            for match in re.finditer(pattern, text):
                findings.append(f"{rel}: {name} {match.group(0)[:30]}")
    return findings


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = Path(argv[1])
    findings = scan(root)
    for finding in findings:
        print(finding)
    if findings:
        print(f"\n{len(findings)} leak pattern(s) found in {root}")
        return 1
    print(f"clean: no leak patterns in {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
