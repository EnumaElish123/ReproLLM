# fixture: openai_judge_eval

OpenAI LLM-as-a-judge evaluation. Level 0 expectations: pyproject dependency
manifest without a lockfile; `openai` not pinned; `.env.example` is exempt from
the secret-file rule. The judge call sets no temperature (triggers
`judge.params_declared` at Level 1 in M3 gaps manifests).

All tokens in this fixture tree are fake and exist only for tests.
