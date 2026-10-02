# UX specification proposals and delivery status

Status: **Product changes approved for implementation on 2026-10-02** by the
maintainer's instruction to complete all six recommendations in order. The
[ordered delivery plan](../UX2_2026-10-02.md) records scope and acceptance.
**UX2-T01–T06 are implemented on `main` (unreleased).** T06 received explicit
D-41 maintainer approval and [PR #8](https://github.com/EnumaElish123/ReproLLM/pull/8)
was squash-merged as `b5e1317`. [All five main CI jobs passed](https://github.com/EnumaElish123/ReproLLM/actions/runs/37023660708).
The [workflow report](../../dogfooding/2026-10-02-ux2-workflows.md) and
[lifecycle report](../../dogfooding/2026-10-02-ux2-rule-lifecycle.md) retain their
dated validation snapshots; the PR records subsequent approval and merge.

Proposal files below retain their historical pending labels and evidence; this
index and the normative specification record their current disposition.

| Task | Concrete proposal | Current disposition |
|---|---|---|
| UX2-T01 / UX-T03 | [Separate task inventory from selected experiment tasks](UX-T03-T04-proposal.md) | Implemented: read-only inventory, explicit selection and empty default metrics; spec §§3.2/14 and reviewed val §7.1 supplement adopted. |
| UX2-T02 / UX-T04 | [Explicit findings/exit policy and compact terminal warnings](UX-T03-T04-proposal.md) | Implemented under §21; complete JSON/GitHub findings and exit thresholds preserved. |
| UX2-T03 / UX-T06 provider | [Classify provider=other with an explicit API endpoint](UX-T06-provider-other-api.md) | Implemented under §§4.3/12.4; provider identity, D-21 pinnability and metadata-only/offline behavior preserved. |
| UX2-T04 / UX-T06 judge-only | [Add an explicit judge-only profile](UX-T06-judge-only-profile.md) | Implemented: approved D-44 supersedes only D-06's seven-profile limit; explicit `judge_only` is the eighth profile with the conservative exception in §6.1. |
| UX2-T05 / UX-T08 extension | [Render evaluation/judge/privacy research details](UX-T08-export-research-details.md) | Implemented under §19 with effective values, source labels, selected-run evidence and safe Markdown. |
| UX2-T06 / UX-T05 lifecycle | [Full candidate view and reversal/deactivation](future-rules-lifecycle.md) | Implemented and explicitly reviewed under D-41: versioned recovery copies, retained provenance, inspection, removal and restoration. Merged via PR #8. |

[UX-T03/T04 GitHub issue draft](UX-T03-T04-issue-draft.md) is prepared but unfiled. [Independent source review](source-review.json) records exact pins, source anchors, count and set hash. The complete 13,123-entry source inventory is retained only in the local validation workspace as `scope/independent-lm-eval-task-gold.json`; it is not included in this compact historical proposal bundle and this label is not a repository link. The inventory has 13,123 safe lm-eval names and set hash `2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`; it is not evidence that an experiment ran every task. Historical proposed output counts are predictions from source/rule semantics; the adopted task-selection expectations and measured deltas are recorded separately in val §7.1 and the session report.

The two exported example documents are historical evidence for the extension proposal, not successful model executions. [Initial wording review](proposal-review.json) records the first reviewed boundaries, safe single-line task names and unchanged 13,123-name source gold. The [latest concrete-option review](proposal-review-concrete.json) supersedes the two earlier provider/judge draft hashes: the judge option now gives 14 exact additional rules, 6 required fields, 5 CRITICAL overrides and a complete exception/init predicate; the provider option gives a qualifying-URL predicate and exact per-role manifest/State source table. These concrete options were subsequently approved and implemented; [D-44](../00_architecture_and_decisions.md) now records the profile-limit amendment. Historical review files are not evidence that current integration, CI or release gates have completed. `source-ledger.json` retains original source hashes and bundle hashes. No absolute temporary links, credentials, paid requests, model executions, new package release or Action publication are required to review these documents.
