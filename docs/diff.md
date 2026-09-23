# Compare experiment states

`reprollm diff A B` explains recorded differences that may affect reproducibility.
It is available in the development checkout for the planned 0.4.0 release.
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
