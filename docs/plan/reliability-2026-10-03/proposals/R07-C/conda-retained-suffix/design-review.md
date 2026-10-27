# D-M-CS independent design and exact-patch review

Result: **PASS static design/patch review; no blocking finding**. This is not a
maintainer decision or product validation. Baseline:
`22e3dbcb799a18b8ef096c6fc42e5f5ab7ae9a0d`.

Both before-file hashes match frozen Git source and the unchanged worktree.
Applying the unified diffs in memory yields exactly the two bound after hashes.
`git apply --check` succeeds without applying either patch to the product.
Static Python 3.10 AST parsing, Ruff and Ruff formatting checks pass. These
checks only inspect proposed text; candidate policy execution count remains zero.

The whole-product AST difference reduces to one new internal Literal member and
one `setdefault(path, "unparsed_conda_specifier")` expression at the existing
RANGE-failed placeholder assignment. Removing only those additions reproduces
the original complete module AST. No regex, CE return, declaration append,
canonicalization, read, candidate, barrier or consumer change is hidden in the
implementation patch.

The design preserves the existing numeric RANGE branch and both accepted CE
returns. Whole-document shape checks still precede traversal; existing causes
and CS/CE/pip first-call ordering retain `setdefault` semantics. Existing
qualified/exact credit and D-F/D-S → D-L → D-M → D-G priority match the actual
rule source. Higher-priority complete findings remain unchanged. An existing
D-M finding may gain only another distinct sorted failed-source path, after its
original first declaration/import evidence.

The significant product cost is clearly disclosed: even a nonexact wildcard or
unrelated noncritical retained suffix may replace other uncredited critical
package warnings with INFO/SKIPPED. Isolated threshold exits and default text /
export visibility can consequently change. This is a new discretionary policy,
not a logical consequence of Conda syntax, and option B remains valid. The new
cause supplies neither exact credit nor unknown package use or completeness.

The proposed §12.3.14 and limited cross-reference edits preserve §12.2 exact
parsing and §12.3.13's omission scope. Engine, redaction, schemas, scanner,
dependencies, version, rule IDs, historical artifacts and five-project gold are
outside the patch. Wider R07-C remains OPEN.

All 38 acceptance groups are future contracts marked PROPOSED/NOT_RUN. This
review neither waits for nor converts independently collected current-baseline
observations into candidate-policy PASS. Full finding, CLI, graph, privacy,
platform-newline and five-project acceptance remain future P-B obligations.

The official-source packet was reviewed for citation framing and explicit
limits. This review did not independently re-fetch its external pages, install
or execute Conda, or certify installed/historical client grammar. The package
properly separates upstream syntax evidence from the project's optional global
SKIP policy. A concrete maintainer decision is still required before P-B.

[Machine review](concrete-patch-review.json) binds all reviewed file hashes,
exact before/after targets, static command receipts and scope qualifications.
No repository file or packet byte changed during the review.
