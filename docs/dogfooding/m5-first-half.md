# M5 first-half validation

Validated on 2026-09-19 with Python 3.12.14 on macOS. This session delivers
M5-T01–T05, following the two-session sprint convention. It extends the
[M4 validation record](m4-lock.md) without advancing a repository pin, changing
a gold answer, or releasing a version.

## Tasks and review

| Task | Commit | Result |
|---|---|---|
| T01: normative secret redaction and corpus | `831d2e5` | Merged first through [PR #4](https://github.com/EnumaElish123/ReproLLM/pull/4), after explicit maintainer review under D-41 |
| T02: hardware and scheduler capture | `a723b47` | Bounded GPU queries, CPU count, UUID hashes, filtered scheduler namespaces |
| T03: files and declared bindings | `7b5192b` | Containment, original hashes, redacted text snapshots, all declared observations |
| T04: subprocess wrapper | `e020e76` | Atomic records, child exit preservation, signal forwarding, opt-in log tee, machine privacy |
| T05: run and inspection CLI | `83eaad6` | Config defaults, JSON/table inspection, unique prefixes, locked-fixture run snapshot |

The maintainer approved the padded-JWT correction in
[Issue #3](https://github.com/EnumaElish123/ReproLLM/issues/3). The normative
expression, corpus and tests now allow zero to two trailing `=` characters in
each segment. All 27 padding combinations are tested. T01's review CI passed
on all five matrix entries before approval and merge
([run](https://github.com/EnumaElish123/ReproLLM/actions/runs/35436613168)).

T03's sprint wording assigns manifest binding files `origin: binding`, while
normative §5.1 R-04 explicitly requires `origin: declared`. The implementation
follows R-04. Additional project-rule config paths use `origin: binding`.
This documented precedence resolution changes no schema.

`--no-snapshot` disables input `files[]` snapshots; mandatory manifest/lock
document references retain their redacted copies. Snapshot hashes refer to
original bytes, not redacted copies, as documented in [run.md](../run.md).
Identity/path removal belongs to the run persistence boundary (§5.1 R-10);
it does not change the nine reviewed patterns in `core/redaction.py`.

## Quality gate

Acceptance tests were written before each implementation. Every task passed
the full local pytest, lint, formatting, strict typing, schema freshness and
generated-documentation checks before its commit.

| Checkpoint | Tests | Overall branch coverage |
|---|---|---|
| T01 | 867 passed | 93.00% |
| T02 | 890 passed | 93.09% |
| T03 | 941 passed | 93.03% |
| T04 | 957 passed, 2 Linux-only tests skipped | 92.79% |
| T05 | 967 passed, 2 Linux-only tests skipped, 36.93 s | 92.61% |

Final commands:

```console
.venv/bin/pytest -q --cov=reprollm --cov-report=term --cov-fail-under=85
.venv/bin/coverage report --fail-under=100 --include=src/reprollm/core/redaction.py
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/
.venv/bin/reprollm schema export --out <temporary-schema-directory>
diff -r schemas <temporary-schema-directory>
.venv/bin/python scripts/gen_rules_doc.py --check
.venv/bin/python scripts/gen_profiles_doc.py --check
```

The environment's executables were used directly because `uv` is not on PATH.
All HTTP in tests remains mocked. The redaction module has **100% statement
and branch coverage**, including streaming PEM suppression. The run-specific
identity/path helper also has 100% coverage. The Linux signal cases exercise
SIGINT and SIGTERM in CI; macOS skips are explicit, not a claim of Linux
verification. CI retains Ubuntu Python 3.10/3.11/3.12 and macOS/Windows 3.12.

The new `hf_vllm_eval/expected/run.json` was reviewed against source files and
independent SHA-256 calculations. It records both CLI temperature `1.0` and
config temperature `0.0`, config max tokens `2048`, model ID `Qwen/Qwen3-32B`,
two declared files, clean fixture Git state, and a redacted PATH. JSON Schema
validation passes. Existing audit/lock snapshots and exported schemas are
unchanged. The dirty-tree fixture also produces a redacted patch whose hash
matches the saved patch bytes.

## Five-project Gate A

All original checkouts had the expected upstream origin, exact SHA and empty
porcelain status before and after validation. Every mutating command ran in a
disposable shared clone.

| Target | SHA | L0 seconds | C/W/I/P/S |
|---|---|---:|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 6.746 | 0/14/1/8/1 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 0.586 | 0/16/1/8/1 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 0.797 | 1/15/1/7/1 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 0.567 | 0/7/1/7/1 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0.283 | 0/7/1/7/1 |

For each original checkout:

```console
reprollm -v audit <checkout> --level 0 --format json --fail-on never --output <outside-report>
reprollm doctor --json
```

All audit and doctor exits were 0. The complete rule/status and dependency
sets, profiles/confidences, provider/backend/adapter/dataset/trust hints, HF
IDs with physical source lines, relative evidence paths, and scan diagnostics
match [val.md §§3–6](../../val.md). There are **zero gold deltas** from M4.
The lm-eval scan still discloses its 500/816 file limit; LlamaFactory's tracked
`.env.local` remains CRITICAL. Optional `nvidia-smi`/`uv` absence remains explicit.
`init` and manifest loading behavior were unchanged, so no init gate was activated.

## New command validation in all five disposable clones

These are bounded command-contract checks, not model inference or a substitute
for Gate B. Before running ReproLLM, the driver independently recorded each
upstream README's raw SHA-256/size, literal config bytes, expected observations,
and expected output bytes. No ReproLLM output was used to redefine a gold answer.

Each clone received a temporary manifest declaring `validation-inputs.json`
containing `{"temperature":0.0}`. The temperature binding names CLI
`--temperature`, config `validation-inputs.json:temperature`, and environment
`REPROLLM_VALIDATION_TEMPERATURE=0.25`. README is an argv input. The child is
ordinary Python: it writes `{"score":1}` to `validation-result.json`, prints
its run ID and a synthetic HF token, and exits 0. A second child runs in
`work/`, exits 3, and uses `--no-snapshot --env-capture all`.

The child environment is minimal, with synthetic credentials only. No saved
HF credential, paid API key, model weights, dataset download or GPU workload
is involved.

```console
reprollm run --cwd <clone> --name gate-a-snapshot --capture-output -- python -c <bounded-script> README.md --temperature 1.0
reprollm run --cwd <clone>/work --name gate-a-no-snapshot --no-snapshot --env-capture all -- python -c 'import sys; sys.exit(3)' ../README.md --temperature=1.0
reprollm runs list --json
reprollm runs list
reprollm runs show <unique-prefix> --json
reprollm runs show <full-run-id>
```

Both show forms ran for both records in each clone. Expected exits were 0 for
every command except the second `run`, which propagated 3. All matched.

| Target | Snapshot run seconds | No-snapshot run seconds | Result |
|---|---:|---:|---|
| lm-evaluation-harness | 0.315 | 0.296 | All assertions passed |
| FastChat | 0.287 | 0.277 | All assertions passed |
| LlamaFactory | 0.324 | 0.254 | All assertions passed |
| HarmBench | 0.815 | 0.256 | All assertions passed |
| llm-dp-finetune | 0.263 | 0.264 | All assertions passed |

All ten records validate against the exported schema, retain the upstream
commit, have `status: completed` and zero warnings, and record CLI/config/env
observations `[1.0, 0.0, 0.25]` with their exact source keys/paths. File sets,
origins, sizes, raw hashes and output hashes match the independent inputs.
The two working directories are `.` and `work`. Snapshots exist only for the
first run; default-off logs are absent in the second. The synthetic terminal
token is present in the echoed output and absent from saved logs.

Known secret environment variables are presence-only. The unallowlisted
synthetic password variable is absent by default and presence-only in `all`
mode. Recursive reads of every run artifact found no synthetic credential,
current hostname, current username or clone absolute path. JSON show output
is byte-identical to the saved record. Unique prefixes, table output and
human-readable binding summaries all worked.

Raw reports, independent inputs, per-command timings and the ten sanitized
run directories are preserved outside the worktree at
`../dogfooding/m5-first-half-2026-09-19/`. Machine-readable records are
`gate-a-record.json` and `gate-run-record.json`; each target also has a
`*-run-expected.json` input contract.

## Remaining scope

M5's second session owns T06–T10: runtime consistency rules and audit run
loading, the integrated leakage security gate, full user documentation,
resource validation, and release. Recording conflicting observations now
works; audit does not yet compare those run observations. Exactly the four
Issue #2 runtime rule placeholders remain.

Per `val.md`, M5 Gate B activates at milestone completion or release, not this
half-sprint. Its five inference/training/judge scenarios still need independently
reviewed bounded expectations and provisioned resources. This session does
not claim those checks passed. M4's networked Linux H2 and successful gated
model-file access remain pending as previously recorded. No version bump,
tag, package publication, diff/export/discover implementation, or unrelated
workspace change was made.
