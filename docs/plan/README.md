# Development plans

This is the entry point for selecting the current execution plan. Read
[AGENTS.md](../../AGENTS.md), the [architecture decisions](00_architecture_and_decisions.md),
the [specification](01_specification.md) and [val.md](../../val.md) before
implementing a task. A plan does not supersede frozen decisions or approve a
pending policy/schema amendment.

## Current execution package

The maintainer-approved [validation workflow optimization](validation-workflow-2026-10-13.md)
defines validation cadence for this package: focused checks per task, one complete final session
quality gate, and five-project Gate A with affected extensions. Its VOPT-01–03 tasks are a scoped
workflow supplement, not authorization to advance the product sprint or change gold answers.

The current plan is the **2026-10-03 reliability execution package v1.2**,
revised after code review at `781366e` at the maintainer's request. It adds
run-persistence redaction, shared file-read boundaries, input-capture phases and
an explicit dependency-specification prerequisite. Start at the
[package index](reliability-2026-10-03/README.md), then read the
[execution guide](reliability-2026-10-03/00_Execution_Guide.md) and the assigned
Sprint/Session document. S1-A, S1-B and S2 are delivered; S3-A
(R07-A → R07-B) is **产品与本地验收已完成**. Read the
[latest S3-A report](../dogfooding/2026-10-13-reliability-s3a/README.md) and
[scope handoff](../dogfooding/2026-10-13-reliability-s3a/s3a-handoff.md).
S3-B (R04-A → R04-B) has also passed product and local acceptance; read its
[session report](../dogfooding/2026-10-14-reliability-s3b/README.md) and
[runtime evidence handoff](../dogfooding/2026-10-14-reliability-s3b/runtime-evidence-handoff.md).
S4-A (D01 → D02) has passed product and local acceptance; read its
[session report](../dogfooding/2026-10-15-reliability-s4a/README.md) for the real
lm-eval A/B replay, snapshot fidelity repair, installed-wheel success/failure
matrix and final shared gates. S4-B's D03 publication gates are implemented;
its current acceptance and resource boundaries are recorded in the
[S4-B session report](../dogfooding/2026-10-18-reliability-s4b/README.md).
The engineering implementation does not authorize a version release.
The [A01 local evidence session](../dogfooding/2026-10-18-a01-local/README.md)
recorded 12 of 50 exact input slots in its 2026-10-18 local environment and
completed the resource-free two-path replay layer. The
[2026-10-19 resource replay](../dogfooding/2026-10-19-resource-completion/README.md)
restores 45 of 50 exact input slots on the provisioned Linux node; five original
metadata manifests remain missing. Linux H2 and all five native GPU A/B pairs,
complete capture/consumption/diff checks and 20 default export states pass at
`750270b`, closing VAL-R01 for those product bytes. That candidate's formal judge
A remains a historical capture FAIL; B was not sent. The
[R02-R snapshot follow-up](../dogfooding/2026-10-19-judge-snapshot-fix/README.md)
repairs both demonstrated defects at candidate `75d1b0`, with final local quality
and fresh five-project CPU capture/diff/export acceptance PASS. A new formal
judge A/B replay also passes complete provider, capture and semantic-pair
acceptance under a newly approved CNY 3 budget, closing VAL-R02 at `75d1b0`.
The direct judge-cap leaf is HIGH; the earlier `750270b` failure is unchanged.
The [Windows test-identifier correction](../dogfooding/2026-10-19-judge-snapshot-fix/windows-ci/README.md)
at `409a1a7` changes test metadata only; the accepted product and formal wheel
remain those of `75d1b0`. The preceding progress check confirmed
[all five CI jobs on `af8adea`](https://github.com/EnumaElish123/ReproLLM/actions/runs/39209260394)
successful on 2026-10-19. This is that commit's CI result; later commits require
their own check, and historical CI receipts remain unchanged.
HF authenticated small-file access last returned 403; original metadata and
successful model-access requirements remain independent. Follow the maintainer's
updated resource guidance in `val.md §8.3` without reinstating old artificial
GPU thresholds. Continue A01 recovery and remaining acceptance, with
policy proposals and adoption materials tracked separately. For work independent
of these resources, continue with the [A02 local trial materials](../trials/a02-local/README.md),
[A03 sourced facts and provisional narrative](../adoption/a03-2026-10-18.md), then
P-A's concrete policy proposals. Actual independent trials remain PENDING;
application form checks and any submission are separate from local drafting.
The current [R06-B dependency/lock-scope proposal](reliability-2026-10-03/proposals/R06-B/R06-B_dependency_lock_scope.md)
is **PROPOSED**, not approved or implemented. Its preparation does not change
scope, dependency gold or lock ownership; other proposals need their own decisions.
The maintainer accepted R08-A option A on 2026-10-18. Its direct judge-param
HIGH default is implemented, unreleased; read the
[P-B acceptance report](../dogfooding/2026-10-18-r08a/README.md) and
[specific decision](reliability-2026-10-03/proposals/R08-A/decision.json).
Other policy proposals and resource gates remain independent.
All five native scenarios have acceptance at `750270b`; the `75d1b0` CPU/judge
follow-up does not claim a new native GPU or H2 matrix. Successful gated access
and a complete same-candidate release matrix remain outstanding; no release is
authorized.
The [R07-A performance follow-up](../dogfooding/2026-10-13-reliability-s3a/r07a-perf-session.md)
is committed at `110087b1e416c12c25253c07365944935e986470`: 2,505 tests,
174 security tests and a fresh five-project Gate A passed. Final five-job CI
is checked against the actual pushed main HEAD in the session's final reply.

- [Copyable agent prompts](reliability-2026-10-03/AGENT_PROMPTS.md)
- [Task dependencies and gates](reliability-2026-10-03/00_Execution_Guide.md)
- [Sprint 1: persistence and effective state](reliability-2026-10-03/01_Persistence_and_State.md)
- [Sprint 2: dependency accuracy](reliability-2026-10-03/02_Dependency_Accuracy.md)
- [Sprint 3: scanning and runtime evidence](reliability-2026-10-03/03_Scan_and_Runtime_Evidence.md)
- [Sprint 4: recipe and release](reliability-2026-10-03/04_Recipe_and_Release.md)
- [Policy and compatibility decisions](reliability-2026-10-03/05_Policy_and_Compatibility.md)
- [Validation, adoption and application evidence](reliability-2026-10-03/06_Validation_and_Adoption.md)

The package records delivered S1 through S4-B engineering and the later dated
policy/resource results above alongside remaining tasks. Historical importing
and revision reports do not establish current implementation status. S2 itself
did not change judge drift policy; the later accepted R08-A implementation is
the current direct-parameter policy. Resource acceptance remains candidate-bound.
Resume from the assigned session and its actual
predecessor report, checking the current HEAD rather than resetting to the
reviewed commit.

## Previous plans and delivery status

The existing M1–M12 and UX plans remain historical task/acceptance records:

- [UX3: run readiness and navigation](UX3_2026-10-02.md), including the historical
  [judge policy proposal](https://github.com/EnumaElish123/ReproLLM/issues/9).
  Its narrow direct-parameter policy is accepted and implemented through R08-A,
  unreleased; this does not approve other policy changes.
- [UX2: experiment workflow improvements](UX2_2026-10-02.md).
- [Earlier UX repairs](UX_2026-10-02.md) and
  [proposal status](ux-2026-10-02-proposals/README.md).
- [Adoption plans M9–M12](M9-M12_adoption.md) and [backlog](backlog.md).
- [Current release and delivery status](../community/roadmap.md), which remains
  the public availability index alongside [CHANGELOG.md](../../CHANGELOG.md).

Do not infer current feature availability or approval from historical sprint
dates alone.
