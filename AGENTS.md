# AGENTS.md — Working conventions for coding agents on ReproLLM

This file is read by coding agents (Codex CLI, Cursor, and others) working in this repository. It is short on purpose; the authoritative documents are linked.

## 1. What this project is

ReproLLM is a CLI-first, local-first reproducibility toolkit for LLM research experiments: a deterministic audit (`reprollm audit`), a manifest (`reprollm.yaml`), a lockfile (`reprollm.lock`), runtime capture (`reprollm run`), semantic drift detection (`reprollm diff`), export (`reprollm export`), and an opt-in LLM-assisted discovery step (`reprollm discover`).

Principle: **LLM discovers. Rules decide. Runtime verifies.**

## 2. Read before you write

**Every development session starts from the plan documents — no session invents its own scope.**

1. `docs/plan/00_architecture_and_decisions.md` — frozen decisions (`D-nn`). Never violate one; if a task seems to require it, stop and report.
2. `docs/plan/01_specification.md` — normative CLI contract, schemas, rule catalog, redaction policy, diff semantics, test requirements. Field names and behaviors come from here, not from memory.
3. The current sprint document (`docs/plan/M<N>_*.md`) — the task list (T-numbers), each task's acceptance criteria, and this sprint's forbidden zone (禁区). Tasks come from this document, in order; acceptance criteria are turned into tests *before* implementation; the forbidden zone is binding.

If the task description and the specification disagree, the specification wins; say so in the session report or PR.

## 3. Non-negotiables

- **No LLM in the audit path.** Only `reprollm discover` may call a model endpoint, and only behind `--experimental`/config opt-in.
- **No heavy dependencies.** Never add `torch`, `transformers`, `vllm`, `huggingface_hub`, `numpy`, or anything that pulls them. Call the HF Hub HTTP API with `httpx`. Read installed versions with `importlib.metadata`, never `import` the package.
- **No network in tests.** All `httpx` calls are mocked with `respx`; an autouse fixture fails unmocked requests. `git` and `nvidia-smi` go through `reprollm.core.proc.run_cmd` so tests can stub them.
- **Rule IDs are frozen once released.** Renaming requires an `aliases` entry. Never reuse an ID for different semantics.
- **Never write user files** except the artifacts each command owns (`init` → manifest/.reprollm; `lock` → reprollm.lock; `run` → run directory; `rules accept/ignore/add` → project-rules.yaml). Never modify user code, configs, or prompts.
- **Redaction is a security boundary.** Any change to `src/reprollm/core/redaction.py` must keep 100 % branch coverage and add cases to `tests/fixtures/secrets/`. A redaction bypass is a security bug, not a normal bug.
- **Persisted artifacts contain no absolute paths, hostnames, usernames, or secrets.**
- **Deterministic output.** Same inputs → byte-identical JSON (modulo timestamp fields listed in spec §22 T-02). Sort everything you emit.
- **`schema_version` on every persisted document.** Breaking a schema requires a CHANGELOG migration note and a spec update in the same PR.

## 4. Repository map

```text
src/reprollm/
  cli/           typer commands; thin, no business logic
  schemas/       pydantic v2 models (manifest, lock, run_record, profile, project_rules, config, finding, discover, state)
  core/          paths, hashing, git, envinfo, proc, redaction, yaml_io, registry, engine, context, levels, precedence, errors
  rules/         one module per category; each rule is a @register_rule class
  profiles/      built-in *.yaml, loader.py, detect.py
  integrations/  huggingface, vllm, openai_, peft, transformers_
  lock/ run/ diff/ export/ discover/ reporters/
tests/
  unit/          mirrors src layout
  fixtures/repos/      golden repositories (materialized as git repos at test time)
  fixtures/secrets/    redaction corpus
  fixtures/hf_api/     recorded Hub responses
  fixtures/nvidia_smi/ canned outputs
schemas/         exported JSON Schema (generated; CI checks freshness)
docs/            markdown docs; docs/plan/ holds the planning documents
```

## 5. Environment and commands

```bash
uv sync --dev                       # create/refresh the environment (no optional extras exist in Beta)
uv run reprollm --help
uv run pytest -q                    # full suite, no network
uv run pytest -q tests/unit/rules   # subset
uv run ruff check . && uv run ruff format --check .
uv run mypy src/
uv run reprollm schema export --out schemas/   # after changing any schema; commit the result
```

Python ≥ 3.10. Do not use features newer than 3.10 in `src/`.

## 6. How to add things

**A rule** (`src/reprollm/rules/<category>.py`):

```python
@register_rule
class ModelRevisionPinned(Rule):
    id = "model.revision_pinned"
    category = "model"
    default_severity = Severity.CRITICAL
    min_level = 2
    description = "Every model has an exact resolved revision or an explicit pinnability record."
    fix_hint = (
        "Run `reprollm lock` with network access, or set models.<role>.revision to a commit sha."
    )

    def applies(self, ctx: AuditContext) -> bool: ...
    def check(self, ctx: AuditContext) -> list[Finding]: ...
```

Then: add it to the right profile YAML(s) per spec §6.1; add a PASS and a FAIL test in `tests/unit/rules/test_<category>.py`; update fixture `expected/*.json` snapshots if affected (`REPROLLM_UPDATE_SNAPSHOTS=1 uv run pytest tests/...` only after confirming the new output is correct by reading the diff); add a CHANGELOG line.

**A profile**: `src/reprollm/profiles/<name>.yaml` per spec §6; a loader test asserting inheritance closure; `reprollm profiles show <name>` output test.

**An integration**: `src/reprollm/integrations/<name>.py` implementing the `Integration` protocol (spec §14); it must not import the target library.

**A schema field**: update the pydantic model, spec §3–§8 (in the same PR), exported `schemas/`, fixtures, and CHANGELOG.

## 7. Task workflow

Every development session follows the plan documents in `docs/plan/`:

1. **Scope comes from the current sprint doc** (`docs/plan/M<N>_*.md`): implement its tasks (T-numbers) in order, honoring each task's acceptance criteria and the sprint's forbidden zone (§2). A session never invents, reorders into unrelated territory, or "improves" beyond the sprint list; anything found along the way that belongs to a later sprint goes to a backlog note, not into the diff.
2. **Sessions per sprint**: by maintainer decision a sprint is delivered in two sessions (typically first half / second half of the task list); both follow this protocol, and the second session starts from the first session's report.
3. **Per task**: write the tests implied by the acceptance criteria first, then implement, then run the full quality gate (`pytest`, `ruff`, `mypy`, schema freshness). One task = one commit with Conventional Commits (`feat(rules): add model.revision_pinned`, `fix(redaction): handle jwt with padding`, `test(fixtures): add dirty_tree repo`, `docs: …`, `chore: …`). The commit message cites the spec sections implemented, notes fixture/snapshot changes and why, and references the sprint task (e.g. "M2-T03").
4. **Before pushing**: quality gate green **and** the §10 dogfooding run done; then push directly to `main` (the branch/issue/PR flow applies only when the maintainer explicitly asks for a reviewed change). Session reports list: tasks completed with commit hashes, dogfooding delta versus the last baseline, deviations from the sprint doc and why.
5. Do not mix unrelated tasks in one commit, reformat unrelated files, or bump dependencies without being asked.
6. If the spec is wrong or incomplete, open an issue labeled `spec` with a concrete proposal and stop that part of the work; implement the rest. If a sprint task seems to require violating a frozen decision (`D-nn`) or the sprint's forbidden zone, stop and report — never proceed silently.

## 8. Style

- Type hints everywhere; `mypy --strict` clean.
- `ruff` defaults plus `I` (isort), `UP`, `B`, `SIM`; line length 100.
- Pure functions in `core/`; side effects (filesystem, subprocess, HTTP) isolated behind small interfaces that tests can stub.
- Errors: raise `reprollm.core.errors.UserError` (exit 2) for user-fixable problems with an actionable message; anything else is an internal error (exit 3).
- Comments explain *why*, not *what*. No narrating comments. No emojis in code or output except the fixed symbols defined in spec §21.
- User-facing strings: concise, imperative fix hints, always mention the field path or file.

## 9. What "done" means

A task is done when: tests for its acceptance criteria (from the sprint doc) exist and pass; quality gate is green locally and in CI; fixture snapshots were updated deliberately (with the diff reviewed, not blind-regenerated); the CHANGELOG has an entry; the commit references its sprint task and spec sections; and — where the sprint doc requires it — the command has been run against one of the golden fixtures with the expected result pasted into the session report. A *session* is done when its tasks are done, the §10 dogfooding run is recorded, and `main` is pushed with CI green.

## 10. Standing five-project validation gate

Golden fixtures are necessary but not sufficient. **After the quality gate, every development
session MUST read and execute the applicable gates in [`val.md`](val.md).** That document is the
single source of truth for the five pinned repositories, gold answers, commands, milestone resource
gates, and baseline-update policy.

Per session:

1. Run Gate A against all five valid pinned checkouts; at minimum run Level 0 audit, plus every
   non-resource command changed by the session.
2. When the session completes a milestone or prepares a release, also run every Gate B scenario
   activated for that milestone. Real network resolution starts at M4; minimal inference/training,
   including a bounded local judge case, starts at M5; paired semantic diff starts at M6; and
   export/discover plus paid API paths start at M7. Run the complete applicable matrix at M8 and
   every release.
3. Run mutating commands only in disposable clones/worktrees. Use credentials, paid APIs, restricted
   data, and GPU resources only when they are explicitly provisioned for validation.
4. Compare complete rule sets, profiles, hints, paths, diagnostics, and generated manifests with the
   gold answer; summary counts alone are insufficient. Record commands, target SHAs, exit statuses,
   elapsed times, expected/actual results, and every delta in the session report.

A session is not complete if any target is missing, dirty, silently skipped, crashes, or has an
unexplained gold delta. An unavailable GPU, credential, provider, or approved budget marks the
affected resource gate **blocked**, never passed; complete and report every unaffected gate. Update
a pinned commit or gold answer only in a dedicated reviewed change based on independent evidence,
never by copying ReproLLM's current output.
