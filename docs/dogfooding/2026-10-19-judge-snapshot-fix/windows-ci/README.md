# R02-R Windows test-identifier correction

This test-only follow-up corrects the cross-platform test definition introduced
with the snapshot repair. `409a1a707c5da1f23d06f890cd88e2399002da20`
adds one explicit `ids` line to three existing parser stress cases. Their source
inputs, signatures and assertion bodies are unchanged. The accepted product
remains `75d1b065e9f0e3eeafa8e480e195a2a2ddbe95b5`; all 143 package payload
files, schemas, dependencies, examples and CI configuration retain exact bytes.
See the [original product/provider acceptance](../README.md).

## Observed failure and reproduced cause

The initial main push `4ada2d17394e969a790797d039b354da847d6c93` passes the
three Linux jobs and macOS. Its Windows Test output shows two `E` markers near
the line ending at 88%, then reaches 100% and stops displaying further output
after the `ERRORS` heading. The maintainer supplied the screenshot and confirmed
that no exception details followed. Its original image hash is retained; the
image and temporary page data are not copied into this bundle.
The original Windows traceback was unavailable. That run is never reported as
a five-job PASS.

Local collection with the Windows marker filter identifies exactly one oversized
node identifier: 1,048,684 characters, at 87.24% of the collected sequence. Pytest
uses that identifier in `PYTEST_CURRENT_TEST` before both setup and teardown.
Those values are 1,048,692 and 1,048,695 characters. Windows limits an environment
variable value to 32,767 characters, according to the
[official SetEnvironmentVariable documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setenvironmentvariable).

A throwaway plugin applies only that documented value-length boundary to the
real pytest environment setter and records lengths/stages, never values.
Before the change, the original three cases produce **2 passed, 2 errors**:
setup and teardown both reject the oversized `PYTEST_CURRENT_TEST`. After adding
short case names, the exact same run produces **3 passed** with no rejection;
the maximum observed environment value is 128 characters. This is an explicitly
labelled platform-limit simulation, not an invented Windows traceback.
The hypothesis that huge error-report names also explain the stalled output is
consistent with the screenshot, but is not separately established by a trace.

The correction uses `unfinished-string`, `excessive-depth` and `excessive-size`.
All three original stress cases remain enabled, including the 1 MiB input.
The Windows-filter local collection retains all 3,002 tests; only those three
node IDs change. The maximum ID decreases from 1,048,684 to 261 characters,
and IDs over the Windows limit decrease from one to zero. No platform, test,
assertion or security case is skipped.

## Verification and scope

- The platform-limit RED/GREEN, collection and byte-change proofs are retained
  through the [source manifest](source-files.json), with full commands, exit
  statuses, elapsed times and output hashes.
- The Python parser module passes 107 tests; all three affected parser/capture
  modules pass 159 tests. Ruff lint and format checks pass.
- The [new final quality gate](quality/summary.json) passes all 24 checks on
  `409a1a7`: 3,004 tests, 2 slow deselected, 94.02% overall
  coverage, 100% core redaction branches, 345 security tests, lint/format/types,
  schemas, generated documents, examples, wheel build and isolated installation;
  574.512 s wall time. Inputs remain byte-identical before/after.
- The rebuilt wheel is byte-identical to the original formal wheel, and its
  complete 143-file product payload is checked
  independently. No product, gold, profile, packaging, input or resource output
  changes accompany this follow-up.

The [validation workflow §3](../../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义)
requires a new complete final quality gate even for a test-only correction, so
the earlier local gate does not substitute for these final test inputs.
Product Gate A and resource execution for this corrective follow-up are
**NOT_APPLICABLE — test metadata only**. The earlier five-project CPU/native
and paid-provider evidence retains its original product candidate and dates;
it is not relabelled as a new resource run. The two paid judge requests and
CNY 0.002836 total estimate remain unchanged.

The initial focused work ran in the main checkout, whose product already
matched the isolated checkout. The single added line was then transferred to
the isolated worktree and removed from main before the final gate. The three
pre-existing user changes retain their original hashes and are excluded from
all task commits. Final quality runs on the clean, committed isolated candidate.


The sharing helper initially rejected a literal dummy credential URL in its own
negative self-check because the sharing marker matched the credential detector
again. The failed helper and partial copy remain hash-bound. The runtime value
of that negative case is unchanged; constructing it from separate source
strings and qualifying the helper's own sharing copy resolves the packaging
failure. The final copy is independently audited against the same immutable
quality outputs; no product check or resource execution is repeated for this
report-only sharing correction.

The portable supplement binds 168 source selections and 17 hash-only originals.
Its initial 84-file copy excludes this README and the later closing audit and
credential scan. The [independent audit](independent-packaging-audit.json) checks
all source/retained hashes and sizes. The [closing checks](closure-checks.json)
verify report links and product identity. The closing
[credential scan](credential-scan.json) includes final task files; no credential
value, prefix, length or credential hash is recorded.

The normal push concurrency setting supersedes the obsolete CI run. All five
jobs must pass on the actual final pushed main commit; that result is checked
in the session's final reply. No API completion, GPU job, HF attempt or release
is performed by this follow-up.
