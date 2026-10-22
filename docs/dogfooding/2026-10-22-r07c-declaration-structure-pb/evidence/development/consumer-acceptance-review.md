# R07-C D-M-S consumer and acceptance review

Reviewed the accepted specification patch against the current implementation and regression inputs.
This is an independent source/test review, not a substitute for the final quality or five-project gate.

## Implementation boundary

- `DeclarationReadIssue` adds only `invalid_structure`.
- Pyproject checks default only absent keys. False, zero, empty strings, and wrong-type empty
  containers cannot become absence. All checked nested containers have already passed their
  parent type check. A first error suffices for the specified single file-level issue.
- Environment root None retains compatibility, while a present null dependencies/pip value fails.
  Unknown mapping keys and all string grammar are outside the new checks.
- Pipfile uses its already existing wrong-section test, recording the additional typed issue.
- New checks precede legacy extraction but do not change extraction, file reads, qualification,
  barriers, diagnostics, lock inventory, or partial credit. No new consumer branch is introduced.
- `rules/env.py`, engine, redaction, and schemas have no diff. Existing credit and D-F/D-S > D-L >
  D-M order therefore remains mechanically unchanged and receives explicit consumer regression coverage.

## Accepted matrix mapping

| Cases | Concrete regression coverage |
| --- | --- |
| A01–A04 | Core raw wrong-mapping/container parametrizations and missing/empty qualification controls |
| A05–A09 | Core direct/optional mixed-list inventory, bad-group siblings; rule partial-exact remaining-use case |
| A10–A13 | Core Poetry/Pipfile container boundaries, individual values excluded, valid sibling and custom-category controls |
| A14–A21 | Core both environment basenames; root/null distinction, dependency and pip wrong values/members, unknown mappings and string grammar controls |
| A22–A23 | Rule `test_declaration_structure_gap_never_revokes_positive_credit` (same-file exact, unrelated exact, qualified partial lock), plus existing lock-scope tests |
| A24 | Rule `test_associated_lock_failure_retains_precedence_over_structure_gap` (body/shape); `test_possible_format_credit_retains_precedence_over_structure_gap` |
| A25–A26 | Rule `test_body_and_structure_gaps_merge_sorted_evidence_for_each_uncredited_package`; literal torch finding plus second current package paths/status |
| A27 | Rule no-use case, full credited cases under complete/unknown Python view, four coverage states with current use; existing empty-result veto tests |
| A28 | Core restoration inventory and rule exact/empty/removal rescan outcomes; old context remains immutable |
| A29 | Audit CLI 3 new structure fixtures × 7 prewritten threshold/override/mixed cases, each restored to the old missing-pin behavior |
| A30 | Audit CLI 3 new fixtures through JSON/schema, default/show-skipped text, default export, ignore/suppression, user-file immutability |
| A31 | Conflicting exact consumer case, unchanged existing requirements graph/body controls, core PEP 508 and individual-value exclusions |
| A32 | Repeated whole JSON comparison excluding only generated_at, existing legacy defaults/body tests and schema reader validation; historical artifact preservation is separately hash-checked by session gate |

## Evidence limits and deliberate test changes

The CLI unit assertions contain independently written complete finding objects and exact summaries,
with schema validation for the entire document. They do not supply a new whole-report gold artifact.
The affected validation runner must independently freeze complete synthetic report expectations and
compare all fields, including paths, documents and order, before claiming whole-report acceptance.

The former `wrong-shape` member of the old out-of-scope WARNING test is removed because this exact
shape is now in the accepted finite table, and is explicitly tested as SKIPPED. Existing malformed
child-manifest and uncertain-tool tests now expect the same D-M skip while still asserting no
ancestor/import credit. Their declaration-credit positive case remains unchanged. Requirements
grammar/cycle/depth/directive exclusions remain WARNING and are not reclassified.

Original RED attempts used the old product. Setup failure at default sandbox TEMP and an attempt
under the parent Git checkout are preserved as environment/harness failures, separately from
semantic RED (45 failed/10 passed and 6 failed/4 passed). A later GREEN selection typo referenced
a non-existent test folder and executed zero tests; its log/receipt is also retained separately.
No failed setup attempt is counted as semantic regression evidence.
