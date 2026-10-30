# Bounded GSM8K replay

New to ReproLLM? Start with the [short first-experiment walkthrough](../../docs/tutorials/first-experiment.md), which uses this recipe's standard-library probe without a GPU, model download or API call. Return here for the complete native replay.

This recipe restores the reviewed [val.md §8.3](../../val.md#83-activated-bounded-linux-runtime-inputs-2026-09-26)
inputs: Qwen2.5-0.5B-Instruct, the first 100 GSM8K test documents, five training
examples per prompt, and generation caps **32 → 48**. It checks bounded execution
and capture; neither accuracy nor generated text has a fixed expected value.

Upstream source is fixed at `b954108c9baaaa934b4ad842033b31a97ee30816`.
[expected.json](expected.json) contains independently recovered input hashes,
both historical input commits, and the expected semantic change. A/B YAML files
retain those original bytes. The corrected config excludes the unsupported
`bootstrap_iters` key. `gsm8k_validation` includes upstream `gsm8k` and adds only
the dataset revision. It is never an MMLU task.

## Install and prepare a disposable checkout

Use the same native Python environment for ReproLLM and the child. CUDA/vLLM
and model/data caches are separate from ReproLLM's lightweight dependencies.
Use a candidate wheel checked by [the distribution runner](../../scripts/validate_distribution.py).
The [roadmap](../../docs/community/roadmap.md) is the feature availability source;
a source recipe does not prove that a similarly named published version has
its features.

Set `RECIPE` to this directory, `WHEEL` to the candidate wheel, and `CASE` to a
new disposable directory on the approved resource volume. In the provisioned
native environment:

```bash
python -m pip install "$WHEEL"
git clone https://github.com/EleutherAI/lm-evaluation-harness.git "$CASE"
git -C "$CASE" checkout --detach b954108c9baaaa934b4ad842033b31a97ee30816
python -m pip install -e "$CASE[vllm]"
cp "$RECIPE/reprollm.yaml" "$CASE/reprollm.yaml"
cp -R "$RECIPE/validation" "$CASE/validation"
cd "$CASE"
printf '\n.reprollm/runs/\noutputs/\nREPRODUCIBILITY.md\n' >> .git/info/exclude
python -c 'from lm_eval.config.evaluate_config import EvaluatorConfig; c = EvaluatorConfig.from_config("validation/eval.yaml"); assert c.gen_kwargs["max_gen_toks"] == 32; assert c.seed == [42, 42, 42, 42]'
reprollm audit --format json --fail-on never
reprollm lock
git add reprollm.yaml reprollm.lock validation
git commit -m 'validation: prepare reviewed GSM8K cap 32 inputs'
reprollm lock --check
```

Dependency installation and initial model/dataset acquisition may use network
access. Before inference, verify the complete cached model snapshot at
`7ae557604adf67be50417f59c2c2f167def9a775` and GSM8K revision
`740312add88f781978c0658806c59bc2815b9866` against the independently reviewed
identities in [val.md](../../val.md). A lock establishes resolution intent, not
that a later framework consumed those bytes. Reuse the provisioned native
environment for the recorded resource gate; a newly resolved framework
environment is a separately identified run.

## Resource boundary and A/B execution

The formal local gate uses GPU 0 only, sequentially. Before **each** run require
used memory below 2 GiB, at least 70,000 MiB free, utilization at most 10%, and
50 GiB free on the resource volume. Respect the GPU lease; do not terminate
other processes or use GPU 1. The config fixes vLLM memory fraction 0.12,
`max_model_len: 4096`, `max_num_seqs: 8`, batch size 1 and eager execution.
These are the recovered activated inputs; earlier proposal prose mentioning
`max_num_seqs: 1` is not the executed config.

Set `HF_HOME` to the verified cache. Clear inherited distributed-launch
overrides, disable external trackers, and use CPU math threads 2. Required CUDA
compatibility libraries must stay process-local. Use a short owned `TMPDIR`
and vLLM IPC directory so Unix socket paths fit their platform limit.

```bash
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export WANDB_MODE=disabled HF_HUB_DISABLE_TELEMETRY=1 VLLM_NO_USAGE_STATS=1
export HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
reprollm run --name gsm8k-cap32 --capture-output -- \
  python -m lm_eval run --config validation/eval.yaml
reprollm runs list --json
```

Set `RUN_A` to the recorded ID. Preserve A's complete `outputs/current` outside
the checkout, with original byte hashes, before B can overwrite it. Retain A's
run directory and its snapshots. Then:

```bash
cp "$RECIPE/variants/eval-b.yaml" validation/eval.yaml
cp "$RECIPE/variants/reprollm-b.yaml" reprollm.yaml
python -c 'from lm_eval.config.evaluate_config import EvaluatorConfig; c = EvaluatorConfig.from_config("validation/eval.yaml"); assert c.gen_kwargs["max_gen_toks"] == 48'
reprollm lock
git add reprollm.yaml reprollm.lock validation/eval.yaml
git commit -m 'validation: change only GSM8K generation cap to 48'
reprollm lock --check
reprollm run --name gsm8k-cap48 --capture-output -- \
  python -m lm_eval run --config validation/eval.yaml
reprollm runs list --json
```

Set `RUN_B` to the second ID and preserve B's outputs separately. Require 100
distinct documents and 200 logged sample rows (one row per extraction filter),
identical document/prompt identities across A/B, actual generation request
dictionaries (`gen_args_0.arg_0` / `arg_1`), finite metrics, output hashes and
complete snapshot fidelity. The 48-token case must not truncate prompts;
otherwise an additional experimental input changed.

```bash
reprollm diff "$RUN_A" "$RUN_B" --format json --fail-on HIGH
reprollm diff "$RUN_A" "$RUN_A" --format json
reprollm export --run "$RUN_A"
reprollm export --run "$RUN_B"
```

The pair diff intentionally exits **1**. Assert `generation.max_tokens`
**32 → 48, HIGH**, plus the changed config hash. Save each export before the
next overwrites it. Explain every other change, including the clean input commit
and timing; highest severity alone cannot establish a working binding.
Self-diff must be empty.

## Evidence mapping

| Manifest declaration | Actual framework input | Binding / captured phase | Independent consumption evidence |
|---|---|---|---|
| `models.primary.id` / `.revision` | `model_args.pretrained` / `.revision` | Config bindings, before child | Native effective args and verified cached file hashes; pinned adapter passes revision to vLLM and AutoConfig |
| Tokenizer identity | `model_args.tokenizer_revision` | Config bytes, before child; no separate tokenizer binding | Native args and cached tokenizer hashes |
| Dataset / task / split | `gsm8k_validation` overlay, pinned data revision, upstream `main` / `test` | Declared config/task hashes, before child | Resolved native task, data identity and 100 document hashes |
| Five-shot count | `num_fewshot: 5`, train split | Config/task bytes, before child | Native task config and identical prompt hashes |
| `generation.max_tokens` | `gen_kwargs.max_gen_toks` | Config binding, before child | Saved requests; adapter maps to `SamplingParams(max_tokens=...)` |
| Temperature | `gen_kwargs.temperature: 0.0` | Config binding, before child | Saved requests and native generation config |
| Generation / execution seed | `seed: 42`, `model_args.seed: 42` | Config bytes; formal manifest has no seed binding | Native parser expands random/NumPy/torch/few-shot seeds to `[42,42,42,42]`; backend seed 42 |
| Metric / aggregation | Upstream `exact_match`, `mean`, strict/flexible filters | Task/implementation hashes, before child | Native resolved metric/filter config and real metric output |

The task uses plain few-shot prompts and does not request chat-template
application. A lock's tokenizer/chat-template hash does not prove template use.
Recorder environment metadata does not attest an arbitrary child interpreter.
All run v2 input observations describe pre-child baselines; post-child
`unchanged` alone does not prove consumption.

## Three validation layers

L1 checks exact hashes, manifest/task/metric mappings and native
`EvaluatorConfig.from_config` acceptance. Offline regressions are in
[test_lm_eval_replay.py](../../tests/unit/test_lm_eval_replay.py). Their static
checks do not import a heavyweight framework; native parser acceptance is
recorded separately in the provisioned environment.

L2 uses the **stdlib-only** `probe.py`. It reads this exact restricted YAML
shape and writes `outputs/current/consumed.json` with the input hash and values
actually read. Substitute this child command in the disposable fixture:

```bash
reprollm run -- python "$RECIPE/probe.py" --config validation/eval.yaml
```

The regression also uses `--rewrite-cap 96`: consume 32, write an independent
receipt, then rewrite the input to 96. ReproLLM must retain baseline 32, record
the post-run hash change, and export 32. The receipt supplies consumption
evidence; ReproLLM itself continues to label consumption unverified.

L3 is actual bounded native execution. Read the current session report for its
status; L1/L2 never substitute for L3. Missing resources, cache identity or
failed capture/output checks leave L3 **BLOCKED/FAIL** with the exact command
retained. Passing this recipe does not close other projects' resource gates
or authorize release. The [S3-B handoff](../../docs/dogfooding/2026-10-14-reliability-s3b/runtime-evidence-handoff.md)
defines the recorder/child distinction.

`upstream/gsm8k.yaml` is an unchanged test/reference copy from the fixed
[MIT-licensed upstream repository](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/LICENSE.md).
Native execution reads the original checkout's task file.
