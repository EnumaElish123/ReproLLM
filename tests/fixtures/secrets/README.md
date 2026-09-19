# secrets corpus

Executable redaction test corpus (spec §16.5), completed in M5-T01:

- `positive.txt` — ≥ 3 samples per secret kind; every line MUST be redacted
- `negative.txt` — benign look-alikes (`MAX_TOKENS=2048`, commit shas, model ids,
  short `sk-` prefixes); no line may be altered
- `env_cases.yaml` — env var name → secret/not-secret classification

All tokens in this directory are fake and exist only for tests.

Each positive row is one complete sample, including single-line PEM blocks.
The streaming tests additionally expand RSA, EC and OPENSSH blocks across lines
and cover interrupted/unterminated blocks without buffering their bodies.
JWT padding cases follow the maintainer-approved correction in spec issue #3.
The original M2 scaffold's oversized AWS example and two nonmatching generic
key names were corrected to the exact normative patterns before activating
the behavioral tests; the negative corpus remains unchanged except additions.
