# Codex for Open Source: public evidence index

Checked 2026-11-07 (Asia/Shanghai). Tasks OWNER-03 / M3–M5.
This is a claim-to-source index, not an approval or proof of application submission.
The [adoption ledger](../adoption.md) retains earlier dated snapshots.

| Claim | Bounded statement | Public source | Date / scope and limit |
|---|---|---|---|
| C01 | ReproLLM is public, Apache-2.0, under EnumaElish123 | [Repository](https://github.com/EnumaElish123/ReproLLM), [license](../../LICENSE), [observed repository metadata](../dogfooding/2026-11-07-owner-followup/evidence/github-state.json) | 2026-11-07. Repository control does not establish the applicant's personal name or ChatGPT account. |
| C02 | A local-first reproducibility CLI: deterministic audit, manifest/lock, runtime capture, semantic diff and export; model-assisted discovery is opt-in | [Specification](../plan/01_specification.md), [architecture](../plan/00_architecture_and_decisions.md) | Current source contract. Audit does not call an LLM. Planned API credits are for OSS maintenance, not permission to alter this boundary. |
| C03 | Public package is 0.6.1; source 0.7.0 and directory `.pth` support remain unreleased | [PyPI](https://pypi.org/project/reprollm/), [fresh index observation](../dogfooding/2026-11-07-owner-followup/evidence/release-status.json), [implementation](https://github.com/EnumaElish123/ReproLLM/commit/b4d6c713fe9cf16c1d97364fa07dda5f4ef24a60) | 2026-11-07. Alpha metadata is retained. No release is created by this work. |
| C04 | PI-01 documents agent-assisted use of released 0.6.1 and later source-scoped research captures | [Pinned case](https://github.com/Mosionca2/Privacy_Injection/blob/95e3200053afaecc31af880313045e19393ee832/docs/reprollm-case-study.md), [source follow-up](https://github.com/Mosionca2/Privacy_Injection/blob/dbbdff0791229d6edf3c1ca5f5432ce07dbfc3fb/reports/source-recorder-validation/REPORT.md), [corrected judge follow-up](https://github.com/Mosionca2/Privacy_Injection/blob/9e3650282f4b72bfb3ccccdc0b4df45bec40ac34/reports/judge-injection-v2/REPORT.md) | Public project evidence; repeated captures and #11/#13/#14 are one project, not independent adopters. Scientific results are not re-certified here. |
| C05 | LS-01 has public trial code/manifest, reported fixture/local/live use and a later fixed-main `.pth` format probe | [Pinned report](https://github.com/LiangRichard13/LingshuSmartLink/blob/b09becc18b1b9cd0e4d6ac04ed61a7dcbb63554b/docs/reprollm-single-case-trial.md), [claim classification](lingshu-2026-11-07.md), [#15 follow-up](https://github.com/EnumaElish123/ReproLLM/issues/15#issuecomment-6704715084) | Original recorder `dfb72eda`; fixed-main probe reported at `d73f45f`. Raw local/live/probe logs and fixed wheel hash remain private/unpublished. No full post-fix application or clinical validation claim. |
| C06 | Five non-owner-account issues and two merged PRs from two accounts, associated with two documented projects | [Adoption definitions](../adoption.md), [dated GitHub inventory](../dogfooding/2026-11-07-owner-followup/evidence/github-state.json), [PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12), [PR #17](https://github.com/EnumaElish123/ReproLLM/pull/17) | 2026-11-07 after #17 integration. Excludes owner issues and counts PRs separately. Different accounts do not establish independent laboratories or people. |
| C07 | Maintainer engineering acceptance and a fresh external synthetic recipe replay are recorded separately | [Issue-14/15 acceptance](../dogfooding/2026-11-07-issues-14-15/README.md), [owner fixture report](../dogfooding/2026-11-07-owner-followup/README.md), [validation baseline](../../val.md) | Candidate-bound results only. The five validation targets are not upstream adopters. This documentation session marks product Gate A/B NOT_APPLICABLE, not PASS. Resource restrictions remain visible. |
| C08 | Codex is intended to reduce reproduction, regression, compatibility review and documentation maintenance work | [Application draft and form check](a03-2026-11-07.md), [governance](../plan/validation-workflow-2026-10-13.md), [program](https://developers.openai.com/community/codex-for-oss) | Proposed maintainer use. No API integration, budget, program acceptance, security access or future outcomes are claimed. Applicant details and submission receipt stay private. |

## Citation and privacy rules

Link the public case/report commits above; do not copy private raw logs,
credentials, medical assets or the contributor's contact details into application
materials. Public contribution #16/#17 permits the offered tutorial's public
citation, not publication of unrelated private assets. The two projects are
documented usage cases with different levels of public reproducibility.

Repository signals at this check: 270 stars, 2 forks and 9 published GitHub
releases. They are dated popularity/activity signals, not download/user/lab
counts. Current monthly downloads, GitHub dependents and paper artifacts are
unmeasured. No arbitrary star threshold or promised selection probability is used.

## Remaining owner actions

Use the [current form/draft](a03-2026-11-07.md). Applicant details and role were
confirmed privately; Pro/Codex only was selected, without optional benefits.
Actual conditional fields remain unverified because browser URL verification
stopped the UI task; no Organization ID is invented and nothing is submitted.
Submission requires the final concrete form and applicable terms decision;
until observed it remains NOT_SUBMITTED / NOT_APPROVED. New releases stay behind
the independent release gates. M10 is continued handling of genuine feedback;
no new adopter or contribution can be manufactured to complete a checklist.
