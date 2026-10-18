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
The other four native project scenarios still need acceptance on the current
candidate; S4-A does not close the complete VAL-R01 or release resource matrix.
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

The package combines delivered S1/S2 work and the recorded S3-A/S3-B/S4-A status with
planned later tasks. Historical
importing/revision reports do not establish implementation status. S2 does not
change the judge drift policy in Issue #9 or complete the pending resource gates.
Resume from the assigned session and its actual
predecessor report, checking the current HEAD rather than resetting to the
reviewed commit.

## Previous plans and delivery status

The existing M1–M12 and UX plans remain historical task/acceptance records:

- [UX3: run readiness and navigation](UX3_2026-10-02.md), including its pending
  [judge policy proposal](https://github.com/EnumaElish123/ReproLLM/issues/9).
- [UX2: experiment workflow improvements](UX2_2026-10-02.md).
- [Earlier UX repairs](UX_2026-10-02.md) and
  [proposal status](ux-2026-10-02-proposals/README.md).
- [Adoption plans M9–M12](M9-M12_adoption.md) and [backlog](backlog.md).
- [Current release and delivery status](../community/roadmap.md), which remains
  the public availability index alongside [CHANGELOG.md](../../CHANGELOG.md).

Do not infer current feature availability or approval from historical sprint
dates alone.
