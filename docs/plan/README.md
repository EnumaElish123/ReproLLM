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
The [2026-10-20 validation follow-up](../dogfooding/2026-10-20-validation-followup/README.md)
completes fresh quality, five-project Gate A, supplementary Linux H2 and all ten
native GPU children/five semantic pairs/20 export states at `948d164`. A newly
accepted current-input discover case completes one real request and reviewed
candidate acceptance. Historical input hashes/gold and formal judge acceptance
at `75d1b0` remain separate; no paid judge replay is claimed. Original metadata
manifests remain missing and the fresh authenticated HF small-file preflight
still returns 403. Release readiness remains outstanding.

The maintainer accepted [R06-B option A](reliability-2026-10-03/proposals/R06-B/decision.json)
on 2026-10-20, after reviewing the concrete proposal and specification patch.
P-B implements bounded format-lock origin credit while retaining repository-wide
existential exact declarations and presence semantics. Follow its
[session report](../dogfooding/2026-10-20-r06b/README.md) for final candidate,
quality, fresh Gate A and affected consumer acceptance. The original
[proposal snapshot](reliability-2026-10-03/proposals/R06-B/R06-B_dependency_lock_scope.md)
retains its preparation-time state. The maintainer has now explicitly accepted
[R07-C partial A and its concrete specification/D-41 patches](reliability-2026-10-03/proposals/R07-C/decision-accepted.json).
P-B implements only the two-rule empty-result veto for known primary-Python gaps
or unavailable internal coverage. Follow the
[P-B session report](../dogfooding/2026-10-20-r07c-pb/README.md) for the exact candidate
and validation status. The [P-A packet](reliability-2026-10-03/proposals/R07-C/R07-C_incomplete_scan_conclusions.md)
and its original PROPOSED decision remain preparation-time snapshots;
[P-A acceptance checks](../dogfooding/2026-10-20-r07c-pa/README.md) are distinct from P-B product gates.
Wider R07-C mixed-evidence work remains OPEN. The maintainer has now
[accepted R08-B A4 and its concrete specification/prospective-gold patches](reliability-2026-10-03/proposals/R08-B/decision-accepted.json).
P-B promotes only the three exact privacy parameter paths and
`training.params.num_train_epochs` to default HIGH. Follow the
[P-B session report](../dogfooding/2026-10-20-r08b-pb/README.md) for the exact candidate
and validation status. The original [P-A proposal](reliability-2026-10-03/proposals/R08-B/R08-B_exact_parameter_risk.md),
PROPOSED decision and [conditional evidence report](../dogfooding/2026-10-20-r08b-pa/README.md)
retain their preparation-time state. Historical resource results and gold remain
bound to their original candidates.
The maintainer has now [specifically accepted the R07-C profile-absence continuation](reliability-2026-10-03/proposals/R07-C/profile-absence/decision-accepted.json).
P-B applies only its per-profile SKIP for declared-but-undetected outcomes under
incomplete/unavailable primary-Python analysis, preserving positive high-confidence
mismatches. Follow its [P-B report](../dogfooding/2026-10-21-r07c-profile-pb/README.md)
for the exact candidate and current validation status. The original [P-A proposal](reliability-2026-10-03/proposals/R07-C/profile-absence/R07-C_profile_absence.md),
PROPOSED record and [P-A report](../dogfooding/2026-10-21-r07c-profile-pa/README.md)
retain their preparation-time state. Broader R07-C remains OPEN.

The maintainer has [specifically accepted R07-C D-F](reliability-2026-10-03/proposals/R07-C/format-lock-read/decision-accepted.json).
P-B handles known captured associated format-lock body read/decoder failures independently of Python coverage;
exact/qualified credit and existing D-L remain. Follow its [P-B report](../dogfooding/2026-10-21-r07c-lock-read-pb/README.md)
for implementation, completed local quality/five-project/affected gates and separate final-head CI status. The [P-A proposal](reliability-2026-10-03/proposals/R07-C/format-lock-read/R07-C_associated_format_lock_failures.md)
and original PROPOSED snapshot remain immutable; broader R07-C stays OPEN.

The maintainer has [specifically accepted R07-C D-S](reliability-2026-10-03/proposals/R07-C/format-lock-structure/decision-accepted.json).
P-B implements only the bounded associated-lock extraction-structure policy, retaining partial positive credit;
its [P-B report](../dogfooding/2026-10-21-r07c-lock-structure-pb/README.md) records implementation and current validation status.
The original [P-A report](../dogfooding/2026-10-21-r07c-lock-structure-pa/README.md), PROPOSED snapshot and concrete patches remain historical preparation evidence.
Broader R07-C remains OPEN.

The maintainer has [specifically accepted R07-C D-M](reliability-2026-10-03/proposals/R07-C/declaration-read/decision-accepted.json).
P-B handles known captured declaration-body failures, including actual requirements body-read failures;
its [P-B report](../dogfooding/2026-10-21-r07c-declaration-read-pb/README.md) records implementation and current validation status.
The original [P-A proposal](reliability-2026-10-03/proposals/R07-C/declaration-read/R07-C_declaration_body_failures.md),
PROPOSED snapshot and [P-A evidence](../dogfooding/2026-10-21-r07c-declaration-read-pa/README.md) remain historical preparation records.
Broader R07-C remains OPEN.

The accepted R07-C D-L slice implements the [dependency format-lock policy](reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/R07-C_dependency_lock_credit.md).
Its [P-A report](../dogfooding/2026-10-21-r07c-dependency-pa/README.md) preserves the proposal and conditional design.
The maintainer has [specifically accepted D-L](reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/decision-accepted.json);
follow its [P-B report](../dogfooding/2026-10-21-r07c-dependency-pb/README.md) for the implementation, completed local quality/five-project gates and separate final-head CI status.
Broader R07-C remains OPEN.

The maintainer has [specifically accepted D-M-S option A and its specification patch](reliability-2026-10-03/proposals/R07-C/declaration-structure/decision-accepted.json).
P-B adds the bounded decoded declaration container/member checks while retaining
partial declarations, positive credit and existing D-F/D-S/D-L/D-M priority.
Follow its [P-B report](../dogfooding/2026-10-22-r07c-declaration-structure-pb/README.md)
for implementation and final validation status. The original
[P-A proposal](reliability-2026-10-03/proposals/R07-C/declaration-structure/R07-C_declaration_structure.md),
PROPOSED decision and [preparation report](../dogfooding/2026-10-22-r07c-declaration-structure-pa.md)
remain historical snapshots. Individual package-value/string grammar, requirements
graphs and wider R07-C remain OPEN; no release is authorized.

The maintainer explicitly delegated the R07-C D-G A/B adjudication; the agent
[chose A and the exact patch](reliability-2026-10-03/proposals/R07-C/requirements-depth/decision-accepted.json),
including its repository-wide conservative SKIP and exit-code costs. Follow the
[P-B report](../dogfooding/2026-10-22-r07c-requirements-depth-pb/README.md): implementation at `d823f90`
has passed final local quality, fresh five-project Gate A and the affected D-G consumers.
Exact final pushed-head CI is checked separately at delivery.
The original [P-A report](../dogfooding/2026-10-22-r07c-requirements-depth-pa.md),
PROPOSED snapshot and raw observations remain historical. A separate
[ordering evidence correction](reliability-2026-10-03/proposals/R07-C/requirements-depth/decision-evidence/README.md)
preserves those bytes and adds actual deep-first/reverse-order observations.
This specific delegated choice does not approve other OPEN R07-C policies or a release.

R08-A option A remains implemented and unreleased; read its
[P-B acceptance report](../dogfooding/2026-10-18-r08a/README.md) and
[specific decision](reliability-2026-10-03/proposals/R08-A/decision.json).
For work independent of outstanding resources, the
[A02 local trial materials](../trials/a02-local/README.md) and
[A03 historical sourced facts](../adoption/a03-2026-10-18.md) remain available.
The [2026-10-22 A03 supplement](../adoption/a03-2026-10-22.md) records dated facts,
read-only public-form matching and measured draft lengths, with separate preparation
and verified PB delivery identities. Conditional form behavior and server validation
remain untested; independent trials are PENDING and no application is submitted.
No release is authorized. Resource results stay candidate-bound.
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

The maintainer specifically [accepted D-C A and its exact specification patch](reliability-2026-10-03/proposals/R07-C/requirements-comments/decision-accepted.json).
The bounded ordinary requirements comment fallback is implemented at `0f8c4df`;
the session started on 2026-10-22 and completed its local acceptance on 2026-10-23.
The [P-B report](../dogfooding/2026-10-22-r07c-requirements-comments-pb/README.md) records
141 new cases, the full quality gate, fresh five-project Gate A, affected graph/verbose
checks, complete CLI replay, unchanged original checkouts and independent evidence readback.
The exact final pushed head's five-job CI and Linux exact schema check are independently verified at delivery. The [P-A report](../dogfooding/2026-10-22-r07c-requirements-comments-pa.md)
and original PROPOSED packet retain their historical observations; broader R07-C policy,
resource blockers, independent adoption feedback and release remain separately bounded.


The maintainer directed the specific D-M-P P-B next step after receiving option A,
its exact patch and conservative costs; the [acceptance record](reliability-2026-10-03/proposals/R07-C/pep621-strings/decision-accepted.json)
records that contextual authorization without inventing a verbatim acceptance quote.
P-B implements only the two PEP 621 parse-failure sites at `26a4d30`, retaining
partial declarations, credit and existing D-M priority. The [P-B report](../dogfooding/2026-10-23-r07c-pep621-strings-pb/README.md)
records 170 new cases, corrected final quality, fresh five-project Gate A and
affected checks, 24 complete internal records, final identities and independent archive readback.
All applicable local gates pass; exact pushed-head five-job CI is checked separately at delivery.
The [P-A packet](reliability-2026-10-03/proposals/R07-C/pep621-strings/README.md),
PROPOSED decision and original observations remain immutable historical snapshots.
The maintainer has [specifically accepted D-M-E A and its exact patch](reliability-2026-10-03/proposals/R07-C/environment-pip/decision-accepted.json), including repository-wide conservative costs.
P-B at `a221e9d` records only failures of the existing stripped nonblank embedded-pip call,
preserving partial declarations, prior causes, credit and priorities. Its
[P-B report](../dogfooding/2026-10-23-r07c-environment-pip-pb/README.md) records 154 new cases,
final local quality, fresh five-project Gate A, affected checks, 27 full internal records and archive readback, all PASS.
Exact pushed-head five-job CI is checked separately at delivery. The original
[P-A packet](reliability-2026-10-03/proposals/R07-C/environment-pip/README.md), PROPOSED snapshot and observations remain immutable preparation evidence.
The next independent P-A may investigate Poetry's explicit dependency-version extraction boundary;
no new policy is implemented by that suggestion. Wider R07-C, resource, adoption and release work remain OPEN.

The maintainer [accepted D-M-V A and its exact specification patch](reliability-2026-10-03/proposals/R07-C/poetry-version/decision-accepted.json), including repository-wide conservative costs.
P-B at `b18ed19` records only the explicit non-string version-field fact in the existing Poetry loop; declarations, credit, line fallbacks and prior causes remain.
The [P-B report](../dogfooding/2026-10-23-r07c-poetry-version-pb/README.md) records171 new regressions, final quality, fresh five-project Gate A/affected checks and35 full internal records, all applicable local gates PASS.
Exact final-head five-job CI is checked separately at delivery. The [original P-A](reliability-2026-10-03/proposals/R07-C/poetry-version/README.md), PROPOSED decision and observations retain historical bytes.
A separate Pipfile P-A may be investigated next; that suggestion approves no new policy. Wider R07-C, resources and adoption remain OPEN. No release.

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

## Pipfile 显式 version 独立 P-A（2026-10-24）

[当前提案](reliability-2026-10-03/proposals/R07-C/pipfile-version/README.md)及[报告](../dogfooding/2026-10-24-r07c-pipfile-version-pa.md)已准备：38例当前行为、fresh五项目来源、官方类型边界、A/B、精确未应用补丁及45组未来验收。状态PROPOSED，推荐A；Poetry批准不扩展，候选执行0。下一步先裁决具体A/补丁及全仓warning→SKIP、孤立exit1→0成本，再P-B先RED实施。文稿会话不冒充Gate A；资源/采用仍OPEN，不发布版本。
