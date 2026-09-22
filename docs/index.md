# ReproLLM documentation

> Make LLM experiments reproducible.

ReproLLM is a CLI-first, local-first reproducibility toolkit for LLM research experiments.
It records the LLM-specific state that other tools ignore — model revisions, tokenizer and
chat-template hashes, prompt hashes, generation parameters, LLM-as-a-Judge configuration,
and the pinnability of closed-source API models — and tells you why two runs differ.

**Status: alpha.** PyPI 0.1.1 provides Audit Level 0/1, manifest scaffolding, and the
seven built-in profiles. The development branch adds lock and Level 2 verification
for 0.2.0, plus runtime capture and consistency checks for 0.3.0. Releases await
their validation gates. Semantic diff is available in development for 0.4.0;
export and discovery arrive in a later milestone.

## Documentation map

- [Roadmap and architecture](plan/00_architecture_and_decisions.md) — product definition,
  boundaries, and the frozen decision register (D-01 … D-42)
- [Beta specification](plan/01_specification.md) — CLI contract, schemas, rule catalog,
  redaction policy, diff semantics
- [Manifest guide](manifest.md) — map model/data/prompt roles, execution settings, and
  detected candidates into one concrete experiment
- [Lockfile guide](lockfile.md) — resolve identities, interpret provenance, and check
  offline state, credentials, and file freshness
- [Runtime guide](run.md) — capture runs, declare bindings, understand redaction,
  inspect conflicts and share selected artifacts
- [Diff guide](diff.md) — compare recorded states, interpret severity and source
  conflicts, customize policy and select CI thresholds
- [Rule catalog](rules.md) and [profile catalog](profiles.md) — Level 1 checks,
  inheritance, severities, and detection signals
- [Adoption metrics](adoption.md) — updated monthly from week 1 (D-37)

## Commands (current)

| Command | Status |
|---|---|
| `reprollm --version` | available |
| `reprollm doctor [--json] [--check-network]` | available |
| `reprollm audit [PATH] [--format text\|json] ...` | available at Level 0/1/2 on main |
| `reprollm schema export [--out DIR]` | available |
| `reprollm init` | available |
| `reprollm profiles list/show` | available |
| `reprollm lock` | available on main; planned for 0.2.0 |
| `reprollm run` / `runs list` / `runs show` | available in development; planned for 0.3.0 |
| `reprollm diff` | available in development; planned for 0.4.0 |
| `reprollm export` / `discover` | planned — see the roadmap |

## Core principle

**LLM discovers. Rules decide. Runtime verifies.** Known reproducibility requirements are
checked by deterministic rules; an optional, opt-in LLM step only proposes candidates that
take effect after you accept them; runtime capture records what actually happened,
independent of what was declared.

## Security

Secret redaction is a security boundary. See [SECURITY.md](../SECURITY.md) for private
disclosure; redaction bypasses are treated as security bugs, not normal bugs.
