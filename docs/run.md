# Record and inspect an experiment run

`reprollm run` executes your command and records its runtime evidence under
`.reprollm/runs/<run_id>/`. It preserves the child's arguments, environment and
exit code, and adds `REPROLLM_RUN_ID` and `REPROLLM_RUN_DIR` to the child environment.
It does not invoke a shell; put the command after `--`.

```console
reprollm run --name baseline -- python eval.py --temperature 0.0
reprollm runs list
reprollm runs show <run-id-or-unique-prefix>
reprollm runs show <run-id-or-unique-prefix> --json
reprollm audit .
```

Run inspection commands use the current repository. `runs list --json` emits
summaries; `runs show --json` emits the saved record unchanged. Records are
ordered by start time, with run ID breaking ties. Corrupt records generate a
warning and are skipped by listing and audit. Audit reads only `run.json` and
compares the latest valid record; it does not silently reconstruct it from snapshots.

With a manifest and at least one valid run, audit reaches Level 2 even without
a lock. Lock-dependent comparisons still require `reprollm.lock`. A missing
manifest permits basic capture with a warning, but audit remains at Level 0.

## Captured evidence

| Evidence | Recorded form |
|---|---|
| Execution | Redacted argv, relative working directory, optional name, UTC start/end, duration, status and child exit code |
| Git | Commit, branch, dirty state, modified/untracked counts, sanitized remote, redacted tracked-file diff when dirty |
| Environment | Python/OS, installed LLM-critical distribution versions, filtered environment variables, hashed hostname |
| Hardware | CPU count; GPU names, memory, driver and hashed UUIDs when bounded `nvidia-smi` queries succeed |
| Scheduler | Filtered SLURM, PBS and LSF variables when present |
| Documents | Original manifest/lock hashes and redacted `manifest.yaml` / `lock.yaml` copies |
| Inputs | Repository-contained argv and declared files: path, origin, size, original hash and optional redacted text snapshot |
| Bindings | Every observation from explicitly declared CLI flags, YAML/JSON/TOML keys and environment variables |
| Outputs | Hashes and sizes for repository-contained files matching manifest `artifacts.outputs` globs |

Most metadata, files and bindings are collected after the child exits. If a
command changes its input files, their recorded hashes describe the final bytes.
Unavailable GPU metadata is recorded as `source: unavailable`; it does not mean
the experiment used no GPU. Capture failures become warnings without replacing
the child's exit code. Always inspect `warnings` before relying on a record.

A minimal `status: running` record is written before launch. Final records are
written atomically. A normally terminated child has `status: completed` even
when its exit code is nonzero; check `exit_code` as well as status. A command
that cannot start leaves `failed` evidence, and an interrupted child records
`interrupted`. A machine crash can leave the initial `running` record.

Capture does not install packages, import the LLM stack, download models, read
model tensors, fingerprint dataset contents, trace functions, or recover hidden
library defaults. It does not query a provider or verify what a remote model
actually executed. Undeclared command flags are not interpreted as parameters.
Untracked file contents are not included in the Git patch; only explicitly
captured inputs receive snapshots. User-created output contents are not copied
or rewritten by ReproLLM.

## Declare the values you want compared

For an evaluation script accepting `--temperature`, add these fields to
`reprollm.yaml` and create `configs/eval.yaml` with `sampling.temperature: 0.0`:

```yaml
generation:
  temperature: 0.0
bindings:
  generation.temperature:
    cli: --temperature
    config: configs/eval.yaml:sampling.temperature
```

This CPU-only command demonstrates the conflict without running a model:

```console
reprollm run -- python -c pass --config configs/eval.yaml --temperature 1.0
reprollm audit .
```

The audit emits `consistency.generation_params` at CRITICAL, with manifest `0.0`,
CLI `1.0` and config `0.0` in its evidence. It retains repeated flags and all
declared sources instead of choosing a value that hides disagreement. Numeric
strings and numbers are normalized for comparison (`"0"` equals `0.0`).

The other runtime checks compare lock/tree/run file hashes, observed model IDs
and revisions, LLM-critical package versions, and accepted `custom.*` bindings
in `.reprollm/project-rules.yaml`. Resolved lock revisions represent mutable
manifest references; explicit commit declarations are also checked. Package
version changes are WARNING; packages present on only one side are INFO.
Custom-field conflicts retain their accepted project-rule severity. These
checks report missing evidence as skipped, rather than claiming a match.

## Environment capture and redaction

The default `allowlist` captures selected reproducibility-related names/prefixes
such as `CUDA_`, `TORCH_`, `PYTHON`, `HF_HOME` and `TOKENIZERS_PARALLELISM`.
Known credentials such as `OPENAI_API_KEY`, `HF_TOKEN` and
`AWS_SECRET_ACCESS_KEY` are stored only as `{"present": true}`. An unlisted
custom variable such as `MY_SERVICE_PASSWORD` is absent in this mode.

`--env-capture all` includes other names, but secret names still get only the
presence marker. Name checks take priority over allowlists. For example,
`SSH_AUTH_SOCK` matches the `AUTH` segment and becomes presence-only if selected;
this intentional false positive protects credentials at the cost of detail.
`MAX_TOKENS` and `TOKENIZERS_PARALLELISM` do not match the singular `TOKEN` segment.
See the complete [normative policy](plan/01_specification.md#16-secret-redaction-policy-d-19-d-20--normative).

Configure defaults in `.reprollm/config.yaml`:

```yaml
schema_version: 1
run:
  env_capture: allowlist
  extra_env_allowlist: [EXPERIMENT_]
  capture_output: false
  snapshot_max_bytes: 1048576
```

Saved argv, values, text snapshots, patches and opt-in logs apply the nine
secret-pattern classes: OpenAI, Hugging Face, GitHub, AWS access-key IDs, Slack,
JWT, private-key PEM, URL credentials and generic secret key/value pairs.
Run persistence also removes the current hostname/username and replaces
absolute paths with repository-relative paths or a redacted marker.

These are deterministic name and pattern rules, not a detector for arbitrary
confidential text. Unknown token formats, personal data, and secrets printed
without a matching pattern may need manual removal before sharing. The child
receives its original environment and prints original output to the terminal.
`--capture-output` redacts the **saved** `stdout.log` and `stderr.log`; it does
not sanitize the terminal or logs written by the experiment itself.

## Hashes and snapshots

`files[].sha256` hashes the **original bytes**. A snapshot is a separate redacted
copy and can have a different hash. Compare the recorded hash against original
inputs or the lock, rather than hashing the snapshot to verify the original.
`patch_sha256`, in contrast, hashes the saved redacted patch bytes.

Only regular files resolving inside the repository are eligible. Forbidden
names such as `.env` and private-key files are hash-only with `redacted: true`
and `snapshot: null`. Binary files and text over the configured size limit are
also hash-only. More than 200 inputs disables file snapshots with a warning.
`--no-snapshot` disables `files[]` snapshots; manifest/lock document copies remain.

Manifest binding config paths have `origin: declared` under specification
§5.1 R-04. Additional project-rule config paths have `origin: binding`; argv-only
files have `origin: argv`. No command modifies the source input files.

## Write experiment outputs into the run directory

Inside your own Python experiment, the two injected variables connect outputs
to the run record:

```python
import json
import os
from pathlib import Path

run_id = os.environ["REPROLLM_RUN_ID"]
artifacts = Path(os.environ["REPROLLM_RUN_DIR"]) / "artifacts"
artifacts.mkdir(exist_ok=True)
(artifacts / "metrics.json").write_text(
    json.dumps({"run_id": run_id, "accuracy": 0.75}), encoding="utf-8"
)
```

`REPROLLM_RUN_DIR` is an absolute path for the child to use, not a value to store
in shared metrics. Output collection uses repository-relative globs:

```yaml
artifacts:
  outputs: [.reprollm/runs/*/artifacts/*.json]
```

This glob can include older runs' files; narrow it if you want a smaller set.
The child owns these artifacts. ReproLLM records their hashes and does not redact
or rewrite their contents, even when they sit inside `.reprollm/runs/`.

On SLURM, place `reprollm run -- python eval.py ...` inside the allocated
`sbatch` script or launch it through `srun`, so capture occurs on the compute
node. Signals are forwarded to the immediate child; scheduler-specific signal
behavior still needs verification on the target cluster.

## Share selected records

Inspect `runs show`, warnings, JSON, snapshots, patches and saved logs before
sharing. Review child-created artifacts separately. Commit only selected run
directories after checking their contents:

```console
git add .reprollm/runs/<run-id>
git diff --cached --stat
git diff --cached
```

If runs are ignored locally, use `git add -f` only for the reviewed directory.
Review binary or large child artifacts outside Git's text diff before adding
them. A redaction bypass should be reported privately using [SECURITY.md](../SECURITY.md).
