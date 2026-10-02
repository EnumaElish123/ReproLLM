# UX2 workflow evidence, 2026-10-02

This portable evidence covers completed local gates through UX2-T05.
The five-project init/audit and export gates passed; `session-status.json` keeps
T06 final integration/lifecycle Gate A, D-41 review and push/CI separate.

- `quality-summary.json` binds local test/coverage summaries and raw-file hashes to the six recorded commits. Per-task quality files retain command/exit/timing observations. `t04-quality-initial-failure.json` preserves the old seven-profile assertion and overlapping generator/document-read failure.
- `t01-gate-a-complete.json`, `t01-commands.json` and `t01-command-summary.json` retain all 100 commands, pins, expected/actual exits, subprocess timing and output hashes. Logical path labels replace local roots in the command ledger.
- `t01-independent-source-summary.json` records the independently read upstream YAML inventory count/hash and selected task anchors. The large inventory is intentionally omitted.
- `t01-complete-delta.json` records full normalized report comparisons, every changed rule family and independent selected-task expectations; counts alone are not the gate.
- `t01-source-snapshot.json` retains the actual pre-commit HEAD and tracked-diff/driver/oracle hashes. The recorded HEAD is S01 plus T01 working-tree changes, not the eventual T01 commit itself. This snapshot does not claim a complete inventory of then-untracked files.
- `combined-gate-a-complete.json`, `combined-commands.json`, `combined-command-summary.json` and `combined-source-snapshot.json` record the final five-project init/audit gate at b00f06c: 102 commands, clean tracked source, exact exits and timing. `combined-complete-comparisons.json` retains full comparison hashes, complete judge rule sets/predicates and threshold/details outcomes; `combined-independent-source-summary.json` records the fresh independent inventory check. Export has a separate completed matrix below.
- `t05-export-complete.json`, `t05-export-commands.json`, `t05-export-evidence.json`, `t05-export-recoveries.json` and `t05-export-source-hashes.json` retain the five-project/15-scenario export matrix, 242 expected-exit commands, full comparisons, source-derived oracles and the three corrected harness interruptions. Cached template variants are distinguished from real complete CLI exports.
- `regression-summary.json` retains red/green facts and the two historical proposal corrections.
- `schema-compatibility.json` verifies byte equality of the existing nine exported schemas through T05 and in the isolated T06 candidate. Its additional archive schema remains subject to D-41 review.

Every JSON has `schema_version: 1`. Raw logs, stdout, machine identities, absolute
local paths and the large task inventory are excluded. Hashes identify retained
local evidence; they do not make omitted raw bytes reconstructible from this bundle.
