# inspect-ai

ReproLLM detects inspect-ai usage (imports, `inspect eval` CLI) and extracts
task names from `@task` decorated functions.

## Manifest example

```yaml
project:
  name: inspect-demo
experiment:
  profiles: [inference, evaluation, safety]
models:
  primary:
    provider: openai
    id: gpt-4o-2024-08-06
generation:
  temperature: 0.0
  max_tokens: 4096
  seed: 0
evaluation:
  metrics:
    - {name: accuracy, implementation: solver.py}
bindings:
  generation.max_tokens:
    cli: "--max-tokens"
```

## Recording a run

```bash
reprollm lock
reprollm run -- inspect eval solver.py --model openai/gpt-4o-2024-08-06
```

The `@task` decorated function names in your solver files are extracted as
task hints for `reprollm init` pre-filling.
