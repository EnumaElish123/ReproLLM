# Real-world validation gates design

## Goal

Expand ReproLLM's standing dogfooding policy from one repository to six pinned
open-source repositories. Every development session must exercise all six with
safe, offline-capable validation. Resource-consuming validation starts only
when the corresponding ReproLLM feature exists and is then required at milestone
completion and before release.

## Validation portfolio

Keep `EleutherAI/lm-evaluation-harness` and add the five projects selected in
`docs/research/reprollm_validation_cases.md`:

- `lm-sys/FastChat`, scoped to MT-Bench and `fastchat/llm_judge`;
- `hiyouga/LlamaFactory`;
- `centerforaisafety/HarmBench`;
- `jyhong836/llm-dp-finetune`.

Each repository is cloned into a sibling `../dogfooding/<name>` directory,
checked out at the commit recorded in `AGENTS.md`, and never committed to
ReproLLM. The six repositories form one complementary portfolio rather than six
interchangeable targets.

## Gate model

### Gate A: every development session

After the local quality gate is green, run every command changed in the session
that can execute without GPU, paid API calls, or mutation of the target against
all six repositories. At minimum, run `audit` against every repository. Starting
in M4, also run offline `lock` checks wherever a maintained dogfooding manifest
exists. Run mutating commands only in a disposable clone or worktree.

A session cannot be reported complete until all six repositories have a result.
Record command, exit status, finding/profile summary, runtime, and delta from the
last baseline. A target crash or unexplained regression blocks completion; an
unavailable checkout must be reported explicitly rather than silently skipped.

### Gate B: milestone resource validation

Resource-consuming scenarios become mandatory only when their owning feature is
implemented:

- M4: real Hugging Face resolution and authenticated provider verification for
  `lock --verify-api` when project credentials and budget are provisioned;
- M5: minimal real executions through `reprollm run`: a small lm-eval inference,
  one MT-Bench judge item, a one- or two-step LlamaFactory fine-tune, one minimal
  HarmBench behavior pipeline, and a one- or two-step privacy fine-tune;
- M6: paired runs that change exactly one high-value field, followed by semantic
  `diff` assertions;
- M7: `export`, opt-in `discover`, and one end-to-end API-backed judge/discovery
  path;
- M8 and every release: rerun every applicable Gate A and Gate B scenario.

Gate B runs at the end of the owning milestone and before release, not after
every ordinary development session. Missing GPU, credentials, provider access,
or an approved spend blocks the resource gate and must be recorded as such; an
agent never substitutes a fake success or spends money without provisioned
credentials and budget.

## Repository roles

- lm-evaluation-harness: evaluation/inference, large-tree scanning, HF/vLLM/API
  backends, prompt and chat-template identity.
- FastChat MT-Bench: evaluated-model/judge-model identity, judge prompt,
  closed-model pinnability, and staged execution.
- LlamaFactory: LoRA/QLoRA, quantization, templates, dataset identity, and dense
  training configuration.
- HarmBench: attack/target/classifier stages, safety definitions, local/API
  backends, Ray, and SLURM capture.
- llm-dp-finetune: privacy budget, DP/scrubbing modes, DeepSpeed, and discovered
  project-specific parameters.

## AGENTS.md change

Replace the current single-target standing dogfooding section with one concise
source of truth containing:

1. the six repository names, locations, pinned commits, and validation roles;
2. Gate A's per-session commands and completion criteria;
3. Gate B's M4–M8 activation schedule and minimal real scenarios;
4. safety and cost constraints for target mutation, credentials, GPU, and APIs;
5. a session-report schema and baseline-update rule;
6. a pointer to `docs/research/reprollm_validation_cases.md` for detailed case
   rationale, paper links, and scenario design.

The edit changes process documentation only. It does not add repositories,
fixtures, credentials, model weights, or generated dogfooding artifacts to the
ReproLLM worktree.

## Acceptance criteria

- `AGENTS.md` names all six pinned repositories and gives each an explicit local
  path and purpose.
- Every development session has a checkable six-target static gate.
- M4–M8 each state exactly when network, GPU, training, inference, paid API,
  `diff`, `export`, and `discover` validation begins.
- The policy distinguishes unavailable resources from passing validation and
  forbids silent skips.
- The session report contains enough information to compare against the prior
  baseline.
- Markdown links resolve locally and `git diff --check` passes.
