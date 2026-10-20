# A01-B — complete executable prior-product validation

Date: 2026-10-20. Product candidate: `948d16423023027fff77322b8a872acaba306691`.
This work precedes the accepted R06-B P-B implementation. Every result below
retains that source identity; none is relabelled as a native execution of the
later dependency-policy change. Product version is unreleased 0.7.0.

The maintainer requested completion of already-delivered validation before
further development. All executable prior-product checks now pass. Five
original metadata manifests remain missing and authorized Llama 2 small-file
access still returns 403. These external requirements remain BLOCKED.
There is no release, tag or publication.

## Completed checks and exact scope

| Layer | New result at `948d164` | Evidence |
|---|---|---|
| Final local quality | 24 checks PASS; 3,004 tests, 2 slow deselected; 345 security tests; coverage 94.02%; redaction 59/59 lines and 24/24 branches | [quality package](prevalidation/README.md) |
| Fresh five-project Gate A | All pins/origins/clean states; 10 complete JSON comparisons, 32 checks, 51 commands; no gold delta | [prevalidation sources](prevalidation/source-index.json) |
| Built and installed wheel | One wheel SHA `3d1b83b4488064664e776ddaae495776cd12847e9a0d8690d00e7263d877ece3`; both provisioned framework environments verify all 143 payload files; other installed distributions unchanged | [installation evidence](prevalidation/README.md) |
| Linux H2 supplementary metadata | Five targets × offline / online 1 / online 2; 639 checks; 15 complete reports and 15 complete locks compared with qualified independent historical evidence | [H2 package](metadata/README.md) |
| Real native GPU runtime | 10 original children, five full A/B pairs, 20 available default exports; 1,291 independent export comparisons; 244 terminal checks | [native package](native/README.md) |
| Initialized discover | Five offline previews; one newly approved live input case; actual provider response and reviewed candidate acceptance PASS | [discover package](discover/README.md) |
| Original metadata recovery | 45/50 exact input slots available; five original §8.1 manifests still absent | [input recheck](prevalidation/original-metadata-input-recheck.json) |
| Gated HF success | Authentication 200, both specified small files 403 | [access preflight](prevalidation/hf-access-preflight.json) |

The original full quality run takes 584.105309 seconds wall time; pytest itself
reports 449.03 seconds. Fresh Gate A takes 87.790025 seconds wall time
(82.992120 seconds summed product commands). H2 takes 198.642184 seconds wall
time (182.971293 seconds summed product commands). These are separate layer
measurements, not an added total session duration. The environment was synced
separately with the locked development dependencies before quality execution;
the runner's `environment_synced: false` describes its own actions only.

The wheel is byte-identical to the earlier accepted `75d1b0` judge-repair wheel.
Its new build/installation binding is recorded independently; the formal paid
judge A/B remains the earlier successful execution and is not sent again.
The baseline five-project Gate A compares complete findings, profiles,
diagnostics, paths, detection, hints and dependency/source facts. Counts alone
are not the oracle.

## Native acceptance

All jobs use provisioned caches and isolated framework environments, GPU0,
serial execution and the device lease. Launch decisions follow the maintainer's
continuing actual-capacity direction; old artificial idle/utilization/numeric
thresholds are not reinstated. Other tasks and GPU1 are not modified.

| Project | Actual A/B change | Required native evidence |
|---|---|---|
| lm-evaluation-harness | generation cap 32 → 48, HIGH | 100 GSM8K documents; actual vLLM consumption and independent output checks |
| FastChat | generation cap 32 → 48, HIGH | Original two-turn question, one choice, actual calls and complete capture |
| LlamaFactory | learning rate 0.0001 → 0.0002, HIGH | Two actual LoRA optimizer updates per variant, finite losses and actual LR |
| HarmBench | target cap 16 → 24, HIGH | Target/classifier stages, actual constructor/log arguments and classifications |
| llm-dp-finetune | epsilon 8 → 4, MEDIUM | Two DP steps; clipping/noise/accountant/weights and larger B noise multiplier |

Each semantic pair contains exactly seven explained changes, including the
intended leaf, config hash, clean commit and four NONE metadata changes.
Self-diffs are empty and threshold exits are checked. DP's epsilon leaf is
independently required to be MEDIUM; an unrelated HIGH config hash cannot mask
a wrong leaf severity. Complete capture, pre/post input hashes, consumption,
outputs and available export projections pass.

The package binds 170 original command receipts, 340 retained command streams
and all 84 files in the ten original run trees. Private runtime logs and argv
remain hash-only; safe typed documents, snapshots and projections are retained.
Generated HarmBench text is not published.

Observer defects and their failed attempts remain visible. The division/path
oracle was qualified on the same original files. A stricter operator-mask
postcheck then scanned all 84 original run files successfully. HarmBench's
initial constructor observer did not establish all actual arguments; a separate
CPU observer verifies four original stage logs instead. GPU0 identity is based
on launch environment/guards and the CUDA backend, not an in-engine physical
GPU query. The owner briefly paused its own top-level driver before HarmBench
while the active child completed normally, then resumed it. No native child,
model request or product command is rerun to obtain these observer corrections.

## Real discover acceptance and spending

The maintainer explicitly accepted the current initialized input hashes and a
new CNY 4 ceiling. Three hashes differ from the historical initialized case;
this is **DISCOVER-INIT-948D-20261020**, not an exact replay of those historical
bytes. Historical input hashes and gold remain unchanged. Project C sends
31,337 user-message characters, fixed public source and generated intent.
The final transport allows one actual POST, no retry, a 120-second stage limit
and a 400-second total limit using the production client and `deepseek-flash`.

One real POST returns HTTP 200, finish `stop`, CLI exit 0 in 42.330705 seconds.
Usage is 8,762 prompt and 10,811 completion tokens (19,573 total). The peak-tariff
estimate is CNY 0.104012, not an account invoice. Reasoning content is not
persisted; its reported token count is retained. No second provider request is
made. A preceding isolated-controller import failure occurs before credentials
or POST; it is preserved as setup failure, not a second paid attempt.

All 21 final candidates are reviewed: eight source-supported without a binding
restriction; nine concept-supported with unverified proposed bindings; three
requiring source/binding correction; one with unusable persisted evidence.
Twenty IDs can be independently recomputed. The unused low-confidence item
whose evidence was removed lacks its original first path, so its ID cannot be
recomputed from the final document; this limitation is retained.

The selected `top_p` candidate `c-8914b9` is supported by fixed Git bytes, the
actual sent source block and AST line 24, with literal default float 1.0. It has
no proposed binding. Acceptance preserves its source identity, produces the
missing-value WARNING, changes to PASS after an explicit operator declaration,
rejects duplicate acceptance with exit 2 without changing rules bytes, and
preserves all other complete findings. Repeated audit differs only in its root
generation timestamp. The declared value is validation intent, not a claim of
runtime consumption. The original candidate document remains unchanged.

An overly narrow acceptance helper initially allowed only two privacy fields;
its reviewed successor validates the same response, one positive and fourteen
negative cases. Frozen send helpers and failed attempts remain preserved. Human
acceptance stdout contains a private scratch path and is retained hash-only.
Two public-source absolute-path literals are qualified against the fixed Git
source; they are not machine identity leaks. Exact configured HF/DeepSeek
credential scanning checks 302 bound files with zero hits; final delivery bytes
are scanned separately before pushing.

## Open requirements and continuation

VAL-R01 is PASS for `948d164`'s available native/H2 matrix. H2 remains §8.2
supplementary metadata; it does not replace the five original §8.1 manifests or
establish successful authenticated gated access. VAL-R02 remains PASS at
`75d1b0`; the historical `750270b` A FAIL / B NOT_RUN is unchanged. VAL-R03
remains BLOCKED. Recover the exact original manifests from their custodian and
obtain the model author's permitted small-file access before claiming those
requirements pass. The original candidate-specific receipts remain historical.

The independent R06-B A decision is now accepted and its P-B implementation is
the next session slice. It requires its own final quality gate, fresh five-pin
Gate A and affected non-resource consumers. This resource report does not
substitute for those checks, and the static policy task does not automatically
repeat GPU, paid judge/discover or authenticated HF execution.

All shareable packages retain source and retained-byte hashes plus explicit
sharing transformations. Private paths, machine identity and credentials are
excluded; originals remain private where required. Reports preserve failed
observer/setup attempts and do not regenerate gold. Final pushed-HEAD CI is
recorded with the R06-B session closure; historical CI is not relabelled.
