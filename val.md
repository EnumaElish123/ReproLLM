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
| M5 (`run`) | lm-eval: one tiny-model/single-task inference; FastChat: one MT-Bench judge item; LlamaFactory: 1–2 step tiny LoRA/QLoRA run; HarmBench: one behavior through the minimal attack/target/classifier path; llm-dp: 1–2 step privacy fine-tune. Verify capture, hashes, relative paths, and redaction. |
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

## 9. Baseline maintenance

- Pinned commits do not move implicitly. A refresh changes this file in a dedicated reviewed commit
  with old/new SHA, reason, manually rebuilt gold, and explained deltas.
- Tool output never updates gold automatically. Snapshot regeneration is evidence only until a
  human or independent source review confirms it.
- New ReproLLM features extend the relevant milestone section before their gate becomes mandatory.
- Known implementation failures belong in the current sprint/fix report, not in gold expectations.
- Store generated reports and target artifacts outside the ReproLLM worktree.
