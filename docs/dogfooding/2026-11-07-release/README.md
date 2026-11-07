# Application-material cleanup; release deferred

Assigned scope: [REL-01–04](../../plan/release-2026-11-07.md).
Starting main: `07e7e855d87b65b56bca4c301286eb8667b929c1`.
Status: **REL-01 DOCUMENTATION_ACCEPTED / RELEASE_DEFERRED_BY_MAINTAINER / NOT_PUBLISHED**.

The maintainer subsequently limited this session to repository material removal:
“先不发行新版本，删除仓库中申请表相关内容”. No release acceptance or publication
is being continued. Three newly drafted, uncommitted producer/workflow/test files
were removed from the source tree and never pushed. Existing product, tests,
dependencies, schemas and CI/release workflows remain unchanged.

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

## Deferred release scope

Existing source is 0.7.0 and writes run schema 2, reading schemas 1 and 2.
The previously built 0.6.2 bridge is local compatibility evidence, not an
available PyPI release. A final candidate needs honest migration/release notes,
fresh complete quality, all five Gate A/B matrices, installed-wheel checks and
exact-head cross-platform CI.

The existing release workflow consumes a same-candidate `release-validation`
artifact but this repository has no producer workflow. That work is deferred;
no evidence channel or resource replay is added by this cleanup. Historical
GPU/API PASS records are not rebound. No GPU work or paid request is executed.

Do not create a tag, upload to PyPI or claim release acceptance before all
mandatory gates and artifact provenance pass. Publication uses the existing
protected PyPI OIDC workflow, one build and the exact accepted wheel/sdist.

## Delivery

The cleanup itself is committed at `62d18025f5357c7805ae9df1c526dbcbe376fac0`.
The following documentation-only update records the maintainer's narrowed
scope. Final main CI is checked against that exact delivery commit after push;
it does not mark release Gate A/B complete. No tag or package is published.
