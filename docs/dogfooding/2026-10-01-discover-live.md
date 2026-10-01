# Real DeepSeek discover validation

Date: 2026-10-01. M7-T04/T06; specification §§0, 7, 15–16, 20.
The maintainer provisioned a credential and authorized the paid validation.
Pre-execution source expectations remain those in [val.md §8.6](../../val.md#86-real-discover-validation-2026-10-01).

## Request and inputs

Production CLI at `b88e602b9bb54f03c887ccb91071f47415ef0d8b`, package `0.6.0`:

```console
reprollm discover . --experimental --yes --max-chars 30000
```

The target was an initialized disposable Project C, `llm-dp-finetune` at
`7f8b5dff4b92aae90ceccce3ec959b48307bed9e`. The original pinned checkout was
unchanged. README, generated manifest, public AST snippets and tree paths were
reviewed before sending. No weights, dataset contents or GPU execution were involved.
The credential was read in memory; the supplied credential file is locally
excluded from Git and is not included in any validation input or report.

| Input | SHA-256 |
|---|---|
| Initial manifest | `c23306a04f2a0ebc3ca28f9e3a2cd8ce27255342d302faee15c78367755e2477` |
| Rendered collection | `861765d98613dc6069d5be38c0202b4fa5f4ee315323bc90397dfb0a87995802` |
| Actual user message | `3059cc02dc6a9d91e803f5ca1cc3abff77b07e11145ebd077add1e5acba41b08` |
| System prompt | `e93ac5604c0defc347ae67e18c58eca21589c7ee1627c9040c784d8930d207c2` |
| Persisted candidate document | `2e82cab1a1751149e69cb631364ec19f446074b7bb3244de79f8c1017a49d30c` |

Collection content was 30,000 characters; collection headers and locators made
the rendered collection 31,210 characters. Declared-field context made the actual
user message 31,340 characters, below the reviewed 40,000-character ceiling.
The production request body was unchanged; the observer recorded only sanitized
accounting metadata. Limits were three attempts and a 400-second whole-run deadline.

One request succeeded: HTTP 200, CLI exit 0, 48.125 seconds, `finish_reason=stop`.
Requested and served model: `deepseek-flash`; response ID
`84dec632-af2a-4840-a6ca-6dc5a8faa030`; fingerprint
`aeb56401ca74e127821c4f9126dcb669`. This is a provider alias/fingerprint record,
not an exact model-weight revision or a claim of deterministic model output.

Usage: 8,758 prompt tokens, all cache misses; 12,933 completion tokens, including
11,428 reasoning tokens; total 21,691. Reasoning content was not persisted.
At the published CNY rates, estimated cost is **CNY 0.06049–0.12098** across
off-peak/peak tariffs; this is a usage-based estimate, not a billing receipt.
See [DeepSeek pricing](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/).

## Independent candidate review

Ten candidates passed schema and ID checks. All ten concepts have support in
the sent source; five are directly usable and five require evidence/binding
correction. There are zero candidate-to-candidate semantic duplicates. Counts
and wording are observations from this response, not updated gold answers.
Only the reviewed candidate below was accepted; the response document was not edited.

| Candidate | Review | Source and limitation |
|---|---|---|
| `fastdp_source` | Correct binding before use | README lines 61/63 support the unpinned Git dependency; the proposed whole `pip install` command is not a CLI flag binding |
| `cuda_visible_devices` | Usable | README lines 86/104 support the setting and environment binding |
| `dataset_mode` | Correct binding before use | DatasetArgs lines 17–22 support the parameter; nested scrubbed YAML contents were not sent |
| `max_grad_norm_dp` | Usable; accepted | PrivacyArgs lines 26–28, default `1.0`, no proposed binding |
| `model_architecture` | Usable | ModelArgs lines 17–21; the custom field does not replace the required model identity declaration |
| `ner_model` | Correct line before use | Actual declaration is line 22; the returned line 21 is blank |
| `noise_multiplier` | Usable | PrivacyArgs lines 18–20 explicitly describe overriding target epsilon |
| `per_device_train_batch_size` | Usable | TrainerArgs lines 50–55, default `16`; the returned snippet compresses the source and has no line number |
| `target_delta` | Correct binding before use | PrivacyArgs lines 14–16; DP8 YAML is only a tree path in the payload |
| `target_epsilon` | Correct binding before use | PrivacyArgs lines 10–12; DP8 YAML contents were not sent |

Tree visibility does not verify a config key or value. High model confidence
does not override the independent review. Model-proposed snippets often compress
multiline source; the source ranges above provide the actual evidence.

## Acceptance and deterministic audit

```console
reprollm rules accept c-7b21e7
reprollm audit . --format json --fail-on never --output <evidence>/missing.json
```

Acceptance exited 0 and preserved `source: discover`, `candidate_id: c-7b21e7`,
`field: custom.privacy.max_grad_norm_dp`, and no bindings. The rule ID was
`project.max_grad_norm_dp`, severity WARNING. With the field absent, audit exited
0 under `--fail-on never` and emitted FAIL/WARNING with `severity_origin: project_rule`.

The operator then explicitly declared `custom.privacy.max_grad_norm_dp: 1.0`
in the operator-generated disposable manifest, independently checking the source
AST default at line 26. This is validation intent, not a claim that a real training
run used that value. The updated manifest SHA-256 is
`38720a6adbac5069acbefc536f6ab5fe160b4382c07ae457af71f09fca14221d`.

```console
reprollm audit . --format json --fail-on never --output <evidence>/present.json
reprollm rules accept c-7b21e7
reprollm audit . --format json --fail-on never --output <evidence>/repeat.json
```

| Step | Expected/actual exit | Specific result | Seconds |
|---|---|---|---:|
| Accept | 0 / 0 | Source and ID retained | 0.081 |
| Audit missing field | 0 / 0 | FAIL / WARNING | 0.156 |
| Audit declared field | 0 / 0 | PASS / PASS | 0.135 |
| Duplicate accept | 2 / 2 | Rejected as already accepted | 0.153 |
| Repeat audit | 0 / 0 | Complete JSON equals prior audit except `generated_at` | 0.158 |

The five existing CRITICAL findings from the intentionally incomplete init
template remain. Summary changes only from `5/18/1/8/7` to `5/17/1/9/7`
(CRITICAL/WARNING/INFO/PASS/SKIPPED); this does not claim that the entire experiment
passes audit. No extra model request was made during acceptance or audit.

A driver attempt initially resolved `.venv/bin/reprollm` relative to the clone
and exited 127. Correcting the console-script path required no product change
or additional paid request; that failed attempt remains recorded.

Eight response/accounting/rule/audit artifacts were checked: zero actual
credential matches, zero known secret-pattern matches, and zero local identity
or absolute host-path matches. All ten candidate IDs recompute correctly.

A secondary `RunPrivacy` heuristic scan marked three standalone `/` separators
in each audit's existing public hints (for example, `generation.seed / training.seed`).
Independent inspection confirmed these are punctuation, not host paths or leaks.
The same existing helper also conservatively treats some `./` source text as a
path. General prose false positives remain a documented backlog item. A scoped
discover correction preserves legal relative config bindings while retaining
original-text credential and identity checks; it does not alter the privacy helper.

## Outcome

The §8.6 real-discover resource gate passes: usable independent evidence,
explicit acceptance, missing-to-PASS deterministic rule behavior, duplicate
rejection and clean persisted artifacts are demonstrated. The response's five
review corrections remain documented; they were not silently rewritten or accepted.

The relative config-binding compatibility fix added fifteen cases, with the
three positive cases failing first. The integrated local gate passed: 1,380 tests,
three skipped, two slow tests deselected, 64.70 seconds; combined coverage 92.48%,
redaction branch coverage 100%. Ruff, mypy and all four generated-document checks
passed; schemas and fixture snapshots were unchanged. Existing slow-marker and
upstream-source escape warnings remain explained in the original session evidence.

Gate A was repeated after the final correction: all five pinned checkouts were
clean with expected origins; 40 command stages passed with zero unexplained gold
deltas. All five generated manifests are byte-identical to the preceding gate.
The corrected finalizer also preserves the ten real returned candidates exactly;
that comparison used the cached response document and made no network request.

The commands and source-derived baseline are the same as the
[preceding five-project gate](2026-10-01-followup.md#five-project-gate-a).
All expected/actual command exit statuses were 0. Latest elapsed times:

| Target | Pin | L0 seconds | Init seconds | L1 seconds | Dry-run seconds |
|---|---|---:|---:|---:|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 6.426 | 10.271 | 7.435 | 0.807 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 0.581 | 0.586 | 0.562 | 0.388 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 0.819 | 0.853 | 0.899 | 0.425 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 0.597 | 0.634 | 0.626 | 0.366 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0.312 | 0.287 | 0.284 | 0.250 |

Compatibility correction: `0ce63d5fca6c71d133468d07c70afc03fd82e971`
(`fix(discover): preserve safe relative config bindings`, M7-T04).
Execution and resource-gate report: `35c6d22f80d662a03f24fa96484a3e944156414d`
(`docs(validation): complete real DeepSeek discover gate`, M7-T04/T06).

Exact HEAD `35c6d22f80d662a03f24fa96484a3e944156414d` passed cloud validation:

- [CI 36824409229](https://github.com/EnumaElish123/ReproLLM/actions/runs/36824409229)
  completed successfully. Ubuntu Python 3.10/3.11/3.12, macOS Python 3.12 and
  Windows Python 3.12 all passed. Ubuntu 3.12 schema freshness, examples,
  generated-document freshness, self-audit and published Action also passed.
- [Nightly 36824467968](https://github.com/EnumaElish123/ReproLLM/actions/runs/36824467968)
  completed successfully after one explicit dispatch. Performance: two tests
  passed in 4.71 seconds. Rules, profiles, CLI and quickstart document checks
  all executed and passed.

This cloud-results addendum changes only this report; the code, validation
inputs, source gold, schemas and fixture snapshots are unchanged.
