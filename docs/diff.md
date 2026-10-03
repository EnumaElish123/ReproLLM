# Compare experiment states

`reprollm diff A B` explains recorded differences that may affect reproducibility.
It has been available since 0.4.0; these docs track the current main branch.
It reads local artifacts without running a model or contacting a provider.

```bash
reprollm runs list
reprollm diff <run-a-id> <run-b-id>
reprollm diff before/reprollm.lock after/reprollm.lock --format json
reprollm diff .reprollm/runs/<run-id> reprollm.lock --fail-on HIGH
```

Each input can be a run ID, a unique ID prefix, a `run.json`, its directory, or a
lockfile. Ambiguous prefixes produce an error listing the candidates. Run inputs
need their referenced manifest/lock snapshots alongside the record; missing or
invalid snapshots are errors. A lockfile includes an adjacent `reprollm.yaml`
when present. Comparing a run to a lock also shows fields only the run recorded,
such as hardware and the command, as added or removed.

## Compare recent successful runs

On main (unreleased), use this shortcut to select the two newest successful
records in the current project:

```console
reprollm diff --latest-successful
reprollm diff --latest-successful --name baseline --format json --fail-on HIGH
```

The older selected record is A and the newest is B. Text and JSON reports include
their full IDs. Success requires completed status and exit code 0; labels match
exactly. Without `--name`, the two records may have different labels. Filters
and start-time/ID ordering are the same as [run listing](run.md#find-the-runs-you-need).

If fewer than two records qualify, the command exits 2 and suggests listing
successful runs. It keeps corruption warnings visible and skips invalid records.
Once a pair is selected, missing or invalid snapshots cause an error; the command
does not substitute an older pair. A current file named like a selected ID cannot
replace that stored run. The comparison still uses captured historical values
and the usual profile/threshold policy.

Use either this shortcut or explicit A/B inputs. `--name` is available only with
`--latest-successful`; names are labels, not run-ID aliases. A successful child
process does not prove complete capture or comparable experiments. Review the
resolved IDs and drift report before relying on the result.

## Reading the output

Every `reprollm diff` report lists only what changed between the two
experiments, grouped by section, each line as `path  A → B  [SEVERITY]`.
Here is what each kind of line means:

| Line kind | Meaning | Why it can change |
|---|---|---|
| `generation.max_tokens 32 → 48 [HIGH]` | A declared experiment parameter differs. | You (or a config) changed it between runs — the usual suspect for result differences. |
| `files.configs/eval.yaml.sha256 … [HIGH]` | A tracked input **file's content hash** differs. | The file's bytes changed (often the same edit as the parameter above — the hash proves the file on disk really changed, independent of what the manifest declares). The hash is not meant to be read; it is meant to be compared. |
| `code.commit … [MEDIUM]` + `code changed` | The two runs executed at different git commits. | Expected when each variant's inputs were committed separately; becomes a real warning when the tree was dirty (`[HIGH]`). |
| `models.*`, `datasets.*`, `prompts.*`, `inference.*` … | Identity drift in experiment inputs (revision, prompt hash, backend…). | Model/dataset/prompt changed — results are usually not comparable. |
| `environment.packages.torch 2.8.0 → 2.8.1 [MEDIUM]` | A dependency changed at patch level. | Major/minor bumps raise the severity (`MEDIUM_HIGH`). |
| `run_id`, `started_at`, `duration_seconds` … `[NONE]` | Bookkeeping fields that always differ. | Listed for completeness; never counted as drift. |

The final verdict line summarizes: `HIGH` present → *not directly
comparable*; `MEDIUM` → *results may differ; review the changes above*;
only `LOW`/`NONE` → *no reproducibility-relevant drift detected*.

Severity comes from the drift table (`drift_severity.yaml`), which profiles
can override; see the rest of this guide for the full table and
version-component semantics.

## What gets compared

Both inputs become a State with a value and provenance for every field. Effective
values follow `run CLI > run config > run environment > lock > manifest > default`.
Diff compares those effective values. It normalizes numeric strings, booleans and
lists with the same rules used by runtime consistency checks. Added and removed
fields receive the same severity as changes to an existing field.

Other sources remain available as alternatives. A change with conflicting sources
has a note such as `a has inconsistent sources (see audit)`. Use `reprollm audit`
to see the source evidence for the latest run against the current manifest, lock
and working files. Diff uses each run's captured declarations. Thus changing the
current manifest does not rewrite historical comparisons. A run compared with
itself has no changes, even if it contains internal source conflicts.

Values are compared before redaction. Two distinct secrets still count as a
change when both displayed values become the same redaction marker. JSON retains
full non-secret hashes; text shortens long hashes to 12 characters.

## Drift policy, version 1

The [complete ordered table](../src/reprollm/diff/drift_severity.yaml) is shipped
with the package. These are default judgments about experiment comparability:

| Severity | Typical fields | Verdict |
|---|---|---|
| HIGH | model/data identity, prompts, generation, training, privacy | These runs are not directly comparable. |
| MEDIUM_HIGH | critical package major/minor versions, preprocessing, evaluation settings | Results may differ; review the changes above. |
| MEDIUM | dtype, parallelism, Python, GPU model, clean commit changes | Results may differ; review the changes above. |
| LOW | branch name, GPU driver, GPU memory utilization | No reproducibility-relevant drift detected. |
| NONE | run IDs, timestamps, durations, hashed host identity | No reproducibility-relevant drift detected. |

The verdict uses the highest severity across all changes. LOW is advisory under
this default policy: these fields alone do not block comparability. This is not a
guarantee of identical results; unrecorded inputs and nondeterminism are outside
the comparison. You can strengthen the policy for your experiment.

First matching table entry wins; an unmatched field defaults to MEDIUM. `*`
matches one dotted field segment. For `files.*.sha256`, it matches the complete
file path, including slashes and dots. A changed `code.commit` is MEDIUM when both
trees are clean and HIGH if either was dirty. The note identifies the dirty side.

For `environment.packages.*` and `inference.version`, differing major or minor
versions use the matched table severity. Patch or finer changes lower it by one
level, with a LOW floor: `HIGH → MEDIUM_HIGH → MEDIUM → LOW`. Invalid versions use
ordinary value comparison. Examples:

| Change | Severity |
|---|---|
| torch 2.8.0 → 2.9.0 | MEDIUM_HIGH |
| torch 2.8.0 → 2.8.1 | MEDIUM |
| vLLM 0.10.0 → 0.11.0 | MEDIUM_HIGH |
| numpy 2.0.0 → 2.0.1 | LOW |

The torch patch case is MEDIUM under specification §18.1 and the approved table;
the LOW example in the original M6 task plan is inconsistent with that rule.

## Display and exit thresholds

```bash
reprollm diff <a> <b> --min-severity HIGH --format json
reprollm diff <a> <b> --min-severity HIGH --fail-on MEDIUM
reprollm --no-color diff <a> <b>
```

`--min-severity` filters displayed changes only. JSON records `filtered_below`,
while `summary`, the verdict and `--fail-on` still use the complete comparison.
Without `--fail-on`, a successful comparison exits 0 even when it finds HIGH
drift. With a threshold it exits 1 when any change meets or exceeds it. Invalid
inputs exit 2; internal failures exit 3.

## Override the policy

Create `.reprollm/profiles/strict_hardware.yaml` in your experiment:

```yaml
schema_version: 1
name: strict_hardware
description: Treat GPU model changes as identity changes for this experiment.
extends: [inference]
rules: []
drift_overrides:
  "hardware.gpus.*.name": HIGH
  "inference.gpu_memory_utilization": MEDIUM
```

Include `strict_hardware` in `experiment.profiles` before recording the runs.
Overrides precede the built-in table; child profiles override inherited values.
Profiles from input A, then B, are resolved with duplicates removed, using profile
definitions in the current project. Keep the profile file with your shared
experiment so recipients can use the same policy. Version-component adjustments
still apply after matching a package override.

## Example: prompt and temperature changes

The following excerpt comes from the tested `hf_vllm_eval` fixture. It captures
`python -c pass` twice to exercise the recorder; it does not run inference. Before
the second capture, the test appends a prompt line, refreshes the mocked lock,
commits the changed inputs, and changes `--temperature` from 1.0 to 0.7.

```text
prompts
  prompts.system.sha256  sha256:1012fd0edf9e → sha256:f3773a23d712  [HIGH]
  prompts.system.size_bytes  162 → 180  [MEDIUM]

files
  files.prompts/system.txt.sha256  sha256:1012fd0edf9e → sha256:f3773a23d712  [HIGH]

generation
  generation.temperature  1.0 → 0.7  [HIGH]
    a has inconsistent sources (see audit); b has inconsistent sources (see audit)

code
  code.commit  ff0e12644514 → 506d9fd8371f  [MEDIUM]
    code changed
```

The complete report also shows argv and run ID changes, then concludes:

```text
Highest drift: HIGH (3 changes). These runs are not directly comparable.
```

The prompt appears under both its semantic role and the captured file hash.
Both runs disagree with the declared/configured temperature of 0.0, hence the
source-conflict notes. The three HIGH entries identify fields, not three
independent causes. See the [complete JSON and text fixtures](../tests/fixtures/repos/hf_vllm_eval/expected/).
