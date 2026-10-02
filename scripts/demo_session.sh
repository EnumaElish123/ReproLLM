#!/usr/bin/env bash
# Record this resource-free walkthrough with asciinema or vhs.
set -euo pipefail
REPROLLM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$REPROLLM_ROOT/.venv/bin:$PATH"
cd "$REPROLLM_ROOT"
python - <<'PY'
import tempfile
from pathlib import Path
from scripts.gen_quickstart import run_workflow

with tempfile.TemporaryDirectory() as directory:
    for step in run_workflow(Path(directory) / "hf_vllm_eval"):
        print(f"$ reprollm {' '.join(step.command)}")
        print(step.stdout)
        if step.stderr:
            print(step.stderr)
        print(f"Exit: {step.exit_code}\n")
PY
