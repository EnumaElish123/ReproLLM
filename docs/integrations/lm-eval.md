# lm-evaluation-harness

ReproLLM detects lm-eval usage (imports, CLI invocations, task YAMLs) and
extracts task names + metrics for `init` pre-filling.

## Manifest example

```yaml
project:
  name: my-eval
experiment:
  profiles: [inference, evaluation]
models:
  primary:
    provider: huggingface
    id: Qwen/Qwen3-32B
datasets:
  eval:
    provider: huggingface
    id: cais/mmlu
    subset: abstract_algebra
    split: test
generation:
  temperature: 0.0
  top_p: 1.0
  max_tokens: 2048
  seed: 42
inference:
  backend: vllm
execution:
  command: lm_eval --model vllm --model_args pretrained=Qwen/Qwen3-32B --tasks gsm8k
bindings:
  generation.max_tokens:
    cli: "--max_gen_toks"
```

## Recording a run

```bash
reprollm lock                    # resolve model revision, tokenizer, chat template
reprollm run -- lm_eval --model vllm \
  --model_args pretrained=Qwen/Qwen3-32B,dtype=bfloat16 \
  --tasks gsm8k --seed 42
reprollm export --template neurips
```

The run record captures the exact model revision, task config, generation
parameters, and consumed files. `diff` between two runs (e.g. different
`--max_gen_toks`) surfaces the changed field with severity.
