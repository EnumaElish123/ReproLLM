# M5 second-half validation

Validated on 2026-09-19 with Python 3.12.14 on macOS, starting from the
[first-half report](m5-first-half.md) and baseline commit `e678d2e`.
Scope is M5-T06–T10. T06–T08 have implementation and local verification;
resource acceptance and release remain incomplete.

## Delivery status

| Task | Local result | Commit / remote status |
|---|---|---|
| T06: runtime consistency and audit run loading | Implemented; 990 tests pass; reviewed post-run fixture | Uncommitted on `codex/m5-second-half`; D-41 engine review still required |
| T07: integrated leakage gate | Both environment modes pass; CI and release build steps added | Uncommitted |
| T08: runtime documentation | Guide, README, security policy and index updated; installed-package example executes | Uncommitted |
| T09: real resource acceptance | All unaffected Gate A checks pass; Gate B is blocked | No milestone acceptance claim |
| T10: 0.3.0 release | Draft notes and isolated wheel/sdist preflight prepared | No version bump, tag or publication |

Two automatic permission reviews for `git add` timed out. The first tool response
allowed one retry; that retry timed out too. Neither staging operation executed,
and the queued commit did not execute. The tool did not identify a code-safety
problem. Explicit local staging/commit approval was requested, while all
unaffected implementation and validation continued. No second-half changes were
pushed and no new remote CI result is claimed.

The planned per-task commit sequence is preserved in separate local delivery
patches. The previous unrelated `.codex-pet-runs/`, `hatch-runs/` and `output/`
directories were neither modified nor included. No schema, frozen rule ID,
dependency version or validation pin changed.

The engine change is subject to
[D-41](../plan/00_architecture_and_decisions.md):
“Any PR touching `core/redaction.py`, `core/engine.py`, or a schema requires
explicit maintainer review.” T01's earlier approval does not cover this change.
The source review is still required before merging; T01 remains the first
merged M5 implementation as required by the sprint forbidden zone.

## Quality gates

Acceptance tests were added before the corresponding implementation. The first
T06 run demonstrated the missing run loading and runtime comparisons. Additional
coverage checks timezone ordering, missing timestamps, deterministic ties,
corrupt/symlink-escaping records, latest-record selection, normalized observations,
lock/tree/run evidence, resolved versus explicit model revisions, package presence,
custom-rule severity ownership and redacted finding values.

| Checkpoint | Full suite | Statement/branch coverage |
|---|---|---|
| T06 | 990 passed, 2 Linux-only skips; 37.52 s | 92.69% |
| T07 | 993 passed, 2 Linux-only skips; 38.67 s | 92.69% |
| T08 | 993 passed, 2 Linux-only skips; 37.99 s | 92.69% |

Each checkpoint passes lint, format, strict typing, exported-schema freshness
and generated-documentation freshness. `core/redaction.py` is unchanged and
retains **100% statement and branch coverage**. The two signal tests are
explicitly deferred to Linux CI; macOS results do not establish Linux behavior.

```console
.venv/bin/pytest -q --cov=reprollm --cov-report=term --cov-fail-under=85
.venv/bin/coverage report --fail-under=100 --include=src/reprollm/core/redaction.py
.venv/bin/pytest -q -m security --no-cov
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/
.venv/bin/reprollm schema export --out <temporary-schema-directory>
diff -r schemas <temporary-schema-directory>
.venv/bin/python scripts/gen_rules_doc.py --check
.venv/bin/python scripts/gen_profiles_doc.py --check
```

The environment's executables were used directly because `uv` is absent from
PATH. The dedicated security invocation passes both parameterized cases
(2 passed, 993 deselected). Tests retain the autouse mocked-HTTP guard.

The security test runs a real child in a real dirty temporary Git repository,
with synthetic OpenAI/HF/AWS credentials, a custom password, allowlisted CUDA
settings, argv credentials, a forbidden `.env`, a config snapshot, document
copies, a password-bearing diff and captured stdout/stderr. Every run file is
read recursively. All fake secret values, actual hostname, actual username and
the repository absolute path are absent. Credential presence markers, raw
input hashes and redacted patch/log markers are checked separately.

## Deliberate snapshot changes

Three pre-run Level 2 snapshots replace four “not implemented yet” results with
specific missing-evidence skip reasons and empty evidence. Their summary counts
do not change. Profile output and generated rule documentation now show those
rules as implemented; the registry asserts zero remaining stubs.

The new `hf_vllm_eval/expected/audit_L2_after_run.json` records manifest/config
temperature `0.0` versus CLI `1.0` as one CRITICAL finding. `exec.run_recorded`,
model identity and environment comparisons pass. The newly created `.reprollm/`
directory produces an expected untracked-file WARNING. Summary changes from
C/W/I/P/S `0/1/2/42/9` to `1/2/1/44/6`. The run ID/time is fixed for this test so
evidence paths are compared exactly. Existing run/lock snapshots and all nine
exported schemas remain unchanged.

## Five-project Gate A

All five originals have the pinned SHA, expected upstream origin and clean
porcelain status. They remained clean after validation. Mutating operations
ran only in disposable shared clones.

| Target | SHA | L0 seconds | C/W/I/P/S |
|---|---|---:|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 6.991 | 0/14/1/8/1 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 0.605 | 0/16/1/8/1 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 0.888 | 1/15/1/7/1 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 0.608 | 0/7/1/7/1 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0.295 | 0/7/1/7/1 |

```console
reprollm -v audit <checkout> --level 0 --format json --fail-on never --output <outside-report>
reprollm doctor --json
```

Every exit is 0. Full rule/status and unpinned dependency sets, profiles and
confidence, provider/backend/adapter/dataset/trust hints, model hints and physical
source lines, relative evidence paths and scan diagnostics match `val.md`.
There are zero unexplained gold deltas. lm-eval still discloses the 500/816
Python scan boundary; LlamaFactory's tracked `.env.local` remains CRITICAL.

The unchanged first-half source was exported from Git to an isolated directory.
For each clone, its `init` outputs and complete Level 1 JSON report were compared
against this session, removing only approved volatile timestamps/version fields
from the report. All three initialized files are byte-identical; stdout/stderr
and complete Level 1 findings match. Declared profiles and candidate IDs/source
comments also independently satisfy `val.md §7`. A TODO ID is represented by
YAML null plus a TODO comment, not the literal string `TODO`.

| Target | Init seconds | L1 seconds | Conflict audit seconds | Matching audit seconds |
|---|---:|---:|---:|---:|
| lm-evaluation-harness | 6.444 | 6.472 | 6.480 | 6.403 |
| FastChat | 0.555 | 0.573 | 0.551 | 0.554 |
| LlamaFactory | 0.793 | 0.788 | 0.784 | 0.782 |
| HarmBench | 0.598 | 0.579 | 0.573 | 0.574 |
| llm-dp-finetune | 0.299 | 0.287 | 0.290 | 0.290 |

### Runtime command contracts

Each clone then received the same independently specified synthetic manifest,
accepted custom rule and literal config bytes before the commands were run.
These expectations do not redefine the permanent gold answer or substitute for
model execution. Inputs, complete reports, run directories, per-command elapsed
times and expected/actual exit codes are retained with the validation drivers.

```console
reprollm init
reprollm audit --format json --fail-on never
reprollm lock --offline
reprollm run --capture-output --name conflict -- python -c <bounded-script> --temperature 1.0 --model fixture/other --alpha 0.5
reprollm audit --format json
reprollm run --name matching -- python -c pass --temperature 0.0 --model fixture/model --alpha 0.25
reprollm audit --format json
reprollm runs list --json
reprollm runs show <unique-prefix> --json
reprollm runs show <full-id>
```

The bounded child prints its run ID and a synthetic HF token; it does no model
work. Manifest/config temperature is `0.0`, environment temperature is `0.25`
for the first run and `0` for the second. `custom.privacy.alpha` is declared
`0.25` with accepted WARNING severity. Model IDs are synthetic, and the lock is
offline. The config is changed after the first run, then restored before the
second, testing all three file-hash sources. A deliberately corrupt future-dated
record is added after the second run to test skipping and warning behavior.

Expected results, all observed:

- The first audit emits CRITICAL file/generation/model conflicts and one custom
  WARNING with `severity_origin: project_rule`. Temperature evidence is exactly
  `[0.0, 1.0, 0.0, 0.25]`. File evidence retains lock, changed tree and original run.
- The second audit selects the newer matching run and all five runtime
  consistency checks plus `exec.run_recorded` pass. It warns about the malformed
  future record, counts only two valid runs, and does not reuse the older conflict.
- Both L2 audit exits are **1**. Offline revisions have declared, not exact,
  confidence, so `model.revision_pinned` remains CRITICAL. LlamaFactory additionally
  retains the known tracked-secret-file CRITICAL. This is expected existing
  behavior; a matching runtime alone does not make the entire audit pass.
- Init, offline lock, both children, list and show exit 0. JSON show is byte-identical
  to its saved record; records validate against the exported schema and retain the
  upstream commit. Recursive artifact checks find no synthetic secrets or local
  identity/path strings. Original checkouts stay clean.

The validation driver initially assumed a literal TODO string and a zero exit
after fixing runtime conflicts. Those assertions were corrected using the
scaffold source and the offline-provenance contract, without changing ReproLLM
or `val.md`. Final runs pass all independently specified assertions.

## Resource gates and release preparation

| Gate B scenario | State | Missing prerequisite |
|---|---|---|
| lm-eval tiny-model inference / M5 H2 | Blocked | Provisioned Linux/GPU environment and reviewed bounded inputs/expectations |
| FastChat one judge item / M5 H3 | Blocked | Explicitly provisioned API credential, provider access and budget; reviewed item |
| LlamaFactory 1–2 training steps | Blocked | Provisioned training environment and reviewed tiny-model/data scenario |
| HarmBench minimal target/classifier path | Blocked | Provisioned model execution resources and reviewed bounded scenario |
| llm-dp 1–2 privacy fine-tuning steps | Blocked | Provisioned training resources, applicable data/model access and reviewed scenario |

The resource question is still unanswered. No real credential was used;
prior HF authorization covered M4 metadata only. No weights, restricted data,
paid inference, GPU job or real training were invoked. Real scheduler/GPU
behavior, successful gated-model access and the prior M4 networked Linux H2
check are not established by these tests.

M5's sprint risk note allows H2 to follow release, but standing AGENTS §10 and
`val.md` require applicable Gate B scenarios before any release. The standing
gate controls this session, so T09 and publication remain incomplete.

The [0.3.0 draft](../releases/0.3.0-draft.md) includes an actual sanitized
`runs show` excerpt and CRITICAL generation finding. A disposable source copy,
excluding unrelated untracked directories, was assigned version `0.3.0` for
packaging only. Both distributions built, the wheel installed into an isolated
target directory without network/dependency installation, and bundled profiles,
version/help and schema exports passed. The guide's exact Python metrics example
ran through that installed wheel and produced the expected run-linked artifact
and hash. The actual package version remains `0.1.1`.

Raw evidence and delivery patches remain outside the worktree in the temporary
`reprollm-m5-second-half` directory. The machine-readable summaries are
`gate-a-record.json`, `gate-runtime-record.json` and
`release-preflight/preflight-record.json`. No main push, remote CI, review,
resource acceptance or release is being represented as complete.
