# 0.7.0 release preparation

Assigned scope: [REL-01–04](../../plan/release-2026-11-07.md).
Starting main: `07e7e855d87b65b56bca4c301286eb8667b929c1`.
Status: **IN_PROGRESS / NOT_RELEASE_READY / NOT_PUBLISHED**.

## REL-01: current-tree material cleanup

Remove seven dedicated form/draft/index files and the actual templates/field
instructions in mixed plans and reports. Repair navigation and preserve public
project cases, tests, runtime evidence and original hash inventories. No Git
history rewrite, Issue/PR deletion or local private-handoff upload is performed.
The maintainer's new publication request supersedes older session-specific
release prohibitions; it does not waive acceptance.

Acceptance first fails on the seven existing files. After removal it exposes one
remaining document link; that link is corrected. The final content check passes:
all seven files absent, no actual form URLs/draft markers/templates, and no
Markdown links to the removed documents. Added/modified text and local link
destinations are reviewed; product/test/dependency/schema/workflow inputs are
unchanged for this task. All original machine-readable engineering evidence
remains byte-identical. REL-01 uses the documentation-only validation category;
it does not mark release quality or Gate A/B as passed.

## Candidate and remaining gates

Existing source is 0.7.0 and writes run schema 2, reading schemas 1 and 2.
The previously built 0.6.2 bridge is local compatibility evidence, not an
available PyPI release. A final candidate needs honest migration/release notes,
fresh complete quality, all five Gate A/B matrices, installed-wheel checks and
exact-head cross-platform CI.

The existing release workflow consumes a same-candidate `release-validation`
artifact but this repository has no producer workflow. REL-02A adds that missing
nonpublishing evidence channel while preserving all 28 gate requirements and
same-commit/hash checks. Historical GPU/API PASS records are not rebound to the
new candidate. Current GPU/provider resources and a fresh paid budget have been
requested; until supplied the affected gates remain BLOCKED_NOT_AUTHORIZED.

Do not create a tag, upload to PyPI or claim release acceptance before all
mandatory gates and artifact provenance pass. Publication uses the existing
protected PyPI OIDC workflow, one build and the exact accepted wheel/sdist.
