> **PENDING — proposal only. Not approved, implemented, filed on GitHub, or adopted as gold.**

# Spec proposal: an explicit profile for judging pre-generated outputs

Status: PENDING MAINTAINER APPROVAL; proposal only, not implemented. This option
supersedes part of frozen D-06 through a new decision entry chosen by the maintainer.

## Current behavior and existing compatible workaround

llm_judge extends evaluation, which extends inference, which extends implicit core.
Thus models.primary.id, general generation parameters and inference.backend remain
required even when the command only judges existing answer pairs. This follows the
current §6.1/§12.4 contract; it must not be silently weakened as a bug fix.

An existing valid role arrangement is models.primary=<judge identity> and
evaluation.judge.model_ref=primary. The judge rules already honour this reference;
primary need not mean a second model. It still requires the inherited generation
fields, so it does not solve the separate-parameter requirement.

Sources: profiles/llm_judge.yaml:5, evaluation.yaml:5, inference.yaml:5;
rules/model.py:188; rules/judge.py:87; D-05,D-06,D-08,D-13.

## Proposed explicit option

Add one built-in profile named judge_only. Extend core directly; explicitly select
the following exact §6.1 policy without inheriting inference. This is the complete
recommended row for review, not a request that the maintainer design the rule set:

| Property | Proposed value |
|---|---|
| name / extends | `judge_only` / `[core]` |
| additional dataset rules | `dataset.declared`, `dataset.preprocessing_declared`, `dataset.sampling_seed_declared`, `dataset.subset_declared` |
| additional evaluation rules | `eval.metrics_declared`, `eval.metric_implementation_referenced`, `eval.aggregation_declared`, `eval.repetitions_declared` |
| additional judge rules | `judge.model_declared`, `judge.prompt_declared`, `judge.prompt_hashed`, `judge.params_declared`, `judge.pinnability_recorded`, `judge.repetitions_declared` |
| required_fields | `datasets.eval.id`, `evaluation.metrics`, `models.judge.id`, `prompts.judge.path`, `evaluation.judge.params.temperature`, `evaluation.judge.params.max_tokens` |
| severity_overrides | `dataset.declared: CRITICAL`, `dataset.revision_pinned: CRITICAL`, `dataset.sampling_seed_declared: CRITICAL`, `eval.metrics_declared: CRITICAL`, `exec.seed_declared: CRITICAL` |
| drift_overrides | `evaluation.judge.*: HIGH` |
| detect | empty imports/dependencies/keywords/files; no automatic selection |

All implicit core rules remain selected. `gen.seed_declared` and other inference
rules are not newly selected or overridden. Dataset revision/file hashing and
prompt file/hash checks remain inherited from core. The evaluation severity
overrides above are deliberate; missing metrics/data are not downgraded simply
because the profile no longer inherits evaluation. Existing default severities
apply to every other selected rule. Use `datasets.eval` to identify the actual
pre-generated answer/input collection, not an invented fresh generation dataset.
Require a referenced judge model/prompt and evaluation/judge parameters and metrics.
Keep llm_judge/evaluation/inference and their existing default behavior unchanged.
Do not infer judge_only from repository-wide keywords; the researcher explicitly
selects it for the chosen command/experiment.

Keep model.primary_declared selected by implicit core. Define the narrow exception
predicate exactly: `judge_only` is explicitly declared (manifest/--profiles), the
resolved closure is a subset of `{core, judge_only, privacy}`, and none of those
resolved profiles is replaced by a `.reprollm/profiles/<name>.yaml` user override.
Only when this predicate holds is primary_declared skipped. Thus inference and
finetuning both prevent the exception; so do any other/custom profiles or applicable
user overrides. Inference combinations retain existing primary/generation checks;
finetuning retains existing primary/training checks, without new generation checks.
This conservative custom-profile boundary keeps all existing custom primary
requirements; extension of the exception to custom profiles is deferred.
This is a declared
experiment-policy choice, not verification that a command actually only judges:
static profile selection cannot guarantee the purpose of an arbitrary command.
All explicitly approved judge/evaluation critical checks remain active.

Apply the exact same predicate in init. When true, remove only core's
`models.primary.id` from the scaffold's effective required_fields; keep the table's
judge fields and every other union field. Do not pre-fill a primary model detection
into the active model block in this mode; retain candidate evidence for author
review. When false, ordinary required-field union and current initialization stay
unchanged. Manual model_ref/prompt_ref may name any existing role; init defaults to
judge, with the existing schema reference checks intact.
Task inventory/metric selection follows the separately reviewed UX-T03 option if
approved, otherwise the current M11 prefill contract; this profile proposal does
not silently approve or replace that separate policy.

Within the same narrow exception only, `judge.model_declared` fails CRITICAL if the
referenced role is absent OR its id is absent/empty/whitespace-only;
`judge.prompt_declared` fails CRITICAL if the referenced role is absent OR both
path and text are absent. Explicit empty inline text is still declared content;
existing path validation, file existence and hash rules handle paths. Elsewhere
these two rules preserve their released presence behavior. This scoped refinement
keeps their identity-declaration purpose and existing IDs, and must be included in
the approved §12.9 wording before implementation. A missing reference in a present
evaluation.judge remains a §3 V-05 validation error (exit2), not an invented audit
finding; existing empty role containers can still load so the new identity checks
can explain missing intent. No schema relaxation is proposed.

Recommended complete example: select only judge_only, declare models.judge.id,
prompts.judge.path or text, datasets.eval identity/files, evaluation.metrics and
judge.params.temperature/max_tokens, plus execution.seed. Optional privacy may be
combined under the same explicit predicate. Absence of model primary, general
generation and inference blocks is allowed; other selected checks still apply.

## Acceptance criteria

- A complete explicit judge-only experiment with models.judge and judge parameters,
  but no primary/general generation/inference block, has no unrelated CRITICAL.
- Missing judge model/prompt/parameters or evaluation evidence still fails.
- llm_judge alone and existing seven-profile fixtures keep their existing results.
- Combining judge_only with inference/evaluation/llm_judge/safety retains their
  primary/generation requirements; combining it with finetuning retains primary
  and training requirements. Include custom-profile composition; no broad severity
  lowering or suppression is introduced.
- Detection never silently chooses the exemption; profiles show documents closure,
  applicability and required field intent. Keep every existing rule ID.
- Core-only/legacy seven-profile and custom override cases preserve their full
  reports. Pure judge_only and shipped judge_only+privacy omit primary scaffolding;
  adding finetuning, inference, a custom profile or applicable override restores it.
- Missing referenced id and undeclared prompt content are critical under the
  exception; invalid zero max_tokens/repetitions keep existing validation, while
  zero temperature stays valid. Source-authored positive/negative fixtures define
  complete rule sets/severities before any gold update; no five-pin refresh occurs.

Architecture §6 requires a new superseding decision: propose eight built-in
profiles, obtain maintainer approval, then add the new D-nn selected by that review
and mark D-06 superseded by it. Do not rewrite D-06 silently or invent a frozen ID
in this pending proposal. Update §6.1, §3.2, §12.4, profile/CLI fixture expectations
and relevant docs together; check schema freshness rather than assume a schema
diff. The new profile itself does not require a
persisted schema change. Any proposal adding experiment.mode instead would touch a
schema and require D-41 review. A maintainer can instead choose only to document the
existing primary-as-judge setup and defer the explicit exemption.

The recommended option can use the existing declared_profiles/resolved_profiles
AuditContext plus profile override paths, and the existing init resolver. It does
not need a new engine field or persisted schema; proposed edits are confined to
profile policy, model/judge applicability, scaffold and tests. If implementation
instead changes core.engine, core.redaction or any schema, mark D-41 explicitly and
obtain that review rather than treating this proposal as approval for those files.
