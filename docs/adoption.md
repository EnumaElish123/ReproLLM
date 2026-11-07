# Adoption metrics

Updated 2026-11-07 (Asia/Shanghai). Refresh monthly on the 1st (D-37) and when
new public usage or contributions appear. Counts below describe observed
artifacts and projects; they do not establish distinct independent people.

## Current observed evidence

| Metric | Observed value | Scope and source |
|---|---|---|
| Public project identities with documented use | **2** | `PI-01`, Privacy_Injection; `LS-01`, LingshuSmartLink. LS-01 local/live results and fixed-source probe are contributor-reported, with private raw receipts. |
| Non-owner-account issues | **5** | #11/#13/#14 by `Mosionca2` for PI-01; #15/#16 by `LiangRichard13` for LS-01 |
| Merged non-owner-account PRs | **2** | #12 by `Mosionca2`; #17 by `LiangRichard13`, integrated with maintainer documentation corrections |
| Non-owner contributing GitHub accounts | **2** | Account identities only; not a verified count of independent people or organizations |
| Distinct independent adopters / laboratories | Not established | Different accounts and repeated experiments do not establish independence |
| Planned independent Agent Skill researcher trials | Unobserved | The CLI case below is not the planned 3–5-person Skill cohort |
| Current monthly PyPI downloads / GitHub dependents / paper artifacts | Not measured | No current collection was performed; absence of a measurement is not zero |

The [repository issue inventory](https://api.github.com/repos/EnumaElish123/ReproLLM/issues?state=all&per_page=100)
was checked on this date. PRs returned by that endpoint are counted separately
from issues; #12 is not a third issue. Owner-authored #9 is excluded from the
non-owner-account count. Account-based contribution counts are not counts of
independent people or unassisted use. The dated
[GitHub observation](dogfooding/2026-11-07-owner-followup/evidence/github-state.json)
records the post-integration inventory: no open issue or PR. This is a snapshot,
not a promise about future reports. Stars (270), forks (2) and published GitHub
releases (9) are repository signals on this date, not adoption counts.

## PI-01: one research project and its upstream feedback

| Evidence | Verified connection and outcome |
|---|---|
| [Privacy_Injection case study](https://github.com/Mosionca2/Privacy_Injection/blob/95e3200053afaecc31af880313045e19393ee832/docs/reprollm-case-study.md) | One public, agent-assisted local-model privacy study using released ReproLLM 0.6.1 for isolated condition capture, lock, audit, diff and historical export. A [committed manifest](https://github.com/Mosionca2/Privacy_Injection/blob/dbbdff0791229d6edf3c1ca5f5432ce07dbfc3fb/reprollm.yaml) confirms repository integration. |
| [Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) | Opened 2026-11-02 from that workflow; requested a consolidated isolated-condition recording recipe. Closed through PR #12. |
| [Merged PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) | Same project/account; merged 2026-11-02 as `ad8b2c7057b6473072b65102eaf8e122b647acec`. Adds the [concurrent local-model recipe](tutorials/concurrent-local-experiments.md). Its CPU documentation checks are distinct from the study's GPU evidence. |
| [Issue #13](https://github.com/EnumaElish123/ReproLLM/issues/13) | Same project's [source-0.7.0/schema-2 follow-up](https://github.com/Mosionca2/Privacy_Injection/blob/dbbdff0791229d6edf3c1ca5f5432ce07dbfc3fb/reports/source-recorder-validation/REPORT.md). Asked about inline text retained as missing optional input candidates; clarified and closed 2026-11-03 in `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`. See the [upstream resolution](dogfooding/2026-11-03-issues-9-13/README.md). |
| [Issue #14](https://github.com/EnumaElish123/ReproLLM/issues/14) | Same project's [corrected stored-answer judge report](https://github.com/Mosionca2/Privacy_Injection/blob/9e3650282f4b72bfb3ccccdc0b4df45bec40ac34/reports/judge-injection-v2/REPORT.md), using source 0.7.0 at `f7bd2ad` while installed distribution metadata stayed 0.6.1. Closed 2026-11-07 after the [stored-answer recipe](tutorials/stored-answer-judge.md); retained V1 failures and the corrected campaign are not new adopters. |

These entries share **one project identity, PI-01**: three issue reports and one
merged contribution. The public
reports identify the work and contribution as agent-assisted, with maintainer
help and bounded version/platform evidence. They do not establish independent
laboratory replication, sustained adoption or completion of the Skill trial
cohort. This update reads the published evidence; it does not rerun or certify
the scientific results. The five pinned dogfooding repositories and the
maintainer's separate Action remain validation/internal integration evidence.

## LS-01: one application project and its upstream feedback

| Evidence | Verified connection and outcome |
|---|---|
| [Pinned LingshuSmartLink trial](https://github.com/LiangRichard13/LingshuSmartLink/blob/b09becc18b1b9cd0e4d6ac04ed61a7dcbb63554b/docs/reprollm-single-case-trial.md) | Public trial code/manifest and agent-assisted contributor report, on application PR #2 rather than its default branch. Original recorder is source `dfb72eda`, module/wheel 0.7.0. Reports synthetic fixture, real CPU ResNet18/GTE/Chroma components, and one online pipeline; most raw local/live evidence remains private. |
| [Issue #15](https://github.com/EnumaElish123/ReproLLM/issues/15) | Real `.pth` classifier layout motivated a reproducible synthetic format proposal. Accepted support landed in `b4d6c713f`; [maintainer reply](https://github.com/EnumaElish123/ReproLLM/issues/15#issuecomment-6704715084) distinguishes upstream engineering acceptance from the contributor's later fixed-main format probe. No full post-fix application replay is claimed. |
| [Issue #16](https://github.com/EnumaElish123/ReproLLM/issues/16) / [PR #17](https://github.com/EnumaElish123/ReproLLM/pull/17) | Same project/account's tutorial request and contribution; merged/closed 2026-11-07 in `506dd87756161668c7c397f8171c9b626cb0042b`. The [tutorial](tutorials/single-case-multimodal-app.md) has pinned sources, explicit interpreters and reported-versus-replayed boundaries. |
| [Maintainer fixture acceptance](dogfooding/2026-11-07-owner-followup/README.md) | 20 offline application tests and 18 command receipts, repeated identical report/trace bytes and bounded rounds drift, with network/model imports guarded. It checks the recipe, not the contributor's private local/live campaign. |

The [claim classification](adoption/lingshu-2026-11-07.md) records PUBLIC_VERIFIED,
USER_REPORTED, DEVELOPER_VALIDATED and unknown/not-applicable boundaries.
LS-01 and PI-01 are two distinct public projects; neither separate accounts nor
an accepted PR establish independent laboratories, sustained deployment or
medical effectiveness. The `.pth` feature is unreleased source functionality,
not part of public PyPI 0.6.1.

## Monthly accounting

| Month | PyPI downloads | Non-owner-account issues | Merged non-owner-account PRs | Public research project identities |
|---|---|---:|---:|---|
| 2026-10 | Not measured | 0 | 0 | No evidence established in the reviewed October inventory |
| 2026-11, through 11-05 | Not measured | 2 | 1 | 1, PI-01; independence not established |
| 2026-11, through 11-07 | Not measured | 5 | 2 | 2 documented projects, PI-01 and LS-01; reported/replayed scopes above |

The October contribution zeros are from the reviewed issue/PR creation and
merge dates, not an estimate of downloads or people. November is a partial
month; repeated captures and the source-recorder follow-up do not increment the
project count. Current GitHub dependents and papers containing exported
artifacts remain unmeasured.

The earlier September snapshot is retained as history: 110 downloads in a
30-day window including CI/mirror scans, zero reported external issues/PRs or
dependents, the maintainer's own Action integration, and zero reported paper
artifacts. Those historical observations are not current measurements or
independent adoption. Earlier star counts and duplicate release lists are not
used as adoption evidence. Current package availability is tracked on the
[roadmap](community/roadmap.md).

For independent trial materials, see [A02](trials/a02-local/README.md).
The [LS-01 classification](adoption/lingshu-2026-11-07.md) retains the dated
public-versus-reported evidence boundaries.
