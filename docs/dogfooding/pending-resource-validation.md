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

| Tracking ID | Outstanding coverage | Blocker | Status |
|---|---|---|---|
| VAL-R01 | Linux M4-H2; five real GPU inference/training scenarios and their M6 pairs | S4-A fixes observed source fidelity and accepts fresh lm-eval A/B; the other four native projects still need current-candidate acceptance | BLOCKED — remaining native matrix |
| VAL-R02 | Formal FastChat/DeepSeek judge pair, including the M7 API-judge path | Bundle historically recovered remotely; exact local inputs remain inaccessible. Current provider/tariff/budget and bounded paid replay are not provisioned for this session | BLOCKED |
| VAL-R03 | Successful authenticated HF gated-file resolution | Original Project C metadata manifest is missing; model-author-approved file access and a permitted token are not provisioned for this session | BLOCKED |

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

**Close only when:**

- [x] Linux H2 (2026-10-13 candidate): offline/two-online/check/audit runs complete with the expected
  revisions, file hashes, normalized lock equality and freshness results.
- [x] lm-evaluation-harness (2026-10-15 S4-A candidate): real bounded inference,
  complete A/B capture, source fidelity, independent consumption/output checks,
  required semantic leaf/severity and selected-run exports match §8.3.
- [ ] FastChat: real local answer generation and its A/B capture/diff pass.
- [x] LlamaFactory (2026-10-13 candidate): real bounded LoRA updates, finite loss and its A/B
  capture/diff pass. Its additional RPC scratch-variable MEDIUM delta is
  independently explained; complete A/B environment byte identity is not claimed.
- [ ] HarmBench: real target/classifier execution and its A/B capture/diff pass.
- [ ] llm-dp-finetune: real DistilGPT2 privacy fine-tuning and its A/B
  capture/diff pass under the formal standard in §8.5.
- [ ] Every pair passes binding, package, input/output hash, snapshot-fidelity,
  privacy and self-diff checks; all additional drift is explained. Preserve
  the prescribed MEDIUM DP leaf even when the config-file hash is HIGH.
- [ ] Available captured states pass the applicable M7 export checks.

The 2026-10-13 report records ten successful native children, independent output
checks and all 36 semantic changes, with the original snapshot fidelity failures
preserved. S4-A fixes the observed defects and reaccepts the formal lm-eval pair.
Remaining project items need fresh native capture and consumer verification;
the ten-file CPU fidelity regression alone cannot promote their older runs.
LlamaFactory and Linux H2 checkmarks above remain explicitly dated evidence,
not complete release coverage for the new candidate.

Standard-library capture probes do not close these native execution items.
The retired gated Llama-2 multi-GPU DP scenario remains additional coverage,
not a new prerequisite for the approved DistilGPT2 standard.

## VAL-R02 — Formal FastChat/DeepSeek judge replay

**Resources:** the approved input bundle from the remote evidence store, an
isolated compatible environment, usable DeepSeek credentials and a provisioned
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
- [ ] Pair diff contains the prescribed nested cap MEDIUM, config hash HIGH and
  clean commit MEDIUM changes; remaining changes are explained, self-diff is
  empty, and `--fail-on HIGH` exits 1. Retain the known nested-severity gap.
- [ ] The sanitized dated report covers the M5/M6 pair and M7 API-judge gate.

The already-passed real `discover` request is separate evidence and does not
close this judge replay. The earlier CNY 3 execution and formal promotion are
historical records in §§8.4–8.5.

## VAL-R03 — Successful HF gated-file resolution

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
If a resource is still missing or execution fails, record the reason and retain
BLOCKED rather than substitute historical success or current tool output for gold.

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
