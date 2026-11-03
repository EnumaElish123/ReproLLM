# Issues #9 and #13: verified policy and candidate clarification

Date: 2026-11-03. Source baseline: `ad8b2c7057b6473072b65102eaf8e122b647acec`.
Scope comes from the maintainer's request to handle the two open issues and the
[bounded issue plan](../../plan/issues-2026-11-03.md).

## Resolutions

[#9](https://github.com/EnumaElish123/ReproLLM/issues/9) is already implemented
by `0b36780edaaa6150693dc9dd7330e5ba429a1398` (R08-A). The
[accepted decision](../../plan/reliability-2026-10-03/proposals/R08-A/decision.json)
and [original implementation report](../2026-10-18-r08a/README.md) retain their
actual candidates and results. The current table and specification contain
`evaluation.judge.params.*: HIGH`; direct changed/added/removed leaves, vendor
parameters, user LOW/NONE overrides and single-segment matching are reverified
below. No duplicate product change or task commit is needed to close this stale
issue. Existing historical MEDIUM records are not rewritten.

[#13](https://github.com/EnumaElish123/ReproLLM/issues/13) is resolved as a
clarification of the existing schema-2 candidate inventory. Specification §3
allows inline text or paths without a discriminator in `privacy.threat_model`
and `evaluation.definitions.*`. Their safe relative-path spellings are retained
as optional candidates, including when absent. `missing` before and after with
`change: unchanged` means continued absence, not proof of a missing required
scientific file, lost bytes or a failed capture. `origin: declared` does not
encode whether the originating field requires a file. The
[runtime guide](../../run.md#interpret-input-candidates) now explains how to read
these records and why lock's existing-file inventory can differ.

The four native cases below were run before changing the explanation. One
deliberately uses the reported prose as the name of a real project file: spaces
and punctuation cannot distinguish text from filenames. No path heuristic or
schema change is introduced; explicit missing configuration diagnostics,
creation/removal detection and the pre-child baseline stay intact. This issue
does not establish that all candidates exist or that any child consumed them.

## Verification before documentation changes

On Python 3.12.14 / Linux, the following existing regressions completed with
**364 passed in 17.47 seconds**, exit 0:

```console
.venv/bin/python -m pytest -q tests/unit/diff/test_severity.py tests/unit/cli/test_judge_param_policy.py tests/unit/run/test_input_capture.py tests/unit/run/test_input_schema.py tests/unit/run/test_input_export_evidence.py tests/unit/cli/test_run_preflight.py --tb=short
```

This includes actual standard-library child captures, thresholds, filtered
reports, deterministic JSON, self-diff, historical-byte preservation, input
change states, unavailable inputs, snapshot options and all four export
templates. It does not execute a model or call a provider.

Four additional disposable CPU-only native CLI cases pass at the same source:

| Case | Independent expected result | Actual |
|---|---|---|
| Exact issue text in both optional fields; child `pass` | Both candidates missing before/after and unchanged; no captured file or required-file warning | PASS |
| Existing prose-named threat file and definition file; child deletes the former, rewrites the latter and creates an explicitly declared config | Removed/changed/created; original hashes and snapshot bytes retained; created file absent from pre-child `files` | PASS |
| Same file mutations with `--no-snapshot` | Same fingerprints and change states; no file snapshots | PASS |
| Initially missing optional threat path created by child, absent definition and explicitly missing config | Optional created; other two absent/unchanged; explicit config still warned about; no invented pre-child file | PASS |

Each invocation used the source-selected recorder and a standard-library Python
child in a fresh temporary project:

```console
python -c 'from reprollm.cli.main import cli; cli()' run [--no-snapshot] -- python -c CHILD
```

`[--no-snapshot]` marks the single optional policy variant, not literal argv.
The child in the mutation pair removes `Only synthetic examples are used.`,
rewrites `definitions/asr.txt` from `Original definition.\n` to
`New definition.\n`, and creates `configs/later.json` containing `{}\n`.
The final case creates `threat-model.txt` containing `Created.\n` while leaving
`definitions/asr.txt` and `configs/required.json` absent. Before/after byte
hashes, counts and states were asserted independently from those fixed inputs.
The [portable receipt](input-candidates.json) records full relevant checks,
CLI and child exit 0, schema 2, recorder 0.7.0 and elapsed time for each case.
Temporary projects and their run artifacts were discarded after assertions.

Two additional `reprollm lock --offline` invocations compare the same two
text-or-path values when both are absent and when files with those exact names
exist. Both exit 0: lock's `files` is empty in the first case and contains exactly
those two files in the second. The receipt's `offline_lock_cases` retains the
results separately from the four run captures. Product bytes remain identical
to the baseline; these two checks ran after the prose edits.

## Scope and final documentation checks

Only specification/runtime prose, plan navigation, the changelog and this
report/receipt are changed. No product code, test, dependency, profile, formal
schema or scientific gold is edited. All ten in-memory JSON Schema exports
match the committed bytes; all nine pre-existing user files retain their
original hashes. See the [scope receipt](scope-checks.json).

All 153 local links in the changed Markdown documents resolve, the partial YAML
example validates as part of a minimal manifest, the public report directory
passes `scripts/check_no_leaks.py`, and `git diff --check` passes. Generated
CLI/rules/profiles/quickstart content is unaffected. Following the
[validation workflow §3](../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义),
the full local quality gate and five-project Gates A/B are
`NOT_APPLICABLE_DOCUMENTATION_ONLY`, not PASS. The focused regressions and four
synthetic captures are additional verification, not a fresh five-project or
GPU/provider/release acceptance. No paid request, model inference or external
research validation is claimed.

The starting source's [five-job CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/41467966244)
is green. The clarification commit's own official CI is checked after push and
reported in the issue closure; this pre-push report does not claim that result.
The GitHub connector's label mutation returned HTTP 403. The existing owner
GitHub CLI login successfully added the requested `spec` label to #13; no
credential was displayed or changed. After exact-head CI verification, issue
comments link the existing implementation or delivered documentation before
closing both issues as completed.
