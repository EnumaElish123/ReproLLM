# reprollm/action

GitHub Action for [ReproLLM](https://github.com/EnumaElish123/ReproLLM) — the
reproducibility audit for LLM experiments.

## Usage

```yaml
- uses: EnumaElish123/reprollm-action@v1
  with:
    path: .
    fail-on: critical
```

That's it. Findings appear as inline annotations on your PR; a summary table
lands in the Checks tab; the full JSON report uploads as an artifact.

## Inputs

| Input | Default | Description |
|---|---|---|
| `path` | `.` | Directory to audit |
| `fail-on` | `critical` | Exit 1 when findings reach this severity (`critical`, `warning`, `never`) |
| `level` | `auto` | Force a lower audit level (`0`, `1`, `2`) |
| `version` | `latest` | ReproLLM version to install |
| `check-lock` | `false` | Also run `reprollm lock --check` |

## Outputs

| Output | Description |
|---|---|
| `critical-count` | Number of CRITICAL findings |
| `warning-count` | Number of WARNING findings |

## What it checks

Zero-config (Level 0): git state, dependency pins, secret files, and automatic
experiment-type detection. With a `reprollm.yaml` manifest (Level 1): model
identity, datasets, prompts, generation parameters, judge configuration.
With a lockfile or run records (Level 2): cross-document consistency.

See [docs/why.md](https://github.com/EnumaElish123/ReproLLM/blob/main/docs/why.md)
for the ten failure modes ReproLLM catches.
