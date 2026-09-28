# M7 validation record — export, project rules, discover

Session date: 2026-09-28. Baseline: main `334aaab` (M7 session 1) → delivered
through `2596a6a`; tag `v0.5.0a1` at `37dd484`. All work follows
`docs/plan/M7_export_discover_dogfooding.md`; deviations are listed at the end.

## Tasks and quality gate

| Task | Commit | Result |
|---|---|---|
| M7-T01 export | `5320b69` | Full §19 section order, embedded audit, determinism, redaction; three fixture snapshots + no-run/no-lock degradation |
| M7-T02 project rules | `334aaab` | GeneratedProjectRule engine path, `rules add/list`, custom_fields + lock-fresh second branch real data; integration suite + golden |
| M7-T03 collector | `32b493d` | §20.2 selection/redaction-gating/budget; three dry-run snapshots |
| M7-T04 discover client + accept/ignore | `3092fe2` | Delivered inside the time box — the §4 cut clause was **not** needed; gates, JSON-mode fallback, retry-then-exit-3, evidence demotion, state machine all tested |
| M7-T05/T07 docs | `c056936` | `docs/discover.md` (privacy statement first), `docs/export.md`, `docs/project-rules.md`, `docs/plan/backlog.md` |
| M7-T06 full flow | this record + `7504380` | Below |
| M7-T08 release | `37dd484` + tag | 0.5.0a1 published; pre-release semantics documented |

Gate: 1285 tests on 3.10/3.11/3.12, ruff, mypy --strict, schema freshness,
both coverage gates, five-repository Gate A unchanged.

## Five-repository full flow (disposable worktrees)

`init` → `audit` (L1) → `lock --offline` → `audit` (L2) → `export` completed
on all five pinned checkouts; worktrees removed afterwards.

| Repository | init profiles | L1 | lock | L2 | export |
|---|---|---|---|---|---|
| lm-evaluation-harness | evaluation, finetuning, inference | 6C/26W | exit 0 | 7C/26W | written (1 model, no-run degradation) |
| FastChat | finetuning, inference, llm_judge | 6C/30W | exit 0 | 8C/32W | written (2 models) |
| LlamaFactory | evaluation, finetuning, inference | 6C/27W | exit 0 | 7C/27W | written |
| HarmBench | evaluation, finetuning, inference, safety | 7C/20W | exit 0 | 8C/20W | written |
| llm-dp-finetune | finetuning, privacy | 5C/17W | exit 0 | 6C/17W | written |

CRITICALs are the honest TODO/unresolved state of init-scaffolded manifests
under offline locking (unfilled required fields, unresolved revisions) — not
crashes or suppressed findings. Discover `--dry-run` verified on lm-eval
(budget-filled README) and llm-dp (21 files incl. argparse/dataclass snippets);
nothing was sent.

## Dogfooding findings fixed in-session

- `lock --offline` constructed an `httpx.Client` it never used; under a SOCKS
  proxy environment this crashed at construction (exit 3). Offline now builds
  no client at all (`7504380`, type-narrowed in `2596a6a`).

## Open items at release

- GPU re-pairs (lm-eval clean re-run after the fidelity fix; HarmBench local
  pair) — both card-0 guards failed at every checkpoint today (100 % util);
  not claimed, tracked in val.md.
- Real discover execution awaits a provisioned endpoint/budget (the approved
  DeepSeek two-attempt plan is spent); only dry-runs are claimed.
- M6-H2 readability review material is prepared; the maintainer's assessment
  is the remaining human step.
- Post-release PyPI/GitHub verification was network-blocked from this host at
  release time; the workflow is the same trusted-publishing pipeline that
  published v0.4.0 successfully.

## Deviations from the sprint doc

- T02 acceptance wording "modify configs/privacy.yaml after run →
  custom_fields CRITICAL" implemented per §12.12 normative semantics (run
  observations vs manifest declarations; post-run file edits are file_hashes
  drift) — documented in the test.
- T03/T04/T05 sequencing compressed into one session day (the time box's
  Thursday-18:00 checkpoint passed early); T06's Project-A real GPU flow is
  replaced by the recorded open GPU gate above.
