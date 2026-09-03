# Contributing to ReproLLM

Thank you for considering a contribution. ReproLLM is developed in the open, and the
process below keeps the project deterministic and reviewable.

## Read first

- [`AGENTS.md`](AGENTS.md) — working conventions (read order, non-negotiables, how to add
  rules/profiles/integrations, style). It applies to human contributors too.
- [`docs/plan/00_architecture_and_decisions.md`](docs/plan/00_architecture_and_decisions.md) —
  frozen decisions (`D-nn`). Never violate one; if a task seems to require it, open an
  issue instead.
- [`docs/plan/01_specification.md`](docs/plan/01_specification.md) — the normative CLI
  contract and schemas. **If a task description and the specification disagree, the
  specification wins; say so in your PR.**

## Development setup

```bash
git clone https://github.com/EnumaElish123/ReproLLM.git
cd ReproLLM
uv sync --dev          # creates .venv with a suitable Python (>= 3.10)
```

## Running the quality gate

Run all of these before opening a PR; CI runs the same set:

```bash
uv run pytest -q                             # full test suite, no network
uv run ruff check . && uv run ruff format --check .
uv run mypy src/
uv run reprollm schema export --out /tmp/schemas && diff -r schemas /tmp/schemas
```

Conventions enforced by the gate:

- **No network in tests.** All `httpx` calls are mocked with `respx`; an autouse fixture
  fails unmocked requests. `git` and `nvidia-smi` go through `reprollm.core.proc.run_cmd`
  so tests can stub them.
- **No heavy dependencies.** Never add `torch`, `transformers`, `vllm`,
  `huggingface_hub`, `numpy`, or anything that pulls them.
- **Deterministic output.** Same inputs must produce byte-identical JSON (modulo
  timestamp fields listed in spec §22 T-02). Sort everything you emit.
- **Type hints everywhere**; `mypy --strict` must pass on `src/`.

## Pull requests

1. One task = one issue = one branch (`m<N>/t<NN>-<slug>`) = one PR. Keep PRs under
   ~400 changed lines where possible; split otherwise.
2. Start from the acceptance criteria: write the tests they imply, then implement.
3. Commit with [Conventional Commits](https://www.conventionalcommits.org/):
   `feat(rules): add model.revision_pinned`, `fix(redaction): handle jwt with padding`,
   `test(fixtures): add dirty_tree repo`, `docs: …`, `chore: …`.
4. The PR template checklist must be completed: spec sections implemented, test summary,
   fixture/snapshot changes and why, CHANGELOG entry, no network in tests, no new heavy
   dependencies.
5. If you believe the specification is wrong or incomplete, open an issue labeled `spec`
   with a concrete proposal and stop that part of the work; implement the rest.

## Adding rules, profiles, integrations

See the recipes in [`AGENTS.md` §6](AGENTS.md). In short: a rule is a Python class
registered with `@register_rule` plus PASS and FAIL tests plus the profile YAML wiring; a
profile is a YAML file with loader tests; an integration must never import its target
library.

## Security

Redaction (`src/reprollm/core/redaction.py`) is a security boundary. Any change there
must keep 100 % branch coverage and add cases to `tests/fixtures/secrets/`. A redaction
bypass is a security bug, not a normal bug — see [SECURITY.md](SECURITY.md) for private
disclosure.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
