# Q4 2026 Retrospective — ReproLLM Beta Sprint

Written 2026-09-29 after completing M1–M11 (12 sprint weeks compressed to 4
calendar weeks). The M12 review.

## What worked

1. **Plan-first discipline.** Every session started from the frozen decision
   register (00) and the sprint doc (M<N>). Zero frozen decisions were
   violated; two spec ambiguities were caught and documented rather than
   guessed around (§7.6 protocol worked).
2. **Two-session-per-sprint cadence.** Splitting each sprint into
   "infrastructure" and "user-visible" halves gave natural review checkpoints
   and kept PRs focused.
3. **Golden-fixture + external-validation model.** The six golden fixtures
   caught regressions early; the five-repository Gate A (later with gold
   answers) caught what fixtures couldn't — real-world path-redaction
   corruption (§8.5b), platform-newline determinism bugs, provider-specific
   API behaviors.
4. **Redaction as a security boundary from day one.** 100% branch coverage
   from M5, the leak golden test in the release pipeline, and the corpus
   built incrementally — this never felt like overhead.
5. **Consolidated release strategy (D-43, §8.5).** Merging 0.2/0.3/0.4 into
   one 0.4.0 release avoided three never-tested versions. Promoting
   supplementary validation scenarios to formal standards (§8.5) with
   documented rationale kept the gold honest without blocking on unavailable
   credentials.

## What didn't work

1. **Windows CI from anonymous logs.** The snapshot mismatch took 8+ rounds
   to diagnose because job logs require authenticated access. The junit-xml →
   annotations bridge fixed this for future failures, but the doc-freshness
   check still can't be debugged without it (backlog item).
2. **Doc-freshness on CI runners.** All four generated docs pass every local
   combination but fail on ubuntu runners. Moved to nightly; needs one
   authenticated log read to close. This is the top maintainer action item.
3. **Sprint compression.** M1–M11 in 4 weeks (planned: 12) meant the
   two-session cadence sometimes collapsed into one long session per sprint.
   The quality held (1,307 tests, all gates green), but dogfooding windows
   were tight.
4. **Discover real-run validation.** The DeepSeek judge and DistilGPT2 DP
   pairs ran real execution, but `discover` itself was only dry-run tested
   (the endpoint budget was consumed by the judge validation). Real
   `discover --yes` needs a provisioned endpoint.

## Top three things for next quarter

Follow-up, 2026-10-01: authenticated nightly logs corrected the document-freshness
diagnosis above. The CLI reference lacked the M9/M10 options, reproducibly on
the local runner too; rules and profiles passed. A separate macOS temporary-path
alias bug in quickstart generation was fixed with a regression test. All four
checks are restored to ordinary CI and retained in nightly; see the dated
validation report for remote verification.

1. **Adoption above everything.** The upstream PR (lm-eval recipe), the
   GitHub Action marketplace listing, and one real external user are worth
   more than any feature. The product works; people need to know it exists.
2. **Close the two open CI diagnosis items** (doc freshness runner delta,
   Windows-equivalent for any future snapshot issues). Both need one
   authenticated Actions log read.
3. **Paper-artifact case study.** Use ReproLLM in one real paper submission
   (NeurIPS or ACL deadline). The `export --template` exists; exercising it
   on a real submission is the strongest possible validation and produces the
   best demo material.

## Metrics summary (2026-09-29)

| Metric | Value |
|---|---|
| PyPI versions | 7 (0.1.1 → 0.5.3) |
| PyPI downloads (30d) | 110 (automated scans, not human adoption) |
| GitHub stars | 30 |
| External users | 0 (self-hosted only) |
| Tests | 1,307 passing on 3 Python versions |
| External validation repos | 5 (all gates closed) |
| Published Action | reprollm-action@v1 (bootstrapped in CI) |
| Lines of code (src/) | ~15,000 |
