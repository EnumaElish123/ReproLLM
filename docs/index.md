# ReproLLM documentation

> Make LLM experiments reproducible.

ReproLLM is a CLI-first, local-first reproducibility toolkit for LLM research experiments.
It records the LLM-specific state that other tools ignore — model revisions, tokenizer and
chat-template hashes, prompt hashes, generation parameters, LLM-as-a-Judge configuration,
and the pinnability of closed-source API models — and tells you why two runs differ.

**Status: alpha (0.1.1).** Audit Level 0/1, manifest scaffolding, and the seven built-in
profiles are usable. Lock, run capture, diff, and export arrive in later milestones.

## Documentation map

- [Roadmap and architecture](plan/00_architecture_and_decisions.md) — product definition,
  boundaries, and the frozen decision register (D-01 … D-42)
- [Beta specification](plan/01_specification.md) — CLI contract, schemas, rule catalog,
  redaction policy, diff semantics
- [Manifest guide](manifest.md) — map model/data/prompt roles, execution settings, and
  detected candidates into one concrete experiment
- [Rule catalog](rules.md) and [profile catalog](profiles.md) — Level 1 checks,
  inheritance, severities, and detection signals
- [Adoption metrics](adoption.md) — updated monthly from week 1 (D-37)

## Commands (current)

| Command | Status |
|---|---|
| `reprollm --version` | available |
| `reprollm doctor [--json] [--check-network]` | available |
| `reprollm audit [PATH] [--format text\|json] ...` | available at Level 0/1; Level 2 rules are visible stubs |
| `reprollm schema export [--out DIR]` | available |
| `reprollm init` | available |
| `reprollm profiles list/show` | available |
| `reprollm lock` / `run` / `diff` / `export` / `discover` | planned — see the roadmap |

## Core principle

**LLM discovers. Rules decide. Runtime verifies.** Known reproducibility requirements are
checked by deterministic rules; an optional, opt-in LLM step only proposes candidates that
take effect after you accept them; runtime capture records what actually happened,
independent of what was declared.

## Security

Secret redaction is a security boundary. See [SECURITY.md](../SECURITY.md) for private
disclosure; redaction bypasses are treated as security bugs, not normal bugs.
