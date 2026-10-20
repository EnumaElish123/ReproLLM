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

## Static analysis scope

ReproLLM analyzes research files after excluding known environment and generated
directories: `.venv`, `venv`, `node_modules`, VCS metadata, Python caches,
`.tox`, `dist`, `build`, `.eggs`, and `*.egg-info`. Nested directories containing
`pyvenv.cfg` are also excluded, even when they have an unusual name. Internal
links into these directories do not restore their contents to the analysis.
The directory selected as the audit root remains in scope; ordinary nested
research projects, including `vendor` and `third_party`, remain eligible.

These exclusions apply to code, dependency declarations, framework tasks,
profile signals, and discovery input before their budgets are counted. Static
Python analysis reads at most 500 eligible files, with a 512 KiB text limit per
file. Discovery retains its separate 64 KiB file limit, 2,000 tree-entry limit,
and configured character budget. Files larger than 2 MiB and `.reprollm/runs/`
are outside repository analysis.

Git state and security checks keep their existing file facts. A tracked
`.env.local` inside an excluded environment can still fail the secret-file
check, and adding environment files can still change Git's dirty or untracked
state. Excluding those files from experiment detection does not hide these
facts.

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

## Dependency evidence in a repository

The L0 `env.llm_critical_deps_pinned` check aggregates supported declarations
and scanned imports across the repository. Any exact declaration of a package,
including one in a nested project, remains sufficient for that package. Two
different exact versions do not create a new conflict finding. This does not
select an experiment environment or verify that its dependencies install together.

Starting with the accepted R06-B policy in unreleased 0.7.0, a format lock can
provide package credit only through an actual associated declaration or import.
A `uv.lock` needs a valid same-directory `[project]` pyproject;
`poetry.lock` accepts `[project]` or `[tool.poetry]`; `Pipfile.lock` needs a
same-directory packages or dev-packages table; `conda-lock.yml` needs one unambiguous
same-directory environment dependencies list. Declarations must come from that
paired manifest. Imports use the nearest valid runtime project ancestor;
unreadable or malformed candidate manifests block inferred credit across that
boundary. A deeper independent project may still use its own pair.

For example, a root `torch>=2` declaration is no longer covered solely because
`tools/uv.lock` happens to contain torch. If the tools project itself declares
or imports torch and has a qualified pair, its evidence can still satisfy the
repository-wide check. Workspace members do not inherit a parent lock under
this bounded policy. Users relying on that inference may see a new WARNING.

Lock inventory and `env.lockfile_present` retain their presence semantics.
Exact requirements use their actual include closure. A presence PASS and a
critical-package WARNING can therefore coexist. Format-lock versions,
freshness, platform compatibility and installation are not newly verified.
See [specification §12.2](plan/01_specification.md#122-env-l0-m2) for the complete
pairing, uncertainty and safe-path contract. Rule IDs, severity, thresholds and
persisted schemas are unchanged.

## Why no score?

A number would hide *which* identity is ambiguous. ReproLLM tells you exactly
what is missing and how to fix it; deciding whether it matters is yours.
