# M6 second-half session — State audit and diff acceptance

Implementation and local validation: 2026-09-22. Submission prepared: 2026-09-23.
Baseline: main `a6498ec`, containing approved PRs #5 and #6. The maintainer
approved drift table v1 (M6-H3) on 2026-09-22; this session does not change it.

## Scope and commits

| Task | Commit | Result |
|---|---|---|
| M6-T05 | `97708bb` | Five consistency rules consume State leaves and alternatives; existing M4/M5 audit snapshots unchanged |
| M6-T06 | `de3ad01` | Four JSON/text fixture pairs, including real child captures and relocking with mocked HF responses |
| M6-T07 | `41af36c` | Diff guide, README excerpts, policy/override/threshold explanations; Gate A passed |
| M6-T08 preparation | This report and `docs/releases/0.4.0-draft.md` | Draft only; no version bump, tag or publication |

Code is ready for D-41 review, not yet merged. T07's real Project A/H2 acceptance
and T08's release remain blocked. Remote CI results belong to the submission PR's
checks; a local pass does not substitute for those checks.

## Implementation and regression evidence

The audit engine takes one State view before executing Level 2 rules. Projection
combines the current manifest/lock, the latest run's observations and working-tree
hashes. It does not load historical snapshots as current declarations. Standalone
diff still requires referenced historical snapshots. This preserves §12.12's
current-tree/current-declaration semantics without duplicating historical sources.

Generation, model identity, accepted custom fields, critical packages and files
now obtain compared values and provenance from State. Mutable model references
still compare against their resolved lock identity; missing packages retain INFO
severity; custom rules retain their accepted severity. Comparison precedes
redaction. Structured custom values stay atomic at their binding boundary.
Invalid lock paths, including an empty path, remain findings rather than causing
the new projection to abort the audit.

New tests include manifest temperature 0.0 / config 0.7 / CLI 1.0, asserting one
finding with all three evidence rows, plus proof that rules consume supplied
State evidence without rereading raw bindings. No existing audit, run, lock or
State golden was regenerated. All nine exported schemas remain byte-identical.

Final local quality gate:

```text
pytest --cov=reprollm --cov-fail-under=85: 1223 passed, 2 skipped; 43.26 s
coverage: 93.09%; core/redaction.py: 100% statements and branches
pytest -m security: 2 passed; 0.66 s
ruff check / format --check: passed
mypy src/: passed, 104 source files
schema freshness: all 9 files unchanged
generated rules/profile documentation freshness: passed
```

The two skips are Linux-only cases on macOS. Tests have the existing unmocked-HTTP
guard. The documentation profile validates, and every shown diff excerpt matches
the reviewed scenario A text. The installed wheel contains table v1 and produces
the expected torch MEDIUM diff and fresh exported schemas.

## Four fixture scenarios and plan interpretations

- **A:** The first captured run matches the existing M5 `run.json` golden after
  its standard volatile-field exclusions. Append `Answer concisely.` to the
  system prompt, relock with mocked HF metadata, commit the changed prompt/lock,
  then capture `python -c pass --config configs/eval.yaml --temperature 0.7`.
  Expect three HIGH fields (prompt role hash, captured file hash, temperature),
  three MEDIUM fields (prompt size, clean commit, argv), and one NONE run-ID
  change. Fixed test clocks produce no time drift. Verdict: not directly comparable.
- **B:** Change only `models.primary.revision.value` in a lock copy. Exactly one
  HIGH change, with full revision values in JSON.
- **C:** Compare one run with itself. No changes; highest NONE. The task plan's
  mention of changed IDs/times does not apply to identical inputs.
- **D:** Change only torch 2.8.0 → 2.8.1. Exactly one MEDIUM change; verdict asks
  the reader to review it. Normative §18.1 and the approved table take precedence
  over the plan's conflicting LOW example. The policy itself is unchanged.

Scenario A explicitly commits the changed inputs: appending a file alone cannot
change `code.commit`. Prompt size and argv changes are retained rather than
hidden to fit the abbreviated task description. Appends use LF on every platform
so the golden hashes and Git commits stay deterministic.

## Standing five-project Gate A

All original checkouts were verified at the exact `val.md` pins with a clean tree
and the expected origin. Mutating commands ran only in disposable shared clones.
All five targets passed complete rule/profile/dependency/hint/path/line/diagnostic
checks, not just summary counts. Init bytes and Level 1/2 reports were compared
against isolated source from `a6498ec`, ignoring only documented volatile fields;
stderr diagnostics also matched. Every delta set is empty.

| Target | Pinned SHA | L0 seconds | L0 C/W/I/P/S | L2 conflict/matching seconds | Diff checks seconds |
|---|---|---:|---|---|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 6.775 | 0/14/1/8/1 | 6.521 / 6.595 | 4.031 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 0.585 | 0/16/1/8/1 | 0.604 / 0.578 | 2.381 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 0.794 | 1/15/1/7/1 | 0.768 / 0.767 | 2.338 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 0.575 | 0/7/1/7/1 | 0.564 / 0.592 | 3.525 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 0.289 | 0/7/1/7/1 | 0.293 / 0.309 | 2.199 |

L0 uses `reprollm -v audit <checkout> --level 0 --format json --fail-on never`;
all exit 0. `doctor --json` also exits 0 on all five. lm-eval still reports its
500/816 Python scan boundary, and LlamaFactory still reports tracked `.env.local`
as CRITICAL. Neither known baseline result was suppressed or reclassified.

Runtime contracts in each disposable clone:

```text
init; audit --format json --fail-on never
lock --offline
run --capture-output --name conflict -- python -c <bounded-print-command> \
  --temperature 1.0 --model fixture/other --alpha 0.5
audit --format json
run --name matching -- python -c pass \
  --temperature 0.0 --model fixture/model --alpha 0.25
audit --format json
runs list --json; runs show <unique-prefix> --json; runs show <run-id>
```

Generation conflict evidence is `[0.0, 1.0, 0.0, 0.25]` (declaration, CLI, config,
environment). Generation/model/file conflicts are CRITICAL; accepted custom
conflict is WARNING. Matching capture passes those rules and environment
consistency. Both L2 audits intentionally exit 1 because offline model revision
confidence remains insufficient; LlamaFactory additionally retains `.env.local`.
Fake secrets never occur in captured artifacts. A corrupt extra run yields a
warning and does not replace the latest valid record.

Each target also runs 16 commands covering paired runs, identical inputs,
standalone copied run directories, HIGH filtering, text output, revision locks,
torch patch locks and run-vs-lock. Temperature 0.0 → 0.7 is HIGH, argv MEDIUM and
changed clocks/IDs NONE. `--fail-on HIGH` exits 1, including with a display filter;
identical inputs exit 0. The revision lock pair exits 1 at HIGH; the torch patch
pair exits 1 at MEDIUM. Default-threshold comparisons exit 0. Complete change
objects, summaries and JSON schema validation match the independent expectations.

The additional Project B offline lock pair changes the judge from
`gpt-4o-2024-08-06` to `gpt-4o`. Exactly `models.judge.id` HIGH and
`models.judge.pinnability` MEDIUM appear; `--fail-on HIGH` exits 1. This exercises
metadata classification without calling the provider or claiming a real judge run.

Detailed drivers, per-command argv, expected/actual exits, elapsed times, reports,
and baseline source are retained in the temporary `reprollm-m6-second-half`
evidence directory: `gate-a-record.json`, `gate-runtime-record.json`,
`gate-diff-record.json`, `gate-judge-record.json`, and `package-reviewed/record.json`.
No model weights, restricted data, paid API or GPU resource was used. Original
checkouts stayed clean; `val.md` pins and gold answers were not changed.

## Blocked acceptance and next step

M6-H3 is already approved. The new engine change requires its own D-41 review;
approval of PRs #5/#6 does not cover this diff. After CI succeeds, request review
of the concrete PR before merging.

The outstanding M4 Linux and M5 resource gates remain blocked. M6 Gate B requires
real paired inference (lm-eval), a bounded judge item (FastChat), tiny LoRA steps
(LlamaFactory), the attack/target/classifier path (HarmBench), and privacy
fine-tuning (llm-dp). Provisioned environments, model/data access and any required
API budget, plus independently reviewed bounded expectations, are not available.
M6-H2's real Project A comparison and maintainer assessment therefore remain
blocked too. The synthetic command checks above do not pass those gates.

The release draft records every remaining gate. Version 0.1.1 is unchanged;
there is no `v0.4.0` tag or publication. Unrelated pet/output directories were
not modified or staged.
