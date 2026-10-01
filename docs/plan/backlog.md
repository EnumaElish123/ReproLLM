# Post-Beta backlog

Deferred items collected during M2–M7 with their reasons. M8 turns this into
roadmap issues; nothing here is scheduled for the Beta.

## Rules & detection

- P1 rule polish: `gen.stop_declared` / `prompt.few_shot_declared` negative
  corpora from real repositories (M3 risk table leftovers).
- Provider identity vs API compatibility: `model.revision_pinned` treats a
  truthful `provider: other` OpenAI-compatible vendor (e.g. DeepSeek) as
  CRITICAL even when the lock records `pinnability` correctly — surfaced by the
  DeepSeek validation. Needs a spec-reviewed provider contract, not a relabel.
- Judge-only manifests trip the full `llm_judge → … → core` presence chain
  (five CRITICALs in the DeepSeek pair); a profile variant for judging stored
  answers could express that honestly. Spec change first.
- Nested judge-parameter drift currently MEDIUM under the one-segment wildcard
  policy (§8.4 gap); review `evaluation.judge.*` severity semantics.

## Features (post-Beta by decision)

- `discover --paper` (D-26) and paper–code consistency.
- `rag` / `agent` profiles (detected, report-only today).
- Dataset content fingerprints (D-22; sampled hashing is the candidate design).
- SARIF output; `export --template neurips|acl|acm` checklist mapping (M10).
- Multi-stage/pipeline experiments (multiple manifests per repository).

## Engineering

- **Privacy heuristic punctuation / relative-source false positives (M7 follow-up,
  2026-10-01):** existing `RunPrivacy.text` treats standalone `/` prose separators
  and some `./` source strings as absolute-path matches. Independent real-discover
  review found no actual leak; candidate and accounting artifacts are clean.
  Discover now preserves verified relative config DSL bindings with original-text
  secret/identity checks. A broader prose heuristic change needs separate source
  cases and security review; it is outside this scoped binding correction.

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
