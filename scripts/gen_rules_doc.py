"""Generate docs/rules.md from the registered rule catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

import reprollm.rules  # noqa: F401 -- populate the rule registry
from reprollm.core.registry import all_rules
from reprollm.profiles.loader import builtin_profile_names, resolve

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "rules.md"


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_rules_doc() -> str:
    """Return deterministic Markdown for every registered audit rule."""
    profile_names = builtin_profile_names()
    selected = {
        name: set(resolve([] if name == "core" else [name], ROOT).rules) for name in profile_names
    }
    lines = [
        "# Audit rules",
        "",
        "This file is generated from the registered Python rules and built-in profiles.",
        "Run `python scripts/gen_rules_doc.py` after changing either source.",
        "",
        (
            "| Rule ID | Category | Default | Level | Status | Effective profiles | "
            "Description | Fix |"
        ),
        "|---|---|---|---:|---|---|---|---|",
    ]
    for rule in all_rules():
        profiles = ", ".join(name for name in profile_names if rule.id in selected[name]) or "—"
        status = "stub, arrives in 0.2.0" if rule.stub else "implemented"
        default = "project rule" if rule.severity_from_project_rule else rule.default_severity.value
        lines.append(
            f"| `{rule.id}` | {rule.category} | {default} | {rule.min_level} | {status} | "
            f"{profiles} | {_cell(rule.description)} | {_cell(rule.fix_hint)} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when docs/rules.md is stale.")
    args = parser.parse_args()
    rendered = render_rules_doc()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            parser.error("docs/rules.md is stale; run python scripts/gen_rules_doc.py")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
