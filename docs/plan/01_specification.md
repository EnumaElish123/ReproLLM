# ReproLLM — Beta Specification (v0.5.0)

> Status: **NORMATIVE for Beta.** This document defines the CLI contract, all persisted schemas, the rule catalog, redaction policy, diff semantics, and testing requirements. Implementers follow this document literally; deviations require a spec change PR that updates this file first.
>
> Key words MUST, MUST NOT, SHOULD, MAY are used as in RFC 2119.
>
> Last updated: 2026-09-03. Companion documents: `00_architecture_and_decisions.md` (intent, decision IDs `D-nn`), `AGENTS.md` (working conventions).

---

## 0. Conventions

- All paths persisted in artifacts are **POSIX-style, relative to the repository root**. Absolute paths and `..` segments are rejected in manifests.
- All timestamps are ISO-8601 UTC with `Z` suffix, second precision: `2026-10-01T09:30:00Z`.
- All hashes are lowercase hex SHA-256 of raw bytes, prefixed `sha256:` in YAML/JSON (`sha256:8fa2…`).
- Every persisted document carries `schema_version: 1` (integer) and `reprollm_version: "<semver>"`.
- YAML documents are written with 2-space indentation, keys in the order defined here (stable ordering is a requirement for reviewable diffs).
- "Field path" means a dotted path into the manifest/ExperimentState, e.g. `models.primary.revision`. Role keys appear literally (`models.judge.id`); the wildcard `*` matches any single role.
- Severities: `CRITICAL | WARNING | INFO | PASS` (audit); drift severities: `HIGH | MEDIUM_HIGH | MEDIUM | LOW | NONE` (diff).
- Rule categories (D-08, extended): `code, env, exec, model, dataset, gen, prompt, eval, judge, train, privacy, consistency, project`.

---

## 1. CLI contract

Entry point: `reprollm` (typer). Global options: `--version`, `--no-color`, `-v/--verbose`, `-q/--quiet`. Color is disabled automatically when stdout is not a TTY or `NO_COLOR` is set.

| Command | Purpose | Sprint |
|---|---|---|
| `reprollm --version` | print version | M1 |
| `reprollm doctor [--json] [--check-network]` | environment diagnostics | M1 |
| `reprollm schema export [--out DIR]` | write JSON Schema files | M1 |
| `reprollm init [PATH] [--force] [--interactive] [--profiles a,b]` | create `reprollm.yaml` + `.reprollm/` | M2 |
| `reprollm audit [PATH] [--format text\|json] [--output FILE] [--fail-on critical\|warning\|never] [--level 0\|1\|2\|auto] [--profiles a,b] [--show-passed] [--show-skipped]` | run rules | M2–M6 |
| `reprollm profiles list \| show NAME` | inspect profiles | M2 |
| `reprollm lock [PATH] [--offline] [--check] [--verify-api] [--hash-large-files]` | resolve and write `reprollm.lock` | M4 |
| `reprollm run [--name NAME] [--capture-output] [--env-capture allowlist\|all] [--no-snapshot] [--cwd DIR] -- CMD…` | execute and record | M5 |
| `reprollm runs list [--json]` / `runs show RUN_ID [--json]` | inspect run records | M5 |
| `reprollm diff A B [--format text\|json] [--min-severity LOW\|MEDIUM\|MEDIUM_HIGH\|HIGH] [--fail-on SEV]` | semantic drift | M6 |
| `reprollm export [--run RUN_ID] [--output PATH] [--template default]` | write `REPRODUCIBILITY.md` | M7 |
| `reprollm discover [PATH] --experimental [--yes] [--dry-run] [--max-chars N] [--paper FILE]` | LLM-assisted candidate discovery | M7 |
| `reprollm rules list [--json] \| accept CANDIDATE_ID [--severity S] \| ignore CANDIDATE_ID \| add --field F --severity S --reason R [--cli FLAG] [--config P:K] [--env VAR]` | manage project rules | M7 |

`PATH` defaults to `.`. The repository root is the nearest ancestor containing `reprollm.yaml`, else the git toplevel, else `PATH` itself.

### 1.1 Exit codes (D-11)

| Code | Meaning |
|---|---|
| 0 | success; for `audit`/`diff`, nothing at or above the `--fail-on` threshold |
| 1 | `audit`: findings at/above threshold (default `critical`); `lock --check`: stale or missing lock; `diff --fail-on`: drift at/above threshold |
| 2 | usage error, invalid manifest/config/profile, unknown rule ID, `--paper` in Beta |
| 3 | internal error (unexpected exception); a traceback is written only with `-v` |
| child | `run` exits with the wrapped command's exit code after writing the record |

### 1.2 Output formats

- `text`: rich-formatted, grouped by category, CRITICAL first; see §21.
- `json`: exactly one JSON document on stdout (schemas §10, §18.3). Diagnostics go to stderr. `--output FILE` writes the document to a file and prints a one-line summary on stdout.

---

## 2. Storage layout

See `00 §7`. Path constants live in `reprollm/core/paths.py`:

```python
MANIFEST = "reprollm.yaml"
LOCK = "reprollm.lock"
DOTDIR = ".reprollm"
CONFIG = ".reprollm/config.yaml"
PROJECT_RULES = ".reprollm/project-rules.yaml"
USER_PROFILES_DIR = ".reprollm/profiles"
RUNS_DIR = ".reprollm/runs"
DISCOVER_DIR = ".reprollm/discover"
```

---

## 3. Manifest schema — `reprollm.yaml`

pydantic model `Manifest` (`reprollm/schemas/manifest.py`), `extra="forbid"` everywhere except `custom`, `*.params`, and `artifacts.metadata`.

```yaml
schema_version: 1

project:
  name: string                      # required, ^[A-Za-z0-9._-]{1,64}$
  description: string?
  paper: { title: string?, url: string?, doi: string? }?

experiment:
  name: string?
  description: string?
  profiles: [string]                # required; may be []; names must resolve to built-in or user profiles

models:                             # map role -> ModelSpec; role ^[a-z][a-z0-9_]{0,31}$
  <role>:
    provider: huggingface | openai | openrouter | anthropic | local | other   # required
    id: string                      # required; HF repo id, API model id, or local path
    revision: string?               # user-declared pin; lock resolves/verifies
    tokenizer: { id: string?, revision: string? }?
    dtype: string?                  # e.g. bfloat16
    quantization: string?           # e.g. none | awq | gptq | fp8 | bnb-4bit
    adapter:
      provider: peft | other
      id: string                    # HF id or local path
      revision: string?
      type: lora | qlora | ia3 | other
      rank: int?  alpha: number?  dropout: number?  target_modules: [string]?
    trust_remote_code: bool?
    chat_template: { path: string }?      # custom template file, hashed by lock
    endpoint: { base_url: string?, api_version: string? }?
    params: {}                      # free-form provider parameters

datasets:                           # map role -> DatasetSpec
  <role>:
    provider: huggingface | local | other
    id: string                      # HF id or local path/glob root
    revision: string?
    subset: string?  split: string?
    files: [string]?                # local files (relative); hashed by lock
    preprocessing: { script: string?, description: string?, params: {} }?
    sampling: { n: int?, method: string?, seed: int? }?

prompts:                            # map role -> PromptSpec; exactly one of path|text
  <role>:
    path: string?
    text: string?
    format: jinja | fstring | plain?  # default plain
    few_shot: { path: string?, n: int? }?

generation:
  temperature: number?  top_p: number?  top_k: int?  max_tokens: int?
  seed: int?  do_sample: bool?  stop: [string]?  repetition_penalty: number?  n: int?

inference:
  backend: vllm | transformers | sglang | openai | other
  version: string?                  # declared; lock records actual
  mode: offline | serving?
  dtype: string?  tensor_parallel_size: int?  gpu_memory_utilization: number?
  quantization: string?  max_model_len: int?  kv_cache_dtype: string?
  params: {}

training:                           # finetuning profile
  method: full | lora | qlora | other
  learning_rate: number?  optimizer: string?  scheduler: string?
  batch_size: int?  gradient_accumulation: int?  epochs: number?  max_steps: int?
  precision: string?  seed: int?
  deepspeed: { config: string }?    # path; hashed by lock
  params: {}

evaluation:
  metrics: [ { name: string, implementation: string?, params: {} } ]   # implementation: path or "pkg==ver"
  aggregation: string?
  repetitions: int?
  thresholds: { <name>: number }?
  definitions: { refusal: string?, asr: string?, <other>: string }?    # text or relative path
  query_budget: int?
  judge:
    model_ref: string               # key into models; default "judge"
    prompt_ref: string              # key into prompts; default "judge"
    params: { temperature: number?, top_p: number?, max_tokens: int?, seed: int? }
    repetitions: int?
    parser: string?

privacy:                            # privacy profile
  threat_model: string              # text or path
  mechanism: { name: string, params: {} }
  metrics: [string]?
  attack: { method: string?, params: {}, query_budget: int? }?

execution:
  command: string?
  cwd: string?                      # relative
  seed: int?
  config_files: [string]?           # additional files to hash/snapshot
  env_requirements: [string]?       # informational

bindings:                           # field path -> runtime locations (D-40)
  <field.path>:
    cli: string?                    # "--temperature" ; matches "--temperature V" and "--temperature=V"
    config: string?                 # "configs/eval.yaml:sampling.temperature"
    env: string?                    # "SEED"

custom: {}                          # free-form; values only; requirements come from project rules

artifacts:
  outputs: [string]?                # paths/globs hashed by run after the command exits
  metadata: {}
```

### 3.1 Validation rules

- V-01 `project.name` and `experiment.profiles` are required.
- V-02 Unknown profile name → exit 2 with the list of known profiles.
- V-03 Any path field: relative, POSIX, no `..`, no leading `/`, no drive letter.
- V-04 `prompts.<role>` has exactly one of `path`, `text`.
- V-05 `evaluation.judge.model_ref`/`prompt_ref` MUST reference existing keys when `evaluation.judge` is present.
- V-06 `bindings` keys MUST be valid field paths into this schema (validated against the flattened model, wildcards not allowed). Paths that descend into a free-form block (`custom.*`, `*.params.*`, `artifacts.metadata.*`) are accepted without structural validation.
- V-07 `models.<role>.provider == local` requires `id` to be a relative path.
- V-08 Numeric ranges: `0 ≤ temperature ≤ 2`, `0 < top_p ≤ 1`, `max_tokens ≥ 1`, `gpu_memory_utilization ∈ (0,1]`.

### 3.2 `init` template

`init` writes YAML text from `reprollm/cli/templates/manifest.yaml.j2` (comments preserved), not from a model dump. Detected profiles fill `experiment.profiles`. Fields listed in the union of selected profiles' `required_fields` are rendered with `# TODO` comments; detected literal HF ids (AST string constants passed to `from_pretrained`/`LLM(model=…)`) are pre-filled with `# detected: <file>:<line>`.

---

## 4. Lock schema — `reprollm.lock`

pydantic model `Lock` (`reprollm/schemas/lock.py`). YAML. Written only by `reprollm lock`.

### 4.1 Provenance object

```yaml
value: <scalar|null>
source: string           # e.g. hf_api, hf_file:tokenizer_config.json, manifest, importlib_metadata, nvidia_smi, filesystem, provider_no_pinning, hf_api_forbidden, offline
confidence: exact | declared | unresolved
resolved_at: timestamp?  # present when confidence == exact
note: string?            # human-readable reason when unresolved
```

### 4.2 Document

```yaml
schema_version: 1
reprollm_version: "0.2.0"
generated_at: 2026-10-01T09:30:00Z
manifest_sha256: sha256:…
project_rules_sha256: sha256:… | null
resolution: { mode: online | offline }

models:
  <role>:
    provider: huggingface
    id: Qwen/Qwen3-32B
    pinnability: exact | snapshot_alias | unpinnable
    revision: <Provenance>                 # HF commit sha; null for API
    observed_at: timestamp?                # API providers
    tokenizer: { id: string, revision: <Provenance> }
    chat_template: { sha256: <Provenance>, status: present | absent | custom_file }
    config_sha256: <Provenance>?           # HF config.json
    adapter: { id, revision: <Provenance>, config_sha256: <Provenance>? }?
    local: { path, config_sha256: <Provenance>?, weights: { hashed: bool, total_size_bytes: int, sha256: string? } }?
    dtype: …  quantization: …  trust_remote_code: …   # passthrough

datasets:
  <role>:
    provider: huggingface
    id: cais/mmlu
    revision: <Provenance>
    subset: …  split: …                    # passthrough
    content_fingerprint: { status: not_computed }       # D-22
    files: [ { path, sha256, size_bytes } ]?            # local provider

prompts:
  <role>: { path: string, sha256: string, size_bytes: int } | { text_sha256: string }

files:                                     # execution.config_files, bindings config paths, training.deepspeed.config, models.*.chat_template.path, evaluation.definitions paths
  - { path: string, sha256: string, size_bytes: int }

generation: { … passthrough … }
inference:
  backend: vllm
  version: <Provenance>                    # importlib_metadata
  … passthrough …
training: { … passthrough … }
evaluation:
  metrics: [ { name, implementation, implementation_sha256: string?, implementation_version: <Provenance>? } ]
  … passthrough …
privacy: { … passthrough … }
environment:                               # expected environment at lock time
  python: "3.11.9"
  platform: linux | darwin | windows
  packages: { torch: "2.8.0", transformers: "4.57.0", … }     # LLM-critical list §4.4, only if installed
  gpu: { driver: string?, cuda_driver_max: string?, source: nvidia_smi | unavailable }
```

### 4.3 Resolution rules

| Provider | Behavior |
|---|---|
| `huggingface` model | `GET https://huggingface.co/api/models/{id}/revision/{rev or main}` → `sha`; tokenizer resolved likewise (same repo unless `tokenizer.id` differs); `chat_template.sha256` = SHA-256 of the UTF-8 `chat_template` value in `tokenizer_config.json` at that sha (if string) or of `json.dumps(value, sort_keys=True, ensure_ascii=False)` (if list/dict); if `chat_template.jinja` exists in `siblings`, hash that file instead and set `source: hf_file:chat_template.jinja`; `status: absent` when neither exists; `config_sha256` from `config.json`. Adapter (`adapter.provider == peft`, HF id) resolved as a model repo with `adapter_config.json` hashed. |
| `huggingface` dataset | `GET https://huggingface.co/api/datasets/{id}/revision/{rev or main}` → `sha`. |
| Gated / private / 401 / 403 | `confidence: unresolved`, `source: hf_api_forbidden`. If `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` is present in the environment it is sent as `Authorization: Bearer` and never persisted. |
| Network error / timeout (10 s, 2 retries) | `confidence: unresolved`, `source: network_error`, `note` with the error class. |
| `--offline` | no HTTP; declared `revision` → `confidence: declared`; otherwise `unresolved`, `source: offline`. |
| `openai` / `openrouter` / `anthropic` | no network by default. `pinnability`: `snapshot_alias` if `id` matches `-\d{4}-\d{2}-\d{2}$` or `@\d{8}$`, else `unpinnable`. `revision.value: null`, `source: provider_no_pinning`, `observed_at: now`. With `--verify-api` and the provider's key present: `GET {base_url}/models/{id}` → `note: "exists"` or `"not_found"`. |
| `local` | `id` must exist. Directory: hash `config.json`, `tokenizer_config.json`, `tokenizer.json` if present; weights files (`*.safetensors`, `*.bin`, `*.gguf`, `*.pt`) hashed only with `--hash-large-files` or if total ≤ 100 MiB; otherwise `weights.hashed: false`. |
| prompts / files | SHA-256 of bytes; missing file → lock entry omitted and audit rule `prompt.file_exists` reports. |
| `inference.version` | `importlib.metadata.version(backend_package)`; `unresolved` if not installed. |
| `evaluation.metrics[].implementation` | if a relative path exists → `implementation_sha256`; if `pkg==ver` or `pkg` → `implementation_version` via importlib.metadata. |

### 4.4 LLM-critical package list

`torch, transformers, tokenizers, datasets, accelerate, peft, trl, vllm, sglang, openai, anthropic, numpy, safetensors, deepspeed, flash_attn, xformers, bitsandbytes, sentencepiece, evaluate, lm_eval, lighteval, inspect_ai`. Constant `LLM_CRITICAL_PACKAGES` in `reprollm/core/envinfo.py`. Versions via `importlib.metadata`; never `import`.

### 4.5 Staleness

`lock --check` exits 1 if the lock is missing, `manifest_sha256` differs from the current manifest, or `project_rules_sha256` differs. Rule `consistency.lock_fresh` reports the same at audit Level 2.

---

## 5. Run record schema — `.reprollm/runs/<run_id>/run.json`

pydantic model `RunRecord` (`reprollm/schemas/run_record.py`).

```json
{
  "schema_version": 1,
  "reprollm_version": "0.3.0",
  "run_id": "20261005T093000Z-a1b2c3",
  "name": "optional user label",
  "status": "completed | failed | interrupted",
  "started_at": "…Z", "ended_at": "…Z", "duration_seconds": 123.4, "exit_code": 0,
  "command": { "argv": ["python", "eval.py", "--temperature", "0.7"], "cwd": ".", "redactions": 0 },
  "code": {
    "commit": "a12f738…", "branch": "main", "dirty": true, "modified_count": 4, "untracked_count": 1,
    "remote": "https://github.com/org/repo.git", "patch_sha256": "sha256:…", "patch_file": "patch.diff"
  },
  "environment": {
    "os": "Linux-6.8…", "platform": "linux", "python": "3.11.9", "hostname_sha256": "sha256:…",
    "packages": { "torch": "2.8.0", "transformers": "4.57.0" },
    "env": { "CUDA_VISIBLE_DEVICES": "0,1", "OPENAI_API_KEY": { "present": true } },
    "env_capture": "allowlist"
  },
  "hardware": {
    "cpu_count": 32,
    "gpus": [ { "index": 0, "name": "NVIDIA H100 80GB HBM3", "memory_mib": 81559, "uuid_sha256": "sha256:…" } ],
    "driver": "560.35.03", "cuda_driver_max": "12.6", "source": "nvidia_smi | unavailable"
  },
  "scheduler": { "slurm": { "SLURM_JOB_ID": "…", "SLURM_NNODES": "1", "SLURM_GPUS_ON_NODE": "2" } },
  "manifest": { "path": "reprollm.yaml", "sha256": "sha256:…", "snapshot": "manifest.yaml" },
  "lock": { "path": "reprollm.lock", "sha256": "sha256:…", "snapshot": "lock.yaml" },
  "files": [
    { "path": "configs/eval.yaml", "sha256": "sha256:…", "size_bytes": 812, "origin": "argv | declared | binding", "snapshot": "files/<sha256>", "redacted": false }
  ],
  "bindings_observed": {
    "generation.temperature": [
      { "value": 0.7, "source": { "type": "cli", "key": "--temperature" } },
      { "value": 0.0, "source": { "type": "config", "path": "configs/eval.yaml", "key": "sampling.temperature" } }
    ]
  },
  "artifacts": [ { "path": "outputs/results.json", "sha256": "sha256:…", "size_bytes": 20480 } ],
  "warnings": [ "binding generation.seed: config key not found" ]
}
```

### 5.1 Capture rules (D-18, D-20)

- R-01 The child process runs via `subprocess.Popen(argv, cwd=…, env=os.environ | {REPROLLM_RUN_ID, REPROLLM_RUN_DIR})`, no shell. Signals: SIGINT/SIGTERM are forwarded; the record is written with `status: interrupted`.
- R-02 `run.json` is written atomically (temp file + rename) **after** the child exits, and a minimal `run.json` with `status: running` is written before start so crashes leave evidence.
- R-03 Files: each argv token (and each `--k=v` value part) that resolves to an existing regular file within the repository root is hashed. Files ≤ 1 MiB and detected as text (UTF-8 decodable, no NUL bytes) are snapshotted to `files/<sha256>` after redaction; others get `snapshot: null`. Forbidden names (§16.4) are never snapshotted (`redacted: true`).
- R-04 Declared files (`execution.config_files`, `bindings.*.config` paths, prompt paths, `training.deepspeed.config`) are hashed with `origin: declared` even if not in argv.
- R-05 Dirty tree: `git diff` (tracked files) is saved to `patch.diff` after redaction; untracked files are counted, not captured.
- R-06 Environment: see §16.3.
- R-07 Hardware: `nvidia-smi --query-gpu=index,name,memory.total,uuid --format=csv,noheader,nounits` and `nvidia-smi --query-gpu=driver_version --format=csv,noheader`; CUDA driver max from `nvidia-smi` header line; absent binary → `source: unavailable`. GPU UUIDs are hashed.
- R-08 Scheduler: all `SLURM_*` variables except those matching secret patterns (values recorded; they are not secrets). `PBS_*`/`LSB_*` recorded likewise.
- R-09 Bindings: for each manifest/project-rule binding, observe every declared location (§15). All observations are recorded; comparison happens in audit.
- R-10 `cwd` is stored relative to the repository root; the record never contains absolute paths, hostnames, or usernames.
- R-11 `--capture-output` tees child stdout/stderr to `stdout.log`/`stderr.log` after redaction (line-buffered; redaction applied per line). Default off.
- R-12 `--no-snapshot` disables file snapshots (hashes still recorded).

---

## 6. Profile schema

pydantic model `Profile` (`reprollm/schemas/profile.py`). Built-ins: `src/reprollm/profiles/<name>.yaml`. User: `.reprollm/profiles/<name>.yaml` (same name overrides built-in).

```yaml
schema_version: 1
name: llm_judge                      # ^[a-z][a-z0-9_]{0,31}$
description: string
extends: [evaluation]                # multiple inheritance, left-to-right merge; cycles → exit 2
rules: [judge.model_declared, …]     # rule IDs; unknown → exit 2
required_fields: [models.judge.id, evaluation.judge.prompt_ref]   # used by `init` scaffolding only
severity_overrides: { gen.seed_declared: CRITICAL }
drift_overrides: { "evaluation.judge.*": HIGH }                  # §18
detect:
  imports: [string]                  # module names (top-level or dotted)
  dependencies: [string]             # distribution names in pyproject/requirements
  keywords: [string]                 # case-insensitive, word-boundary matches in README* text, config key names, dir/file names
  files: [string]                    # glob patterns
```

Merge semantics: `rules` = union; `required_fields` = union; `severity_overrides`/`drift_overrides` = child wins; `detect` = union. `core` is always included implicitly and MUST NOT be listed in `experiment.profiles` (validation error if it is).

### 6.1 Built-in profiles (Beta)

| Profile | extends | rules (in addition to inherited) | severity_overrides | required_fields |
|---|---|---|---|---|
| `core` | — | all `code.*`, `env.*`, `exec.*` (except none), `model.primary_declared`, `model.provider_known`, `model.revision_pinned`, `model.tokenizer_pinned`, `model.dtype_declared`, `dataset.revision_pinned`, `dataset.split_declared`, `dataset.local_files_hashed`, `prompt.file_exists`, `prompt.hashed`, `gen.backend_version_locked`, all `consistency.*`, all `project.*` | — | `project.name`, `models.primary.id` |
| `inference` | core | `gen.params_declared`, `gen.backend_declared`, `gen.backend_config_declared`, `gen.seed_declared`, `gen.stop_declared`, `model.chat_template_hashed`, `model.quantization_declared`, `prompt.declared`, `prompt.few_shot_declared` | `gen.params_declared: CRITICAL`, `gen.backend_declared: CRITICAL`, `model.quantization_declared: WARNING` | `inference.backend`, `generation.temperature`, `generation.max_tokens` |
| `evaluation` | inference | `dataset.declared`, `dataset.preprocessing_declared`, `dataset.sampling_seed_declared`, `dataset.subset_declared`, `eval.metrics_declared`, `eval.metric_implementation_referenced`, `eval.aggregation_declared`, `eval.repetitions_declared` | `dataset.declared: CRITICAL`, `dataset.revision_pinned: CRITICAL`, `dataset.sampling_seed_declared: CRITICAL`, `eval.metrics_declared: CRITICAL`, `exec.seed_declared: CRITICAL`, `gen.seed_declared: CRITICAL` | `datasets.eval.id`, `evaluation.metrics` |
| `llm_judge` | evaluation | `judge.model_declared`, `judge.prompt_declared`, `judge.prompt_hashed`, `judge.params_declared`, `judge.pinnability_recorded`, `judge.repetitions_declared` | — | `models.judge.id`, `prompts.judge.path`, `evaluation.judge.params.temperature` |
| `finetuning` | core | `model.adapter_declared`, `dataset.declared`, `dataset.preprocessing_declared`, `train.method_declared`, `train.hyperparameters_declared`, `train.optimizer_declared`, `train.precision_declared`, `train.lora_config_complete` | `exec.seed_declared: CRITICAL`, `dataset.declared: CRITICAL` | `training.method`, `training.learning_rate`, `datasets.train.id` |
| `safety` | evaluation | `eval.definitions_declared`, `eval.query_budget_declared` | `eval.definitions_declared: CRITICAL` | `evaluation.definitions.refusal` or `evaluation.definitions.asr` |
| `privacy` | core | `privacy.threat_model_declared`, `privacy.mechanism_declared`, `privacy.metrics_declared`, `privacy.attack_config_declared` | — | `privacy.threat_model`, `privacy.mechanism.name` |

Detection signals per profile are in §13.

---

## 7. Project rules schema — `.reprollm/project-rules.yaml`

```yaml
schema_version: 1
rules:
  - id: project.alpha                    # ^project\.[a-z][a-z0-9_]{0,47}$ ; unique
    field: custom.privacy_method.alpha   # manifest field path; MUST start with custom. or be a valid schema path
    severity: CRITICAL | WARNING | INFO
    reason: string                       # required, non-empty
    source: manual | discover
    candidate_id: string?                # when source == discover
    accepted_at: timestamp
    bindings: { cli: string?, config: string?, env: string? }?
ignored_candidates:
  - { candidate_id: string, ignored_at: timestamp, reason: string? }
```

Semantics: each entry generates a rule instance with `id`, `default_severity = severity`, `min_level = 1`, check = "field present and non-null in manifest"; with `bindings`, `consistency.custom_fields` additionally compares observed values at Level 2.

---

## 8. Config schema — `.reprollm/config.yaml`

```yaml
schema_version: 1
audit:
  fail_on: critical | warning | never        # default critical
  ignore:
    - { rule: code.no_untracked, reason: "generated notebooks" }   # reason required
  show_passed: false
run:
  env_capture: allowlist | all               # default allowlist
  capture_output: false
  snapshot_max_bytes: 1048576
  extra_env_allowlist: [string]              # additional exact names or prefixes ending with "_"
discover:
  enabled: false                             # must be true OR --experimental passed
  base_url_env: REPROLLM_LLM_BASE_URL
  api_key_env: REPROLLM_LLM_API_KEY
  model_env: REPROLLM_LLM_MODEL
  max_chars: 60000
  include: [string]?                         # extra globs
  exclude: [string]?
```

CLI flags override config; config overrides defaults.

---

## 9. Finding schema

```json
{
  "rule_id": "model.revision_pinned",
  "aliases": [],
  "category": "model",
  "severity": "CRITICAL | WARNING | INFO | PASS",
  "status": "fail | pass | suppressed | skipped",
  "level": 2,
  "message": "models.primary (Qwen/Qwen3-32B) has no resolved revision in reprollm.lock",
  "evidence": [
    { "kind": "field | file | git | env | lock | run | detection | http", "path": "reprollm.lock", "field": "models.primary.revision", "line": null, "value": null, "expected": "commit sha", "note": "confidence: unresolved (hf_api_forbidden)" }
  ],
  "fix_hint": "Run `reprollm lock` with network access, or set models.primary.revision to a commit sha.",
  "profile_origin": ["core"],
  "severity_origin": "default | profile:<name> | project_rule",
  "suppressed_reason": null
}
```

## 10. Audit report schema (`--format json`)

```json
{
  "schema_version": 1, "reprollm_version": "0.1.0", "generated_at": "…Z",
  "target": ".", "level": 1,
  "profiles": { "declared": ["inference", "evaluation"], "resolved": ["core", "inference", "evaluation"], "detected": [ { "profile": "llm_judge", "confidence": "medium", "evidence": [ { "kind": "detection", "path": "README.md", "line": 12, "note": "keyword 'judge'" } ] } ] },
  "documents": { "manifest": "sha256:… | null", "lock": "sha256:… | null", "runs": 3 },
  "summary": { "critical": 2, "warning": 5, "info": 3, "pass": 21, "suppressed": 1, "skipped": 4 },
  "findings": [ … Finding … ]
}
```

Ordering: `findings` sorted by (severity rank CRITICAL>WARNING>INFO>PASS, category order as in §0, rule_id). Deterministic.

---

## 11. Audit engine semantics

1. **Locate root** (§1). Load config (if any). Load manifest (if any) → validation errors exit 2.
2. **Determine level**: no manifest → 0; manifest → 1; lock or ≥1 run record → 2. `--level` may lower it.
3. **Resolve profiles**: `core` + declared (`--profiles` overrides declared) with inheritance closure. At Level 0, run detection and report as INFO only.
4. **Select rules**: union of resolved profiles' rules + project rules. Rules not selected are not executed and produce nothing.
5. **Execute**: for each selected rule with `min_level ≤ level`: if `applies(ctx)` is false → `status: skipped`; else `check(ctx)` returns zero or more findings; zero findings → synthesize one `PASS`.
6. **Severity**: a rule MAY emit a finding with a severity lower than its `default_severity` (e.g. `model.revision_pinned` for API providers); otherwise the finding carries `default_severity`. If the resolved profiles define a `severity_overrides` entry for the rule (most-derived profile wins), that value **replaces** the emitted severity. Project rules carry their own severity. Record `severity_origin`.
7. **Suppression**: `config.audit.ignore` by `rule_id` or alias → `status: suppressed`, severity `INFO`, keep original in `evidence[].note`.
8. **Report**: sort, summarize, emit. Exit code per §1.1 computed on non-suppressed `fail` findings.

`AuditContext` (`reprollm/core/context.py`) exposes: `root: Path`, `manifest: Manifest|None`, `lock: Lock|None`, `runs: list[RunRecord]`, `latest_run`, `git: GitInfo`, `fs: RepoScanner` (cached file listing respecting `.gitignore`, size caps), `detection: DetectionResult`, `project_rules`, `config`, `state: ExperimentState|None` (Level 2), `env: EnvInfo` (Level 0 rules only).

The `RepoScanner` MUST skip: `.git`, `.reprollm/runs`, `node_modules`, `__pycache__`, virtualenv dirs (`.venv`, `venv`, `env` containing `pyvenv.cfg`), files > 2 MiB, and anything matched by `.gitignore` (via `git ls-files --cached --others --exclude-standard` when inside git; fallback to walking with a built-in ignore list).

---

## 12. Rule catalog

Columns: default severity; `min_level`; `applies` condition; FAIL condition; sprint. `fix_hint` text is in the rule docstring and MUST be present. Rules marked **P1** may be deferred to post-Beta if M3 slips.

### 12.1 `code.*` (L0, M2)

| ID | Sev | applies | FAIL when |
|---|---|---|---|
| `code.git_repo` | CRITICAL | always | root is not inside a git work tree |
| `code.git_commit` | CRITICAL | git repo | `git rev-parse HEAD` fails (unborn) |
| `code.clean_tree` | WARNING | git repo | `git status --porcelain` lists modified/staged tracked files |
| `code.no_untracked` | WARNING | git repo | untracked, non-ignored files exist (count in evidence, first 10 paths) |
| `code.submodules_initialized` | WARNING | `.gitmodules` exists | any submodule path lacks a checked-out commit (`git submodule status` prefix `-`) |
| `code.remote_recorded` **P1** | INFO | git repo | no `origin` remote |

### 12.2 `env.*` (L0, M2)

| ID | Sev | applies | FAIL when |
|---|---|---|---|
| `env.dependency_manifest_present` | CRITICAL | always | none of `pyproject.toml` (with `[project]` or `[tool.poetry]`), `requirements*.txt`, `environment.yml`, `uv.lock`, `poetry.lock`, `Pipfile` exists |
| `env.lockfile_present` | WARNING | dependency manifest present | no `uv.lock` / `poetry.lock` / `Pipfile.lock` / `conda-lock.yml` and no `requirements*.txt` where every non-comment line uses `==` |
| `env.llm_critical_deps_pinned` | WARNING | any LLM-critical package (§4.4) appears in declarations **or** imports | for each such package, no declaration pins it exactly: pip-style `==`, conda-style `name=version` in `environment.yml` (single `=` with a full version), or presence in a lockfile; one finding per package. `pytorch` in conda counts as `torch`. |
| `env.python_version_declared` | WARNING | always | no `requires-python` in pyproject, no `.python-version`, no `python=` in environment.yml |
| `env.secret_files_ignored` | CRITICAL | always | any file matching the forbidden patterns of §16.4 (except the template names `.env.example`, `.env.sample`, `.env.template`) exists and is tracked or not ignored by git (`git check-ignore` false) |
| `env.reprollm_initialized` | INFO | level 0 only | `.reprollm/` or `reprollm.yaml` absent |

### 12.3 `exec.*` (M2–M5)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `exec.command_declared` | WARNING | 1 | manifest | `execution.command` absent |
| `exec.seed_declared` | WARNING | 1 | manifest | none of `execution.seed`, `generation.seed`, `training.seed` present |
| `exec.run_recorded` | INFO | 1 | manifest | no run records |
| `exec.profile_detection_mismatch` | INFO | 1 | manifest | a `high`-confidence detected profile is not declared, or a declared profile has no detection evidence |

### 12.4 `model.*` (M3 presence, M4 lock)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `model.primary_declared` | CRITICAL | 1 | manifest | `models.primary.id` absent |
| `model.provider_known` | WARNING | 1 | per model | provider is `other` |
| `model.revision_pinned` | CRITICAL | 2 | per model | HF: lock `revision.confidence != exact`; API: `pinnability == unpinnable` → rule emits WARNING, `snapshot_alias` → rule emits INFO (see §11 step 6); local: `config_sha256` absent |
| `model.tokenizer_pinned` | WARNING | 2 | per HF model | lock `tokenizer.revision.confidence != exact` |
| `model.chat_template_hashed` | WARNING | 2 | per HF/local model | lock `chat_template` missing, or `status ∈ {present, custom_file}` with `sha256.confidence != exact`. `status: absent` (repository has no chat template) is PASS with an evidence note. |
| `model.dtype_declared` | WARNING | 1 | per model, provider ∉ {openai, openrouter, anthropic} | `dtype` absent and `inference.dtype` absent |
| `model.quantization_declared` | INFO | 1 | per model, non-API | `quantization` absent and `inference.quantization` absent |
| `model.adapter_declared` | WARNING | 1 | detection found `peft` import or dependency | no model has `adapter` |
| `model.trust_remote_code_declared` **P1** | WARNING | 1 | scanner finds `trust_remote_code=True` in `*.py` | no model has `trust_remote_code: true` |

### 12.5 `dataset.*` (M3, M4)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `dataset.declared` | INFO | 1 | manifest | `datasets` empty |
| `dataset.revision_pinned` | WARNING | 2 | per HF dataset | lock `revision.confidence != exact` |
| `dataset.split_declared` | WARNING | 1 | per HF dataset | `split` absent |
| `dataset.subset_declared` **P1** | INFO | 1 | per HF dataset | `subset` absent |
| `dataset.preprocessing_declared` | WARNING | 1 | per dataset | `preprocessing` absent |
| `dataset.sampling_seed_declared` | WARNING | 1 | per dataset with `sampling.n` | `sampling.seed` absent |
| `dataset.local_files_hashed` | CRITICAL | 2 | per local dataset | lock `files` missing or any declared file lacks sha256 |

### 12.6 `gen.*` (M3, M4)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `gen.params_declared` | WARNING | 1 | manifest | any of `generation.temperature`, `top_p`, `max_tokens` absent (one finding listing missing) |
| `gen.seed_declared` | WARNING | 1 | `generation.do_sample == true` or `temperature > 0` | `generation.seed` absent |
| `gen.backend_declared` | WARNING | 1 | manifest | `inference.backend` absent |
| `gen.backend_version_locked` | WARNING | 2 | `inference.backend` declared, non-API | lock `inference.version.confidence != exact` |
| `gen.backend_config_declared` | WARNING | 1 | `inference.backend == vllm` | any of `dtype`, `tensor_parallel_size`, `quantization`, `gpu_memory_utilization` absent (one finding per field) |
| `gen.stop_declared` **P1** | INFO | 1 | manifest | `generation.stop` absent |

### 12.7 `prompt.*` (M3, M4)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `prompt.declared` | WARNING | 1 | manifest | `prompts` empty |
| `prompt.file_exists` | CRITICAL | 1 | per prompt with `path` | file missing |
| `prompt.hashed` | WARNING | 2 | per prompt | lock has no sha256 for the role |
| `prompt.few_shot_declared` **P1** | INFO | 1 | manifest | no prompt has `few_shot` |

### 12.8 `eval.*` (M3)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `eval.metrics_declared` | WARNING | 1 | manifest | `evaluation.metrics` empty |
| `eval.metric_implementation_referenced` | WARNING | 1 | per metric | `implementation` absent |
| `eval.aggregation_declared` | WARNING | 1 | metrics declared | `aggregation` absent |
| `eval.repetitions_declared` | WARNING | 1 | metrics declared | `repetitions` absent |
| `eval.definitions_declared` | WARNING | 1 | manifest | `evaluation.definitions` lacks both `refusal` and `asr` |
| `eval.query_budget_declared` | WARNING | 1 | manifest | `evaluation.query_budget` absent |

### 12.9 `judge.*` (M3, M4)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `judge.model_declared` | CRITICAL | 1 | manifest | `models[evaluation.judge.model_ref or "judge"]` absent |
| `judge.prompt_declared` | CRITICAL | 1 | manifest | `prompts[evaluation.judge.prompt_ref or "judge"]` absent |
| `judge.prompt_hashed` | WARNING | 2 | judge prompt declared | lock lacks sha256 for that role |
| `judge.params_declared` | CRITICAL | 1 | manifest | `evaluation.judge.params.temperature` or `.max_tokens` absent |
| `judge.pinnability_recorded` | WARNING | 2 | judge model declared | lock lacks `pinnability` for judge role |
| `judge.repetitions_declared` | WARNING | 1 | manifest | `evaluation.judge.repetitions` absent |

### 12.10 `train.*` (M3)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `train.method_declared` | WARNING | 1 | manifest | `training.method` absent |
| `train.hyperparameters_declared` | CRITICAL | 1 | manifest | any of `learning_rate`, `batch_size`, (`epochs` or `max_steps`) absent |
| `train.optimizer_declared` | WARNING | 1 | manifest | `optimizer` or `scheduler` absent |
| `train.precision_declared` | WARNING | 1 | manifest | `precision` absent |
| `train.lora_config_complete` | CRITICAL | 1 | `training.method ∈ {lora, qlora}` | no model adapter with `rank`, `alpha`, `target_modules` |

### 12.11 `privacy.*` (M3)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `privacy.threat_model_declared` | CRITICAL | 1 | manifest | `privacy.threat_model` absent |
| `privacy.mechanism_declared` | CRITICAL | 1 | manifest | `privacy.mechanism.name` absent or `params` empty |
| `privacy.metrics_declared` | WARNING | 1 | manifest | `privacy.metrics` empty |
| `privacy.attack_config_declared` | WARNING | 1 | `privacy.attack` present | `attack.method` absent or `query_budget` absent |

### 12.12 `consistency.*` (L2, M4–M6)

| ID | Sev | applies | FAIL when |
|---|---|---|---|
| `consistency.lock_fresh` | WARNING | lock | `lock.manifest_sha256 != sha256(manifest)` or `project_rules_sha256` mismatch |
| `consistency.file_hashes` | CRITICAL | lock | any file in `lock.prompts`/`lock.files` whose current working-tree sha256, or latest-run sha256, differs (one finding per file) |
| `consistency.generation_params` | CRITICAL | latest run has `bindings_observed` for `generation.*` | any observed value ≠ manifest value (normalized §15.2); evidence lists all sources |
| `consistency.model_identity` | CRITICAL | run observations for `models.*.id`/`revision` | observed ≠ lock/manifest |
| `consistency.env_vs_lock` | WARNING | lock and latest run | any LLM-critical package version in run ≠ lock (one finding per package) |
| `consistency.custom_fields` | (project rule) | project rules with bindings and run observations | observed ≠ manifest `custom.*` value |

### 12.13 `project.*` (M7)

Generated from `.reprollm/project-rules.yaml` (§7). FAIL when the `field` is absent/null in the manifest.

---

## 13. Deterministic profile detection (M2)

`reprollm/profiles/detect.py`. Input: `RepoScanner`. Output `DetectionResult`: `{profiles: [{profile, confidence: high|medium|low, evidence: [Evidence]}], hints: {providers: [...], hf_ids: [{value, path, line}], trust_remote_code: bool}}`.

Signals (Level 1 = deterministic, Level 2 = heuristic):

| Signal | Source | Profile / hint | Confidence |
|---|---|---|---|
| import `peft`, `trl`; `from transformers import Trainer|Seq2SeqTrainer|TrainingArguments`; import `deepspeed` | AST | `finetuning` (+ hint adapter) | high |
| import `accelerate` | AST | `finetuning` | medium |
| import `vllm`, `sglang` | AST | `inference`; hint backend | high |
| import `openai`, `anthropic` | AST | hint provider | — |
| import `lm_eval`, `lighteval`, `inspect_ai`, `evaluate` | AST | `evaluation` | high |
| import `datasets` | AST | hint datasets | — |
| distribution names above in pyproject/requirements | deps | same profile | medium |
| string constants passed to `from_pretrained(`, `LLM(model=`, `AutoTokenizer.from_pretrained(` matching `^[\w.-]+/[\w.-]+$` | AST | hint `hf_ids` | — |
| keyword `trust_remote_code=True` | AST | hint | — |
| keywords `judge`, `llm-as-a-judge`, `llm_judge`, `rubric`, `grader` | README*, config keys, dir/file names | `llm_judge` | medium if ≥2 hits else low |
| `jailbreak`, `attack success rate`, `asr`, `refusal`, `harmbench`, `advbench`, `red team`, `red-team` | same | `safety` | same |
| `differential privacy`, `epsilon`, `membership inference`, `threat model`, `privacy budget`, `dp-sgd`, `dp_sgd` | same | `privacy` | same |
| `lora`, `fine-tun`, `finetun`, `sft`, `dpo`, `rlhf` | same | `finetuning` | same |
| `mmlu`, `gsm8k`, `benchmark`, `accuracy`, dir `eval`/`evaluation` | same | `evaluation` | same |
| `retriev`, `rag`, `vector store`, `faiss`, `chroma` | same | `rag` (report only; not shipped) | same |
| `agent`, `tool call`, `tool_call`, `function calling` | same | `agent` (report only) | same |

Keyword matching is case-insensitive and **word-boundary based** (`\bkeyword\b`, with `-`/`_`/space treated as equivalent separators), never bare substring: "manager" MUST NOT match `agent`, "storage" MUST NOT match `rag`. Only README text, configuration **key names** (not values), directory names, and file stems are scanned. Highest confidence per profile wins. `init` includes `high` and `medium`. AST scanning caps: ≤ 500 `.py` files, ≤ 512 KiB each; files beyond caps are skipped with a warning in `-v`.

---

## 14. Integrations contract

`reprollm/integrations/base.py`:

```python
class Integration(Protocol):
    name: str  # huggingface | vllm | openai | peft | transformers

    def detect(self, scanner: RepoScanner) -> list[Evidence]: ...  # optional
    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client
    ) -> LockFragment: ...  # optional
    def capture(self) -> dict: ...  # runtime facts, e.g. package versions; optional
```

| Integration | detect | resolve | capture |
|---|---|---|---|
| `huggingface` | HF ids, `datasets` import | §4.3 models/datasets | — |
| `transformers` | Trainer imports, `from_pretrained` | — | `transformers`, `tokenizers`, `accelerate` versions |
| `vllm` | import | `inference.version` | `vllm` version, `VLLM_*` env (allowlisted) |
| `openai` | import; `base_url` strings containing `openrouter.ai` → provider hint openrouter | pinnability, optional `--verify-api` | `openai` version |
| `peft` | import | adapter repo resolution | `peft` version |

Integrations MUST NOT import their target libraries.

---

## 15. Bindings

### 15.1 Observation (run time)

| Location | Observation |
|---|---|
| `cli: "--flag"` | scan argv for `--flag VALUE` (next token not starting with `-`) or `--flag=VALUE`; repeated → last wins but all recorded; present without value → `true`; absent → no observation |
| `config: "path:dotted.key"` | load YAML/JSON/TOML by extension; traverse dotted key (list index as integer segment); missing → `warnings[]` entry, no observation |
| `env: "VAR"` | `os.environ[VAR]`; if `VAR` matches secret-name rules (§16.1) the binding is refused with a warning |

### 15.2 Normalization for comparison

Values are normalized before comparison: strings that parse as int/float → numbers (`"0"` == `0` == `0.0`); `"true"/"false"` (case-insensitive) → booleans; other strings compared exactly; lists element-wise. Floats compared with `math.isclose(rel_tol=1e-9)`.

---

## 16. Secret redaction policy (D-19, D-20) — NORMATIVE

Module `reprollm/core/redaction.py`. Applies to: env capture, argv, file snapshots, `patch.diff`, stdout/stderr logs, discover payloads, export output.

### 16.1 Environment variable **name** rules

Uppercase the name, split on `_`. The variable is a **secret name** if any segment ∈ `{KEY, TOKEN, SECRET, PASSWORD, PASSWD, CREDENTIAL, CREDENTIALS, AUTH, PRIVATE, COOKIE, SESSION}` **or** the full name ∈ `KNOWN_SECRET_NAMES` = `{HF_TOKEN, HUGGING_FACE_HUB_TOKEN, HUGGINGFACEHUB_API_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, WANDB_API_KEY, GITHUB_TOKEN, GH_TOKEN, DATABASE_URL, AZURE_OPENAI_API_KEY, GOOGLE_API_KEY, GEMINI_API_KEY}`.
Secret names are recorded as `{ "present": true }` only.
Required negative cases: `MAX_TOKENS`, `TOKENIZERS_PARALLELISM`, `CUDA_VISIBLE_DEVICES`, `NCCL_SOCKET_IFNAME` are **not** secret names. Accepted false positives: `SSH_AUTH_SOCK`, `KEY_FRAMES`.

### 16.2 **Value** patterns (applied to all captured text)

| Kind | Regex (Python `re`) |
|---|---|
| openai | `\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b` |
| huggingface | `\bhf_[A-Za-z0-9]{20,}\b` |
| github | `\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b` |
| aws | `\bAKIA[0-9A-Z]{16}\b` |
| slack | `\bxox[baprs]-[A-Za-z0-9-]{10,}\b` |
| jwt | `\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b` |
| pem | `-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----` |
| url_cred | `(?<=://)[^/\s:@]+:[^/\s@]+(?=@)` |
| generic_kv | `(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd)\b\s*[:=]\s*["']?([^\s"']{8,})` (redact group 2 only) |

Replacement: `<REDACTED:kind>`. Counting redactions per artifact is recorded (`command.redactions`, `files[].redacted`).

### 16.3 Environment capture policy

Default `allowlist`: record **values** only for names that start with one of `CUDA_, NCCL_, TORCH_, PYTORCH_, OMP_, MKL_, TRANSFORMERS_, HF_HOME, HF_HUB_OFFLINE, HF_HUB_DISABLE, VLLM_, SLURM_, PBS_, LSB_, PYTHON, VIRTUAL_ENV, CONDA_, TOKENIZERS_PARALLELISM, WANDB_MODE, LD_LIBRARY_PATH, PATH, LANG, LC_, TZ` plus `config.run.extra_env_allowlist`. Name rules (§16.1) take precedence over the allowlist (`HF_TOKEN` is a secret even though it starts with `HF_`). Everything else is **omitted**. With `--env-capture all`: every name is recorded; secret names as `{present: true}`; other values pass through §16.2.

### 16.4 Forbidden file patterns

Never snapshot or send: `.env`, `.env.*`, `*.pem`, `*.key`, `id_rsa*`, `id_ed25519*`, `credentials*`, `*.p12`, `*.pfx`, `*.jks`, `*_rsa`, `.netrc`, `.npmrc`, `.pypirc`. Their hashes MAY be recorded with `redacted: true`. The template names `.env.example`, `.env.sample`, `.env.template` are exempt from this list (they are still passed through §16.2 value redaction).

### 16.5 Testing requirements

- `tests/fixtures/secrets/positive.txt`: ≥ 3 samples per value kind; all MUST be redacted.
- `tests/fixtures/secrets/negative.txt`: benign strings including `MAX_TOKENS=2048`, `TOKENIZERS_PARALLELISM=false`, model ids like `Qwen/Qwen3-32B`, commit shas, `sk-` followed by < 16 chars; none may be altered.
- `tests/fixtures/secrets/env_cases.yaml`: name → expected classification.
- Branch coverage of `core/redaction.py` MUST be 100 % (enforced in CI via `--cov-fail-under` on that module).

---

## 17. ExperimentState and precedence (M6)

`reprollm/schemas/state.py`. A tree mirroring manifest sections plus `code`, `environment`, `hardware`, `files`. Every leaf is:

```python
class Leaf(BaseModel):
    value: Any
    source: Literal["manifest", "lock", "run", "working_tree", "default"]
    detail: (
        str | None
    )  # e.g. "cli:--temperature", "config:configs/eval.yaml:sampling.temperature", "hf_api"
    confidence: Literal["exact", "declared", "unresolved", "observed"]
```

Projections: `State.from_manifest(m)`, `State.from_lock(l)`, `State.from_run(r)`. `State.merge(manifest, lock, run)` applies precedence `run(cli) > run(config) > run(env) > lock > manifest > default` per leaf and keeps all alternatives in `leaf.alternatives` for consistency findings. `State.flatten() -> dict[str, Leaf]` with paths like `models.primary.revision`, `environment.packages.torch`, `files.configs/eval.yaml.sha256`.

---

## 18. Diff semantics (M6)

Inputs: two of {run_id, path to `run.json`, path to `reprollm.lock`}. Each is projected to a State (`run` uses its embedded lock and manifest snapshots).

### 18.1 Algorithm

Flatten both; for each path in the union: `same | changed | added | removed`. Severity from `drift_severity.yaml`: first matching pattern in file order wins; profile `drift_overrides` are prepended. Package versions (`environment.packages.*`, `inference.version`) are compared with `packaging.version`: differing major/minor → the listed severity; differing patch only → one level lower (min LOW). `code.commit` changed is reported as `MEDIUM` with note "code changed" unless `code.dirty` is true on either side (→ HIGH). Paths matching no pattern → `MEDIUM`.

### 18.2 `drift_severity.yaml` (initial contents)

```yaml
schema_version: 1
default: MEDIUM
rules:
  - { path: "models.*.id",                         severity: HIGH }
  - { path: "models.*.revision",                   severity: HIGH }
  - { path: "models.*.tokenizer.revision",         severity: HIGH }
  - { path: "models.*.chat_template.sha256",       severity: HIGH }
  - { path: "models.*.quantization",               severity: HIGH }
  - { path: "models.*.adapter.*",                  severity: HIGH }
  - { path: "models.*.dtype",                      severity: MEDIUM }
  - { path: "models.*.pinnability",                severity: MEDIUM }
  - { path: "datasets.*.id",                       severity: HIGH }
  - { path: "datasets.*.revision",                 severity: HIGH }
  - { path: "datasets.*.subset",                   severity: HIGH }
  - { path: "datasets.*.split",                    severity: HIGH }
  - { path: "datasets.*.sampling.*",               severity: HIGH }
  - { path: "datasets.*.preprocessing.*",          severity: MEDIUM_HIGH }
  - { path: "prompts.*.sha256",                    severity: HIGH }
  - { path: "prompts.*.text_sha256",               severity: HIGH }
  - { path: "generation.*",                        severity: HIGH }
  - { path: "inference.backend",                   severity: HIGH }
  - { path: "inference.version",                   severity: MEDIUM_HIGH }
  - { path: "inference.quantization",              severity: HIGH }
  - { path: "inference.dtype",                     severity: MEDIUM }
  - { path: "inference.tensor_parallel_size",      severity: MEDIUM }
  - { path: "inference.max_model_len",             severity: MEDIUM }
  - { path: "inference.gpu_memory_utilization",    severity: LOW }
  - { path: "training.*",                          severity: HIGH }
  - { path: "evaluation.judge.*",                  severity: HIGH }
  - { path: "evaluation.metrics",                  severity: HIGH }
  - { path: "evaluation.definitions.*",            severity: HIGH }
  - { path: "evaluation.*",                        severity: MEDIUM_HIGH }
  - { path: "privacy.*",                           severity: HIGH }
  - { path: "custom.*",                            severity: MEDIUM }
  - { path: "files.*.sha256",                      severity: HIGH }
  - { path: "environment.packages.torch",          severity: MEDIUM_HIGH }
  - { path: "environment.packages.transformers",   severity: MEDIUM_HIGH }
  - { path: "environment.packages.vllm",           severity: MEDIUM_HIGH }
  - { path: "environment.packages.tokenizers",     severity: MEDIUM_HIGH }
  - { path: "environment.packages.*",              severity: MEDIUM }
  - { path: "environment.python",                  severity: MEDIUM }
  - { path: "environment.platform",                severity: MEDIUM }
  - { path: "hardware.gpus.*.name",                severity: MEDIUM }
  - { path: "hardware.driver",                     severity: LOW }
  - { path: "hardware.cuda_driver_max",            severity: MEDIUM }
  - { path: "code.commit",                         severity: MEDIUM }
  - { path: "code.dirty",                          severity: HIGH }
  - { path: "code.branch",                         severity: LOW }
  - { path: "command.argv",                        severity: MEDIUM }
  - { path: "run_id",                              severity: NONE }
  - { path: "started_at",                          severity: NONE }
  - { path: "ended_at",                            severity: NONE }
  - { path: "duration_seconds",                    severity: NONE }
  - { path: "environment.hostname_sha256",         severity: NONE }
```

### 18.3 Diff report JSON

```json
{
  "schema_version": 1, "reprollm_version": "0.4.0",
  "a": { "kind": "run | lock", "ref": "20261005T093000Z-a1b2c3" }, "b": { … },
  "summary": { "highest": "HIGH", "counts": { "HIGH": 2, "MEDIUM_HIGH": 1, "MEDIUM": 0, "LOW": 3, "NONE": 4 }, "same": 57 },
  "changes": [ { "path": "models.primary.revision", "status": "changed", "a": "abc…", "b": "def…", "severity": "HIGH", "note": null } ]
}
```

Text output groups by top-level section, shows `A → B` per change, severity tag, and ends with a one-line verdict: `Highest drift: HIGH (2 changes). These runs are not directly comparable.` when HIGH exists.

---

## 19. Export (M7)

`reprollm export` renders `REPRODUCIBILITY.md` from `templates/REPRODUCIBILITY.md.j2` using the merged State (manifest + latest lock + selected/latest run). Sections in order: Title & generated-by line; **Experiment identity** (models table: role, provider, id, revision/pinnability, tokenizer rev, chat-template hash; datasets table; prompts table with hashes; generation parameters; inference backend/version); **Code** (commit, branch, dirty, remote); **Environment** (python, LLM-critical packages, GPU names/driver); **Execution** (command, run id, timestamps, duration, exit code); **Audit summary** (counts by severity; list CRITICAL and WARNING messages); **Known limitations** (every `unresolved`, `unpinnable`, `not_computed`, and unresolved binding); footer with `reprollm` version and schema versions.
Requirements: deterministic ordering; relative paths only; redaction applied; if no run exists the Execution section states so; if no lock exists the identity table marks revisions as `not locked`.

---

## 20. Discover (M7, experimental)

### 20.1 Gate

Requires `--experimental` **or** `config.discover.enabled: true`. Requires `REPROLLM_LLM_BASE_URL`, `REPROLLM_LLM_API_KEY`, `REPROLLM_LLM_MODEL` (names configurable). `--paper` → exit 2: "Paper analysis is not available in Beta."

### 20.2 Collection (`collector.py`)

Include: `README*`, top-level `*.md`, `*.yaml|*.yml|*.json|*.toml` ≤ 64 KiB (excluding lockfiles and `.reprollm/`), AST-extracted snippets of `argparse.add_argument(...)`, `@dataclass` classes, `hydra`/`omegaconf` config classes, the repository tree (paths only, ≤ 2000 entries). Exclude: forbidden files (§16.4), files > 64 KiB, binary files, anything under `data/`, `datasets/`, `checkpoints/`, `outputs/`, `wandb/`. All text passes §16.2 redaction; any file whose redaction count > 0 is **dropped** and listed. Total ≤ `max_chars` (default 60 000); truncated files listed. `--dry-run` prints the file list and byte counts, sends nothing. Without `--yes`, the file list is printed and the user must confirm.

### 20.3 Request

Single chat-completion request (OpenAI-compatible `POST {base_url}/chat/completions`) with a packaged system prompt (`discover/prompts/system.md`) demanding JSON only, and `response_format: {type: json_object}` when supported. Temperature 0. Timeout 120 s. Invalid JSON → one retry with the validation error appended; second failure → raw response saved to `.reprollm/discover/<ts>.raw.txt`, exit 3.

### 20.4 Output schema — `.reprollm/discover/<ts>.json`

```json
{
  "schema_version": 1, "reprollm_version": "0.5.0a1", "generated_at": "…Z",
  "model": "<REPROLLM_LLM_MODEL>", "input_files": ["README.md", "configs/privacy.yaml"], "dropped_files": [], "truncated_files": [],
  "candidates": [
    {
      "id": "c-3f9a1b",
      "kind": "parameter | dependency | artifact | profile",
      "name": "alpha",
      "suggested_field": "custom.privacy_method.alpha",
      "suggested_severity": "CRITICAL | WARNING | INFO",
      "confidence": "high | medium | low",
      "rationale": "controls noise scale; results not comparable across values",
      "evidence": [ { "kind": "file", "path": "configs/privacy.yaml", "line": 12, "snippet": "alpha: 0.25" } ],
      "suggested_bindings": { "config": "configs/privacy.yaml:method.alpha", "cli": "--alpha" }
    }
  ]
}
```

`id = "c-" + sha256(kind + name + first evidence path)[:6]`. Evidence paths not present in `input_files` are dropped and the candidate confidence lowered to `low`.

### 20.5 Acceptance

`reprollm rules accept c-3f9a1b [--severity S] [--field F]` appends to `project-rules.yaml` (`source: discover`, `candidate_id`), copying bindings. `rules ignore` records the id in `ignored_candidates` so re-running discover marks it `ignored`. `rules add` creates a manual rule. `rules list` shows active rules and pending candidates from the latest discover file.

---

## 21. Text output conventions

```text
ReproLLM audit · level 1 · profiles: core, inference, evaluation

CRITICAL (2)
  ✖ model.revision_pinned      models.primary (Qwen/Qwen3-32B) has no resolved revision in reprollm.lock
      lock: models.primary.revision → confidence: unresolved (hf_api_forbidden)
      fix: run `reprollm lock` with network access, or set models.primary.revision to a commit sha
  ✖ judge.params_declared      evaluation.judge.params.temperature is missing
      ...

WARNING (5)
  ...

INFO (3)
  ...

21 passed · 1 suppressed · 4 skipped        (use --show-passed / --show-skipped)
Result: FAIL (2 critical)
```

Symbols: `✖` CRITICAL, `▲` WARNING, `ℹ` INFO, `✔` PASS, `–` suppressed/skipped. With `--no-color`/non-TTY, symbols remain ASCII-safe alternatives (`X`, `!`, `i`, `+`, `-`).

---

## 22. Testing requirements

- T-01 Unit tests per module; every rule has ≥ 1 PASS and ≥ 1 FAIL test using minimal in-memory manifests or fixture repos.
- T-02 Golden fixture repos in `tests/fixtures/repos/` (see M1). Each has `expected/audit_L0.json`, later `audit_L1.json`, `lock.yaml`, `audit_L2.json`, `diff.json`. Snapshot comparison ignores `generated_at`, `reprollm_version`, `resolved_at`, `observed_at`.
- T-03 Fixture git repos are materialized in a temp dir at test time by `tests/conftest.py::materialize_repo(name)` with `GIT_AUTHOR_NAME=ReproLLM Test`, `GIT_AUTHOR_EMAIL=test@reprollm.dev`, `GIT_AUTHOR_DATE=GIT_COMMITTER_DATE=2026-01-01T00:00:00Z`, so commit SHAs are deterministic across machines.
- T-04 No network: `respx` mocks all `httpx` calls; a session-scoped autouse fixture fails any unmocked request. Recorded Hub responses live in `tests/fixtures/hf_api/`.
- T-05 `nvidia-smi` and `git` are invoked through `reprollm/core/proc.py::run_cmd`, which tests monkeypatch; fixtures provide canned outputs (`tests/fixtures/nvidia_smi/*.txt`).
- T-06 Redaction: §16.5.
- T-07 CLI tests via `typer.testing.CliRunner`; JSON outputs validated against exported JSON Schemas.
- T-08 Coverage gate: ≥ 85 % overall from M3 onward; `core/redaction.py` 100 % branches.
- T-09 CI matrix: ubuntu-latest (py3.10, 3.11, 3.12), macos-latest (3.12), windows-latest (3.12, core unit tests only via marker `-m "not linux_only"`).

---

## 23. JSON Schema export

`reprollm schema export --out schemas/` writes: `manifest.schema.json`, `lock.schema.json`, `run_record.schema.json`, `profile.schema.json`, `project_rules.schema.json`, `config.schema.json`, `audit_report.schema.json`, `diff_report.schema.json`, `discover_candidates.schema.json`. CI fails if the committed `schemas/` differ from a fresh export.
