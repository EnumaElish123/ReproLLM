# ReproLLM v0.1.0 外部仓库人工 Gold Answer

> 日期：2026-09-10
>
> 性质：独立于 ReproLLM 实际输出的人工预期
>
> 适用范围：干净、无额外文件、检出到下列固定提交的完整仓库 checkout

## 1. 方法与判定边界

本文只依据五个固定提交中的源码、README、配置、依赖清单和 Git 元数据，并按照
[`01_specification.md` §12.1–§13](../plan/01_specification.md) 的规则人工推导。取证过程中没有
运行 `reprollm audit` 或 `reprollm init`，也没有把它们的输出作为预期来源。

证据命令统一为：

```bash
git -C <repo> rev-parse HEAD
git -C <repo> status --porcelain=v1 --untracked-files=all
git -C <repo> remote get-url origin
git -C <repo> ls-tree -r --name-only HEAD
git -C <repo> show HEAD:<path>
```

标记含义：

- **精确**：固定提交加上述干净 checkout 前提下，可以逐项断言。
- **边界**：规范没有规定多候选的选择顺序，或 500 文件截断没有规定选择顺序；只能断言集合或
  不变量，不能把某一个候选硬编码为唯一 gold。
- Profile 关键词的 `medium` 要求至少两个**独立语义命中**。同一位置同时匹配等价拼写
  （例如 `red team` 与 `red-team`）只能算一次。

## 2. 核心 Gold 矩阵

### 2.1 Git、环境与扫描边界（精确）

| 仓库（commit） | Git | 依赖清单 | lockfile | Python 声明 | secret-file | 初始化状态 | Python 扫描 |
|---|---|---|---|---|---|---|---|
| lm-evaluation-harness (`b954108c9baaaa934b4ad842033b31a97ee30816`) | repo/commit/clean/no-untracked/remote 全 PASS；submodule N/A | PASS：`pyproject.toml` | FAIL | PASS：`requires-python = ">=3.10"` | PASS | 未初始化（INFO） | 816 个 `.py`，必须报告 500 上限 |
| FastChat (`587d5cfa1609a43d192cedb8441cac3c17db105d`) | 同上 | PASS：`pyproject.toml` | FAIL | PASS：`requires-python = ">=3.8"` | PASS | 未初始化（INFO） | 148 个 `.py`，不截断 |
| LlamaFactory (`673048c6a543cbbeaed5b8444b8223dc4e23c721`) | 同上 | PASS：`pyproject.toml` | FAIL | PASS：`requires-python = ">=3.11.0"` | **FAIL/CRITICAL：`.env.local` 被跟踪且未忽略** | 未初始化（INFO） | 311 个 `.py`，不截断 |
| HarmBench (`8e1604d1171fe8a48d8febecd22f600e462bdcdd`) | 同上 | PASS：`requirements.txt` | FAIL | **FAIL/WARNING** | PASS | 未初始化（INFO） | 123 个 `.py`，不截断 |
| llm-dp-finetune (`7f8b5dff4b92aae90ceccce3ec959b48307bed9e`) | 同上 | PASS：`requirements.txt` | FAIL | **FAIL/WARNING** | PASS | 未初始化（INFO） | 46 个 `.py`，不截断 |

五个仓库在固定 checkout 中均满足：HEAD 等于表中 SHA、`git status --porcelain` 为空、有
`origin`、没有 `.gitmodules`，且没有 `reprollm.yaml`/`.reprollm/`。因此
`code.submodules_initialized` 应为不适用，而不是 PASS finding。所有仓库都没有
`uv.lock`、`poetry.lock`、`Pipfile.lock` 或 `conda-lock.yml`；已有的 `requirements*.txt`
均含非 `==` 行，不能充当全量 lockfile。

LlamaFactory 的安全边界证据是 [`.env.local`](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/.env.local)：
它出现在 `git ls-files --stage` 中，而 `.gitignore` 的 `.env` 精确项不覆盖 `.env.local`。
即便该文件当前值为空，它仍命中规范 §16.4 的禁止文件模式，必须报 CRITICAL。

### 2.2 LLM-critical 依赖（精确）

下面集合表示 `env.llm_critical_deps_pinned` 应产生的**未精确 pin** package finding；每个包一条。

| 仓库 | 未精确 pin 集合 | 数量 | 主要证据 |
|---|---|---:|---|
| lm-evaluation-harness | `accelerate, anthropic, datasets, evaluate, lm_eval, numpy, openai, peft, sentencepiece, sglang, torch, transformers, vllm` | 13 | `pyproject.toml:20-35,52-114`；`lm_eval/models/{anthropic_llms,openai_completions,sglang_causallms,vllm_causallms}.py` |
| FastChat | `accelerate, anthropic, datasets, deepspeed, flash_attn, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, vllm, xformers` | 15 | `pyproject.toml:15-26`；`fastchat/{train,model,serve,llm_judge}/**/*.py` |
| LlamaFactory | `accelerate, bitsandbytes, datasets, deepspeed, numpy, openai, peft, safetensors, sentencepiece, sglang, torch, transformers, trl, vllm` | 14 | `pyproject.toml:38-76`；`src/llamafactory/**` 与 `scripts/**` 的 imports |
| HarmBench | `anthropic, numpy, openai, safetensors, vllm` | 5 | 根 `requirements.txt:3-8`；alignment-handbook `requirements.txt:1-24` |
| llm-dp-finetune | `datasets, numpy, peft, torch, transformers` | 5 | `requirements.txt:1-3`；`fine_tune.py`、`data/**/*.py`、`src/llm_pft/**/*.py` |

HarmBench 的 `accelerate, bitsandbytes, datasets, deepspeed, evaluate, peft, torch, transformers, trl`
在 `adversarial_training/alignment-handbook/requirements.txt` 中使用 `==`，因此它们不应出现在
未 pin 集合中。没有 lockfile 时，版本范围（`>=`、`<=`、`<`）和裸包名都不算 exact pin。

lm-evaluation-harness 有 816 个 Python 文件。按字典序取前 500 个时，上表 13 项精确成立；
`tokenizers` import 和五个测试中的字面 HF id 位于后 316 个文件。由于规范只规定上限而未规定
取哪 500 个文件，替代扫描顺序的**允许边界**是：必须报告截断；`tokenizers` 可以额外出现，后述
五个 tail HF id 也可以额外出现，但一次运行的选择必须确定且输出排序稳定。

### 2.3 Profile detection（精确 gold）

| 仓库 | 期望 detected profiles |
|---|---|
| lm-evaluation-harness | `evaluation=high, finetuning=high, inference=high, llm_judge=low, rag=low, agent=low` |
| FastChat | `finetuning=high, inference=high, llm_judge=medium, evaluation=low` |
| LlamaFactory | `finetuning=high, inference=high, agent=medium, evaluation=medium, rag=medium, llm_judge=low` |
| HarmBench | `finetuning=high, inference=high, safety=medium, evaluation=medium, llm_judge=low, privacy=low, agent=low` |
| llm-dp-finetune | `finetuning=high, privacy=medium, safety=low` |

未列出的 shipped profile 应缺席。`rag` 与 `agent` 可以报告，但它们仍是 report-only profile。

高置信证据：

- lm-evaluation-harness：`lm_eval` 自身 import 产生 `evaluation=high`；
  `lm_eval/models/{vllm_causallms.py,sglang_causallms.py}` 产生 `inference=high`；
  `lm_eval/models/{huggingface.py,hf_steered.py}` 的 `peft` import 产生 `finetuning=high`。
- FastChat：`fastchat/train/train.py:27` 从 Transformers import `Trainer`；
  `fastchat/serve/{vllm_worker.py,sglang_worker.py}` 分别 import vLLM/SGLang。
- LlamaFactory：`src/llamafactory/train/**/trainer.py` import `Trainer`/`Seq2SeqTrainer`；
  `src/llamafactory/chat/{vllm_engine.py,sglang_engine.py}` 提供两种 inference import。
- HarmBench：`adversarial_training/alignment-handbook/scripts/adv_training_utils.py` import
  `Trainer`/PEFT/TRL；`baselines/artprompt/artprompt.py` 等 import vLLM。
- llm-dp-finetune：`src/llm_pft/arguments/trainer_args.py:7` import `TrainingArguments`，
  `src/llm_pft/models/language_model.py:12` import `Trainer`。

关键词证据和置信度：

- FastChat 的目录 `fastchat/llm_judge/` 同时给出 `judge` 与 `llm_judge`，故为 medium；根
  README 只有 `benchmark` 类 evaluation 信号，故 evaluation 为 low。
- LlamaFactory 根 README 同时包含 `agent` 和 `function calling`，包含 MMLU/benchmark，包含
  `retrieval` 和 `RAG`；这些均至少两个独立信号。仅有论文标题中的 `judge`，故 judge 为 low。
- HarmBench 根 README 同时包含 `harmbench`、`red team`、`refusal` 等 safety 信号；evaluation
  还由 `evaluate` 依赖与 `eval` 路径支持。配置只有 `judge_*`、`epsilon`、`agent_orange_*`
  各自单类词面，因此对应 judge/privacy/agent 为 low。
- llm-dp-finetune README 中 `fast-differential-privacy` 与配置中的 `target_epsilon` 是两个独立
  privacy 信号，故 privacy 为 medium。唯一 safety 证据是 `README.md:69` 的模型缓存路径
  `...LLMPC-Red-Team...`，故 safety 只能是 low。

**已知核对哨兵：**如果 llm-dp-finetune 被判为 `safety=medium`，应首先检查 detector 是否把同一
`Red-Team` span 同时按 `red team` 与 `red-team` 计为两次。两者是规范明确要求等价的分隔符写法，
不能抬高置信度；而且该命中只是 README 中的模型 ID 路径，不是仓库具有 safety 工作流的证据。

## 3. Detection hints Gold

| 仓库 | provider hints | backend hints | `trust_remote_code` | 字面 HF ids |
|---|---|---|---|---|
| lm-evaluation-harness | `anthropic, openai` | `sglang, vllm` | `true` | 前 500 文件为空（见截断边界） |
| FastChat | `anthropic, openai` | `sglang, vllm` | `true` | 两个唯一值，见下文 |
| LlamaFactory | `openai` | `sglang, vllm` | `true` | 五个唯一值，见下文 |
| HarmBench | `anthropic, openai` | `vllm` | `true` | 空 |
| llm-dp-finetune | 空 | 空 | `true` | 空 |

provider/backend 证据分别来自 `import openai|anthropic` 与 `import vllm|sglang`；不能因 README
提及某 provider 就新增 AST hint。`trust_remote_code=true` 的代表证据包括：

- lm-evaluation-harness：`lm_eval/tasks/babilong/common_utils.py:24`；
- FastChat：`fastchat/model/model_adapter.py:758` 等；
- LlamaFactory：`scripts/llama_pro.py:51` 等；
- HarmBench：`baselines/model_utils.py:183` 等。
- llm-dp-finetune：`src/llm_pft/dataset/real_dataset.py:32`。

FastChat 字面 HF id 集合（AST 调用实参）：

- `EleutherAI/pythia-160m`（`fastchat/model/model_adapter.py:1063`、`rwkv_model.py:52`）；
- `lmsys/vicuna-7b-v1.5`（`fastchat/serve/monitor/.../compute_stats.py:96`）。

因此唯一值实际为两项。`DetectionResult.hints.hf_ids` 可以保留同一值的多个源码位置；`init`
必须保留候选值与来源的对应关系，但规范没有要求按值去重。LlamaFactory 唯一值集合：

- `Qwen/Qwen3-4B-Instruct-2507`；
- `Qwen/Qwen3-8B`；
- `Qwen/Qwen2.5-7B-Instruct`；
- `meta-llama/Meta-Llama-3-8B-Instruct`；
- `llamafactory/tiny-random-qwen3`。

lm-evaluation-harness 的字典序 tail 中存在以下允许但非前 500 gold 的 ids：
`EleutherAI/pythia-14m`、`allenai/OLMo-3-7B-Instruct`、
`hf-internal-testing/tiny-random-LlamaForCausalLM`（重复三次，输出应去重）。

## 4. `init` 可判定 Gold

规范只允许从 AST 字面量 `from_pretrained(...)`、`AutoTokenizer.from_pretrained(...)` 或
`LLM(model=...)` 提取 HF id；README 和 YAML **值**不能自动填模型。

- lm-evaluation-harness（前 500）、HarmBench、llm-dp-finetune：没有合格字面 HF id，
  `models.primary.id` 必须保持 TODO，不能猜测 README/YAML 中的模型。
- FastChat 与 LlamaFactory：存在多个合格候选，但规范未规定多候选如何选唯一 primary。
  因此 gold 只能要求所填值属于上一节的候选集合并带 `# detected: <file>:<line>`；选择集合外的值、
  静默丢失来源或把多个不同模型拼成一个值均为错误。
- `init` 的 profile 列表只包含 high/medium，不包含 low；按上一节矩阵取对应集合，并保持确定排序。

这一区分很重要：仓库“实际上主要使用哪个模型”是研究语义，当前 v0.1.0 detector 只承诺确定性
字面信号，不能由工具替用户推断。

## 5. 核对准则

将 ReproLLM 实际输出与本文比较时：

1. 先比较 Git/环境规则的 PASS/FAIL/N/A 和每包 finding 集合，不只比较 summary 数字；
2. profile 的 high 信号必须完全匹配；keyword-only 信号按独立语义命中核对；
3. lm-evaluation-harness 必须显式暴露 500 文件截断，不能把未扫描 tail 当作“仓库没有该信号”；
4. 所有 evidence 路径必须为仓库相对路径，不得持久化本文取证机器的绝对路径；
5. 对 FastChat/LlamaFactory 的多 HF id，使用允许集合，不把未规范化的遍历首项误称为唯一答案；
6. llm-dp-finetune 的 `safety=low` 是专门的重复计数回归哨兵。

## 6. ReproLLM v0.1.0 核对结果

本节在前述人工 gold 冻结后形成。验证分别在五个原始干净 checkout 上运行 Level 0 `audit`，
并在一次性临时克隆中运行 `init` 后再运行 Level 1 `audit`；另外直接读取内部
`DetectionResult.hints`，核对 CLI 当前没有展示的 detection hints。当前版本尚未实现 `lock`、
`run`、`diff`、`export` 和 `discover`，所以本轮没有把真实训练、推理或付费 API 调用冒充为
ReproLLM 功能验证。

| 仓库 | Level 0 实际结果 | Gold 核对 | `init` 核对 |
|---|---|---|---|
| lm-evaluation-harness | 0 CRITICAL / 14 WARNING；13 个未 pin 包 | Git、环境、依赖集合和 profiles 全部匹配 | profiles 匹配；primary model 保持 TODO，匹配 |
| FastChat | 0 / 16；15 个未 pin 包 | Git、环境、依赖集合、profiles 和 hints 全部匹配 | profiles 匹配；`EleutherAI/pythia-160m` 属允许集合且带来源 |
| LlamaFactory | 1 / 15；14 个未 pin 包 | `.env.local` CRITICAL、依赖集合、profiles 和 hints 全部匹配 | profiles 匹配；`Qwen/Qwen3-4B-Instruct-2507` 属允许集合且带来源 |
| HarmBench | 0 / 7；5 个未 pin 包 + lock/Python 缺口 | Git、环境、依赖集合、profiles 和 hints 全部匹配 | profiles 匹配；primary model 保持 TODO，匹配 |
| llm-dp-finetune | 0 / 7；5 个未 pin 包 + lock/Python 缺口 | 除 `safety` 外全部匹配；实际为 medium，gold 为 low | 实际把 safety 写入 profiles，偏离 gold |

五仓共有的输出契约偏差：以绝对路径调用 CLI 时，JSON 的 `target` 原样持久化绝对路径；
`generated_at` 还保留了微秒。lm-evaluation-harness 的 816→500 文件截断虽然在内部产生 warning，
但 `-v/--verbose` 没有消费 scanner/pyscan warnings，用户看不到分析不完整这一事实。

结论：当前 v0.1.0 的核心 Git/环境规则和依赖集合在五仓上与 gold 一致；profile/hints 只有一个
业务结果偏差（llm-dp safety 重复计数）。不过输出安全边界、截断可见性和 evidence 行号仍会降低
报告的可移植性与可审计性。

## 7. 项目审阅发现

以下只审已发布的 M1/M2；M3–M8 的占位模块没有被当成缺陷。

1. **P1 — Audit JSON 持久化绝对路径。** `cli/audit.py` 把用户参数原样传给
   `AuditReport.target`，违反规范“持久化路径必须为仓库相对路径”的边界，也使同一提交在不同
   checkout 位置产生不同 JSON。
2. **P1 — 未预期异常不符合退出码契约。** JSON `--output` 的父目录不存在时，当前命令泄漏
   Rich traceback 并退出 1；用户可修复的写入错误应为 exit 2，其他内部错误应为 exit 3，且仅
   `-v` 展示 traceback。
3. **P1 — 等价关键词被重复计数。** matcher 先把 `-`、`_`、空格归一化，却仍把
   `red team/red-team`、`dp-sgd/dp_sgd`、`tool call/tool_call` 分别计数。一个 span 可以被抬成
   medium；本轮已在 llm-dp-finetune 上改变 `init` 结果。
4. **P1 — `eval`/`evaluation` 目录信号未实现。** 规范明确列出这两个 evaluation 信号，
   `PROFILE_KEYWORDS` 却没有对应项；最小诊断中的单独 `eval/` 目录没有产生 detection。
5. **P1 — 工具型 `pyproject.toml` 被误认为依赖清单。** 规范要求文件包含 `[project]` 或
   `[tool.poetry]`；当前实现只检查文件存在。仅含 `[tool.ruff]` 的最小输入错误地得到
   `manifest_present=True`。
6. **P1 — 大仓扫描截断静默发生。** scanner 和 AST scanner 会记录 warnings，但全局
   `verbose` 选项没有任何消费者；lm-evaluation-harness 的 316 个未扫描 Python 文件没有在
   CLI 中提示。
7. **P2 — 时间戳精度错误。** 规范要求 UTC `Z`、秒精度；当前 JSON 输出微秒。
8. **P2 — 依赖 evidence 行号不是真实文件行号。** PEP 621 主依赖使用数组序号，optional
   dependency 使用 0；五仓输出中多次出现 `pyproject.toml:0`，不满足“指向声明行”的验收标准。
9. **P2 — 冻结仓库标识与实际链接冲突。** D-01 指定 `reprollm/reprollm`，而 package metadata、
   README 和 SECURITY 指向 `EnumaElish123/ReproLLM`；应统一链接或用新的冻结决策正式取代 D-01。
10. **P2 — redaction fixture corpus 尚未落地。** `core/redaction.py` 已有禁止文件匹配逻辑，
    但 `tests/fixtures/secrets/` 只有 README。当前分支覆盖率是 100%，仍缺 AGENTS 要求的独立
    positive/negative/env corpus；完整 value redaction 属 M5，不应提前实现。
11. **P2 — dogfooding 组合计数矛盾。** 新设计说明写“从一个扩展到六个”，但它列出的组合是
    既有 lm-evaluation-harness 加四个新仓库；调研报告的“五个”也已经包含 lm-eval。正式修改
    AGENTS.md 前必须选择一个第六仓库，或把门禁统一定义为本文实际验证的五仓组合。

质量门本身全部通过：273 tests、ruff check、ruff format、mypy strict、schema freshness；带 branch
coverage 的本机结果为 91%。这说明上述问题主要是未被现有 fixture 覆盖的契约边界，而不是已有
测试失败。
