# Development plans

This is the entry point for selecting the current execution plan. Read
[AGENTS.md](../../AGENTS.md), the [architecture decisions](00_architecture_and_decisions.md),
the [specification](01_specification.md) and [val.md](../../val.md) before
implementing a task. A plan does not supersede frozen decisions or approve a
pending policy/schema amendment.

## Current execution package

The next planned iteration is the [2026-10-30 Agent Skill extension v2](skill-2026-10-30/README.md):
automatic isolated installation, capability introduction and user-directed access to the full
supported CLI, including actual experiment runs, online resolution, discovery and rule management.
This delivery is a **plan only**; SK10–SK21 are NOT_STARTED across six batches SK2-A–SK2-F.
The next implementation batch is **SK2-A (SK10 → SK11)** when implementation is requested.
The unimplemented v1 SK01–SK05 are SUPERSEDED, not completed. See the
[acceptance matrix](skill-2026-10-30/acceptance.md),
[assessment](../research/2026-10-30-agent-interfaces-assessment.md),
[v1 delivery record](../dogfooding/2026-10-30-skill-plan.md) and
[v2 revision record](../dogfooding/2026-10-30-skill-plan-v2.md).
Concrete runtime/paid/data-sharing authorization still applies at use time; MCP and release are outside this plan.

The active usability iteration is [2026-10-29](usability-2026-10-29/README.md). UX-A is delivered with all five official CI jobs successful on `8ea80e8`. UX-B is implemented at `48caea2`: guided field descriptions, local retries, accurate remaining declarations and a [four-command first-use tutorial](../tutorials/first-experiment.md). All 24 local checks, 5,474 tests and fresh five-project acceptance (280 command receipts / 233 checks) pass, with independent receipt review. See the [UX-B report](../dogfooding/2026-10-30-usability-uxb/README.md). All five usability development tasks have local acceptance; exact final-delivery-head CI is checked after the report commit and push. External first-use feedback remains unobserved. The reliability records below remain historical.

The accepted R07-C closing contract is implemented at `7e57809`; final test inputs
are `3157ae7`. All 24 local quality checks, 5,295 tests and fresh five-project
230 records / 184 checks pass with independent receipt review. See the
[27-task completion ledger](reliability-2026-10-03/07_Completion_Status.md) and
[final session report](../dogfooding/2026-10-29-r07c-final-coverage/README.md).
All 23 engineering/policy implementations and applicable local acceptance are complete;
exact final-delivery-head CI is verified separately after this report commit and push.
A01 candidate evidence, external A02 feedback, A03 identity/submission and release
readiness remain separate. Earlier dated OPEN/PROPOSED/pending paragraphs below
are historical; the specifically accepted finite section12.3.16 now closes the
R07-C development boundary. No release or external submission is authorized.


The existing-contract Makefile correction at `28de938` is independently reviewed.
The closing proposal's [supplement](reliability-2026-10-03/proposals/R07-C/final-coverage/README.md)
mechanically carries that correction, and corrects the forward LF export passed
count from 9 to 8. Original policy patches remain frozen and unapplied.
The first quality attempt was interrupted for the review finding; new final acceptance is pending.


2026-10-29 final R07-C closure is now prepared as a
[concrete six-rule proposal](reliability-2026-10-03/proposals/R07-C/final-coverage/README.md),
with exact implementation/specification/forward-gold patches and a 69-rule disposition table.
It remains PROPOSED; future policy execution is zero and the specific decision is pending.
Independent existing-contract fixes at `f980e36` and `60d2087` handle task-YAML
composition recursion and standalone shell-comment continuation. Their focused
regressions pass; shared final quality/five-project/CI acceptance is pending.
Wider R07-C is not closed by preparation, and no release is authorized.


The maintainer specifically accepted D-I A and both exact patches on 2026-10-29.
P-B at `3aadb9a` records actually reached supported requirements include targets
rejected by the existing candidate check, with a separate typed tuple and a rule
branch after all existing credit and skip priorities. The
[session report](../dogfooding/2026-10-29-r07c-filtered-include-pb/README.md)
records 39 new CLI passes, frozen-old sensitivity of 20 FAIL/19 PASS, 688 existing
passes, native WARNING/promoted-CRITICAL gate pairs from 1 to 0, final24 quality
and fresh five-project acceptance. The old 225 receipts remain separate from
five new public dependency collectors which independently verify empty tuples;
all 230 outer receipts and 184 checks pass with no unexplained gold delta.
The [specific acceptance](reliability-2026-10-03/proposals/R07-C/filtered-include/decision-accepted.json)
includes repository-wide conservative influence and unrelated/nonexistent-target
costs. The P-A snapshots below retain their original bytes. Exact delivery-head
CI is checked separately after push; wider R07-C remains OPEN, with no release.

The next bounded R07-C batch is the 2026-10-28 D-I
[filtered-include P-A](reliability-2026-10-03/proposals/R07-C/filtered-include/README.md).
Its exact specification/implementation patches remain PROPOSED and unapplied.
Twenty-four current-policy cases and 27 CLI calls document the captured-view
boundary; five-project source inventory has no supported include edges, so its
zero-delta forecast does not validate the new policy. Specific acceptance must
precede P-B. See the [preparation report](../dogfooding/2026-10-28-r07c-filtered-include-pa.md).
The preceding exact `e3aa653` delivery has all five CI jobs and Ubuntu3.12's twelve
required steps successful. Wider R07-C remains OPEN; this preparation grants no release.

The 2026-10-28 configuration-depth follow-up at `9903627` follows all five
successful exact-`a8806aa` predecessor CI jobs and Ubuntu3.12's twelve required steps.
It replaces recursive configuration-key traversal with live iterator frames, preserving
DFS key/value order, active ancestor back-edge handling and repeated acyclic aliases.
The [session report](../dogfooding/2026-10-28-r07c-config-depth/README.md)
records a 2,033-byte, depth-1,000 JSON replay decoded successfully before the old walker
failed with CLI exit3; the new walker completes with exit0. It records 13 new CLI
cases, 190 focused passes, final24 quality and fresh all-five local acceptance:
180 base/affected commands plus five task-list calls and forty separate Git guards.
CLI comparisons establish canonical keyword outputs, not container visit counts;
iterator order, repeated alias handling and exceptional cleanup have bounded structural
and targeted fixture evidence. The original decoder handling, key-only scans, budgets,
rules, engine, schema, dependencies and version remain unchanged. Exact delivery-head CI
is checked separately after push. Wider R07-C and decoder/alias resource boundaries
remain open; this bounded repair authorizes no release. Historical text stays intact.

The 2026-10-28 YAML object-cycle follow-up at `ccf9baf` follows all five
successful exact-`347eae7` predecessor CI jobs and Ubuntu3.12's twelve required steps.
It cuts only back edges to active dict/list ancestors while collecting configuration
keys, retaining healthy keys and the original DFS repetitions/order of acyclic aliases.
The [session report](../dogfooding/2026-10-28-r07c-yaml-config-cycles/README.md)
records a 46-byte native YAML replay with old CLI exit3 to new0, 18 new CLI cases,
177 focused passes, final24 quality and fresh all-five local acceptance: the original
180 base/affected commands plus five task-list calls and forty separate Git guards.
CLI comparisons establish canonical keyword outputs, not container visit counts;
the repeated-alias traversal claim rests on the source structure review.
Existing decoding/parser handling, key-only scans, budgets, rules, engine, schema
and version stay unchanged. Exact delivery-head CI is checked separately after push.
Wider R07-C and decoder/alias resource boundaries require independent review;
this bounded repair authorizes no release. Historical entries below retain their text.

The 2026-10-28 InspectAI follow-up at `3c21749` routes its independent Python
parser's `RecursionError` to the existing identical task-name fallback. It retains
the regex grammar, safe inventory, explicit selection and metric-review contract.
The [session report](../dogfooding/2026-10-28-r07c-inspect-parser-recursion/README.md)
records 18 new CLI cases, 59 focused passes, native-proof limits, final24 quality,
fresh five-project base/affected acceptance and five separate complete task lists.
Before implementation, all five exact-`960a1fd` predecessor CI jobs and Ubuntu3.12's
twelve required steps were confirmed successful. Final delivery-head CI is separate.
This repairs an existing fallback boundary; no new policy/schema/engine contract
or release is accepted. Wider R07-C remains OPEN; the YAML config object-cycle
candidate remains untested for a future independent batch.

The 2026-10-28 R07-C follow-up repairs primary-Python parser recursion failures
under the existing §13 selected-but-unparsed contract and §§12.3.1–2 consumers.
Product commit `40c92d2` adds only a three-line `RecursionError` handler;
the specification, rules, engine, scan limits and default diagnostic visibility
retain their contracts. Final local quality, fresh all-five Gate A and affected
consumers pass on that candidate. See the
[session report](../dogfooding/2026-10-28-r07c-python-parser-recursion/README.md)
for 15 new CLI regressions, native-proof limits, complete comparisons and
separate exact-delivery-head CI. This is an existing-contract crash repair,
not acceptance of another OPEN policy. Wider R07-C remains OPEN.
The preceding D-M-CS delivery has
[all five exact-`d512301` CI jobs](https://github.com/EnumaElish123/ReproLLM/actions/runs/40492274192)
successful; its original snapshots retain their historical identities.

The maintainer specifically
[accepted D-M-CS A and both exact patches](reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/decision-accepted.json)
on 2026-10-27. P-B at `1607ee0` adds only the internal retained-name Conda
specifier cause at the existing placeholder assignment. The test-only `bd74330`
follow-up aligns two cross-manager first-cause expectations; runtime/spec bytes
remain identical. Final local quality, fresh all-five Gate A and affected consumers
pass at `bd74330`; see the [P-B report](../dogfooding/2026-10-27-r07c-conda-retained-pb/README.md)
for full comparisons, retained first-attempt failure, compatibility costs and
separate exact-delivery-head CI. The original
[P-A packet](reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/README.md)
and its PROPOSED snapshot retain all 29 original files. Wider R07-C stays OPEN;
this adds no grammar support, resource replay or release authorization.
The preceding D-M-CE delivery and Windows test correction are complete:
[all five exact-`22e3dbc` CI jobs](https://github.com/EnumaElish123/ReproLLM/actions/runs/40462446381)
passed. Historical PROPOSED snapshots with separate acceptance records are not new blockers.

The maintainer specifically [accepted D-M-CE A and both exact patches](reliability-2026-10-03/proposals/R07-C/conda-omissions/decision-accepted.json)
on 2026-10-27, including repository-wide SKIP and isolated exit-code costs.
P-B at `c9ee53d` adds only the internal `unparsed_conda` fact at the two existing
native Conda omission returns. The [P-B report](../dogfooding/2026-10-27-r07c-conda-omissions-pb/README.md)
tracks final quality, fresh five-project acceptance and exact delivery-head CI.
The [P-A packet](reliability-2026-10-03/proposals/R07-C/conda-omissions/README.md)
and its PROPOSED snapshot retain their original bytes; current-source observations
and source-only zero applicability remain distinct from P-B product validation.
Wider R07-C remains OPEN; this does not authorize a release.

The later 2026-10-27 maintainer instruction replaces the inaccessible Llama-2
metadata model with public DistilGPT2. The current five-case catalog is
[M4-META-PUBLIC-20261027](../dogfooding/metadata-public-model-2026-10-27/README.md)
under `val.md §8.1.2`; the other four manifests retain their bytes. The old
mandatory gated-success branch is superseded, without claiming gated access.
Fresh five-project/15-mode metadata replay, 51 product commands and full
comparisons pass at product candidate `00c2392`; current VAL-R03 is PASS under
the revised public-model contract. Release readiness and wider R07-C remain separate.

The maintainer directed a new formal metadata baseline on 2026-10-27. The
[M4-META-20261027 input bundle](../dogfooding/metadata-formal-2026-10-27/README.md)
now supplies all five version-controlled manifests for future M4 validation,
superseding the unavailable original files under `val.md §8.1.1`.
Old input hashes/results remain historical; the later public-model replacement
above defines the current VAL-R03 target. Input replacement does not authorize a release.

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

## Pipfile D-M-PF P-B（2026-10-24）

维护者[已接受A、精确补丁与全仓成本](reliability-2026-10-03/proposals/R07-C/pipfile-version/decision-accepted.json)。产品`ba1415b`仅在原Pipfile两节loop新增6行typed fact，保留声明/信用/先因/helper False及line fallback/barrier。
[P-B报告](../dogfooding/2026-10-24-r07c-pipfile-version-pb/README.md)记录267新增回归、8旧预期同步、首轮5旧断言失败及重验、最终质量、fresh五项目Gate A/受影响与38完整记录，适用本地门均PASS；精确最终HEAD五项CI在交付核验。原P-A/PROPOSED快照保持，其他R07-C、资源与实际反馈仍OPEN；不发布版本。

## 当前候选资源补验（2026-10-26）

维护者要求先补齐已开发部分的验证。[本轮报告](../dogfooding/2026-10-26-validation-completion/README.md)
在 `6afe8f4` 完成新质量门、五项目 Gate A/受影响消费者、匿名 supplementary H2、
十次原生 GPU 运行/五配对/二十 export、原输入正式 judge A/B 与 current-input discover 接受。
DP epsilon 8→4 和 direct judge cap 均按已接受的前瞻政策独立验为 HIGH。
VAL-R01/R02 的新通过绑定本候选；历史候选和失败记录保持。
VAL-R03 仍缺五份原始 metadata manifest，认证 200 后限定小文件仍 403；维护者已要求先完成其余检查。
本轮只补验与更新证据，没有推进下一项产品开发，也未发布版本；更广 R07-C、独立试用与申请条件继续分别登记。
