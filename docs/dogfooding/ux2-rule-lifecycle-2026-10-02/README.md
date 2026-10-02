# Rule lifecycle evidence, 2026-10-02

All JSON wrappers have schema_version 1. This bundle records completed local
quality and five-project lifecycle Gate A; D-41 review, remote delivery/CI and merge
are recorded at the pre-PR report stage in delivery-status.json. The associated PR
tracks subsequent remote outcomes. Main 1451032 CI has separately passed all five
jobs; main-ci-success.json records the final GitHub page observation. Main baseline CI is separately confirmed green for all five jobs in main-ci-success.json; this does not claim candidate/PR CI success.

- quality.json and quality-summary.json retain complete local quality commands,
  actual exits/timing, coverage summary and omitted raw-source hashes.
- implementation-provenance.json records actual source HEAD/tracked diff and every
  product/template/exported-schema file hash, including then-untracked product files.
- schema-compatibility.json verifies nine unchanged schemas, one added archive v1,
  and unchanged core engine/redaction against the first-five-task main baseline.
- commands.json and matrix-summary.json retain all gate commands, expected/actual
  exits, pins, output hashes and summed subprocess time.
- Each PROJECT-lifecycle.json retains the full original/archive/restored rule,
  field-by-field empty differences, all bindings and five current-file/hash snapshots.
- independent-lifecycle-fixture.json is authored from the product contract rather
  than copied from tool output. independent-source-summary.json confirms the fixed
  upstream sources without copying their large task inventory.
- evidence-source-ledger.json preserves input-file hashes; raw stdout/stderr,
  logs, full inventories, absolute machine paths and identities are not copied.

Raw omitted contents cannot be reconstructed from the recorded hashes. Archive
state derives from current rules; an archive alone is not a completed-removal log.
