"""Standard-library capture exercise; this does not perform model inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(f"Capture exercise only: max_tokens={config['generation']['max_tokens']}; no model run")


if __name__ == "__main__":
    main()
