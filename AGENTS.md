# AGENTS.md — Working conventions for coding agents on ReproLLM

This file is read by coding agents (Codex CLI, Cursor, and others) working in this repository. It is short on purpose; the authoritative documents are linked.

## 1. What this project is

ReproLLM is a CLI-first, local-first reproducibility toolkit for LLM research experiments: a deterministic audit (`reprollm audit`), a manifest (`reprollm.yaml`), a lockfile (`reprollm.lock`), runtime capture (`reprollm run`), semantic drift detection (`reprollm diff`), export (`reprollm export`), and an opt-in LLM-assisted discovery step (`reprollm discover`).

Principle: **LLM discovers. Rules decide. Runtime verifies.**

## 2. Read before you write

1. `docs/plan/00_architecture_and_decisions.md` — frozen decisions (`D-nn`). Never violate one; if a task seems to require it, stop and report.
2. `docs/plan/01_specification.md` — normative CLI contract, schemas, rule catalog, redaction policy, diff semantics, test requirements. Field names and behaviors come from here, not from memory.
3. The sprint document you were assigned (`docs/plan/M<N>_*.md`) — your task list, acceptance criteria, and this sprint's forbidden zone.

If the task description and the specification disagree, the specification wins; say so in the PR.

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

1. One task = one issue = one branch `m<N>/t<NN>-<slug>` = one PR. Keep PRs under ~400 changed lines where possible; split otherwise.
2. Start by reading the acceptance criteria and writing the tests they imply. Then implement. Then run the full quality gate (`pytest`, `ruff`, `mypy`, schema freshness).
3. Commit with Conventional Commits: `feat(rules): add model.revision_pinned`, `fix(redaction): handle jwt with padding`, `test(fixtures): add dirty_tree repo`, `docs: …`, `chore: …`.
4. PR description must include: the spec sections implemented (e.g. "spec §12.4, §6.1"), a test summary, whether fixtures/snapshots changed and why, and a CHANGELOG entry under `Unreleased`.
5. Do not open PRs that mix unrelated tasks, reformat unrelated files, or bump dependencies without being asked.
6. If you discover the spec is wrong or incomplete, open an issue labeled `spec` with a concrete proposal and stop that part of the work; implement the rest.

## 8. Style

- Type hints everywhere; `mypy --strict` clean.
- `ruff` defaults plus `I` (isort), `UP`, `B`, `SIM`; line length 100.
- Pure functions in `core/`; side effects (filesystem, subprocess, HTTP) isolated behind small interfaces that tests can stub.
- Errors: raise `reprollm.core.errors.UserError` (exit 2) for user-fixable problems with an actionable message; anything else is an internal error (exit 3).
- Comments explain *why*, not *what*. No narrating comments. No emojis in code or output except the fixed symbols defined in spec §21.
- User-facing strings: concise, imperative fix hints, always mention the field path or file.

## 9. What "done" means

A task is done when: tests for its acceptance criteria exist and pass; quality gate is green locally and in CI; fixture snapshots were updated deliberately; the CHANGELOG has an entry; the PR references its issue and spec sections; and — where the sprint doc requires it — the command has been run against one of the golden fixtures with the expected result pasted into the PR.
