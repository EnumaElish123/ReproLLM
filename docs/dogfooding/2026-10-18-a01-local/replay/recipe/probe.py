"""Read this recipe's restricted YAML shape without framework dependencies.

This stdlib witness tests capture plumbing; it does not implement lm-eval.
The native parser and actual requests remain separate L1/L3 evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def read_recipe(data: bytes) -> dict[str, Any]:
    """Accept only the two-level scalar/list mapping used by the fixed recipe."""
    document: dict[str, Any] = {}
    current = document
    for line in data.decode("utf-8").splitlines():
        match = re.fullmatch(r"(  )?([a-z_]+):(?: (.*))?", line)
        if match is None:
            raise ValueError("probe config must use the fixed recipe's two-level mapping")
        indent, key, raw = match.groups()
        if indent is None:
            current = document
        if key in current:
            raise ValueError("probe config contains a duplicate key")
        if raw is None:
            if indent is not None:
                raise ValueError("probe config nested mappings exceed the recipe shape")
            current[key] = {}
            current = current[key]
        elif raw == "[gsm8k_validation]":
            current[key] = ["gsm8k_validation"]
        else:
            try:
                current[key] = json.loads(raw)
            except json.JSONDecodeError:
                if not re.fullmatch(r"[A-Za-z0-9_./-]+", raw):
                    raise ValueError("probe config contains an unsupported scalar") from None
                current[key] = raw
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--rewrite-cap", type=int)
    args = parser.parse_args()
    original = args.config.read_bytes()
    configuration = read_recipe(original)
    receipt = {
        "schema_version": 1,
        "witness": "stdlib recipe parser; no model execution",
        "input_sha256": hashlib.sha256(original).hexdigest(),
        "configuration": configuration,
    }
    output = Path("outputs/current/consumed.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    if args.rewrite_cap is not None:
        changed, count = re.subn(
            rb"(?m)^  max_gen_toks: [0-9]+$",
            f"  max_gen_toks: {args.rewrite_cap}".encode(),
            original,
        )
        if count != 1:
            raise ValueError("probe config must contain exactly one generation cap")
        args.config.write_bytes(changed)


if __name__ == "__main__":
    main()
