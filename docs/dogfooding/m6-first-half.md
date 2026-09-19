# M6 first-half validation

Validated on 2026-09-19 with Python 3.12.14 on macOS. Scope: M6-T01–T04,
following the submitted [M5 second-half report](m5-second-half.md).

## Delivery and review boundary

| Task | Commit | Result |
|---|---|---|
| M6-T01: State and projections | `06ef533` | Complete locally; three projection goldens |
| M6-T02: severity table/resolver | `c29c7a2` | Every normative row and version/dirty cases covered |
| M6-T03: differ | `4293379` | Normalized changes, ordering, counts and source notes |
| M6-T04: CLI and reports | `b0d8cfa` | Run/lock combinations, safe input handling, JSON/text and thresholds |

Follow-up `5da2e7d` fixes a reproduced crash on valid YAML dates in free-form
manifest data; dates become ISO strings before ordering. A separate test-only
commit makes the arrow-bearing text golden use explicit UTF-8 on Windows.

The branch `codex/m6-first-half` is based on M5's `codex/m5-second-half`, with
its submitted documentation synchronized. M5 is [PR #5](https://github.com/EnumaElish123/ReproLLM/pull/5);
its latest `b9d22a0` passes [CI run 35442637699](https://github.com/EnumaElish123/ReproLLM/actions/runs/35442637699).
M5 engine review is pending. M6 submission/CI are in progress; no main merge is claimed.

[D-41](../plan/00_architecture_and_decisions.md) requires explicit maintainer
review of schema changes. This session adds the internal State model and
implements the previously unreleased diff-report placeholder. M6 H3 additionally
requires maintainer review of the packaged severity table as a product judgment.
Both reviews precede merge. No lock/run-record schema, released rule ID,
dependency, validation pin, package version or tag changed.

## Tests and quality gates

Acceptance tests preceded implementation, with initial failures retained outside
the worktree. Each task passed the full lint/format/type/schema/doc/test gate.

| Checkpoint | Full test suite | Combined statement/branch coverage |
|---|---|---|
| T01 | 1005 passed, 2 Linux-only skips; 38.02 s | 92.83% |
| T02 | 1184 passed, 2 Linux-only skips; 39.42 s | 92.88% |
| T03 | 1190 passed, 2 Linux-only skips; 39.48 s | 92.95% |
| T04 | 1209 passed, 2 Linux-only skips; 40.55 s | 93.02% |
| Final source, YAML-date regression | 1210 passed, 2 Linux-only skips; 41.01 s | 93.03% |

The unchanged `core/redaction.py` retains 100% statement and branch coverage.
All tests keep the mocked-HTTP guard. No target library is imported or installed.
`uv` is absent from PATH, so the existing virtual-environment executables are used.

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

Projection tests check every source, CLI/config/environment precedence, complete
alternatives, optional documents, unresolved provenance, deterministic ordering,
atomic dotted file keys, GPU indices, standalone snapshots, corrupt/escaping
snapshots and JSON round trips. Severity tests cover all 51 normative rows for
changed/added/removed values, profile order, single-segment patterns, patch/prerelease/
local-version handling, zero-major minor changes and dirty-code notes.

Differ tests check normalized equality without bool/number conflation, explicit
null versus absence, counts, sorting and alternatives that produce only notes.
CLI tests exercise all input combinations, unique/ambiguous prefixes, unchanged
files after comparison, adjacent manifests, current profile overrides, missing
and invalid records, snapshot symlink escapes, full-summary filtering and exit
codes. Secret values and host paths are removed after raw comparison, including
nested credentials; distinct secrets remain a reported change.

An isolated wheel built and installed without network or dependency changes.
The wheel contains `drift_severity.yaml`; an installed-package diff reports torch
2.8.0 → 2.8.1 as MEDIUM, and its nine exported schemas match the repository.
This is package-content verification, not a release. Version remains `0.1.1`.

## Deliberate fixture/schema changes and plan interpretations

- Three `state_flat.json` files contain separate manifest/lock/run projections.
  Their leaves and alternatives were inspected. The existing M5 HF run golden
  omits volatile fields; the test supplies fixed clock/environment metadata.
  Two new, explicitly synthetic `expected/run.json` inputs cover the judge and
  privacy fixtures. They do not claim model/API execution.
- One text golden shows a lock revision change and its HIGH verdict. Existing
  audit, lock and HF run goldens are unchanged. T06's four broader diff scenarios
  remain for the second session.
- `diff_report.schema.json` now has the normative v1 references, summary and
  changes, plus nullable `filtered_below`. The spec and CHANGELOG describe the
  first-writer transition from M1's unreleased placeholder. The other eight
  exported schemas are byte-identical.
- T03 needs a typed `DiffReport` return value, so its required report models were
  implemented with T03 instead of waiting for T04. T04 then added CLI filtering
  and schema-validated reports. The existing module name `schemas/diff_report.py`
  remains the public export location, rather than introducing a parallel file.
- M6-T02/T06 examples say torch patch drift is LOW, but normative §18.1 and T02's
  algorithm say **one level lower**, and §18.2 starts torch at MEDIUM_HIGH.
  Per AGENTS §2 the specification controls: the result is **MEDIUM**. No severity
  table row was silently changed; the H3 review can propose a separate policy change.

## Five-project Gate A

Every original checkout matches its pin and upstream, is clean before and after
validation, and is used read-only. All mutations use disposable shared clones.
The complete Level 0 rule/status/dependency sets, profile confidences, hints,
physical evidence lines, relative paths and diagnostics match `val.md`.
Summary counts alone were not used. There are zero unexplained gold deltas.

| Target | SHA | L0 seconds | Diff validation total seconds (16 commands) | Gold deltas |
|---|---|---:|---:|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 7.084 | 4.230 | 0 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 0.627 | 2.367 | 0 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 0.807 | 2.361 | 0 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 0.577 | 4.106 | 0 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0.292 | 2.276 | 0 |

```console
reprollm -v audit <checkout> --level 0 --format json --fail-on never --output <outside-report>
reprollm doctor --json
# In each disposable clone:
reprollm lock --offline
reprollm run -- python -c pass --temperature 0.0
reprollm run -- python -c pass --temperature 0.7
reprollm diff <a> <b> --fail-on HIGH --format json
reprollm diff <a> <a> --fail-on LOW --format json
reprollm diff <a> <b> --min-severity HIGH --fail-on HIGH --format json
reprollm --no-color diff <run-a.json> <run-b-directory>
reprollm diff <detached-run-directory> <run-a.json> --format json
reprollm diff <lock-a> <lock-b> --fail-on HIGH --format json
reprollm diff <patch-lock-a> <patch-lock-b> --fail-on MEDIUM --format json
reprollm diff <b> reprollm.lock --format json
```

L0 audit and doctor exit 0 on all five. L0 C/W/I/P/S counts stay at
`0/14/1/8/1`, `0/16/1/8/1`, `1/15/1/7/1`, `0/7/1/7/1`, `0/7/1/7/1`.
lm-eval still discloses the 500/816 Python scan boundary; LlamaFactory still
reports its tracked `.env.local` as CRITICAL. These known baseline results remain.

The synthetic manifest declares one model, generation temperature 0.0 and
`configs/eval.v2.json`; the lock is offline. A minimal valid `.reprollm/config.yaml`
exists before either capture so creation of the first run does not introduce a
new untracked directory between captures. The initial driver omitted that setup:
FastChat's physical Git untracked count changed 2 → 3, yielding the correct extra
MEDIUM drift. The driver was corrected to establish the same initial conditions;
no ReproLLM behavior or permanent gold answer was changed. The initial evidence
is retained alongside the passing final run.

Independently specified expectations, all observed:

- Run pair: `generation.temperature` 0.0 → 0.7 HIGH with a B-source conflict note;
  `command.argv` MEDIUM; changed run ID/duration/time fields NONE. Complete change
  objects, counts and same-value totals are checked. `--fail-on HIGH` exits 1.
- Identical/detached run copies: no changes, highest NONE, exit 0. Historical
  snapshots supply declarations; the current manifest is irrelevant.
- HIGH display filter: one displayed temperature change; summary remains the
  complete summary and exit stays 1. Plain text has the not-comparable verdict.
- Lock revision pair: one HIGH model revision change, full 40-character hashes
  in JSON, exit 1. The B lock also retains the differing manifest source as a note.
- Torch patch pair: one MEDIUM change, exit 1 at `--fail-on MEDIUM`, following §18.1.
- Run vs lock: generation drift plus explicit removal of fields only observed at
  runtime (code/command/hardware/environment/IDs/times), never guessed agreement.
  Default exit is 0 because no failure threshold was requested. All JSON validates.

Per-command argv, pinned SHAs, exits, elapsed times, expected changes, full reports
and original-clean checks are in the temporary `reprollm-m6` evidence directory:
`gate-a-record.json`, `gate-diff-record.json`, per-target JSON and validation drivers.
Package evidence is in `package-final/record.json`. No credential, paid API,
model weight, restricted dataset or GPU resource was used.

## Remaining work

M6-T05–T08 are the second session: migrate Level 2 consistency to State while
keeping audit goldens unchanged, add the four full diff scenarios, complete the
user guide and real paired-run acceptance, then prepare release only when gates
permit. M6 Gate B activates at milestone completion; this first-half session
does not claim it passed. The previous M4 Linux and M5 model/judge/training resource
gates remain blocked on provisioned resources. Publication and version tags remain
pending. The unrelated pet/output directories were not modified or committed.
