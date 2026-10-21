# R07-C D-F implementation draft qualification

Status: PROPOSED, not applied. Baseline `60aa97f91b09c56e118c434c954ebc451679423e`.

Only `core/deps.py` and `rules/env.py` are proposed. The original worktree remains unchanged.
The draft source has passed Python 3.10 AST parsing, Ruff check/format, and read-only `git apply --check`.
No product, test, HTTP, provider, GPU, package-manager or child experiment execution took place.

## Existing credit equivalence

Let A(l) be the set of canonical declaration/import origin names associated with a lock l before
package membership, using exactly the previous same-directory manager table, source-file equality,
nearest project root and uncertain-directory barrier logic. Let P(l) be its captured package set.
The old algorithm computes requirement-closure packages union each A(l) intersect P(l).
The shared `_format_lock_origins` extracts A(l), and `qualified_lock_packages` still computes precisely
that same union. Moving membership after origin association does not add a project root, manager,
origin, candidate, package name, traversal budget or lock-credit source. Unknown barriers retain the
old import-only effect; direct declaration pairing keeps its old independent path. Requirements closure
credit still comes directly from qualified closure lock records. This is an algebraic/source review,
not a claim that runtime equivalence tests have executed.

## New bounded fact and conclusion

`Lockfile.read_issue` is an optional typed known-failure flag with only `unreadable` and `invalid_syntax`.
The default None preserves existing constructor behavior; it means no recorded failure from those two
checks, not a certificate of complete/valid package grammar. Format parsers keep exactly their previous
successful package-name extraction and `unparsed` diagnostic behavior. `read_text` None includes its
existing missing/binary/oversize/safe-path/read failure contract; a skipped listing candidate is not
newly discovered. Syntax decoder exceptions carry no message into new persisted evidence.

The new map includes a package only when the captured origins already satisfy existing R06-B
association for a supported failed format lock. An unpaired/wrong-manager lock cannot grant credit
or trigger D-F. There is no inferred omitted import origin. A new rule branch follows existing exact
and qualified credit and precedes the existing D-L branch; severity INFO/status SKIPPED with fixed
path-only evidence is independent of primary-Python coverage. It does not create per-package PASS.
`env.lockfile_present`, manifest presence, critical in-use enumeration and old empty-result veto are unchanged.
The no-failed-lock fast path avoids a second origin traversal for ordinary captured dependency views.

Valid syntax with wrong top-level/collection/partial-entry shapes remains unchanged and explicitly OPEN.
General dependency/parser/listing, missing origin, framework, README/config and broader R07-C certificates
are not covered. No engine, redaction, schema, profile, dependency version or historical gold edit is proposed.
