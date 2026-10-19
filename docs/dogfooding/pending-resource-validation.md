# Pending resource validation

Recorded: 2026-10-01. Owner: ReproLLM maintainers.

These are the three unfinished validation groups reported after the **0.6.1**
patch release (`9ed6d9964d39281cf62cca667b0457c90fb352c1`). They track fresh
release coverage, not missing feature implementations. The maintainer directed
the session to defer unavailable resources and complete the executable checks.

[`val.md`](../../val.md) remains authoritative for repository pins, inputs,
commands, independent gold and resource guards. This checklist does not change
that baseline. Earlier successful executions remain historical evidence;
unchecked items below are **blocked**, not fresh passes for 0.6.1.

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

The formal DeepSeek A request succeeds, but capture fails two non-secret source
snapshot requirements: `common.py` is omitted and four unused multi-turn rubric
rows are changed. Both have independent CPU reproducers; no product fix or
second completion is performed. VAL-R02 is **FAIL**, rather than missing an
input bundle or budget. HF authentication succeeds, but both selected restricted
small files return 403; original §8.1 manifests are still missing. VAL-R03 remains
**BLOCKED**. This is not release readiness or a retrospective pass for 0.6.1.

| Tracking ID | Outstanding coverage | Current cause | Status |
|---|---|---|---|
| VAL-R01 | Linux H2; five bounded native inference/training A/B pairs; capture/consumption/diff/export | Current candidate passes complete native matrix, including all additional differences and self-diffs | PASS — 2026-10-19, `750270b` |
| VAL-R02 | Formal FastChat/DeepSeek judge pair and M7 API-judge acceptance | Actual A capture fails two snapshot-fidelity cases; B NOT_RUN after the known failure. Exact inputs, usable credentials and a fresh CNY 3 budget were provisioned | FAIL — product capture defects |
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

**Current closure — 2026-10-19 candidate `750270b`:**

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

**Current result:** one genuine A judgment completes and the original parser
returns a finite score of 7. All four bindings, usage accounting and six judge
rules are verified; the complete source-snapshot gate fails. The retained
[failed run and CPU diagnoses](2026-10-19-resource-completion/DYNAMIC-PARTIAL.md)
do not become a passing formal pair. B is NOT_RUN, not an exhausted-budget claim.
The estimated peak-tariff charge is CNY 0.001394, not a verified account invoice.

**Resources for a repaired-candidate replay:** the exact approved input bundle,
an isolated compatible environment, usable DeepSeek credentials and a bounded
execution budget. This judge-only scenario does not require a GPU. Recover and
verify the four Variant A input hashes in [`val.md` §8.4](../../val.md#84-approved-deepseekfastchat-supplementary-judge-2026-09-27)
before sending anything. Public question/rubric files alone are insufficient.

**Resume:** use the §8.4 entry and transport with public MT-Bench question 82,
the fixed synthetic answer and original `single-v1` rubric. A/B changes only
the declared judge cap and its config binding, 256 → 384. Confirm the selected
model is available through authenticated `/models`; verify the provider tariff
and budget reservation before execution. Preserve the documented limits of
two completion attempts, no retries, input size and request deadline. If the
bundle, provider or budget cannot satisfy that scenario, retain BLOCKED and
propose a separate reviewed scenario change.

**Close only when:**

- [ ] Both real judgments finish successfully; the original parser returns a
  finite score from 1 to 10. Exact scores or identical generated text are not gold.
- [ ] Sent rubric/question/answer, consumed cap, provider identity, usage,
  bindings, package versions, input/output hashes and snapshots match §8.4.
- [ ] Credentials appear only as presence metadata; persisted artifacts contain
  no secrets, absolute host paths or machine identity.
- [ ] All selected judge checks and capture consistency meet the independent
  expectations; unrelated upstream findings remain visible.
- [ ] A new pair after R08-A uses §8.4.1: direct cap HIGH, config hash HIGH and
  clean commit MEDIUM; retain the historical §8.4 cap MEDIUM evidence unchanged.
  Remaining changes are explained, self-diff is empty, and `--fail-on HIGH`
  exits 1. Preserve the historical nested-severity gap as historical evidence;
  the current direct judge-param policy follows §8.4.1.
- [ ] The sanitized dated report covers the M5/M6 pair and M7 API-judge gate.

The already-passed real `discover` request is separate evidence and does not
close this judge replay. The earlier CNY 3 execution and formal promotion are
historical records in §§8.4–8.5.

## VAL-R03 — Successful HF gated-file resolution

**2026-10-19 preflight:** the supplied token authenticates successfully through
the existing HTTP proxy, while official pinned `config.json` and
`tokenizer_config.json` requests both return 403. Direct official-HF connectivity
also fails without that transport. No token value, model weight or private data
is persisted. Successful authorized-file resolution remains unverified.

**Resources:** model-author approval for `meta-llama/Llama-2-7b-hf` and a locally
provisioned token with permission to read that repository. HF login alone does
not grant model-author access. This check needs neither GPU nor paid inference.

**Resume:** use Project C at the §2 pin and the reviewed metadata inputs in
[`val.md` §8.1](../../val.md#81-m4-metadata-resolution-scenarios-reviewed-2026-09-19).
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
