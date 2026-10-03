# UX3 validation evidence, 2026-10-03

This bundle records local quality and Gate A for code commit `c1cf91e`.
All persisted documents carry `schema_version: 1`. Read the
[session report](../2026-10-03-ux3-readiness.md) for task commits, deviations,
resource blockers and remote delivery status. These synthetic offline checks
are not real-model runtime acceptance or a package release.

- `gate-a-complete.json` records five clean pinned targets, 261 commands,
  410 successful complete comparisons and no unexplained deltas.
- `commands.json` retains arguments, target SHAs, expected/actual exits,
  per-command time and raw/portable output hashes. `<implementation>`,
  `<pinned-sources>`, `<evidence>` and `<driver>` replace machine directories.
- `comparisons.json` preserves equality and SHA-256 digests for every complete
  comparison, including no-write filesystem metadata checks.
- The five `PROJECT-complete-comparisons.json` files preserve all 72 semantic
  cases per target: full L0 reports, diagnostics, hints, parsed preflight,
  complete list rows/JSON bytes and complete diff reports/selection/warnings.
  Array/string payloads remain data inside the document; no product schema is changed.
- `independent-fixture-oracle.json` contains expected inputs/results authored
  before invoking new commands. `PROJECT-fixture-hashes.json` records actual
  synthetic input bytes. Fixed upstream sources remain separate clean checkouts.
- `implementation-provenance.json` binds every product/template/schema file,
  exact code commit, specification/plan/val hashes and temporary driver/guard hashes.
  `independent-gate-review.json` records the preexecution harness review;
  `independent-t04-review.json` binds the final reviewed source/tests.
  `final-evidence-review.json` independently verifies the consolidated payloads,
  command exits, comparison/source digests, coverage, schema compatibility and privacy.
- `t01-quality.json`, `t03-quality.json`, `t04-quality.json` retain all local
  quality commands/exits/timings. `quality-summary.json` retains redaction
  coverage and hashes of omitted raw logs/coverage inputs. `compatibility.json`
  verifies all ten schemas and core engine/redaction are unchanged from `b5e1317`.
- `evidence-source-ledger.json` preserves original comparison-source hashes and
  maps consolidated payloads to their per-target documents. Original/intermediate
  byte hashes and current aggregate document hashes are recorded separately.

Raw machine-bearing filesystem metadata, disposable clones, symlink sentinels
and Git logs remain outside the repository. Their comparison hashes cannot
reconstruct omitted contents. Product outputs were checked before replacing
paths for evidence portability; a host-path leak would fail validation.
No credentials, provider calls, experiment launch or GPU job occurred.
VAL-R01/R02/R03 remain blocked. No pin or gold answer was changed.

`code-ci-success.json` records the exact implementation push head and all five
remote job successes. Documentation/report delivery uses the same product tree;
its current main CI is linked in the session report.
