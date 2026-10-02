# Post-Beta backlog

Active follow-up and deferred items, reconciled on 2026-10-02. Historical sprint
plans retain their original scope; current delivery state is summarized in the
[public roadmap](../community/roadmap.md) and [changelog](../../CHANGELOG.md).

## Pending resource validation

The [resource-validation checklist](../dogfooding/pending-resource-validation.md)
tracks the three groups deferred after 0.6.1: VAL-R01 (Linux H2 and five-project
GPU/pair replay), VAL-R02 (formal FastChat/DeepSeek judge inputs and replay), and
VAL-R03 (successful HF gated-file access). They remain BLOCKED until their
resources and acceptance evidence are available; val.md remains the gold source.

## Product trial follow-up (2026-10-02)

The [UX repair report](../dogfooding/2026-10-02-ux-repairs.md) records Discover,
onboarding, candidate-list, Action and export fixes and five-project validation.
All six [UX2 tasks](UX2_2026-10-02.md) are implemented on main, unreleased:
task selection, clearer audit outcomes, opaque API identity, `judge_only`, research
export details and reversible project-rule lifecycle. [PR #8](https://github.com/EnumaElish123/ReproLLM/pull/8)
received explicit D-41 approval and merged as `b5e1317`; its five main CI jobs
passed. The [review bundle](ux-2026-10-02-proposals/README.md) retains historical
proposals, not pending product decisions. The next approved work is the
[four-task UX3 plan](UX3_2026-10-02.md).

## Rules & detection

- P1 rule polish: `gen.stop_declared` / `prompt.few_shot_declared` negative
  corpora from real repositories (M3 risk table leftovers).
- Nested judge-parameter drift currently MEDIUM under the one-segment wildcard
  policy (val §8.4 gap); narrow policy review is scheduled as UX3-T02.

## Features (post-Beta by decision)

- `discover --paper` (D-26) and paper–code consistency.
- `rag` / `agent` profiles (detected, report-only today).
- Dataset content fingerprints (D-22; sampled hashing is the candidate design).
- SARIF output (checklist export templates already shipped in 0.5.2).
- Multi-stage/pipeline experiments (multiple manifests per repository).

## Engineering

- **Privacy heuristic punctuation / relative-source false positives (M7 follow-up,
  2026-10-01):** existing `RunPrivacy.text` treats standalone `/` prose separators
  as absolute-path matches. UX-T08's 2026-10-02 persistence fix preserves valid
  POSIX `./` and `../` source strings while retaining secret/identity redaction
  and explicit Discover traversal checks. The broader prose-separator heuristic
  remains pending separate source cases and security review; that part is not
  closed by the dot-relative correction.

- **Generated-document freshness — fixed (M8-T02, 2026-10-01):** authenticated
  logs for nightly run `36698429076` show performance, rules and profiles passing;
  `docs/cli.md` was stale after the M9 GitHub format and M10 template additions.
  This reproduces locally; the earlier all-generators/Ubuntu-only diagnosis was
  incorrect. Refreshing the reviewed help diff and restoring all four checks to
  ordinary CI prevents another delayed failure; nightly retains the checks.
  Revalidation exposed GitHub Actions forcing terminal styling and wrapping in
  captured Typer output. Documentation subprocesses now use a plain terminal
  with fixed dimensions; a regression reproduces the runner environment.
  Windows also selected a `.EXE` program name and legacy ASCII console. The
  isolated CLI-document renderer now fixes those presentation choices, with
  a complete-output Windows simulation and unchanged committed body.
- **Quickstart path aliases — fixed (M8-T02, 2026-10-01):** on macOS, temporary
  `/var` paths resolve to `/private/var`; replacing only the original spelling
  left a `/private` prefix in generated examples. Both aliases are normalized,
  with a regression test. Windows artifact separators are also normalized from
  authenticated runner evidence; the committed quickstart body is unchanged. CLI and
  quickstart checks now print the exact generated diff on failure.

- **Windows snapshot mismatch — RESOLVED (M8-T01).** The canonical comparator's
  hex annotation decoded to `sha256:6655ca5f…` — the **CRLF** hash of the
  project-rules file the test writes, vs the golden's LF hash
  (`18818d586f…`, verified byte-for-byte locally). The write lacked
  `newline="\n"`; fixed. This is the same platform-newline family as the
  product fix in `183f18a`; the test-side straggler is now closed and the
  comparator stays as a permanent guard.

- RepoScanner/pyscan performance pass on very large repositories (the ~28 s
  lm-eval Level 0 audit is the recorded benchmark; M8-T04).
- lm-eval HF-ID extraction stops at the 500-file scan cap — consider a
  targeted second pass for `from_pretrained` literals when truncated.
