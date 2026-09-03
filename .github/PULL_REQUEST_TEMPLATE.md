<!--
PR checklist (see AGENTS.md §7). Fill in every section; CI enforces the technical items.
-->

Closes #

## Spec sections implemented

<!-- e.g. "spec §12.4 model.*, §6.1 profile wiring" — cite docs/plan/01_specification.md -->

## Test summary

<!-- which acceptance criteria are covered by tests; paste the FAIL output of any new
     rule's message + fix_hint here (required for rule PRs) -->

## Fixtures / snapshots

<!-- were tests/fixtures/**/expected/*.json or other snapshots updated? why is the new
     output correct? (REPROLLM_UPDATE_SNAPSHOTS=1 output diff must be reviewed) -->

## Checklist

- [ ] Tests written for the acceptance criteria and passing
- [ ] `pytest -q` passes with no network access
- [ ] `ruff check . && ruff format --check .` pass
- [ ] `mypy src/` passes (`--strict`); any new `type: ignore` has an inline reason
- [ ] No new heavy dependencies (torch / transformers / vllm / huggingface_hub / numpy
      or anything that pulls them)
- [ ] Persisted artifacts: sorted keys, relative POSIX paths, no hostnames/usernames/
      absolute paths/secrets; `schema_version` present on new documents
- [ ] `schemas/` re-exported (`reprollm schema export --out schemas/`) and committed,
      if any schema changed
- [ ] CHANGELOG entry added under `Unreleased`
- [ ] No files modified outside the issue's scope
