> **PENDING — proposal only. Not approved, implemented, filed on GitHub, or adopted as gold.**

# Spec proposal: expose evaluation, judge and privacy details in the default export

Status: PENDING MAINTAINER APPROVAL; proposal only. Do not implement new sections before the maintainer approves
the contract change. The separately prepared mapping patch fixes already incorrect
claims under the existing M10-T01 contract; it does not complete this proposal.

## Current contract and evidence

Specification §19 and M7-T01 prescribe the export's sections and their order. The
default identity currently has model/dataset/prompt tables, generation, inference
and optional training, followed by Code/Environment/Execution/Audit/Limitations.

Actual local exports of the complete openai_judge_eval example omit
evaluation.metrics=win_rate, its judge.py implementation, aggregation=mean,
evaluation.repetitions=3, and judge temperature=0.0/max_tokens=16/repetitions=1.
Only primary generation temperature=0.7/max_tokens=512 appears. The privacy
example's dataset split=test, preprocessing and privacy mechanism are also absent
from the default document. Evidence files are export-openai_judge_eval-default.md
and export-privacy_custom_params-neurips.md in this proposal's directory.

Source: src/reprollm/export/exporter.py:26,113,198;
src/reprollm/export/templates/REPRODUCIBILITY.md.j2:12,20,28,34.

## Proposed §19 amendment

Within Experiment identity, preserve models → datasets → prompts → generation →
inference → optional training, then add optional Evaluation and Privacy subsections.
Evaluation contains a metric table (name, implementation, any recorded hash/version),
aggregation, repetitions, definitions/thresholds/query budget when declared. Its
optional Judge subsection names actual model_ref/prompt_ref roles, judge parameters,
repetitions and parser. Keep judge parameters separate from primary generation.
Privacy contains threat model, mechanism and parameters, metrics and attack settings
only when present. Extend dataset rows with subset/split and declared preprocessing;
extend prompt/model details with few-shot and declared dtype/quantization/adapter
information when available.

Every value comes from the merged State, retaining D-16 effective-value precedence
and D-27 single-state semantics, including metric implementation hash/version and
model/prompt role references. Do not bypass State with current-manifest values when
an observed/locked alternative exists. Add only fields already represented by the
approved schemas and State; no new measurements are computed.

The existing whole-document redact_text gate only applies §16.2 value patterns;
it does not itself remove arbitrary absolute paths or current usernames/hostnames.
The expanded free-form privacy/parameter fields require an explicit persistence
privacy check in addition to that gate, using existing privacy helpers where
applicable without modifying core.redaction. Check keys as well as values and do
not let quoting/serialization conceal a secret-bearing key/value pair. Preserve
legal relative paths and URLs; do not normalize secret-bearing input before its
secret check. Render maps/lists and Markdown cells deterministically without
allowing embedded separators/newlines to invent checklist evidence or sections.
Write no absolute paths/identities/secrets and call no model/provider.
Missing observations must not be called verified execution: distinguish declared,
locked and observed provenance for the new evidence even when an unrelated run
exists. Absence of a run keeps the existing no-run statement.
Checklist mapping must cite actual rendered values or explicitly say not covered.

## Acceptance criteria

- Both generation 0.7/512 and judge 0.0/16 appear under distinct labelled contexts.
- A nondefault judge.model_ref=grader renders the grader role, not hardcoded judge.
- Metrics, implementations, repetitions, split, preprocessing and privacy survive
  export with and without a lock/run; missing fields remain honestly absent.
- A run-observed value overrides its manifest declaration in the export.
- A selected older run keeps its own snapshots/observations for new detail rows;
  do not silently describe current later configuration as that run's evidence.
  Audit summary scope is a separate existing issue, not silently redefined here.
- Same input produces identical bytes, relative paths and no secrets/machine identity.
- Fake absolute paths, identities, secret patterns and secret-bearing map keys in
  new free-form fields are removed safely; Unicode, zero/false values, relative
  paths and normal URL values remain accurate. Nested map order and Markdown
  escaping are deterministic. Do not read real credentials for these tests.
- Review all three existing default snapshots and checklist examples deliberately;
  do not derive new fixture expectations solely from generated output.

Six local failing prototype regressions were prepared as `test_export_research_details.py`; that temporary test file is not included in this bundle or delivered repository tests. They describe this proposal, not completed implementation. No persisted schema or frozen
decision changes are necessary; the §19/M7 ordered-section contract must be updated.
