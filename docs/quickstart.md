# Quick start

This tour needs Python 3.10 or newer and Git. It runs a standard-library capture probe; it does not run Qwen, load MMLU, install model libraries, use a GPU, or call an API. The HF/vLLM experiment declaration remains an example of intended research state.

Commands below are executed in a disposable example by CI. JSON blocks are excerpts of actual reports; run IDs and elapsed seconds are replaced with placeholders. Audit exit 1 means findings reached the configured threshold (default: critical). Diff exit 1 means the requested drift threshold was reached. Exit 2 means an input or usage error; exit 3 means an internal error.

## Install and prepare a separate copy

```bash
python --version  # must be 3.10 or newer
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install reprollm
reprollm --version
git clone https://github.com/EnumaElish123/ReproLLM.git
python -c "import shutil
shutil.copytree('ReproLLM/examples/hf_vllm_eval', 'reprollm-tour',
    ignore=shutil.ignore_patterns('reprollm.yaml', 'reprollm.lock',
        '.reprollm', 'REPRODUCIBILITY*'))
shutil.copyfile('ReproLLM/scripts/capture_probe.py',
    'reprollm-tour/capture_probe.py')"
cd reprollm-tour
python -c "from pathlib import Path
p=Path('.gitignore')
p.write_text(p.read_text()+'\n.reprollm/runs/\nREPRODUCIBILITY.md\n')"
git init -b main
git config user.name Tour
git config user.email tour@example.invalid
git add .
git -c commit.gpgsign=false commit -m "Prepare capture exercise"
```

The source example's completed manifest, reviewed online lock and exports stay untouched. This copy starts with no manifest or lock, so its first audit really is Level 0. For your own project, start with `reprollm audit .` in that repository.

## Audit before initialization: Level 0

```bash
reprollm audit . --no-color --format json
```

```json
{
  "level": 0,
  "summary": {
    "critical": 0,
    "warning": 3,
    "info": 2,
    "pass": 6,
    "suppressed": 0,
    "skipped": 1
  }
}
```
Exit: `0`.

## Create a scaffold

```bash
reprollm init .
```

```text
Created <workdir>/reprollm.yaml (profiles: inference; 5 required fields to fill)
Applied detected profiles: inference.
Review experiment.profiles; use --profiles to select this experiment's profiles.
Task candidates: 0; selected: 0. List with: reprollm init PATH --list-tasks
Next: fill the TODO fields, then run `reprollm audit .`
```
Exit: `0`.

## Inspect the scaffold: Level 1

```bash
reprollm audit . --no-color --format json
```

```json
{
  "level": 1,
  "summary": {
    "critical": 2,
    "warning": 9,
    "info": 4,
    "pass": 7,
    "suppressed": 0,
    "skipped": 8
  }
}
```
Exit: `1`.

## Fill the declaration

Replace `reprollm.yaml` with the following completed example and save `configs/capture.json` with the JSON below. In your own project, fill the scaffold from your actual model, data, prompt and execution settings. Here only `capture_probe.py` executes; the model and metric declarations describe the research example, not a successful evaluation.

```yaml
schema_version: 1
project:
  name: capture-tour
experiment:
  profiles:
  - inference
  - evaluation
models:
  primary:
    provider: huggingface
    id: Qwen/Qwen3-32B
    dtype: bfloat16
    quantization: none
datasets:
  eval:
    provider: huggingface
    id: cais/mmlu
    subset: abstract_algebra
    split: test
    preprocessing:
      description: Read the MMLU question and compare the generated answer.
    sampling:
      n: 100
      method: first_n
      seed: 0
prompts:
  system:
    path: prompts/system.txt
    few_shot:
      n: 0
generation:
  temperature: 0.0
  top_p: 1.0
  max_tokens: 32
  seed: 42
  stop: []
inference:
  backend: vllm
  dtype: bfloat16
  tensor_parallel_size: 2
  quantization: none
  gpu_memory_utilization: 0.9
evaluation:
  metrics:
  - name: accuracy
    implementation: eval.py
  aggregation: mean
  repetitions: 1
execution:
  command: python capture_probe.py --config configs/capture.json
  seed: 42
  config_files:
  - configs/capture.json
bindings:
  generation.temperature:
    config: configs/capture.json:generation.temperature
  generation.max_tokens:
    config: configs/capture.json:generation.max_tokens
```

```json
{
  "generation": {
    "temperature": 0.0,
    "max_tokens": 32
  }
}
```

## Audit the filled declaration: Level 1

```bash
reprollm audit . --no-color --format json
```

```json
{
  "level": 1,
  "summary": {
    "critical": 0,
    "warning": 4,
    "info": 3,
    "pass": 30,
    "suppressed": 0,
    "skipped": 4
  }
}
```
Exit: `0`.

## Hash inputs without network resolution

```bash
reprollm lock . --offline
```

```text
Wrote reprollm.lock
Resolved: 0 exact · 0 declared · 6 unresolved · 0 unpinnable
Unresolved:
  - datasets.eval.revision: offline mode; run reprollm lock with network access
  - inference.version: distribution not installed: vllm
  - models.primary.chat_template.sha256: offline mode; run reprollm lock with network access
  - models.primary.config_sha256: offline mode; run reprollm lock with network access
  - models.primary.revision: offline mode; run reprollm lock with network access
  - models.primary.tokenizer.revision: offline mode; run reprollm lock with network access
```
Exit: `0`.

Offline lock hashes available inputs and retains declared values. It leaves remote revisions unresolved. Level 2 and a fresh lock describe available evidence; they do not mean the model experiment passed. Resolve online with `reprollm lock .` later when the required network access is available.

## Check manifest and rule freshness

```bash
reprollm lock . --check
```

```text
reprollm.lock is up to date
```
Exit: `0`.

Commit the declared inputs before capture:

```bash
git add .
git -c commit.gpgsign=false commit -m "Declare capture a"
```

## Capture capture-a (standard-library probe)

```bash
reprollm run --name capture-a --capture-output -- python capture_probe.py --config configs/capture.json
```

```text
Capture exercise only: max_tokens=32; no model run
Recorded run <run-a> (exit 0, <elapsed> s, 3 files hashed, 2 bindings observed, 0 warnings) → .reprollm/runs/<run-a>
```
Exit: `0`.

Keep the printed run ID for the diff/export commands below. Use `reprollm runs list` and `reprollm runs show <run-id>` to inspect it. Hardware or environment availability warnings may vary by machine.

Change `generation.max_tokens` from `32` to `48` in both `reprollm.yaml` and `configs/capture.json`, then rebuild the offline lock.

## Record the intentional parameter change

```bash
reprollm lock . --offline
```

```text
Wrote reprollm.lock
Resolved: 0 exact · 0 declared · 6 unresolved · 0 unpinnable
Unresolved:
  - datasets.eval.revision: offline mode; run reprollm lock with network access
  - inference.version: distribution not installed: vllm
  - models.primary.chat_template.sha256: offline mode; run reprollm lock with network access
  - models.primary.config_sha256: offline mode; run reprollm lock with network access
  - models.primary.revision: offline mode; run reprollm lock with network access
  - models.primary.tokenizer.revision: offline mode; run reprollm lock with network access
```
Exit: `0`.

Offline lock hashes available inputs and retains declared values. It leaves remote revisions unresolved. Level 2 and a fresh lock describe available evidence; they do not mean the model experiment passed. Resolve online with `reprollm lock .` later when the required network access is available.

Commit the declared inputs before capture:

```bash
git add .
git -c commit.gpgsign=false commit -m "Declare capture b"
```

## Capture capture-b (standard-library probe)

```bash
reprollm run --name capture-b --capture-output -- python capture_probe.py --config configs/capture.json
```

```text
Capture exercise only: max_tokens=48; no model run
Recorded run <run-b> (exit 0, <elapsed> s, 3 files hashed, 2 bindings observed, 0 warnings) → .reprollm/runs/<run-b>
```
Exit: `0`.

Keep the printed run ID for the diff/export commands below. Use `reprollm runs list` and `reprollm runs show <run-id>` to inspect it. Hardware or environment availability warnings may vary by machine.

## Audit captured state: Level 2

```bash
reprollm audit . --no-color --format json
```

```json
{
  "level": 2,
  "summary": {
    "critical": 2,
    "warning": 6,
    "info": 2,
    "pass": 37,
    "suppressed": 0,
    "skipped": 7
  }
}
```
Exit: `1`.

## Explain the drift

```bash
reprollm diff <run-a> <run-b> --fail-on HIGH --format json
```

```json
{
  "changes": [
    {
      "a": 32,
      "b": 48,
      "note": null,
      "path": "generation.max_tokens",
      "severity": "HIGH",
      "status": "changed"
    }
  ],
  "highest": "HIGH"
}
```
Exit: `1`.

## Export the selected capture

```bash
reprollm export . --run <run-b>
```

```text
Wrote <workdir>/REPRODUCIBILITY.md (1 models, run <run-b>) — commit this file with your paper artifact
```
Exit: `0`.

Open `REPRODUCIBILITY.md` to review the selected capture, unresolved metadata and audit limitations. Export success means the report was written. This tour verifies capture and comparison; a real inference/evaluation run still requires the experiment's libraries, model/data access and compute.

---
Continue: [concepts](concepts.md) · [CLI reference](cli.md) · [why ReproLLM](why.md)
