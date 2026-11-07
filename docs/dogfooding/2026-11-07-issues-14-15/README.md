# Issue #14 / #15 delivery

Date: 2026-11-07. Synced baseline: `dfb72eda57abb47cc0fc972982e770c6199c5bd2`.
Final local candidate: `5079c0c5cbd8c6a03abe267e05026afae67fce5e`.

## Changes and authorization

- ISSUE-14 (`859116a`): a runnable stored-answer `judge_only` tutorial, navigation,
  strict verdict parsing and selected-run export guidance. Its CPU fixture uses
  canned responses and performs no inference. Independent review caught empty
  responses being excluded from the invalid-output denominator; the final
  recipe admits empty/whitespace responses as invalid and retains input errors.
- ISSUE-15 (`b4d6c71`): add `.pth` to the existing local directory suffix set.
  The maintainer explicitly accepted option A, its exact specification patch
  and compatibility costs. The original proposal remains a PROPOSED snapshot;
  the committed acceptance sidecar records the subsequent decision.

The ISSUE-15 product diff is one suffix-set line. Recursive traversal, case-insensitive
selection, opaque streaming hashes, total-size threshold, metadata revision
priority, explicit-file and empty-inventory behavior remain under the existing
contract. Relocking can change sizes/hashes or cross the aggregate 100 MiB
threshold. Fixed metadata retains revision authority; weight-only default drift
remains MEDIUM, and a changed hashed revision remains HIGH. Old locks/runs are
readable and are not migrated. `lock --check` still checks declarations.

The existing-contract schema prerequisite at `5079c0c` writes canonical UTF-8/LF
bytes on Windows and strengthens freshness to byte comparison. Its regression
produces one old failure/four controls, then five passes. Schema definitions and
all ten committed exports remain unchanged; the extra five-project export matrix
compares all 50 generated files with the original Git blobs.

No schema definitions, dependencies, engine/redaction policy, severity table, historical
fixtures/gold or package version changed. No GPU, paid API or release was used.

## Test-first evidence

The 38 new regressions (26 core, 12 CLI) produced 19 FAIL / 19 passing controls
on the unchanged baseline, with no errors/skips. All 38 pass after implementation.
The affected suite passes 425 tests; it overlaps 26 new core cases and is not an
additional disjoint total. Final source hashes bind the unchanged test inputs.

The final tutorial rehearsal executes 31 commands: 15 main commands / 23 checks,
five large-input commands / seven checks, and 11 parser control cases. The
1,048,901-byte input has `snapshot: null`, independently matching hash/size and
unchanged pre/post-child bytes. All three selected-run export templates refer
to the captured run. These are CPU capture checks, not real judge acceptance.

## Final validation

| Gate | Actual result |
|---|---|
| Final complete local quality | 30/30 commands PASS on `5079c0c`; 1234.13 s wall / 1234.09 s command time |
| Full pytest | 6,552 passed, six platform skips, 213 deselected under the Windows CI marker filter |
| Combined coverage | 85.107148% (required >=85%); redaction branches 100% |
| Five-project Gate A | PASS; 263 baseline/candidate command receipts / 526 raw streams verified; 102 import/environment identities |
| Complete semantic comparisons | 25 JSON, 90 exact bytes, five command-cwd-bound console relocations; 4,033 literal/source assertions per candidate comparison |
| Extra schema matrix | Five clean pinned projects, 35 commands, all 50 exported files byte-equal to original Git schema blobs |

The five pins and formal gold remain exactly those in [val.md](../../../val.md).
All 38 new `.pth` cases pass in final pytest. Only `cli/schema.py` and
`lock/local_resolver.py` differ in the 148-file product payload from the synced baseline.

The first complete comparison retained a failure on `A-init-stdout`: its first
`Created .../reprollm.yaml` prefix names separate baseline/candidate working
copies. A reviewed adapter binds each prefix to that exact command receipt's
cwd, compares every remaining byte, and rejects wrong paths, extra replacements
or changed business text (one positive / three negative controls). Five such
console relocations are recorded separately from the 90 byte-identical checks.
The frozen original checker, literal gold, JSON fields, hints and persisted
paths are unchanged; all original comparison outputs remain retained.

Platform skips, recorded verbatim from final JUnit:

| Test | Reason |
|---|---|
| `cli.test_audit_normalization::test_symlinked_invocation_normalizes` | creating symlinks needs privileges on Windows |
| `cli.test_scan_diagnostics::test_untrusted_warning_prefix_cannot_become_default_coverage[syntax]` | POSIX filename includes colon/control character |
| `cli.test_scan_diagnostics::test_untrusted_warning_prefix_cannot_become_default_coverage[external-read]` | POSIX filename includes colon/control character |
| `core.test_manifest_scaffold::test_force_success_preserves_existing_file_modes` | POSIX permission bits are unavailable on Windows |
| `skills.test_bootstrap::test_console_probe_requires_executable_permission` | POSIX executable permission |
| `skills.test_skill_run::test_control_fifo_is_refused_without_a_writer` | Named pipes unavailable |

Replay the focused public regressions with:

```bash
uv run pytest -q tests/unit/lock/test_local_pth_inventory.py tests/unit/cli/test_local_pth_inventory.py tests/unit/schemas/test_json_schema_export.py
```

[Machine-readable acceptance](session-checks.json) and [private-original hash references](source-index.json) retain the actual scopes.


## Retained failures and environment correction

The first complete pytest attempt is retained as 54 FAIL / 6,383 PASS /
121 SKIP / 213 deselected, taking 1,727.30 seconds. Later quality commands did
not execute after pytest failed. Trace-based classification found 34 Windows
path-length failures, 17 missing Bash/GNU command failures and three missing
symbolic-link privilege failures, all outside the new `.pth` cases.

An unchanged-source PATH A/B gives 17 FAIL then 17 PASS. A shorter user-Temp
attempt still fails all 34 path cases, with existing parents and failing paths
263–273 characters long; this attempt is also retained. The final environment
uses a fresh short D-drive validation directory, existing Git tools in the
process PATH and a validation token able to create real symbolic links. All
54 original failures then pass, with real file/directory symlink probes.
These environment corrections leave product/tests, global PATH, long-path policy,
developer mode and existing ACLs unchanged. A second full attempt passed
6,552 tests / six platform skips, then failed at schema byte freshness: ten
Windows CRLF exports differed from canonical LF files. The JSON values were
identical. That attempt is retained. The separate schema writer correction and
byte-level test above precede the new final complete quality gate.
This does not claim arbitrary-length Windows installation paths are supported.

Five pinned checkouts were reacquired. Initial permission/long-copy preparation
failures and partial copies remain preserved. The accepted external copies
match 17,919 source/Git files by bytes and hash. Initial workspace copies were
preparation only; formal five-project inputs are external and clean.

Baseline native commands total 132 with 264 raw streams. Their 148 source files
match Git blobs at the baseline, and all 51 import/environment receipts bind to
that isolated source. The original baseline runner was reconstructed after two
candidate-guard additions, and its bytes match the already recorded original
hash; this is recorded as reconstruction, not an earlier frozen copy.

The independent comparison tool first rejected its own LF expectation for
Windows diagnostic stderr. The original attempt remains; the corrected literal
CRLF expectation was reviewed without modifying product outputs. Its independent
baseline checks and six negative controls pass. Synthetic complete expectations
were frozen before candidate output was read.

## Evidence and remaining scope

Machine-readable checks and source-index files record hashes of retained private
originals. Public hash references do not contain or independently replay those
private bodies; the committed regressions and tutorial are executable locally.
No current output was copied into formal gold. No pins or formal gold changed.

This ordinary issue session does not activate milestone/release Gate B. Historical
VAL-R01/R02 and VAL-R03 keep their original candidate bindings. The five formal
metadata inputs are available; superseded missing manifests/Llama-2 authorization
are not current blockers. Current Skill authenticated metadata, live discovery
and formal judge integrations remain BLOCKED_NOT_AUTHORIZED; Claude Code remains
deferred, independent Skill trials unobserved, and A03 identity/submission pending.
A release requires its own same-candidate resource acceptance.

Exact final delivery-head CI and remote/main equality are verified after this
report commit is pushed, avoiding a report/commit self-reference cycle. The
verified CI link and issue closure are recorded in the delivery response.
