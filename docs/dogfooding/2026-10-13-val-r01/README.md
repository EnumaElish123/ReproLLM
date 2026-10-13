# VAL-R01 resource replay — 2026-10-13

The previously unavailable resources are now provisioned. Linux H2 and all ten
bounded native GPU children completed successfully. **VAL-R01 remains BLOCKED
on snapshot fidelity:** eight captures from four projects alter non-secret
source/configuration syntax. LlamaFactory's two captures pass, with one explained
operational environment delta. This report records current-candidate evidence;
it does not promote the historical 0.6.1 release or an A01-B delivery gate.

## Scope and fixed inputs

- Task: VAL-R01 from [the resource checklist](../pending-resource-validation.md),
  following [val.md §§8.1–8.3/8.5](../../../val.md) and the
  [independent native gold](../m5-m6-runtime-gold.md).
- Candidate: `26c0b4a716b5b025058a3b1daabc64afdf1a022d`, reporting version 0.6.1.
  All 1,811 tracked candidate files retain their original Git bytes;
  inventory SHA-256: `226d273b78ad0dca733f9827c2102bc9a44aa7128c40d2b36056c8936a657d0c`.
- The isolated modern/DP environments received only the candidate ReproLLM wheel,
  SHA-256 `85c9949b38744461b71ddbd60bbed7450f19a74b66a99b9c4138c6e8f88b6c7b`.
  Its 138 package files match candidate source bytes. Distribution metadata changed
  from stale 0.1.1 to 0.6.1; framework/dependency versions stayed unchanged.
- The [input integrity evidence](input-integrity/) identifies all five original
  pins/origins, ten exact A/B variants and 32 lightweight input records. All ten
  manifests pass the exported schema. Only the predeclared parameter and its
  manifest binding change for each B variant; generated locks and clean input
  commits are fresh. The corrected lm-eval config hash remains
  `a7bc8316852aac0e9a4b2fb0ea67b0bf10df9b7debc000cad1b0e1a997ad5467`.
- All 45 cached snapshot files were completely hashed: 42 independently
  preselected SHA-256/LFS comparisons and three official immutable Git-blob
  comparisons pass. GSM8K canonical rows match 7,473 train / 1,319 test records
  and the preselected hashes. The classifier cache uses six safetensors shards;
  the earlier three-bin description is historical.

The five pinned source checkouts remain clean and unchanged. Runtime mutations
occur only in new disposable clones on the approved resource volume. Credentials,
weights, checkpoints and complete private raw logs remain outside Git. The paid
judge (VAL-R02) and authenticated gated-file success (VAL-R03) retain their
separate outstanding status; this session made zero paid completion requests.
S3-B (R04-A → R04-B) remains the next engineering session.

## Shared prerequisites and Linux H2

The [validation cadence](../../plan/validation-workflow-2026-10-13.md) was followed:
one complete quality gate on the fixed candidate, then fresh minimal Gate A on
all five pins, then the applicable resource matrix. Per-command evidence and
external raw-content references are in [prerequisites](prerequisites/).

- Full pytest: 2,527 passed, two slow tests deselected; coverage 93.64%.
- Security: 174 passed; redaction statements and branches 100%.
- All 13 quality commands exit 0, including Ruff/format, strict typing,
  generated documentation and ten-schema freshness. Quality command sum
  410.402 s; wall 411.255 s.
- Gate A: ten unique fresh product commands (L0 JSON plus required context facts),
  ten complete JSON comparisons, twenty checks PASS, zero unexplained gold deltas.
  Product time 82.885 s; comparison time 2.055 s. Original pins and candidate
  byte inventories pass before/after checks. This matrix avoids repeated
  unchanged renderers, templates and task inventory commands.

[Linux H2](linux-h2/summary.json) uses the exact five reviewed **§8.2 supplemental
metadata manifests**. Their SHA-256 values match the existing table; original
M3 inputs are not reconstructed. The official HF endpoint worked through the
provisioned HTTP proxy; this run needed no mirror fallback and used anonymous
metadata requests. For each pin, offline / online-1 / online-2 each performed
lock, lock check and a clean Level 2 audit. All 45 product commands and 45
preparation commands exit 0 (product 175.177 s; all-command 185.563 s;
wall 191.254 s). Every fixed local/remote revision, config/template hash,
normalized online-lock equality, freshness and file consistency assertion passes.
Timestamp exclusions apply only to the specified metadata positions. Deliberately
limited-manifest findings remain visible, including DP's missing training seed.
Anonymous gated-file denial remains `unresolved/hf_api_forbidden` and establishes
denial handling. See [all checks](linux-h2/checks.json),
[commands](linux-h2/commands.json), [results](linux-h2/results.json) and
[independent review](linux-h2/independent-review.json).

## Native A/B execution and complete semantic comparison

Each native child uses the same isolated environment as its ReproLLM launcher.
GPU 0 is pinned, the original GPU lease is held, stages are sequential, CPU math
threads are two, trackers are disabled and cached native execution is offline.
The original caps remain 0.12 lm-eval, 0.35 LoRA, 0.15 DP, 0.30 FastChat,
and 0.28/0.45 HarmBench target/classifier. A conservative cap-plus-2-GiB memory
reserve and 50-GiB storage reserve are checked before launch. HarmBench additionally
checks resources in each actual target/classifier process before native entry.
The original idle guard was satisfied for successful launches; GPU 1 was unused.
Both cards' final occupancy matches the pre-launch idle state; no unrelated
process or system driver was changed.

Commands are the exact §8.3 native commands, prefixed with
`reprollm run --name <unique-label> --capture-output --`. A/B preparation runs
`lock`, commits owned inputs in the disposable clone, then `lock --check` and a
JSON audit. After execution, audit and independent output checks run before
outputs are archived. Full command argv, exits, elapsed times and raw-stream
hashes are retained in [the command ledger](runtime/commands.json).

| Project / native child | A → B | Child exit A/B; run-command seconds | Capture A/B | Pair projection |
|---|---|---|---|---|
| lm-eval: `python -m lm_eval run --config validation/eval.yaml` | cap 32 → 48 | 0/0; 101.130 / 98.549 | FAIL / FAIL | HIGH leaf PASS |
| LlamaFactory: `python validation/train_entry.py` | learning rate 0.0001 → 0.0002 | 0/0; 31.701 / 47.790 | PASS / PASS | HIGH leaf; explained MEDIUM environment delta |
| llm-dp-finetune: `python validation/train_entry.py` | target epsilon 8 → 4 | 0/0; 30.700 / 13.598 | FAIL / FAIL | MEDIUM leaf PASS |
| HarmBench: `python validation/pipeline.py` | cap 16 → 24 | 0/0; 83.944 / 70.300 | FAIL / FAIL | HIGH leaf PASS |
| FastChat: `python validation/answer_entry.py` | cap 32 → 48 | 0/0; 42.331 / 43.489 | FAIL / FAIL | HIGH leaf PASS |

Captured `reprollm run` command elapsed sum is 563.532 s, including launcher
and capture overhead. Run-record durations sum to 490.096 s; neither total
is a whole-session wall time.
Independent output checks pass for both variants: 100 GSM8K documents / 200
filter rows and identical document/prompt identities; two finite-loss LoRA
updates and nonzero adapter tensors; two real DP updates with clipping, positive
noise, complete intended-parameter coverage and identical initial weights;
one HarmBench target completion and original classifier result; and one FastChat
question with two nonempty turns. Accuracy, prose, scores and labels are observations,
not preselected gold.

All five complete A/B finding lists and profile lists are equal. Each pair has
empty self-diff and `--fail-on HIGH` exits 1. The prescribed nested DP epsilon
leaf remains **MEDIUM** while its changed config hash is HIGH. Four pairs contain
seven complete changes; LoRA contains eight. [The complete matrix](runtime/matrix.json)
retains all 36 changes, exact values, severities and explanations. Config hashes
are HIGH, clean disposable commits MEDIUM, and timing/run identity NONE.
LoRA's additional `environment.env.VLLM_RPC_BASE_PATH` is added at MEDIUM after
the process-local IPC correction. Independent source review confirms the native
SFT path does not consume it; packages, argv and SFT source remain identical.
This limited deviation is accepted and retained; complete environment byte
identity is not claimed. See [its review](capture/llamafactory-rpc-env-deviation-review.json).

## Snapshot fidelity defects and acceptance

The complete CPU-only [capture index](capture/index.json) covers all ten states:
559 subchecks PASS, 20 snapshot checks FAIL, 17 historical current-source
comparisons explicitly not applicable. These reports check original Git input
bytes, output hashes/sizes, archived artifacts, package metadata, clean captured
commits, model/data identities, saved-file privacy and actual primary bindings.
The earlier A-state checks remain valid receipts rather than repeating native
execution after B has changed the current source tree. All raw hash/privacy/
binding checks pass. The semantic snapshot failures remain failures:

- lm-eval: the original `gsm8k.yaml` escaped dollar/dot patterns and numeric-answer
  regex are replaced in whole or part by path markers.
- DP: `/`, `//`, f-string division and relative path separators are changed in
  `language_model.py` and `validation/train_entry.py`. Original Python parses;
  the saved Python does not.
- HarmBench: four saved source files per state fail semantic fidelity.
- FastChat: three saved source files per state fail semantic fidelity.

The [independent defect note](capture/snapshot-fidelity-followup-defect-note.json)
records exact paths, source/snapshot hashes and the applicable existing
specification §§5/16 and val.md §8.3. These are implementation defects in
path redaction, covered by the existing engineering backlog; the specification,
rule IDs, severity policy, pins and gold remain unchanged. Passing original-byte
hashes and effective-State pair projections cannot substitute for intact source
snapshots. The current candidate therefore does not close VAL-R01.

All ten default captured-state exports have been executed once, with exit 0.
Their independent [selected-state projection verification](exports/selected-state-export-summary.json)
passes all 704 comparisons, with zero additional product executions. It binds
each of the ten final capture reports explicitly: two fidelity PASS / eight
fidelity FAIL. Default export command time is 88.542 s. Upstream capture
fidelity remains a separate blocker. Full release/A01-B delivery closure requires its
own prerequisites and acceptance; the bounded runtime version metadata proves
the current launch environment, not arbitrary external-interpreter attestation.

## Preserved corrections and final recording scope

Every failed attempt is retained outside Git and identified by hashes:

1. A Gate A helper expected `EQUAL` instead of compare_gold's `PASS`; the same
   first product output was requalified, with nine remaining fresh commands.
2. Two CPU dataset integrity helpers stopped during imports due to overstrict
   filesystem guards (owned tempfile probe / standard null-device probe). The
   corrected helper read the actual Arrow rows once, matching preselected gold.
3. The initial stage-hook test used runpy and overwrote argv. Four real interpreter
   positive/negative cases confirm rejection before native entry.
4. First lm-eval startup exited 1 after 39.317 s because its vLLM IPC path was
   113 bytes, exceeding 107. A fresh dedicated namespace and owned short scratch
   generate an 84-byte path. Explicit TMPDIR/RPC-base settings change no model,
   dataset, scenario or memory cap. The successful native A/B attempts above
   are distinct; the failed attempt is preserved and excluded from PASS counts.
5. A capture helper initially required non-null scheduler metadata in a
   non-scheduler environment; privacy helper versions misclassified slash prose
   and HTTPS as paths. Source-derived corrections and focused negative checks
   requalified existing raw data without rerunning successful native children.
6. H2's first observer incorrectly assumed declared dataset file order rather
   than schema-normalized sorted order. Its three false failures are retained;
   pure same-input requalification passes with zero product children.
7. Export helper projection corrections handle schema patternProperties and
   the template's exact-null fallback; existing Markdown is checked again,
   with zero additional export CLI executions.

Only documentation/evidence is committed by this recording session. Product code,
fixtures, schemas and baseline gold remain the fixed candidate. The already-green
shared quality/Gate A evidence remains applicable under the documentation-only
exception in the validation workflow; affected local links, JSON schemas,
content hashes, privacy and evidence accounting are checked before recording.
Final pushed recording-commit CI is tracked separately from candidate runtime
validation. Complete private raw logs are retained on the provisioned resource
volume; compact metadata and hash references are published once here.

The [independent recording review](recording-review.json) verifies complete findings,
all deltas, capture statuses and timing. [The content index](content-index.json)
binds every published payload; upstream bundle indexes retain references to
externally held raw files beyond this compact publication.

Published audit JSON trims the CLI's extra final blank line; every JSON value
is unchanged and [raw/published hashes](runtime/audit-publication-format.json)
remain separately recorded.
