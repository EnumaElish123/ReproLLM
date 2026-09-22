# ReproLLM

[![CI](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml/badge.svg)](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/reprollm)](https://pypi.org/project/reprollm/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

> Make LLM experiments reproducible.

**Status: alpha. PyPI 0.1.1 supports Audit Level 0/1 and `init`. The development
checkout adds `lock`, runtime capture and Level 2 consistency checks. The 0.2/0.3
releases still await validation gates; `diff` follows in 0.4.0.**

A reproducibility linter, experiment recorder, lockfile system, and drift detector for LLM
research. It records the LLM-specific state that other tools ignore — model revision,
tokenizer and chat-template hashes, prompt hashes, generation parameters,
LLM-as-a-Judge configuration, and the pinnability of closed-source API models — and tells
you why two runs differ.

ReproLLM answers two questions:

1. *Does this experiment contain enough information for someone to understand, rebuild,
   and compare it later?*
2. *Why is this run different from that run?*

Core principle: **LLM discovers. Rules decide. Runtime verifies.** Known reproducibility
requirements are checked by deterministic rules. Runtime capture records what actually
happened, independent of what was declared. An optional, opt-in LLM step only proposes
*candidates* for project-specific parameters; a candidate takes effect only after you
explicitly accept it.

## Quick start (development checkout)

```console
$ pip install .             # inside a checkout of ReproLLM main
$ cd your-llm-experiment
$ reprollm audit .
ReproLLM audit · level 0 · profiles: core

WARNING (3)
  ! env.llm_critical_deps_pinned      vllm is used but not pinned to an exact version (suggestion: vllm==<version>)
      requirements.txt (declared as >=0.10)
      fix: Pin vllm exactly, e.g. `vllm==<version>`.
  …

6 passed · 0 suppressed · 1 skipped
Result: FAIL (3 warning)

Detected profiles: evaluation (medium), inference (high) — run: reprollm init --profiles evaluation,inference

$ reprollm init --profiles evaluation,inference   # or plain `reprollm init`
Created reprollm.yaml (profiles: evaluation, inference; 7 required fields to fill)
Next: fill the TODO fields, then run `reprollm audit .`

$ $EDITOR reprollm.yaml     # fill the TODOs
$ reprollm audit .          # now at level 1: model/dataset/generation gaps
$ reprollm lock .           # resolve revisions and hash declared inputs
$ reprollm audit .          # now at level 2: verify locked identities and files
$ reprollm lock . --check   # network-free manifest/project-rule freshness check
$ reprollm run -- python eval.py --temperature 0.0
$ reprollm runs list
$ reprollm runs show <run-id-or-unique-prefix>
$ reprollm audit .          # compare the latest run against declarations and lock
```

Without any configuration ReproLLM audits your repository at **Level 0** (code
state, dependency pins, secret files, detected experiment types). With a
`reprollm.yaml` manifest it audits at **Level 1** (what your experiment is
missing to be rebuildable). The output above is real output from an evaluation
repository — nothing is fabricated.

The lock records uncertainty explicitly. For example, the API judge in the
FastChat dogfooding manifest has this identity (other fields omitted):

```yaml
models:
  judge:
    provider: openai
    id: gpt-4o-2024-08-06
    pinnability: snapshot_alias
    revision:
      value: null
      source: provider_no_pinning
      confidence: unresolved
```

Read the [lockfile guide](docs/lockfile.md) for provenance, offline mode,
authentication, file changes, and the distinction between exact revisions,
provider snapshot labels, and mutable aliases.

## What it checks

ReproLLM's deterministic rules cover repository and environment state plus the
LLM-specific declarations that commonly disappear from experiment records:
model/provider identity, dtype and quantization, dataset split and preprocessing,
prompt sources, generation and backend settings, evaluation metrics, judge
configuration, training hyperparameters, and privacy assumptions. The complete
[rule catalog](docs/rules.md) records each rule's severity, level, fix, and profile
membership; the [profile catalog](docs/profiles.md) shows inheritance, required
fields, severity overrides, and detection signals.

The [manifest guide](docs/manifest.md) explains model and dataset roles,
generation versus judge settings, implementation references, execution
bindings, and how to review repository-wide detections in multi-workflow codebases.

Level 2 verifies lock freshness and compares file hashes, observed generation
parameters, model identities, LLM package versions and accepted custom fields
against the latest valid run. The [runtime guide](docs/run.md) explains bindings,
environment policies, redacted snapshots and how to share selected records.

## Commands

| Command | Status | Purpose |
|---|---|---|
| `reprollm audit` | **usable** (Level 0/1/2 on main) | deterministic reproducibility audit |
| `reprollm init` | **usable** | create `reprollm.yaml` from detected experiment profiles |
| `reprollm doctor` | **usable** | environment diagnostics |
| `reprollm profiles list/show` | **usable** | inspect the seven built-in profiles |
| `reprollm lock` | **usable on main**, planned for 0.2.0 | resolve models/datasets/prompts into a reviewable `reprollm.lock` |
| `reprollm run -- CMD` | **usable in development**, planned for 0.3.0 | execute a command and record runtime truth |
| `reprollm runs list/show` | **usable in development**, planned for 0.3.0 | inspect saved runtime evidence |
| `reprollm diff A B` | 0.4.0 | semantic drift between two runs or lockfiles |
| `reprollm export` | 0.5.0 | generate a `REPRODUCIBILITY.md` for your paper artifact |

ReproLLM is CLI-first, local-first, and collects no telemetry. The only network calls are
revision resolution against provider APIs (`lock`), an opt-in LLM endpoint
(`discover --experimental`), an opt-in `doctor --check-network`, and version verification
you explicitly request (`lock --verify-api`).

## Roadmap

The architecture and the full Beta specification are frozen in the repository:

- [`docs/plan/00_architecture_and_decisions.md`](docs/plan/00_architecture_and_decisions.md) —
  product definition, boundaries, and the decision register (D-01 … D-42)
- [`docs/plan/01_specification.md`](docs/plan/01_specification.md) — CLI contract, schemas,
  rule catalog, redaction policy, diff semantics

- [`docs/index.md`](docs/index.md) — documentation index
- [`docs/adoption.md`](docs/adoption.md) — monthly adoption metrics (updated from week 1)

Milestones: M1 foundation → M2 audit core + `init` → M3 rules + profiles → M4 `lock` →
M5 `run` + redaction → M6 `diff` → M7 `export`/`discover` → M8 Beta (`0.5.0`).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The repository is developed in the open under
[Apache-2.0](LICENSE).

## License

[Apache-2.0](LICENSE)
