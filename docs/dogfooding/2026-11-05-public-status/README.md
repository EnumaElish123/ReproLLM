# Public status maintenance

Date: 2026-11-05 (Asia/Shanghai). Baseline:
`f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`.
Scope: the maintainer's three requests under the
[public-status plan](../../plan/public-status-2026-11-05.md).

## PUB01: adoption evidence

Task commit: `33b57b1`.

The [adoption ledger](../../adoption.md) now links PI-01 to the pinned public
case report, committed manifest, Issues #11/#13 and merged PR #12. Both issues
and the PR are by `Mosionca2`; PR #12 merged as `ad8b2c7`, and #13's clarification
is `f7bd2ad`. All belong to one research project. The full current issue
inventory was read: two non-owner-account issues and one non-owner-account PR,
all created in November. They are not three independent adopters, and #12 is
not counted again as an issue.

Public reports explicitly describe agent assistance and maintainer help.
Account identity does not prove personal or institutional independence. The
roadmap and Skill page now distinguish this real CLI case from the planned
independent Skill trial cohort. No research run is repeated or scientific
conclusion certified by this documentation update. Unmeasured downloads,
dependents and paper artifacts are labeled as such; historical September data
retain their dated meaning. The initial document checks resolve 184 local links,
and all nine pre-existing user files retain their hashes.

## PUB02: GitHub About

Task commit: `ea585e9`.

The [repository API](https://api.github.com/repos/EnumaElish123/ReproLLM) originally
returned `description: null` and `topics: []`. The maintainer explicitly requested
the following values, applied through the existing owner GitHub CLI login:

```console
gh repo edit EnumaElish123/ReproLLM --description 'LLM experiment reproducibility toolkit' --add-topic llm --add-topic reproducibility --add-topic research-tools
```

The command exits 0. A fresh API readback confirms description
`LLM experiment reproducibility toolkit` and topics `llm`, `reproducibility`,
`research-tools`. The GitHub connector supports repository reads but exposes no
repository metadata mutation tool, so the existing owner CLI is used for this
authorized update. This changes GitHub presentation metadata, not package or
product behavior.

## PUB03: published-version verification

The [dated public release check](../../adoption/2026-11-05-release-check.md)
records the live PyPI JSON, GitHub release, pip output and artifact identity.
Latest published version is 0.6.1 in all reviewed sources. Both artifacts are
not yanked. The downloaded wheel's SHA-256 matches PyPI, and its ZIP metadata
confirms 0.6.1, Python >=3.10 and the existing Alpha classifier. No package was
installed or executed. Source remains unreleased 0.7.0.

The first pip query used the local default Python 3.9.13 and exited 1 with no
compatible distribution; this result is retained rather than replaced by the
successful queries. Explicit compatibility targets 3.10 and 3.12 both exit 0
and list 0.6.1 as latest. The older search snapshot's cause is not established;
the actual live Alpha classifier is distinct from the version availability.
See the [machine-readable observations](observations.json).

## Applicable validation

This is documentation and specifically requested repository metadata work.
The local gate checks links, primary-source consistency, case deduplication,
metadata readback, package-index observations, public content and the hashes
of nine pre-existing user files. Product source, tests, package metadata,
dependencies, schemas, profiles and scientific gold are outside the change.
Generated CLI/rules/profiles/quickstart inputs are unaffected.

Final local checks pass: 194 local Markdown links resolve; the public receipt
passes `scripts/check_no_leaks.py`; one-project/two-issue/one-merged-PR accounting,
the requested About values and the three version observations agree. The first
Python-3.9 failure and both successful supported-Python queries are retained.
All nine user-file hashes match the starting snapshot. A comparison to the
baseline confirms zero changes to product, Skill, test, script, example, schema,
CI, dependency or packaging inputs; `git diff --check` is clean. PUB03 and this
final report are delivered in the third task commit; its exact SHA/CI are
reported after push rather than introducing a self-referencing report commit.

The full local product gate and five-project Gates A/B are
`NOT_APPLICABLE_DOCUMENTATION_AND_REPOSITORY_METADATA` under the
[validation workflow §3](../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义),
not PASS. Task commits are provisional until final documentation acceptance.
The exact pushed delivery head's CI is checked after push rather than asserted
in advance in this report.
