# S1-A reliability baseline evidence, 2026-10-10

This bundle starts S1-A (`R00 → R01`) from actual main HEAD
`d7d9d63390335788e1804e0b5af87c6d64f319cd`, using Python 3.12.14 and
ReproLLM 0.6.1 on Linux. Read [R00 baseline report](r00-baseline.md) for scope,
task states, commands, environment deviations and next-session inputs.

- [r00-reproductions.json](r00-reproductions.json) preserves the 13 observed
  minimal defect cases (R01 plus 12 delegated cases), source locations,
  exits and elapsed times. Every case still reproduces at the frozen HEAD.
- [r00-quality.json](r00-quality.json) records both the original Git 2.25.1
  environment failures and the compatible complete baseline, together with
  command exits, timings and SHA-256 hashes of omitted raw logs.
- [r00-input-inventory.json](r00-input-inventory.json) records all five clean
  pinned targets, exact origins/SHAs/Python counts and independent oracle sources.
- [r00-gate-a-summary.json](r00-gate-a-summary.json) records the actual frozen
  candidate's five-project Gate A: 45 primary commands, 180 complete/source-backed
  comparisons, all exits 0 and zero deltas. Complete per-target payloads,
  commands, comparisons and source archive provenance are retained alongside it.
- Historical oracle recovery and its initial source-anchor check failure are
  distinct from the actual candidate gate. The separate oracle, initial failure
  and harness-correction documents preserve both attempts; no gold was changed.
- [r00-gate-input-check-commands.json](r00-gate-input-check-commands.json) records
  15 supplemental source metadata checks, counted separately from primary commands.

All retained JSON documents have `schema_version: 1`. Logical placeholders
replace machine directories; raw machine-bearing logs, synthetic unsafe input
files, disposable clones, child venv metadata and wrapped-run artifacts remain
outside the repository. Minimum replay constructions are documented in the
report and linked task cards, without relying on those temporary directories.

The actual Gate A uses a byte-verified Git archive of frozen `d7d9d63` to isolate
the baseline from subsequent R01 work. Only `generated_at` is removed from full
audit JSON comparisons; the timestamp format and version 0.6.1 are checked.

These records establish defects and a local quality/Gate A baseline; they do not assert that
the planned repair acceptance matrices have passed. R01 implementation evidence
is separate from the frozen R00 observations. R05-S still needs its concrete
spec decision; R08/scope policy changes remain PROPOSED. No resource gate was
activated and VAL-R01/R02/R03 retain their existing BLOCKED states.
