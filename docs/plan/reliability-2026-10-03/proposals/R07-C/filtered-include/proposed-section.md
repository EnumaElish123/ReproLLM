### 12.3.15 Reached requirements include targets excluded from analysis (R07-C D-I)

For `env.llm_critical_deps_pinned` only, retain a separate internal
`Declarations.excluded_requirement_targets: tuple[str, ...] = ()` after the
existing fields. Legacy/manual values default to empty. This is not a persisted
schema field and does not extend `DeclarationReadIssue` or `_RequirementFile`.

In the existing `_RequirementsGraph._node` branch where the existing
`scanner.is_analysis_candidate(source)` call returns False, add that logical
source to a private graph-local set. Do not add another eligibility check or
body read. After every existing requirements root has completed expansion,
collect exactly the non-None normalized targets of `_RequirementInclude` events
on captured readable parent nodes whose targets belong to that private set.
Deduplicate and lexicographically sort this final intersection into the new tuple.
A rejected root with no qualifying incoming include is not itself sufficient.
Retain the same cached nodes and expansion; do not retry after filesystem changes.

The fact means an existing, actually reached candidate check rejected the
logical target. It does not prove existence, readable contents, a particular
filter reason, any dependency or any exact pin. A missing path beneath a skipped
directory can qualify. Existing lexical exclusions, virtualenv-marker checks,
internal aliases to excluded paths and rejection after an existing marker-check
failure may qualify; do not classify their causes from prose or add new probes.
Targets may use any extension supported by the existing include path grammar;
only discovered roots require their existing requirements filename predicate.

A depth-frontier target that was never reached does not enter this set; it keeps
only the independent final-node predicate in §12.3.8. Candidate-eligible targets
whose actual body read returns None keep §12.3.6. Missing/binary/oversize or unsafe
physical aliases do not become this fact merely because their nodes are unreadable.
Unsupported includes without a normalized target do not qualify. Listing omission
alone is not a rejection: an explicit supported include may still reach its target.
Never derive this fact from `readable=False`, incomplete/nonexact closures,
diagnostics, file presence or a new scan of all candidates.

Preserve all declarations and their order, source, line, specifier and exact
version; roots, edges, nodes, closure qualification, lock sets and associations,
manifest/lock presence, barriers, diagnostics, budgets and every existing read.
Grant no use or credit, and do not extend grammar, candidate selection, scanner,
physical read boundaries or the requirements-as-lock contract.

Keep canonical known package use, applicability and iteration. Exact/qualified
credit wins first, then D-F/D-S, D-L, D-M, and D-G. Only for each remaining
used-but-unpinned FAIL/WARNING does a nonempty new tuple produce SKIPPED/INFO.
Preserve every earlier finding in full without appending these target paths.
Keep the original first declaration/import evidence, then one kind=file evidence
per distinct sorted target, without a line, value, raw include or filter reason.
For the package display name `P`, use exactly:

- Message: `P is used; a supported requirements include target was excluded from static analysis, so missing pin evidence is not established`
- Target evidence note: `P include target excluded from static analysis`
- Fix hint: `Review P declarations and excluded requirements include targets; make intended dependency sources eligible for static analysis before deciding that exact pin evidence is absent.`

This influence is repository-wide under §12.2's existential exact policy. An
unrelated or nonexistent excluded target can conservatively skip any remaining
currently used, uncredited critical package; it need not contain a hidden pin.
Python coverage does not control this branch. Preserve no-known-use applicability,
all-credited empty-result behavior and the primary-Python empty-result veto.
Do not add an aggregate result, a per-package PASS or unknown package use.

FAIL-only overrides, suppression, sorting and thresholds retain their contracts.
An isolated WARNING or promoted CRITICAL gate may change from exit 1 to 0;
independent qualifying findings still fail. Default text may show PASS with skips,
and default export omits a former notable warning; complete JSON retains SKIP.
Captured dependency/profile/init inventories and all other rule results remain
unchanged. No renderer, engine, redaction, persisted schema, dependency, version,
historical result, five-project gold or release change is included.

D-I is a local proposal label, not an architecture decision. Other include or
line grammar, omitted roots/use, listing/README/config/framework completeness,
resource limits and broader sufficient certificates remain OPEN R07-C work.

