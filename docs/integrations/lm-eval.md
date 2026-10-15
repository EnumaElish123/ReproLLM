# lm-evaluation-harness

ReproLLM detects lm-eval imports, command invocations and task YAMLs. On main
(unreleased), `reprollm init --list-tasks` lists the complete inventory;
`reprollm init --profiles evaluation --task gsm8k` selects one task. Unselected
candidates are not declared as experiment metrics. Confirm the actual metric
and aggregation from the pinned task YAML.

Use the [bounded GSM8K replay](../../examples/lm_eval_replay/README.md) for a
complete install → A/B run → diff → export example. It restores the reviewed
100-document, five-shot Qwen2.5-0.5B-Instruct case, changing only cap 32 → 48.
Framework, model, tokenizer and dataset revisions are fixed. Its
`gsm8k_validation` task includes upstream GSM8K and adds the dataset revision.

The native command reads an actual framework config:

```bash
reprollm run --capture-output -- \
  python -m lm_eval run --config validation/eval.yaml
```

That config contains `gen_kwargs.max_gen_toks`, so the manifest binds the same
field rather than declaring an unpassed standalone flag:

```yaml
generation:
  max_tokens: 32
bindings:
  generation.max_tokens:
    config: validation/eval.yaml:gen_kwargs.max_gen_toks
```

An ordinary CLI binding does not parse a compound
`--gen_kwargs max_gen_toks=32,temperature=0` value. Native YAML needs no new
adapter. The pinned vLLM integration maps `max_gen_toks` to
`SamplingParams(max_tokens=...)`; saved native request arguments separately
establish which values the workload used.

The recipe's [input hashes and independent expectations](../../examples/lm_eval_replay/expected.json)
align model revision, GSM8K `main` / `test`, five-shot inputs, seeds, cap,
`exact_match` and `mean`. A/B must specifically report `generation.max_tokens`
**32 → 48 at HIGH**. A HIGH config hash alone is insufficient. Accuracy and
text are observations rather than fixed gold.

Keep evidence claims separate: a manifest declares intent; a lock resolves
identities; run v2 captures pre-child inputs and post-child changes. None
alone proves consumption. Native parser/model arguments, verified cached
bytes, task/document identities and saved requests support the bounded
consumption claim. This plain few-shot case does not apply a chat template.
Environment capture describes the recorder; use the same installed native
environment for the launcher and child and record independent metadata.

The recipe distinguishes L1 static/native-parser checks, L2 stdlib consumption
and rewrite probes, and L3 actual framework execution. Blocked L3 stays blocked
even when L1/L2 pass. Consult the current session report for results and the
[roadmap](../community/roadmap.md) for installation/feature availability.
