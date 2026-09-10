# M2 corrective sprint and validation documentation design

## Goal

Turn the 2026-09-10 whole-project review and five-repository validation into an
executable corrective sprint, a single authoritative gold answer, and a concise
agent completion gate.

## Documents and ownership

### `docs/plan/M2-fix-0910.md`

This is the corrective sprint plan. It records every confirmed review finding,
including functional defects, output-contract violations, test-corpus gaps,
architectural debt, and documentation inconsistencies. Each item contains:

- priority and evidence;
- expected behavior and root cause;
- tests to add before implementation;
- bounded implementation steps;
- acceptance criteria and regression commands;
- one-task/one-commit boundary.

Functional P1 defects are ordered before P2 quality and governance work. The
repository-identity conflict requires a maintainer decision because D-01 is
frozen. Configuration suppression and severity overrides are explicitly excluded
because M3 already owns them. M3–M8 features remain outside the corrective
sprint.

### `val.md`

This is the single source of truth for external-repository gold answers. It is
derived from fixed repository commits without using ReproLLM output and contains:

- checkout preconditions and evidence rules;
- exact Git, dependency, Python, secret-file, and scan-limit expectations;
- exact unpinned LLM-critical dependency sets;
- expected profile confidences and detection hints;
- bounded `init` expectations for repositories with multiple model candidates;
- per-session static validation commands;
- milestone activation gates for network resolution, real inference/training,
  paid APIs, semantic diff, export, and discover;
- delta reporting and failure criteria.

The portfolio contains five repositories total: lm-evaluation-harness, FastChat,
LlamaFactory, HarmBench, and llm-dp-finetune. lm-evaluation-harness is part of
the five, not an additional sixth target. ReproLLM observations and known current
failures do not appear in the gold sections, preventing circular validation.

### `AGENTS.md`

Section 10 becomes a short mandatory pointer to `[val.md](val.md)`. After the
normal quality gate, every development session must run Gate A for all five fixed
repositories and compare every result with the gold answer. Milestone completion
and release sessions additionally run each resource gate activated in `val.md`.

A checkout, GPU, credential, provider, or budget problem is reported as blocked,
not passed. A crash, unexplained gold delta, silent skip, or missing five-target
result prevents session completion. Mutating commands run only in disposable
clones or worktrees.

## Information hierarchy

`AGENTS.md` owns the mandatory step and completion criterion. `val.md` owns the
repository data, commands, baselines, and milestone branches. The corrective
sprint owns implementation order and acceptance criteria. No gold table or
repository metadata is duplicated in `AGENTS.md`.

## Verification

- Check all local Markdown links and relative paths.
- Confirm every reviewed issue is represented once in the corrective sprint.
- Confirm all five fixed SHAs and gold sets match primary-source evidence.
- Confirm `AGENTS.md` names `val.md` with a relative Markdown link and defines a
  checkable completion condition.
- Confirm no sixth repository is implied.
- Run `git diff --check` and Markdown whitespace checks on new untracked files.
- Do not modify source code, schemas, fixtures, target repositories, or the
  existing untracked `plan/` directory.
