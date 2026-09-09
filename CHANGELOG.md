# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/EnumaElish123/ReproLLM/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/EnumaElish123/ReproLLM/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/EnumaElish123/ReproLLM/releases/tag/v0.0.1
