# ReproLLM documentation

ReproLLM is a CLI-first, local-first reproducibility toolkit for LLM research.
Audit a repository, declare its experiment, lock inputs, capture a run, compare
recorded state and export the evidence with your paper artifact.

**Start here:** use the [Agent Skill tutorial](tutorials/agent-skill.md) for
natural-language requests, or the [guided CLI exercise](tutorials/first-experiment.md)
to save a command and run it again. Both use a disposable standard-library probe
without a GPU, model download or API account. The [executable quick start](quickstart.md)
shows the longer evidence workflow. For a first audit, run `reprollm audit .`.

## Choose a guide

| Goal | Guide |
|---|---|
| Let an Agent install and use the tool | [Agent Skill](tutorials/agent-skill.md) · [Current support and remaining work](skill-status.md) |
| Save an experiment command, preview and run it | [First experiment](tutorials/first-experiment.md) |
| Understand the problem and evidence model | [Why ReproLLM](why.md) · [Concepts](concepts.md) |
| Describe one experiment | [Manifest](manifest.md) · [Profiles](profiles.md) |
| Resolve revisions and file hashes | [Lockfile](lockfile.md) |
| Record commands, settings and snapshots | [Runtime capture](run.md) |
| Explain changes between runs | [Semantic diff](diff.md) |
| Create a paper artifact | [Export](export.md) · [Checklist coverage](checklists.md) |
| Add project-specific checks | [Project rules](project-rules.md) · [Experimental discovery](discover.md) |
| Look up options or findings | [CLI reference](cli.md) · [Rule catalog](rules.md) · [FAQ](faq.md) |

## Frameworks and examples

- [lm-eval](integrations/lm-eval.md), [lighteval](integrations/lighteval.md),
  and [inspect-ai](integrations/inspect-ai.md): configuration, detection and capture.
- [Completed examples](../examples/README.md): HF/vLLM evaluation, API-based
  judging and privacy/custom parameters. Copy them before modifying artifacts;
  their real model scripts need separate dependencies and resources.
- [Model/dataset card snippets](integrations/card-snippets.md).
- [GitHub Action](https://github.com/EnumaElish123/reprollm-action): audit in CI.

## Current availability

The full audit → init → lock → run → diff → export workflow is available,
together with project rules, profiles, diagnostics and experimental discovery.
The latest published package at this update is **0.6.1**. These documents track
`main`; consult [Unreleased changes](../CHANGELOG.md#unreleased) before assuming a
new option or fix is present in PyPI. The Action's published tag is maintained
separately from this repository's Action source.

Source also contains the implemented Skill v2 and saved-command/guided setup
workflow. The verified Skill delivery has five green CI jobs and real Codex Linux
acceptance. Three online gates remain unapproved, Claude Code is deferred and
external feedback is unobserved; [the status page](skill-status.md) distinguishes
these from unfinished code. Installing the PyPI package does not install the Skill.

| Audit level | Evidence used |
|---|---|
| 0 | Repository code and dependency declarations; no manifest needed |
| 1 | A manifest describing the experiment |
| 2 | A manifest plus lock and/or run evidence for consistency checks |

Levels describe evidence depth, not a passing result. Audit is deterministic
and makes no model calls. Discovery is opt-in and proposes candidates that only
become rules after acceptance. Provider resolution and explicit network checks
have separate network requirements; see the linked command guides.

## Project and validation

- [Current development plans](plan/README.md) and
  [coding-agent prompts](plan/reliability-2026-10-03/AGENT_PROMPTS.md).
- [Architecture and decisions](plan/00_architecture_and_decisions.md) and
  [normative specification](plan/01_specification.md).
- [Five-project validation baseline](../val.md),
  [current Skill acceptance](dogfooding/2026-10-31-skill-final/README.md) and
  [resource validation history](dogfooding/pending-resource-validation.md).
- [Current roadmap](community/roadmap.md), [backlog](plan/backlog.md),
  [UX delivery status](plan/ux-2026-10-02-proposals/README.md)
  and [adoption records](adoption.md).
- [Contributing](../CONTRIBUTING.md), [citation](../CITATION.cff) and
  [security reporting](../SECURITY.md).

**LLM discovers. Rules decide. Runtime verifies.**
