# R07-C profile-absence P-A observations

Status: **conditional design experiment PASS; not P-B acceptance**. Candidate `bb98e67c6e108822c62842d738f42af2eda871e4`; production source was never edited. The exact proposed rule was injected only into a fresh worker process registry.

16 API inputs × two policies and four isolated CLI inputs × two policies completed: 40 product workers and 20 complete strict JSON comparisons, with no ignored fields. The separate first CLI helper failed before command entry; its original streams and correction remain in qualification. The 32 completed API workers were preserved, and only eight CLI workers were run after the launcher correction.

| API input | Baseline target statuses | Conditional target statuses |
|---|---|---|
| cap-hidden | fail | skipped |
| full-hidden | pass | pass |
| mixed-positive | fail, fail | skipped, fail |
| complete-absent | fail | fail |
| zero-candidates | fail | fail |
| syntax-gap | fail | skipped |
| binary-gap | fail | skipped |
| oversize-gap | fail | skipped |
| unreadable-gap | fail | skipped |
| dependency-witness | skipped | skipped |
| readme-witness | skipped | skipped |
| multi-absence | fail, fail | skipped, skipped |
| custom-detection-witness | skipped | skipped |
| unknown-marker | fail | skipped |
| invalid-counts | fail | skipped |
| positive-unknown | fail | fail |

| Isolated CLI input | Baseline exit | Conditional exit |
|---|---:|---:|
| cli-warning-cap | 1 | 0 |
| cli-critical-cap | 1 | 0 |
| cli-suppressed-cap | 0 | 0 |
| cli-warning-complete | 1 | 1 |

The CLI core/probe profiles are synthetic user-owned loader inputs selecting only the target rule. WARNING/CRITICAL thresholds therefore prove the target effect without unrelated failures. Suppression and complete-view controls retain their prior behavior. All default scan stderr is byte-identical between policies.

The mixed case retains the high-confidence positive `finetuning` mismatch while only the missing declared `inference` conclusion becomes SKIPPED. Existing empty-result skips and complete-view absence findings remain unchanged. This does not certify dependency/listing/framework completeness or real experiment membership.

[Input recipes](input-recipes.json) reconstruct every synthetic input byte without duplicate large files. [Source guard](source-guard-summary.json) binds all 8,602 original tracked Git blobs at the observation boundaries. [Timings](timing-summary.json) distinguish worker/body/wall measurements. [Source index](source-index.json) records exact bytes, hash-only external sources and the explicitly projected failure stderr. No network, GPU, provider or native child was used.
