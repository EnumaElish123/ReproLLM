# Replay the stdlib evidence layer

This A01-B case is **supplementary L2 evidence**. It installs one candidate wheel
in two fresh environments, clones two disposable input projects at independent
paths, and runs the existing recipe's standard-library child. The second input
project starts from an independent copy of the [shared recipe package](replay/recipe/README.md).
It does not install lm-eval, load a model, download GSM8K, use a GPU, contact a
provider or consume credentials. Formal native and resource gates remain BLOCKED.

The original [D01 recipe](../../../examples/lm_eval_replay/README.md) and its
[independent expectations](../../../examples/lm_eval_replay/expected.json) remain
unchanged. The copied upstream `gsm8k.yaml` comes from the MIT-licensed framework
at `b954108c9baaaa934b4ad842033b31a97ee30816`; its SHA-256 is
`82eb1780b263bc040729032b3e076990c7933f42163c91e359f38820dd1d8833`.
The CPU fixture provides that reference file at the declared relative path; it
does not contain or execute the complete upstream framework.

## Prerequisites and the candidate wheel

Use Python 3.10 or newer, Git supporting `git init -b`, and a checkout containing
this guide and [the public runner](../../../scripts/a01_local_replay.py). The host
runner requires PyYAML; the actual product commands run in newly created venvs,
with isolated Python and an import-location/wheel-hash check reused from D02.
The host's source privacy policy is used only to reject unsafe evidence, not to
provide the product CLI under test.

This session reuses the S4-B wheel built from
`a4d895d4f30f6f74421d7f1cd96606f9b0baba15`, version `0.7.0`:

```text
reprollm-0.7.0-py3-none-any.whl
SHA-256 0be12d1d44a07e1ab29459c161cf67fcdc48a0934d1e57d593cc5887ac6049ff
```

The exact [build manifest](replay/build-manifest.json) retains that original
source association. Later tool/document commits do not rewrite the build SHA.
The wheel, sdist and dependency wheelhouse are not included in Git or published
by this session. `pip install reprollm` from PyPI does not select this candidate.

If the wheel is unavailable, obtain the source commit in a separate checkout
and build it locally once. For example, starting in an existing public clone:

```console
git worktree add --detach <build-checkout> a4d895d4f30f6f74421d7f1cd96606f9b0baba15
```

Inside that build checkout, install its locked environment and build:

```console
uv sync --locked --dev
uv build
```

Check the rebuilt wheel hash against the value above before using the recorded
manifest. If it differs, investigate the source/build-environment delta and
create a separate correctly associated manifest/result; do not edit the old
manifest to pretend that the new bytes were the recorded wheel.

Prepare software dependencies while package-index access is available. These
commands download packages, not models or datasets. The wheelhouse is a local
prerequisite, not an asset silently supplied by this evidence bundle:

```console
uv export --locked --no-dev --no-emit-project --format requirements-txt --output-file <runtime-requirements.txt>
python -m pip download --dest <wheelhouse> --requirement <runtime-requirements.txt>
python -m pip download --dest <wheelhouse> PyYAML==6.0.3
```

Use a wheelhouse compatible with the target Python/platform. The recorded
installation package map is in each replay's `results.json`. A different Python
or dependency set is separately identified evidence. Do not copy a development
venv into the fresh environments and call that independent installation.

## Run both independent replays

Use new, short paths outside the source checkout for `--work-root`. Raw logs,
temporary venvs and disposable Git projects stay there. `--output-dir` must be
empty or absent and receives only the checked portable package. Windows Git/MSYS
may need an ordinary user terminal because restricted process sandboxes can
prevent local cloning; this is an environment failure, not a passed replay.

In PowerShell, replace the angle-bracket placeholders with local paths. `$Python`
is a host interpreter with PyYAML installed; the runner creates the tested venvs:

```powershell
$Python = '<host-python>'
$Wheel = '<local-wheel>'
$Manifest = 'docs/dogfooding/2026-10-18-a01-local/replay/build-manifest.json'
$Wheelhouse = '<prepared-wheelhouse>'
$Work = '<new-short-private-directory-outside-checkout>'
$Output = '<new-empty-public-result-directory>'
& $Python scripts/a01_local_replay.py `
  --wheel $Wheel --build-manifest $Manifest `
  --work-root $Work --output-dir $Output `
  --no-index --find-links $Wheelhouse
```

The same script arguments work in a normal Linux/macOS shell. Installation uses
only the supplied wheelhouse with `--no-index`; product CLI commands block socket
connections through the existing D02 offline launcher. The inspected child is
the unchanged stdlib-only `probe.py`, launched with isolated Python and a cleaned
environment. It makes no network calls. No model/provider variables or secrets
are forwarded by the launcher.

The runner preserves source bytes during Git checkout (`core.autocrlf=false`)
and verifies every D01 input hash before either run. Each disposable manifest
changes only the project name and the declared command to identify this stdlib
case; the original formal manifest files remain unchanged. The mutation case
also declares its additional probe option.

## Independent expectations

Each installation executes these three captures through the installed CLI:

| Capture | Child actually reads | Child input after completion | Required capture/export |
|---|---|---|---|
| A | cap 32 and the exact A config bytes | Unchanged | Observed cap 32, pre-child hashes/snapshots, selected export 32 |
| B | cap 48 and the exact B config bytes | Unchanged | Observed cap 48, pre-child hashes/snapshots, selected export 48 |
| Consume then mutate | cap 32; writes its receipt before rewriting | cap 96 | Baseline and selected export remain 32; post-child hash/check says changed |

The child receipt's complete parsed configuration must equal an independent
PyYAML parse of the original input bytes. Its hash must equal a direct SHA-256
of those bytes. Four captured source/config files must have matching sizes,
hashes and exact snapshot bytes. The lock's manifest/config hashes, saved
manifest/lock bytes and output receipt hash/size are independently checked.
The counter `input_snapshot_files_checked: 4` counts files, not bytes.

A/B snapshots preserve the recipe's stop tokens and relative paths. A/B code
must be clean; the mutation child intentionally dirties its tracked input and
the recorder must report that fact. Each capture gets its own saved run, lock,
receipt, audit, selected export and empty self-diff.

The complete non-NONE A/B drift set must be exactly:

| Path | Expected |
|---|---|
| `generation.max_tokens` | 32 → 48, HIGH |
| `files.validation/eval.yaml.sha256` | Different direct input hashes, HIGH |
| `code.commit` | Two deliberately committed variants, MEDIUM |

The target leaf is asserted independently of the config hash. Missing or
duplicate paths, a wrong cap, unexpected additional drift and wrong severities
fail the runner. The full saved `pair-diff.json` retains NONE changes; these are
run identity/timing metadata, not additional experimental drift. Self-diffs
have no changes. A/B pair diff exits 1 at `--fail-on HIGH`; ordinary successful
commands exit 0. Audits use `--fail-on never` and preserve all findings, including
unresolved offline/framework fields, rather than claiming zero findings.

ReproLLM continues to say child environment/consumption is **unverified**. The
independent stdlib receipt supplies evidence for this named child only. Reading
a model revision, task name or limit from a config does not prove loading model
weights, reading 100 dataset items, using a chat template or executing a metric.

## Results, integrity and remaining limits

Read [the replay summary](replay/summary.json), each installation's `results.json`,
and their complete run/diff/export artifacts. [SHA256SUMS](replay/SHA256SUMS)
checks every shared file except the checksum file itself. Run IDs, timestamps,
duration and independently created input commits can differ between replays;
input identity, consumed caps and required semantic assertions must agree.

The frozen runner's accepted attempt completed both independent replays in
**40.813 seconds**. Each replay recorded 22 product commands: 21 exited 0 and
the A/B threshold diff exited the expected 1. The 44 product-command durations
sum to 24.798 seconds; this is part of the total wall time, not an additional
elapsed interval. Both installations and import-isolation checks succeeded.
All six captures passed; the actual NONE diff fields are exactly `ended_at`,
`run_id` and `started_at`. The package has 109 files with 108 original-byte
checksums, including six original schema-2 run records. New report envelopes,
child receipts, audits and diff documents retain their respective schema 1.

[Replay attempts](replay-attempts.json) preserve four earlier rejected attempts:
a sandbox Git process failure, checkout line-ending conversion, an incorrect
tool expectation about the mutation child's dirty tree, and an overbroad tool
privacy matcher. Their private original streams remain referenced by hashes;
none was promoted to PASS. The accepted attempt reran the entire two-path
workflow with the final tool. [Focused regression evidence](replay-regressions.json)
records 26 passing checks and the preceding deliberate failures; the main
session report supplies the separate shared full quality gate.

The runner checks the package against the existing secret policy, known local
identity and machine-path patterns before copying it from private staging. It
does not rewrite unsafe evidence to obtain PASS. These bounded checks do not
prove that every possible private datum is detectable; the session's independent
review remains necessary. Original import/install logs stay private; portable
receipts contain logical executables, exits, timings and original-stream hashes.

This is author-operated installation/replay evidence, not independent external
adoption. L3 native execution, VAL-R01/02/03 and formal release resource gates
retain their [BLOCKED boundaries](../pending-resource-validation.md).
