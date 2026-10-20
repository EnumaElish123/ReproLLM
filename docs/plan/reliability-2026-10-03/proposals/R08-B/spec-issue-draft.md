# spec(diff): classify four source-backed privacy/training parameter paths

Local draft only; not posted. Intended label: spec. Issue #9 remains the separate
judge-parameter discussion; this draft does not duplicate that judge policy.

Current §18 correctly implements single-segment first-match matching, leaving
four actual DP manifest leaves at MEDIUM: privacy.mechanism.params.target_epsilon,
.target_delta, .max_grad_norm and training.params.num_train_epochs. The exact
source mappings and caveats are in R08-B_exact_parameter_risk.md.

Proposed A4 adds those four exact HIGH rows only, preserves user profile matching
and historical MEDIUM reports, and adds prospective val §8.3.1. New target-only
comparisons can make explicit --fail-on HIGH exit1. This classifies recorded
experimental-value drift, without certifying DP, child consumption or causal
output changes. Other default paths, aliases, recursive wildcards and other fields remain
outside the amendment. There is no schema or D-41-sensitive-module change.

Acceptance: all four paths changed/added/removed, exact/nested/alias controls,
effective LOW/NONE and inheritance, isolated CLI thresholds without another
HIGH, filtering/full summary, deterministic JSON and self-diff, complete five
retained-pair comparisons, then the applicable final quality and fresh five
project gates after concrete acceptance. No release or paid request is sought.
