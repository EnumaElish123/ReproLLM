# lighteval

ReproLLM detects lighteval usage (imports, CLI) and extracts task names from
config YAMLs.

On main (unreleased), list candidates with `reprollm init --list-tasks`, then
select exact names with repeated `--task NAME` options during initialization.
An ordinary init leaves the metrics list empty; confirm metric implementations
for the selected experiment.

## Manifest example

```yaml
project:
  name: lighteval-demo
experiment:
  profiles: [inference, evaluation]
models:
  primary:
    provider: huggingface
    id: meta-llama/Llama-3.1-8B-Instruct
generation:
  temperature: 0.0
  max_tokens: 1024
  seed: 0
inference:
  backend: transformers
execution:
  command: lighteval model=hf --tasks mmlu
```

## Recording a run

```bash
reprollm lock
reprollm run -- lighteval model=hf model_args=pretrained=meta-llama/Llama-3.1-8B-Instruct \
  --tasks mmlu --seed 0
```
