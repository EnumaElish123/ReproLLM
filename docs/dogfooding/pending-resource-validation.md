# Pending resource validation

Recorded: 2026-10-01. Owner: ReproLLM maintainers.

**Later model replacement — 2026-10-27:** the maintainer cannot obtain Llama-2
permission and directed a model change. [M4-META-PUBLIC-20261027](metadata-public-model-2026-10-27/README.md)
and `val.md §8.1.2` replace Project C with public DistilGPT2. The old mandatory
gated-success gate is **SUPERSEDED_NOT_PASSED**. Current VAL-R03 tests public
metadata/file resolution and persistence, with results in the new bundle.
No Llama-2 access request is required for future formal validation.

The revised public-model gate **PASS** at product candidate `00c2392`: anonymous
official model/config/tokenizer access, all five metadata cases/15 modes,
complete locks/audits/stderr and repeat locks pass; 51 product commands and
the gpt2 metadata probe exit 0. This closes the current VAL-R03 prerequisite,
without turning the retired gated-success branch into a pass.

**Earlier input update — 2026-10-27:** the maintainer directed replacement of the
five unavailable metadata manifests. [M4-META-20261027](metadata-formal-2026-10-27/README.md),
adopted by `val.md §8.1.1`, supplies all five new formal inputs in version control.
Future validation uses these files; historical 45/50 recovery and old MISSING
records remain unchanged. VAL-R03's input prerequisite is satisfied, but its
successful-access branch remains BLOCKED on Llama-2 authorization. Existing
VAL-R01/R02 results remain candidate-bound.

These are the three unfinished validation groups reported after the **0.6.1**
patch release (`9ed6d9964d39281cf62cca667b0457c90fb352c1`). They track fresh
release coverage, not missing feature implementations. The maintainer directed
the session to defer unavailable resources and complete the executable checks.

[`val.md`](../../val.md) remains authoritative for repository pins, inputs,
commands, independent gold and resource guards. This checklist does not change
that baseline. Earlier successful executions remain historical evidence;
resource blockers, actual capture failures and active replays are distinguished
below, and later-candidate results are not fresh passes for 0.6.1.

Updated 2026-10-13: [current-candidate resource replay](2026-10-13-val-r01/README.md)
restored the reviewed inputs and completed Linux H2 plus ten native GPU A/B
children at `26c0b4a716b5b025058a3b1daabc64afdf1a022d`. Linux H2 and
LlamaFactory capture/diff are accepted; eight captures from the remaining four
projects fail non-secret snapshot fidelity. All specified semantic leaves,
self-diffs and independent native output checks pass, and default export
projection is checked separately from the failed upstream captures. VAL-R01
remains open for the existing path-redaction implementation follow-up. These
are later-candidate results, not a promotion of the historical 0.6.1 release.
Recovered judge inputs and configured credentials do not substitute for a
fresh VAL-R02 bounded API run or VAL-R03 authorized-file success.

Updated 2026-10-15: [S4-A D01/D02](2026-10-15-reliability-s4a/README.md), candidate
`b86c014cf9f15f1efddb6902979dcc6ddf79be9f`, repairs the observed source snapshot
fidelity defects. Ten original failing input files now retain exact bytes in a
fresh public-CLI capture. The formal lm-eval A/B GPU recipe passes complete
capture, consumption, diff and export acceptance using the candidate wheel.
The other four native projects have not been rerun on these product bytes;
their historical evidence does not establish current release readiness.

Updated 2026-10-18: [A01-A local input recovery](2026-10-18-a01-local/input-readiness.md)
inventories 50 required input slots: 12 recovered with exact independent hashes,
5 original metadata manifests missing, and 33 inaccessible through the current
remote evidence connection. The input inventory retains formal/supplementary
identities and exact recovery members. Historical remote availability does not
establish local possession. The [local resource receipt](2026-10-18-a01-local/resource-readiness.json)
records a 16 GiB GPU, below the current formal native guard. Paid API calls are
excluded from this session; authorized gated-file success remains unprovisioned.
No resource checkbox is promoted by input recovery or offline regression tests.

Updated 2026-10-18, R08-A P-B: the maintainer accepted the direct judge-param
HIGH default and the prospective [val §8.4.1](../../val.md#841-prospective-r08-a-judge-policy-supplement).
New comparisons after this policy use HIGH for the direct cap leaf; historical
§8.4 MEDIUM reports stay unchanged. [Local policy validation](2026-10-18-r08a/README.md)
does not restore the original judge bundle, provide execution/budget or model
access, or close any resource checkbox. Paid API calls and publication are
excluded from this session.

Updated 2026-10-19: the [provisioned-node replay](2026-10-19-resource-completion/README.md)
restores 45 of 50 exact input slots; no slot remains inaccessible on this node.
Linux H2, ten real native GPU children, all five complete semantic pairs and
20 available default export states pass on candidate
`750270b10307455795fcff126664429dc895983a`. VAL-R01 is closed for these product
bytes. The maintainer's continuing actual-capacity GPU guidance supersedes old
artificial numerical launch restrictions in `val.md §8.3`; historical receipts
and gold inputs retain their identities.

At `750270b`, the formal DeepSeek A request succeeds, but capture fails two
non-secret source snapshot requirements: `common.py` is omitted and four unused
multi-turn rubric rows are changed. Both have independent CPU reproducers; no product fix or
second completion is performed. VAL-R02 is **FAIL**, rather than missing an
input bundle or budget. HF authentication succeeds, but both selected restricted
small files return 403; original §8.1 manifests are still missing. VAL-R03 remains
**BLOCKED**. This is not release readiness or a retrospective pass for 0.6.1.

Updated 2026-10-19, R02-R follow-up: the
[snapshot repair](2026-10-19-judge-snapshot-fix/README.md) at candidate
`75d1b065e9f0e3eeafa8e480e195a2a2ddbe95b5` passes final quality and fresh
five-project CPU capture/diff/export acceptance, including exact original Python
and complete eight-row JSONL snapshot fidelity. Under a newly approved CNY 3
budget, both new formal requests, complete captures and the full semantic pair
PASS, closing VAL-R02 for `75d1b0`. The seven changes are the direct cap HIGH,
config-file hash HIGH, clean commit MEDIUM and four NONE metadata changes;
self-diff is empty and `--fail-on HIGH` exits 1. The older `750270b` paid A
remains FAIL and its B NOT_RUN. VAL-R01's native acceptance remains bound to
`750270b`; the CPU repair
does not rerun GPU/H2. HF 403 and all five original metadata-manifest gaps remain
independent, with no new HF success or release-readiness claim.

Updated 2026-10-20: the [prior-product validation follow-up](2026-10-20-validation-followup/README.md)
passes fresh final quality and five-project Gate A at
`948d16423023027fff77322b8a872acaba306691`, then replays Linux H2 and all ten
native children with complete captures, consumption, five semantic pairs and
20 exports. VAL-R01 is now PASS for those product bytes. The approved
`DISCOVER-INIT-948D-20261020` current-input case also completes one real provider
request and reviewed `top_p` acceptance; three input hashes differ from the
historical case, whose gold stays unchanged. Formal judge A/B is not repeated:
VAL-R02 retains `75d1b0` acceptance. A fresh preflight still authenticates but
returns 403 for both restricted small files. All five original metadata
manifests remain missing. The subsequent R06-B policy change has separate CPU
quality/Gate A evidence; these resource runs are not relabelled to its commit.
No release is authorized.

Updated 2026-10-26: the [current-candidate validation completion](2026-10-26-validation-completion/README.md)
executes fresh quality, five-project Gate A and affected consumers, anonymous
supplementary Linux H2, all ten native GPU children/five pairs/20 exports and
25 complete native audit comparisons at
`6afe8f40ab8d33e191ca0e75c4e5e08a57cabc46`.
The DP epsilon leaf is HIGH under accepted R08-B. A newly approved CNY 3
ceiling covers two original-input formal judge requests, complete captures,
independent exports and the full HIGH-cap pair. VAL-R01 and VAL-R02 pass for
these product bytes. A separately approved CNY 4 current-input discover case
also completes one request, independent source review and candidate acceptance.
Historical inputs, gold and earlier failures remain unchanged. The current
authenticated HF preflight is 200 for identity and 403 for both selected small
files; all five original metadata manifests remain missing. The maintainer
directed completion of the other checks. VAL-R03 remains BLOCKED; no release.

| Tracking ID | Outstanding coverage | Current cause | Status |
|---|---|---|---|
| VAL-R01 | Linux H2; five bounded native inference/training A/B pairs; capture/consumption/diff/export | Fresh anonymous supplementary H2/native/capture/diff/25 full audits/20 exports at `6afe8f4`; original §8.1 inputs remain separate | PASS — 2026-10-26, `6afe8f4` |
| VAL-R02 | Formal FastChat/DeepSeek judge pair and M7 API-judge acceptance | Two new original-input provider requests, full capture fidelity, independent exports and complete HIGH direct-cap pair under a newly approved CNY 3 ceiling | PASS — 2026-10-26, `6afe8f4` |
| VAL-R03 | Successful authenticated HF gated-file resolution | Authenticated small files still return 403; original Project C metadata manifest remains missing | BLOCKED |


## VAL-R01 — Linux and five-project GPU replay

**Resources:** an accessible Linux runner; explicitly provisioned GPU, storage,
model/data access and isolated framework environments; the exact reviewed
manifests, validation drivers and A/B configs. Linux H2 itself does not require
a GPU and can be completed separately. Recover input bytes and verify their
hashes; hashes alone cannot reconstruct the missing bundles.

**Resume:** verify all five source checkouts against [`val.md` §2](../../val.md#2-pinned-portfolio).
For Linux H2 use the metadata command sequence and reviewed inputs in
[§§8.1–8.2](../../val.md#81-m4-metadata-resolution-scenarios-reviewed-2026-09-19);
do not label supplementary manifests as the original M3 inputs. For GPU replay,
use the five bounded native commands, model identities, A/B changes and resource
guards in [§8.3](../../val.md#83-activated-bounded-linux-runtime-inputs-2026-09-26)
and the [independent runtime gold](m5-m6-runtime-gold.md). Read the corrected
lm-eval input and completion records in §§8.3 and 8.5a–8.5c before preparing runs.
Previous shared-GPU exceptions are historical approvals, not a replacement for
checking the resources provisioned for the new execution.

**Closure for 2026-10-19 candidate `750270b`:**

- [x] Linux H2: all five supplementary metadata inputs, offline/two-online/check/audit,
  exact hashes/revisions, normalized lock equality, freshness, doctor and probe.
- [x] lm-evaluation-harness: bounded native inference, A/B capture/consumption,
  source fidelity, exact HIGH cap leaf and available-state exports.
- [x] FastChat: real local answer generation, both turns, actual consumed cap,
  complete A/B capture, HIGH target drift and available-state exports.
- [x] LlamaFactory: two actual LoRA optimizer updates per variant, finite raw
  loss, actual learning-rate observation, adapter checks and A/B acceptance.
- [x] HarmBench: native DirectRequest/target/classifier, complete A/B acceptance,
  actual cap observation and classification checks; no generated text published.
- [x] llm-dp-finetune: formal DistilGPT2 privacy pair, real clipping/noise/optimizer
  assertions and the unchanged MEDIUM epsilon leaf under §8.5.
- [x] Every pair passes bindings, package metadata, original input/output hashes,
  snapshot fidelity and privacy; self-diffs are empty and all 35 changes explained.
- [x] Twenty available default export states pass complete projection checks:
  five manifest-only, five lock-only and ten selected-run states.

The [report](2026-10-19-resource-completion/README.md) retains initial observer
failures and same-raw qualifications without repeating a native child. Eight
launches satisfy the historical strict checks; the last two use the latest
explicit actual-capacity direction. No existing process is modified. The older
2026-10-13 and S4-A results remain historical; they are not overwritten.
The retired gated Llama-2/ECHR multi-GPU case is not a prerequisite for the
approved DistilGPT2 standard. Original §8.1 metadata input gaps remain separate.


## VAL-R02 — Formal FastChat/DeepSeek judge replay

**Current result — `6afe8f4`:** the
[2026-10-26 replay](2026-10-26-validation-completion/README.md) completes two
newly authorized requests without retry, full source/JSONL snapshot fidelity,
154 independent export comparisons and 214 terminal comparisons. Scores 7/8
are observations, not gold. The peak-tariff estimate is CNY 0.002740, not an
account invoice. The seven-change HIGH-cap pair, empty self-diff and HIGH gate
exit 1 pass; unrelated upstream findings remain visible.

**Historical result — `75d1b0`:** the product repair, final quality and fresh
five-project CPU acceptance PASS. Both formal provider requests, complete
captures and semantic-pair acceptance PASS under a newly approved CNY 3 budget.
The original parser returns observed scores 7/7, which are observations rather
than gold. Both attempts return valid usage with no retry; the combined
peak-tariff estimate is CNY 0.002836, not a verified account invoice. The direct
cap leaf and config hash are HIGH, the clean commit is MEDIUM, all four NONE
changes are explained, self-diff is empty, and `--fail-on HIGH` exits 1.
Complete audit findings/profiles agree and all six judge rules pass in each run.
The [new report](2026-10-19-judge-snapshot-fix/README.md) records this real pair;
the preceding CPU source-fidelity checks alone are not formal provider evidence.

**Historical result — `750270b`:** one genuine A judgment completes and the
original parser returns a finite score of 7. All four bindings, usage accounting and six judge
rules are verified; the complete source-snapshot gate fails. The retained
[failed run and CPU diagnoses](2026-10-19-resource-completion/DYNAMIC-PARTIAL.md)
do not become a passing formal pair. B is NOT_RUN, not an exhausted-budget claim.
The estimated peak-tariff charge is CNY 0.001394, not a verified account invoice.

**Resources:** this replay has the exact approved input bundle, an isolated
compatible environment, usable DeepSeek credentials and a newly approved CNY 3
ceiling. Each later replay still requires its own resource and budget checks.
This judge-only scenario does not require a GPU. Recover and verify the four
Variant A input hashes in
[`val.md` §8.4](../../val.md#84-approved-deepseekfastchat-supplementary-judge-2026-09-27)
before sending anything. Public question/rubric files alone are insufficient.

**Future replays:** use the §8.4 entry and transport with public MT-Bench question 82,
the fixed synthetic answer and original `single-v1` rubric. A/B changes only
the declared judge cap and its config binding, 256 → 384. Confirm the selected
model is available through authenticated `/models`; verify the provider tariff
and budget reservation before execution. Preserve the documented limits of
two completion attempts, no retries, input size and request deadline. If the
bundle, provider or budget cannot satisfy that scenario, retain BLOCKED and
propose a separate reviewed scenario change.

**Closure checks — candidate `75d1b0`:**

- [x] Both real judgments finish successfully; the original parser returns a
  finite score from 1 to 10. Exact scores or identical generated text are not gold.
- [x] Sent rubric/question/answer, consumed cap, provider identity, usage,
  bindings, package versions, input/output hashes and snapshots match §8.4.
- [x] Credentials appear only as presence metadata; persisted artifacts contain
  no secrets, absolute host paths or machine identity.
- [x] All selected judge checks and capture consistency meet the independent
  expectations; unrelated upstream findings remain visible.
- [x] A new pair after R08-A uses §8.4.1: direct cap HIGH, config hash HIGH and
  clean commit MEDIUM; retain the historical §8.4 cap MEDIUM evidence unchanged.
  Remaining changes are explained, self-diff is empty, and `--fail-on HIGH`
  exits 1. Preserve the historical nested-severity gap as historical evidence;
  the current direct judge-param policy follows §8.4.1.
- [x] The sanitized dated report covers the M5/M6 pair and M7 API-judge gate.

The already-passed real `discover` request remains separate evidence and is not
a substitute for this formal judge pair. The earlier CNY 3 execution and formal
promotion are historical records in §§8.4–8.5.

## VAL-R03 — HF small-file resolution; public-model replacement

**Current contract:** follow `val.md §8.1.2` and the
[public-model input/report](metadata-public-model-2026-10-27/README.md).
The success criteria are exact public model/tokenizer/config identity,
independently established template absence, two matching online locks,
freshness, complete audit/diagnostic comparison and clean persistence.
No HF credential, weight, data-content download or GPU is required.

**Current result: PASS** at `00c2392`, with unchanged product bytes from `6afe8f4`.
The new case completes anonymous model/tokenizer/config resolution, independently
verified config hash and template absence, two matching online locks and complete
five-project lock/audit/diagnostic comparisons. Exact commands, input/source hashes,
elapsed times and output references are in the linked bundle's checks.json.

**Retired contract — SUPERSEDED_NOT_PASSED:** all Llama-2 access conditions and
unchecked items below document the historical gate, not requirements to resume
current development. Its author-approval branch is no longer mandatory under
the maintainer's explicit model-change instruction. The old 403 did not pass.

**2026-10-19 preflight:** the supplied token authenticates successfully through
the existing HTTP proxy, while official pinned `config.json` and
`tokenizer_config.json` requests both return 403. Direct official-HF connectivity
also fails without that transport. No token value, model weight or private data
is persisted. Successful authorized-file resolution remains unverified.

**2026-10-26 preflight:** identity again returns 200 and both pinned small files
return 403; no weights or identity-response body are persisted. Five original
§8.1 manifests are still absent, and the maintainer has confirmed no additional
copy is currently available. This remains BLOCKED, independently of the new
anonymous supplementary H2 and native/judge/discover successes.

**Resources:** model-author approval for `meta-llama/Llama-2-7b-hf` and a locally
provisioned token with permission to read that repository. HF login alone does
not grant model-author access. This check needs neither GPU nor paid inference.

**Resume:** use Project C at the §2 pin and its new formal manifest in
[`val.md` §8.1.1](../../val.md#811-current-formal-metadata-inputs-2026-10-27).
Recovering the old manifest is no longer required; verify the new catalog hash.
First establish independently reviewed successful-access expectations from
official metadata and direct file hashes at the recorded revision. Limit file
reads to the approved small config/tokenizer/template files (2 MiB each);
do not download weights or dataset contents for this check. Run the existing
lock/check/audit sequence with the token supplied only to the metadata process.

**Close only when:**

- [ ] Model-author approval and authenticated access to the selected files are
  confirmed; every resolved revision/hash/provenance matches the independent
  successful-access expectations.
- [ ] Two online locks are equal after the permitted timestamp exclusions;
  freshness and relevant consistency findings match the new case.
- [ ] The token occurs zero times in stdout, stderr, locks, reports and evidence.
- [ ] A sanitized report distinguishes successful access from denial handling.
  The existing anonymous 401/authenticated 403 case remains historical evidence;
  any formal gold update is a dedicated reviewed change under val.md §9.

Correct handling of the observed 403 already passed. This item tracks the
remaining successful-access branch; another 403 leaves it BLOCKED.

## Resumption and evidence

Complete any independently executable item without waiting for all three groups.
Before resuming, read the current specification and val.md, confirm the resource
provisioning, choose and record the ReproLLM commit/version under test, and run
the quality gate and five-project Gate A. Use disposable clones for mutating
commands; preserve the original checkouts and independent gold.

For each completed item, add a dated report under `docs/dogfooding/` containing
commands, target SHAs, input hashes, expected/actual exits, elapsed times, full
finding/diff deltas and reviewed evidence. Keep credentials, host connection
details, weights and raw runtime artifacts outside the repository. Link the
sanitized report here, date the checkbox update, and distinguish a later-version
pass from a replay of 0.6.1. Mark a group complete only after all its items pass.
If a resource is still missing, record BLOCKED; if an actual acceptance check
fails, record FAIL and keep the group unclosed. Never substitute historical
success or current tool output for independent gold.

The original deferral is in [`val.md` §8.7](../../val.md#87-patch-061-resource-execution-deferral-2026-10-01)
and the [0.6.1 patch report](2026-10-01-patch-0.6.1.md#packaging-and-outstanding-resources).

## Recording-session verification — 2026-10-01

This documentation follow-up records the M4–M7 resource blockers from the
M12-T01 patch report. It changes no product code, schema, fixture, snapshot, pin
or gold. Independent review confirmed the resumption criteria and references.

The local quality gate passed: `.venv/bin/pytest -q --cov=reprollm
--cov-report=term --cov-fail-under=85 --tb=short` reported 1,437 passed, three
skipped and two slow tests deselected in 67.00 s; coverage was 92.75%, with all
24 redaction branches covered. Ruff check/format, mypy, the nine-schema freshness
comparison and all four generated-document checks exited 0. Local links and
blocked/unchecked statuses were checked separately.

After that gate, each original §2 checkout was verified clean at its exact pin
and origin before and after the following command:

```console
.venv/bin/reprollm -v audit <pinned-checkout> --level 0 --format json --fail-on never
```

| Target (SHA inherited from val.md §2) | Exit | Elapsed | Full baseline delta |
|---|---|---|---|
| lm-evaluation-harness | 0 | 6.521 s | None |
| FastChat | 0 | 0.554 s | None |
| LlamaFactory | 0 | 0.785 s | None |
| HarmBench | 0 | 0.572 s | None |
| llm-dp-finetune | 0 | 0.273 s | None |

Complete JSON reports matched the confirmed 0.6.1 baseline after excluding only
`generated_at`; full diagnostics matched byte-for-byte. All 26 subprocess
records exited 0 (8.993 s total). Sanitized raw records are kept in the external
`<tracking-session-evidence>` directory. This docs-only session ran no Gate B
resource scenario and leaves all three groups BLOCKED.
