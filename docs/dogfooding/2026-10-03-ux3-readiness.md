# Run readiness and navigation, 2026-10-03

Development began on 2026-10-02 under the approved
[UX3 plan](../plan/UX3_2026-10-02.md) and resumed on 2026-10-03.
This report covers UX3-T01, T03 and T04. UX3-T02 remains pending a concrete
maintainer decision on [spec Issue #9](https://github.com/EnumaElish123/ReproLLM/issues/9).
No judge-severity/default-profile/gold change is claimed by this delivery.

## Delivered behavior

| Task | Commit | Result |
|---|---|---|
| UX3-T01 | `5b546df` | Separate released 0.6.1, implemented unreleased UX2, planned improvements and blocked resource gates. |
| UX3-T03 | `59918e3` | Read-only `run --dry-run`: explicit bindings, input capture eligibility, required environment presence and local lock freshness. |
| UX3-T04 | `c1cf91e` | Exact name/status/outcome/limit filters; `diff --latest-successful` selects a fixed older/newer pair of completed exit-0 records. |

The preview executes no subprocess, makes no request, creates no run ID and
writes no artifact. Required documents and inspected inputs have bounded reads;
forbidden file contents and bound values are withheld. Missing bindings or a
stale/missing lock remain visible advisories. This is not runtime evidence or a
prediction that the experiment will succeed.

Listing preserves its seven-field JSON and default table. Filters apply before
limits, and full-scan corruption warnings remain visible. Shortcut comparison
retains the existing profiles and thresholds and reports full selected IDs;
selected invalid snapshots fail instead of silently substituting an older run.
Neither process success nor shortcut selection proves comparability.

## Tests first and compatibility

T03 added 62 cases, including bounded reads, privacy, forbidden input reads,
unsafe symlinks, capture policy, absent bindings and no side effects. T04 added
68 cases covering the full outcome matrix, exact/empty/null labels, stable UTC
ordering, all-record warnings, fixed selection, cwd ID-path shadowing, one-read
eligibility and historical snapshots. Before T04 implementation, 52 new behavior
cases failed and 16 compatibility cases passed; all 68 subsequently passed.
The combined existing/new navigation and diff regression set passed 294 cases.
Independent source and harness reviews found no blocking issue.

All ten persisted JSON schemas remain byte-identical to `b5e1317`.
`core/engine.py` and `core/redaction.py` are unchanged. Redaction line and branch
coverage remains 100%. No dependency, user-code/config, run-writer, provider or
release change is included. Generated CLI help was reviewed and refreshed.

| Task | Full pytest | Pytest seconds | Result |
|---|---|---:|---|
| T01 | 1,797 passed | 105.35 | PASS |
| T03 | 1,859 passed | 105.93 | PASS |
| T04 | 1,927 passed | 103.73 | PASS |

All task quality gates include Ruff check/format, strict mypy, schema freshness,
all four generated-document checks and whitespace checks. The existing three
skips, two deselections and unknown `slow` mark warning remain recorded; they
are not new successful test claims.

## Five-project Gate A

All five targets match their fixed SHAs/origins and remain clean. **261 commands and 410 complete comparisons passed**, with 59.393s summed subprocess time (not session wall time). The source inventory hash is `a76a320226e653b81852b944c02f04600a31a0412c30976a7ac3479f61e94d0e` at exact code commit `c1cf91e01627f3dd5a49c8561f508ca43a755fef`.

| Repository | Fixed SHA | Commands | Subprocess seconds |
|---|---|---:|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 52 | 22.429 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 52 | 8.804 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 52 | 9.329 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 52 | 10.612 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 52 | 8.207 |

Each complete Level 0 JSON report, verbose diagnostics and detection-hint set
matches the previous independently reviewed baseline, excluding only
`generated_at`. This preserves every rule/status, dependency/profile set, path,
line and scan-limit diagnostic. `--fail-on never` exiting 0 does not claim all
findings passed; LlamaFactory's tracked `.env.local` remains CRITICAL.

Changed commands ran in disposable clones with independently authored synthetic
inputs and records. The preview cases cover missing/fresh/stale locks, bindings,
policy options, overlarge/binary/forbidden files and unavailable declarations.
Listing cases compare full rows and byte output for exact labels, all statuses,
outcomes, combined selectors and limits. Diff cases compare the complete report,
full selected IDs, repeated bytes, explicit/prefix inputs, thresholds, selection
errors, cwd shadows and selected-snapshot failure. External hooks on preflight/navigation reject writes,
subprocesses, network and reading forbidden synthetic fixtures; L0 retains its
required read-only Git inspection. Filesystem
metadata before/after also matches. These fixtures do not execute upstream
experiments or substitute for real-model acceptance.

The [evidence bundle](ux3-2026-10-03/README.md) retains every exact command,
expected/actual exit, target SHA, elapsed time, complete semantic comparison,
source/contract/oracle hashes and quality/compatibility records. Large raw
filesystem metadata and disposable clones stay outside the repository; their
comparison digests are preserved. No pin or gold answer was updated, and there
are no unexplained baseline deltas.

## Pending policy, resources and delivery

T02 is held under AGENTS.md §7.6 and val.md §9 because changing direct judge
parameters from MEDIUM to HIGH also changes the formal cap expectation. Issue #9
proposes one narrow default row, preserving one-segment wildcards and user
profile overrides; historical MEDIUM execution records remain historical.
Continuing unaffected tasks follows the approved UX3 plan's explicit dependency
exception. A pending question or elapsed time is not approval.

[VAL-R01/R02/R03](pending-resource-validation.md) remain blocked on previously
recorded Linux/GPU resources, the reviewed formal judge input bundle and
successful selected-model HF gated-file access. This ordinary development
session does not activate a milestone/release Gate B or use credentials, paid
APIs or GPU resources. Package 0.6.1 and the separately published Action tag are
unchanged; these improvements are on main and unreleased.

Implementation commit `c1cf91e01627f3dd5a49c8561f508ca43a755fef` was pushed to main. Its [GitHub CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/37088414830) completed successfully on all five jobs: Linux/Python 3.10, 3.11 and 3.12; macOS/Python 3.12; Windows/Python 3.12. [Exact-head CI evidence](ux3-2026-10-03/code-ci-success.json) records all job conclusions and URLs. This confirms the implementation commit, separately from local quality. The report/status-only follow-up preserves the validated product inventory; [current main CI](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml?query=branch%3Amain) tracks its delivery.
