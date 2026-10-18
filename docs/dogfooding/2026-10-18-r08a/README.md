# P-B / R08-A — direct judge parameter policy

Session date: 2026-10-18. Starting clean main:
`a2005b46f18c4bb30ecdca1053815e699ebf487f`, already current after `git pull --ff-only`.
The maintainer explicitly accepted option A in the current conversation; see
the [decision and accepted patch hashes](../../plan/reliability-2026-10-03/proposals/R08-A/decision.json).

## Scope and focused regressions

The product change adds one default `evaluation.judge.params.*: HIGH` row before
the broader judge row. Single-segment matching, first-match order, user LOW/NONE
overrides, schemas and profile definitions stay unchanged. This is an unreleased
source change; no version, tag or package publication is introduced.

Tests precede implementation. The [unit receipt](regressions-unit.json) records
10 expected failures / 189 passes under the old policy and 199 passes after the
change. The [CLI receipt](regressions-cli.json) records 7 expected failures /
12 passes, then all 19 new CLI cases passing. Adjacent CLI regressions add
18 passes and one platform symlink skip in the focused ordinary-token run.
The final quality run uses the established Windows administrator test context.

CLI cases cover changed/added/removed caps, two inherited judge profiles,
default/LOW/NONE, actual standard-library child receipts, complete drift,
thresholds/filters, deterministic JSON, self-diff and historical byte preservation.
Only the target leaf can be HIGH; config/code hashes cannot conceal a lost leaf.
The legacy case is explicitly synthetic, not a claimed historical provider run.

The specification and changelog reflect the accepted default. `val.md` gains
only a prospective [§8.4.1](../../../val.md#841-prospective-r08-a-judge-policy-supplement).
Historical MEDIUM judge/DP records, frozen P-A material (except its current
decision), existing fixture snapshots and validation pins remain unchanged.
No redaction, engine, schema, resolver or profile-loader change is required.

## Final session acceptance

Product task commit: `0b36780edaaa6150693dc9dd7330e5ba429a1398`.
Local acceptance: **PASS**. The final pushed main commit's five-job CI is checked
after the documentation/evidence closure commit; this snapshot does not reuse
an earlier commit's CI or claim a release-ready resource matrix.

The [final quality receipt](quality-summary.json) binds this exact product commit
to [498 frozen input hashes](quality-inputs.json). All **21 commands exit 0**,
with 636.641 seconds wall time. This is one final full run, after focused GREEN;
there is no full-run failure or discarded full-run result in this session.

| Final quality check | Actual result |
|---|---|
| Complete pytest | 2,839 passed, 4 skipped, 4 deselected; zero failures |
| Coverage | 93.76416347581464% overall; redaction 59/59 lines and 24/24 branches, 100% |
| Security | 203 passed, 2 skipped; no failure |
| Ruff / format / mypy | All pass |
| Locked dependency sync / generated documentation | All pass; quickstart preflight precedes full pytest |
| Examples and source self-audit | All applicable example audit/lock checks and self-audit exit 0 |
| Schema exports | Exact set of ten; original Windows exports differ from Git only by CRLF |
| Final input inventory | All 498 hashes unchanged after the run |

[Schema comparison](schema-comparison.json) retains expected, original and
canonical-LF hashes. Raw equality is **false**; only CRLF→LF equality is true,
under the existing S4-B/D02 policy. No source or expected schema is edited.
The pushed commit's Linux CI must still pass exact-byte schema freshness.

[Environment preflight](environment-preflight.json) records the current Windows
administrator test token, supported Git, identical Python/python3 aliases and
six passing prerequisite cases. [Platform skips](platform-skips.json) list every
full-suite skip: one symlink-normalization prerequisite, two POSIX-only filename
cases and one POSIX permission-bit case. Slow/Linux-only exclusions follow the
existing Windows marker policy. These are explicit skips, not passed cases.

[Static acceptance checks](acceptance-checks.json) prove that removing the one
new policy row recovers the old table byte for byte; original val §8.4, all nine
frozen P-A artifacts, protected implementation files and prior evidence retain
their bytes. [Peer review](peer-review.json) found no must-fix issue. This is a
second agent within the author-operated session, not an external user's trial.

The fresh [five-project Gate A](gate-a/README.md) follows this quality PASS:
five L0/facts pairs, ten complete JSON gold comparisons with zero differences,
and all 15 isolated diff cases pass. All five original checkouts retain their
exact pins, origins and clean status; the 498 quality inputs remain unchanged.

The final successful attempt records **380 commands**: 130 product collection /
diff commands, ten JSON comparison commands, 30 original-checkout identity checks
and 210 disposable-clone Git preparation commands. Product commands comprise ten
base collections, 30 standard-library captures and 90 diff invocations. Wall time
is 176.055400 seconds; command time summed across parallel work is 275.893365
seconds. These are separate measurements.

An earlier attempt passed all five base checks and ten comparisons, then failed
in the private harness before any diff product invocation: isolated empty Git
templates do not create `.git/info`, which the harness assumed existed. Its 185
command records and failed expansion are retained, not overwritten. After an
explicit directory-creation fix and four pure-Git preparation regressions, a new
complete attempt ran in fresh disposable clones. No product, test, oracle or
quality input changed, so this harness-only repair did not invalidate the final
product quality run. See [attempt history](gate-a/attempts.json).

Public evidence includes complete comparison results and the 15 unfiltered diff
reports. Original base L0/facts streams are retained once in private local logs,
with their hashes in the receipts; the public package does not duplicate those
large streams. Raw diff/compare bytes retain their original line endings and EOF.
The [document closure checks](document-checks.json) and [checksums](SHA256SUMS)
cover the public package. Earlier Gate A success is not reused as a fresh pass.

## Delta and implementation notes

Against A01's last local baseline, pytest adds 39 passing cases (20 policy unit
cases plus 19 CLI cases); rounded total coverage, 100% redaction coverage and
203 passing security cases remain unchanged. This compares recorded counts,
not performance across different test inputs or machine load.

The only intended semantic delta is direct judge-param drift: the isolated
default cap case changes from MEDIUM / HIGH-gate exit 0 to HIGH / exit 1.
LOW/NONE overrides keep HIGH-gate exit 0; hidden argv MEDIUM still triggers an
explicit MEDIUM gate. Deeper params, privacy/training paths and default no-gate
exit behavior retain their contracts. Old diff reports stay MEDIUM while a new
comparison of supported old runs uses the new policy.

No fixture or snapshot regeneration is needed: the four existing diff fixture
groups' nine changes do not match the new pattern. The CLI matrix is in a new
focused `test_judge_param_policy.py` file rather than expanding the existing
`test_diff.py`; adjacent tests are retained and run. Prospective gold comes from
the accepted proposal, not from copying current program output.

## Resource boundaries

VAL-R01 / R02 / R03 remain **BLOCKED** under the
[standing ledger](../pending-resource-validation.md) and [val.md](../../../val.md).
The following blockers carry forward from the A01 input/resource inventory;
this bounded policy session does not reprovision them.

| Gate | Remaining prerequisite |
|---|---|
| VAL-R01 | Four native project scenarios still need current-candidate acceptance; exact original inputs, Linux and the formal GPU free-memory guard are not provisioned |
| VAL-R02 | Original eight-file judge bundle is inaccessible; provider execution, credentials and an approved bounded budget are not provisioned; paid calls are explicitly excluded |
| VAL-R03 | Original Project C metadata manifest is missing; model-author-approved file access and a permitted token are not provisioned |

This session does not provision missing original manifests, native Linux/GPU
environments, provider execution/budget or gated-file authorization. No paid API
or model execution is performed. The source policy and local CPU validation do
not promote formal native, paid judge or authenticated-success resource gates.

After this bounded P-B delivery, continue independent R06-B / R07-C / R08-B
proposal work or restore specifically missing inputs when provisioned. The
remaining resource matrix still prevents a release-ready claim.
