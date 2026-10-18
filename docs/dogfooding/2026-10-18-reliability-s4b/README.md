# S4-B: D03 candidate publication gates

Date: 2026-10-18. Starting main: `53782ab93a606abe3b57491d878759dd41aa5f52`.
The work follows the current reliability package, S4-A report and CI follow-up,
and Sprint 4's D03 task. The starting checkout was clean. No version bump, tag,
PyPI publication, GitHub release, provider request or model run is part of this session.

## Implementation

- Main/PR CI and release reuse the same five-job quality matrix, check
  the exact requested commit and install locked dependencies.
- Preflight verifies the candidate version/tag, nonempty unique CHANGELOG
  section and the complete same-commit resource/validation bundle from a
  successful same-repository Actions run. Its exact notes are retained.
- One build produces wheel/sdist and a source/version/hash manifest. The existing
  D02 isolated-install validator tests that exact wheel. Distribution receipts
  require all 26 actual command shapes/exits/hashes and all 13 acceptance checks.
- Final authorization recalculates the wheel, sdist, notes and validation hashes.
  Both publishing jobs repeat that check after downloading the same artifacts.
  Non-successful prerequisites and manual dispatch cannot publish. PyPI retains
  its protected environment and job-local OIDC permission.
- The S4-A handoff's missing/duplicate run-record RuntimeError now becomes a
  portable JSON FAIL, without copying the private exception text.

The tool does not infer actual model execution from JSON: the validation run is
the trusted producer of independently reviewed evidence. Its compact, closed
28-item matrix indexes the existing requirements in `val.md`. The contract and
safe nonpublishing rehearsal instructions are in [releasing.md](../../releasing.md).

## Tests and evidence

Acceptance tests preceded implementation. The initial gate tests failed because
the release decision module did not exist; workflow tests failed against the old
graph. Two actual capture failures preceded the D02 error-handling fix. Review
then reproduced length-only command acceptance and null metadata failures;
seven new negative regressions first failed and then passed after hardening.

The three new/affected gate, workflow and distribution suites passed **99 tests**.
Workflow selection and existing consumer checks were additionally exercised.
Official actionlint 1.7.12 accepted all three workflow files. Its downloaded ZIP
SHA-256 was `6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9`,
matched against the official checksums. Shellcheck/pyflakes were unavailable and
explicitly disabled in that lint invocation; Git Bash independently parsed all
23 shell blocks. Actual Python metadata/checkout guards and publication condition
evaluation cover success, cancellation, skipped/missing results, wrong commits,
foreign repositories and nonpublishing dispatch.

The final Windows quality run completed all **19 commands**: **2,774 passed,
4 skipped, 4 deselected**, 93.76% coverage; redaction line/branch coverage 100%;
the separate security selection **203 passed, 2 skipped**. Ruff, format, strict
mypy, four generated documents, all examples and self-audit passed. All 450
code/test/workflow/schema/dependency inputs remained unchanged during the run.
The final gate took 463.110 seconds of wall time. Its frozen-input identity is
separate from the first candidate's accepted quality snapshot retained in
[quality-first-candidate.json](quality-first-candidate.json).

The initial sandbox/long-TEMP run failed and is retained in
[quality-initial-failure.json](quality-initial-failure.json). A short-TEMP,
verified-tool rerun narrowed the failures to three Windows symlink privilege
errors. The final run used an administrator token and did not skip those tests
or change the test selection. An old security-order consumer assertion was
updated to follow the reusable quality graph and passed its focused regression.

The first schema comparison retained in
[quality-windows-newlines.json](quality-windows-newlines.json) was physically
unequal because Windows exports CRLF while the ten Git schema blobs use LF.
Recomparison of those same artifacts after **only CRLF-to-LF canonicalization**
matches every Git blob byte for byte; all raw and canonical hashes are in
[quality-summary.json](quality-summary.json). No schema, product behavior or
gold was changed. Strict Linux schema freshness remains part of remote CI.

The final [five-project Gate A](gate-a-final/README.md) repeated all 50 commands
after the corrected tool's full QA: ten fresh product commands, ten complete
JSON comparisons and 30 before/after Git checks. All passed with zero JSON or
stderr differences; wall time was **60.774684 seconds**, product-command time
70.857644 seconds and all-command time 73.370015 seconds. The original
[first-candidate Gate A](gate-a/README.md) remains a separate historical run.
The 154 protected product inputs did not change in either run.

Quality receipts record the parent HEAD observed while the frozen working tree
was tested. [commit-input-binding.json](commit-input-binding.json) verifies all
450 tested raw file hashes still match and their Git-filtered blobs belong to
the accepted corrected commit. [The first binding](first-commit-input-binding.json)
preserves the earlier candidate's identity. Test logs stay in a private temporary directory;
portable summaries retain command identifiers, exit codes, elapsed times and
byte hashes. They do not copy local paths or identities. This is a CI/tool-only
product scope; the five-project L0 baseline is nevertheless freshly exercised
for this session as requested. Historical native results are not relabeled as
current-candidate resource passes.

## Actual build follow-up

The first implementation commit was
`7ca1c25e2c8c29dfaa73f70c7c0fdb513984e9bb`. Its first and only build succeeded,
but the manifest gate rejected uv's automatically created one-byte `.gitignore`.
The original packages, build log and failure hashes are retained in
[initial-build-failure.json](initial-build-failure.json); the candidate was not
published. This exposed a real build integration failure beyond synthetic tests.

Three positive marker cases first failed; eight rejection cases already passed.
The smallest fix accepts only the regular uv marker's exact star bytes with
optional LF/CRLF and at most three bytes. It remains outside the two-package
manifest. Unknown hidden files, directories and invalid content still fail.
All **51 release-gate tests** then passed, including authorization after download
without the marker. The changed tool/test inputs trigger a new complete final
quality run and a separate single build for the corrected candidate. The first
candidate's quality, inventory binding and five-project evidence are preserved.

The initial real installed-wheel attempt also rejected Windows schema exports
at command 22 (`installed_schema_exports`), after isolated installation and
the walkthrough succeeded. Its FAIL remains in
[initial-wheel-validation.json](initial-wheel-validation.json). The D02 tool now
normalizes **only CRLF/LF** when comparing the schema byte dictionaries, without
rewriting either side. A positive `_package_data` case first failed; five
negative cases reject semantic/space changes, missing/extra JSON and bare CR.
The complete distribution suite then passed **36 tests**. The intermediate
marker-only QA was stopped after this new failure and retained as
[quality-marker-only-aborted.json](quality-marker-only-aborted.json), never PASS.

## Corrected candidate acceptance and delivery

The corrected implementation is
`a4d895d4f30f6f74421d7f1cd96606f9b0baba15`. It passed a **single fresh build**,
the D02 isolated installed-wheel acceptance (**26 commands / 13 checks**), and
an independent recheck of the two copied download-artifact files. All **141
package payload files** exactly equal the accepted source tree. Build through
preflight verification took **24.547 seconds**; this is a different candidate
from the retained failed first build, not a second build inside one release chain.

| Artifact | SHA-256 |
|---|---|
| `reprollm-0.7.0-py3-none-any.whl` | `0be12d1d44a07e1ab29459c161cf67fcdc48a0934d1e57d593cc5887ac6049ff` |
| `reprollm-0.7.0.tar.gz` | `922d83edcc1fbefe31998ae40e85301a6875c208bd47b69054ebf27a669445f1` |

[build-summary.json](build-summary.json) retains commands, hashes, source binding
and the exact manifest text (including its original line endings), so its hash
can be reconstructed independently. [distribution.json](distribution.json)
contains the actual isolated import evidence, full receipts and acceptance checks.
The earlier same-wheel recovery is separately retained in
[initial-wheel-after-schema-fix.json](initial-wheel-after-schema-fix.json).

The actual corrected candidate's nonpublishing preflight exited **1** with
`release_notes_section`: development 0.7.0 has no finalized versioned notes.
It stopped there before inspecting resources; the absent formal resource bundle
is an additional independent block. [release-readiness.json](release-readiness.json)
records the exact expected failure. No successful formal bundle was fabricated.

At report creation, **push and remote CI acceptance remain BLOCKED by unavailable
local GitHub authentication**. HTTPS and default SSH authentication prechecks did
not succeed. The two implementation commits exist on local main; no tag or
version was published. A subsequent report-only commit carries these receipts.
The final pushed HEAD's five-job CI must be checked after successful authentication
and push; historical main/nightly success cannot substitute for it.

## Resource and publication readiness

The [standing resource ledger](../pending-resource-validation.md) retains:

| Gate | This session |
|---|---|
| VAL-R01 | BLOCKED: remaining four native projects need current-candidate acceptance; dated Linux H2/lm-eval/LlamaFactory evidence retains its original SHA |
| VAL-R02 | BLOCKED: formal paid judge needs fresh provider/tariff/budget preflight and bounded replay |
| VAL-R03 | BLOCKED: successful authenticated, model-author-authorized gated-file replay remains outstanding |

All 23 formal Gate B entries, their missing candidate evidence and dated
historical boundaries are listed individually in
[resource-readiness.md](resource-readiness.md).

There is no completed release validation bundle for this candidate. The current
development version also has no finalized versioned CHANGELOG section. These
conditions deliberately prevent release preflight. Unit success scenarios use
synthetic evidence in temporary fixtures only; they do not close resource gates.
The staged 0.6.2 bridge/0.7.0 transition remains unpublished. Release readiness is
**BLOCKED**, independently of D03's engineering/test acceptance.

## Handoff

Provisioned validation work should restore the formal inputs, execute the full
applicable matrix on one candidate SHA, retain input/report hashes and upload
the documented `release-validation` artifact. Only then can a nonpublishing
dispatch exercise the real accepted chain. A later release requires its own
explicit authorization and complete candidate evidence. Other pending policy
and adoption activities retain their existing task scope.
