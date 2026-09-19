# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (M5, first half)

- Capture CPU/GPU metadata through bounded `nvidia-smi` calls, hash GPU UUIDs,
  and capture SLURM/PBS/LSF namespaces with secret names omitted and values
  redacted; malformed or unavailable GPU data is explicit (M5-T02, spec §5.1 R-07/R-08).
- Implement the nine ordered text-redaction classes, segment-based environment
  name checks, allowlisted environment capture, and streaming PEM suppression;
  execute the synthetic positive/negative/name corpus and enforce 100% branch
  coverage for the redaction module in CI (M5-T01, spec §16).
- Accept complete JWT padding variants under the maintainer-approved
  [spec correction #3](https://github.com/EnumaElish123/ReproLLM/issues/3), with
  all 27 segment-padding combinations covered. No schema or rule ID changes.

### Pending M4 release

Planned for `0.2.0`: the first release of the **lock schema v1 writer**
(`reprollm.lock`, `schema_version: 1`). Existing manifest schema v1 remains
compatible; no schema migration is required.

### Clarified

- Keep only the four runtime consistency placeholders through M4; require an
  empty stub set after M5-T06, with a CI assertion for the current boundary.
  This maintainer-approved clarification changes no schema or rule selection
  ([#2](https://github.com/EnumaElish123/ReproLLM/issues/2), spec §§6.1, 12.12).

### Added (M4, second half)

- Record five-project metadata validation with independently checked HF
  revisions and file hashes, offline/online stability, and authenticated
  gated-file denial without credential leakage; retain Linux H2 as a pending
  manual gate (M4-T08, spec §§4, 12, 22; [validation record](docs/dogfooding/m4-lock.md)).

- Reuse the bounded HF client in `doctor --check-network`, including mirror,
  retry, metadata-validation, and sanitized authentication failure behavior;
  document lock provenance, pinnability, offline resolution and freshness
  (M4-T07, spec §§1, 4, 22 T-04).

- Add reviewed lock and Level 2 audit snapshots for all three complete fixtures,
  with exported-schema validation, an intentionally unavailable vLLM backend,
  API judge pinnability, and a gated-model denial (M4-T06, spec §§4, 10, 22).

### Fixed (M4 dogfooding)

- Recognize supported Apple Git version strings in `doctor` instead of reporting
  a parsing warning for their vendor suffix (M4-T08, spec §1).

### Documentation (M4-T09 preparation)

- Prepare [draft release notes](docs/releases/0.2.0-draft.md) with the real
  FastChat judge lock fragment and isolated wheel/sdist packaging evidence.
  Version bump, tag and publication await the manual Linux validation gate.

### Added (M4, first half)

- Add a bounded Hugging Face Hub HTTP client with mirror support, environment-based
  authentication, sanitized errors, and deterministic retry behavior, backed by a
  hand-written offline response corpus (M4-T01, spec §4.3 and §22 T-04).
- Resolve Hugging Face, API, and local model and dataset identities; hash prompts,
  declared files, metrics, local metadata, adapters, and bounded weights; and capture
  backend and environment provenance in online and offline modes (M4-T02, spec §4).
- Add `reprollm lock` with atomic deterministic YAML writes, offline and optional API
  verification modes, large-weight control, provenance summaries, and a network-free
  `--check` freshness path with exit code 1 for missing or stale locks (M4-T03, spec §§1, 4).
- Load and validate locks during audit, auto-detect Level 2, report manifest and accepted
  project-rule staleness independently, and compare locked prompt/config hashes with the
  current working tree using repository-contained paths (M4-T04, spec §§9–12.12).
- Enforce resolved model, tokenizer, chat-template, dataset, backend, prompt, and judge
  lock metadata with provider-specific severities and provenance evidence; API snapshot
  aliases remain informational while mutable API aliases warn (M4-T05, spec §§12.4–12.9).

## [0.1.1] - 2026-09-17

M3 completes all 38 Level 1 LLM experiment rules and finalizes the seven built-in
profiles: `core`, `inference`, `evaluation`, `llm_judge`, `finetuning`, `privacy`,
and `safety`.

An intentionally incomplete OpenAI judge manifest now reports the missing judge
sampling contract directly:

```text
CRITICAL (1)
  X judge.params_declared      Missing fields: evaluation.judge.params.max_tokens, evaluation.judge.params.temperature
      evaluation.judge.params.max_tokens (absent)
      evaluation.judge.params.temperature (absent)
      fix: Set evaluation.judge.params.max_tokens, evaluation.judge.params.temperature in reprollm.yaml.

28 passed · 0 suppressed · 11 skipped
Result: FAIL (1 critical, 2 warning)
```

### Added (M3, second half)

- Generated rule and profile reference pages with CI freshness checks, a
  documented Level 1 coverage overview, and an enforced 85% CI coverage floor
  (M3-T09, spec §§6, 12, 22–23).
- Complete and intentionally incomplete Level 1 manifests for the HF/vLLM,
  OpenAI judge, and privacy fixtures, with six reviewed JSON snapshots and
  variant-scoped dependency/secret overlays (M3-T08, spec §§3, 6.1, 12, 22).
- Apply `audit.ignore` by canonical rule ID or alias, preserving the original
  severity and mandatory reason in INFO findings. Honor config defaults for
  `fail_on` and `show_passed`, with explicit CLI flags taking precedence;
  suppressed results remain visible and do not affect exit thresholds
  (M3-T07, spec §§1.1, 8, 11, 21).
- Complete built-in profile rule selections and severity overrides, with
  most-derived override origins in audit findings and profile inspection.
  Add 15 explicitly skipped Level 2 placeholders and preserve project-owned
  severity metadata without implementing lock or runtime checks (M3-T06,
  spec §§6.1, 11–12, 18.2).

### Fixed (M3, second half)

- Treat either explicit boolean value for `models.<role>.trust_remote_code` as
  satisfying the repository-wide detection rule, matching the selected
  execution path without encouraging an inaccurate `true` declaration
  ([#1](https://github.com/EnumaElish123/ReproLLM/issues/1), M3-T10, spec §12.4).
- Compare detected profiles with the resolved inheritance closure, so a profile
  inherited by the selected experiment is not reported as undeclared. Clarify
  that unrelated repository capabilities do not need to be added to the
  manifest (M3-T10, spec §§6, 12.3).
- Allow `reprollm profiles show core` while continuing to reject explicitly
  selecting core in a manifest or `audit --profiles` (M3-T06).

### Documentation (M3-T10)

- Mark statically detected model IDs as candidates whose experiment role must
  be verified, add a practical manifest guide, and record Project A/B Level 1
  dogfooding findings and their disposition.

### Added (M3, first half)

- Five training and four privacy rules for training hyperparameters, complete
  LoRA adapters, threat models, nonempty mechanism parameters, privacy metrics
  and attack budgets (M3-T05, spec §§12.10–12.11).
- Six evaluation and four judge rules for metrics and implementation references,
  aggregation, repetitions, safety definitions/budgets, and independently declared
  judge roles and sampling settings (M3-T04, spec §§12.8–12.9).
- Five generation/backend rules and three prompt rules, including conditional
  sampling seeds, vLLM fields, explicit stop/few-shot declarations and prompt
  file existence without reading prompt contents (M3-T03, spec §§12.6–12.7).
- Five Level 1 dataset rules for role declarations, Hugging Face split/subset,
  preprocessing and sampling seeds, with zero-valued seeds preserved (M3-T02,
  spec §12.5).
- Six Level 1 model declaration rules, including per-role API exclusions,
  inference dtype/quantization fallback evidence, adapter detection, and explicit
  remote-code trust declarations (M3-T01, spec §12.4). The trust rule is selected
  by core per the maintainer-approved correction to spec §6.1.

### Fixed (M2-fix corrective sprint, 2026-09-10)

- Audit JSON no longer persists the raw invocation path (absolute paths
  leaked `/home/...`); the target is normalized to `.` or a repository-
  relative POSIX path, and `generated_at` is second-precision UTC (F-01,
  F-02).
- CLI error contract enforced: output-write failures are exit 2 with an
  actionable message; unexpected exceptions exit 3 without a traceback
  (traceback only with `-v`) (F-03).
- A `pyproject.toml` without `[project]`/`[tool.poetry]` no longer counts
  as a dependency manifest (F-04).
- Dependency evidence points at physical declaration lines instead of
  array/mapping indexes; no more `line: 0` (F-05).
- Separator-equivalent keyword spellings (`red team`/`red-team`,
  `dp-sgd`/`dp_sgd`, …) count as one detection concept (F-06).
- Exact `eval`/`evaluation` directory segments are an evaluation signal
  (F-07).
- Scan diagnostics (truncation, syntax errors, unparsed declarations)
  surface on stderr under `-v`; stdout stays one JSON document (F-08).

### Added

- Normative secret fixture corpus (§16.5): positive/negative/env/file
  cases for the M5 redaction classifiers (F-09).

### Changed

- init/doctor domain logic extracted into `core.manifest_scaffold` and
  `core.diagnostics`; CLI commands only parse/prompt/render/exit (F-10).
- Detection signals now come from the profile YAML definitions (user
  overrides honored); only schema-inexpressible semantics stay in Python
  (F-11).

### Added

- Authoritative five-project gold-answer validation matrix (`val.md`), milestone-gated real
  training/inference/API checks, and the M2 corrective sprint plan (M2F-T12).

## [0.1.0] - 2026-09-20

First usable release: **audit Level 0/1 + `init`**.

### Added

- Full `RepoScanner`: gitignore-aware listing with built-in ignores, cached
  reads, python/readme/config/directory helpers, and scan caps (M2-T01).
- `code.clean_tree`, `code.no_untracked`, `code.submodules_initialized`,
  `code.remote_recorded` rules (M2-T02).
- Dependency-declaration parsing (requirements incl. `-r` recursion,
  pyproject PEP 621 + Poetry, environment.yml incl. embedded pip lists,
  Pipfile), lockfile detection, and the six `env.*` rules
  (`dependency_manifest_present`, `lockfile_present`,
  `llm_critical_deps_pinned`, `python_version_declared`,
  `secret_files_ignored`, `reprollm_initialized`) (M2-T03).
- Python AST scanning (imports, HF repo-id constants, `trust_remote_code`,
  Trainer imports) and the forbidden-file matcher of the redaction policy
  (§16.4) (M2-T03).
- Deterministic profile detection per spec §13 with report-only rag/agent;
  detected profiles appear in audit reports and in the Level 0 text output
  with an `init` suggestion (M2-T04, M2-T08).
- Profile loader with inheritance closure, cycle detection, and user
  overrides at `.reprollm/profiles/`; all seven built-in profiles shipped;
  `reprollm profiles list|show` commands (M2-T05).
- `exec.command_declared`, `exec.seed_declared`, `exec.run_recorded`,
  `exec.profile_detection_mismatch` rules and the Level 1 audit path (M2-T06).
- `reprollm init`: manifest scaffolding from detected signals (template-
  rendered, required fields as TODOs, detected HF model ids prefilled,
  `--force`, `--interactive`, `--profiles`) plus `.reprollm/config.yaml`
  and `project-rules.yaml` creation (M2-T07).
- `reprollm` entry point maps `UserError` to exit code 2 (D-11).

### Changed

- Level 0 audits run the full sixteen-rule core profile; all six golden
  fixture snapshots updated (reviewed against the sprint acceptance list).

## [0.0.1] - 2026-09-13

### Added

- Project skeleton, quality tooling (ruff, mypy `--strict`, pytest), CI matrix
  (Linux/macOS/Windows), and trusted-publishing release workflow.
- Pydantic v2 schemas for every persisted document (manifest, lock, run record,
  profile, project rules, config, finding, audit report) with exported JSON
  Schemas and a `reprollm schema export` command.
- Deterministic audit engine (Level 0) with a rule registry, the implicit
  `core` profile, and the first two rules: `code.git_repo`, `code.git_commit`.
- `reprollm audit` (text/JSON output, exit codes per threshold) and
  `reprollm doctor` (environment diagnostics, opt-in network probe).
- Golden fixture repository infrastructure with deterministic commit SHAs and
  snapshot testing.

Not yet usable: `init`, `lock`, `run`, `diff`, `export`, and the full rule
catalog arrive in 0.1.0+ (see `docs/plan/00_architecture_and_decisions.md`).

[Unreleased]: https://github.com/EnumaElish123/ReproLLM/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/EnumaElish123/ReproLLM/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/EnumaElish123/ReproLLM/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/EnumaElish123/ReproLLM/releases/tag/v0.0.1
