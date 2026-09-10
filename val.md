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

## 9. Baseline maintenance

- Pinned commits do not move implicitly. A refresh changes this file in a dedicated reviewed commit
  with old/new SHA, reason, manually rebuilt gold, and explained deltas.
- Tool output never updates gold automatically. Snapshot regeneration is evidence only until a
  human or independent source review confirms it.
- New ReproLLM features extend the relevant milestone section before their gate becomes mandatory.
- Known implementation failures belong in the current sprint/fix report, not in gold expectations.
- Store generated reports and target artifacts outside the ReproLLM worktree.
