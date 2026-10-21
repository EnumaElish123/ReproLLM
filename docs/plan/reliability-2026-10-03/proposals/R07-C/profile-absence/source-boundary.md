# R07-C declared-profile absence — exact draft source boundary

Status: PROPOSED_NOT_APPLIED. Base `bb98e67c6e108822c62842d738f42af2eda871e4`.
These are inert patch files and source text for a concrete policy decision;
no repository product, specification, tests or gold have been changed by this preparation.

The implementation patch changes only `src/reprollm/rules/exec_.py`: add the existing
FindingStatus import and an explicit per-profile SKIPPED/INFO branch immediately
before the old declared-but-undetected FAIL construction. The branch is entered
only when the existing typed primary-Python coverage method returns non-None.
Its reason text is neither parsed nor copied. Known gaps and unavailable coverage
share this exact message template:

```text
declared profile {profile!r} has no detection evidence in the analysed inputs; Python candidate analysis is incomplete or unavailable, so absence is not established
```

The one field evidence item uses `experiment.profiles` and note
`{profile} declared; detection absence unverified`. Remaining Finding metadata
retains the rule aliases/category, current level/fix hint and current defaults.
No finding schema, counts field, rule ID or default severity is added or changed.

Each absent declared non-core profile is considered in existing sorted order;
existing duplicate behavior is retained. `continue` skips only that profile's
old absence FAIL. The separate sorted positive high-confidence/shipped/not-effective
branch still executes. Existing engine sorting and nonempty-list handling remain.
No new rule-wide coverage outcome is appended to a nonempty list. The old empty-result
PASS veto and missing-manifest skip remain exact.

With consistent observed parsed=candidate, the old absence FAIL/message/evidence
remain; that is a retained bounded contract, not a global negative certificate.
Detected profiles never enter this new branch, including non-Python witnesses.
Unobserved or inconsistent counts use the generic new SKIP exactly as known gaps do.

The engine already applies profile severity overrides only to FAIL. A new SKIP
therefore stays INFO/default even if the rule has a WARNING/CRITICAL override.
An isolated old override-derived failure can stop producing exit 1; this is an
explicit compatibility cost, not a change to CLI thresholds or FAIL-only counting.
Existing suppression still applies to all statuses and produces SUPPRESSED/INFO,
with the same supplied reason and appended ignore evidence.

No engine, registry, pyscan, schema, State, profile, dependency or upstream reader
code is changed. The earlier D-41 engine approval does not approve this new policy;
this concrete normative specification patch must be accepted before P-B. Dependency
absence, listing/README/config/framework completeness and sufficient certificates
remain OPEN; whole R07-C is not closed. Historical reports/gold remain original.

`source-boundary.json` contains exact source, patch and proposed-target hashes.
`draft-static-qualification.json` records AST/reconstruction/read-only apply checks
and the earlier changelog-anchor construction assertion. No product, tests, provider,
GPU, credentials or network was used for this preparation.
