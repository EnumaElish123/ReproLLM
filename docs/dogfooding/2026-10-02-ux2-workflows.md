# UX2 workflow session, 2026-10-02

Status: **S01 and T01–T05 implemented; all applicable local quality and five-project
init/audit/export gates passed at `b00f06c`; main `1451032` is pushed with all five CI
jobs successful. T06 is separately implemented and locally validated, pending D-41 review.** This report
follows [the approved ordered work](../plan/UX2_2026-10-02.md), following the prior
[UX repair session](2026-10-02-ux-repairs.md). It is not a release or completed-session claim.

## Recorded commits and local quality

| Task | Commit | Tests passed | Pytest seconds | Branch-inclusive coverage |
|---|---|---:|---:|---:|
| S01 | `e09797f` | 1,518 | 180.18 | 93.04% |
| T01 | `ed83fa6` | 1,537 | 221.08 | 93.04% |
| T02 | `175d880` | 1,565 | 194.66 | 93.11% |
| T03 | `0a2e65d` | 1,683 | 208.59 | 93.15% |
| T04 | `5d66783` | 1,728 | 181.62 | 93.20% |
| T05 | `b00f06c` | 1,746 | 173.94 | 93.21% |

S01 approves the selected-task specification and independently derived val §7.1
supplement. T01 separates full task inventory from explicit experiment selection.
T02 prints Findings separately from Result and groups repeated warning fixes with
`--details`. T03 recognizes declared opaque APIs per model role without a request.
T04 adds the explicitly selected `judge_only` profile and one shared conservative
exception for audit and init. T05 adds effective Evaluation/Judge/Privacy and
model/dataset/prompt details with explicit source labels, selected-run snapshots
and literal safe Markdown rendering.

All six runs also have 3 skipped, 2 deselected and the existing single warning.
Ruff check/format, strict mypy, all nine exported-schema byte comparisons and four
generated-document checks pass. Redaction retains all 59 statements and 24 branches
at 100%. [Quality records](ux2-2026-10-02/quality-summary.json) include commands,
elapsed times and source-log/coverage hashes; these are local results, not CI results.
T04's first full run had two failures (1,726 tests passed): one old assertion still
expected seven profiles, and generator/document changes during that run produced
inconsistent rendered/read content. After updating the assertion and aligning the
generated documents, a complete rerun with stationary source passed all checks.
[Red/green evidence](ux2-2026-10-02/regression-summary.json) records acceptance tests
that failed before each implementation.

## T01 complete five-project comparison

All five original checkouts matched the fixed origins/SHAs and remained clean.
Mutation took place only in disposable clones. The completed T01 gate records
**100 commands, 530.905 seconds summed subprocess time**, and zero unexpected exits
or unexplained deltas. This duration is not session wall time. [Full command ledger](ux2-2026-10-02/t01-commands.json)
and [completion record](ux2-2026-10-02/t01-gate-a-complete.json) retain the exact pins,
expected/actual exits, timing and output hashes.

| Repository | Fixed source SHA | Default L1 C/W/I/P/S | Result |
|---|---|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 6/26/3/9/16 | Only the approved metrics declaration and four dependent evaluation rules change. |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 6/30/3/13/17 | Default manifest bytes and full L1 report unchanged. |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 6/27/3/9/16 | Default manifest bytes and full L1 report unchanged. |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 7/20/3/8/16 | Default manifest bytes and full L1 report unchanged. |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 5/17/1/8/7 | Default manifest bytes and full L1 report unchanged. |

All five full L0 reports, verbose diagnostics/stderr, detection, hints and evidence
paths match the reviewed baseline, ignoring only `generated_at`. The old five pins
and L0 gold remain unchanged. Audits use `--fail-on never`, so exit 0 is an expected
policy outcome and does not mean there are no findings.

The [independent source review](ux2-2026-10-02/t01-independent-source-summary.json)
reads 13,986 upstream YAML files with no silently omitted file and identifies
13,123 safe task names. The sorted-set hash remains
`2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`;
legal parentheses remain accepted. `gsm8k` and `arc_easy` have source anchors and
file hashes. These are task candidates, not an assertion that every task or metric
was used in this experiment. The source/rule-derived expectations were approved
in S01 before implementation; current tool output was not promoted to gold.

Historical lm-eval automatic selection produced C/W/I/P/S 5/13,151/3/10/13.
Empty default metrics now produce **6/26/3/9/16**: `eval.metrics_declared` becomes
CRITICAL FAIL, 13,123 implementation warnings become one SKIPPED finding, and
aggregation/repetition warnings become SKIPPED. One explicit task produces
**5/29/3/10/13**; two produce **5/30/3/10/13**. Actual complete changed-rule rows
match the independent rule oracle in all three cases. The complete remaining
report, including profiles and evidence, is equal after excluding those four
rules, derived summary and the independently checked manifest digest.
[Complete delta evidence](ux2-2026-10-02/t01-complete-delta.json) retains normalized
hashes and each selected-task oracle, rather than only summary counts.

Full read-only inventories match before and after init. Unknown/unsafe selectors,
incompatible profiles and invalid list-option combinations exit 2 before writes.
Two-task ordering/duplicates produce identical manifest bytes. Explicit evaluation
selection is checked against its own profile closure rather than default
multi-profile counts. The [source snapshot](ux2-2026-10-02/t01-source-snapshot.json)
records S01 HEAD plus the T01 tracked working-tree diff; it is not mislabeled as
the later T01 commit or as a complete then-untracked-file inventory.

## Final T01–T05 init/audit Gate A

The combined gate ran at committed `b00f06c` with an empty tracked diff and passed
all five fixed projects: **102 commands, 285.138 seconds summed subprocess time**,
zero unexpected exits and zero unexplained deltas. The complete L0 reports and
verbose diagnostics still match historical gold; full default init/L1 comparisons
match the same independent task-selection supplement and the completed T01 results.
The full safe inventory was independently rechecked. T01's exhaustive list/0/1/2,
ordering and no-write error cases are explicitly reused, not claimed as rerun.

Each project also receives explicit `judge_only` init and L1 checks against the
approved exact scaffold, complete rule-ID set and finding predicates. Primary is
SKIPPED under the approved exception; judge/evaluation intent remains required,
and generation/training rules are absent. These are source-defined predicate
checks with hashes of the complete actual reports, not an invented full-report
golden snapshot.

For each default manifest, compact/details output is checked at all three
critical/warning/never thresholds; every CRITICAL/WARNING message is present in
details. Details JSON remains completely equal after timestamp normalization at
each threshold. This retains actual exit policy and full findings while changing
only presentation. All source checkouts remain clean.

[Complete combined comparisons](ux2-2026-10-02/combined-complete-comparisons.json)
retain normalized complete-report hashes, unchanged-portion comparisons,
manifest/hint hashes, exact rule predicates and all threshold outcomes.
[All commands](ux2-2026-10-02/combined-commands.json),
[completion](ux2-2026-10-02/combined-gate-a-complete.json) and
[source binding](ux2-2026-10-02/combined-source-snapshot.json) retain invocations,
exits, timings and provenance. This gate covers init/audit; the export matrix below
is independent.

## T05 five-project export comparison

At `b00f06c`, all five fixed projects passed three scenarios each against the
pre-export baseline `5d66783`: manifest only, offline lock, and a selected older
run. Ten default exports use the unmodified complete CLI and real embedded audit;
15 additional complete current audit reports are captured independently. Forty-five
current-template variants and 45 baseline variants reuse the actual report from
the same immutable scenario and are explicitly marked as harness-cached checks,
not independent end-to-end executions. All four templates are covered per project.

Every new field and source label is checked against authored inputs and effective
manifest/lock/run values. Default repeated exports are byte-identical. Selecting
the older run retains temperature 0.2 and repetitions 7, while the current audit
correctly refers to the latest run's temperature 0.8. Original checkouts retain
their exact pins and clean state. These runs execute only standard-library `pass`
captures; no model, credential, paid API or GPU is used and HTTP constructors are
blocked for every product subprocess.

All **242 subprocess commands** match their expected exits, with **141.260 seconds**
summed subprocess time. Four harness invocations have exits 1/1/1/0: the first
three preserve an independent checklist-column parser error and two groups of
reviewed display differences. The exact allowlist covers dynamic field paths
changing from code to plain literal text, truthful Evaluation/Judge/Privacy section
references, missing-training wording, and absent prompt formats becoming `not
declared` instead of `none` or an invented `plain`. Displayed values remain checked
with a Markdown renderer against the independent input oracle. No product code
or upstream gold was changed during this gate; no unexplained delta remains.

[Completion](ux2-2026-10-02/t05-export-complete.json),
[commands](ux2-2026-10-02/t05-export-commands.json),
[complete comparison evidence](ux2-2026-10-02/t05-export-evidence.json),
[recorded harness recoveries](ux2-2026-10-02/t05-export-recoveries.json) and
[source hashes](ux2-2026-10-02/t05-export-source-hashes.json) retain the full scope.

## Contract clarifications and review boundary

The historical opaque-API proposal incorrectly called lock freshness CRITICAL.
T03 preserves normative `consistency.lock_fresh` **WARNING** and the separate
`consistency.model_identity` **CRITICAL** result. API classification does not erase
stale-lock findings, role-specific identity, State alternatives or pinning limits.
The historical judge proposal also called zero repetitions invalid. T04 preserves
released zero evaluation/judge repetitions and zero temperature behavior; zero
`max_tokens` remains invalid. Neither correction changes a schema or weakens an
existing check to match a mistaken draft.

Approved D-44 supersedes only D-06's seven-profile limit and defines the eighth
profile's product contract. `judge_only` is never detected automatically; only an
explicit declaration with closure inside `{core, judge_only, privacy}` and no
applicable user override receives the primary exception. Mixed/custom selections
retain normal requirements. Init keeps full task inventory, defaults metrics to
empty, and retains unassigned model candidates as comments.

T06 uses a separate versioned archive for the complete original project rule,
required removal reason and timestamp, keeping project-rules v1 intact. The
[compatibility record](ux2-2026-10-02/schema-compatibility.json) verifies that the old
nine schema files remain byte-identical through T05 and in the isolated candidate.
**The new archive schema and concrete implementation still require explicit D-41
maintainer review before merge.** D-44/product authorization does not waive that
review. Candidate tests or its earlier isolated gate do not establish final
integration, approval or the final T05-baseline lifecycle gate.

## Delivery and remaining review

- **T01–T05:** main `145103291ff819d0ed534e5afa7dc3ec211b160a` is pushed and its
  [five-job CI run passed](https://github.com/EnumaElish123/ReproLLM/actions/runs/37017287499).
- **T06:** final candidate `94ae366` passed 1,797 tests and the five-project
  lifecycle gate (92 commands). Its [separate report](2026-10-02-ux2-rule-lifecycle.md)
  records the complete provenance, recovery comparisons and D-41 review boundary.
  The candidate PR tracks remote delivery/CI and approval; no merge is claimed.

Resource Gate B, model/GPU/credential/paid API use, package release and separate
Action publication are outside this request. Existing deferred resource gates
remain recorded in [pending resource validation](pending-resource-validation.md);
this session neither runs nor passes them. Version remains 0.6.1. The compact
[evidence bundle](ux2-2026-10-02/README.md) excludes raw logs, machine identities,
absolute local paths and the large inventory; every JSON has `schema_version: 1`.
