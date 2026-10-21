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
- Every persisted document carries integer `schema_version` and `reprollm_version: "<semver>"`. Starting with ReproLLM 0.7.0, new run records use version 2; all other document schemas remain version 1. Run readers accept legacy version 1 and current version 2; unknown newer versions require an upgrade.
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
| `reprollm init [PATH] [--force] [--interactive] [--profiles a,b] [--task NAME]... [--list-tasks]` | create `reprollm.yaml` + `.reprollm/`; list task candidates without writes | M2 / UX2-T01 |
| `reprollm audit [PATH] [--format text\|json] [--output FILE] [--fail-on critical\|warning\|never] [--level 0\|1\|2\|auto] [--profiles a,b] [--show-passed] [--show-skipped] [--details]` | run rules | M2–M6 |
| `reprollm profiles list \| show NAME` | inspect profiles | M2 |
| `reprollm lock [PATH] [--offline] [--check] [--verify-api] [--hash-large-files]` | resolve and write `reprollm.lock` | M4 |
| `reprollm run [--name NAME] [--capture-output] [--env-capture allowlist\|all] [--no-snapshot] [--cwd DIR] [--dry-run] -- CMD…` | execute and record, or preview capture without execution | M5 / UX3-T03 |
| `reprollm runs list [--json] [--name TEXT] [--status running\|completed\|failed\|interrupted] [--outcome success\|failure] [--limit N]` / `runs show RUN_ID [--json]` | inspect and filter run records | M5 / UX3-T04 |
| `reprollm diff A B [--format text\|json] [--min-severity LOW\|MEDIUM\|MEDIUM_HIGH\|HIGH] [--fail-on SEV]` / `diff --latest-successful [--name TEXT] [same options]` | semantic drift | M6 / UX3-T04 |
| `reprollm export [--run RUN_ID] [--output PATH] [--template default]` | write `REPRODUCIBILITY.md` | M7 |
| `reprollm discover [PATH] --experimental [--yes] [--dry-run] [--show-content] [--max-chars N] [--paper FILE]` | LLM-assisted candidate discovery | M7 |
| `reprollm rules list [--json] [--candidates]` | inspect active rules, latest candidates and recovery-copy state | M7 / UX2-T06 |
| `reprollm rules show ID` | inspect an active rule, latest candidate or recovery archive without writes | UX2-T06 |
| `reprollm rules accept CANDIDATE_ID [--severity S] [--field F]` | accept a latest discovery candidate | M7 |
| `reprollm rules ignore CANDIDATE_ID [--reason R]` | record an ignored, inactive candidate | M7 / UX2-T06 |
| `reprollm rules add --field F --severity S --reason R [--id ID] [--cli FLAG] [--config P:K] [--env VAR]` | add a manual project rule | M7 |
| `reprollm rules remove RULE_ID --reason TEXT` | save an immutable recovery copy, then deactivate the rule | UX2-T06 |
| `reprollm rules restore ARCHIVE_ID` | restore the complete original rule when its identifiers are inactive | UX2-T06 |

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

Lifecycle recovery copies live under `.reprollm/rule-archives/`; their
`ARCHIVE_DIR` constant belongs to `reprollm/core/rule_lifecycle.py`.

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

Before writing any owned artifact, validate the final rendered YAML in memory
with the same parser and Manifest model as `load_manifest` (R01). A legal directory
basename becomes `project.name` with string semantics, including YAML implicit
scalars such as `123` or `true`. If the basename fails the unchanged project-name
schema or existing secret/machine-identity checks, use the fixed name `experiment`
and print safe guidance to edit `project.name` in `reprollm.yaml`.

Refuse existing `reprollm.yaml` without `--force`. Owned output nodes
(`reprollm.yaml`, `.reprollm`, `.reprollm/config.yaml`, `.reprollm/project-rules.yaml`)
must be regular files or, for `.reprollm`, a directory; reject symlinks (including
dangling ones) before write-mode detection and again at the writer boundary.
Prepare and sync a temporary manifest in the project directory, create only
missing auxiliary files, then atomically replace the manifest last. Preserve
existing auxiliary bytes and permissions; preserve the old manifest permission bits
on successful `--force`. Validation and ordinary write/replace failures preserve
existing artifact bytes and permissions, remove only artifacts created by that
invocation, and remove its new auxiliary directory only when empty. Diagnostics
identify safe owned locations and corrective actions without echoing YAML values
or OS absolute paths. This guarantees ordinary-exception preservation, not a
power-loss transaction across multiple files or concurrent-writer isolation.

Task inventory and experiment selection are separate (UX2-T01, approved 2026-10-02).
`init --list-tasks` lists the complete safe deterministic inventory, sorted and
unique, one name per line, without writes even if a manifest already exists.
It rejects combinations with `--interactive`, `--task`, `--force` or `--profiles`.
Ordinary init leaves `evaluation.metrics` empty unless the author selects exact
names using repeatable `--task NAME` or interactive task selection. Deduplicate
and sort selections; unknown/unsafe names and selectors incompatible with the
selected profiles are usage errors before writes. Candidates are nonempty,
single-line strings without control/format/line-separator characters or existing
secret/machine-identity redaction triggers; preserve remaining Unicode exactly.
Print detected/selected profiles and candidate/selection counts with review and
listing guidance. Interactive init offers profile selection (the detected or
explicit list as its visible default), then exact task names one per prompt
(empty ends selection), then required fields. Noninteractive init never prompts.

When the §6.1 explicit shipped `judge_only` exception applies, omit only
`models.primary.id` from the required-field union. Keep detected model candidates
as unassigned comments, without inserting one into the active model block.
Keep judge fields and every other selected required field. Apply normal init
behavior whenever the exception does not apply. Judge max_tokens is a numeric
interactive field; metric task selection follows the same policy above.

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

`provider: other` with a qualifying `endpoint.base_url` declares an opaque model
API and follows the existing API pinnability policy for rule applicability.
The original endpoint must be a nonempty HTTP(S) string parsed by `urlsplit`,
with a hostname and valid optional port, no whitespace, Unicode Cc/Cf/Zl/Zp,
backslash, fragment or userinfo, and zero existing secret/machine-identity
privacy replacements. Test the original string before normalization; ordinary
safe paths and queries are allowed. Invalid or absent endpoints retain the
existing unsupported-other rule behavior without a new schema validation error.

Preserve `provider: other` and its unsupported-provider WARNING; never infer
provider identity from `inference.backend` or another role. Level 1 presence
rules use each role's manifest provider/endpoint even in a Level 2 audit.
Level 2 `model.revision_pinned` uses each role's effective provider/endpoint
in merged State and retains source alternatives and existing consistency checks.
Unpinnable aliases yield WARNING and dated snapshot aliases INFO; neither proves
an immutable revision. Skip unobservable dtype/quantization presence demands
for these API declarations. Keep unsupported `other` without a qualifying
endpoint unchanged. This classification makes no request and adds no credential
lookup, provider enum, endpoint lock field or verification transport. Existing
API resolution still records null/unresolved revision; `--verify-api` for `other`
remains unavailable. Offline lock creates no HTTP client; mixed online HF
resolution remains permitted. Changed endpoint declarations still stale the
manifest hash (`consistency.lock_fresh`: WARNING); identity conflicts remain
CRITICAL under their existing rules.

Lock environment Python/packages are recorder metadata observed during lock
resolution; platform/GPU describe that recorder's visible host. Metadata-based
inference/metric versions also come from the resolving recorder, never a probed
future child. These observations preserve their existing confidence semantics
and do not attest to a future experiment's installed environment. The source
registry for recognized producers is separate from run producer recognition.

### 4.4 LLM-critical package list

`torch, transformers, tokenizers, datasets, accelerate, peft, trl, vllm, sglang, openai, anthropic, numpy, safetensors, deepspeed, flash_attn, xformers, bitsandbytes, sentencepiece, evaluate, lm_eval, lighteval, inspect_ai`. Constant `LLM_CRITICAL_PACKAGES` in `reprollm/core/envinfo.py`. Versions via `importlib.metadata`; never `import`.

### 4.5 Staleness

`lock --check` exits 1 if the lock is missing, `manifest_sha256` differs from the current manifest, or `project_rules_sha256` differs. Rule `consistency.lock_fresh` reports the same at audit Level 2.

### 4.6 Safe new writes

Before creating a temporary lock file, check both the final persisted object and
its complete serialized YAML. Apply §16.2 value patterns to mapping keys and
values, including nested mappings/lists and provenance notes. Retain raw mapping
key context for scalar leaves: the six `generic_kv` key aliases and its minimum
eight-character value length also apply to structured values. This is contextual
application of the existing policy, not recognition of arbitrary secret formats.

Serialized YAML must decode to that checked object; comments and scalar text are
also checked. Mapping-key syntax must not be mistaken for a following scalar
value across newlines, and safety inspection never changes emitted bytes.

Reject an unsafe new lock with `UserError` (exit 2), preserving any existing lock
byte for byte. Also reject absolute paths (including local `file://` URIs) and
current machine/user identity under
the existing run privacy policy; use project-relative paths. Do not silently
replace executable parameters with redaction markers. The diagnostic names
`reprollm.yaml`, withholds unsafe values, and directs credentials to environment
variables or another secure source read by the child. Manifest interpolation is
not implied. Hash-only prompt bodies are not persisted and are not inspected by
this boundary. Ordinary model IDs, HTTPS URLs, relative paths, globs, closing
tokens and `max_tokens` remain valid. Old locks are not rewritten, and §4.5
freshness checks remain unchanged.

---

## 5. Run record schema — `.reprollm/runs/<run_id>/run.json`

pydantic model `RunRecord` (`reprollm/schemas/run_record.py`).

R04-S version transition: the 0.6.2 compatibility bridge writes/reads run
schema 1 and rejects newer versions with upgrade guidance. Starting with 0.7.0,
new run records use run-specific schema 2; readers accept schemas 1 and 2 and
reject unknown newer versions before model validation. Other persisted
document versions remain 1. No legacy record is rewritten automatically.
The released 0.6.1 diagnostic limitations are documented separately; a later
reader cannot retroactively change that binary. Upgrade it to at least the
0.6.2 bridge before exchanging schema-2 records.

Schema 2 adds a required `input_capture` object (including running/fallback
records). Its `baseline_phase` is `pre_child`, `check_phase` is `post_child`,
and `consumption` is `unverified`. `checks` is sorted by relative `path` and
contains the frozen input candidates: manifest, lock, declared files and
eligible argv files. Each entry contains `path`, `origin`, `before`, `after`
and `change`. An input fingerprint contains `availability` (`present`,
`missing`, `unavailable`), `sha256` and `size_bytes`; the last two are required
only when present. `change` is `unchanged`, `changed`, `removed`, `created` or
`unknown`. A missing fingerprint is not an unreadable/unsafe fingerprint.
While the child is running or a final recheck fails, after availability and
change remain unavailable/unknown. Matching fingerprints mean unchanged
recorded bytes, not proof the child consumed the file. No after-only file is
inserted into pre-child `files`, document references or config observations.
For schema 1, no non-null `input_capture` is accepted; its input phases and
consumption remain unknown/unverified. The producer version never proves
what bytes an old child consumed.


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
- R-03 Files: in schema 2, before child start, each argv token (and each `--k=v` value part) that resolves to an existing regular file within the repository root is hashed. Files ≤ 1 MiB and detected as text (UTF-8 decodable, no NUL bytes) are snapshotted to `files/<sha256>` after redaction; others get `snapshot: null`. Forbidden names (§16.4) are never snapshotted (`redacted: true`).
- R-04 In schema 2, declared files are captured before child start (`execution.config_files`, `bindings.*.config` paths, prompt paths, `training.deepspeed.config`) are hashed with `origin: declared` even if not in argv.
- R-05 Dirty tree: `git diff` (tracked files) is saved to `patch.diff` after redaction; untracked files are counted, not captured.
- R-06 Environment: see §16.3. Python/packages describe the recorder interpreter after child completion. OS/platform/hardware describe the recorder host at collector time; the hostname hash describes its pre-child hostname copy. Recorded env/scheduler values are the recorder's pre-child inherited baseline; they do not describe child-internal changes. Lock environment describes the lock recorder during resolution. All child environment verification remains unverified, including when argv names the same executable. Sources are recovered only from explicitly confirmed producer contracts; unrecognized producers have unknown context. Empty recorder packages never prove an empty child installation.
- R-07 Hardware: `nvidia-smi --query-gpu=index,name,memory.total,uuid --format=csv,noheader,nounits` and `nvidia-smi --query-gpu=driver_version --format=csv,noheader`; CUDA driver max from `nvidia-smi` header line; absent binary → `source: unavailable`. GPU UUIDs are hashed.
- R-08 Scheduler: all `SLURM_*` variables except those matching secret patterns (values recorded; they are not secrets). `PBS_*`/`LSB_*` recorded likewise.
- R-09 Bindings: for each pre-child manifest/project-rule binding, observe every declared location before launch (§15). CLI and env describe the passed/inherited baseline, and config observations come from the same bounded original bytes used for input hashing. All observations retain their location and order; comparison happens in audit. No observation is an automatic child-consumption claim.
- R-10 `cwd` is stored relative to the repository root; the record never contains absolute paths, local `file://` URIs, hostnames, or usernames.
- R-11 `--capture-output` tees child stdout/stderr to `stdout.log`/`stderr.log` after redaction (line-buffered; redaction applied per line). Default off.
- R-12 `--no-snapshot` disables file snapshots (hashes still recorded).
- R-13 In schema 2, manifest/lock references and files describe the pre-child baseline. Recheck the frozen candidate set after child completion, streaming hashes and recording typed changed/missing/created/unavailable outcomes. Do not inspect unrelated files or alter child inputs. `artifacts.outputs` remains post-child. More than 200 eligible files disables file snapshots, not their hashes. The existing 1 MiB file snapshot limit and `--no-snapshot` semantics remain; manifest/lock copies keep their separate existing policy.
- R-14 Config binding parsing uses at most 2 MiB of original UTF-8 bytes per config, independently of snapshot options. Larger/invalid/unsafe configs produce fixed diagnostics and no observation; a full streaming file hash is still retained when readable. Never parse the redacted copy as the original input.

Input read, config observation, privacy-copy and final-recheck failures remain
separate operations. Unknown final state is not reported as unchanged or
removed. Capture failure never replaces a completed child's exit code;
pre-child invalid manifest/project-rules validation still prevents launch.


R02-R capture protection applies to new run records, manifest/lock copies,
declared-file copies, patches and saved output before any temporary or final
write. File and document references retain hashes of original source bytes;
redacted copies can therefore differ from those bytes. `files[].redacted`
records an actual transformation or a forbidden-file decision. Existing run
directories are not automatically rewritten.

After a child completes, capture or privacy failures add fixed diagnostics and
omit unsafe data. If record sanitation fails, save a minimal completed record
using the already-safe prewrite command and the child's result; never retry by
writing original values. Retry an atomic record replacement failure before this
fallback. If the filesystem remains unwritable, keep the prior safe evidence
and return the completed child's exit code with a finalization warning. Before
child start, an unsanitizable command is a `UserError` (exit 2) with command
guidance. None of these paths echo exception contents.

Saved output retains line-buffered capture and streaming PEM removal. YAML
parent-key context follows indented or indentless lists and block-scalar lines.
TOML table context follows bare, quoted and dotted headers, including array
tables. Supported TOML patch fragments retain visible parent-table context;
changed assignments whose table context is absent are omitted with a fixed
capture warning. No source lookup is added to infer missing patch context.
The PEM stream pass runs before contextual scalar handling so BEGIN/END markers
cannot be transformed before their private body is discarded. An unsafe incomplete
fragment or sanitizer failure disables remaining saved output and drains the
child stream in bounded chunks. Child argv and raw terminal output remain
unchanged, including when saved capture fails. Saved argv retains adjacent
secret-flag context for negative-looking values; this does not change §15.1's
binding-observation token boundary.

---

### 5.2 Read-only run preflight (UX3-T03)

`reprollm run --dry-run [--cwd DIR] [--no-snapshot] [--capture-output]
[--env-capture allowlist|all] [--name LABEL] -- COMMAND...` previews capture
readiness without executing COMMAND. The command remains required. This mode
requires the nearest ancestor `reprollm.yaml` from the selected working
directory; it does not invoke Git for fallback root discovery. Missing or
invalid manifests are usage errors with an actionable `init`/repair hint.
Normal `run` retains its existing behavior, including capture without a manifest.

Preflight MUST NOT execute subprocesses (including Git and nvidia-smi), make
network calls, create a run ID/directory, write snapshots, hash experiment input
contents or mutate any file. Only the bounded manifest and project-rule bytes
are hashed for local lock freshness. It uses the existing schemas to read manifest,
optional config/project rules and optional lock. Documents must be regular files
contained in the manifest root; dangling links and links escaping the root are
usage errors. Read at most 2 MiB per document or inspected configuration/input
file. Oversized required ReproLLM documents are usage errors; an oversized input
or bound config is explicitly `not inspected`, never reported as missing or
successfully observed. Errors must not echo parser input, values or host paths.

Text output is deterministic and includes:

- Portable working directory and effective snapshot/output/environment policies.
- Declared and existing argv files using §5.1 R-03/R-04's exact discovery and
  deduplication policy. Report available text eligible for redacted snapshots,
  hash-only files (snapshot disabled/forbidden name/binary/size), unavailable
  required files and optional declarations that are not files. Preview never
  reads forbidden file contents. Apply the existing 200-file snapshot limit.
- Every distinct declared CLI/config/environment binding location, grouped by
  field, and whether it can be located now. Preserve repeated CLI occurrence
  counts; configuration key traversal and null/list handling follow §15.
  Secret environment bindings remain refused. Never print bound values or raw
  argv, config contents, environment values or a command label.
- Sorted unique `execution.env_requirements` names with presence only; an empty
  environment value is present. Presence is not proof that a credential works.
- Declared non-null leaf fields under `generation`, `evaluation.judge.params`,
  `inference.params`, `training.params`, `privacy.mechanism.params`,
  `privacy.attack.params` and `custom`, plus model `id`/`revision` fields and
  accepted project-rule fields, that lack any declared binding location. Accepted
  rule fields are included even when their manifest value is absent or null:
  the advisory describes a missing capture source, not a missing experiment
  value. Lists are atomic leaves. This fixed advisory set is not a claim to find all
  reproducibility parameters or infer the meaning of undeclared command flags.
- Local lock status: missing, fresh or stale, based only on the exact manifest
  and active project-rule bytes (§4.5). A valid missing project-rules file uses
  the same null-hash semantics as lock. State that remote revisions, artifact
  hashes, dependencies, hardware and provider access are not revalidated.

Sanitize user-controlled names, paths and field labels with existing secret and
machine-identity protection and escape terminal control characters; keep fixed
headings/status labels intact. Preflight may report warnings without preventing
a subsequent real run. A completed preview exits 0 even with warnings; malformed
inputs/options exit 2 and unexpected internal errors exit 3. It never claims an
experiment ran or will succeed. State that files/bindings can change after this
preview and actual run evidence is still collected by the existing run path.
No persisted document or JSON schema is added; no JSON preview mode is defined.

### 5.3 Recorded-run listing filters (UX3-T04)

`runs list` retains its default table and the existing seven-field JSON rows:
`run_id`, `started_at`, `status`, `exit_code`, `duration_seconds`, `name`, `dirty`.
No derived outcome field or wrapper is added. The following optional selectors
are combined with AND, before applying a positive integer `--limit`:

- `--name TEXT` matches the saved name exactly and case-sensitively. Do not trim,
  normalize or interpret patterns/prefixes. An explicit empty string matches an
  empty name, not null. Duplicate names remain separate records.
- `--status` accepts exactly `running`, `completed`, `failed`, `interrupted`.
- `--outcome success` requires `status: completed` AND `exit_code: 0`.
  `--outcome failure` matches completed records with a non-null nonzero exit,
  or any failed/interrupted record. Running records and completed records with
  a null exit match neither outcome, regardless of other recorded values.
- `--limit N` requires an integer at least 1; invalid options exit 2 before
  scanning records. Omission applies no limit.

Preserve start time descending, then full run ID descending; missing start times
sort oldest and historical naive timestamps are treated as UTC. Scan/validate
all recognized records before filtering/limiting; corrupt/missing/unsafe records
retain existing safe stderr warnings and are excluded. A limit must not hide
warnings. Zero matches produce the normal empty table or `[]` JSON and exit 0.
Outcome describes child termination, not complete capture, passing audit or
experiment comparability. These commands remain read-only; `runs show` ID and
prefix resolution and exact saved JSON output are unchanged.

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
| `core` | — | all `code.*`, `env.*`, `exec.*` (except none), `model.primary_declared`, `model.provider_known`, `model.revision_pinned`, `model.tokenizer_pinned`, `model.dtype_declared`, `model.trust_remote_code_declared`, `dataset.revision_pinned`, `dataset.split_declared`, `dataset.local_files_hashed`, `prompt.file_exists`, `prompt.hashed`, `gen.backend_version_locked`, all `consistency.*`, all `project.*` | — | `project.name`, `models.primary.id` |
| `inference` | core | `gen.params_declared`, `gen.backend_declared`, `gen.backend_config_declared`, `gen.seed_declared`, `gen.stop_declared`, `model.chat_template_hashed`, `model.quantization_declared`, `prompt.declared`, `prompt.few_shot_declared` | `gen.params_declared: CRITICAL`, `gen.backend_declared: CRITICAL`, `model.quantization_declared: WARNING` | `inference.backend`, `generation.temperature`, `generation.max_tokens` |
| `evaluation` | inference | `dataset.declared`, `dataset.preprocessing_declared`, `dataset.sampling_seed_declared`, `dataset.subset_declared`, `eval.metrics_declared`, `eval.metric_implementation_referenced`, `eval.aggregation_declared`, `eval.repetitions_declared` | `dataset.declared: CRITICAL`, `dataset.revision_pinned: CRITICAL`, `dataset.sampling_seed_declared: CRITICAL`, `eval.metrics_declared: CRITICAL`, `exec.seed_declared: CRITICAL`, `gen.seed_declared: CRITICAL` | `datasets.eval.id`, `evaluation.metrics` |
| `llm_judge` | evaluation | `judge.model_declared`, `judge.prompt_declared`, `judge.prompt_hashed`, `judge.params_declared`, `judge.pinnability_recorded`, `judge.repetitions_declared` | — | `models.judge.id`, `prompts.judge.path`, `evaluation.judge.params.temperature` |
| `finetuning` | core | `model.adapter_declared`, `dataset.declared`, `dataset.preprocessing_declared`, `train.method_declared`, `train.hyperparameters_declared`, `train.optimizer_declared`, `train.precision_declared`, `train.lora_config_complete` | `exec.seed_declared: CRITICAL`, `dataset.declared: CRITICAL` | `training.method`, `training.learning_rate`, `datasets.train.id` |
| `safety` | evaluation | `eval.definitions_declared`, `eval.query_budget_declared` | `eval.definitions_declared: CRITICAL` | `evaluation.definitions.refusal` or `evaluation.definitions.asr` |
| `privacy` | core | `privacy.threat_model_declared`, `privacy.mechanism_declared`, `privacy.metrics_declared`, `privacy.attack_config_declared` | — | `privacy.threat_model`, `privacy.mechanism.name` |
| `judge_only` | core | `dataset.declared`, `dataset.preprocessing_declared`, `dataset.sampling_seed_declared`, `dataset.subset_declared`, `eval.metrics_declared`, `eval.metric_implementation_referenced`, `eval.aggregation_declared`, `eval.repetitions_declared`, `judge.model_declared`, `judge.prompt_declared`, `judge.prompt_hashed`, `judge.params_declared`, `judge.pinnability_recorded`, `judge.repetitions_declared` | `dataset.declared: CRITICAL`, `dataset.revision_pinned: CRITICAL`, `dataset.sampling_seed_declared: CRITICAL`, `eval.metrics_declared: CRITICAL`, `exec.seed_declared: CRITICAL` | `datasets.eval.id`, `evaluation.metrics`, `models.judge.id`, `prompts.judge.path`, `evaluation.judge.params.temperature`, `evaluation.judge.params.max_tokens` |

Detection signals per profile are in §13.

`judge_only` has empty detection signals and `evaluation.judge.*: HIGH` drift
override. It is explicitly selected for judging pre-generated outputs; declare
the actual answer/input collection in `datasets.eval`. Core remains implicit.
The primary exception applies exactly when `judge_only` is explicitly declared
(manifest or CLI profile override), the resolved closure is a subset of
`{core, judge_only, privacy}`, and no resolved member is replaced by a user
`.reprollm/profiles/<name>.yaml`. Keep `model.primary_declared` selected but emit
SKIPPED only under that predicate. Additional/custom profiles or applicable user
overrides restore the existing primary and their own task requirements. No new
generation rules are added by judge_only; no existing inference/training checks
are weakened. This predicate also controls the scoped judge intent checks in §12.9
and init in §3.2. It does not verify the purpose of the execution command.

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

### 7.1 Ownership and active state

`rules add`, `accept`, `ignore`, `remove` and `restore` own
`.reprollm/project-rules.yaml`. Only entries in its `rules` array generate active
checks. An active rule's candidate ID takes precedence over a matching
`ignored_candidates` entry for presentation; accepting an ignored candidate does
not erase that earlier ignored record. `ignore` must reject an already active
candidate, even if its discovery file no longer exists, and direct the author to
`rules remove RULE_ID --reason TEXT`.

`rules remove` additionally owns `.reprollm/rule-archives/<archive_id>.json`.
`restore` reads the archive and writes the active rules file; it leaves the archive
unchanged. Inspection writes nothing. These commands never modify the manifest,
config, bindings in experiment code, or discovery output. Successful removal or
restoration changes `project_rules_sha256` freshness and must instruct the author
to run `reprollm lock` again.

### 7.2 Recovery archive schema — `.reprollm/rule-archives/<archive_id>.json`

`RuleArchive` (`reprollm/schemas/rule_archive.py`) is an additive, independent v1
persisted document; `ProjectRules` stays at schema version 1. Unknown fields are
forbidden. The new schema remains subject to explicit maintainer code review under
D-41; contract approval does not replace that review.

```json
{
  "schema_version": 1,
  "archive_id": "ra-d48db3bd01e05c7f",
  "archived_at": "2026-10-02T00:00:00Z",
  "reason": "This experiment no longer uses alpha.",
  "rule": {
    "id": "project.alpha",
    "field": "custom.privacy_method.alpha",
    "severity": "WARNING",
    "reason": "Record the privacy parameter.",
    "source": "discover",
    "candidate_id": "c-3f9a1b",
    "accepted_at": "2026-01-02T00:00:00Z",
    "bindings": {
      "cli": "--alpha",
      "config": "configs/privacy.yaml:method.alpha",
      "env": "ALPHA"
    }
  }
}
```

- `schema_version` is integer 1. A newer version exits 2 with an upgrade message.
- `archive_id` matches `^ra-[0-9a-f]{16}$` and is the filename stem.
- `archived_at` requires a timezone. The writer uses UTC, second precision, with `Z`.
- `reason` is the nonblank removal reason, distinct from `rule.reason`; the writer
  strips its outer whitespace.
- `rule` is the complete original `ProjectRule` from §7, including its ID, field,
  severity, reason, `source`, `candidate_id`, `accepted_at` and every binding.
  Manual rules retain `source: manual` and their original optional candidate ID.
  Restoration must not replace approval time, invent discovery provenance or
  substitute current candidate suggestions. Optional values, including nulls,
  retain their original model values; preservation is semantic, not YAML formatting.

Compute the ID as `"ra-" + sha256(canonical_utf8)[:16]`, where `canonical_utf8` is
`json.dumps(payload_without_archive_id, ensure_ascii=False, sort_keys=True,
separators=(",", ":")).encode("utf-8")` from the model's JSON-mode values. Thus the
ID includes the archive timestamp, removal reason and complete original rule.
Readers verify both the filename/embedded ID and the recomputed content ID.
A mismatched or malformed archive exits 2 rather than being restored.

### 7.3 Archive-first deactivation and recovery

`remove` requires an active rule ID and a nonblank reason. It first saves a complete
archive by writing and fsyncing a temporary file and publishing an exclusive
hard link;
publication must never overwrite an existing archive. An identical archive may be
reused, including an identical request in the same second. A conflicting existing
file is an error. Only after the archive is available does the command replace
`project-rules.yaml` with the selected rule removed.

An archive records a **recovery copy**, not a completed removal event. If archive
publication fails, do not remove the rule. If the active-file update fails after
publication, retain the archive, exit 2, report its ID and state that the rule was
not removed by this command. Direct the author to inspect the current rules and
`rules show ARCHIVE_ID` before retrying; concurrent edits may have changed the
current file. Never infer inactivity from an archive's existence.

Archive state is computed from the current active rules and is never persisted:
`active-identical` means the original rule is active unchanged; `inactive` means
neither its rule ID nor its candidate ID is active; `conflict` means an active
entry with either identifier differs from the archived rule. Conflicts take
precedence over an identical active entry. `restore` accepts
only `inactive`, appends the entire original rule without discovery, and keeps the
archive. Even an identical active rule is a restore conflict, so restoration never
overwrites or silently duplicates an active entry.

Removal and restoration parse the same bytes used as their source snapshot and
compare that snapshot with the current file immediately before replacing it. A
visible edit, disappearance or read failure exits 2 without overwriting that
state; a removal archive already saved remains available. This is best-effort
conflict detection, not a filesystem transaction or compare-and-swap guarantee.
There is no cross-process lock; callers must serialize concurrent rule mutations.

Check privacy before publishing an archive or rewriting the active document.
Reject secret-bearing or machine-specific variable text with exit 2 and leave the
original fields unchanged; never sanitize and save an altered recovery copy.
Inspection may redact displayed variable text while preserving fixed schema keys,
enum values and owned source-path prefixes. Refuse symlinks in the owned rules,
archive and inspected discovery paths before reading or writing their targets.

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

Discover include globs add small text files to the default selection; they do
not replace it. Exclude globs remove matching repository-relative POSIX paths
from file contents, source snippets and the outgoing tree, taking precedence
over includes. Matching is case-sensitive shell-style matching (`*`, `?`,
`[seq]`) of the whole relative path; `*` can match `/`. Explicit includes never
override forbidden paths, lockfile exclusion, binary/size checks or redaction.
Symbolic links must resolve inside the repository and their target paths must
pass the same hard and configured exclusions. Source files used for AST
snippets are subject to the same 64 KiB limit.

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
  "schema_version": 1, "reprollm_version": "0.1.1", "generated_at": "…Z",
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
5. **Execute**: for each selected rule with `min_level ≤ level`: if `applies(ctx)` is false → `status: skipped`; else `check(ctx)` returns zero or more findings. Preserve every nonempty result, including explicit PASS/SKIPPED findings. For an empty built-in-rule result only, ask its opt-in `pass_skip_reason(ctx)`; a reason produces one `SKIPPED` with severity INFO, the reason as message, empty evidence and the original rule identity/fix hint. Otherwise synthesize one `PASS`. The default hook returns no reason. Generated project rules keep their existing execution path. Profile overrides, suppression, ordering, summaries and exit thresholds are then applied as before.
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
| `env.lockfile_present` | WARNING | dependency manifest present | no `uv.lock` / `poetry.lock` / `Pipfile.lock` / `conda-lock.yml` and no `requirements*.txt` satisfying the complete exact requirements closure contract below |
| `env.llm_critical_deps_pinned` | WARNING | any LLM-critical package (§4.4) appears in declarations **or** imports | for each such package, no declaration pins its version exactly under the Python or supported Conda contracts below, or a qualified lock-origin association under the scope contract below; one finding per package, subject to the bounded possible-format-lock SKIP in §12.3.3. `pytorch` in conda counts as `torch`. |
| `env.python_version_declared` | WARNING | always | no `requires-python` in pyproject, no `.python-version`, no `python=` in environment.yml |
| `env.secret_files_ignored` | CRITICAL | always | any file matching the forbidden patterns of §16.4 (except the template names `.env.example`, `.env.sample`, `.env.template`) exists and is tracked or not ignored by git (`git check-ignore` false) |
| `env.reprollm_initialized` | INFO | level 0 only | `.reprollm/` or `reprollm.yaml` absent |

**Repository aggregation and format-lock credit (R06-B).** L0 retains repository-wide, existential evidence. For each canonical critical package in supported declarations or scanned imports, any exact declaration anywhere in the repository remains sufficient. Conflicting exact versions do not become a new conflict finding. Otherwise a lock must contain the package and have a qualified association to at least one actual in-use origin of that same package. A lock's own package entry is not an in-use origin. This does not require every origin to be covered and does not verify a selected experiment environment.

Preserve all inventory paths, existing exact-version rules and requirements closure rules. Format-lock associations are bounded static evidence:

- A uv.lock pairs only with a valid same-directory pyproject.toml containing a project table. A poetry.lock pairs only with a valid same-directory pyproject.toml containing project or tool.poetry. A Pipfile.lock pairs only with a valid same-directory Pipfile containing a packages or dev-packages table. A conda-lock.yml pairs only with one unambiguous same-directory environment.yml or environment.yaml containing a dependencies list; both environment basenames present are ambiguous regardless of parse success. Cross-directory sources and workspace membership do not create additional pairs in this phase.
- A declaration origin must be from that paired manager's manifest. Same-directory declarations from another manager are not interchangeable. Exact declarations remain independently sufficient under the repository aggregation rule.
- For an import origin, qualified project directories are created by the valid pyproject, Pipfile and environment structures above. The lock's paired directory must be the nearest such ancestor of the import. Do not cross a nearer project boundary. Requirements roots retain their actual include graph and do not create format-project boundaries. A tool-only or build-system-only pyproject does not create a project boundary.
- Observed unreadable or malformed candidate project manifests form uncertain barriers. Imports cannot borrow lock credit across the nearest such barrier toward its ancestors; inferred import credit at its directory is unproven even if another manager has a valid pair. A deeper independent qualified project can still use its own pair. Explicit declaration credit from another valid same-directory pair remains available. Preserve existing diagnostics rather than interpreting uncertainty as coverage.
- Use normalized repository-relative logical path components and existing safe-read guards, retaining permitted internal aliases. String prefixes, physical aliases or symlinks do not establish extra ownership relations. Do not expand scanner scope, read outside the root or execute a package manager to infer association.

An unassociated format lock remains in the inventory. env.dependency_manifest_present and env.lockfile_present retain their existing repository-wide presence semantics, including the existing treatment of empty or malformed format-lock artifacts; only the critical-package lock-credit branch changes. Presence PASS with a package WARNING is permitted. Package versions within format locks, freshness, platform resolution, hashes and actual installation are not newly verified. No persisted scope field or schema change is introduced. Existing messages, thresholds and unaffected evidence remain unchanged.

**Python exact-version contract.** For requirements declarations, PEP 621 project dependencies and optional dependencies, embedded pip declarations, and Pipfile version fields, a supported valid version constraint is exact only when its parsed specifier contains one non-wildcard `==` version clause. A valid PEP 440 version may contain local, pre-release, post-release, development-release, or epoch components. Poetry dependency version fields also accept a valid bare PEP 440 version as exact, in addition to the same single `==` form. Ranges, wildcard/prefix matching, unversioned declarations, URL/VCS/path dependencies, unsupported syntax, arbitrary equality (`===`), and multiple distinct clauses are not accepted as exact by this bounded static contract. Preserve each format's grammar; do not treat a bare requirements or Pipfile version as a Poetry version field.

Exact means a version constraint, not identity of a build, wheel, index, platform, or file hash. A public `==` pin does not distinguish local variants unless a local label is explicitly included. Extras and markers do not remove an otherwise exact version constraint, but this audit does not claim the same installation on every platform or resolve transitive dependencies.

**Complete exact requirements closure.** Evaluate each discovered `requirements*.txt` root from its actual supported `-r` / `--requirement` include edges, relative to the containing file's directory, after normalization and root-containment checks. Allow normalized internal `..`; reject absolute or escaping targets before reading. A qualifying closure has at least one valid package declaration, every reachable package declaration meets the Python exact-version contract, and every include edge is resolved. Cycles, depth-limit exhaustion, unreadable/missing/escaping files, malformed declarations, and unsupported directives prevent that root from qualifying. Blank lines and comments do not count as declarations. Repeated/shared nodes are deduplicated and are not cycles unless encountered on the active recursion stack. The lock's package set contains only declarations actually reachable from that root, never an unreferenced sibling. Use one graph/result for qualification and package membership. This retains L0 repository aggregation and is independent of the format-lock association contract above.

**Supported Conda exact-version contract.** Parse the bounded simple MatchSpec subset independently of Python/PEP 440 grammar. For a literal package name and a numeric release version (`N(.N)*`), `name==version` is version-exact. The export forms `name=version=build` and `name==version=build` are version-exact when the build is a non-empty literal composed of ASCII letters, digits, `.`, `_`, `+`, or `-`. Single `name=version` without build is prefix matching and is not exact, regardless of the number of version components. Unsupported channel/subdir/bracket/regex/range/compound forms, wildcard versions or builds, empty or malformed parts, and version forms outside this explicitly supported subset are not accepted as exact; diagnose them conservatively without running Conda or a solver. Preserve the original supported version/build declaration as evidence. Build equality is a separate fact; the audit adds no build field and does not infer channel, platform, or artifact-hash identity. Embedded `pip:` entries follow the Python contract above. `pytorch` retains its canonical mapping to `torch`.


### 12.3 `exec.*` (M2–M5)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `exec.command_declared` | WARNING | 1 | manifest | `execution.command` absent |
| `exec.seed_declared` | WARNING | 1 | manifest | none of `execution.seed`, `generation.seed`, `training.seed` present |
| `exec.run_recorded` | INFO | 1 | manifest | no run records |
| `exec.profile_detection_mismatch` | INFO | 1 | manifest | a `high`-confidence detected profile is not declared, or a declared profile has no detection evidence (subject to the branch-specific SKIP in §12.3.2) |

### 12.3.1 Known primary-Python gaps: bounded synthetic-PASS policy (R07-C A)

Only `env.llm_critical_deps_pinned` and `exec.profile_detection_mismatch` opt in.
When applicable and their check returns no findings, synthesize SKIPPED/INFO instead
of PASS if primary-Python candidate analysis is unobserved, its counts are
inconsistent, or parsed is less than candidate. This is a deliberately conservative rule-level veto, including when
input-specific evidence might already settle the rule. The fixed message is:

```text
Python candidate analysis incomplete: parsed {parsed} of {candidate} candidate files; selected {selected} (limit {limit}); no rule-wide PASS is established.
```

Unobserved or inconsistent internal coverage uses `Python candidate coverage is
unavailable; no rule-wide PASS is established.` Count invariants are
0 <= parsed <= selected <= candidate, 0 <= limit and selected <= limit.
Normal completed scans record observation even
with zero candidates. Counts refer only to the captured eligible candidate view
and the active count/read/parse budgets in §13. They do not certify Git listing,
filesystem enumeration, dependency parsing, framework scanning or full detection.
No warning prose is parsed into coverage facts; no persisted fields are added.

Nonempty rule results remain unchanged except for the declared-but-undetected
profile branch in §12.3.2 and the possible-format-lock dependency branch in §12.3.3.
Applicability skips, all other built-in rules and generated project rules are
unchanged. Used-but-unpinned package WARNING outside §12.3.3 remains an existing
bounded-scan conclusion relative to the captured dependency view; it may depend
on absence and be overturned by additional evidence. It is not relabelled as a
fully proven violation. Listing/dependency/framework uncertainty and broader
input-specific sufficient certificates remain OPEN R07-C work. This limited policy must not be described as
full R07-C coverage assurance or proof of complete experiment reproducibility.
With consistent observed counts and parsed=candidate, prior behavior stays
unchanged; default fail-on and all existing schema versions stay unchanged.


### 12.3.2 Declared-profile absence with primary-Python gaps (R07-C continuation)

For `exec.profile_detection_mismatch` only, consider each declared non-core profile
that has no entry in the current detection result. If the existing typed
primary-Python coverage assessment in §12.3.1 is incomplete or unavailable, emit
one explicit SKIPPED/INFO finding for that profile instead of its absence-derived
FAIL. This includes unobserved or inconsistent counts; no warning text is parsed.
Use the following message template, where `{profile!r}` is the existing quoted
profile-name representation:

```text
declared profile {profile!r} has no detection evidence in the analysed inputs; Python candidate analysis is incomplete or unavailable, so absence is not established
```

Both incomplete and unavailable assessments use that same message. Evidence is
exactly one existing field item: `kind: field`, `field: experiment.profiles`,
`note: "{profile} declared; detection absence unverified"`. Keep the rule ID,
aliases, category, current audit level and rule fix hint; optional evidence fields
and finding origin/suppression fields retain their existing defaults. No counts,
new status, schema field or schema version are added.

When the captured primary-Python view has consistent observed counts with
parsed=candidate, retain the current declared-but-undetected FAIL, message and
evidence. This preserves a bounded evaluation result; it does not prove complete
listing, dependency, README/config/framework detection or repository-wide absence.
A detected profile has no such absence finding regardless of whether its witness
came from Python or another supported source. Core remains implicit and excluded.

Keep the positive branch unchanged: a shipped high-confidence detected profile
that is not in the effective declarations still yields its existing FAIL and
concrete detection evidence, even in the same result list as one or more new
SKIPPED findings. Emit absence outcomes in the existing sorted declared-profile
order, then positive outcomes in the existing sorted detected-profile order;
the engine's unchanged final severity/category/rule-ID sort still applies.
Do not short-circuit the whole rule or add a rule-wide coverage finding when its
check already returned outcomes. The existing empty-result veto in §12.3.1 and
missing-manifest applicability skip retain their exact contracts.

Profile severity overrides continue to apply only to FAIL outcomes. A new
SKIPPED outcome remains INFO/default, including when the rule has an override of
WARNING or CRITICAL. An isolated absence finding that previously triggered an
explicit or default failure threshold through such an override can therefore
stop triggering exit 1. Threshold values and FAIL-only counting are unchanged.
Existing ignore/suppression handling still applies to every status: matching
outcomes become SUPPRESSED/INFO with the same reason and appended ignore evidence.

This continuation changes only the declared-but-undetected branch under the
specified primary-Python assessment. The separate dependency policy in §12.3.3
has its own bounded scope. Upstream listing/detection completeness and broader
sufficient-certificate policy remain unchanged or OPEN. It does not close the whole R07-C task, certify child execution
or authorize rewriting historical reports.

### 12.3.3 Possible format-lock credit with primary-Python gaps (R07-C D-L)

For `env.llm_critical_deps_pinned` only, keep the current in-use canonical package
set from captured declarations and scanned imports. A format-lock package entry
alone does not establish use. Keep the existing qualified-lock and exact-declaration
checks first; packages already credited by either follow their existing path.
For each remaining package, use the existing typed primary-Python assessment in
§12.3.1 and the captured `Declarations.lockfiles` package sets:

- Supported format-lock names are exactly `uv.lock`, `poetry.lock`, `Pipfile.lock`
  and `conda-lock.yml`, identified by the final logical POSIX path component.
- If that assessment is incomplete or unavailable AND the package belongs to at
  least one captured supported-format lock package set, emit one SKIPPED/INFO
  finding for that package instead of its used-but-unpinned FAIL/WARNING.
- Otherwise retain the existing FAIL/WARNING message, evidence, suggestion and
  fix hint, including when Python analysis is incomplete but no captured format
  lock contains that package. Consistent observed parsed=candidate retains all
  prior per-package behavior, including zero candidates.

The new finding retains rule ID, aliases, category and audit level. Use the
existing display-name mapping for `{display}` and this exact message:

```text
{display} is used; Python analysis is incomplete or unavailable and a captured format lock lists the package, so missing pin evidence is not established
```

Use the exact fix hint:

```text
Review {display} declarations and format-lock origins; complete Python analysis before deciding that exact pin evidence is absent.
```

Evidence first retains the existing package-use evidence selection: the first
captured declaration for that canonical package, or otherwise its first captured
import. Then append one `kind: file` item for every distinct matching supported
format-lock logical path, sorted lexicographically. Its `path` is that path and
its `note` is `{display} listed; import-origin credit unverified`; other optional
evidence fields keep their existing defaults. Finding severity/status are INFO /
SKIPPED with existing default origin/suppression fields. Emit packages in the
existing sorted canonical order and preserve the engine's final sort.

This is a conservative upper bound relative to the FIXED captured dependency
view, not newly granted lock credit. Under §12.2, additional Python imports can
only add qualified format-lock credit for names already present in those format
package sets. Requirements-closure credit and exact declarations are independent
of Python imports. Qualified existing credit/exact declarations therefore still
win before the new branch. Requirements closure lock entries do not trigger this
branch and keep their existing contract.

The upper bound deliberately includes format entries without a valid pair, with
wrong-manager association, behind a nearer project/uncertain barrier, or with no
actual matching omitted import. Those entries may conservatively cause SKIP even
when the existing association rules would never credit them; they do not become
in-use origins or acquire credit. This policy does not inspect omitted file bodies,
expand discovery/read budgets, add inferred import paths or execute a package
manager. It does not change R06-B association or repository existential semantics.

Unreadable/malformed locks whose parser captured no matching package entry do
not trigger this branch. The resulting old bounded WARNING does not certify
lock parsing, dependency reading, listing or the completeness of package-use
enumeration. This policy settles only the stated primary-Python uncertainty
relative to a captured dependency view. Independent dependency/parser/listing
uncertainty and broader sufficient certificates remain OPEN R07-C work.

A nonempty result may contain both new SKIPPED findings and existing WARNING
findings for other packages. Do not short-circuit the whole rule or synthesize
an extra coverage finding. No per-package PASS is introduced. The existing empty
result veto in §12.3.1 and no-critical-package applicability skip are unchanged.
FAIL-only profile severity overrides do not affect new SKIPPED/INFO findings;
ignore/suppression still applies to all statuses. An isolated warning or a
profile-promoted CRITICAL failure may stop triggering exit 1. Fail-on threshold
values and the set of statuses counted by them stay unchanged. Default text and
export follow existing SKIPPED visibility and summary contracts; JSON retains
the complete findings. No schema, rule ID, default rule severity or historical
report is changed, and this continuation does not close the whole R07-C task.

### 12.4 `model.*` (M3 presence, M4 lock)

| ID | Sev | L | applies | FAIL when |
|---|---|---|---|---|
| `model.primary_declared` | CRITICAL | 1 | manifest, except §6.1's explicit shipped judge_only predicate | `models.primary.id` absent |
| `model.provider_known` | WARNING | 1 | per model | provider is `other` |
| `model.revision_pinned` | CRITICAL | 2 | per model | HF: lock `revision.confidence != exact`; API: `pinnability == unpinnable` → rule emits WARNING, `snapshot_alias` → rule emits INFO (see §11 step 6); local: `config_sha256` absent |
| `model.tokenizer_pinned` | WARNING | 2 | per HF model | lock `tokenizer.revision.confidence != exact` |
| `model.chat_template_hashed` | WARNING | 2 | per HF/local model | lock `chat_template` missing, or `status ∈ {present, custom_file}` with `sha256.confidence != exact`. `status: absent` (repository has no chat template) is PASS with an evidence note. |
| `model.dtype_declared` | WARNING | 1 | per model, non-API under §4.3's per-role predicate | `dtype` absent and `inference.dtype` absent |
| `model.quantization_declared` | INFO | 1 | per model, non-API | `quantization` absent and `inference.quantization` absent |
| `model.adapter_declared` | WARNING | 1 | detection found `peft` import or dependency | no model has `adapter` |
| `model.trust_remote_code_declared` **P1** | WARNING | 1 | scanner finds `trust_remote_code=True` in `*.py` | no model explicitly declares `trust_remote_code: true` or `trust_remote_code: false` |

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

Under the exact §6.1 primary exception only, `judge.model_declared` additionally
fails for a referenced model with absent/empty/whitespace-only id, and
`judge.prompt_declared` fails when both path and inline text are absent. Explicit
empty inline text counts as declared content. Existing reference validation,
file existence and hashing remain unchanged; invalid references still exit 2.
Outside that predicate these two rules preserve their released presence behavior.
Keep existing numeric validation: zero temperature is valid, max_tokens must be
positive, and repetitions has no added positive constraint (zero remains a
declared value). No schema relaxation or new rule ID is introduced.

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
| `consistency.env_vs_lock` | WARNING | lock and latest run with confirmed compatible recorder context | any recorder LLM-critical package version in run ≠ lock (one finding per package); matching recorded versions yield a recorder-scoped PASS, never child verification; unknown/incompatible context yields SKIP with scope guidance |
| `consistency.custom_fields` | (project rule) | project rules with bindings and run observations | observed ≠ manifest `custom.*` value |

### 12.13 `project.*` (M7)

Generated from `.reprollm/project-rules.yaml` (§7). FAIL when the `field` is absent/null in the manifest.

---

## 13. Deterministic profile detection (M2)

`reprollm/profiles/detect.py`. Input: `RepoScanner`. Output `DetectionResult`: `{profiles: [{profile, confidence: high|medium|low, evidence: [Evidence]}], hints: {providers: [...], hf_ids: [{value, path, line}], trust_remote_code: bool}}`.

Static repository content readers MUST resolve the actual target and verify it is
inside the project root before any content open, including explicit `max_bytes`
reads and cache hits. Reject absolute inputs, targets outside the root, invalid
paths and symlink loops with stable diagnostics containing only a safe project
source. Internal symlinks and normalized internal `..` are allowed; evidence
retains the repository-relative source alias. User profile overrides share this
path boundary. File existence, Git state and forbidden-file facts remain visible
even when content is refused; listing, binary, size and consumer budgets retain
their existing contracts. Reads use the resolved target, but replacement of any
resolved path component, including the final target, after validation can still
race the open; this boundary does not claim a filesystem sandbox.
Profile names, including inherited names, must satisfy the existing profile
identifier grammar before constructing any file path. Built-in reads are limited
to shipped profile names; invalid names produce a fixed diagnostic without
echoing a path supplied as a name.

Signals (Level 1 = deterministic, Level 2 = heuristic):

| Signal | Source | Profile / hint | Confidence |
|---|---|---|---|
| import `peft`, `trl`; `from transformers import Trainer|Seq2SeqTrainer|TrainingArguments`; import `deepspeed` | AST | `finetuning` (+ hint adapter) | high |
| import `accelerate` | AST | `finetuning` | medium |
| import `vllm`, `sglang` | AST | `inference`; hint backend | high |
| import `openai`, `anthropic` | AST | hint provider | — |
| import `lm_eval`, `lighteval`, `inspect_ai`, `evaluate` | AST | `evaluation` | high |
| `lm_eval` / `lm-eval`, `python -m lm_eval`, `lighteval`, or `inspect eval` command | shell script / Makefile command, excluding comments | `evaluation` | high |
| recognizable lm-eval task YAML | bounded framework configuration scan | `evaluation` | high |
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

Keyword matching is case-insensitive and **word-boundary based** (`\bkeyword\b`, with `-`/`_`/space treated as equivalent separators), never bare substring: "manager" MUST NOT match `agent`, "storage" MUST NOT match `rag`. Only README text, configuration **key names** (not values), directory names, and file stems are scanned. Highest confidence per profile wins. `init` includes `high` and `medium`. AST scanning caps remain ≤ 500 static-candidate `.py` files and ≤ 512 KiB per file.

When the Python candidate count exceeds the active file-count limit, `audit`,
`init` (including `--list-tasks` and interactive planning), and `export`'s embedded
audit MUST emit one short default stderr coverage diagnostic. Candidates are the
sorted `.py` paths remaining after shared static exclusions and existing listing
hard limits. Selected is the number returned by the bounded Python selection;
parsed counts only selected files for which `ast.parse` succeeds. Omitted is
candidate minus selected. The active limit MUST be reported, not assumed to be
500 or equated with successful parsing. The fixed diagnostic is:

```text
scan: Python analysis incomplete: parsed {parsed} of {candidate} candidate files; selected {selected} (limit {limit}), omitted {omitted}. Missing signals may be in unanalysed files.
```

If selected minus parsed is nonzero, insert `{selected_skips} selected files were
not parsed.` before the last sentence. Size, unreadable/non-text and syntax-error
skips reduce parsed; their causes MUST NOT be inferred as separate exact counts
from an undifferentiated read failure. No such default summary is added when the
candidate count is within the file-count limit. Existing per-file and other
verbose diagnostics keep their existing visibility; init/export forward only
the new coverage summary. `-v` MUST NOT repeat that summary or display the legacy
file-truncation line for the same budget fact. Interactive replanning and repeated
cached access MUST NOT repeat the same coverage summary within one command.

The diagnostic contains only fixed text and integers. JSON stdout remains one
unmodified JSON document; report files and exported Markdown gain no diagnostic
fields or text. Internal coverage counts and CLI diagnostics do not add persisted
schema fields or change findings, severity/summary counts, rule statuses or fail-on
by itself. The separate bounded R07-C policy in §12.3.1 changes two rules' empty-result
PASS handling; the R07-B diagnostic and its default visibility remain unchanged. Discover payload/snippet budgets remain
independent under §20.2 and are not described as this Python file-count limit.

---

## 14. Integrations contract

`reprollm/integrations/base.py`:

```python
class Integration(Protocol):
    # Includes provider names and lm_eval, lighteval, inspect_ai frameworks.
    name: str

    def detect(self, scanner: RepoScanner) -> list[Evidence]: ...  # optional
    def resolve(
        self, manifest: Manifest, *, offline: bool, http: httpx.Client
    ) -> LockFragment: ...  # optional
    def capture(self) -> dict: ...  # runtime facts, e.g. package versions; optional
    def extract_task_hints(self, scanner: RepoScanner) -> TaskHints: ...  # evaluation frameworks
```

| Integration | detect | resolve | capture |
|---|---|---|---|
| `huggingface` | HF ids, `datasets` import | §4.3 models/datasets | — |
| `transformers` | Trainer imports, `from_pretrained` | — | `transformers`, `tokenizers`, `accelerate` versions |
| `vllm` | import | `inference.version` | `vllm` version, `VLLM_*` env (allowlisted) |
| `openai` | import; `base_url` strings containing `openrouter.ai` → provider hint openrouter | pinnability, optional `--verify-api` | `openai` version |
| `peft` | import | adapter repo resolution | `peft` version |
| `lm_eval` | bounded imports, CLI entry, recognizable task YAML | — | `lm_eval` version |
| `lighteval` | bounded imports, CLI entry | — | `lighteval` version |
| `inspect_ai` | bounded imports, `inspect eval`; task extraction from `@task` | — | `inspect_ai` version |

Integrations MUST NOT import their target libraries.

Evaluation framework task hints are internal initialization candidates, not an assertion that
every discovered task was used by an experiment. Retain the complete sorted unique safe inventory
independently of selected profiles. When `evaluation.metrics` is required, `init` pre-fills only
explicitly selected task names; no selection renders an empty TODO list. The author must confirm
each metric name and implementation: task identity is not metric identity. An explicit profile
selection that does not require evaluation does not pre-fill metrics. Framework YAML tags are
inspected as syntax only and never executed; names not satisfying §3.2 are neither listed nor
selected. Do not infer metric implementation, aggregation or bindings from task names.

---

## 15. Bindings

### 15.1 Observation (run time)

| Location | Observation |
|---|---|
| `cli: "--flag"` | scan argv for `--flag VALUE` (next token not starting with `-`) or `--flag=VALUE`; repeated → last wins but all recorded; present without value → `true`; absent → no observation |
| `config: "path:dotted.key"` | before child start, load bounded original YAML/JSON/TOML bytes by extension; traverse dotted key (list index as integer segment); missing → `warnings[]` entry, no observation |
| `env: "VAR"` | pre-child inherited `os.environ[VAR]`; if `VAR` matches secret-name rules (§16.1) the binding is refused with a warning |

Before recording an observation, apply §16.2 with its binding field, actual
source key, config traversal segments and enclosing data keys. Preserve context
for nested mappings, lists and a bound secret scalar. Source type/key/path describe evidence rather
than its secret value and retain their semantics. Typed presence records such
as `{present: true}` are also retained. This contextual handling does not apply
§16.1 environment-name classification to arbitrary experiment keys.

Schema-2 config values are baseline observations, even if a child later
rewrites the config. The end-of-run hash/check is separate evidence and cannot
override those binding values. Schema-1 config observations retain their
recorded values and precedence with unknown input phase; never upgrade them
to consumed values. Existing generation/model/custom conflict rules continue
to inspect all baseline/legacy observations against declarations; their messages
identify baseline or unknown phase rather than asserting child consumption.

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
| jwt | `\beyJ[A-Za-z0-9_-]{8,}={0,2}\.[A-Za-z0-9_-]{8,}={0,2}\.[A-Za-z0-9_-]{8,}={0,2}(?![A-Za-z0-9_=-])` |
| pem | `-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----` |
| url_cred | `(?<=://)[^/\s:@]+:[^/\s@]+(?=@)` |
| generic_kv | `(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password|passwd)\b\s*[:=]\s*["']?([^\s"']{8,})` (redact group 2 only) |

Replacement: `<REDACTED:kind>`. Counting redactions per artifact is recorded (`command.redactions`, `files[].redacted`).

R02-R adds capture context without changing the pattern table. Structured data
leaves are checked with their raw enclosing keys and field/source context.
Standard JSON/YAML quoted keys, escaped JSON strings, nested mappings/lists,
flow containers and block scalars retain that context. Safe scalar source bytes
remain unchanged; unsafe scalar spans are replaced while retaining surrounding
structure. Keys and source gaps are checked separately so a mapping key such
as `password` cannot consume a following `max_tokens` key as its value. Manifest
binding descriptors retain their source-location semantics. Lexical scalar
handling covers patch/output fragments, comments and embedded serialized text.
Apply streaming PEM removal to decoded structured scalar values before keyed
handling, including bound values; an incomplete PEM does not consume a safe
sibling field outside that scalar.

TOML capture uses the existing TOML reader to validate input, decode table and
dotted assignment keys, and verify the sanitized result against the same keyed
policy. Keep safe assignments unchanged and replace unsafe assignment values
with valid TOML values while retaining data types and structure. Check comments
inside container values as well as source gaps. If an unsafe key cannot be
mapped safely, or a supported table context has an ambiguous incomplete value,
omit that capture with a fixed warning rather than writing original text.

Classification retains the existing generic aliases, case/separator variants
and minimum matching length of eight; it does not identify arbitrary unknown
secret formats. Malformed nested text with recognizable supported unsafe
context fails closed even under an ordinary outer key. Structured parsing is
bounded to 1 MiB, 10,000 visited nodes, 64 container ancestors and eight nested
serialized-text levels; cycles or unsafe ambiguity produce capture warnings
rather than original-text fallback. Applying capture privacy to its own safe
output changes no bytes and records no new transformation.

Redacted observations and snapshots are evidence substitutes, not runnable
original configuration. Different secrets can produce the same placeholder,
so diff/export cannot reconstruct or prove equality of their original values.
Original file hashes can still report a source-file change. Protection applies
to new writes and does not claim that historical artifacts have been cleaned.

The maintainer-approved M5-T01 correction accepts zero to two trailing `=`
characters per JWT segment and includes padding in the replacement. This
reconciles the normative expression with M5's padded-token corpus requirement;
it changes no persisted schema or other pattern class. See approved
[spec issue #3](https://github.com/EnumaElish123/ReproLLM/issues/3).

### 16.3 Environment capture policy

Values below are captured from the recorder environment copied before child
launch. They are the inherited baseline, not a report of later child/launcher
changes. This scope does not alter the allowlist or secret rules.

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
    context: EvidenceContext | None = None
```

`EvidenceContext` has typed `subject` (`recorder`, `host`,
`inherited_environment`, `input_file`, `unknown`), `phase` (`pre_child`,
`post_child`, `lock_resolution`, `unknown`) and `verification: unverified`.
It is internal provenance, not an experimental value or an additional drift
leaf. Context survives State JSON round-trip, alternatives and repeated merge.
Binding location remains in `detail`; warnings carry human diagnostics only.
Environment context follows §5.1 R-06; new schema-2 config/file/document
observations follow the input baseline, and legacy input phase stays unknown.
An absent context on legacy/internal data never means child verified.


Projections: `State.from_manifest(m)`, `State.from_lock(l)`, `State.from_run(r)`. `State.merge(manifest, lock, run)` applies precedence `run(cli) > run(config) > run(env) > lock > manifest > default` per leaf and keeps all alternatives in `leaf.alternatives` for consistency findings. `State.flatten() -> dict[str, Leaf]` with paths like `models.primary.revision`, `environment.packages.torch`, `files.configs/eval.yaml.sha256`.

Repeated CLI bindings select the last explicit occurrence for their field,
including mapped aliases, while the run record retains every observation in
original argv order. Config/env same-source selection keeps its deterministic
location/value ordering rather than inheriting CLI last-wins.

A State primary is already selected: later merges must not promote its older CLI
alternatives back into the effective value. Re-merging overlapping projections,
including after State JSON round-trip, preserves that choice and bounds evidence
multiplicity; genuinely repeated identical observations remain recorded. Across
independently selected States, equal-rank primaries use the existing deterministic
location/value tie rule, without inventing a shared argv timeline. Existing v1 run
records recover CLI selection from their ordered observations without a schema
or ordinal field change. Audit, diff and export consume the same effective State.

Consistency checks still inspect every observation for conflicts with declarations;
a final CLI value matching the manifest does not erase an earlier conflict.

---

## 18. Diff semantics (M6)

Inputs: two of {run_id, path to `run.json`, path to `reprollm.lock`}. Each is projected to a State (`run` uses its embedded lock and manifest snapshots).

### 18.1 Algorithm

Flatten both; for each path in the union: `same | changed | added | removed`. Severity from `drift_severity.yaml`: first matching pattern in file order wins; profile `drift_overrides` are prepended. Package versions (`environment.packages.*`, `inference.version`) are compared with `packaging.version`: differing major/minor → the listed severity; differing patch only → one level lower (min LOW). `code.commit` changed is reported as `MEDIUM` with note "code changed" unless `code.dirty` is true on either side (→ HIGH). Paths matching no pattern → `MEDIUM`.

Equality means equality of recorded effective values within the stated
evidence context. It does not verify a child environment or consumed input.
Changed environment/input leaves include safe context notes using the existing
`DiffChange.note` field. Context-only changes add no experimental drift and do
not alter severity or fail-on. Diff text displays the scope even for an empty
self-diff. Schema-1 input observations stay comparable as recorded values,
with unknown-phase guidance; no post-child value from a new schema-2 check
becomes a baseline parameter.

Direct `evaluation.judge.params.*` leaves use HIGH for changed, added and removed
values. Each `*` matches exactly one dotted segment; deeper parameter paths and
unrelated privacy/training paths retain their existing policies. Profile overrides
remain before defaults in first-match order, including explicit LOW/NONE. A direct
judge-parameter change alone can therefore make explicit `--fail-on HIGH` exit 1;
omitting `--fail-on` still reports without a drift-triggered nonzero exit.

The exact flattened paths `privacy.mechanism.params.target_epsilon`,
`privacy.mechanism.params.target_delta`, `privacy.mechanism.params.max_grad_norm`
and `training.params.num_train_epochs` use HIGH for changed, added and removed
values (R08-B A4). No alias, prefix, recursive wildcard or other parameter path
is added. This is the default comparison policy for recorded experimental values;
it does not compute a privacy guarantee, verify child consumption, or establish
that each change affected execution. Non-null explicit noise may bypass epsilon
calibration; an epoch horizon may affect calibration even when max_steps limits
training. Value validation, State flattening and source precedence remain unchanged.
The existing first-match profile overrides still precede defaults, including
winning LOW/NONE entries. Any one of these leaves alone can make explicit
`--fail-on HIGH` exit 1; the default without --fail-on still exits 0 for drift.
Historical reports retain their original severities; new comparisons of supported
old inputs use the current policy without rewriting those inputs or reports.

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
  - { path: "training.params.num_train_epochs",      severity: HIGH }
  - { path: "training.*",                          severity: HIGH }
  - { path: "evaluation.judge.params.*",           severity: HIGH }
  - { path: "evaluation.judge.*",                  severity: HIGH }
  - { path: "evaluation.metrics",                  severity: HIGH }
  - { path: "evaluation.definitions.*",            severity: HIGH }
  - { path: "evaluation.*",                        severity: MEDIUM_HIGH }
  - { path: "privacy.mechanism.params.max_grad_norm", severity: HIGH }
  - { path: "privacy.mechanism.params.target_delta",  severity: HIGH }
  - { path: "privacy.mechanism.params.target_epsilon", severity: HIGH }
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


M6 implements the first diff report writer. The unreleased M1 placeholder schema
is replaced by the complete v1 shape below; `a`, `b`, `summary` and `changes` are
required. This does not change the manifest, lock or run-record schemas.

A run directory is also accepted and resolves to its contained `run.json`.
Lock inputs include an adjacent `reprollm.yaml` when present; run inputs use only
their captured document snapshots. Missing or invalid referenced snapshots are
user errors, not silently omitted evidence. Ambiguous run prefixes list candidates.

Without `--min-severity`, all changes are shown; the optional `filtered_below`
field is null. With the flag, `changes` is filtered and `filtered_below` records
the selected threshold. `summary` and `--fail-on` always use all changes.
Omitting `--fail-on` prints a report without a drift-triggered nonzero exit.
Declared profiles from A then B are resolved in order using §6's existing merge
semantics, with duplicate names removed. The current project's profile files
supply overrides; the historical input values remain unchanged.

Report values are redacted only after comparison, so distinct secret values
remain a change even if both display the same redaction marker. References are
relative paths or external input basenames, never absolute host paths.

```json
{
  "schema_version": 1, "reprollm_version": "0.4.0",
  "a": { "kind": "run | lock", "ref": "20261005T093000Z-a1b2c3" }, "b": { … },
  "summary": { "highest": "HIGH", "counts": { "HIGH": 2, "MEDIUM_HIGH": 1, "MEDIUM": 0, "LOW": 3, "NONE": 4 }, "same": 57 },
  "changes": [ { "path": "models.primary.revision", "status": "changed", "a": "abc…", "b": "def…", "severity": "HIGH", "note": null } ]
}
```

Text output groups by top-level section, shows `A → B` per change, severity tag, and ends with a one-line verdict: `Highest drift: HIGH (2 changes). These runs are not directly comparable.` when HIGH exists.

### 18.4 Recent successful-run selection (UX3-T04)

`diff --latest-successful [--name TEXT]` selects the two newest valid records in
the current project using §5.3 ordering and success/exact-name predicates. A is
the second-newest (older) and B the newest. Without a name filter, labels may
differ. This flag is mutually exclusive with either positional input; explicit
mode still requires both A and B. `--name` is valid only in shortcut mode.
Invalid combinations exit 2 before reading inputs.

Scan records once and print the same corruption warnings to stderr as listing.
Fewer than two qualifying records is a usage error stating the count and
suggesting `reprollm runs list --outcome success` and a name filter when relevant;
do not echo raw selector text. Never widen a filter, substitute a non-success
record or compare a record with itself. After selecting two valid run records,
invalid/missing referenced snapshots cause exit 2; never fall back to a third run.

Construct inputs from the selected validated records and their owned run
directories, with §18.3 snapshot containment and historical-state rules. Do not
resolve selected IDs again through generic input parsing: a same-named current
directory/file must not shadow a selected stored run. This avoids a second
eligibility read, without promising a transaction across snapshot files.

The existing text A/B lines and JSON `a.ref`/`b.ref` contain the full selected
IDs with `kind: run`; add no selection preamble to JSON or persisted schema
fields. Format, profile overrides, display thresholds and full-summary/fail-on
semantics are unchanged. Selection never depends on a threshold. Success alone
does not establish that the experiments are comparable. Ordinary explicit
inputs and unique/ambiguous ID-prefix behavior remain unchanged; labels do not
become input aliases.

---

## 19. Export (M7)

`reprollm export` renders `REPRODUCIBILITY.md` from `templates/REPRODUCIBILITY.md.j2` using merged State. With a selected/latest run, merge that run's own available manifest/lock snapshots and observations; current declarations must not replace historical evidence. Without a run, merge the current manifest and lock. Sections in order: Title & generated-by/source line; **Experiment identity** (models table: role, provider, id, revision/pinnability, tokenizer rev, chat-template hash; datasets table; prompts table with hashes; generation parameters; inference backend/version; optional Training; optional Evaluation with Judge subsection; optional Privacy); **Code** (commit, branch, dirty, remote); **Environment** (python, LLM-critical packages); **Hardware** (available captured GPU/driver details); **Execution** (command, run id, timestamps, duration, exit code); **Audit summary** (counts by severity; list CRITICAL and WARNING messages); **Known limitations** (every `unresolved`, `unpinnable`, `not_computed`, and unresolved binding); footer with `reprollm` version and schema versions.
Requirements: deterministic ordering; relative paths only; redaction applied; if no run exists the Execution section states so; if no lock exists the identity table marks revisions as `not locked`.

Evaluation includes metric name, implementation, recorded hash/version and
parameters; declared aggregation, repetitions, definitions, thresholds and query
budget. Judge names actual model_ref/prompt_ref roles and its own parameters,
repetitions and parser, separate from primary generation. Privacy includes
declared threat model, mechanism/parameters, metrics and attack settings.
Add available model dtype/quantization/adapter, dataset subset/split/preprocessing
and prompt format/few-shot details beside their identity tables. All values
derive from effective State, including identity/hash tables; never bypass
observations with a direct current-manifest/lock lookup. Source labels distinguish
declared manifest values, locked confidence and observed run values. Preserve
zero, false, nested maps/lists and absent-value honesty; compute no new measurements.

Every current export template (default, neurips, acl, acm) labels recorder
Python/packages, host hardware, inherited env and unverified child environment.
Selected run documents/inputs are labeled pre-child baseline for schema 2 and
unknown input phase for schema 1. Typed post-child checks are displayed
separately with path, availability/change and hashes; they do not replace
effective parameters. Known limitations explicitly retain unverified child
consumption, even when checks are unchanged. Checklist references point to
these scoped statements and never upgrade them to verified experiment facts.

The existing Audit summary remains a current-working-tree audit using current
declarations/lock and latest valid run when applicable. Label that scope explicitly;
it is not a re-audit of the selected historical run. Explain the selected-run
snapshot source in the report opening and never call unobserved fields verified.

Before serialization or display escaping, redact keyed secrets and remove
machine-specific paths/identity recursively from free-form keys and values using
existing privacy helpers. Preserve safe relative paths, ordinary URLs and Unicode.
Render free text as literal Markdown/HTML-safe cells; embedded pipes, newlines,
tags, images or links must not invent report structure or executable content.
Use safe code spans for commands and identifiers so visible literal text remains
copyable, then apply the final secret-redaction gate. Keep rendering deterministic.
Checklist mappings cite actual rendered evidence or say not covered. Export makes
no model/provider request and changes no persisted artifact schema.

---

## 20. Discover (M7, experimental)

### 20.1 Gate

Requires `--experimental` **or** `config.discover.enabled: true`. Requires `REPROLLM_LLM_BASE_URL`, `REPROLLM_LLM_API_KEY`, `REPROLLM_LLM_MODEL` (names configurable). `--paper` → exit 2: "Paper analysis is not available in Beta."

### 20.2 Collection (`collector.py`)

Include: `README*`, top-level `*.md`, `*.yaml|*.yml|*.json|*.toml` ≤ 64 KiB (excluding lockfiles and `.reprollm/`), AST-extracted snippets of `argparse.add_argument(...)`, `@dataclass` classes, `hydra`/`omegaconf` config classes, the repository tree (paths only, ≤ 2000 entries). Exclude: forbidden files (§16.4), files > 64 KiB, binary files, anything under `data/`, `datasets/`, `checkpoints/`, `outputs/`, `wandb/`. All text passes §16.2 redaction; any file whose redaction count > 0 is **dropped** and listed. Total ≤ `max_chars` (default 60 000); truncated files listed. `--dry-run` prints the file list and byte counts, sends nothing. Without `--yes`, the file list is printed and the user must confirm.

### 20.3 Request

`discover --dry-run --show-content` prints the complete initial system/user
messages as JSON after the collection report; it needs no endpoint credentials
and makes no request. `--show-content` without `--dry-run` is a usage error.
The preview and production request share message construction. A manifest
excluded or dropped from collected content also contributes no field-name
context. Configured exclusions are listed locally, with their reason, but are
absent from the outgoing contents and tree.

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

`reprollm rules accept c-3f9a1b [--severity S] [--field F]` appends to
`project-rules.yaml` (`source: discover`, `candidate_id`), copying bindings and
recording the approval time. Duplicate acceptance of an active candidate exits 2.
`rules add` creates a manual rule. `rules ignore` records an inactive candidate ID
in `ignored_candidates`; an already active candidate must be deactivated through
§7.3 instead. Acceptance may follow an earlier ignore, with active acceptance
winning the displayed state.

Candidate inspection uses the lexicographically last `.json` file in
`.reprollm/discover/`. It never searches an older discovery for an unknown ID.
`rules show CANDIDATE_ID` and the explicit candidates view fail with exit 2 on a
malformed latest file rather than falling back silently.

`rules list` prints active rules, latest candidates labelled accepted/ignored/pending,
and stored archive IDs with their derived state. Its established `--json` output
remains an array of complete active rule objects. `rules list --candidates --json`
instead returns an array sorted by candidate ID, each entry shaped as
`{"candidate": <complete §20.4 Candidate>, "status": "accepted|ignored|pending",
"source": ".reprollm/discover/<latest>.json"}`. The same explicit view without
`--json` prints the complete records for review. Missing or empty discovery
directories produce an empty candidate array; no status is added to persisted
Candidate documents.

`rules show ID` is read-only and emits the complete requested record with a relative
source path: an active rule gives `{"kind": "rule", "rule": <ProjectRule>,
"source": ".reprollm/project-rules.yaml"}`; a latest candidate gives
`{"kind": "candidate", "candidate": <Candidate>, "status": <computed status>,
"source": <latest relative path>}`; an archive gives `{"kind": "archive",
"archive": <RuleArchive>, "source": <archive relative path>, "state": <computed state>,
"note": <recovery-copy explanation>}`. Unknown active rule, candidate or archive
IDs exit 2. The display privacy rules in §7.3 apply to these inspection views.
Removal/restoration and lock-staleness requirements are defined in §7.3.

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
Findings: FAIL (2 critical, 5 warning)
Result: exit 1 (--fail-on critical; findings reach the threshold)
```

Symbols: `✖` CRITICAL, `▲` WARNING, `ℹ` INFO, `✔` PASS, `–` suppressed/skipped. With `--no-color`/non-TTY, symbols remain ASCII-safe alternatives (`X`, `!`, `i`, `+`, `-`).

`Findings: PASS` means no unsuppressed FAIL CRITICAL or WARNING findings remain;
otherwise report both counts as `Findings: FAIL (N critical, M warning)`.
`Result` states the actual exit code and effective `--fail-on`, including config
and explicit flag precedence. Its reason is `findings reach the threshold` for
exit 1, `no finding reaches the threshold` for exit 0, or `finding-based failure
disabled` for `never`. CLI calculates the exit once from the full unchanged report,
passes it and the effective threshold to the text renderer, and exits with that code.
Warnings at the default `critical` threshold therefore show Findings FAIL and exit 0.

Default text groups repeated FAIL WARNING findings only when both `rule_id` and
`fix_hint` match. Sort groups by rule ID; show the exact count, up to three example
messages and evidence locations in existing report order, one shared fix, and
`Use --details for every finding; --format json preserves all evidence.`
Single warnings and every CRITICAL, INFO, PASS, suppressed or skipped row remain
individual. Never infer a shared cause, normalize hints or change finding data.
`--details` emits every original row with the same visibility flags and symbols.
Summary counts, severities, JSON, GitHub annotations and exit semantics stay complete
and unchanged. No threshold or presentation fields are added to AuditReport.

---

## 22. Testing requirements

- T-01 Unit tests per module; every rule has ≥ 1 PASS and ≥ 1 FAIL test using minimal in-memory manifests or fixture repos.
- T-02 Golden fixture repos in `tests/fixtures/repos/` (see M1). Each has `expected/audit_L0.json`, later `audit_L1.json`, `lock.yaml`, `audit_L2.json`, `diff.json`. Snapshot comparison ignores `generated_at`, `reprollm_version`, `resolved_at`, `observed_at`, and the archive operation timestamp `archived_at`. Archive identity tests freeze `archived_at` when comparing filenames/hashes and verify content IDs against the original, unnormalized document; do not ignore mismatched archive IDs.
- T-03 Fixture git repos are materialized in a temp dir at test time by `tests/conftest.py::materialize_repo(name)` with `GIT_AUTHOR_NAME=ReproLLM Test`, `GIT_AUTHOR_EMAIL=test@reprollm.dev`, `GIT_AUTHOR_DATE=GIT_COMMITTER_DATE=2026-01-01T00:00:00Z`, so commit SHAs are deterministic across machines.
- T-04 No network: `respx` mocks all `httpx` calls; a session-scoped autouse fixture fails any unmocked request. Recorded Hub responses live in `tests/fixtures/hf_api/`.
- T-05 `nvidia-smi` and `git` are invoked through `reprollm/core/proc.py::run_cmd`, which tests monkeypatch; fixtures provide canned outputs (`tests/fixtures/nvidia_smi/*.txt`).
- T-06 Redaction: §16.5.
- T-07 CLI tests via `typer.testing.CliRunner`; JSON outputs validated against exported JSON Schemas.
- T-08 Coverage gate: ≥ 85 % overall from M3 onward; `core/redaction.py` 100 % branches.
- T-09 CI matrix: ubuntu-latest (py3.10, 3.11, 3.12), macos-latest (3.12), windows-latest (3.12, platform-safe tests via marker `-m "not slow and not linux_only"`). Regular CI excludes `slow` on every platform; nightly explicitly runs `tests/perf -m slow` without coverage instrumentation. Command-line marker overrides must preserve both the slow and platform exclusions. Coverage and security gates remain mandatory in regular CI.

---

## 23. JSON Schema export

`reprollm schema export --out schemas/` writes: `manifest.schema.json`, `lock.schema.json`, `run_record.schema.json`, `profile.schema.json`, `project_rules.schema.json`, `config.schema.json`, `audit_report.schema.json`, `diff_report.schema.json`, `discover_candidates.schema.json`, and `rule_archive.schema.json` (ten documents). R04-S upgrades only run_record.schema.json to support the run-specific version-1/version-2 contract; the other nine schema files retain their previous bytes. Conditional input_capture/fingerprint requirements are exported as JSON Schema; change/fingerprint equality is additionally checked by typed model validation. CI fails if the committed `schemas/` differ from a fresh export.
