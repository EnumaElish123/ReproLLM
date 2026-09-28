# M5–M6 bounded runtime gold: independent source review

Reviewed 2026-09-26 against the five commits in [`val.md`](../../val.md), the
normative specification, and the author's pinned fastDP fork. This is a
**pre-execution gold proposal**, not a result report. No GPU execution or package
installation was performed by this review. Materialize the driver/config/fixture
files, independently hash them, and record the final commands in the activated
validation scenario before running it. Their not-yet-created bytes cannot have a
preclaimed hash.

The gold is about real execution, input identity, capture and semantic drift. It
does not predict benchmark accuracy, generated text, classifier labels, training
quality, or a production privacy guarantee. Preparation requirements are in
[the resource note](m4-m6-resource-compatibility.md).

Final pre-execution clarifications from the validation controller review:

- Native lm-eval logs one row per document **per extraction filter**: the 100
  unique GSM8K documents produce 200 JSONL rows for `strict-match` and
  `flexible-extract`. This follows the pinned evaluator's filter loop; it is not
  200 model questions. Compare identical document/prompt hashes between A/B and
  check all prompts fit even with the larger 48-token cap.
- The LlamaFactory entry observer now calls the original
  `CustomSeq2SeqTrainer.compute_loss` unchanged, asserts nonmasked labels and a
  finite raw loss in each of the two actual batches, and returns the original
  result. This avoids mistaking Trainer's NaN-filtered logs for proof of valid
  training. Final driver SHA-256:
  `c9520bc72fc0fd50ffd547e07da164f678f3ae3d8372053465f10a7be640c5b2`.
  The initial driver hash later in this note is retained as review history.
- Capture hash checks accept the specified `sha256:` prefix and independently
  hash original bytes, not redacted snapshots. Failed attempts remain in separate
  evidence directories and never become the published successful pair.

## 1. Contract and expected drift

The normative [specification §3, §5, §15 and §18](../plan/01_specification.md)
defines valid paths, capture, bindings and severity. [M6-T02](../plan/M6_diff.md)
explicitly defines `*` as matching one path segment. No existing profile override
changes the following conclusions:

| Scenario | Actual experimental change | Captured semantic path | Built-in severity |
|---|---|---|---|
| lm-eval | generation cap 32 → 48 tokens | `generation.max_tokens` | HIGH |
| FastChat answers, supplemental only | optional cap 32 → 48 tokens per turn | `generation.max_tokens` | HIGH |
| LlamaFactory | learning rate 0.0001 → 0.0002 | `training.learning_rate` | HIGH |
| HarmBench | target generation cap 16 → 24 tokens | `generation.max_tokens` | HIGH |
| supplementary DP | target epsilon 8 → 4, recalibrated noise | `privacy.mechanism.params.target_epsilon` | **MEDIUM** |

The DP row exposes a policy coverage gap, not permission to change the gold:
`privacy.*` is a two-segment pattern and cannot match the four-segment epsilon
path. The specification says unmatched paths are MEDIUM. `privacy.target_epsilon`
would be an invalid replacement path; changing the manifest shape to obtain HIGH
would misrepresent the experiment. Similarly, `evaluation.judge.*` does not cover
`evaluation.judge.params.temperature`. Record this as a specification/policy
limitation for maintainer review. A separately declared, independently reviewed
exact-path `drift_overrides` rule could produce HIGH, but that would be a different
scenario, not the built-in-policy result proposed here.

Compare the **specific semantic leaf**, not merely `summary.highest`: changing a
bound configuration also changes `files.<relative-config>.sha256` at HIGH, which
could conceal the missing privacy HIGH classification. Expect `command.argv`
MEDIUM if arguments differ; run IDs/times are NONE. Config/manifest hashes and
code commits can also differ as a direct consequence of preparing the pair.
Document each such difference; do not assert that a real pair contains exactly
one changed State leaf. Only one experimental parameter should change.

## 2. Shared runtime assertions

For each pair, pin identical model/data revisions and immutable input files;
reuse identical sampling/order, seeds, precision, batch/sequence limits and
software environment. Recheck GPU occupancy before every stage and use only the
approved card. Do not change global driver settings or terminate another process.

Run ReproLLM and the child in the **same validation Python environment**. Version
capture uses the launcher's installed package metadata, not a probe inside an
arbitrary child interpreter; a launcher from the lightweight development venv
cannot honestly establish the external child's torch/vLLM versions. Independently
compare recorded versions with metadata obtained using that child's interpreter.
See [`core/envinfo.py`](../../src/reprollm/core/envinfo.py) and
[`run/wrapper.py`](../../src/reprollm/run/wrapper.py).

Expected assertions, derived from the contract rather than ReproLLM output:

- The real child exits zero; `run.json` is complete with matching exit status,
  command, selected GPU environment, pinned experiment snapshots and actual
  bound values. A nonzero child is a failed scenario even if recording succeeds.
- Independently recomputed input/output SHA-256 and byte counts match captured
  entries. Only declared, relative output artifacts are expected; a model's
  generated answer is not an a priori hash gold.
- Persisted captures contain no raw absolute paths, hostnames, usernames or
  credential values. Use no real secrets for the currently authorized local
  cases. Inspect all saved files, not only `run.json`.
- Both runs' bindings reach the actual consumed upstream parameter. Merely
  putting a field in `reprollm.yaml` does not show runtime observation.
- Diff the two real run snapshots; assert the exact path, values and severity
  above. Self-diff has no reproducibility-relevant change. Audit contradictions
  should be judged against what was actually declared, not suppressed to force
  PASS.

## 3. A — native lm-evaluation-harness

Keep the existing Qwen2.5-0.5B-Instruct and GSM8K revisions in `val.md` §8.1. The
tracked `gsm8k.yaml` uses GSM8K `main`, test examples, train few-shot examples,
five-shot prompting, deterministic generation and strict/flexible extraction.
Use the first 100 test items. With a 32/48-token cap this is a bounded
reproducibility smoke, not the original full-generation performance benchmark.
[Pinned task](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/tasks/gsm8k/gsm8k.yaml).

Use native YAML configuration and command, from the disposable checkout:

```console
reprollm run --capture-output -- python -m lm_eval run --config validation/eval.yaml
```

Proposed shared configuration: `model: vllm`, `tasks: [gsm8k]`, `limit: 100`,
`num_fewshot: 5`, `batch_size: 1`, `seed: 42`; model arguments include the
pinned local model, `dtype: bfloat16`, `tensor_parallel_size: 1`, `seed: 42`,
`max_model_len: 4096`, `max_num_seqs: 1`, and a preapproved memory cap. Use
`gen_kwargs.temperature: 0.0`, `gen_kwargs.do_sample: false`; change only
`gen_kwargs.max_gen_toks` from 32 to 48. Keep output logging local and external
trackers disabled. Both prompts must fit without truncation; otherwise the cap
change can also change prompt tokens and the pair is not single-parameter clean.

Declare the binding:

```yaml
generation.max_tokens:
  config: validation/eval.yaml:gen_kwargs.max_gen_toks
```

This mapping is independently justified by the native config loader and vLLM
adapter: `max_gen_toks` is converted to `SamplingParams(max_tokens=...)`. A
compound `--gen_kwargs` argument is not an independently parseable ReproLLM
`--max-tokens` binding. Check 100 real evaluated records, the same question and
few-shot identities across the pair, finite metric output and bounded generation;
do not demand a particular accuracy or different answer text.
[Config loader](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/config/evaluate_config.py),
[vLLM adapter](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/models/vllm_causallms.py).

## 4. B — FastChat answer generation is supplemental

The paid MT-Bench judge scenario is explicitly deferred by the user. Local answer
generation cannot pass that gate, prove API-secret capture, or validate judge
responses. If performed, label it supplemental native model-answer coverage.

The first pinned MT-Bench item is question ID 81, category `writing`, with two
turns. Native `gen_model_answer.py` selects category temperature 0.7 and seeds
each choice with its index; one choice uses seed 0. Do not claim temperature zero
unless intentionally creating and identifying a different adapter scenario.
Candidate native arguments are `--question-begin 0 --question-end 1`,
`--num-choices 1`, `--num-gpus-per-model 1 --num-gpus-total 1`, the pinned local
Vicuna model, bounded `--max-gpu-memory` and `--max-new-token 32`. The parameter
spelling is singular `--max-new-token`.
[Native generator](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge/gen_model_answer.py),
[temperature map](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge/common.py).

Expected output: exactly one question record, one choice and two generated turns;
neither turn may be the generator's error placeholder. An optional paired 48-token
answer run binds `generation.max_tokens` to CLI `--max-new-token`, hence HIGH.
No expected prose, rating or judge result is asserted.

## 5. LlamaFactory — native two-step LoRA

Use the pinned Qwen3-4B-Instruct-2507 model with the native training CLI:

```console
reprollm run --capture-output -- llamafactory-cli train validation/train.yaml
```

Derive a disposable config from `examples/train_lora/qwen3_lora_sft.yaml`, keeping
SFT, LoRA rank 8, target `all`, `qwen3_nothink` template and bf16. Restrict the
dataset to `identity`, `max_samples: 16`, `cutoff_len: 64`, batch 1, accumulation
1, `max_steps: 2`, seed/data seed 42, one preprocessing worker and no dataloader
workers. Disable evaluation, external loggers and periodic checkpoint saves;
retain the final adapter artifact. Do not enable QLoRA, DeepSpeed or remote code
unnecessarily. Inspect tokenized labels: at least the two actual training batches
must retain nonmasked target tokens after the 64-token cutoff.

The native loader applies `max_samples` using `select(range(max_samples))`, so
this means the first 16 identity records, not a new random 16-item subset.
Pair only `learning_rate: 0.0001` versus `0.0002`, keeping the scheduler/warmup
choice explicit and identical. Bind `training.learning_rate` to
`validation/train.yaml:learning_rate`. Expected: two completed optimizer updates,
finite loss, nonzero LoRA trainable parameters and a loadable nonempty final
adapter. LoRA weights must actually change; no convergence assertion is made.
[Pinned example](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/examples/train_lora/qwen3_lora_sft.yaml),
[dataset loader](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/src/llamafactory/data/loader.py).

## 6. HarmBench — one low-risk text behavior, original functions

Select `BehaviorID: profane_insult_generation` from the pinned behavior CSV.
It is a standard, non-contextual text behavior with empty Tags/ContextString,
not a request targeting a protected group or a named real person. This confines
the smoke test to generic profanity rather than weapon, cyber, or political
content. Keep generated content out of this document and public reports; record
only identifiers, hashes, lengths and labels. Do not optimize a jailbreak.

Stage 1 calls the original `DirectRequest.generate_test_cases(behaviors,
verbose=False)` on exactly this row; output must have exactly this ID and one
test case, equal to the row's behavior because context is empty. Stage 2 uses
the selected Vicuna model and the upstream Vicuna template to generate exactly
one real completion. Stage 3 uses the pinned HarmBench-Llama-2-13b classifier,
temperature 0, one classification token and the **original** classifier helper.
Target and classifier run sequentially in separate bounded-memory processes.
[DirectRequest](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/baselines/direct_request/direct_request.py),
[model templates](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/baselines/model_utils.py).

The helper's exact signature is
`compute_results_classifier(behavior_dict, data, cls, cls_params)`. Each data item
contains `generation`; the helper constructs its unchanged classifier prompt and
calls `cls.generate(inputs, cls_params, use_tqdm=False)`. Case-insensitive exact
`yes`/`no` becomes 1/0; any other string becomes -1, with a warning that includes
original text. A -1 is an invalid/unresolved classification, not a successful
binary judgment. Do not substitute labels or strip output beyond the original
parser to force success. Capture warnings privately and redact public reports.
[Classifier function](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/eval_utils.py).

Import requirements: `eval_utils` imports spaCy and `datasketch.MinHash`, although
the selected classifier path does not use the hash-check routine. DirectRequest's
base/model utilities import torch, Transformers, vLLM, Ray and fschat. Ray is not
launched by this method (`use_ray=False`). Importing these real dependencies is
different from stubbing them. A thin driver may avoid the original completion
CLI's unrelated API/multimodal imports, but report this as original-function
adapter coverage, not unmodified CLI coverage.

Pair target `max_new_tokens: 16` and `24`, map the consumed driver config to
`generation.max_tokens`, and expect HIGH. Classifier settings remain identical.
Require one testcase, one target completion and one classifier result per run.
The binary label may differ or stay equal; neither specific label is a gold
answer about model safety or attack success.

## 7. Supplementary DP — original single-GPU method

Use public pretrained DistilGPT2 at the revision in the resource note, not gated
Llama-2. The driver calls the pinned original
`LanguageModel._fine_tune_fast_dp(train_dataset, eval_dataset, train_args,
privacy_args, extra_callbacks=None)` explicitly. The normal `fine_tune` dispatcher
instead calls the ZeRO method; launching that normal entry point without ZeRO is
not equivalent. This supplementary case does not complete the original gated
Llama-2/ECHR/ZeRO validation.

Import the upstream `GPT2`, `ModelArgs`, `EnvArgs`, `TrainerArgs` and `PrivacyArgs`.
`LanguageModel` imports `RealDataset`, which imports `Dataset` and `NERArgs`, but
that chain does not import Flair. `NERArgs` merely has Flair-named string defaults;
`Dataset.load_pii` imports `TaggerFactory` lazily. The synthetic wrapper must not
invoke `load_pii` or the ECHR loader. Missing optional `local_configs` produces a
warning and local cache defaults, not a mandatory dependency.
[Model wrapper](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/models/language_model.py),
[dataset base](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/dataset/dataset.py),
[NER arguments](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/arguments/ner_args.py).

Materialize and hash 16 nonprivate, short synthetic English text examples. The
wrapper needs `__len__`, `get_hf_dataset`, `shuffle`, and `select`; those methods
return real HF datasets/wrappers, not canned model responses. Use fixed ordering
and real tokenization with `tokenizer_max_length: 64`, full fine-tuning, float32,
batch 1, accumulation 1, two optimizer updates, no evaluation/logger, and a
bounded final model save. The upstream `load` method assigns EOS as padding.
Explicitly set `train_args.resume_from_checkpoint=None` because the method reads
it although the custom TrainerArgs does not declare it. Set
`limit_eval_dataset` within the actual eval fixture length.

Privacy arguments: `target_epsilon: 8.0` versus `4.0`, explicit identical
`target_delta`, `noise_multiplier: null`, `max_grad_norm_dp: 1.0`. The original
method maps these to the fastDP engine's `target_epsilon`, `target_delta`,
`noise_multiplier` and `max_grad_norm`. Sigma calibration uses
`num_train_epochs`, not Trainer's `max_steps`; either align the calibration
horizon with the two updates or record its conservative longer horizon. Do not
require measured epsilon to equal the requested target. Require a finite
accountant result at the actual engine step count and a larger calibrated sigma
for the smaller epsilon. Record requested and effective privacy settings.
[Privacy arguments](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/arguments/privacy_args.py),
[fastDP engine](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/privacy_engine.py).

Real-DP execution evidence must include:

1. The upstream engine is attached to the actual optimizer; its `step` is
   `dp_step`, `engine.steps == 2`, intended trainable parameter coverage is not
   silently reduced, model parameters change and outputs are finite.
2. Observe the original clipping call, whose exact signature is
   `_per_block_clip_grad(layer, named_params, named_layers, clipping_style,
   clipping_fn, numerical_stability_constant, max_grad_norm_layerwise)`. Under
   automatic/all-layer clipping it aggregates per-sample norms and computes
   `C = max_grad_norm_layerwise / (norm_sample + numerical_stability_constant)`.
   Record finite aggregate statistics without changing the original result.
3. Observe `_create_or_extend_private_grad(param, summed_clipped_grad,
   accumulate_private_grad=True)` and actual `torch.normal` calls with positive
   `std=param.noise`. `autograd_grad_sample` imports this function by name, so an
   observing wrapper must target the called reference, not an unused module
   attribute. Never replace generated noise or the optimizer update with a stub.
4. Save only counters, booleans, configuration, hashes and aggregate accountant
   values. Do not save raw gradients/noise arrays. Fixed-seed synthetic-fixture
   validation is not a claim of secure randomness for private-data deployment.

Sources: [clipping implementation](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/autograd_grad_sample.py),
[noise implementation](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/supported_layers_grad_samplers.py).
Bind the actual config epsilon to `privacy.mechanism.params.target_epsilon`.
The built-in diff expectation remains MEDIUM for the reason in §1; report the
policy gap even if a changed config file makes overall severity HIGH.

## 8. Independently checked source hashes

Computed with `sha256sum` on the pinned clean source files before runtime
validation. Paths below are relative to the named pinned upstream repository.
The fork was independently checked at
`3339cf45fa334cac67eb6a38726a8726630e31c2`.

| Repository / relative path | SHA-256 |
|---|---|
| lm-eval: `lm_eval/tasks/gsm8k/gsm8k.yaml` | `82eb1780b263bc040729032b3e076990c7933f42163c91e359f38820dd1d8833` |
| lm-eval: `lm_eval/models/vllm_causallms.py` | `a8552f4e522175f422ad2229813a8a725c0504ad7b8e758c504e3e09911e5c89` |
| lm-eval: `lm_eval/_cli/run.py` | `59245f533c514cf448f6f5614d8a7cb388d69acdae47e8fc3f8defc82dfa2746` |
| lm-eval: `lm_eval/config/evaluate_config.py` | `ea8bae4e5a9ed355970ea9559181c383ec819b8da89b8f68480d7531b4010918` |
| FastChat: `fastchat/llm_judge/gen_model_answer.py` | `8feb3c19262b8f8567b49c1cd45b0adfd83f199bdcd17e891a05dd608300c7c6` |
| FastChat: `fastchat/llm_judge/data/mt_bench/question.jsonl` | `119565adbab82227089cefdb44c8d7e2cf04dc0a0ec233634c82e7d4e2a944f7` |
| LlamaFactory: `examples/train_lora/qwen3_lora_sft.yaml` | `783c247613e0c46c4b4ea5c6627acd5387d939af91f22a9d6a9efdb4996147ae` |
| LlamaFactory: `data/identity.json` | `fd029da7dd3df283ed034c82375d16d125a7b07cf1cb0316d03fb8743057d5f2` |
| LlamaFactory: `src/llamafactory/data/loader.py` | `f5f59ae8dcb65f95f16052d3c79645adbb02304ba3425682036a41728d0340d0` |
| HarmBench: `baselines/direct_request/direct_request.py` | `277b6edea5b6aa77b962183dba8a4cace150d85448983e3496222f864d70995d` |
| HarmBench: `baselines/baseline.py` | `ca99bebc83ef636f9f3c05748fdcb66b134525e5c2e0c1cb59f9853bcb5c7c5d` |
| HarmBench: `baselines/model_utils.py` | `e0a0bcfd4c186e7da5bdeb97d85be98053be88c8dad2aa3da211ae35d5e78a35` |
| HarmBench: `eval_utils.py` | `46f1db751866848834d45d5128a18d4cc0a820828e89796ab51bc605d10c7058` |
| HarmBench: `data/behavior_datasets/harmbench_behaviors_text_all.csv` | `8d81accedd38eaaf8b760618622bb888417d1fd0c86eba65c427a16f1cbb4afc` |
| llm-dp: `src/llm_pft/models/language_model.py` | `b3fb5b2302bc98119738808168a7edde4f975acf36aeeb0e3ebb8db761a6c896` |
| llm-dp: `src/llm_pft/models/gpt2.py` | `059e35212c33a72e675caf99fe5c258fcff3ad74ae7f29f357d9230f8a7bde58` |
| llm-dp: `src/llm_pft/arguments/trainer_args.py` | `3b55c96ad11f140424f786c0d4af12f4aa3d372a14aaa119fbebe665018ef2a0` |
| llm-dp: `src/llm_pft/arguments/privacy_args.py` | `39658034cf7df5c5bee934e8010d4cfdfe4288abb2fe1f3ea9875458a97045a7` |
| llm-dp: `src/llm_pft/dataset/dataset.py` | `50cb1fe3830d0510110eb50dd316e87b710d2ff559954e4e8f84b6fa3f2a8bbb` |
| llm-dp: `src/llm_pft/dataset/real_dataset.py` | `57593086db1e4be33a8eb7a81cde18287b932b13b6f7e6e65c58013f620088ff` |
| fastDP: `fastDP/privacy_engine.py` | `b17bcd6cad1b3f9ac2539a1e9cce93984d1818a630352e372b01626821c7cf90` |
| fastDP: `fastDP/autograd_grad_sample.py` | `b30d584bb70761d2228fa66d96398b18fc0dbdb2abcd65ce0e06e7cb33a671df` |
| fastDP: `fastDP/supported_layers_grad_samplers.py` | `d8d9921988e3d58712c78e1a7dd28f58b805945a8c1df489d1af7ec319062110` |
| fastDP: `fastDP/transformers_support.py` | `e791dc9337ed8ab5c9f03f04b362b2a482fe60f04cec36df3eda1e795c86de9e` |

## 9. Materialized-input preflight review

The initial A-side inputs below were subsequently reviewed read-only before
execution. This review did not execute a model or modify a validation checkout.
The lm-eval and LlamaFactory manifests pass the current manifest schema. The
initial DP manifest has the two blocking validation errors listed below; the
reviewed hash identifies that rejected input, not an activated scenario.
Both Python entry drivers parse successfully, and the custom task include exists.
These are prerequisite checks, not runtime PASS results.

### Confirmed consumed inputs

- **lm-eval:** the materialized task is `gsm8k_validation`, not `gsm8k`. Its
  relative include `../../lm_eval/tasks/gsm8k/gsm8k.yaml` resolves from
  `validation/tasks` to the pinned original task file. The loader merges the
  custom `dataset_kwargs.revision` and passes it to `datasets.load_dataset`.
  `gen_kwargs.max_gen_toks: 32` reaches vLLM's real generation cap. The
  materialized `max_num_seqs: 8` differs from the preliminary proposal's 1; it is
  a declared, unchanged pair input, while harness batch size remains 1.
  Result verification must use the `gsm8k_validation` task key.
- **LlamaFactory:** `train_entry.py` sets the CUDA allocator fraction to 0.35,
  then calls the original `llamafactory.cli.main` with the native train/YAML
  arguments. `learning_rate: 0.0001`, LoRA rank/alpha 8/16, bf16,
  `max_samples: 16`, `cutoff_len: 64`, batch/accumulation 1/1 and max steps 2
  match the manifest. The constant scheduler has no warmup.
- **DP:** model ID/revision select the matching local HF snapshot directory;
  the original GPT2 wrapper loads that snapshot. All three observers call the
  original attach/clipping/Gaussian functions, return their outputs unchanged,
  and restore the original references in `finally`. The bound epsilon is passed
  through `PrivacyArgs` to the original single-GPU training method. With 16
  samples, logical batch 1 and `num_train_epochs=0.125`, the author's accountant
  computes `ceil(0.125 / (1/16)) = 2` calibration steps, agreeing with actual
  requested `max_steps=2`. Sixteen synthetic texts, `target_delta=0.001` and
  `max_grad_norm_dp=1.0` are explicit; the loss/step/coverage/noise/weight-change
  assertions are not canned model outcomes.

Sources for these checks, in addition to §8: the pinned
[task include loader](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/tasks/_yaml_loader.py),
[dataset loader](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/api/task.py),
[LlamaFactory launcher](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/src/llamafactory/launcher.py),
and [fastDP accountant](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/accounting/accounting_manager.py).

### Conditions to check immediately before launch

The initial DP manifest cannot launch as written:

1. Its inline YAML description contains an unquoted comma. YAML parses the tail
   `tokenizer truncated at 64 tokens` as another mapping key with a null value,
   which the manifest schema rejects. Quote the entire description and rehash.
2. `training.epochs: 0.125` is rejected because the current implementation types
   epochs as an integer, although the normative specification §3 says `number`.
   This is an implementation/specification mismatch, not a reason to pretend
   training used one epoch. A temporary supplemental manifest can omit that
   integer field and explicitly preserve the actual 0.125 horizon in free-form
   training parameters plus the driver evidence; label that workaround. A schema
   correction is a separate reviewed code change under D-41.

Sources: [`Training` implementation](../../src/reprollm/schemas/manifest.py)
and [normative manifest contract](../plan/01_specification.md). Recheck the
corrected DP manifest and record a new hash before activation.

LlamaFactory's native launcher starts another `torchrun` process if multiple GPUs
are visible or distributed launch is forced. The parent's allocator fraction is
not inherited as a Python setting by that new process. Expose only the approved
single card; clear `FORCE_TORCHRUN`, `USE_MCA`, `USE_MEGATRON_BRIDGE` and avoid
`USE_V1` for this specific driver. Otherwise the claimed driver memory ceiling
does not cover the training process. Tokenized nonmasked labels, prompt
nontruncation, successful kernel loading and actual loss/gradient behavior still
require runtime checks; no preflight source review can certify them.

For the B-side variant, change only the chosen experimental field and its
corresponding manifest value, relock and commit the disposable experiment state.
Both trees should be clean at launch. Expected derived differences include the
changed config's `files.<path>.sha256` at HIGH and `code.commit` at MEDIUM, not a
dirty-tree HIGH escalation. Retain the original upstream pin separately from
these validation-only commits. The DP semantic epsilon leaf remains MEDIUM under
the unchanged default policy even when the configuration hash makes the report's
overall highest severity HIGH.

### Materialized A-side SHA-256 snapshot

These hashes identify the exact reviewed initial files. Any later preparation
edit needs a newly recorded hash and focused re-review; they do not predetermine
the B-side hashes or generated outputs.

| Case / relative file | SHA-256 |
|---|---|
| lm-eval: `validation/eval.yaml` | `71e5cf0de1fee6f9e0fca76eb1232b23960fcfa46873597e5875de46502b54e6` |
| lm-eval: `validation/tasks/gsm8k_validation.yaml` | `020ac469e598124888040f2bc0fa5f4d49902271d42015f220cfdd104f44fe8f` |
| lm-eval: `reprollm.yaml` | `ac4bfde5a7538bfa6058746b51c3e00d25cc327b82c6311fa734f2f33da25775` |
| LlamaFactory: `validation/train_entry.py` | `7e3f01fbe220b4206ef33a25b8005417844fa29c5cfd2a33e94e0f267e893052` |
| LlamaFactory: `validation/train.yaml` | `f4334f6b207c0e1112e3e79665a02ee0541df256f3f71b1d8501b8031366ddae` |
| LlamaFactory: `reprollm.yaml` | `d201b66e2992e21d4e20d11181dbe9ba4911b901b8cbfbe66f59c569a7e503f3` |
| llm-dp: `validation/train_entry.py` | `21d644d2596ae71f633196102561a0c5405fe0f220fc9bf3de895c458ef3e92a` |
| llm-dp: `validation/train.yaml` | `ab9b5ab5be9289eccd4c967f2d9486075c60270a67ad315de7fed2a392f22951` |
| llm-dp: `validation/texts.json` | `1f9a355a543bef54a2bf73e9c9a73050e70b8fdc617c83796cd7c92c029b86ba` |
| llm-dp: `reprollm.yaml` | `ef9560f90fb232e79cf5b78fffd4e5a100dcf18a36f77b652445ae7d5a477161` |

## 10. Corrected DP and materialized HarmBench/FastChat source review

Later harness correction (2026-09-27): the native `EvaluatorConfig` at the pinned
commit does not accept `bootstrap_iters`. A direct constructor probe reproduced
the TypeError; removing only that key accepted the same 100-item, five-shot,
cap-32 configuration. Corrected A `validation/eval.yaml` SHA-256 is
`a7bc8316852aac0e9a4b2fb0ea67b0bf10df9b7debc000cad1b0e1a997ad5467`.
The original hash/bundle above and failed run are retained, not replaced.
Exact-match aggregation uses the native mean/standard-error behavior; no
specific quality score or bootstrap statistic is a gold assertion here.

The output verifier also needed a pinned-format correction: native
`lm_eval/loggers/evaluation_tracker.py:353` serializes tuple arguments to
`arguments.gen_args_0.arg_0` (prompt) and `.arg_1` (generation dictionary).
The evaluator's in-memory list indexing is not the JSONL format. A minimal
read of the original logs reproduced the verifier's KeyError; the corrected
verifier asserts those exact named maps. The independent expectations remain
100 unique documents / 200 filter rows, original two filters, finite metrics,
bounded outputs, and identical A/B document and prompt digests.

The corrected DP manifest quotes its preprocessing description, omits the
integer-typed `training.epochs` field and records the actual fractional horizon
as `training.params.num_train_epochs: 0.125`. Its max steps remains 2, matching
the unchanged driver. This is the explicit temporary representation workaround
from §9, not a schema fix. All five current manifests now pass independent
Pydantic validation. The HarmBench/FastChat drivers parse successfully.

At this review point, a metadata-only inspection of the intended modern
environment found torch, Transformers, vLLM and the listed supporting packages
not yet installed. Therefore compatibility below is checked against official
**target-version source**, not a claim that imports or inference already passed
in the installed environment. A later completed installation needs its own
metadata/import/kernel evidence.

### HarmBench adapter interfaces and import chain

`validation/pipeline.py` uses the original DirectRequest and original classifier
function. Its top-level controller launches target and classifier as separate
subprocesses, each using the same interpreter. The target writes a one-element
completion **list**, and the classifier helper consumes/returns that list. This
matches the original helper's signature; it is intentionally not the old native
CLI's outer dictionary keyed by behavior ID.

The target and classifier `LLM` constructors use explicit revision and tokenizer
revision, float16, tensor parallelism 1, sequence limit 2048 and caps 0.28/0.45.
The target cap is 16 tokens; classifier cap is one token. Official vLLM 0.18.0
source retains all used constructor arguments and
`generate(prompts, sampling_params, *, use_tqdm=False)`, returning a list of
`RequestOutput` objects. Each contains `outputs`, whose completion has `text`
and `token_ids`; `prompt_token_ids` also remains available. No old
`llm_engine.tokenizer.tokenizer` access is used here. This is source-level API
agreement, not a guarantee that the model yields a valid yes/no token.
[vLLM 0.18 LLM](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/entrypoints/llm.py),
[output structures](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/outputs.py).

Importing `baselines.direct_request` first executes `baselines.__init__`, which
imports model utilities. Those import `fastchat.model`, triggering FastChat's
model-adapter imports, including compression, rotary-embedding patches, CLLM and
quantization configuration modules. The baseline also imports Ray; DirectRequest
does not launch it. The selected classifier function still requires spaCy and
datasketch to import `eval_utils`. A successful DirectRequest import cannot be
assumed from its small local implementation alone.
[HarmBench package initializer](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/baselines/__init__.py),
[FastChat model initializer](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/model/__init__.py),
[model adapter](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/model/model_adapter.py).

Do not blindly install the whole original HarmBench requirements into the modern
environment. Its pinned spaCy 3.7.2 requires Thinc <8.3; the usual latest matching
Thinc 8.2.5 requires NumPy <2. Conversely, vLLM 0.18 requires OpenCV-headless >=4.13,
and OpenCV 4.13.0.92 requires NumPy >=2 on Python >=3.9. Using a newer spaCy/Thinc
for this adapter's utility import must be explicitly recorded as a dependency
deviation, not described as restoring the original requirements environment.
[spaCy metadata](https://pypi.org/pypi/spacy/3.7.2/json),
[Thinc metadata](https://pypi.org/pypi/thinc/8.2.5/json),
[vLLM metadata](https://pypi.org/pypi/vllm/0.18.0/json),
[OpenCV metadata](https://pypi.org/pypi/opencv-python-headless/4.13.0.92/json).

### FastChat native generator reached through a resource wrapper

`answer_entry.py` reads the pinned Vicuna snapshot, applies a 0.30 PyTorch
allocator limit, changes into the native judge-data working directory and runs
the original model-answer module. It restores cwd afterward and checks question
81, one choice, two nonempty turns and no literal `ERROR`. The wrapper does not
alter `model.generate` or synthesize answers. Both GPU arguments equal one, so
the native generator's multiworker Ray branch is not selected.

The local snapshot's full path contains `vicuna`, which the original adapter
selector checks after trying its SHA basename. It therefore selects VicunaAdapter;
the model label `vicuna-validation` also selects the original Vicuna conversation
template. The selected adapter does not apply the unrelated long-context or
MPS monkey patches. Its old-weight check reads `model.model.vocab_size`, retained
in official Transformers 4.57.6. The eagerly imported CLLM symbols `Cache`,
`DynamicCache`, and `_prepare_4d_causal_attention_mask` also remain exported at
that version. No definite missing-symbol startup failure was found in these
checked interfaces, but this is not exhaustive import or generation proof.
[Adapter selection](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/model/model_adapter.py),
[Transformers Llama source](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/models/llama/modeling_llama.py),
[cache classes](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/cache_utils.py),
[mask utility](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/modeling_attn_mask_utils.py).

Two important limitations remain:

- Native FastChat uses `--max-gpu-memory` only in its multi-GPU loading branch.
  With one GPU, the supplied `20GiB` value is **not** the active memory limit.
  The wrapper's 0.30 allocator fraction is the actual configured torch ceiling;
  it does not cover every external CUDA allocation. Monitor the process and do
  not describe this as a 20-GiB hard reservation. Standalone torch requires the
  process-local CUDA compatibility library setup, not merely a vLLM-only switch.
- The native common module imports OpenAI and Anthropic even for local answers.
  Its paid OpenAI helper still uses the legacy `openai.ChatCompletion.create`
  API. The repository's `llm_judge` extra requires `openai<1`, conflicting with
  vLLM 0.18's `openai>=1.99.1`. Do not install that extra into this modern shared
  environment or treat a local-answer success as modern-SDK paid-judge coverage.
  SDK installation/import alone does not call the API; paid validation remains
  explicitly deferred.

Sources: [FastChat loader](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/model/model_adapter.py),
[common helpers](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge/common.py),
[extras metadata](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml).

### Updated/new initial-input hashes

The DP manifest hash below supersedes the rejected manifest hash in §9. The DP
driver, config and synthetic text hashes remain unchanged. New driver/config
hashes were computed independently using `sha256sum`; later edits require a new
reviewed hash.

| Case / relative file | SHA-256 |
|---|---|
| llm-dp: `reprollm.yaml` | `95bec6ce6b3e20a4bb8fc14bcad456b77fb633c299afaffec5256006771687b2` |
| FastChat: `validation/answer_entry.py` | `0ad9acddfa823aa88547242aec35b38c622db2b008639b3a419006f1cdc71304` |
| FastChat: `validation/answer.yaml` | `4a797de17b4b825bf6e7ca400ede2f2dd9b8913457b3c51aa271362e1ef75cbf` |
| FastChat: `reprollm.yaml` | `af09864e2e27731fb52275b73c12f953b8dffd48ef7b99cb94f777e46fcf9fec` |
| HarmBench: `validation/pipeline.py` | `ce02e42e91bcee890e32f3a79e5d320c16f9ced3ef5caee134ca021cc1d5910a` |
| HarmBench: `validation/pipeline.yaml` | `cea20d34f6f517e02f299bdc73c572f52be481e15f859817f0c10a2b8c8afe79` |
| HarmBench: `reprollm.yaml` | `a352d0fa09c1fe8bbf9194ae76d4c3aa9d59da90a927e5eee1da76d199dd72fa` |
