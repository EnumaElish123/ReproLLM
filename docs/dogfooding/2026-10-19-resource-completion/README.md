# Current-candidate resource validation — 2026-10-19

**VAL-R01 passes:** Linux H2, ten real GPU children, all five complete A/B pairs
and twenty default export states are accepted on product candidate
`750270b10307455795fcff126664429dc895983a`. **VAL-R02 fails source-snapshot
acceptance after one successful real judge request; B was not sent. VAL-R03
remains blocked by authenticated file denial and original-input requirements.**
The session introduces no product fix, release, version bump or replacement gold.

The repository was updated from `53782ab` with a fast-forward pull. The current
plan has delivered S1–S4-B engineering and the accepted, unreleased R08-A policy.
This session executes A01 input restoration and resource replay. It restores
45 of 50 exact input slots on the available Linux node, replacing the previous
machine's access obstruction with actual possession. Five original §8.1 metadata
manifests remain missing; supplementary inputs do not replace their identities.

| Group | Current result | Evidence boundary |
|---|---|---|
| VAL-R01 | PASS at `750270b` | H2; ten native children; full capture, consumption, diff and available-state export acceptance |
| VAL-R02 | FAIL | Real A request and original score parser succeed; required Python/JSONL snapshot fidelity fails; B NOT_RUN |
| VAL-R03 | BLOCKED | HF authentication HTTP 200; both selected restricted small files HTTP 403; original Project C manifest missing |
| Five supplementary discover previews | PASS for that layer | Complete collection/source/privacy comparisons; no provider request, no formal initialized/live acceptance |
| Release readiness | Not established | No complete release validation artifact, gated success or repaired-candidate formal judge pair |

## Candidate, prerequisites and input recovery

All product runs use source version **0.7.0**, run schema **2**, and the same
verified candidate wheel:
`1f2a747e8a5efd6b65201b238ae1d0059d59c84f8176da645f7a18554bd2ba1e`.
Both framework environments match all 141 package payload files. Installation
changes only ReproLLM; 274 modern and 82 DP third-party distributions stay
unchanged. The [supporting gate report](PARTIAL.md) links the complete quality,
installation, input-integrity, H2 and collection receipts.

- Full quality: **2,845 passed**, 2 slow tests deselected, **93.83%** overall
  coverage; redaction **100% including branches**; security **205 passed**.
  Lint, format, strict types, ten exported schemas, generated docs and installed
  distribution acceptance all pass. Quality wall time is 573.714 seconds.
- Fresh five-project Gate A: all pins/origins and clean states checked;
  ten complete JSON comparisons and full diagnostics match. Its 51 commands
  and 32 assertions pass after the quality gate.
- H2: all five exact §8.2 manifests and fifteen offline/two-online modes pass
  complete revisions, local/config/template hashes, deterministic locks,
  Level 2, freshness and consistency checks. All 96 commands exit 0, including
  five original-checkout doctor calls and the anonymous official-HF probe.
- [Input inventory](input-recovery/inventory.json): **45 AVAILABLE, 5 MISSING,
  0 ACCESS_BLOCKED, 0 HASH_MISMATCH**. Original source/driver/config bytes are
  recovered from immutable objects, not reconstructed from hashes or current
  outputs. Model cache, GSM8K rows and pinned runtime source have independent
  integrity checks. No model weights are added to this repository.

The final report-only changes do not alter the tested product payload. The
closing main commit's CI is checked separately after push; local Linux results
are not presented as a cross-platform run.

## Ten native children and five complete semantic pairs

The [terminal review](native-observers/terminal-evidence-review-final-1.json)
binds actual child records, wheel checks, guards, independent consumption/output
checks, complete differences and exports. Inputs, pins and independent
expectations remain those in [val §8.3](../../../val.md#83-activated-bounded-linux-runtime-inputs-2026-09-26).

| Native case | Independently checked execution | A → B target | Severity | Result |
|---|---|---|---|---|
| lm-evaluation-harness | 100 GSM8K documents, 5-shot; 200 filter rows; fixed question/prompt identities, native request arguments and finite metrics | `generation.max_tokens` 32 → 48 | HIGH | [PASS](native/lm-evaluation-harness/pair-check.json) |
| FastChat | Original question-81 answer generator, one choice/two nonempty turns, original temperature/seed and observed native cap | `generation.max_tokens` 32 → 48 | HIGH | [PASS](native/FastChat/pair-check.json) |
| LlamaFactory | Two real LoRA updates per variant, finite raw batch loss, actual optimizer learning rate and nonempty changed adapter | `training.learning_rate` 0.0001 → 0.0002 | HIGH | [PASS](native/LlamaFactory/pair-check.json) |
| HarmBench | Original DirectRequest, one target generation and original classifier function; actual target/classifier arguments and valid binary classification | `generation.max_tokens` 16 → 24 | HIGH | [PASS](native/HarmBench/pair-check.json) |
| llm-dp-finetune | Two real optimizer/DP steps, original clipping and noise calls, changed finite weights, finite accountant and larger calibrated sigma for smaller epsilon | `privacy.mechanism.params.target_epsilon` 8 → 4 | MEDIUM | [PASS](native/llm-dp-finetune/pair-check.json) |

All ten children exit 0 and retain complete original-byte input/output hash
and size checks, non-secret snapshot fidelity, package metadata and privacy
checks. Each pair has exactly seven explained effective changes: its semantic
parameter, HIGH config hash, MEDIUM clean input commit, and four NONE run/time
leaves. Thus **35 complete changes** have no unexplained extras. All five
self-diffs are empty; explicit `--fail-on HIGH` exits 1. DP's HIGH config hash
does not conceal or change its prescribed MEDIUM epsilon leaf.

Actual native call observations are separate from ReproLLM's provenance.
RunRecord continues to label recorder/host/inherited evidence and pre-child
inputs truthfully; unchanged input checks do not attest whole-child consumption
or environment. Independent observers verify the listed consumed parameters,
without changing native algorithms or fabricating outputs. These bounded smokes
make no benchmark-quality or production-privacy claim.

The ten `reprollm run` wrapper commands total **707.120 seconds**: lm-eval
303.194, FastChat 101.312, LoRA 50.379, HarmBench 195.910 and DP 56.325 seconds.
These are command-elapsed totals, not a sum with overlapping H2, quality or
observer wall time, and not GPU kernel timings.

## Resource instruction and preserved failures

The maintainer's latest direction is: “只要GPU有空闲显存，即可使用，
无需考虑人为设定的资源限制”. [val §8.3](../../../val.md#83-activated-bounded-linux-runtime-inputs-2026-09-26)
records this continuing instruction for already-provisioned bounded work.
Old fixed memory/utilization thresholds and unaccepted numerical proposals
are not reinstated as future approval gates.

Eight original launches meet the earlier strict conditions. Another user's
job then starts. The last two launches use the explicit updated direction,
with 67,397 MiB actually free. This replay uses GPU0 throughout, preserves
reviewed batch/sequence settings and `.30/.28/.45` stage settings, holds the
exclusive validation lease, and never changes another job. HarmBench records
both target/classifier boundaries. All ten child intervals are sequential.

The evidence retains these observer/control failures rather than hiding them:

- FastChat A and HarmBench A initially fail the scratch path oracle on valid
  Python division, tags, relative f-string suffixes or template docstrings.
  Source and snapshot bytes match. The syntax-aware oracle is corrected with
  real path/secret negative cases, then the **same original runs** are qualified;
  neither model is rerun for that correction.
- lm-eval B completes successfully after a valid pre-launch guard. A controller's
  additional post-child idle assertion fails once other work starts. CPU
  acceptance continues over that original record; no model command is repeated.
- An initial numerical sharing allowance cannot launch a child after occupancy
  increases. Its retrospective no-launch note is explicitly not a fabricated
  original process receipt. The later first launches have their own actual
  records under the replacement instruction.
- H2 doctor and export/collection observer corrections retain their original
  failures and raw hashes. Supporting reports distinguish fresh product runs
  from re-comparison of immutable output.

## Export and provider boundaries

[Ten manifest-only/lock-only states](exports/exports-nonrun-final-4/summary.json)
pass 487 complete comparisons; [ten selected-run states](exports/exports-selected-run-final-3/summary.json)
pass 804. Together **20 states / 1,291 comparisons** cover complete parameter
sets, identities, provenance, input phases/hashes, recorder/hardware scope,
unverified-child limitations, audit findings and diagnostics. Independent
pre-lock audits close the manifest-only evidence chain. Final export checker
positive and negative cases also pass; unexpected extra values are rejected.

The [provider/failure report](DYNAMIC-PARTIAL.md) links exact input hashes,
current authorization, request proof and both accepted CPU diagnoses. The
single formal judge A child exits 0, sends the original public rubric/question
and fixed synthetic answer, consumes cap 256 and yields observed score 7 through
the original parser. All four bindings, six judge rules and usage checks pass.
Its returned usage gives a peak-tariff estimate of **CNY 0.001394** using the
[official pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)
checked this session; no account invoice is asserted.

Complete judge capture nevertheless **FAILS**:

1. A Python f-string is treated as a structured fragment; a later symbolic
   API-key assignment makes the whole `common.py` snapshot unavailable.
2. Raw JSONL newline escapes after `A:` are mistaken for Windows paths,
   changing rows 2, 4, 7 and 8 of the saved rubric. The active `single-v1` row
   is unchanged, which does not repair the required complete-file fidelity.

Both issues have valid, secret-free CPU reproducers and causal probes. No
product source is patched during this validation session, no missing snapshot
is fabricated, and **B is NOT_RUN** after the known failure. The accepted R08-A
HIGH policy remains implemented and locally tested; this A-only provider run
does not prove the new real paid pair. The failed state's later export executes
successfully but does not upgrade its upstream capture or join the twenty
accepted native states.

HF authentication is HTTP 200 through the existing proxy; pinned Llama-2
`config.json` and `tokenizer_config.json` remain HTTP 403. No restricted weights
are downloaded. A token's validity is distinct from permitted file access.
Five original §8.1 metadata manifests also remain missing after a documented
bounded search; H2/native manifests cannot substitute for them.

## Handoff and evidence use

Prioritize the two source-snapshot repairs with original-source/minimal CPU
regressions, security negatives and final quality before a new formal judge
acceptance. Preserve this failed paid A as historical evidence. Resolve original
metadata inputs and permitted HF file access independently. Formal initialized
discover/live-provider replay and a complete same-candidate release artifact
remain separate; this report does not declare release readiness.

[Stable evidence](stable-files.json) and [dynamic evidence](dynamic-files.json)
map logical sources, original/retained hashes and duplicate aliases. Raw product
run trees retain their original schema-2 bytes; source licenses and exact input
identities are recorded, including the additional
[captured-code notices](input-recovery/captured-code-licenses.json).
Inert helper/source names and sanitized command receipts
are explicit sharing transforms, not claims of byte-identical executable replay.
The [final integrity check](final-validation.json) and
[exact configured-credential scan](credential-scan.json) pass; no credential
value, prefix or length is retained by the scan.
HarmBench generated text and content-bearing logs stay outside this package;
their safe identifiers, lengths, hashes, binary outcomes and acceptance receipts
are retained. Never send a paid request merely to replay an observer.

The session follows the [validation cadence](../../plan/validation-workflow-2026-10-13.md):
one shared final product quality gate, fresh all-five Gate A, then applicable
resource work. Later additions are evidence and resource-guidance documentation
only. Pre-existing user edits remain outside this change. Main receives the
report directly under the repository workflow; no tag or package is published.
