# M4 lock validation record

Validated on 2026-09-19 with Python 3.12.14 on macOS. This records M4's second
development session and extends the [M3 baseline](m3-project-a-b.md).
The maintainer approved pushing the verified code while Linux H2 remains
unavailable. M4-T09's version bump, tag and publication remain pending.

## Tasks and quality gate

| Work | Commit | Result |
|---|---|---|
| M4-T06: three lock/Level 2 fixtures | `3fdb585` | Complete; provider-specific assertions and JSON Schema validation |
| M4-T07: shared doctor client and lock documentation | `5b82b74` | Complete; mocked retry, mirror and authentication coverage |
| Approved Issue #2: M4/M5 placeholder boundary | `d69139c` | Exactly four runtime consistency stubs remain for M5 |
| M4-T08: independent metadata gold | `a9327bb` | Dedicated baseline extension; no repository pin or Level 0 expectation changed |
| M4-T08: real-repository validation and Apple Git fix | This report's task commit | All available scenarios completed; Linux H2 blocked |

The Apple Git regression test first failed against the existing parser. The
fix accepts the vendor suffix in `git version 2.50.1 (Apple Git-155)` while
retaining the minimum-version check. It changes no schema or fixture snapshot.

The final local gate ran after the fix, before the external validation:

```console
.venv/bin/pytest -q --cov=reprollm --cov-report=term-missing --cov-fail-under=85
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/
.venv/bin/reprollm schema export --out <temporary-schema-directory>
diff -r schemas <temporary-schema-directory>
.venv/bin/python scripts/gen_rules_doc.py --check
.venv/bin/python scripts/gen_profiles_doc.py --check
```

Result: **728 passed in 31.14 s**, **94.87% coverage**; lint, formatting, strict
typing, schema freshness and generated documentation freshness all passed.
The environment's executables were used directly because `uv` was not on PATH.
Tests used mocked HTTP only. Real HTTP below belongs to manual Gate B, outside
CI, preserving frozen decision D-32.

The three reviewed fixture outcomes (CRITICAL/WARNING/INFO/PASS/SKIPPED) are
`0/1/2/42/9` for HF/vLLM, `0/1/4/37/19` for the API judge, and `1/2/3/43/9`
for privacy. The unresolved backend and gated failures are intentional.

## Inputs and artifacts

All original checkouts had the expected origin and an empty porcelain status
at these exact commits. Mutating commands ran in disposable shared clones.

| Target | Upstream commit |
|---|---|
| Project A: lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` |
| Project B: FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` |
| Project C: llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` |

A/B retain their M3 manifests byte for byte. C records the upstream ECHR DP8
full-fine-tuning configuration. LlamaFactory and HarmBench use bounded
metadata manifests; they do not claim complete runnable experiments.
Manifest hashes, remote SHAs and local file hashes were established from
upstream source and direct HTTP/hashlib checks before running the product;
see [val.md §8.1](../../val.md#81-m4-metadata-resolution-scenarios-reviewed-2026-09-19).

Raw locks, manifests, JSON reports, sanitized command output, independent gold
and command wrappers are preserved outside this repository in
`../dogfooding/m4-lock-2026-09-19/`. The two machine-readable command records
are `gate-a-record.json` and `gate-b-record.json`. No target repository or
generated target artifact is committed into ReproLLM.

## Gate A

For each original checkout:

```console
reprollm -v audit <checkout> --level 0 --format json --fail-on never --output <outside-report>
reprollm doctor --json
```

`doctor` ran with the corresponding checkout as its current directory.

| Target | Audit exit | Audit seconds | C/W/I/P/S | Doctor exit | Doctor seconds |
|---|---:|---:|---|---:|---:|
| lm-evaluation-harness | 0 | 6.684 | 0/14/1/8/1 | 0 | 0.183 |
| FastChat | 0 | 0.579 | 0/16/1/8/1 | 0 | 0.162 |
| LlamaFactory | 0 | 0.800 | 1/15/1/7/1 | 0 | 0.158 |
| HarmBench | 0 | 0.568 | 0/7/1/7/1 | 0 | 0.157 |
| llm-dp-finetune | 0 | 0.258 | 0/7/1/7/1 | 0 | 0.158 |

The complete Level 0 rule/status and dependency sets, detected profiles and
confidences, provider/backend/adapter/dataset/trust hints, allowed HF IDs with
physical source lines, relative paths and scan diagnostics match `val.md`
§§3–6. There are **zero gold deltas** from M3. The A scan still reports exactly
`python file scan truncated to 500 of 816 files`. LlamaFactory's tracked
`.env.local` remains CRITICAL, as specified by the unchanged gold.

Doctor reports Python and Git as available, no installed LLM-critical
packages, and Level 0 document state using relative paths. Missing optional
`nvidia-smi` and `uv` produce warnings. The Apple Git parsing warning observed
in the first attempt is fixed, covered by a regression test, and absent from
all five final runs. `init` was unchanged, so this session did not rerun its
separate M3 gate.

## Gate B

For every disposable clone with its reviewed manifest:

```console
reprollm lock <clone> --offline
reprollm lock <clone> --check
reprollm audit <clone> --format json --fail-on never --output <offline-report>
reprollm lock <clone>
reprollm lock <clone>
reprollm lock <clone> --check
reprollm audit <clone> --format json --fail-on never --output <online-report>
```

Manifest and generated lock were committed only in the disposable clone
before each audit. C repeated online lock/check/audit with the authorized
credential supplied in the child process environment. Every lock, check and
audit command exited **0**; `--fail-on never` intentionally preserves reports
with findings. All reports detect Level 2 and validate against the exported
schema. Timings below are seconds; C/W/I/P/S excludes the always-zero
suppression count.

| Target | Mode | Lock | Check | Audit | C/W/I/P/S |
|---|---|---:|---:|---:|---|
| A | Offline | 0.211 | 0.142 | 6.567 | 2/17/2/37/8 |
| A | Online | 2.429 | 0.146 | 6.542 | 0/15/2/41/8 |
| B | Offline | 0.148 | 0.132 | 0.510 | 1/19/3/40/12 |
| B | Online | 2.059 | 0.144 | 0.533 | 0/17/3/42/12 |
| LlamaFactory | Offline | 0.156 | 0.144 | 0.758 | 2/19/3/13/11 |
| LlamaFactory | Online | 2.230 | 0.137 | 0.753 | 1/18/3/15/11 |
| HarmBench | Offline | 0.155 | 0.142 | 0.547 | 1/10/3/14/11 |
| HarmBench | Online | 4.583 | 0.131 | 0.525 | 0/9/3/16/11 |
| C | Offline | 0.151 | 0.137 | 0.257 | 2/11/1/25/11 |
| C | Online, anonymous | 2.380 | 0.136 | 0.248 | 1/9/1/28/11 |
| C | Online, credential supplied | 3.302 | 0.134 | 0.245 | 1/9/1/28/11 |

Second online lock timings were A 3.686, B 4.301, LlamaFactory 1.744,
HarmBench 2.836 and C 2.662 seconds. All five pairs agree after removing only
`generated_at`, `resolved_at` and `observed_at`; saved A/B/LlamaFactory/HarmBench
pairs also pass a byte comparison after replacing those timestamp lines.
All declared local file/prompt/dataset/metric hashes and remote
revision/config/template hashes match the independent gold. Both consistency
rules pass throughout; there are no unresolved gold mismatches.

The opt-in `reprollm doctor --json --check-network` probe used the authorized
HF credential, successfully resolved public gpt2 metadata, and exited 0 in
1.002 seconds.

## Finding review and baseline delta

| Finding or behavior | Evidence and disposition |
|---|---|
| A model/tokenizer/template and GSM8K identity | Exact HF revisions and independently calculated hashes; all applicable lock identity/hash rules pass online. Offline unresolved findings are expected. |
| B judge identity | `gpt-4o-2024-08-06` is `snapshot_alias`, with a null provider revision. `model.revision_pinned` is INFO; judge pinnability and prompt hashing pass. No OpenAI request was made. |
| B Vicuna chat template | Neither supported Hub template source is present; recorded absence produces PASS with explanatory evidence. |
| Backend version | A/B/C do not have vLLM/transformers installed; unresolved provenance and WARNING are correct. No heavy dependency was installed to hide a finding. |
| LlamaFactory/HarmBench | Their limited metadata manifests deliberately omit execution commands/seeds, generating warnings, and leave repository-wide profile capabilities undeclared, generating INFO. LlamaFactory additionally lacks a declared dtype. |
| C gated files | Public repo and tokenizer identity resolve exactly. Anonymous config/tokenizer file fetches return 401; the provisioned credential returns 403 with model-author rejection. Unavailable file hashes remain `unresolved/hf_api_forbidden`. |
| C training seed | The selected configuration has no explicit seed; the privacy profile correctly makes `exec.seed_declared` CRITICAL. No seed was invented to improve the result. |
| C adapter warning | The current §12.4 heuristic detects repository-wide adapter support, although this selected configuration uses full fine-tuning. The warning follows the existing contract; no unsupported adapter declaration or unrelated rule change was added. |
| Runtime consistency | Exactly the four Issue #2-approved M5 placeholders remain skipped. Runtime behavior was not implemented or claimed. |

Relative to the reviewed M3 Level 1 A/B reports, the underlying presence,
profile and dependency findings are unchanged. A adds one backend WARNING,
seven lock PASS findings and five applicable skips. B adds one backend
WARNING, one snapshot-alias INFO, eight lock PASS findings and five skips.
The extra skips comprise the four M5 placeholders and the inapplicable
HF/local-dataset lock rule. These explain the entire summary delta.

C, LlamaFactory and HarmBench now have an initial metadata-resolution record;
their narrower manifests are not compared as if they were the complete M3
A/B experiments. Environment dependency warnings remain about the upstream
declarations; a ReproLLM lock does not rewrite or replace those declarations.

## Credential check and remaining work

The credential was read locally and supplied only in memory to the authorized
metadata subprocess. Exact-value scans of captured stdout/stderr, generated
locks, reports and the archived artifacts found **zero occurrences**. No
credential was committed, embedded in a command, or stored in a report.

T08's example `grep -r hf_` would match legitimate provenance names such as
`hf_api` and `hf_api_forbidden`. Validation therefore scanned for the actual
credential value without printing it. This is a documented correction to the
check, not removal of provenance evidence.

The requested anonymous and authenticated denial scenarios passed. Successful
gated-file access remains unavailable because the repository author rejected
this account; the report does not claim that access succeeded. Unlike the
mocked privacy fixture, the live service exposes repo metadata publicly, so
live revision confidence is correctly exact even when file hashes cannot be
resolved. T08 does not require changing the upstream model to avoid its gate.

M4 H2 explicitly requires a networked **Linux** machine. None was provisioned;
the maintainer confirmed this and requested that verified code be pushed first.
The macOS runs do not satisfy Linux H2, and CI retains mocked networking under
D-32. Complete that manual check before the M4-T09 version bump, `v0.2.0` tag
and publication. No weights, remote dataset contents, inference, training,
paid provider call or GPU job ran in this session.
