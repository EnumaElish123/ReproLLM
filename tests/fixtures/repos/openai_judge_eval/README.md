# fixture: openai_judge_eval

OpenAI LLM-as-a-judge evaluation. Level 0 expectations: pyproject dependency
manifest without a lockfile; `openai` not pinned; `.env.example` is exempt from
the secret-file rule. The judge call sets no temperature (triggers
`judge.params_declared` at Level 1 in M3 gaps manifests).

All tokens in this fixture tree are fake and exist only for tests.

## M4 Level 2

The complete fixture resolves without provider HTTP calls. The mutable primary
`gpt-4o-mini` yields a WARNING; the dated judge `gpt-4o-2024-08-06` yields INFO.
Local dataset and judge prompt hashes pass. The fixed lock is committed before
audit. Summary (C/W/I/P/S): `0/1/4/37/19`.
