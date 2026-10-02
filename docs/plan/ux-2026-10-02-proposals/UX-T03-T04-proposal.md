> **PENDING — proposal only. Not approved, implemented, filed on GitHub, or adopted as gold.**

# UX-T03 and UX-T04: proposed contract and reviewed expectations

Status: read-only proposal. No repository, baseline, or product code is changed.
Reference HEAD: eb9c9484fe045117e123a369984b7e299e1727a5 (UX-T01 may be edited concurrently).

## UX-T03: retain repository inventory, declare selected experiment tasks

The minimum change is to retain automatic high/medium shipped profile selection, but make that
choice visible. Deterministic task inventory remains complete and separate from selected tasks.
Default `init` writes no discovered task as a metric. Add repeatable `--task NAME` and a read-only
`--list-tasks`; only explicitly selected names become `evaluation.metrics[].name`. Do not add an
arbitrary candidate cap or silently select the first N. No `--all-tasks` is needed for this repair.

Examples:

```sh
reprollm init PATH --list-tasks
reprollm init PATH --profiles evaluation --task gsm8k
reprollm init PATH --profiles evaluation --task gsm8k --task arc_easy
```

`--list-tasks` prints every safe candidate name, sorted and unique, one per line. It creates no
manifest or `.reprollm/` and works even when a manifest already exists. It must discover tasks
independently of whether an explicitly selected profile requires metrics. Reject ambiguous
combinations with `--interactive`, `--task`, `--force` or `--profiles`, rather than implying a write
occurred or silently ignoring an explicit profile override. The complete list may be piped to a
search/pager; listing does not shrink the retained inventory.
There is no new persisted candidates document or JSON Schema in the minimum version.

`--task` matches exact names against the complete safe inventory, preserving quoting and Unicode.
Duplicate selectors are deduplicated and output is sorted. Unknown/unsafe names exit 2 before any
owned files are written, and explain `init PATH --list-tasks`. If the selected profile closure does
not require `evaluation.metrics`, exit 2 rather than ignore the task or silently add a profile.
No tasks selected means the existing `metrics: []` TODO scaffold. No implementation, aggregation,
runtime binding, dataset, or metric transformation is inferred from a task name.
Define a listable/selectable name as nonempty and single-line after secret/machine-identity checks;
control/line-separator characters are rejected so names cannot create extra rows or terminal
commands. Preserve ordinary Unicode and remaining names exactly, without trim/normalization.
Independently confirm this safety filter does not change the 13,123-name pinned inventory.

Print these facts explicitly after a successful ordinary init:

```text
Applied detected profiles: evaluation, finetuning, inference.
Review experiment.profiles; use --profiles to select this experiment's profiles.
Task candidates: 13123; selected: 0. List with: reprollm init PATH --list-tasks
No task is declared in evaluation.metrics. Select with --task NAME, or edit metrics manually.
```

For an explicit profile override use `Applied selected profiles` instead. When no candidate exists,
keep the existing empty metric scaffold byte-for-byte; explanations belong to stdout, not a new
large manifest comment block.

Interactive flow: show detected profile/confidence choices and prompt for comma-separated shipped
profiles, with the automatic list as the visible default. Enter explicitly accepts that default.
Then show task candidate count and a list command, and accept exact task names one per prompt
(empty input ends selection). Do not dump 13,123 menu rows or treat commas in a task name as a list.
Finally prompt required scalar fields as today; selected task entries still need human metric
name/implementation confirmation. Noninteractive init never blocks on a prompt.

Forcing explicit profiles in every noninteractive call is a separate, larger behavior change:
spec §3.2/§13 and val §7 presently require automatic selection. It would alter all five default
manifests and many Level1 rules. It is unnecessary to solve the observed task overload. This
proposal preserves the profile contract while making author review conspicuous.

### Proposed specification edits (require maintainer review before implementation)

- CLI table, spec:33: append `[--task NAME]... [--list-tasks]` to `init`.
- Spec §3.2, after the existing paragraph: “Task inventory and experiment selection are separate.
  `init --list-tasks` is read-only and lists the complete safe deterministic task inventory. `init`
  leaves evaluation.metrics empty unless the author explicitly selects names using repeatable
  `--task NAME` or the interactive task prompt. Selected names are sorted and deduplicated; unknown
  names, unsafe names, and task selectors incompatible with selected profiles are usage errors
  before writes. Automatic profile choices are printed with a review/override hint. Interactive
  init offers profile selection before task selection and required-field prompts.”
- Replace spec §14:709–714 with: “Evaluation framework task hints are internal initialization
  candidates, not an assertion that every discovered task was used by an experiment. Preserve the
  complete sorted unique safe inventory. When evaluation.metrics is required, init pre-fills only
  explicitly selected task names; without selection it renders an empty TODO list. The author must
  confirm each metric name and implementation. An explicit profile selection that does not require
  evaluation does not pre-fill metrics. Framework YAML tags are inspected as syntax only and never
  executed; non-string, secret-bearing, or machine-specific names are neither listed nor selected.”
- M11-T01, M9-M12_adoption.md:103: replace “供 init 预填 evaluation.metrics[].name” with
  “保留完整候选供 init --list-tasks 审阅；只有维护者通过 --task 或交互选择的任务名才预填
  evaluation.metrics[].name，仍须确认 metric 名称及 implementation。”
- Public framework docs/init help and CHANGELOG must explain changed default behavior; historical
  follow-up reports remain historical and should not be rewritten as if they never occurred.
- val §7 receives the reviewed supplement below before implementation output is accepted as gold.

### Independent source evidence and proposed gold supplement

All five pinned checkouts are clean and match val §2. A fresh independent YAML-node inventory
reads task syntax only, never imports the framework, and finds 13,123 task names; no YAML omitted.
Name-set SHA256 stays `2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`.
See `source-review.json` for exact pins, source anchors, count and set hash. The complete source inventory is retained only in the local validation workspace as `scope/independent-lm-eval-task-gold.json`, not included as a repository artifact.

Selected-name source examples at lm-evaluation-harness pin b954108:

- lm_eval/tasks/gsm8k/gsm8k.yaml:3 declares `gsm8k`; lines12–15 declare metric `exact_match`.
- lm_eval/tasks/arc/arc_easy.yaml:3 declares `arc_easy`; lines15–20 declare `acc` and `acc_norm`.

These show that task identity is not necessarily metric identity. Preserve the narrowly approved
M11 task-name scaffold contract; do not fabricate implementation/metric mapping in this repair.

Proposed val §7 supplement (not yet adopted):

1. Profiles, models.primary evidence, provider/backend hints, all dependency sets, scan diagnostics,
   pin SHAs and complete Level0 JSON remain unchanged in every target.
2. lm-eval default: `evaluation.metrics=[]`; the complete candidate inventory remains 13,123 with
   the original hash. No task name is silently declared. Exact affected Level1 changes:
   `eval.metrics_declared`: PASS -> FAIL CRITICAL (profile override); implementation warning rows
   for indices0..13122 -> one SKIPPED finding; aggregation/repetitions WARNING -> SKIPPED. All other
   complete findings are unchanged. Expected C/W/I/P/S = 6/26/3/9/16, not a new finding-count gold
   inferred from product output.
3. lm-eval `--profiles evaluation --task gsm8k`: selected metrics exactly `[{name: gsm8k}]`;
   implementation remains absent. Only evaluation profile closure applies; do not compare its
   complete counts to the automatic multi-profile report.
4. lm-eval `--task gsm8k` with default automatic profiles: same profiles as §7, one declared name;
   metrics presence PASS, one missing implementation WARNING, aggregation/repetitions WARNING.
   Expected C/W/I/P/S = 5/29/3/10/13. For two selected names warning count is30; ordered names
   `[arc_easy,gsm8k]`. These predictions follow eval_.py:40–56/68–75/117–141 and evaluation.yaml:22.
5. FastChat, LlamaFactory, HarmBench and llm-dp default: candidates empty in the existing framework
   inventory; no change to their generated YAML or full Level1 JSON. Confirm exact bytes rather
   than assuming this from counts. Supplemental fixture cases cover lighteval/inspect task names.
6. Unknown task, unsafe task and incompatible profile selection exit2 without writes; listing
   exits0 without writes; selection order cannot change output bytes.

The change is a reviewed manifest-selection policy supplement, not a pin refresh or a copied
snapshot. D-04, D-06, D-13 and D-25 stay intact. It needs spec/M11/val changes, but no frozen decision
change and no D-41 files (core/engine.py, core/redaction.py or schemas).

## UX-T04: concise terminal report, complete machine evidence, explicit exit policy

The current text reporter prints all warnings individually (reporters/text.py:69–91), then marks
any warning as Result FAIL (102–110). CLI actually exits using the effective --fail-on threshold
(cli/audit.py:51–60/95/146). A warning-only report therefore says FAIL with default exit0; critical
findings with `--fail-on never` also say FAIL/exit0. The text never states which threshold applies.

Recommended minimum text contract uses two explicit concepts:

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

Use `Findings: PASS` only when no unsuppressed FAIL critical/warning remains. This avoids implying
that disabled failure or warnings are an unconditional reproducibility pass. CLI calculates exit
code once from the unchanged full report, passes that value plus effective threshold to the text
renderer, and raises the same code. Do not add threshold fields to persisted AuditReport/schema.
Explicit flag and configured threshold must both be reflected accurately.

Default aggregation is presentation-only for repeated `status=fail,severity=WARNING` rows with
identical rule_id and fix_hint. Keep CRITICAL, INFO, suppressed, skipped and PASS rows separate
initially. A group shows the exact finding count, three deterministic example messages/evidence
locations (or all when fewer), one shared fix, and an explicit `--details` expansion hint. Example:

```text
WARNING (13151 findings)
  ! eval.metric_implementation_referenced — 13123 findings (3 shown)
      evaluation.metrics.0.implementation is missing
      evaluation.metrics.1.implementation is missing
      evaluation.metrics.2.implementation is missing
      fix: Set evaluation.metrics.<index>.implementation to a relative file or pkg==version in reprollm.yaml.
      Use --details for every finding; --format json preserves all evidence.
```

Grouping cannot change or remove a Finding, alter severity, suppress a rule, alter the overall
summary, or change exit. Separate groups when fix_hint differs. Group entries sorted by rule ID;
examples follow existing deterministic report order. Do not guess a shared cause from text, strip
message numbers for grouping, or aggregate different suppression reasons. `--details` emits the
full original individual rows, retaining fixed severity order, symbols and --show-passed/skipped.
JSON and GitHub annotation output stay complete and byte-identical modulo approved timestamps.

Specification edits: add audit `[--details]` to spec CLI table; §21 explicitly defines grouped text,
three-example limit, shared fixes, complete JSON, expansion mode, and distinct Findings/Result
lines above. Severity vocabulary, overrides/suppressions and --fail-on semantics do not change.
No frozen decision or D-41 file change is needed (D-09/10/11 remain intact).

Tests before implementation: warning-only default critical (exit0), warning threshold (exit1),
critical+never (exit0), configured vs explicit threshold, pass-only and suppressed/skipped-only,
groups with 2/3/4/large warning counts, same rule with different severity/status/fix_hint, safe
evidence paths, byte-deterministic compact and expanded text, full JSON equality and unchanged
GitHub annotations/exit. Existing text snapshots change only in a deliberately reviewed diff.

Five-project validation after quality gate: Level0 JSON full exact comparison for all pins, plus
current text/default/details and three thresholds on all five. No JSON/hint/profile/findings gold
delta is expected for UX-T04. When combined with UX-T03, Level1 semantic deltas must be isolated to
the reviewed selected-metric contract above; terminal aggregation cannot conceal an unexplained
delta. Preserve old gold and full reports as historical evidence.
