# ReproLLM documentation

> Make LLM experiments reproducible.

ReproLLM is a CLI-first, local-first reproducibility toolkit for LLM research experiments.
It records the LLM-specific state that other tools ignore — model revisions, tokenizer and
chat-template hashes, prompt hashes, generation parameters, LLM-as-a-Judge configuration,
and the pinnability of closed-source API models — and tells you why two runs differ.

**Status: pre-alpha (0.0.x).** Audit Level 0 works (`reprollm audit`); the manifest, lock,
run capture, diff, and export commands arrive over the coming weeks.

## Documentation map

- [Roadmap and architecture](plan/00_architecture_and_decisions.md) — product definition,
  boundaries, and the frozen decision register (D-01 … D-42)
- [Beta specification](plan/01_specification.md) — CLI contract, schemas, rule catalog,
  redaction policy, diff semantics
- [Adoption metrics](adoption.md) — updated monthly from week 1 (D-37)

## Commands (current)

| Command | Status |
|---|---|
| `reprollm --version` | available |
| `reprollm doctor [--json] [--check-network]` | available |
| `reprollm audit [PATH] [--format text\|json] ...` | Level 0 (two `code.*` rules); Level 1/2 grow over M2–M6 |
| `reprollm schema export [--out DIR]` | available |
| `reprollm init` / `lock` / `run` / `diff` / `export` / `discover` | planned — see the roadmap |

## Core principle

**LLM discovers. Rules decide. Runtime verifies.** Known reproducibility requirements are
checked by deterministic rules; an optional, opt-in LLM step only proposes candidates that
take effect after you accept them; runtime capture records what actually happened,
independent of what was declared.

## Security

Secret redaction is a security boundary. See [SECURITY.md](../SECURITY.md) for private
disclosure; redaction bypasses are treated as security bugs, not normal bugs.
