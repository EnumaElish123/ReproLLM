# ReproLLM external validation gold answer

> Status: authoritative validation baseline
>
> Baseline date: 2026-09-10
>
> Scope: five clean repositories at the exact commits below

## 1. Purpose and evidence boundary

This document is the single source of truth for ReproLLM's real-repository validation. Every
development session follows the applicable gates in §8 and compares results with the gold answer
in §§3–7. `AGENTS.md` points here instead of duplicating repository metadata or expected output.

The gold answer was derived from repository source, README files, configuration, dependency
manifests, and Git metadata without using `reprollm audit` or `reprollm init` output. Claims follow
[`docs/plan/01_specification.md` §§12.1–13](docs/plan/01_specification.md). ReproLLM observations,
known bugs, and temporary output never redefine the gold answer.

Gold classifications:

- **Exact**: assert the value or complete set at the pinned commit.
- **Allowed set**: the specification permits multiple source candidates; assert membership and
  provenance rather than one invented semantic “primary”.
- **Milestone gold**: add an independently reviewed expected result before activating a future
  resource gate. A command without a reviewed expectation is a smoke run, not validation.

## 2. Pinned portfolio

The portfolio contains five repositories total. lm-evaluation-harness is one of the five, not an
additional sixth target.

| Name | Upstream | Required commit | Local checkout |
|---|---|---|---|
| lm-evaluation-harness | [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) | `b954108c9baaaa934b4ad842033b31a97ee30816` | `../dogfooding/lm-evaluation-harness` |
| FastChat | [lm-sys/FastChat](https://github.com/lm-sys/FastChat) | `587d5cfa1609a43d192cedb8441cac3c17db105d` | `../dogfooding/FastChat` |
| LlamaFactory | [hiyouga/LlamaFactory](https://github.com/hiyouga/LlamaFactory) | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | `../dogfooding/LlamaFactory` |
| HarmBench | [centerforaisafety/HarmBench](https://github.com/centerforaisafety/HarmBench) | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | `../dogfooding/HarmBench` |
| llm-dp-finetune | [jyhong836/llm-dp-finetune](https://github.com/jyhong836/llm-dp-finetune) | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | `../dogfooding/llm-dp-finetune` |

Sprint documents use stable aliases for the first two end-to-end dogfooding targets:

- **Project A** is `lm-evaluation-harness` at the pinned commit above. It exercises the local
  Hugging Face and vLLM evaluation path and is the target already used by M2-T10.
- **Project B** is `FastChat` at the pinned commit above. Its MT-Bench workflow exercises an
  OpenAI-backed LLM judge through `OPENAI_API_KEY` and a concrete `gen_judgment.py` command.

These aliases always inherit the pinned commit and checkout path from this table. They do not
refer to the similarly shaped golden fixtures under `tests/fixtures/repos/`.

Clone once, then detach at the required commit. Never commit these repositories, their model
weights, data, generated manifests, or run artifacts into ReproLLM.

Before every validation, all five checkouts must satisfy:

```bash
git -C <checkout> rev-parse HEAD
git -C <checkout> status --porcelain=v1 --untracked-files=all
git -C <checkout> remote get-url origin
```

`HEAD` must equal the table, status must be empty, and `origin` must exist. A missing or dirty
checkout is an invalid test input, not a product failure and not a passing result.

## 3. Level 0 Git, environment, and scan gold

All five repositories are Git repositories with a committed HEAD, clean tracked files, no
untracked files, an `origin`, and no `.gitmodules`. Therefore:

- `code.git_repo`, `code.git_commit`, `code.clean_tree`, `code.no_untracked`, and
  `code.remote_recorded` pass;
- `code.submodules_initialized` is skipped as not applicable;
- `env.reprollm_initialized` emits INFO because neither `reprollm.yaml` nor `.reprollm/` exists.

| Repository | Dependency manifest | Lockfile | Python declaration | Secret-file result | Python scan |
|---|---|---|---|---|---|
| lm-evaluation-harness | PASS: `pyproject.toml` | WARNING | PASS: `>=3.10` | PASS | 816 files; analysis must disclose truncation to 500 |
| FastChat | PASS: `pyproject.toml` | WARNING | PASS: `>=3.8` | PASS | 148 files; no truncation |
| LlamaFactory | PASS: `pyproject.toml` | WARNING | PASS: `>=3.11.0` | **CRITICAL: tracked `.env.local`** | 311 files; no truncation |
| HarmBench | PASS: `requirements.txt` | WARNING | WARNING: absent | PASS | 123 files; no truncation |
| llm-dp-finetune | PASS: `requirements.txt` | WARNING | WARNING: absent | PASS | 46 files; no truncation |

No repository has `uv.lock`, `poetry.lock`, `Pipfile.lock`, or `conda-lock.yml`; their
`requirements*.txt` files contain non-`==` declarations and are not exact lockfiles.

LlamaFactory's `.env.local` is tracked at the pinned commit and matches specification §16.4.
Empty values do not exempt a forbidden filename, so `env.secret_files_ignored` must be CRITICAL.

Every persisted target/evidence path must be repository-relative. `generated_at` must be UTC with
`Z` suffix and second precision. Report ordering must be stable.

## 4. Unpinned LLM-critical dependency gold

Each package below produces exactly one `env.llm_critical_deps_pinned` WARNING. Compare complete
sets, not only summary counts.

| Repository | Exact expected set | Count |
|---|---|---:|
| lm-evaluation-harness | `accelerate, anthropic, datasets, evaluate, lm_eval, numpy, openai, peft, sentencepiece, sglang, torch, transformers, vllm` | 13 |
| FastChat | `accelerate, anthropic, datasets, deepspeed, flash_attn, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, vllm, xformers` | 15 |
| LlamaFactory | `accelerate, bitsandbytes, datasets, deepspeed, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, trl, vllm` | 14 |
| HarmBench | `anthropic, numpy, openai, safetensors, vllm` | 5 |
| llm-dp-finetune | `datasets, numpy, peft, torch, transformers` | 5 |

HarmBench exactly pins `accelerate, bitsandbytes, datasets, deepspeed, evaluate, peft, torch,
transformers, trl` in its nested alignment-handbook requirements; these packages must not appear
in its warning set.

At lm-evaluation-harness's deterministic first-500-file boundary, `tokenizers` and literal HF IDs
located in the remaining 316 Python files are not findings/hints. The truncation itself must be
visible to the user so absence is not misrepresented as a complete scan.

## 5. Profile detection gold

Confidence requires independent semantic signals. Separator aliases such as `red team` and
`red-team`, `dp-sgd` and `dp_sgd`, or `tool call` and `tool_call` represent one signal, not two.

| Repository | Exact detected profiles |
|---|---|
| lm-evaluation-harness | `agent=low, evaluation=high, finetuning=high, inference=high, llm_judge=low, rag=low` |
| FastChat | `evaluation=low, finetuning=high, inference=high, llm_judge=medium` |
| LlamaFactory | `agent=medium, evaluation=medium, finetuning=high, inference=high, llm_judge=low, rag=medium` |
| HarmBench | `agent=low, evaluation=medium, finetuning=high, inference=high, llm_judge=low, privacy=low, safety=medium` |
| llm-dp-finetune | `finetuning=high, privacy=medium, safety=low` |

Unlisted shipped profiles are absent. `agent` and `rag` remain report-only and are never written to
`experiment.profiles` by `init`.

The llm-dp-finetune safety result is a regression sentinel. Its only safety text is one
`Red-Team` span in `README.md:69`, inside a model-cache path. Matching that span through two
equivalent spellings must still yield `safety=low`.

An exact directory segment named `eval` or `evaluation` is one evaluation keyword signal. The
signal applies only to directory names; a prose substring such as “evaluation” follows the normal
keyword table.

## 6. Detection hints gold

Compare provider/backend lists as sets. HF ID hints retain repository-relative source path and
physical line; multiple source occurrences of the same ID are allowed.

| Repository | Providers | Backends | Adapter | Datasets | `trust_remote_code` |
|---|---|---|---|---|---|
| lm-evaluation-harness | `anthropic, openai` | `sglang, vllm` | true | true | true |
| FastChat | `anthropic, openai` | `sglang, vllm` | true | true | true |
| LlamaFactory | `openai` | `sglang, vllm` | true | true | true |
| HarmBench | `anthropic, openai` | `vllm` | true | true | true |
| llm-dp-finetune | empty | empty | true | true | true |

HF ID allowed sets:

- lm-evaluation-harness: empty within the deterministic first 500 Python files;
- FastChat: `EleutherAI/pythia-160m`, `lmsys/vicuna-7b-v1.5`;
- LlamaFactory: `Qwen/Qwen3-4B-Instruct-2507`, `Qwen/Qwen3-8B`,
  `Qwen/Qwen2.5-7B-Instruct`, `meta-llama/Meta-Llama-3-8B-Instruct`,
  `llamafactory/tiny-random-qwen3`;
- HarmBench: empty;
- llm-dp-finetune: empty.

## 7. `init` gold

Run `init` only in a disposable clone or worktree. The generated manifest must load immediately
and its subsequent audit must be Level 1 without crashing.

Expected profile lists contain high/medium shipped profiles only, in deterministic order:

| Repository | Exact `experiment.profiles` | `models.primary.id` |
|---|---|---|
| lm-evaluation-harness | `[evaluation, finetuning, inference]` | TODO |
| FastChat | `[finetuning, inference, llm_judge]` | member of FastChat HF ID allowed set, with source comment |
| LlamaFactory | `[evaluation, finetuning, inference]` | member of LlamaFactory HF ID allowed set, with source comment |
| HarmBench | `[evaluation, finetuning, inference, safety]` | TODO |
| llm-dp-finetune | `[finetuning, privacy]` | TODO |

README/config values never auto-fill a model. FastChat and LlamaFactory are multi-model frameworks;
the current static evidence cannot determine their semantic primary model, so validation checks
allowed-set membership and provenance rather than hard-coding one candidate.

## 8. Mandatory validation gates

### Gate A — every development session

Run after the normal test/lint/type/schema quality gate:

1. Verify all five checkout SHAs and clean states using §2.
2. Run every non-resource command changed in the session against all five repositories. At minimum,
   run Level 0 `audit --format json --fail-on never` on all five.
3. When `init`, profile detection, manifest loading, or Level 1 rules changed, run `init` and the
   subsequent Level 1 audit in disposable clones for all five.
4. Compare rule status, complete dependency sets, profiles, hints, paths, line evidence, scan-limit
   diagnostics, and `init` output with §§3–7. Summary counts alone are insufficient.
5. Record checkout SHA, exact command, exit status, elapsed time, expected result, actual result,
   and every delta in the session report.

Completion criterion: five valid target results, no crash, no silent skip, and no unexplained gold
delta. A gold mismatch blocks completion until it is fixed or the independently rechecked gold is
updated with an explanation.

### Gate B — resource validation by milestone

Resource gates run at the end of their owning milestone and before release, not after every
ordinary session. Before activating a scenario, add its exact command, bounded inputs, artifact
hashes, and independently reviewed expected result to this document.

| Activation | Mandatory real-world validation |
|---|---|
| M4 (`lock`) | Resolve real HF model/dataset revisions for applicable cases; exercise offline and online modes. Run authenticated provider verification only when credentials and budget are provisioned. |
| M5 (`run`) | lm-eval: one tiny-model/single-task inference; FastChat: local answer generation per §8.3 plus the judge pair per §8.4 (DeepSeek, promoted to the formal standard by §8.5); LlamaFactory: 1–2 step tiny LoRA/QLoRA run per §8.3; HarmBench: one behavior through the minimal attack/target/classifier path per §8.3; llm-dp: the DistilGPT2 single-GPU privacy fine-tune per §8.3 (promoted to the formal standard by §8.5). Verify capture, hashes, relative paths, and redaction. |
| M6 (`diff`) | For every M5 scenario, make paired runs that change exactly one high-value field and assert the expected semantic drift path and severity. |
| M7 (`export`, `discover`) | Export each available state; run offline discover collection checks on all five; with explicit credentials/budget, run one API-backed judge and one opt-in discover request. Verify payload file list and redaction before sending. |
| M8 and every release | Rerun all applicable Gate A and Gate B scenarios at their pinned commits and explain every baseline delta. |

No agent may spend money, use credentials, download restricted data, or start a resource-intensive
GPU job unless those resources are explicitly provisioned for the validation. Missing GPU,
credentials, provider access, or approved budget is **blocked**, never passed. Record the blocker
and complete every unaffected gate.

### 8.1 M4 metadata-resolution scenarios (reviewed 2026-09-19)

These expectations were established from the pinned upstream sources, direct HF
metadata/file HTTP responses, and independent `hashlib.sha256` calculations before
running ReproLLM. They do not change the five commits or Level 0 gold above.
Project C is `llm-dp-finetune` at its §2 pin, using
`configs/fine-tune/echr-llama2-7b-dp8.yml`. A/B retain the M3 manifests.
LlamaFactory and HarmBench use model/data metadata-only manifests, not claims of a
complete training/evaluation experiment. Generated manifests and artifacts remain
outside the ReproLLM worktree.

Inputs are bounded to the manifests below, the listed tracked files, model/dataset
revision metadata, and at most 2 MiB per `config.json`, `tokenizer_config.json`, or
`chat_template.jinja`. No weights, dataset content downloads, inference, training,
paid APIs, or `--verify-api` calls are involved. The gated credential is supplied
only to the HF metadata process by the maintainer's explicit authorization; no
credential value is recorded. The Linux-machine H2 check is recorded separately
if only a macOS runner is provisioned.

| Target | Manifest SHA-256 | Selected input evidence |
|---|---|---|
| FastChat | `sha256:649372b39a13262ca09649a3d65849b748a778bb0d3c480895cf251ee9920189` | M3 Project B; `fastchat/llm_judge/` |
| HarmBench | `sha256:a0899d290472ecbf4e366298059ba629c079d39795925403fe0f331e37665ba7` | Vicuna entry in `configs/model_configs/models.yaml`; tracked behavior CSV |
| LlamaFactory | `sha256:3e28d429fe19e3b179314584c0402ea857e95cf9be52061a1198839f6612cda0` | `examples/train_lora/qwen3_lora_sft.yaml`; local identity/alpaca demos |
| llm-dp-finetune | `sha256:5b53f6552e12e152b1efb21f995adc73ce6c06ffe73aed436924588c88724b82` | DP8 config; `data/echr/echr.py`; privacy arguments; optimizer/scheduler source |
| lm-evaluation-harness | `sha256:39eee344461c486bef31b55cce53789fd17c71e47a637f7d195c9ef9d68ad41a` | M3 Project A; `lm_eval/tasks/gsm8k/gsm8k.yaml` |

Remote revisions are independently observed `main` tips, not silently advanced
pins. A changed upstream tip is a delta to investigate against the provider page.

| HF repository | Expected SHA | Anonymous / authenticated metadata behavior |
|---|---|---|
| `Qwen/Qwen2.5-0.5B-Instruct` | `7ae557604adf67be50417f59c2c2f167def9a775` | HTTP 200; small model files accessible |
| `lmsys/vicuna-7b-v1.5` | `3321f76e3f527bd14065daf69dad9344000a201d` | HTTP 200; small model files accessible |
| `Qwen/Qwen3-4B-Instruct-2507` | `cdbee75f17c01a7cc42f958dc650907174af0554` | HTTP 200; small model files accessible |
| `meta-llama/Llama-2-7b-hf` | `01c7f73d771dfac7d292323805ebc428287df4f9` | Repo info 200 in both modes; config/tokenizer files 401 without token, 403 with the provisioned token (model-author access rejection) |
| `openai/gsm8k` | `740312add88f781978c0658806c59bc2815b9866` | HTTP 200; revision only, no dataset content |
| `ecthr_cases` | `1351ba4211ed9bc44692e6a1e2f237c4e3775b41` | HTTP 200; revision only, no dataset content |

| Artifact | Expected SHA-256 |
|---|---|
| `Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775/config.json` | `sha256:18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45` |
| `Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775/tokenizer_config.json` | `sha256:5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583` |
| `Qwen/Qwen2.5-0.5B-Instruct` extracted chat-template UTF-8 | `sha256:cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f` |
| `lmsys/vicuna-7b-v1.5@3321f76e3f527bd14065daf69dad9344000a201d/config.json` | `sha256:e122b598d0734b489590e99e3b3562a11ce67ea13bce390a7868b4f73ae6e615` |
| `lmsys/vicuna-7b-v1.5@3321f76e3f527bd14065daf69dad9344000a201d/tokenizer_config.json` | `sha256:1cbc84c8a5b41e0ec24e0da66677773569fb0ccfa753d5d184e343e2ec3815a0` |
| `Qwen/Qwen3-4B-Instruct-2507@cdbee75f17c01a7cc42f958dc650907174af0554/config.json` | `sha256:5beea1a4a34c62782bfb2f911c606741a3bab8f92d80a118fa053c28af12e8ba` |
| `Qwen/Qwen3-4B-Instruct-2507@cdbee75f17c01a7cc42f958dc650907174af0554/tokenizer_config.json` | `sha256:a62ff0a2472a0fa1b8eaabcb57c59b58afa42a22831dc141400b6e0cf2b65ce3` |
| `Qwen/Qwen3-4B-Instruct-2507` extracted chat-template UTF-8 | `sha256:64f85b198065d0fba2a81f37e10ed68161ce2c19a754c7100e67e0ca2ee9c326` |
| `FastChat:fastchat/llm_judge/data/judge_prompts.jsonl` | `sha256:fd283293406d024f44c174b094ef48031d0687a4682fd3a56b29b138f80281b6` |
| `FastChat:fastchat/llm_judge/data/mt_bench/question.jsonl` | `sha256:119565adbab82227089cefdb44c8d7e2cf04dc0a0ec233634c82e7d4e2a944f7` |
| `FastChat:fastchat/llm_judge/data/mt_bench/reference_answer/gpt-4.jsonl` | `sha256:f957a5bc977badb66885ec970e6cd08527845780313f0995764260e5777b9b3f` |
| `FastChat:fastchat/llm_judge/common.py` | `sha256:71c3b317322845cb05eb6d9b555b03e5084fa59085d24989ce521fcfa8bdc9a7` |
| `FastChat:fastchat/llm_judge/gen_model_answer.py` | `sha256:8feb3c19262b8f8567b49c1cd45b0adfd83f199bdcd17e891a05dd608300c7c6` |
| `FastChat:fastchat/llm_judge/gen_judgment.py` | `sha256:b6d74c050f91d93eb8c3e339ccc11f230032b4c6093c65f3683e0eba1c13b2ea` |
| `HarmBench:configs/model_configs/models.yaml` | `sha256:8d4b6c734bae3035ec007276e91b37bbcd07edc9649b97bc2d7cb77c563cf6b5` |
| `HarmBench:data/behavior_datasets/harmbench_behaviors_text_all.csv` | `sha256:8d81accedd38eaaf8b760618622bb888417d1fd0c86eba65c427a16f1cbb4afc` |
| `LlamaFactory:data/alpaca_en_demo.json` | `sha256:bcc37c64db1a739a0789a1b81f251146fcf4459f903474bc9e3c21bbb5628318` |
| `LlamaFactory:data/dataset_info.json` | `sha256:17162e129cbfede1ef7e955dbb7819146b78cd8809fa4f39dff4f9e61308c50f` |
| `LlamaFactory:data/identity.json` | `sha256:fd029da7dd3df283ed034c82375d16d125a7b07cf1cb0316d03fb8743057d5f2` |
| `LlamaFactory:examples/train_lora/qwen3_lora_sft.yaml` | `sha256:783c247613e0c46c4b4ea5c6627acd5387d939af91f22a9d6a9efdb4996147ae` |
| `llm-dp-finetune:configs/fine-tune/deepspeed_stage3.json` | `sha256:c445beb05234a979ed80a71a7e209395564eea39630c730de18eb2d51be8b722` |
| `llm-dp-finetune:configs/fine-tune/echr-llama2-7b-dp8.yml` | `sha256:20c9c1ab6bd19f5b92789d394beee9a4131d28a841d2c80ee93235271490fc12` |
| `llm-dp-finetune:data/echr/echr.py` | `sha256:0112037c9b509e83ed1957b8d2ae8504b2449257b58f25a1d9034ac48a21aa8d` |
| `llm-dp-finetune:src/llm_pft/arguments/privacy_args.py` | `sha256:39658034cf7df5c5bee934e8010d4cfdfe4288abb2fe1f3ea9875458a97045a7` |
| `llm-dp-finetune:src/llm_pft/models/language_model.py` | `sha256:b3fb5b2302bc98119738808168a7edde4f975acf36aeeb0e3ebb8db761a6c896` |
| `lm-evaluation-harness:lm_eval/tasks/gsm8k/gsm8k.yaml` | `sha256:82eb1780b263bc040729032b3e076990c7933f42163c91e359f38820dd1d8833` |

For each clean disposable clone (`$CASE`), use its manifest with the exact hash
above. `$OUT` is outside the clone and repository:

```console
reprollm lock "$CASE" --offline
reprollm lock "$CASE" --check
reprollm audit "$CASE" --format json --fail-on never --output "$OUT/offline.json"
reprollm lock "$CASE"
reprollm lock "$CASE"
reprollm lock "$CASE" --check
reprollm audit "$CASE" --format json --fail-on never --output "$OUT/online.json"
```

Commit generated manifest/lock inside disposable clones before audits so their
Git findings refer to clean artifacts. Preserve each lock outside the clone for
comparison. Expected exits are 0, including unresolved/gated cases. Compare both
online locks after removing only `generated_at`, `resolved_at`, `observed_at`.
Check every listed local hash and every resolved remote SHA/config/template hash.
Manifest and project-rule freshness and working-tree file consistency must pass.

- Offline: no HTTP, no declared remote revisions in these manifests, so HF
  revisions remain `unresolved/offline`; local hashes still match the table.
- Online A: exact Qwen model/tokenizer and GSM8K revisions, exact config/template
  hashes. Backend version remains unresolved when vLLM is not installed.
- Online B: exact Vicuna model/tokenizer/config; the Hub has no chat template
  (`absent` with PASS evidence). Judge is `snapshot_alias`, null provider revision,
  INFO for `model.revision_pinned`, and PASS for judge pinnability/prompt hashes.
- LlamaFactory/HarmBench: exact selected HF model identities and local file hashes;
  remaining presence gaps belong to the deliberately limited metadata manifests.
- C: repo revision and tokenizer revision are public and exact even when gated
  files are denied. Config provenance is `unresolved/hf_api_forbidden`; this is
  distinct from the mocked fixture that denies the repo-info endpoint itself.
  Run both without and with `HF_TOKEN`, verify sanitized denial provenance and
  zero occurrences of the actual token in stdout/stderr, lock and reports.
  **Denial handling can pass while successful gated-file resolution is blocked.**
  The selected upstream config has no explicit training seed; preserve that
  actionable gap instead of inventing a seed in the manifest.
- Run `doctor --json` in all five original checkouts; run the opt-in network probe
  against gpt2 with the shared HF client. Compare statuses and relative document
  paths; missing optional GPU/uv tools are explicit warnings.

References: pinned source paths above; direct `/api/models/.../revision/main`
and `/api/datasets/.../revision/main` on [Hugging Face](https://huggingface.co/),
and each model file at the recorded SHA. Model-author rejection must not be
bypassed or reclassified as successful access.

### 8.2 Linux resource follow-up (2026-09-26)

The maintainer authorized public-model downloads and bounded GPU validation,
provided existing processes are not disturbed. Large downloads belong under
`/mnt/share_data/czy/`; permissions must be verified before downloading. Paid
FastChat judge execution is deferred until the maintainer supplies its API
configuration. A public-small-model DP case is authorized as **supplementary**;
it cannot pass the original gated Llama-2 scenario.

On 2026-09-27 the maintainer supplied DeepSeek credentials. Its endpoint and
compatibility constraints are documented in
[`deepseek-api-validation.md`](docs/dogfooding/deepseek-api-validation.md).
A DeepSeek judge is a separate supplement, not the original GPT-4 gold. The
maintainer subsequently approved the temporary adapter and a **CNY 3 total
ceiling** on 2026-09-27. The activated scenario and pre-execution gold are in
§8.4. The existing local-resource scenarios below remain independently authorized.

The Linux checkout lacks the external `manifests/` and
`m4-lock-2026-09-19/` evidence directories. The five exact §8.1 manifests cannot
be recovered from their hashes. Do not label reconstructed manifests as those
original inputs or replace their gold. The following new, metadata-only inputs
exercise the same remote identities and tracked files, independently of runtime
training scenarios; they intentionally do not fill unrelated presence fields.

| Target | Supplementary metadata manifest SHA-256 |
|---|---|
| lm-evaluation-harness | `7a524a1dd41cdca08ca1514cbd5eb4874175bfeff73ae69e94eac2d22fc2bc4f` |
| FastChat | `73b25168de2f52cc994f8b1535fdf04898ad8d8839e260f2f10893f38a3d9ae9` |
| LlamaFactory | `7644338fcc0f7f184bbd031d1b89d6bccc24cacb657e254e1c324df3f13defae` |
| HarmBench | `73164c087770e87b62aaa9b45fcb831134b47c8bf36c04716b8e1bca57847aa5` |
| llm-dp-finetune | `4967f1ed18b8f2484f1a8de6b1252dc7049f7deb3ec2afe2a47959b9e12cea36` |

For each input, run the §8.1 offline/two-online/check/audit command sequence in
a disposable clone. Use `HF_ENDPOINT=https://hf-mirror.com` and process-local
proxy bypass when the official endpoint is unreachable. Expected remote SHAs,
model config/template hashes and tracked-file hashes remain the independently
established §8.1 values; recompute local hashes directly before invoking ReproLLM.
The mirror is an explicit transport deviation, not proof of official endpoint
availability. Assert every resolved hash, both online locks' normalized equality,
Level 2, freshness and file-consistency PASS. Anonymous gated-file denial must
remain unresolved, not success. Authenticated access is not attempted without
provisioned credentials. No exact M3-manifest replay is claimed.

Runtime scenarios must additionally record their concrete bounded command,
inputs and independent capture/diff expectations here before activation.
Quality scores and generated language are not deterministic gold answers;
input identity, consumed parameters, finite training loss, real optimizer steps,
artifact integrity and specified semantic drift are the acceptance targets.

Independent input review and dependency research:
[`m4-m6-resource-compatibility.md`](docs/dogfooding/m4-m6-resource-compatibility.md).
Observed commands, results and unresolved resource gates:
[`m4-m6-linux-validation.md`](docs/dogfooding/m4-m6-linux-validation.md).

### 8.3 Activated bounded Linux runtime inputs (2026-09-26)

The following **new supplemental inputs** are independently reviewed in
[`m5-m6-runtime-gold.md`](docs/dogfooding/m5-m6-runtime-gold.md). They do not
replace the original pinned-repository gold, the paid judge, or gated Llama-2.
All five manifests pass schema validation before execution. Artifact hashes and
quality scores produced by a run are observations, never preselected gold.

| Checkout | Bounded child command after `reprollm run --capture-output --` | A → B; required semantic leaf |
|---|---|---|
| lm-evaluation-harness | `python -m lm_eval run --config validation/eval.yaml` | 100 GSM8K test items, 5-shot, Qwen 0.5B; cap 32 → 48; `generation.max_tokens` HIGH |
| LlamaFactory | `python validation/train_entry.py` | Native LoRA CLI, Qwen3 4B, first 16 identity records, cutoff 64, 2 updates; learning rate 0.0001 → 0.0002; `training.learning_rate` HIGH |
| llm-dp-finetune | `python validation/train_entry.py` | Original single-GPU fastDP method, public DistilGPT2, 16 synthetic texts, 2 updates; target epsilon 8 → 4; `privacy.mechanism.params.target_epsilon` MEDIUM under current policy |
| HarmBench | `python validation/pipeline.py` | Original DirectRequest and classifier function, one `profane_insult_generation` behavior, Vicuna 7B then 13B classifier in separate processes; cap 16 → 24; `generation.max_tokens` HIGH |
| FastChat | `python validation/answer_entry.py` | Native answer generator, question 81, one choice/two turns, temperature 0.7/seed 0; cap 32 → 48; `generation.max_tokens` HIGH; **no paid judge** |

Before each run, require GPU 0 used memory below 2 GiB, at least 70,000 MiB
free, utilization no more than 10%, and at least 50 GiB free disk space. Do not
use GPU 1 or terminate another process. Run GPU stages sequentially; set
`CUDA_VISIBLE_DEVICES=0`, CPU math threads 2, external trackers disabled. The
vLLM memory fractions are 0.12 (lm-eval), 0.28/0.45 (HarmBench target/classifier);
PyTorch allocator caps are 0.35 (LoRA), 0.15 (DP), 0.30 (FastChat). The latter's
native `--max-gpu-memory 20GiB` is not enforced on its single-GPU path, so it is
not the resource guard. Remove inherited distributed-launch overrides.

Use isolated `modern` and `dp` environments on the approved data volume. Install
ReproLLM in each and use that same environment for launcher and child. The
modern CUDA 12.9 compatibility libraries are process-local; never replace the
system driver. Preserve metadata-only M4 results separately. Resolve model/data
identities online before running cached local execution. All weights, caches,
checkpoints and disposable checkouts stay on the approved data volume.

Variant A manifests, SHA-256:

| Checkout | Manifest SHA-256 |
|---|---|
| lm-evaluation-harness | `ac4bfde5a7538bfa6058746b51c3e00d25cc327b82c6311fa734f2f33da25775` |
| LlamaFactory | `d201b66e2992e21d4e20d11181dbe9ba4911b901b8cbfbe66f59c569a7e503f3` |
| llm-dp-finetune | `95bec6ce6b3e20a4bb8fc14bcad456b77fb633c299afaffec5256006771687b2` |
| HarmBench | `a352d0fa09c1fe8bbf9194ae76d4c3aa9d59da90a927e5eee1da76d199dd72fa` |
| FastChat | `af09864e2e27731fb52275b73c12f953b8dffd48ef7b99cb94f777e46fcf9fec` |

Input driver/config hashes are recorded in the independent review and external
evidence. Before executing a variant, resolve its lock and commit its manifest,
lock and validation inputs in the disposable clone; ignore generated output/run
directories. Verify clean code capture and lock freshness. Change only the
listed experimental parameter and its binding declaration for B, then relock
and commit. Preserve A's outputs before B can overwrite them.

Harness preparation correction on 2026-09-27: remove the unsupported
`bootstrap_iters` YAML key; the pinned native `EvaluatorConfig` then accepts
the unchanged scenario. Corrected A config hash is
`a7bc8316852aac0e9a4b2fb0ea67b0bf10df9b7debc000cad1b0e1a997ad5467`;
the initial bundle/hash remains historical evidence. Read saved request
arguments using the pinned logger's `gen_args_0.arg_0` / `arg_1` dictionaries,
not the evaluator's pre-serialization list format. This correction changes no
sample, model, generation setting, metric, or semantic-diff expectation.

For both variants require completed real execution, matching observed bindings,
installed-package versions, independently recomputed input/output hashes and
sizes, no persisted machine identity or absolute paths, and the scenario-specific
output checks in the independent review. Diff the two captured run IDs with
`--format json --fail-on HIGH` (expected exit 1); require the exact leaf/value/
severity above and explain all additional changes. Self-diff must have no
changes. DP's HIGH config-file hash must not conceal its MEDIUM privacy leaf.

Snapshot fidelity is a separate assertion: non-secret stop tokens (including
`</s>`) and relative artifact globs must retain their meaning in captured
documents and the state loaded from them. Raw-byte hashes can remain correct
while a redacted snapshot is wrong. The 2026-09-27 lm-eval review found such a
failure; see the [execution report](docs/dogfooding/m4-m6-linux-validation.md#new-product-defect-path-redaction-changes-non-secret-experiment-values).
This is an open implementation finding, not permission to change the gold.

The fractional DP accounting horizon is 0.125 epoch (2/16), truthfully declared
under `training.params.num_train_epochs` with `max_steps: 2`. The normative
`training.epochs: number` is currently implemented as an integer and rejects
0.125; omitting that optional field is a documented workaround, not a fix or a
passing test of fractional-epoch support. Original Llama-2/ECHR/ZeRO remains
blocked; this public single-GPU supplement makes no production privacy claim.

### 8.4 Approved DeepSeek/FastChat supplementary judge (2026-09-27)

> Promoted to the **formal** FastChat-judge acceptance standard by the
> §8.5 baseline-maintenance decision of 2026-09-28; executed twice within
> budget on 2026-09-27. The "supplementary" wording below is the historical
> record of the scenario's original scope.

Approval: temporary transport adaptation, total ceiling **CNY 3**. Original
FastChat source remains pinned at `587d5cfa1609a43d192cedb8441cac3c17db105d`.
Use a separate disposable checkout, the isolated modern environment, no GPU,
and the original `play_a_match_single` / `run_judge_single` prompt builder and
score parser. Only the provider-name dispatch, OpenAI-compatible conversation
template and obsolete network call are adapted in memory. This does not verify
the old SDK call or pass the original GPT-4-snapshot scenario.

Concrete child: `python validation/judge_entry.py`. Input is public MT-Bench
question 82, first turn, with a fixed **synthetic email answer** declared in
`validation/judge.yaml`; it is not represented as a local model's generated
answer. Use the original `single-v1` rubric. No private project text is sent.
Model is `deepseek-flash`, endpoint `https://api.deepseek.com`, thinking explicitly
disabled and temperature 0. `models.judge.provider: other` plus
`params.actual_provider: deepseek` avoids misidentifying the vendor. The key uses
the conventional `OPENAI_API_KEY` transport variable for M5-H3 capture coverage.
Before inference, require authenticated `/models` to list the selected model.

Exactly two completion attempts at most; no implicit or explicit retries. A/B
changes only `evaluation.judge.params.max_tokens`, **256 → 384**, plus the same
config scalar. Inputs are limited to 4,000 UTF-8 JSON bytes and a 90-second
wall-clock request deadline. Reserve the published entire 1 Mi-token context
at peak uncached input cost before each request (CNY 2.0992 / 2.100224 including
the respective output caps). Settle only from valid returned cache-hit, cache-miss
and completion usage. A timeout retains the entire reservation, preventing a
second request when the remainder is insufficient. Stop on any request failure.
This deliberately conservative accounting uses the verified current
[official CNY tariff](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/);
report estimated token charges, not an unobserved account invoice.

Independent gold before paid execution:

- Exactly one real provider judgment per successful run; nonempty text, finish
  reason `stop`, original parser yields a finite score from 1 to 10. Neither a
  particular score nor identical output text is gold.
- Outgoing system/user messages equal the original rubric plus the selected
  public question and fixed answer. The provider request actually consumes the
  cap recorded by the config binding. Retain model request/response identity,
  usage, response ID/fingerprint when present, prompt digest and effective options.
- ReproLLM captures the identical command, clean disposable commit, matching
  package versions, all four bindings, declared input/output hashes and sizes,
  and manifest/lock snapshots. `OPENAI_API_KEY` is exactly `{present: true}`;
  the real value occurs zero times in logs, captures, outputs and evidence.
  ReproLLM-owned captures also contain no machine identity or absolute paths.
- Judge alias remains `unpinnable`, revision null. All six selected `judge.*`
  rules and file/lock/model/environment consistency should pass; report every
  unrelated upstream finding without suppression.
- Real pair diff: exact nested cap leaf 256 → 384 is **MEDIUM** under the
  current one-segment wildcard policy, the changed config-file hash HIGH, and
  changed clean disposable commit MEDIUM. Explain the full remaining delta set.
  `--fail-on HIGH` exits 1; self-diff has no changes. Do not mistake the HIGH
  file hash for a correctly HIGH judge-parameter policy.

Variant A input SHA-256 values, fixed before execution:

| Input | SHA-256 |
|---|---|
| `reprollm.yaml` | `55de258f63c36ae5b72a4ea14f0bd8d35e8c51d29c2efcab7f0c7316020181f2` |
| `validation/judge.yaml` | `7298a5b24f5b6537a924623c9481117ab5f0965d2d4abb247a5adb0026c8fa1c` |
| `validation/judge_entry.py` | `35659c94714958186c5baa2a33946606055b82fac286722de8ca05c2b8990f02` |
| `validation/judge_transport.py` | `78f12d538c7bd0b9588da4624d8af37ab0fddd162554c62c717d52bf211af232` |

Network-free transport tests use only synthetic credentials and mocked HTTP,
covering the exact request body, tariff calculation, no-retry timeout reservation,
and rejection before network for unapproved output limits. Live acceptance is
recorded separately in the session report, never inferred from these mocks.

### 8.5a Completion record — FastChat and LlamaFactory (2026-09-28)

The FastChat §8.3 answer-generation row and the LlamaFactory §8.3 row are
**complete**: the queued A/B runs of 2026-09-27 passed the full report review
against the pre-execution gold — real native execution (Vicuna 7B answers;
Qwen3-4B LoRA with two real optimizer steps and finite decreasing loss),
complete capture, zero snapshot corruption, and pair diffs of exactly the
required HIGH leaf plus config hash HIGH and clean commit MEDIUM. Evidence
under `evidence/runtime/{FastChat,LlamaFactory}/`; review recorded in the
Linux validation report. HarmBench and the lm-eval clean re-pair remain open.

### 8.5b Completion record — lm-eval clean re-pair and HarmBench (2026-09-29)

Maintainer authorized shared-GPU execution (relaxed guard recorded in the
controller: exclusive lease, GPU-0 pinning, memory-fraction caps and the disk
reserve all retained) plus completing the classifier download.

**lm-evaluation-harness clean re-pair.** The fidelity fix (`fc3f6aa`) was
active through an editable install pointing at main `690fe67`. Variant inputs
restored byte-identical from the corrected 2026-09-27 commits (`2a977fd1` /
`0b99b87e`); runs `20260929T012042Z-b154ee` / `…T012830Z…` completed with
exit 0 (79.7 s / comparable). The pair diff is exactly the required
`generation.max_tokens` 32 → 48 HIGH plus config hash HIGH, clean commit
MEDIUM and four NONE fields; self-diff empty. Both manifest/lock snapshots are
byte-identical to the expected privacy-processed sources with **zero**
path-redaction misfire lines — the 2026-09-27 corruption does not reproduce.
Historical runs and evidence archived under
`evidence/runtime/lm-evaluation-harness-pre-fix-20260927/`. The §8.3 lm-eval
row is complete.

**HarmBench local pair (first execution).** The queued classifier download
was incomplete: shards 1–3 fully downloaded but never renamed, and the
tokenizer files absent — the cause of the one prior failure. The three shards
were resumed-verified, `tokenizer.model`/configs fetched, and every shard plus
the tokenizer verified against the official API LFS sha256 (mirror ETags are
not LFS hashes — recorded to prevent a repeat misdiagnosis). Variant inputs
match the reviewed input plan bytes. Runs `20260929T013849Z-8c6d58` (A) and
the B run completed with exit 0 through the real DirectRequest target
(Vicuna 7B, revision `3321f76e…`) and HarmBench classifier (Llama-2-13b-cls,
revision `bda70534…`); five bindings observed including both model revisions;
no privacy violations; snapshots clean against each variant's own commit.
Pair diff: exactly `generation.max_tokens` 16 → 24 HIGH + config hash HIGH +
commit MEDIUM + four NONE. The §8.3 HarmBench row is complete.

With §8.5a this closes every §8.3 runtime row. GPU 0/1 readings returned to
their pre-run levels afterward; no download or validation process remains.

### 8.5c M6-H2 maintainer acceptance (2026-09-29)

**Accepted.** The maintainer reviewed the text diff of the 2026-09-29 clean
lm-eval pair and confirmed the 30-second readability requirement is met: the
change source (`generation.max_tokens 32 → 48 [HIGH]`) is immediately clear,
and the verdict line states non-comparability. Review note, recorded verbatim
in substance: `files.*.sha256` lines may confuse users unfamiliar with
development workflows; address via README or a dedicated output-reading
document. Disposition: `docs/diff.md` gained a "Reading the output" section
explaining every line kind (including file-hash and commit rows); README
links to it. M6-H2 is closed.

### 8.5 Baseline maintenance: promotion of supplementary scenarios (2026-09-28)

Maintainer decision recorded in a dedicated reviewed change per §9. Two Gate B
scenarios whose original definitions require unavailable credentials are
re-based on their already-executed, independently reviewed supplements. Pinned
commits, Level 0 gold, and every other gold section are unchanged. No tool
output created this section; it records a maintainer decision on evidence that
was independently established before execution (§§8.3–8.4 and
`docs/dogfooding/m5-m6-runtime-gold.md`).

#### FastChat judge: DeepSeek pair is now the formal standard

- **Retired original**: the GPT-4 MT-Bench snapshot scenario. It required an
  OpenAI credential never provisioned; it was never executed.
- **Formal standard**: the §8.4 scenario — DeepSeek (`deepseek-flash`), adapted
  in memory only at the provider-dispatch layer, original MT-Bench question 82,
  synthetic declared answer, `single-v1` rubric, A/B judge cap 256 → 384.
  Executed twice on 2026-09-27 within the approved CNY 3 ceiling (estimated
  CNY 0.003476 conservatively); both completions, captures, audits and diffs
  are retained under `evidence/runtime/FastChat-deepseek/`.
- **Why equivalent for this tool**: the DeepSeek endpoint is OpenAI-compatible
  and exercises the identical `openai`-provider HTTP path, key-transport
  capture (`{present: true}`), consumption recording, and pair-diff semantics
  that the GPT-4 scenario was designed to prove. The remaining difference is
  the vendor identity, which no ReproLLM behavior distinguishes on that path.
- **Residual limitations that stay open** (owned by fix reports, not by gold):
  the six CRITICAL audit findings of the narrow judge-only manifest are
  explained in the session report — five presence findings from applying the
  full `llm_judge → evaluation → inference → core` chain to a judge-only run,
  and one `model.revision_pinned` CRITICAL for a truthful `provider: other`
  DeepSeek entry. The nested judge-cap leaf differring as MEDIUM under current
  policy is likewise retained as a known policy gap. None may be silenced or
  relabeled to claim a cleaner run.

#### llm-dp privacy fine-tune: DistilGPT2 pair is now the formal standard

- **Retired original**: the gated Llama-2 multi-GPU DP fine-tune. Gated access
  was never granted for weight execution.
- **Formal standard**: the §8.3 scenario — public DistilGPT2, single GPU,
  original upstream `_fine_tune_fast_dp` method and author-pinned fastDP fork,
  16 synthetic texts, 2 optimizer updates, target epsilon 8 → 4
  (`privacy.mechanism.params.target_epsilon` MEDIUM). The capture and paired
  drift passed on 2026-09-26/27.
- **Why equivalent for this tool**: training-loop capture, real optimizer
  steps, finite loss, file/artifact hashing, redaction and semantic drift do
  not depend on model scale or gating. The gated-access *path itself* was
  separately verified with a real provisioned token in the §8.1 metadata
  scenarios (401 anonymous / 403 authenticated model-author rejection); what
  the supplement does not cover is only execution with Llama-2 weights.
- **Residual difference**: multi-GPU execution and the Llama-2 weight identity
  remain unexercised; recorded here, not hidden.

#### Effect

Gate B's M5 judge and DP entries are closed by the §8.4 and §8.3 scenarios
respectively. This does not close lm-eval/LlamaFactory/HarmBench/FastChat
answer-generation execution, any M6 pairing beyond those already recorded, or
any M7 gate. The retired originals stay described above so a future maintainer
with credentials can still execute them as *additional* coverage.

### 8.6 Real discover validation (2026-10-01)

Maintainer authorization: on 2026-10-01, complete the pending real DeepSeek
discover check; sufficient account balance is confirmed. The credential was
subsequently provisioned locally and used only in process memory for this gate.
This supplements the existing M7 gate without changing pins or earlier gold.

Project C is an initialized disposable `llm-dp-finetune` clone at the §2 pin.
Run `reprollm discover . --experimental --dry-run --max-chars 30000`, review the
actual payload, then `reprollm discover . --experimental --yes --max-chars 30000`
with `REPROLLM_LLM_BASE_URL=https://api.deepseek.com` and
`REPROLLM_LLM_MODEL=deepseek-flash`. The key is supplied only in process memory.
The production client is used unchanged; an observer records sanitized response
usage and request hashes. Allow at most three HTTP attempts, a 400-second whole
run deadline, and a 40,000-character actual user-message ceiling, including
collection headers and declared-field context. A timeout after submission
leaves charging uncertain and is not retried outside the bounded client.

Prepared input hashes:

- Generated manifest SHA-256:
  `c23306a04f2a0ebc3ca28f9e3a2cd8ce27255342d302faee15c78367755e2477`.
- Rendered collection SHA-256:
  `861765d98613dc6069d5be38c0202b4fa5f4ee315323bc90397dfb0a87995802`.
- Content budget: 30,000 characters; actual rendered collection includes
  separators/locators and is 31,210 characters (31,215 UTF-8 bytes). Check the
  final message independently against the 40,000-character execution ceiling.

Independent source expectations, reviewed before execution:

- The payload contains only public source at the pin and generated intent;
  forbidden files, dataset content, credentials and local identity are absent.
  A second redaction check returns zero. No GPU or weight download is authorized
  or required for this gate.
- `PrivacyArgs`, sent from `src/llm_pft/arguments/privacy_args.py#L7`, declares
  `target_epsilon` (line 10), `target_delta` (14), `noise_multiplier` (18),
  `eps_error` (22), and `max_grad_norm_dp` (26). At least one candidate must have
  a reproducibility-relevant parameter with independently verified sent-source
  evidence. Counts and wording are not deterministic gold.
- The nested DP8 YAML is visible only as a tree path, not sent file contents;
  a model cannot use it as verified value/line evidence. A training seed is not
  defined in the sent class snippets and is not a required discovery result.
- Parse the real candidates through the production schema/finalizer; check
  stable IDs, normalized relative evidence paths, actual source lines/snippets,
  and absence of secrets/identity. Record valid, noisy and repeated candidates.
- Accept a manually justified candidate in the disposable clone, retain its
  source/candidate ID and reviewed bindings, and audit the resulting project
  rule. Missing values must be reported; any declaration used to demonstrate
  a PASS is an explicit validation input with independently sourced value,
  never an inferred model value silently written into an author's manifest.
- Preserve sanitized model identity, finish reason, usage and attempt count.
  A successful paid response alone does not pass this gate; usable evidence
  and acceptance/audit behavior are required. Default provider thinking may
  ignore temperature zero; do not claim byte-identical LLM results.

Completion: the production CLI made one successful DeepSeek request (HTTP 200),
returned ten candidates, and the independently reviewed `max_grad_norm_dp`
candidate passed explicit acceptance, missing-to-PASS audit and duplicate
acceptance rejection. Eight artifacts passed credential/identity checks.
The real-discover resource gate passes; five other returned candidates still
require evidence or binding correction and were not accepted. See the
[complete execution and review record](docs/dogfooding/2026-10-01-discover-live.md).
These observations do not replace the source-derived expectations above or
change any repository pin or earlier gold answer.

## 9. Baseline maintenance

- Pinned commits do not move implicitly. A refresh changes this file in a dedicated reviewed commit
  with old/new SHA, reason, manually rebuilt gold, and explained deltas.
- Tool output never updates gold automatically. Snapshot regeneration is evidence only until a
  human or independent source review confirms it.
- New ReproLLM features extend the relevant milestone section before their gate becomes mandatory.
- Known implementation failures belong in the current sprint/fix report, not in gold expectations.
- Store generated reports and target artifacts outside the ReproLLM worktree.
