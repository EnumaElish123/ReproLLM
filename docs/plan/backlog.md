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

- **Windows snapshot mismatch (M7→M8):** the golden comparison now uses a
  byte-exact canonical form (bools wrapped so `true`/`1` cannot alias; hex-dump
  delta in any failure message) and the `linux_only` quarantine is lifted. The
  comparator already caught and resolved one class of aliasing locally. If the
  Windows leg fails again, its annotation will contain unambiguous hex bytes —
  one round settles it.

- RepoScanner/pyscan performance pass on very large repositories (the ~28 s
  lm-eval Level 0 audit is the recorded benchmark; M8-T04).
- lm-eval HF-ID extraction stops at the 500-file scan cap — consider a
  targeted second pass for `from_pretrained` literals when truncated.
