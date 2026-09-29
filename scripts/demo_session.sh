#!/usr/bin/env bash
# Use the project venv's reprollm when run from a checkout.
REPROLLM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="$REPROLLM_ROOT/.venv/bin:$PATH"
# ReproLLM demo session — paste into asciinema rec or vhs for the README asset.
set -e
cd examples/hf_vllm_eval
echo '$ reprollm audit .'
reprollm audit . --no-color | head -20
echo
echo '$ reprollm init . --force'
reprollm init . --force
echo
echo '$ reprollm export .'
reprollm export . && head -25 REPRODUCIBILITY.md
