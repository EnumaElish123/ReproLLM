# R07-C D-M-V independent design review

Date: 2026-10-23. Baseline source inspected: 237cd903fde777ede75a415bd75f2dc592ac5d7a. D-M-V is a local R07-C slice label, not an architecture D-nn. Status: PROPOSED; acceptance is not recorded here; candidate policy executions: 0. No product, tests, normative specification, prior proposal, gold, dependency, schema, CI or version is changed by this review.

The current normative §12.3.7 explicitly excludes Poetry individual package version fields. Existing behavior is therefore not a violation of that frozen current contract. This packet proposes one new bounded extraction-shape policy; it does not prove a complete Poetry document invalid and does not close R07-C.

## Recommendation A

At the existing _parse_pyproject Poetry dependencies iteration only, inspect the current decoded value: isinstance(value, dict) and 'version' in value and not isinstance(value['version'], str). On this predicate, use setdefault(logical_source_path, 'invalid_structure') on the existing internal declaration_read_issues. Do not infer a failure from _dependency_version_field returning (None,None), exact=None, diagnostic prose, unknown installed versions or missing pin outcome.

Do not broaden _invalid_pyproject_structure's earlier whole-file precheck. The existing PEP621 loops execute before this Poetry loop: if they set unparsed_requirement for the same file, that first cause must remain. Extending the early precheck would change this precedence and is not the chosen A. The helper remains called once for every existing iteration with allow_bare=True, its body and Pipfile caller stay unchanged, and each original DependencyDeclaration still appends without value coercion or filtering. Keep its name/display/specifier/exact/source/line and encounter order unchanged. Add no unparsed prose.

The mapping need not be for a critical package and may include a transport key. A present non-string version is the bounded shape predicate even with git/url/path/file/hg/svn/bzr; the claim is only about this explicit extractor field. The presence, truthiness or contents of a transport key do not exempt the field. A missing version and every string version, including empty/whitespace, valid nonexact and unsupported string grammar, do not trigger. A whole package value that is a string/scalar/list is outside the predicate, including multi-constraint arrays whose inner mappings are not currently iterated. Unvisited groups and other managers are out of scope. TOML has no decoded null: use real TOML bool/int/float/temporal/list/mapping cases, not invented null bytes.

## What the official sources establish

Official stable docs displayed Poetry 2.5 on access. Its dependency-specification page documents version strings/ranges/wildcards, source-only enrichment and multiple-constraint lists. This directly refutes treating every helper nonexact/empty return as extraction failure. It does not certify installation of any synthetic case.

Poetry-core tag 2.5.0 official poetry-schema.json defines the long-dependency version property as string; dependencies also have distinct string, mapping, transport, options and multi-constraint alternatives. Its bytes equal the separately captured 2.2.1 schema. This directly supports a bounded explicit field type check, not blanket rejection of all non-string package values. Reading a schema is not running schema validation, resolution or installation, and no such claim is made.

Poetry-core factory source at tag 2.5.0, create_dependency, handles git/file/path/url branches before its nontransport version-default branch. Its group loader separately expands constraint lists. The 2.2.1 source supplies a versioned comparison. These are source-level boundary observations, not executions of Poetry or a reason to implement those manager capabilities in ReproLLM.

No source says a wrong-type field conceals a valid exact pin or logically requires repository-wide SKIP. Recommendation A's propagation is an explicit conservative product-policy choice to reuse D-M consistently, not a deduction from schema validity.

## B: retain the current contract

Keep the current explicit version non-string behavior and leave the typed uncertainty extension OPEN. Current captured-view missing-pin WARNING may remain. Do not describe it as an independently proven full-repository absence certificate, nor call B a failing product result. NOT_NEEDED would require evidence that the proposed bounded surface is absent/unreachable in the supported general contract; absence in five fixed examples alone is insufficient. Current source does reach such decoded maps, so a concrete A/B proposal is warranted.

## Compatibility and bounded costs

For already used critical packages, actual exact-declaration or qualified origin-lock credit wins first; then D-F/D-S, D-L, D-M, D-G. Use existing D-M status/severity/message/hint/evidence and final deterministic sort. Partial successful declarations remain. Previously missing version, blank string, legitimate nonexact constraints, transport strings and multiconstraint lists keep their old capture behavior; no positive credit is added.

A malformed entry in an unrelated project or for a noncritical name may conservatively change every remaining used-but-uncredited WARNING, including FAIL-only promoted CRITICAL, to SKIPPED/INFO. An isolated gate can change exit1 to0. This is repository-wide D-M influence under existential exact credit, not a local lock association. An independent warning still fails its applicable threshold; applicability and the no-critical-use/empty-Python result controls remain. Default text can display PASS plus skipped count, default export omits skipped findings, complete JSON retains them. Existing D-M findings may gain sorted file evidence even without a status change. No general completeness claim follows.

Internal vocabulary and persisted document structure do not change. A new reader may assign different findings to newly analyzed inputs, but old stored JSON/history is not rewritten. No migration or release bump is proposed. No engine/scanner/redaction or D-41 protected implementation is changed. Future P-B must verify affected CLI/engine consumer behavior without changing those implementations.

## Exact normative connection checklist for root's unapplied patch

1. §12.2 rule table and Python/existential credit descriptions: references to dependency-SKIP sections may extend to §12.3.11, while preserving the separate exact grammar.
2. §12.3.6 vocabulary/allowed failure producers and final exclusions: keep existing invalid_structure code, add only §12.3.11 as an explicit bounded shape exception; do not broaden text/entry grammar globally.
3. §12.3.7 finite structure table/exclusions: preserve original all-parent precheck and its timing; individual Poetry values remain excluded except the later existing-iteration field predicate in §12.3.11. Pipfile remains excluded. Do not move this check into that table's earlier precheck or imply all individual version grammar now validated.
4. §12.3.8 D-G priority and remaining-exclusion wording: D-M now includes this extension before D-G; graph behavior unchanged.
5. §12.3.9 PEP621 and §12.3.10 embedded-pip exclusions: this is a separate Poetry shape continuation, not another Requirement parse route or blank-string policy.
6. Add §12.3.11 specifying exact reachability/predicate, setdefault first-cause timing, preserved helper/declarations/diagnostics/read traces, positive/uncertainty priority, global conservative cost, no invented pin/use, no persisted schema, alternatives/groups/other managers excluded and R07-C remains OPEN.
7. Other §12.3.1/.3/.4/.5 cross-references should be extended only where they refer to the whole family of dependency uncertainty continuations; do not mechanically convert independent unrelated ranges.

An exact spec-proposed.patch and SHA binding are root-owned deliverables. This review does not create/apply one or record acceptance.

## Future verification

future-acceptance.json/md contain 48 design rows, not executed tests. Independent source inventory is required before forecasting the five-project delta. Product P-B requires tests first, focused checks, one final complete quality gate, fresh five-project Gate A plus affected consumers and exact final-head CI. Documentation-only P-A can report link/content/input-binding checks with full-quality/Gate-A NOT_APPLICABLE, never PASS. Resource-independent work remains local; unavailable resources remain BLOCKED or scenario N/A without pretending passed. No GPU, paid API, external issue write or release is part of this design review.
