# Adoption metrics

Updated 2026-11-05 (Asia/Shanghai). Refresh monthly on the 1st (D-37) and when
new public usage or contributions appear. Counts below describe observed
artifacts and projects; they do not establish distinct independent people.

## Current observed evidence

| Metric | Observed value | Scope and source |
|---|---|---|
| Public research projects with recorded use | **1** | `PI-01`, Privacy_Injection; committed manifest and version-scoped reports below |
| Non-owner-account issues | **2** | Issues #11 and #13, both by `Mosionca2` for `PI-01` |
| Merged non-owner-account PRs | **1** | PR #12, by the same account and for the same project |
| Distinct independent adopters / laboratories | Not established | Different accounts and repeated experiments do not establish independence |
| Planned independent Agent Skill researcher trials | Unobserved | The CLI case below is not the planned 3–5-person Skill cohort |
| Current monthly PyPI downloads / GitHub dependents / paper artifacts | Not measured | No current collection was performed; absence of a measurement is not zero |

The [repository issue inventory](https://api.github.com/repos/EnumaElish123/ReproLLM/issues?state=all&per_page=100)
was checked on this date. PRs returned by that endpoint are counted separately
from issues; #12 is not a third issue. Owner-authored #9 is excluded from the
non-owner-account count. Account-based contribution counts are not counts of
independent people or unassisted use.

## PI-01: one research project and its upstream feedback

| Evidence | Verified connection and outcome |
|---|---|
| [Privacy_Injection case study](https://github.com/Mosionca2/Privacy_Injection/blob/95e3200053afaecc31af880313045e19393ee832/docs/reprollm-case-study.md) | One public, agent-assisted local-model privacy study using released ReproLLM 0.6.1 for isolated condition capture, lock, audit, diff and historical export. A [committed manifest](https://github.com/Mosionca2/Privacy_Injection/blob/dbbdff0791229d6edf3c1ca5f5432ce07dbfc3fb/reprollm.yaml) confirms repository integration. |
| [Issue #11](https://github.com/EnumaElish123/ReproLLM/issues/11) | Opened 2026-11-02 from that workflow; requested a consolidated isolated-condition recording recipe. Closed through PR #12. |
| [Merged PR #12](https://github.com/EnumaElish123/ReproLLM/pull/12) | Same project/account; merged 2026-11-02 as `ad8b2c7057b6473072b65102eaf8e122b647acec`. Adds the [concurrent local-model recipe](tutorials/concurrent-local-experiments.md). Its CPU documentation checks are distinct from the study's GPU evidence. |
| [Issue #13](https://github.com/EnumaElish123/ReproLLM/issues/13) | Same project's [source-0.7.0/schema-2 follow-up](https://github.com/Mosionca2/Privacy_Injection/blob/dbbdff0791229d6edf3c1ca5f5432ce07dbfc3fb/reports/source-recorder-validation/REPORT.md). Asked about inline text retained as missing optional input candidates; clarified and closed 2026-11-03 in `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`. See the [upstream resolution](dogfooding/2026-11-03-issues-9-13/README.md). |

These four entries share **one project identity, PI-01**. They are one usage case,
two issue reports and one merged contribution, not four adopters. The public
reports identify the work and contribution as agent-assisted, with maintainer
help and bounded version/platform evidence. They do not establish independent
laboratory replication, sustained adoption or completion of the Skill trial
cohort. This update reads the published evidence; it does not rerun or certify
the scientific results. The five pinned dogfooding repositories and the
maintainer's separate Action remain validation/internal integration evidence.

## Monthly accounting

| Month | PyPI downloads | Non-owner-account issues | Merged non-owner-account PRs | Public research project identities |
|---|---|---:|---:|---|
| 2026-10 | Not measured | 0 | 0 | No evidence established in the reviewed October inventory |
| 2026-11, through 11-05 | Not measured | 2 | 1 | 1, PI-01; independence not established |

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

For historical preparation, see the [2026-10-18 facts](adoption/a03-2026-10-18.md),
[2026-10-22 supplement](adoption/a03-2026-10-22.md) and
[A02 trial materials](trials/a02-local/README.md). They retain their dated scope.
