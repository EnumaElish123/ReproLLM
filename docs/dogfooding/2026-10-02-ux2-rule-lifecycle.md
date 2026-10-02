# Reversible project-rule lifecycle, 2026-10-02

Status: **Local full quality and five-project lifecycle Gate A passed. Explicit
D-41 review and merge remain PENDING. Remote delivery/CI are tracked on the
review PR for `codex/ux-rule-lifecycle`; this report records the candidate before
that PR is opened.**
This is the separate UX2-T06 candidate following the first five workflow repairs
at main `145103291ff819d0ed534e5afa7dc3ec211b160a`; it is not a release or an approved schema merge.

## Source and quality

Gate source HEAD is `94ae36643d7fba5019a6f14adffc08cefd3df7bc`, with tracked diff SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. The complete product-code/packaged-template/
exported-schema inventory, including files untracked when captured, is bound by
`f11545014ef834c2223e22f4db06fa2311c423ab0b3609ae095c719d856e5bd7`. The packager verifies that current
product inputs still match that inventory; this is not a complete checkout snapshot.
[Source provenance](ux2-rule-lifecycle-2026-10-02/implementation-provenance.json)
retains each relative path/hash and the driver/helper hashes.

Full local pytest: **1,797 passed, 3 skipped,
2 deselected, 1 warning in 101.48s**.
Ruff, format, strict mypy, exported-schema freshness, all four generated-document
checks and diff whitespace checks passed. Redaction remains 100% covered across
59 statements and 24 branches.
[Quality evidence](ux2-rule-lifecycle-2026-10-02/quality-summary.json) separates
actual command timings from pytest-reported time and retains raw-source hashes.
No remote CI success is inferred from these results.

## Rule preservation and failure semantics

`rules list --candidates` and `rules show` expose full records and relative source
labels. Default `rules list --json` remains the existing active-rule array.
`remove` requires a reason, publishes an immutable archive before changing active
rules, and reports any later failure without claiming removal succeeded.
`restore` retains the original source, candidate ID, accepted timestamp, reason,
field, severity and all CLI/config/environment bindings. It does not require the
historical discovery file and never overwrites an active rule or candidate ID.

The independent archive v1 adds one exported schema; the existing nine schema
files, including project-rules v1, are byte-identical to the first-five-task main
baseline. [Schema evidence](ux2-rule-lifecycle-2026-10-02/schema-compatibility.json)
also verifies unchanged core engine/redaction files. This additive schema still
requires explicit D-41 review of the concrete change.

Archive existence means a recovery copy exists. Current active rules determine
inactive/active-identical/conflict; any conflict takes precedence regardless of
array order. Remove/restore compare the originally parsed bytes immediately before
replacement as best-effort concurrent-change detection, not a multiwriter atomic
compare-and-swap guarantee. Privacy failure preserves original content or rejects
the operation. Strict generated archive IDs remain intact when a machine identity
matches their fixed `ra` prefix; arbitrary strings and malformed IDs remain subject
to existing filtering.

## Complete five-project Gate A

All five fixed upstream checkouts match their pins/origins and remain clean.
The gate records **92 commands and 22.715s summed
subprocess time**, with expected exits throughout and no unexplained delta.
This duration is not session wall time. Mutations use disposable clones and an
independently authored synthetic rule/discovery fixture; no endpoint is called.

| Repository | Fixed source SHA | Commands | Subprocess seconds |
|---|---|---:|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 18 | 10.158 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 18 | 2.846 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 18 | 3.098 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 18 | 4.078 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 18 | 2.514 |

Full L0 reports and verbose diagnostics match the reviewed baseline, ignoring
only `generated_at`; `--fail-on never` exits 0 without asserting all findings PASS.
Each clone verifies complete rule/candidate inspection, accepted-ignore rejection,
archive/remove, inactive state, restore after deleting discovery, active-identical
state and refusal of a second restore. The archive stays byte-identical across
restoration/refusal, and every original rule/binding field is restored exactly.

[Per-target evidence and comparison hashes](ux2-rule-lifecycle-2026-10-02/matrix-summary.json)
link the complete current rules and archive hashes to five stage snapshots:
initial, ignore refusal, removed, restored and repeat-restore refusal. Each target's
lifecycle JSON retains the complete original/archive/restored documents and empty
field-by-field diffs, including all bindings. [All commands](ux2-rule-lifecycle-2026-10-02/commands.json)
retain arguments, exact expected/actual exits, target SHAs, elapsed time and
stdout/stderr hashes. The bundle omits raw machine-bearing logs and the large inventory.

## Main baseline CI and pending candidate delivery

The first-five-task main baseline `1451032` has [successful CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/37017287499): all five Linux/Python, macOS and Windows jobs completed successfully in 9m 30s. The final public API query returned 403; the independently observed GitHub workflow page confirms success. [Retained UI observation](ux2-rule-lifecycle-2026-10-02/main-ci-success.json) records the exact head, job URLs, conclusions and source. This is main baseline CI; the T06 candidate/PR CI remains pending.

- D-41 concrete schema/implementation review and PR reference: **PENDING**.
- Candidate branch push, CI results and exact checked head: **PENDING**.
- Merge outcome: **PENDING**; local green checks do not authorize a schema merge.

The [delivery record](ux2-rule-lifecycle-2026-10-02/delivery-status.json) separates
these pending actions from completed local checks. Resource Gate B, model/GPU or
credential use, paid APIs, package release and standalone Action publication remain
outside this request. Existing resource blockers are not passed by this offline gate.
