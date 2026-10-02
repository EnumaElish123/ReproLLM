> **PENDING — proposal only. Not approved, implemented, filed on GitHub, or adopted as gold.**

## Problem

The 0.6.1 product trial found two contract-level usability problems:

1. `init` treats the complete framework task inventory as experiment metrics. At the unchanged
   lm-evaluation-harness pin `b954108c9baaaa934b4ad842033b31a97ee30816`, that writes 13,123 metric entries
   into a 589,351-byte manifest and produces one missing-implementation warning per task. Repository
   inventory does not establish that this experiment used all of those tasks.
2. Audit text says `Result: FAIL` for warnings, while the default `--fail-on critical` correctly exits
   0. With `--fail-on never`, even critical findings exit 0. The terminal gives no threshold explanation
   and repeats thousands of individual warnings; JSON is already complete and should remain so.

This issue proposes the normative changes required for UX-T03/M11-T01 and UX-T04/M10-T03. The ordered
repair plan requires these changes to be reviewed before implementation/output baseline changes.

## Proposed init contract

- Preserve complete deterministic detection and all safe task candidates; never truncate the
  candidate set to an arbitrary first N.
- Default `init` writes `evaluation.metrics: []` with TODO instructions. It declares no unselected task.
- Add repeatable `--task NAME`. Select exact detected names only, deduplicate/sort them, and pre-fill
  only those names in `evaluation.metrics[].name`. Implementation remains unfilled and the author
  must confirm metric names. Unknown/unsafe names and task selectors incompatible with the selected
  profile closure exit 2 before writes.
  Define selectable/listable names as nonempty single-line names after existing secret and machine
  identity checks; reject control/line-separator characters rather than emitting terminal commands
  or ambiguous extra list rows. Preserve ordinary Unicode and the exact remaining name, without
  trimming or transforming it. Confirm this safety filter has zero delta at the existing pin.
- Add `init PATH --list-tasks`: read-only, complete sorted unique safe names, one per line; no
  manifest or `.reprollm/` write, no network, usable after initialization. Reject `--interactive`,
  `--task`, `--force` and `--profiles` combined with listing. Listing is independent of selected
  profiles; do not silently ignore an explicit profile override. Full listing intentionally remains
  large; the caller may pipe it to a search/pager without changing the retained candidate inventory.
- Preserve automatic high/medium shipped profiles. Print `Applied detected profiles: ...`, tell
  the author to review `experiment.profiles`/override with `--profiles`, and state candidate/selected
  counts. Explicit overrides print `Applied selected profiles`.
- `--interactive` offers visible profile choices/default first, then exact task names one at a time
  (blank ends selection), then current required-field prompts. Do not dump the complete catalog as
  a menu. Noninteractive init never prompts.
- Do not infer task execution, actual metric implementation, dataset, runtime bindings or defaults.
  A selected task is still scaffolding that requires author confirmation.

Example:

```console
reprollm init . --list-tasks
reprollm init . --profiles evaluation --task gsm8k
```

Update specification CLI table and §§3.2/14, M11-T01 and public framework instructions. Replace
§14's unconditional “pre-fills sorted, unique task names” with “retains the complete sorted unique
safe inventory; pre-fills only explicitly selected task names, otherwise an empty TODO list.”

## Proposed audit text contract

Keep findings and command exit policy separate:

```text
Findings: FAIL (0 critical, 5 warning)
Result: exit 0 (--fail-on critical; no finding reaches the threshold)
```

```text
Findings: FAIL (2 critical, 5 warning)
Result: exit 0 (--fail-on never; finding-based failure disabled)
```

```text
Findings: FAIL (0 critical, 5 warning)
Result: exit 1 (--fail-on warning; findings reach the threshold)
```

Use `Findings: PASS` only when no unsuppressed critical/warning failure remains. The CLI computes
the exit code from the complete unchanged report once, passes the value/effective threshold to
the renderer, and exits with that same value. Honor both configuration and explicit overrides.

In default text, aggregate repeated WARNING/FAIL findings sharing rule ID and fix hint: exact
count, up to three deterministic example messages/evidence locations, one shared fix, and an
explicit expansion hint. Keep different severities/statuses/fix hints and suppressed reasons
separate. Initially leave CRITICAL, INFO, suppressed, skipped and PASS rows fully individual.
Add `audit --details` for the complete individual rows. Counts always refer to full findings.
JSON and GitHub annotations remain complete and semantically unchanged. This is presentation
only: no severity change, rule suppression, inference or weakened exit threshold.

Update specification CLI table and §21 with these defaults, expanded mode and Findings/Result
semantics. Keep ASCII/symbol behavior and existing show-passed/show-skipped controls.

## Independent source review and proposed gold delta

All five pinned source checkouts were verified clean with the exact current val §2 SHAs. A separate
YAML-node reader (no framework/ReproLLM import or YAML tag execution) again found exactly 13,123
safe lm-eval names, zero omitted YAML; compact sorted-name SHA256:

`2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`

At that pin, `lm_eval/tasks/gsm8k/gsm8k.yaml:3` declares `task: gsm8k` but lines12–15 declare metric
`exact_match`. `lm_eval/tasks/arc/arc_easy.yaml:3` declares `arc_easy`, while lines15–20 declare
`acc` and `acc_norm`. These source facts demonstrate why inventory must not become an automatic
experiment declaration, and why implementation/metric semantics cannot be invented here.

Proposed reviewed supplement to val §7 (preserve every pin and original detection gold):

- All five Level0 full JSON, profiles, dependencies, hints, relative evidence, HF IDs and scan
  diagnostics remain unchanged. Full inventory retains the original 13,123 names/hash.
- lm-eval default metrics become empty. Exact Level1 delta: `eval.metrics_declared` PASS -> CRITICAL
  FAIL (existing evaluation profile override); 13,123 implementation warnings -> one SKIPPED;
  aggregation/repetitions WARNING -> SKIPPED. Every other finding remains unchanged. Expected
  critical/warning/info/pass/skipped = `6/26/3/9/16` (current `5/13151/3/10/13`).
- With default profiles plus `--task gsm8k`, declare exactly `[{name: gsm8k}]`, no implementation.
  Metrics presence PASS; one implementation WARNING; aggregation/repetitions WARNING. Expected
  `5/29/3/10/13`. Two selected names `[arc_easy,gsm8k]` give warning30; invocation order must not
  change manifest bytes. An explicit `--profiles evaluation` has its own smaller closure and is
  compared independently rather than reusing automatic-profile counts.
- The other four default manifests and complete Level1 reports remain byte-identical except
  approved timestamps. Additional controlled lighteval/inspect fixtures verify the same selection
  semantics. No candidates or selected name is silently dropped.
- UX-T04 changes text snapshots deliberately; full audit JSON/GitHub output, findings, summaries,
  profiles, hints, diagnostics and exits have zero semantic delta.

These expected changes are derived from selected source task names plus existing rule applicability
(`eval_.py:40–56,68–75,117–141`, `profiles/evaluation.yaml:22`), not copied from new product output.
Review the complete finding diff, not summary counts alone. Preserve previous reports as history.

## Boundaries and acceptance

No frozen decision needs to change: D-04/D-06/D-13/D-25 and severity/exit D-09/D-10/D-11 remain intact.
The minimum implementation avoids `core/engine.py`, `core/redaction.py` and exported schemas, so
it does not introduce D-41 review scope. No LLM/network/heavy dependency is needed.

Write regression tests first for listing with no writes, exact/deduplicated/sorted selection,
unknown/unsafe names before writes, incompatible profiles, default empty metrics, interactive
profile/task order, no tag execution, and private-name rejection. Text tests cover explicit and
configured thresholds, critical+never, warning+critical/warning, suppression/skips, grouping
boundaries and differences, determinism, full JSON equality and GitHub annotations.

After quality gate, run all five Gate A originals and disposable init/Level1 matrices plus listing,
selected-task/invalid-selector cases and compact/details/threshold text. Adopt the policy supplement
only as a separately reviewed baseline change; never refresh pins or copy current output into gold.
