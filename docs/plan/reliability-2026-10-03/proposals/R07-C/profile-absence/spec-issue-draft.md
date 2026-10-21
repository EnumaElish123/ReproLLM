# [spec] R07-C declared-profile absence under incomplete Python analysis

Status: DRAFT_ONLY_NOT_POSTED. Proposed label: spec.

Current §12.3.1 deliberately preserves nonempty absence findings after the earlier
accepted empty-result policy. A declared profile whose only signal is outside the
candidate budget can therefore receive an absence-derived INFO FAIL; adding the
omitted signal can remove that finding. A user severity override can make the
bounded absence trigger CI.

Propose only the branch-specific policy in [the concrete proposal](R07-C_profile_absence.md):
per missing declared non-core profile, use existing SKIPPED/INFO when the existing
typed primary-Python assessment is incomplete/unavailable. Preserve the positive
high/shipped undeclared branch, full-view bounded contract and empty-result policy.
The exact [rule](implementation-proposed.patch) and [specification](spec-proposed.patch)
patches are unapplied. No engine, registry, redaction or schema edit is proposed.

The decision must acknowledge the override-derived exit 1→0 compatibility change
and conservative skipping even for profiles without AST signals. Full R07-C,
listing/dependency/framework completeness and sufficient certificates remain open.
Historical reports and five-project gold are preserved. Complete counterexamples,
prospective zero deltas and acceptance design are indexed by this packet.

No external issue, invitation or application was submitted by preparing this draft.
The maintainer can decide this concrete policy locally; P-B follows only the
specific accepted range and retains tests-first/final-quality/consumer acceptance.
