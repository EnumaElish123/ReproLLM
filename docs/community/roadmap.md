# Roadmap and delivery status

Updated 2026-11-02. This page separates the published package, source features,
recorded validation and work that still needs authorization. Historical sprint
dates do not establish availability.

## Choose how to use ReproLLM

| Route | Availability | Start here |
|---|---|---|
| Published CLI | PyPI **0.6.1**, rechecked 2026-11-02 | [README installation](../../README.md#1-install) |
| Current source CLI | Development version **0.7.0**, run schema 2, unreleased | [Guided first experiment](../tutorials/first-experiment.md) |
| Agent Skill | Implemented repository preview; verified Codex Linux delivery | [Install once and use natural language](../tutorials/agent-skill.md) |
| Standalone GitHub Action | Distributed separately from this repository | [Action repository](https://github.com/EnumaElish123/reprollm-action) |

Public release sources: [PyPI](https://pypi.org/project/reprollm/) and
[GitHub releases](https://github.com/EnumaElish123/ReproLLM/releases).
The [changelog](../../CHANGELOG.md) identifies release contents. No 0.6.2/0.7.0
package, Skill-market release or MCP server was published by the latest source
development sessions. A source checkout can therefore contain features absent
from `python -m pip install reprollm`.

## Implemented on source

| Workstream | Delivered scope | Evidence |
|---|---|---|
| Reliability | 23 engineering/policy implementations, including exact dependencies, bounded incomplete-evidence conclusions and run v2 input capture | [Completion ledger](../plan/reliability-2026-10-03/07_Completion_Status.md) |
| Usability | Guided field descriptions and retries, saved experiment commands, run previews and actionable report next steps | [UX-A/UX-B plan](../plan/usability-2026-10-29/README.md) and [first-use guide](../tutorials/first-experiment.md) |
| Agent Skill v2 | SK10–SK21: isolated installation, introduction, typed access to supported commands, persistent operations, run recovery/cancellation and tutorials | [Support and remaining work](../skill-status.md) |
| Candidate/release tooling | Bounded real-framework recipe, isolated candidate-wheel validation and same-candidate release gates | [Recipe](../../examples/lm_eval_replay/README.md), [distribution](../distribution.md), [release contract](../releasing.md) |

The source also retains task selection, `judge_only`, detailed exports,
reversible project rules, run filters and recent-success comparisons. See
[Unreleased](../../CHANGELOG.md#unreleased) for the implementation history.
Publication remains a separate action.

The verified Skill delivery `b526d6e` passes all five official CI jobs and
Ubuntu 3.12's twelve required steps in
[run 41386824410](https://github.com/EnumaElish123/ReproLLM/actions/runs/41386824410).
Its fresh local gate has 6,731 passing tests and 91.989757% combined coverage.
The [correction report](../dogfooding/2026-11-02-skill-final-ci-correction/README.md)
preserves the first delivery's failed CI and the test-only corrections.
Cross-platform CI does not establish cross-platform Agent-host lifecycle support.

## Remaining acceptance and deferred work

There are no unimplemented code tasks in the accepted Skill v2 list. The
[current Skill status](../skill-status.md#remaining-work) tracks three remaining
online integration gates: authenticated metadata, live discovery and formal judge
A/B. Each needs the current candidate/input and the appropriate concrete
credential, destination and fresh-budget authorization. Historical budgets and
mock requests are not substitutes.

Claude Code adaptation and the second real-host gate are deferred by the
maintainer. The [adoption ledger](../adoption.md) now records one public,
agent-assisted CLI research project, its two issues and one merged PR, checked
2026-11-05. These share one project identity and do not establish the planned
3–5 independent Agent Skill researcher trials. The related
[trial materials](../trials/a02-local/README.md) are preparation, not
evidence of adoption. Public submission, user outreach and publication have
their own requirements and authorization.

The [final resource report](../dogfooding/2026-10-31-skill-final/README.md)
records five-project base/CPU acceptance, anonymous public HF, five native/Skill
GPU A/B pairs, installation channels and seven real Codex Linux journeys.
These retain their actual candidate/source bindings and bounded consumption
evidence. They do not guarantee paper reproduction or a complete release matrix.

The five replacement metadata manifests are already versioned, and Project C
uses public DistilGPT2. The old missing-manifest/Llama-2-access gate is
`SUPERSEDED_NOT_PASSED`, not a current prerequisite. See the
[model replacement](../dogfooding/metadata-public-model-2026-10-27/README.md)
and [resource history](../dogfooding/pending-resource-validation.md).

Before a release, freeze one candidate and complete the applicable matrix and
installed-wheel acceptance for that candidate. Follow
[val.md](../../val.md), the [validation workflow](../plan/validation-workflow-2026-10-13.md)
and the [release contract](../releasing.md). Engineering delivery is not
`FULL_ACCEPTED` or release readiness while the applicable online gates remain open.

## Future proposals

| Candidate | Boundary |
|---|---|
| MCP interface | Separate future design; not part of Skill v2 |
| Dataset content fingerprints | Requires a reviewed sampling policy and D-22 amendment |
| `rag` / `agent` profiles | Currently detected but report-only |
| `discover --paper` | Post-Beta scope under D-26 |
| SARIF output | Additional CI integration |
| Multi-stage experiments | Requires manifest/schema design |

These are unscheduled proposals. Choose subsequent engineering tasks through the
[current plan index](../plan/README.md) and [backlog](../plan/backlog.md);
use [issues](https://github.com/EnumaElish123/ReproLLM/issues) for concrete proposals.
