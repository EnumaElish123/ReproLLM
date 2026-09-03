# ReproLLM

> Make LLM experiments reproducible.

**Status: pre-alpha (0.0.x). Not yet usable. First usable release: 0.1.0.**

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

## Planned commands (Beta)

| Command | Purpose |
|---|---|
| `reprollm audit` | deterministic reproducibility audit (Level 0 / 1 / 2) |
| `reprollm init` | create `reprollm.yaml` from detected experiment profiles |
| `reprollm lock` | resolve models/datasets/prompts into a reviewable `reprollm.lock` |
| `reprollm run -- CMD` | execute a command and record runtime truth |
| `reprollm diff A B` | semantic drift between two runs or lockfiles |
| `reprollm export` | generate a `REPRODUCIBILITY.md` for your paper artifact |

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

Milestones: M1 foundation → M2 audit core + `init` → M3 rules + profiles → M4 `lock` →
M5 `run` + redaction → M6 `diff` → M7 `export`/`discover` → M8 Beta (`0.5.0`).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The repository is developed in the open under
[Apache-2.0](LICENSE).

## License

[Apache-2.0](LICENSE)
