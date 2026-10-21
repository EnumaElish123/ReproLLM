# R07-C D-S acceptance test draft

State: DRAFT_NOT_APPLIED. Base is `603883fd8b7c7be2eac42d335a182ff654f93918`.
Only external draft files and a patch were written. No tracked product or test file
was changed, and no test, collection or product command was executed.

The draft contains **109 new parameterized cases / 15 new functions**, plus the
explicit amendment of **7 existing decoded-shape cases** that currently assert
`read_issue=None`. Every other existing helper and test function retains its full
source text and AST. The old seven-case test is renamed to reflect its revised
normative assertion; no obsolete expectation is silently deleted.

| Module / independent business expectation | New cases |
| --- | ---: |
| TOML: all present wrong-type package containers, including falsey values; unusable entries; existing diagnostics unchanged | 24 |
| Conda: non-None wrong root, wrong package container, unusable entries; existing diagnostics unchanged | 19 |
| Pipfile: nonmapping decoded root, retaining the old invalid-document diagnostic | 5 |
| Pipfile: present wrong-type default/develop, including null/false/zero/empty string/list | 10 |
| Missing/empty containers and intentionally opaque nonempty names, versions and Pipfile values retain prior extraction | 16 |
| Partial extraction preserves captured names and their qualified credit, while missing associated use remains unverified | 5 |
| Rules: all four formats reuse the full existing D-F finding and lock-presence semantics | 4 |
| Rules: zero, complete, capped and unavailable Python views keep the same structural failure conclusion | 4 |
| Rules: exact, nested exact, other qualified lock and captured partial member retain positive credit | 4 |
| Rules: unpaired/wrong-manager/nearer-project/barrier lock does not suppress its existing warning | 4 |
| Rules: partial known member remains credited while another associated used package receives the complete SKIP finding | 4 |
| Rules: lock entries alone do not establish use | 1 |
| Rules: a structural failure and a syntax failure share sorted evidence without suppressing unrelated WARNING | 1 |
| CLI: severity overrides and never/critical/warning thresholds; isolated 1→0 and mixed 1→1; repaired empty lock returns old failure | 7 |
| CLI: deterministic complete JSON, default/show-skipped text, default export, suppression and read-only artifact protection | 1 |

The independently reviewed proposed specification is §12.3.5. Its shape table,
literal nonempty-name definition, legacy top-level Conda None exception, opaque
Pipfile keys/values, old diagnostic preservation, partial credit ordering and D-F
wording all match the draft assertions. The implementation draft is not used to
compute expected statuses, messages or evidence. Existing unchanged D-F/D-L,
engine, audit/export and scan-diagnostic modules remain required regression inputs
for the later accepted P-B run.

Static qualification: all three proposed test modules compile; Ruff and formatter
pass with the existing repository config and intended logical file names; the
combined patch passes `git apply --check`; formal tracked targets retain their
original hashes. The first static build stopped on a new 101-column assertion
literal; it was split into adjacent literals without changing its value. This is
recorded in `preparation-attempts.json`, not described as a test execution failure.

After concrete policy acceptance, apply tests first and execute a genuine RED run
against the unchanged product. Then apply the accepted implementation and run the
focused complete module set. This preparation does not claim that either stage
has run or passed. Final full quality, five-project Gate A, affected init/L1/export
and exact-head CI remain P-B obligations.
