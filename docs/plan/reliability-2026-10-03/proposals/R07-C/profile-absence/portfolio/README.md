# R07-C profile-absence follow-up: five-project prospective expectations

Status: **DESIGN_EXPECTATION_NOT_EXECUTED**. These are read-only design and source-identity
checks, not a new Gate A or a claim that a proposed implementation has passed. No product,
test, network, GPU or provider command was run; no gold was changed.

The historical execution candidate is `b5564f0c7b94db132053cbe97abd8e824403a8bc`.
Its complete fresh results were stored by `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`;
the current design input is `bb98e67c6e108822c62842d738f42af2eda871e4`.
[Product identity](product-source-identity.json) verifies the entire 143-file product set
against both Git commits and current bytes: 142 files are byte-identical, and the sole
change is the separately accepted R08-B `diff/drift_severity.yaml` table. The audit,
scanner, detection, profile loading, init and export product bytes are unchanged.

[Design expectations](design-expectations.json) reference complete existing L0 reports,
facts, L1 reports, manifests, three initialized files per project, and default exports.
Every referenced repository file is checked against current and original-storage Git
blobs; existing independent normalized L1 and export expectations still match their
historical actual outputs. Those complete sources stay at their recorded repository
locations; they are not copied into new actual/expected report trees here.

| Project | Candidate / selected / parsed / limit | Historical L1 profile conclusion | Proposed ordinary L0 / L1 / default export delta |
|---|---|---|---|
| lm-evaluation-harness | 816 / 500 / 500 / 500 | SKIPPED / INFO, old empty-result veto | none |
| FastChat | 148 / 148 / 148 / 500 | PASS | none |
| LlamaFactory | 311 / 311 / 311 / 500 | PASS | none |
| HarmBench | 123 / 123 / 121 / 500 | SKIPPED / INFO, old empty-result veto | none |
| llm-dp-finetune | 46 / 46 / 46 / 500 | PASS | none |

All ordinary L0 inputs have no declared manifest profiles, execute at Level 0 and contain
no `exec.profile_detection_mismatch` finding. In each historical initialized L1 report,
every declared non-core profile already has an actual detection entry under the existing
any-confidence presence test. There is no missing declared profile and no high-confidence
shipped profile outside the resolved closure. The proposed absence-only branch therefore
cannot be entered by these five ordinary cases. Keeping the existing empty-result policy
means the two historical SKIPPED cases do not become PASS via a new sufficient certificate.
Full findings, summaries, detection/hints, paths, diagnostics, initialized artifacts and
export bytes are consequently predicted unchanged, under that precise scope only.

The counts are independently reconstructed from complete historical `analysis_files`,
`python_paths` and explicit parse/read failure diagnostics using the byte-identical
scanner/pyscan contract. They describe the captured primary-Python view, not full listing,
dependency, framework, config-key or all-signal completeness. HarmBench retains its two
syntax-error diagnostics. Counts alone are not the evidence: the complete L0 and L1
profile entries and all paths/lines/notes are retained by reference and in the
[detection witness source map](detection-witness-source-map.json). Upstream witnesses
are bound to exact public Git objects at the five pins; directory evidence is bound to
the full tracked-path inventory hash and matching paths. This is no fresh checkout
cleanliness or identity test. The DP L1 privacy detection additionally includes a key in
the captured generated manifest, so L0 and L1 evidence are deliberately separate.

[Synthetic acceptance design](synthetic-acceptance-design.json) lists the necessary
cases that the ordinary five-project inputs do not exercise. After a concrete policy
is accepted and implemented, run the fresh applicable quality/Gate A/consumer matrix;
old successful outputs remain oracle inputs rather than new-candidate PASS receipts.
No native execution, provider or release result is inferred.

[Source index](source-index.json), [read-only verification](verification.json) and
[preparation qualification](preparation-qualification.json) retain exact hashes and
boundaries, including the corrected helper wrapper assumption. No historical result,
input, existing decision or report has been rewritten.
