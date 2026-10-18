# S4-B resource readiness — 2026-10-18

**Release readiness: BLOCKED.** This session implements and validates D03's
publication controls. It does not execute the formal release resource matrix.
There is no complete, same-candidate `release-validation` bundle. No GPU/model
execution, paid provider request, authenticated gated-file request or new
resource budget was provisioned for this session.

The authoritative inputs, pins, expectations and resource guards remain in
[val.md §§8.1–8.6](../../../val.md#8-mandatory-validation-gates). The
[release contract](../../releasing.md) indexes them with 28 compact gate IDs:
five Gate A entries and the **23 Gate B entries below**. The index does not
replace the detailed acceptance criteria or authorize resource use. Each row
requires fresh evidence for the exact future release candidate SHA.

The new engineering tests use controlled synthetic success/failure fixtures.
The session's fresh five-project L0 baseline and static facts checks cover
their recorded non-resource scope. Neither establishes formal release Gate B
PASS or closes the full release matrix.

## Dated evidence retains its original identity

- [2026-10-13 VAL-R01 replay](../2026-10-13-val-r01/README.md), candidate
  `26c0b4a716b5b025058a3b1daabc64afdf1a022d`: Linux H2's five-project metadata
  checks and LlamaFactory's native LoRA capture/diff were accepted. The other
  four projects' native children completed, but eight captures failed non-secret
  snapshot fidelity. Their output/diff successes do not erase those failures.
- [2026-10-15 S4-A](../2026-10-15-reliability-s4a/README.md), candidate
  `b86c014cf9f15f1efddb6902979dcc6ddf79be9f`: the repaired product bytes and
  candidate wheel passed the formal lm-eval A/B capture, consumption, semantic
  diff and export case. The other four native projects were not rerun on those
  product bytes. Later CI/tool commits retain this exact historical identity.
- The earlier formal DeepSeek judge and public DistilGPT2 promotions in
  `val.md §8.5`, and the 2026-10-01 live discover success in `§8.6`, remain
  historical evidence. They do not establish current-candidate resource PASS.

## Formal Gate B status by compact ID

Every row is **BLOCKED: not rerun in this session**. This is a readiness ledger,
not a machine-consumable successful validation artifact.

| Compact gate ID | Status | Required evidence still absent for the release candidate |
|---|---|---|
| `m4_metadata:lm-evaluation-harness` | BLOCKED | Fresh reviewed metadata inputs; offline/two-online/check/audit sequence and complete hashes/freshness; applicable Linux H2, doctor and network-probe checks. The 2026-10-13 H2 result retains its old SHA. |
| `m4_metadata:FastChat` | BLOCKED | Fresh reviewed metadata inputs; complete offline/online, hash, freshness, Linux H2 and applicable doctor/network-probe evidence. Historical H2 is not a candidate replay. |
| `m4_metadata:LlamaFactory` | BLOCKED | Fresh reviewed metadata inputs; complete offline/online, hash, freshness, Linux H2 and applicable doctor/network-probe evidence. Historical H2 is not a candidate replay. |
| `m4_metadata:HarmBench` | BLOCKED | Fresh reviewed metadata inputs; complete offline/online, hash, freshness, Linux H2 and applicable doctor/network-probe evidence. Historical H2 is not a candidate replay. |
| `m4_metadata:llm-dp-finetune` | BLOCKED | Fresh reviewed metadata inputs; complete offline/online, hash, freshness, Linux H2 and applicable doctor/network-probe evidence. Denial handling remains distinct from the successful-access gate below. |
| `runtime_pair:lm-evaluation-harness` | BLOCKED | Fresh bounded GSM8K cap 32→48 native pair with complete capture, snapshot fidelity, independent consumption/output checks, required HIGH leaf and self-diff. The accepted 2026-10-15 pair belongs to the b86 candidate. |
| `runtime_pair:FastChat` | BLOCKED | Fresh bounded native local-answer cap 32→48 pair and complete capture/diff acceptance. The separate paid judge is required by `api_judge`. |
| `runtime_pair:LlamaFactory` | BLOCKED | Fresh two-update native LoRA learning-rate pair and complete capture/diff acceptance. The 2026-10-13 accepted pair and explained environment delta retain the 26c candidate identity. |
| `runtime_pair:HarmBench` | BLOCKED | Fresh one-behavior native attack/target/classifier path and cap 16→24 pair; complete capture, source fidelity and semantic acceptance. |
| `runtime_pair:llm-dp-finetune` | BLOCKED | Fresh formal DistilGPT2 privacy fine-tuning pair, real optimizer/DP checks, source fidelity and epsilon 8→4 MEDIUM leaf; a HIGH config hash cannot substitute for that leaf. |
| `export:lm-evaluation-harness` | BLOCKED | Fresh export acceptance for every applicable available state, tied to current-candidate inputs and native captures. Historical S4-A exports retain their original SHA. |
| `export:FastChat` | BLOCKED | Fresh export acceptance for every applicable available state, including applicable answer/judge captures with truthful provenance and resource evidence. |
| `export:LlamaFactory` | BLOCKED | Fresh export acceptance for every applicable available state, tied to current-candidate inputs and accepted native captures. |
| `export:HarmBench` | BLOCKED | Fresh export acceptance for every applicable available state, tied to current-candidate inputs and accepted native captures. |
| `export:llm-dp-finetune` | BLOCKED | Fresh export acceptance for every applicable available state, preserving the formal privacy parameter and capture provenance. |
| `discover_collection:lm-evaluation-harness` | BLOCKED | Fresh formal offline collection, complete file-list/payload expectations, limits and privacy checks at the pinned source and candidate. |
| `discover_collection:FastChat` | BLOCKED | Fresh formal offline collection, complete file-list/payload expectations, limits and privacy checks at the pinned source and candidate. |
| `discover_collection:LlamaFactory` | BLOCKED | Fresh formal offline collection, complete file-list/payload expectations, limits and privacy checks at the pinned source and candidate. |
| `discover_collection:HarmBench` | BLOCKED | Fresh formal offline collection, complete file-list/payload expectations, limits and privacy checks at the pinned source and candidate. |
| `discover_collection:llm-dp-finetune` | BLOCKED | Fresh formal offline collection, complete file-list/payload expectations, limits and privacy checks at the pinned source and candidate. |
| `api_judge` | BLOCKED | Formal FastChat/DeepSeek question-82 cap 256→384 pair under `val.md §8.4`; restored exact inputs, fresh authenticated model/tariff/budget preflight, bounded attempts, full M5/M6 capture/diff and M7 API-judge acceptance. |
| `discover_live` | BLOCKED | Fresh provisioned `val.md §8.6` production discover case: bounded request, reviewed payload, usable source-backed candidate, explicit accept/audit and duplicate-rejection checks. A paid response alone is insufficient. |
| `hf_gated` | BLOCKED | Fresh model-author-authorized successful access to the selected small HF files; independently reviewed revision/hash expectations, repeated-lock/freshness/privacy checks. Another anonymous 401 or authenticated 403 is not success. |

## Standing blockers and resumption

The [standing resource ledger](../pending-resource-validation.md) retains its
three independent **BLOCKED** groups:

| Tracking ID | Current boundary |
|---|---|
| VAL-R01 | The current-candidate native matrix remains incomplete; dated H2/LlamaFactory and lm-eval acceptance does not replace fresh full release coverage. |
| VAL-R02 | The exact formal judge inputs and fresh provider/access/tariff/budget preflight must precede the bounded paid pair. |
| VAL-R03 | Successful model-author-approved gated-file resolution remains unverified for the release candidate. |

After resources are explicitly provisioned, restore the exact reviewed inputs,
verify their hashes and all five pins, and follow `val.md`'s current resource
guards. Run the applicable full quality/Gate A prerequisites and complete the
resource matrix on one candidate SHA. Retain actual commands, exits, timing,
independent expected/actual comparisons and input/report hashes, with sanitized
evidence. Do not reuse an earlier session's budget, resource lease or release
waiver as authorization.

Only genuine complete evidence may become the documented `release-validation`
artifact from a successful same-commit, same-repository validation run. Until
then, preflight must fail closed. A nonpublishing workflow rehearsal and any
future version release remain distinct actions; this session creates no tag or
publication and requests no resource execution.
