# Record concurrent local-model conditions in separate workspaces

Use this recipe when an existing research project runs several conditions with
different manifests, commands or output files. Each condition gets its own
checkout, lock and run history. ReproLLM records the commands; your experiment
code and scheduler still manage model execution, scoring and resource allocation.

The explicit-command workflow below uses options present in published 0.6.1.
Current source writes run schema 2, with pre-child input capture and separate
post-child checks; legacy schema-1 input phase is unknown. See the
[runtime evidence contract](../run.md#what-a-real-run-records). Do not apply
current-source capture guarantees retrospectively to older records.

## Prepare one research project

Start with a committed project named `study`, outside the ReproLLM checkout.
Its experiment command must already work in the intended model environment.
For a resource-free introduction instead, use the
[first-experiment exercise](first-experiment.md).

The examples assume your own `experiment.py` accepts `--defense` and
`--batch-size`. Replace these with your actual entry point and parameters;
`experiment.py` is not a ReproLLM command or a bundled model implementation.
Prepare the applicable profiles, data, prompts, decoding settings, environment
declarations and scientific freeze in that project. For privacy experiments,
describe the actual `privacy.mechanism.params`, not just a condition label.

The following is a **partial** manifest fragment, not a complete declaration:

```yaml
models:
  primary:
    provider: local
    id: assets/model
    tokenizer:
      id: assets/model
custom:
  defense: D0
  batch_size: 64
execution:
  command: python experiment.py --defense D0 --batch-size 64
```

Choose batch size on development inputs before formal testing. A fixed seed and
greedy decoding do not establish that different batch sizes produce identical
outputs. Record any observed differences and keep the selected formal policy.

Keep working assets and outputs out of Git, for example:

```gitignore
assets/
raw/
.reprollm/runs/
```

Keep the manifest, lock, project rules and scientific inputs versioned. Avoid
ignoring the entire `.reprollm/` directory without explicitly tracking the rules
and configuration you need. Review any additional environment files separately.

## Isolate the conditions before launching either one

From the directory containing the clean, committed `study` project:

```bash
git -C study status --short
git clone --no-hardlinks study run-A
git clone --no-hardlinks study run-B
```

Require an empty status before cloning. Untracked files and ignored model assets
are not copied by Git. Materialize the required model/tokenizer files inside
each checkout's `assets/model`, and verify their identity against your intended
local snapshot. Copying is portable; hard links can share immutable files on the
same filesystem. Editing a hard-linked file changes every linked view. Symlinks
that resolve outside the project boundary are rejected; do not weaken that check.

Local file fingerprints do not establish an upstream model revision. Retain
unknown provenance explicitly, and keep independent content checks for any
required assets not covered by the lock's supported file inventory.

In `run-A`, set the actual D0 command and declarations. In `run-B`, set D1 and
its actual mechanism/configuration. Use independent output paths relative to
each checkout. Never have workers repeatedly overwrite a shared manifest,
project-rules file, lock or results file.

## Bind, lock and commit each condition

Run the following in **each** condition checkout. First inspect
`reprollm rules list --json`; add these example rules only if their IDs do not
already exist, and adapt the fields/flags to the real experiment:

```bash
mkdir -p raw
reprollm rules add --id project.defense --field custom.defense --severity CRITICAL --reason "The condition must agree with execution." --cli=--defense
reprollm rules add --id project.batch_size --field custom.batch_size --severity CRITICAL --reason "Batch size is part of this experiment." --cli=--batch-size
reprollm lock . --offline --hash-large-files
reprollm lock . --check
git add -u
git add reprollm.yaml reprollm.lock
git add -f .reprollm/project-rules.yaml
git diff --cached
git commit -m "experiment: freeze this condition's recording inputs"
git status --short
```

Review the staged changes and require a clean tree before execution. Include any
new scientific inputs and runtime declarations deliberately; `git add -u` does
not add new files. Keep inputs immutable while the child runs. Bindings record
passed values, not proof that the child consumed them; retain independent child
output or parser/request evidence where that distinction matters.

`--offline` avoids provider requests. `--hash-large-files` requests hashing of
recognized local weights beyond the default size threshold. A successful lock
write can still contain unresolved entries. `lock --check` checks manifest and
project-rule freshness; it does **not** rehash local model content. Inspect the
[lockfile scope](../lockfile.md#freshness-and-file-changes) and verify changed
assets independently before deliberately creating a new lock.

## Run and inspect the actual commands

In `run-A`:

```bash
reprollm run --name condition-A --capture-output -- python experiment.py --defense D0 --batch-size 64
reprollm runs list --json
```

In `run-B`, after its own lock and commit:

```bash
reprollm run --name condition-B --capture-output -- python experiment.py --defense D1 --batch-size 64
reprollm runs list --json
```

The commands may run concurrently in separate terminals/jobs when resources
permit. Select GPUs and capacity through your own scheduling policy; ReproLLM
does not reserve devices. Each child's `REPROLLM_RUN_ID` links its output to that
checkout's actual capture. Keep both the run ID and recorded Git commit.

Copy the real, complete IDs from the records. In the next examples, replace
`RUN_A` and `RUN_B` with those IDs; they are placeholders, not literal run names.
In `run-A`:

```bash
reprollm runs show RUN_A --json
reprollm audit . --format json --fail-on never --output raw/audit.json
reprollm export . --run RUN_A --output raw/REPRODUCIBILITY.md
reprollm diff .reprollm/runs/RUN_A/run.json ../run-B/.reprollm/runs/RUN_B/run.json --format json > raw/diff.json
```

`raw/` must exist before shell redirection; create it during project preparation.
No `--fail-on` is needed for an informational diff. `--fail-on NONE` is the
lowest drift threshold, not a switch that disables failure.

Check the child's exit code, capture warnings, bindings and scientific output
coverage. `status: completed` alone is insufficient. `audit --fail-on never`
retains findings without failing on severity; it does not make them pass or
hide usage/internal errors. A program that skips already-completed samples may
exit successfully with zero new generations. That is not a fresh model repeat.

## Preserve history and publish reviewed evidence

Run paths make cross-workspace comparisons explicit; bare run IDs are resolved
from the current project. Diff explains recorded state changes, not which
change caused a scientific outcome. Keep paired statistics in the research
project. See [semantic diff](../diff.md).

An explicit export of `RUN_A` uses that run's available snapshots and
observations even after the current declaration changes. Its Audit summary is
still a current-working-tree audit, not a re-audit of the historical run. Read
the source labels and limitations in [export](../export.md).

Condition commits and optional remote provenance refs preserve history; they
are not integration branches that must all be merged into the research
mainline. Publish reviewed per-condition evidence in separate directories.
Replacing one root manifest with every historical condition creates avoidable
merge conflicts and obscures which declaration is currently active.

Review files before sharing. Saved-output redaction does not sanitize original
terminal streams or arbitrary files written by the child. Preserve unsuccessful
findings and original run records; explain any publication-only redaction and
the original-byte hashes. A successful audit or capture does not establish
scientific correctness, model safety or verified child environment/consumption.
