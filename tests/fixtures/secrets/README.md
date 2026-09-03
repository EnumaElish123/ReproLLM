# secrets corpus

Redaction test corpus (spec §16.5), populated in M5-T01:

- `positive.txt` — ≥ 3 samples per secret kind; every line MUST be redacted
- `negative.txt` — benign look-alikes (`MAX_TOKENS=2048`, commit shas, model ids,
  short `sk-` prefixes); no line may be altered
- `env_cases.yaml` — env var name → secret/not-secret classification

All tokens in this directory are fake and exist only for tests.
