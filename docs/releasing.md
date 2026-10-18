# Candidate release gates

The release workflow validates one exact commit and one build before publication.
It reuses the five-job, cross-platform quality matrix used by main and pull requests.
`scripts/release_gate.py` makes the offline preflight and final authorization
decisions; `scripts/validate_distribution.py` remains the single installed-wheel
acceptance entry. Neither script publishes or creates tags.

## Candidate chain

1. Resolve the triggering commit and candidate tag. Check the exact checkout.
2. Obtain a successful same-commit, same-repository Actions run containing the
   `release-validation` artifact. Check its API metadata before downloading it.
3. Preflight source version, matching nonempty CHANGELOG section and complete
   current-candidate validation evidence. Save the exact release notes.
4. Run the reusable full quality matrix against that commit with locked dependencies.
5. Build wheel and sdist once. Record both filenames, versions and byte hashes in
   `release-evidence/build-manifest.json`.
6. Independently install and exercise that wheel with the D02 validator. Its
   source association, import isolation, 26 command receipts and 13 semantic/package
   checks must match the candidate.
7. Revalidate the build, notes and resource evidence before uploading artifacts,
   and again after download immediately before each publishing action.

`dist` contains only the wheel and sdist. Notes, source association, preflight,
distribution result and authorization belong in the separate `release-evidence`
artifact. Publication uses PyPI OIDC and its existing protected environment.
GitHub Release consumes the preflight notes, rather than extracting new notes
after PyPI publication.

## Validation artifact contract

The artifact comes from a maintainer-provisioned validation run. For a tag-triggered
release, set repository variable `RELEASE_VALIDATION_RUN_ID` to that run's ID.
For an explicit **nonpublishing** rehearsal, select the candidate branch/commit
in `workflow_dispatch` and provide `tag` and `validation_run_id`. Dispatch events
cannot enter either publishing job, even when all checks succeed. Do not create a
real tag just to test the workflow.

The producer must execute the applicable matrix in [val.md](../val.md), using its
reviewed inputs, expectations and resource limits. It uploads `validation.json`
with integer `schema_version: 1`, `source_commit` (the candidate's full 40-character
SHA) and a `gates` array. The required set is closed and contains 28 identifiers:

| Identifier | Required instances |
|---|---|
| `gate_a:<project>` | Each of the five pinned projects: complete applicable Gate A |
| `m4_metadata:<project>` | Each project: applicable offline, online and freshness checks |
| `runtime_pair:<project>` | Each project: native bounded M5/M6 pair and complete capture/consumer checks |
| `export:<project>` | Each project's applicable captured-state export acceptance |
| `discover_collection:<project>` | Each project's offline payload/privacy acceptance |
| `api_judge` | The formal bounded API judge pair |
| `discover_live` | The opt-in bounded live discovery acceptance |
| `hf_gated` | Successful authorized access to the selected restricted files |

Project names are exactly `lm-evaluation-harness`, `FastChat`, `LlamaFactory`,
`HarmBench` and `llm-dp-finetune`. This is a compact index of the existing matrix,
not new gold or permission to run resource jobs. `m4_metadata` includes the
applicable doctor/network probes and Linux H2 cases in val.md sections 8.1–8.2.
`export` covers every applicable available state required by val.md, rather than
a single selected run. Each gate has:

```json
{
  "id": "runtime_pair:lm-evaluation-harness",
  "source_commit": "<candidate full SHA>",
  "status": "PASS",
  "inputs": [{"path": "inputs/case.json", "sha256": "<64 lowercase hex>"}],
  "report": {"path": "reports/case.json", "sha256": "<64 lowercase hex>"}
}
```

Every referenced input and report must be present inside the artifact, with exact
original byte hashes. Reports are JSON envelopes with `schema_version: 1`,
`source_commit`, `gate_id` and `status: PASS`, plus their actual commands, exits,
full expected/actual comparisons and supporting evidence. A report's PASS is a
maintainer validation attestation; the gate checks its identity and integrity,
and does not infer model execution from a JSON label. Keep payloads sanitized;
never upload credentials, machine identity, weights or restricted dataset contents.
Use small identity/expectation manifests to reference externally retained large inputs.

Missing, duplicated, unknown or non-PASS gates, absent inputs, altered bytes,
escaping paths and old commits all fail closed. An empty matrix is never success.
Retain BLOCKED in readiness reports until resources and actual acceptance exist;
do not manufacture a PASS artifact to exercise a release. Controlled synthetic
success cases belong only in the automated tests.

## Local checks and remaining readiness

The preflight, manifest and authorization subcommands have `--help`. Run the
unit/workflow regressions to verify successful and rejected decisions without a
publish token. The workflow exercises candidate quality on every normal CI push;
its dispatch path can test a real accepted bundle without publication.

The current development version has no finalized release CHANGELOG section, and
the [resource ledger](dogfooding/pending-resource-validation.md) remains authoritative:
other-project current-candidate native runs, formal paid judge replay and successful
authenticated gated-file access are still outstanding. D03 engineering acceptance
does not close those gates or authorize a version release. The staged 0.6.2 reader
bridge and 0.7.0 schema transition retain their separate publication/compatibility plan.
