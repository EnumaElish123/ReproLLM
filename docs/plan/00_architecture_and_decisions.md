# ReproLLM — Architecture and Frozen Decisions

> Status: **FROZEN for Beta (v0.5.0)**. Changes require a new entry in the Decision Register (§6) and a maintainer sign-off. Coding agents MUST NOT deviate from this document. Where this document and `01_specification.md` disagree, this document wins on *intent*, the specification wins on *field names and exact behavior*.
>
> Last updated: 2026-09-03

---

## 1. Purpose of this document

This is the invariant layer of the ReproLLM plan. It records **what the product is, what it is not, and every architectural decision already taken**, so that implementation work (by humans or coding agents) never has to re-derive or re-litigate them.

Read order for any implementer:

1. this document (`00`);
2. `01_specification.md` (normative schemas, CLI contract, rule catalog);
3. `AGENTS.md` (working conventions);
4. the current sprint document (`M1` … `M8`, `M9-M12`).

---

## 2. Product definition

**ReproLLM** is an open-source, CLI-first, local-first reproducibility toolkit for LLM research experiments.

Package / command / org / PyPI name: `reprollm`.

One-line goal: **Make LLM experiments reproducible.**

Positioning statement (use verbatim in README and applications):

> A reproducibility linter, experiment recorder, lockfile system, and drift detector for LLM research. It records the LLM-specific state that other tools ignore — model revision, tokenizer and chat-template hashes, prompt hashes, generation parameters, LLM-as-a-Judge configuration, and the pinnability of closed-source API models — and tells you why two runs differ.

The two questions ReproLLM answers:

1. *Does this experiment contain enough information for someone to understand, rebuild and compare it later?*
2. *Why is this run different from that run?*

### 2.1 Differentiation focus (D-38)

Public narrative, README, and the Codex-for-OSS application lead with the **five LLM-specific states** that no adjacent tool records together:

1. model identity: HF revision, tokenizer revision, chat-template hash, dtype, quantization, adapter;
2. prompt identity: content hashes, not paths;
3. generation parameters and inference backend version;
4. LLM-as-a-Judge configuration: judge model pinnability, judge prompt hash, judge sampling parameters, repetitions;
5. closed-source API pinnability: `exact | snapshot_alias | unpinnable`, never faked.

Everything else (git state, dependency pins, environment snapshot) is necessary but is not the headline.

### 2.2 Adjacent tools (for positioning, not competition)

| Tool | What it does | Relationship |
|---|---|---|
| MLflow / W&B / TensorBoard | metrics tracking, dashboards | not a replacement; ReproLLM records identity and drift, not metrics |
| reprokit-ml | generic ML seed + env freeze + data Merkle hash | no LLM-specific state, no audit rules |
| EvalRepro | hash-only drift of evaluation input contracts | narrower; complementary |
| detllm | deterministic-inference variance checks | complementary (checks outputs; we check inputs/state) |
| RepDL / Gensyn REE | bitwise-deterministic kernels | different layer |

---

## 3. Non-goals for Beta

ReproLLM Beta does **not**:

- run benchmarks, leaderboards, or compare model quality;
- train, serve, schedule, or manage checkpoints;
- provide a hosted service, dashboard, or metrics visualization;
- let an LLM generate or decide audit rules;
- auto-fix user files (only `init`, `lock`, `run`, `rules accept` write files, and only their own artifacts);
- parse README or paper prose for consistency (post-Beta, see D-17, D-26);
- compute dataset content fingerprints (D-22);
- support languages other than Python as analysis targets (D-33);
- collect telemetry of any kind (D-03).

---

## 4. Core principle

> **LLM discovers. Rules decide. Runtime verifies.**

1. Known reproducibility requirements are checked by **deterministic rules** (Python code, tested, versioned).
2. Known experiment types are expressed as **Profiles** (YAML) that select rules and required fields.
3. Known frameworks/providers are supported by **Integrations** (detection, resolution, capture hooks).
4. Unknown project-specific variables may be **discovered** by an LLM, but discovery only produces *candidates*.
5. A candidate becomes a **Project Rule** only after explicit user acceptance; from then on it is checked deterministically.
6. **Runtime capture** records what actually happened, independent of what was declared.

Corollary: the same repository at the same commit MUST produce byte-identical audit JSON (modulo timestamps) regardless of machine, unless the environment itself is part of what is being checked (Level 0 environment rules), in which case differences are explained by evidence.

---

## 5. Architecture overview

```text
                 ┌──────────────────────────┐
   user writes → │  reprollm.yaml  (Intent) │ ─────────────┐
                 └──────────────────────────┘              │
                              │ reprollm lock              │
                              ▼                            │
                 ┌──────────────────────────┐              │
                 │  reprollm.lock (Resolved)│ ────────┐    │
                 └──────────────────────────┘         │    │
                              │ reprollm run -- cmd   │    │
                              ▼                       ▼    ▼
                 ┌──────────────────────────┐   ┌──────────────────┐
                 │ .reprollm/runs/<id>/     │ → │  ExperimentState │
                 │ run.json (Runtime truth) │   │  (unified model) │
                 └──────────────────────────┘   └────────┬─────────┘
                                                         │
                       ┌────────────────┬────────────────┼────────────────┐
                       ▼                ▼                ▼                ▼
                 reprollm audit    reprollm diff    reprollm export   (consistency
                 (rules engine)    (semantic drift) (REPRODUCIBILITY.md)  findings)

   side channel (opt-in, experimental):
   repo files ─→ reprollm discover ─→ candidates.json ─→ reprollm rules accept ─→ .reprollm/project-rules.yaml
```

Layers:

- **Schemas** (`reprollm.schemas`): pydantic v2 models for manifest, lock, run record, profile, project rules, config, finding, discover output, ExperimentState. JSON Schema exported to `schemas/`.
- **Core** (`reprollm.core`): paths, hashing, git, environment info, redaction, YAML I/O, rule registry, audit engine, levels, precedence.
- **Rules** (`reprollm.rules`): one module per category; each rule is a registered class.
- **Profiles** (`reprollm.profiles`): built-in YAML + loader + deterministic detection.
- **Integrations** (`reprollm.integrations`): huggingface, vllm, openai, peft, transformers; each implements optional `detect()`, `resolve()`, `capture()`.
- **Lock / Run / Diff / Export / Discover**: feature packages built on Core and Schemas.
- **Reporters**: text (rich) and JSON.
- **CLI** (`reprollm.cli`): typer app; thin; no business logic.

---

## 6. Decision Register

Each decision has an ID (`D-nn`), the decision, rationale, and consequences for implementers. IDs are stable; superseding a decision adds a new entry and marks the old one `superseded by D-xx`.

### Product and scope

**D-01 Name and identifiers.** Project *ReproLLM*; CLI `reprollm`; PyPI `reprollm`. Repository location **superseded by D-43** (2026-09-10). Verified available 2026-09-03.
*Consequence:* import root `reprollm`; user directory `.reprollm/`; env var prefix `REPROLLM_`.

**D-43 Canonical repository identity (supersedes the location clause of D-01).**
The project is hosted at `github.com/EnumaElish123/ReproLLM` under the maintainer's
account; no dedicated `reprollm` organization will be created for the Beta. Every
normative and public file (pyproject URLs, README badges, contribution and security
links, changelog references) uses this single canonical identity; a consistency test
enforces it.
*Rationale:* the organization planned in D-01 was never created; migrating before the
first PyPI release was considered and declined by the maintainer on 2026-09-10.
*Consequence:* a future migration requires a new decision entry, a reviewed sweep of
all references, and re-configuration of PyPI trusted publishing in the same change.

**D-02 License and visibility.** Apache-2.0. Repository public from day 1 (W1).
*Rationale:* maintenance history is itself a deliverable; early visibility costs nothing.

**D-03 CLI-first, local-first, zero telemetry.** No hosted component, no dashboard, no usage reporting. The only network calls are: `lock` (resolving revisions against provider APIs), `discover` (opt-in LLM endpoint), `doctor --check-network` (opt-in).
*Consequence:* every network call MUST be avoidable with `--offline` or by not invoking the feature, and MUST be mockable in tests.

**D-04 Deterministic audit.** Audit results depend only on repository contents, manifest, lock, run records, and (for Level 0 environment rules) the local environment. No LLM in the audit path.

**D-05 Four-layer rule system.** `Core` (always) + `Profiles` (experiment type) + `Integrations` (framework/provider) + `Project Rules` (repository-specific, user-accepted).

**D-06 Composable profiles; Beta ships seven.** An experiment declares a *list* of profiles. Built-in for Beta: `core` (implicit), `inference`, `evaluation`, `llm_judge`, `finetuning`, `safety`, `privacy`. Deferred: `rag`, `agent`, `privacy_inference`.

**D-17 Consistency checks are structured-source only in Beta.** Manifest vs lock vs run-captured values (CLI/config/env via declared bindings). README/paper prose is out of scope.

**D-22 No dataset content fingerprint in Beta.** Lock records HF dataset `revision`, `subset`, `split`; `content_fingerprint.status: not_computed`. An INFO finding reports this.

**D-23 No autofix in Beta.** Findings carry `fix_hint` text only.

**D-24 `discover` is experimental and opt-in.** Requires `--experimental`; prints the exact file list to be sent and requires `--yes` or interactive confirmation; OpenAI-compatible endpoint only; output is a candidates file; acceptance is a separate command. 3-day time box in W7; cut if it slips.

**D-25 Level 1/2 profile detection is deterministic and belongs to `audit`/`init`, not `discover`.** AST imports, dependency names, config/directory names, README keywords.

**D-26 Paper–code consistency is post-Beta.** `discover` reserves a `--paper` option (rejected with a clear message in Beta).

**D-33 Python-only analysis target in Beta.** Static analysis scans `*.py`, `pyproject.toml`, `requirements*.txt`, `environment.yml`, YAML/JSON/TOML configs.

**D-38 Positioning narrative.** See §2.1. README, docs, and application text lead with LLM-specific states.

### Rules, severity, audit semantics

**D-07 Rules are Python classes; profiles are YAML.** A rule has `id`, `category`, `default_severity`, `min_level`, `description`, `fix_hint`, `applies(ctx)`, `check(ctx) -> list[Finding]`, registered via decorator. Profiles list rule IDs, required fields, severity overrides, and detection signals.

**D-08 Rule ID scheme.** Dotted lowercase: `<category>.<snake_name>` (e.g. `model.revision_pinned`). Categories: `code, env, exec, model, dataset, gen, prompt, eval, judge, train, privacy, consistency, project`. IDs are frozen once released; renames add `aliases: [...]` and keep the old ID resolvable in suppressions.

**D-09 Severity vocabulary.** `CRITICAL | WARNING | INFO | PASS`. No numeric score in Beta.
- **CRITICAL**: missing or inconsistent information makes the *identity* of the experiment ambiguous (which model/data/prompt/generation parameters were actually used).
- **WARNING**: identity is determinable but reproduction is materially harder (unpinned deps, dirty tree, tokenizer not locked).
- **INFO**: advisory, not computed, or suppressed.
- **PASS**: rule applied and satisfied.

**D-10 Severity ownership.** Rule sets `default_severity`; profile may override via `severity_overrides`; user may suppress a rule ID in `.reprollm/config.yaml` with a mandatory `reason`. Suppressed findings are still emitted with `status: suppressed` at INFO.

**D-11 Exit codes.** `0` success / nothing above threshold; `1` findings at or above `--fail-on` threshold (audit) or stale lock (`lock --check`) or drift at/above `--fail-on` (diff); `2` usage/validation error; `3` internal error. `run` propagates the child process exit code; if ReproLLM itself fails after the child finished, it still writes the record and exits with the child code.

**D-12 Leveled audit.**
- **Level 0** — no `reprollm.yaml`: Core rules (`code.*`, `env.*`) + deterministic profile detection reported as INFO + INFO suggesting `init`.
- **Level 1** — manifest present: Level 0 + all presence rules selected by declared profiles + project rules.
- **Level 2** — lock and/or run records present: Level 1 + consistency rules.
Level is auto-detected; `--level` may force a lower level.

**D-16 Precedence and conflicts.** Effective value precedence: `runtime CLI > config file > manifest > default`. Precedence determines the *effective* value for diff/export only. Any disagreement between sources produces a `consistency.*` finding; ReproLLM never silently overrides.

### Data model

**D-13 Manifest = intent.** `reprollm.yaml` is flat (no provenance), human-authored. `models`, `datasets`, `prompts` are **role-keyed maps** (`primary`, `judge`, `attacker`, `eval`, `train`, `system`, …). Profiles declare which roles/fields are required.

**D-14 Lock = resolved reality.** `reprollm.lock` is YAML (reviewable, diffable). Only *resolved* fields carry a provenance object `{value, source, confidence, resolved_at}`; declared fields pass through unchanged. The lock stores `manifest_sha256` and `project_rules_sha256` for staleness detection.

**D-15 Run record = runtime truth.** `.reprollm/runs/<run_id>/run.json` (JSON) plus snapshots of manifest, lock, declared files (text ≤ 1 MiB), redacted dirty patch, optional stdout/stderr. `run_id = <UTC yyyymmddThhmmssZ>-<6 hex>`.

**D-21 Closed-source API pinnability.** `pinnability: exact | snapshot_alias | unpinnable`. Dated snapshot identifiers (e.g. `gpt-4o-2024-08-06`) are `snapshot_alias`; bare aliases are `unpinnable`; HF commit SHAs are `exact`. Never fabricate a revision.

**D-27 ExperimentState.** Single internal pydantic model into which manifest, lock, and run record are projected. `audit` (Level 2), `diff`, and `export` operate only on ExperimentState. Leaves carry `{value, source, confidence}`.

**D-28 Drift severity table.** `reprollm/diff/drift_severity.yaml` maps field-path patterns to `HIGH | MEDIUM_HIGH | MEDIUM | LOW | NONE`, with version-component semantics for package versions. Profiles may override.

**D-39 Schema versioning.** Every persisted document has integer `schema_version`. Pre-1.0 may introduce breaking changes only at minor version bumps and only with a migration note in `CHANGELOG.md`; readers MUST reject unknown newer versions with a clear message.

**D-40 Bindings syntax.** Manifest `bindings:` maps a manifest field path to runtime locations: `cli: "--flag"`, `config: "<path>:<dotted.key>"`, `env: "VAR"`. Project rules may carry the same `bindings` block.

### Runtime capture and security

**D-18 Deterministic capture only.** `run` records argv, cwd, exit code, timing, git state, environment (per D-20), hardware, scheduler variables, and hashes/snapshots of every argv token that resolves to an existing file (plus declared `execution.config_files`). Individual parameter values are observed **only** via declared bindings. No heuristic flag parsing.

**D-19 Secret redaction is P0.** Normative policy in `01_specification.md §16`: segment-based env var name matching, value-pattern matching applied to argv/snapshots/patch/env values, forbidden file patterns never snapshotted, 100 % branch coverage on the redaction module, positive and negative corpus in `tests/fixtures/secrets/`.

**D-20 Environment capture is allowlist-by-default.** Only allowlisted prefixes have values recorded; known-secret names are recorded as `{present: true}`; everything else is omitted. `--env-capture all` records all names with redacted values.

### Engineering

**D-29 Tech stack.** Python ≥ 3.10; `uv` for environments and locking; `hatchling` build backend; `typer` CLI; `pydantic` v2; `ruff` (lint+format); `mypy --strict` on `src/`; `pytest` + `pytest-cov`; `rich` output; `jinja2` templates; `httpx` for HTTP; `pyyaml`; `packaging`; `tomli` (py<3.11). GitHub Actions CI; PyPI trusted publishing.

**D-30 Zero heavy dependencies.** `pip install reprollm` MUST NOT pull torch, transformers, vllm, or `huggingface_hub`. HF Hub API is called directly via `httpx`. Git via the `git` CLI (subprocess). Installed package versions via `importlib.metadata` (never import the package). GPU info via `nvidia-smi` parsing.

**D-31 Platform tiers.** Linux: tier 1 (all features, CI full). macOS: tier 2 (CI runs unit tests; GPU features return "not available"). Windows: best-effort (CI runs core unit tests; `run` GPU/SLURM capture not guaranteed).

**D-32 Testing policy.** No real network in CI (httpx mocked with `respx`; `nvidia-smi`/`git` shelled out to fixtures or mocked). Golden fixture repositories under `tests/fixtures/repos/` with expected audit JSON snapshots per level. Every rule has at least one PASS and one FAIL test. Redaction module: 100 % branch coverage. Fixture git repos are created at test time with fixed `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`/name/email for deterministic SHAs.

**D-34 Release cadence.** One tag per sprint, every tag published to PyPI: `0.0.1` (W1, name reservation, README says "not yet usable") → `0.1.0` (W2) → `0.1.x` (W3) → `0.2.0` (W4) → `0.3.0` (W5) → `0.4.0` (W6) → `0.5.0a1` (W7, PEP 440 pre-release; `pip install --pre`) → `0.5.0` (W8, **the Beta**; published as a final PyPI release so that `pip install reprollm` resolves to it, GitHub Release titled "v0.5.0 — Beta"). Tags `vX.Y.Z`.
*Rationale:* PEP 440 pre-releases are skipped by `pip install` unless `--pre` is given; the Beta must be the default install. The pre-1.0 major already signals instability.

**D-35 Process.** Conventional Commits; squash merge; branch `m<N>/t<NN>-<slug>`; GitHub Milestones `M1`–`M8` mirror sprint docs; issues created from sprint task lists at sprint start; PR template checklist (spec section, tests, fixtures updated, CHANGELOG entry, no network in tests); Keep a Changelog.

**D-36 Docs.** Markdown under `docs/`; `mkdocs-material` optional in W8. Quick Start must be runnable against `examples/`.

**D-37 Adoption metrics from W1.** `docs/adoption.md` tracks monthly: PyPI downloads (pypistats), GitHub dependents, external issues/PRs, known repositories/papers using ReproLLM.

### Process meta

**D-41 Human review budget.** ~8–10 h/week of maintainer time; 6–10 PRs/week. Quality gating relies on fixtures and snapshot tests, not line-by-line review. Any PR touching `core/redaction.py`, `core/engine.py`, or a schema requires explicit maintainer review.

**D-42 One-week buffer.** A buffer week (W8.5, 2026-11-02 → 11-08) follows W8. The national holiday 2026-10-01 → 10-07 overlaps W4/W5; W4 is planned lighter.

---

## 7. Storage layout (user repository)

```text
<repo>/
├── reprollm.yaml                 # manifest (intent), committed
├── reprollm.lock                 # lockfile (resolved), committed
└── .reprollm/
    ├── config.yaml               # tool config: suppressions, run options, discover endpoint
    ├── project-rules.yaml        # accepted project-specific rules
    ├── profiles/                 # optional user profiles (override built-ins by name)
    ├── discover/<ts>.json        # discovery candidates (experimental)
    └── runs/<run_id>/
        ├── run.json
        ├── manifest.yaml         # snapshot
        ├── lock.yaml             # snapshot (if lock existed)
        ├── files/<sha256>        # snapshots of declared/argv files (text ≤ 1 MiB)
        ├── patch.diff            # redacted `git diff` if tree was dirty
        ├── stdout.log            # only with --capture-output
        └── stderr.log
```

Recommendation to users: commit `reprollm.yaml`, `reprollm.lock`, `.reprollm/config.yaml`, `.reprollm/project-rules.yaml`; commit `.reprollm/runs/` selectively (it is small and text-only by design).

---

## 8. Repository layout (this project)

```text
reprollm/
├── pyproject.toml
├── uv.lock
├── AGENTS.md  README.md  LICENSE  CHANGELOG.md  CONTRIBUTING.md  SECURITY.md  CODE_OF_CONDUCT.md
├── .github/workflows/{ci.yml,release.yml}   .github/PULL_REQUEST_TEMPLATE.md  ISSUE_TEMPLATE/
├── src/reprollm/
│   ├── __init__.py                 # __version__
│   ├── cli/                        # typer commands (thin)
│   ├── schemas/                    # pydantic models
│   ├── core/                       # paths, hashing, git, envinfo, redaction, yaml_io, registry, engine, levels, precedence, errors
│   ├── rules/                      # code.py env.py exec_.py model.py dataset.py gen.py prompt.py eval_.py judge.py train.py privacy.py consistency.py project.py
│   ├── profiles/                   # *.yaml, loader.py, detect.py
│   ├── integrations/               # base.py huggingface.py vllm.py openai_.py peft.py transformers_.py
│   ├── lock/                       # resolver.py hf_resolver.py api_resolver.py local_resolver.py
│   ├── run/                        # wrapper.py capture.py hardware.py slurm.py
│   ├── diff/                       # state.py differ.py severity.py drift_severity.yaml
│   ├── export/                     # exporter.py templates/REPRODUCIBILITY.md.j2
│   ├── discover/                   # collector.py client.py candidates.py
│   └── reporters/                  # text.py json_.py
├── schemas/                        # exported JSON Schema (generated, committed)
├── tests/
│   ├── unit/ …
│   ├── fixtures/repos/{hf_vllm_eval,openai_judge_eval,privacy_custom_params,not_a_git_repo,dirty_tree,no_deps_file}/
│   ├── fixtures/secrets/{positive.txt,negative.txt,env_cases.yaml}
│   └── fixtures/hf_api/*.json      # recorded Hub API responses
├── docs/                           # markdown docs, adoption.md
└── examples/                       # W8: copies of golden fixtures with READMEs
```

---

## 9. Security and privacy posture

- Redaction (D-19, D-20) applies to every artifact ReproLLM writes: run records, snapshots, patches, exported markdown, discover payloads.
- `discover` sends repository content to a user-configured endpoint only after showing the exact file list and receiving confirmation; it never sends files matching secret patterns or forbidden names.
- No hostnames, usernames, or absolute home paths in committed artifacts by default; `run.json` stores `cwd` relative to the repo root, and `hostname_sha256` only.
- `SECURITY.md` defines private disclosure; redaction bypasses are treated as security bugs.

---

## 10. Roadmap summary

| Sprint | Dates (2026) | Theme | Version |
|---|---|---|---|
| M1 | 09-07 → 09-13 | Foundation: repo, CI, schemas, registry, reporters, fixtures skeleton | 0.0.1 |
| M2 | 09-14 → 09-20 | Audit Core (`code.*`, `env.*`), profile detection, `init`, Level 0/1 engine | 0.1.0 |
| M3 | 09-21 → 09-27 | LLM-specific rules, 7 profiles, overrides/suppression, JSON output | 0.1.x |
| M4 | 09-28 → 10-04 | `lock`: HF resolver, hashes, pinnability, offline, staleness, Level 2 | 0.2.0 |
| M5 | 10-05 → 10-11 | `run`: capture, redaction (P0), bindings, `runs` | 0.3.0 |
| M6 | 10-12 → 10-18 | ExperimentState, semantic `diff`, drift table, consistency rules | 0.4.0 |
| M7 | 10-19 → 10-25 | `export`, experimental `discover`, `rules`, dogfooding on A/B/C | 0.5.0a1 |
| M8 | 10-26 → 11-01 | Stabilization, docs, examples, Beta release | 0.5.0 (Beta) |
| W8.5 | 11-02 → 11-08 | Buffer | — |
| M9–M12 | 11-09 → 12-06 | Adoption: GitHub Action, artifact-checklist export, ecosystem integrations, first application | 0.6.x |

---

## 11. Glossary

- **Manifest** — `reprollm.yaml`; what the researcher intends to run.
- **Lock / Lockfile** — `reprollm.lock`; what ReproLLM resolved at a point in time.
- **Run record** — `.reprollm/runs/<id>/run.json`; what actually executed.
- **ExperimentState** — internal unified projection of the three above.
- **Rule** — deterministic check with a stable ID and severity.
- **Profile** — YAML bundle of rules, required fields, overrides, and detection signals for an experiment type.
- **Integration** — framework/provider-specific detection, resolution, and capture logic.
- **Project Rule** — user-accepted repository-specific rule stored in `.reprollm/project-rules.yaml`.
- **Candidate** — a discovery suggestion that has not been accepted.
- **Binding** — declaration of where a manifest field's value lives at runtime (CLI flag, config key, env var).
- **Level (0/1/2)** — audit depth determined by which documents exist.
- **Pinnability** — whether a model identifier can be resolved to an immutable artifact.
- **Drift** — a difference between two ExperimentStates, classified by severity.
