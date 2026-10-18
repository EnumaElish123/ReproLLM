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

Status while collecting final evidence: **IMPLEMENTED, ACCEPTANCE_IN_PROGRESS**.
This product session requires one final complete quality gate followed by fresh
five-project Gate A L0/facts and affected diff extensions. Focused GREEN alone
does not close session acceptance. Commands, exit statuses, durations, frozen
inputs and complete comparisons will be linked here after execution.

## Resource boundaries

VAL-R01 / R02 / R03 remain **BLOCKED** under the
[standing ledger](../pending-resource-validation.md) and [val.md](../../../val.md).
This session does not provision missing original manifests, native Linux/GPU
environments, provider execution/budget or gated-file authorization. No paid API
or model execution is performed. The source policy and local CPU validation do
not promote formal native, paid judge or authenticated-success resource gates.

After this bounded P-B delivery, continue independent R06-B / R07-C / R08-B
proposal work or restore specifically missing inputs when provisioned. The
remaining resource matrix still prevents a release-ready claim.
