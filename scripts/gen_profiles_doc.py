"""Generate docs/profiles.md from built-in profile YAML."""

from __future__ import annotations

import argparse
from pathlib import Path

import reprollm.rules  # noqa: F401 -- profile resolution validates rule IDs
from reprollm.profiles.loader import builtin_profile_names, load_builtin, resolve

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "profiles.md"


def _items(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) or "—"


def _mapping(values: dict[str, str]) -> str:
    return ", ".join(f"`{key}`: {value}" for key, value in sorted(values.items())) or "—"


def render_profiles_doc() -> str:
    """Return deterministic Markdown for all built-in profiles."""
    lines = [
        "# Built-in profiles",
        "",
        "This file is generated from `src/reprollm/profiles/*.yaml`.",
        "Run `python scripts/gen_profiles_doc.py` after changing a built-in profile.",
        "",
        "`core` is included implicitly and must not appear in `experiment.profiles`.",
    ]
    for name in builtin_profile_names():
        profile = load_builtin(name)
        resolved = resolve([] if name == "core" else [name], ROOT)
        lines.extend(
            [
                "",
                f"## `{name}`",
                "",
                profile.description,
                "",
                f"- Extends: {_items(profile.extends)}",
                f"- Resolution order: {_items(resolved.names)}",
                f"- Required fields: {_items(resolved.required_fields)}",
                f"- Severity overrides: {_mapping(resolved.severity_overrides)}",
                f"- Drift overrides: {_mapping(resolved.drift_overrides)}",
                f"- Detection imports: {_items(resolved.detect.imports)}",
                f"- Detection dependencies: {_items(resolved.detect.dependencies)}",
                f"- Detection keywords: {_items(resolved.detect.keywords)}",
                f"- Detection files: {_items(resolved.detect.files)}",
                "",
                f"Effective rules ({len(resolved.rules)}):",
                "",
                *[f"- `{rule_id}`" for rule_id in resolved.rules],
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when docs/profiles.md is stale.")
    args = parser.parse_args()
    rendered = render_profiles_doc()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            parser.error("docs/profiles.md is stale; run python scripts/gen_profiles_doc.py")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
