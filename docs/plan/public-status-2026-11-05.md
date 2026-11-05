# Public evidence and repository metadata follow-up

Date: 2026-11-05. Baseline: `f7bd2ad7686ff603f8508d9eedfb919d35edb8e9`.
The maintainer assigned these three tasks, in order:

| Task | Change | Acceptance |
|---|---|---|
| PUB01 | Refresh adoption metrics and link the Privacy_Injection case, Issues #11/#13 and merged PR #12 | Pin public research evidence and a committed manifest; count one project, two issue artifacts and one merged contribution; distinguish non-owner accounts from independent adopters; replace the October placeholder with an explicit unmeasured status |
| PUB02 | Fill GitHub About | Set description to `LLM experiment reproducibility toolkit` and add `llm`, `reproducibility`, `research-tools`; read the values back from the repository API |
| PUB03 | Reconcile public release availability | Query official PyPI JSON, pip's public index and GitHub releases; record Python compatibility and the actual Alpha classifier; verify the published wheel metadata without installing it |

Use one Conventional Commit per task. Existing dated evidence remains historical;
current adoption and availability pages link the new observations. In particular,
one agent-assisted CLI research project does not satisfy the planned independent
Agent Skill trial cohort. Do not infer distinct people, paper reproduction or
upstream adoption from account names, stars, internal fixtures or repeated runs.

This session changes documentation and the specifically requested GitHub About
fields. Preserve all nine existing user files. Do not modify product code,
dependencies, package classifiers, formal schemas, tests or scientific gold;
do not publish a release, install packages or run research workloads.

Under the [validation workflow §3](validation-workflow-2026-10-13.md#3-执行频率唯一权威定义),
the applicable local gate is source/content consistency, local links, safe public
evidence, protected-file hashes and remote metadata readback. Generated product
documentation is unaffected. Full local product quality and five-project Gates
A/B are `NOT_APPLICABLE_DOCUMENTATION_AND_REPOSITORY_METADATA`, not PASS.
Record task commits, observations and exceptions in the
[session report](../dogfooding/2026-11-05-public-status/README.md), push the three
commits together to main, then verify the exact delivery commit's official CI.
