# Core concepts

## The three documents

ReproLLM's mental model is three documents, each answering one question:

| Document | File | Question | Written by |
|---|---|---|---|
| **Manifest** | `reprollm.yaml` | What do you *intend* to run? | You (or `reprollm init` as a scaffold) |
| **Lock** | `reprollm.lock` | What did resolution *produce* at a point in time? | `reprollm lock` |
| **Run record** | `.reprollm/runs/<id>/run.json` | What *actually executed*? | `reprollm run -- <command>` |

**LLM discovers. Rules decide. Runtime verifies.** An optional LLM step
(`discover`, experimental) only *proposes* candidates; deterministic rules
always decide; runtime capture records what really happened, independent of
what was declared.

## Audit levels

| Level | Exists | Checks |
|---|---|---|
| **0** | nothing | Code state, dependency declarations, secret files, experiment-type detection |
| **1** | `reprollm.yaml` | Level 0 + everything your declared profiles require |
| **2** | `reprollm.lock` and/or run records | Level 1 + cross-document consistency and pinning |

The level is automatic; `--level` can only lower it.

## Severity semantics

- **CRITICAL** — the experiment's *identity* is ambiguous (which model, which
  data, which generation parameters?)
- **WARNING** — identity is determinable but reproduction is materially harder
- **INFO** — advisory or suppressed
- **PASS** — checked and satisfied

Diff (drift) severities are a separate vocabulary: HIGH / MEDIUM_HIGH / MEDIUM
/ LOW / NONE, from a per-field table (`drift_severity.yaml`) that profiles can
override.

## Precedence

Effective value precedence is **run (cli > config > env) > lock > manifest >
default**. A disagreement between sources is never silently resolved — it
becomes a `consistency.*` finding.

## Pinnability

Closed-source API models cannot be pinned to an immutable artifact. ReproLLM
never fakes it: dated snapshot ids (`gpt-4o-2024-08-06`) are
`snapshot_alias`; bare aliases are `unpinnable`; HF commit SHAs are `exact`.

## Why no score?

A number would hide *which* identity is ambiguous. ReproLLM tells you exactly
what is missing and how to fix it; deciding whether it matters is yours.
