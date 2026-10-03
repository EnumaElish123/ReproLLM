# Roadmap and delivery status

Updated 2026-10-03. Status is based on recorded releases and validated changes;
historical sprint dates are planning records, not a statement of availability.
The [changelog](../../CHANGELOG.md) identifies release contents. Documentation
on main can describe options not yet included in the published package.

## Released baseline

The latest recorded package release is **0.6.1**. Install with
`python -m pip install reprollm` and check `reprollm --version`.

| Capability | Release evidence |
|---|---|
| Audit, manifest, lock, runtime capture, semantic diff, export and experimental discovery | [0.5.0 Beta](../../CHANGELOG.md#050--beta--2026-09-29), with subsequent fixes |
| `audit --format github` | [0.5.1](../../CHANGELOG.md#051---2026-09-29) |
| NeurIPS / ACL / ACM export checklist mappings | [0.5.2](../../CHANGELOG.md#052---2026-09-29) |
| Framework integrations and metadata/CLI fixes | [0.6.1 release report](../dogfooding/2026-10-01-patch-0.6.1.md) |
| Standalone GitHub Action | [Published Action repository](https://github.com/EnumaElish123/reprollm-action); its `v1` tag is distributed separately |

## Implemented on main, not yet released

All six [UX2 tasks](../plan/UX2_2026-10-02.md) are integrated:

- Explicit experiment-task selection during init.
- Separate audit findings and exit policy, with compact warning output.
- Honest identity handling for `provider: other` with a declared API endpoint.
- Explicit `judge_only` experiments.
- Detailed research exports with effective values and evidence sources.
- Full project-rule inspection and reversible removal/restoration.

The last item received explicit D-41 approval and merged in
[PR #8](https://github.com/EnumaElish123/ReproLLM/pull/8), commit `b5e1317`;
[all five main CI jobs passed](https://github.com/EnumaElish123/ReproLLM/actions/runs/37023660708).
Other unreleased fixes are listed in [Unreleased](../../CHANGELOG.md#unreleased).
Use the [source-checkout instructions](../../README.md#quick-start) to try main.
Changes to the local Action source do not update its standalone published tag.

The [UX3 delivery report](../dogfooding/2026-10-03-ux3-readiness.md) records
delivery-status alignment, read-only `run --dry-run`, run listing filters and
`diff --latest-successful`. These additions passed full local quality checks and
the five-project offline Gate A and are also implemented on main, unreleased.
The report and its CI reference distinguish local validation from remote results.

## Approved next work

The [2026-10-03 reliability execution package](../plan/reliability-2026-10-03/README.md)
records four two-session engineering sprints plus policy and validation/adoption
workstreams. Its [agent prompts](../plan/reliability-2026-10-03/AGENT_PROMPTS.md)
start implementation at S1-A (R00/R01). The package is committed planning work;
its repairs remain planned, and pending policy/schema decisions retain their
separate review requirements.

The remaining [UX3 task](../plan/UX3_2026-10-02.md), T02, awaits the concrete
policy/baseline amendment in [Issue #9](https://github.com/EnumaElish123/ReproLLM/issues/9).
It proposes HIGH for direct judge parameter leaves while preserving user profile
overrides and historical MEDIUM records. The current default policy has not
changed; other UX3 tasks are delivered as recorded above.

## Future proposals

| Candidate | Boundary |
|---|---|
| Dataset content fingerprints | Requires a reviewed sampling policy and D-22 amendment |
| `rag` / `agent` profiles | Currently detected but report-only |
| `discover --paper` | Post-Beta scope under D-26 |
| SARIF output | Additional CI integration |
| Multi-stage experiments | Requires manifest/schema design |

These are unscheduled proposals, not promises for the next release.

## Pending validation

[VAL-R01, VAL-R02 and VAL-R03](../dogfooding/pending-resource-validation.md)
remain blocked on Linux/GPU resources, the formal judge input bundle and
successful HF gated-file access respectively. They describe fresh acceptance
coverage, not unimplemented features. Historical successes remain historical;
the [five-project baseline](../../val.md) governs resumption and release gates.

## Good first issues

1. `gen.stop_declared` / `prompt.few_shot_declared` negative corpora from real repositories.
2. Add `wildjailbreak` keyword to the `safety` profile detect block + snapshot.
3. New nvidia-smi fixture: 3-GPU CSV (parsing coverage).
4. FAQ entry for conda users (environment.yml + pip block).
5. `doctor` should print the effective `HF_ENDPOINT` mirror configuration.
6. Examples: add an `llm_judge` example manifest exercising judge bindings.
7. `docs/rules.md` cross-links from each rule to its spec section anchor.
8. A `--json` flag for `reprollm check_no_leaks`-style scanning inside `run` (post-run warning hook).
