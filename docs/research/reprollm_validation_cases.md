# ReproLLM 功能验证案例调研

> 调研日期：2026-09-09
> 范围：5 个开源 GitHub 仓库、5 篇论文/研究工件
> 资料原则：只使用项目 plan、当前源码，以及论文原文、ACL Anthology、项目官网、官方 GitHub
> 仓库中的 README、配置和许可证等一手来源。

## 1. 结论

推荐把下面五个仓库组成 ReproLLM 的外部验证组合，而不是只选多个相似的评测或微调框架：

| 优先级 | 仓库 | 主要研究 archetype | 最有价值的验证点 |
|---|---|---|---|
| P0 | [EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness/tree/b954108c9baaaa934b4ad842033b31a97ee30816) | evaluation、inference | 大仓扫描、HF/vLLM/API 多后端、任务/提示/随机种子和 chat template 的身份 |
| P0 | [lm-sys/FastChat（限定 MT-Bench）](https://github.com/lm-sys/FastChat/tree/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge) | llm_judge、evaluation | 被评模型与 judge 双模型、judge prompt hash、闭源模型 pinnability、两阶段 run |
| P0 | [hiyouga/LlamaFactory](https://github.com/hiyouga/LlamaFactory/tree/673048c6a543cbbeaed5b8444b8223dc4e23c721) | finetuning、inference | LoRA/QLoRA、训练模板、量化、数据集和密集 YAML 超参的 lock/run/diff |
| P0 | [centerforaisafety/HarmBench](https://github.com/centerforaisafety/HarmBench/tree/8e1604d1171fe8a48d8febecd22f600e462bdcdd) | safety、evaluation | attack/target/classifier 三段流水线、拒答/ASR 定义、HF/API、SLURM/Ray |
| P0 | [jyhong836/llm-dp-finetune](https://github.com/jyhong836/llm-dp-finetune/tree/7f8b5dff4b92aae90ceccce3ec959b48307bed9e) | privacy、finetuning | `epsilon`、scrubbing/DP/undefended、DeepSpeed、未知关键参数的 discover/project rule |

这套组合覆盖 Beta 已规划的全部七个 shipped profile 中除纯 `core` 外的六类：
`inference`、`evaluation`、`llm_judge`、`finetuning`、`safety`、`privacy`；同时覆盖
Hugging Face、Transformers、vLLM、OpenAI/API 和 PEFT 等主要 integration。五个仓库承担的角色
互补，避免“仓库都很有名，但都只验证普通 benchmark”这一偏差。

建议配套采用五篇研究工件：

1. Biderman et al., [*Lessons from the Trenches on Reproducible Evaluation of Language Models*](https://arxiv.org/abs/2405.14782)；
2. Zheng et al., [*Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*](https://arxiv.org/abs/2306.05685)；
3. Zheng et al., [*LlamaFactory: Unified Efficient Fine-Tuning of 100+ Language Models*](https://aclanthology.org/2024.acl-demos.38/)；
4. Mazeika et al., [*HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal*](https://arxiv.org/abs/2402.04249)；
5. Li et al., [*LLM-PBE: Assessing Data Privacy in Large Language Models*](https://arxiv.org/abs/2408.12787)。

论文在这里是“据此设计验证场景的研究协议”，不是 `discover` 的输入。Beta 明确不实现 paper-code
一致性检查，`discover --paper` 也必须拒绝；见[冻结决策 D-26](../plan/00_architecture_and_decisions.md)
与[规范 §20.1](../plan/01_specification.md)。

## 2. 对项目的理解与筛选标准

ReproLLM 是 CLI-first、local-first 的 LLM 研究可复现性工具。它把实验状态分成三个事实层：

- `reprollm.yaml`：研究者声明的意图；
- `reprollm.lock`：模型、tokenizer、chat template、数据集、prompt 和后端版本等解析后的身份；
- `.reprollm/runs/<id>/run.json`：命令、代码、环境、硬件、绑定值和产物等运行时事实。

随后，`audit` 用确定性规则检查缺口与冲突，`diff` 对两个 `ExperimentState` 做语义差异分类，
`export` 生成可随论文 artifact 提交的 `REPRODUCIBILITY.md`；只有显式启用的 `discover`
可以调用 LLM，而且它只能提出候选，必须经人工接受后才成为确定性 project rule。该定位与五类
LLM 特有状态见[架构文档 §2–§5](../plan/00_architecture_and_decisions.md)，精确 CLI、schema、规则、
bindings、diff 与导出契约见[Beta 规范](../plan/01_specification.md)。

截至本次调研的 `v0.1.0`，真正可用的是 Level 0/1 `audit`、确定性 profile 检测和 `init`；
`lock`、`run`、`diff`、`export`、`discover` 仍是 M4–M7 的计划功能，当前 engine 也明确把
`lock=None`、`runs=[]` 留给后续里程碑。因此下文严格区分“本次已实测”和“到对应里程碑后应跑”。
当前状态也可由[项目 README](../../README.md)和[`core/engine.py`](../../src/reprollm/core/engine.py)
核对。

筛选使用以下标准：

1. 仓库必须暴露会改变实验身份、但普通 `pip freeze`/git commit 不足以说明的 LLM 状态；
2. 五个仓库合起来要覆盖所有 shipped 研究 profile 和主要 integration；
3. 要能设计小型 smoke case，也要有足够复杂度暴露扫描、锁定、运行捕获和语义 diff 的缺陷；
4. 优先选择论文作者或维护组织自己的仓库，并固定 commit；
5. 明确 API 成本、GPU、受限数据、模型单独许可、仓库体量等实际约束。

## 3. 当前 v0.1.0 的本地 smoke-test 基线

下表是 2026-09-09 在浅克隆、指定 commit 上运行当前 `v0.1.0` Level 0 audit 得到的本机结果，
不是从外部网页推断。文件数是 `git` tracked files / Python files；结果会随 ReproLLM 规则变化，
因此应作为回归基线而非仓库的永久属性。

| 仓库与固定 commit | 体量 | 当前确定性检测 | 当前最值得保留的回归信号 |
|---|---:|---|---|
| lm-eval `b954108c…` | 16,413 / 816 | evaluation、finetuning、inference = high；agent、judge、rag = low | 超过 500 个 Python 文件，命中扫描截断；多个 LLM-critical 依赖未精确 pin + 无 lockfile |
| FastChat `587d5cfa…` | 219 / 148 | finetuning、inference = high；llm_judge = medium；evaluation = low | judge 能被关键词可靠检出，同时覆盖本地模型和 API provider |
| LlamaFactory `673048c6…` | 597 / 311 | finetuning、inference = high；agent、evaluation、rag = medium；llm_judge = low | 被 git 跟踪的 `.env.local` 触发 `env.secret_files_ignored` CRITICAL，适合作为安全边界回归用例 |
| HarmBench `8e1604d1…` | 429 / 123 | finetuning、inference = high；safety、evaluation = medium；judge、privacy、agent = low | 无 CRITICAL；主要是无 lockfile、依赖未精确 pin、Python 版本未声明 |
| llm-dp-finetune `7f8b5dff…` | 66 / 46 | finetuning = high；privacy、safety = medium | 小而专一；无 CRITICAL，主要是 lockfile/依赖 pin/Python 版本缺口 |

推荐把同一命令保留为所有里程碑的第一层 gate：

```bash
uv run reprollm audit /path/to/case --format json --output /tmp/<case>-audit-L0.json
```

`init` 会写目标仓库，必须在 disposable clone/worktree 中执行：

```bash
uv run reprollm init /path/to/disposable-case
uv run reprollm audit /path/to/disposable-case --format json
```

## 4. 六项功能的组合覆盖

| 功能 | lm-eval | FastChat / MT-Bench | LlamaFactory | HarmBench | llm-dp-finetune |
|---|---|---|---|---|---|
| `audit` / `init` | 大仓与 evaluation 检测 | judge 检测 | finetuning + secret-file 边界 | safety 检测 | privacy 检测 |
| manifest / `lock` | task、HF/API model、tokenizer、chat template | candidate + judge 双模型、judge prompt | base model、dataset、adapter、template、量化 | attack/target/classifier、多模型配置 | threat model、DP/scrubbing mechanism、epsilon、数据 |
| `run` runtime capture | YAML + CLI override、四 seed、GPU/API | 回答生成与 judge 分开记录、API key 脱敏 | GPU/DeepSpeed、训练 config、checkpoint/adapter | 三阶段产物、SLURM/Ray | DP + DeepSpeed、CUDA env、训练输出 |
| `diff` semantic drift | backend/template/seed/task 变化 | judge model/prompt/mode 变化 | rank/LR/template/quantization 变化 | attack/model/classifier/ASR 变化 | epsilon/defense/duplication rate 变化 |
| `export` | 完整 benchmark recipe | judge rubric 与局限 | 微调 provenance | safety 定义与 query budget | threat model、privacy budget 与 defense |
| `discover` | cache、external task 等扩展参数 | judge mode/reference answer 等 | `lora_target`、`cutoff_len` 等 | method-specific attack knobs | `target_epsilon` binding、scrubbing/NER/custom DP 参数 |

所有 `diff` 验证都应采用“一次只改一个变量”的配对运行，并预先写出期望严重度。例如模型 revision、
chat-template hash、generation 参数和 privacy 参数应该是 `HIGH`；GPU driver 只应是 `LOW`。
期望值来自[规范 §18.2 的 drift 表](../plan/01_specification.md)。

## 5. GitHub 仓库案例

### 5.1 EleutherAI/lm-evaluation-harness：通用评测基准

**固定版本与实操信息**

- 使用 AGENTS.md 已指定的 commit
  [`b954108c9baaaa934b4ad842033b31a97ee30816`](https://github.com/EleutherAI/lm-evaluation-harness/tree/b954108c9baaaa934b4ad842033b31a97ee30816)，
  不跟随移动的 `main`；这是项目现有 standing dogfooding target。
- 代码许可证为 [MIT](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/LICENSE.md)；
  单个任务的数据集和模型权重仍需分别核对许可证/访问条件。
- 本地基线为 16,413 个 tracked files、816 个 Python files，超过 ReproLLM 的 500 文件 AST
  上限，正好验证 warning、确定性截断和真实大仓扫描。

**为什么契合**

官方 README 列出 HF、vLLM、OpenAI/Anthropic API 和 PEFT adapter，并强调公开 prompt 对比较与
复现的重要性；当前版本还支持 YAML 配置。官方[配置规范](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/docs/config_files.md)
把 `model_args`、tasks、few-shot、chat template、system instruction、generation kwargs、输出路径和
四类 seed 都暴露出来。这些字段与 ReproLLM 的 model/dataset/prompt/generation/backend/runtime
状态高度重合，而且同一任务切换 HF 与 vLLM 时可能出现输出差异；官方 README 也提供
[HF/vLLM 比较脚本说明](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/README.md#tensor--data-parallel-and-optimized-inference-with-vllm)。

**推荐验证场景**

1. 当前版本：固定 commit 后运行 L0 audit，断言三个 high profile、500 文件截断和既有未 pin
   findings 不发生无解释漂移。
2. M3/M4：用一个 case-owned `eval_config.yaml` 建 manifest；在线 lock HF model/tokenizer/task
   所用数据集，分别跑 HF 和 vLLM backend，检查 backend version、chat template 和 prompt hash。
3. M5：按官方低成本方式只跑一个小模型、一个 task、少量样本：

   ```bash
   reprollm run -- lm-eval run --config eval_config.yaml --limit 10
   ```

   优先绑定 YAML 键，而不是试图解析 `--model_args pretrained=...,dtype=...` 这种复合字符串；
   ReproLLM Beta 的 binding 只支持整 flag 或 `path:dotted.key`，不做启发式 flag 解析。
4. M6：保持模型和 task 不变，配对改变 `apply_chat_template`，再配对只改变 seed；前者预期 HIGH，
   后者也应落在 generation drift。另做 HF → vLLM 的 backend/version diff。
5. M7：export 应能让第三方看见 model revision、tokenizer/chat-template、task/prompt、few-shot、
   generation、backend 和 seed；discover 可评估 `use_cache`、`cache_requests`、`include_path`
   等尚未内建的候选是否有用。

**局限**

全任务集运行昂贵且经常变化；必须把“静态全仓 audit”和“一个小 task 的运行验证”拆开。
ReproLLM Beta 不做 dataset content fingerprint，task catalog 或上游 dataset 内容变化只能通过
revision/文件 hash 和 known limitation 暴露，不能承诺数据逐样本相同。

### 5.2 lm-sys/FastChat：MT-Bench 与 LLM-as-a-Judge

**固定版本与实操信息**

- 固定到 [`587d5cfa1609a43d192cedb8441cac3c17db105d`](https://github.com/lm-sys/FastChat/tree/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge)，
  并把验证范围限制在 `fastchat/llm_judge`，不要让 serving/UI 淹没目标。
- 仓库为 [Apache-2.0](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/LICENSE)，
  Vicuna/Llama 等权重遵循各自模型许可；本地基线 219 tracked / 148 Python files。

**为什么契合**

官方 [LLM Judge 流程](https://github.com/lm-sys/FastChat/tree/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge)
明确分成：生成候选模型回答、调用 GPT-4 生成 judgment、汇总结果；它还区分 single、
pairwise-baseline、pairwise-all，并发布版本化 judge prompts。FastChat README 同时说明本地
Transformers、vLLM 和 OpenAI-compatible API。因此它能验证 ReproLLM 是否真正理解“primary
model 与 judge model 是不同 role”，以及 API model 只能记录 `snapshot_alias`/`unpinnable`，
不能伪造 immutable revision。

**推荐验证场景**

1. 当前版本：断言 `llm_judge=medium`、`inference/finetuning=high`，并检查 `init` 是否至少选择
   shipped judge/evaluation/inference 链。
2. M3/M4：manifest 建 `models.primary`、`models.judge`、`prompts.judge` 和
   `evaluation.judge`；lock 本地/HF candidate revision 与
   [`judge_prompts.jsonl`](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge/data/judge_prompts.jsonl)
   hash，并验证 bare `gpt-4` 报 unpinnable。
3. M5：把回答生成和 judgment 作为两个 run，第二个 run 验证 `OPENAI_API_KEY` 只记
   `{present: true}`，并把两个 JSONL 输出作为 artifacts 记录。早期可使用官方预生成 answers，
   避免先承担本地大模型 GPU 成本。
4. M6：只更换 judge model、judge prompt、single/pairwise mode 或 reference answer 设置；这些
   都应表现为 HIGH drift。`--parallel` 主要改变吞吐，是否成为实验身份应由 project rule 明示，
   不应盲目判为 HIGH。
5. M7：export 必须同时展示 candidate 与 judge 身份、judge prompt hash、sampling 参数、重复次数
   和 API pinnability；discover 的目标是找 judge mode/reference-answer/category prompt 等候选。

**局限**

论文使用的历史 GPT-4 alias/快照可能不可再访问，API 调用有成本，judge 还存在 position、
verbosity 和 self-enhancement bias。ReproLLM 可以记录配置与变化，但不能证明 judge 是公平或
输出质量等价；这是记录工具而非 benchmark 正确性验证器。

### 5.3 hiyouga/LlamaFactory：配置驱动的 LoRA/QLoRA 微调

**固定版本与实操信息**

- 固定到 [`673048c6a543cbbeaed5b8444b8223dc4e23c721`](https://github.com/hiyouga/LlamaFactory/tree/673048c6a543cbbeaed5b8444b8223dc4e23c721)。
- 代码为 [Apache-2.0](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/LICENSE)，
  官方许可证段明确要求另外遵守模型权重许可；本地基线 597 / 311 files。

**为什么契合**

官方 README 列出 full/freeze/LoRA、2–8 bit QLoRA、SFT、PPO、DPO 等训练方法，并支持 vLLM/
SGLang 推理。固定 commit 的
[Qwen3 LoRA 配置](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/examples/train_lora/qwen3_lora_sft.yaml)
同时包含模型 ID、`trust_remote_code`、LoRA rank/target、多个数据集、chat template、cutoff、
output、batch/accumulation、LR/scheduler、bf16 和 checkpoint。官方还特别提醒训练与推理要使用
相同 template，这正是 ReproLLM 的 chat-template/prompt identity 与 semantic diff 用例。

**推荐验证场景**

1. 当前版本：保留 high-confidence finetuning/inference snapshot；把 tracked `.env.local`
   触发 CRITICAL 作为 `env.secret_files_ignored` 的真实外部安全回归，确认模板例外与普通
   `.env.*` 规则没有被放宽。
2. M3/M4：基于官方 YAML 建 finetuning manifest，lock base model/tokenizer/dataset、adapter config、
   template/config hashes，以及 Transformers/PEFT/vLLM 版本。
3. M5：GPU 预算允许时运行官方 LoRA 路径：

   ```bash
   reprollm run -- llamafactory-cli train examples/train_lora/qwen3_lora_sft.yaml
   ```

   把 YAML 声明为 `execution.config_files` 并为 learning rate、rank、template、dataset 建 config
   bindings；记录 adapter/checkpoint 输出，不要求完整复现 100+ 模型。
4. M6：逐次改变 `lora_rank`、`learning_rate`、`template`、`bf16` 或 quantization。训练参数、
   adapter 与 template 变化应为 HIGH；GPU 型号或 driver 变化要按规范较低级别呈现。
5. M7：export 检查 base model + adapter 两层身份是否清楚；discover 重点评价 `lora_target`、
   `cutoff_len`、`warmup_ratio`、`preprocessing_num_workers` 中哪些真会影响可比性，避免把每个
   性能参数都提升为 CRITICAL。

**局限**

完整运行需要 GPU，模型和数据经常 gated；仓库支持的模型/方法面非常宽，不适合作为单一
黄金输出。建议固定一个 YAML 和小数据 smoke。被跟踪的 `.env.local` 是预期发现，不应为了让
case 变绿而修改上游文件；ReproLLM 的原则本来就是不自动改用户文件。

### 5.4 centerforaisafety/HarmBench：安全红队与 robust refusal

**固定版本与实操信息**

- 固定到 [`8e1604d1171fe8a48d8febecd22f600e462bdcdd`](https://github.com/centerforaisafety/HarmBench/tree/8e1604d1171fe8a48d8febecd22f600e462bdcdd)。
- 代码为 [MIT](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/LICENSE)；
  模型、behavior 数据和各攻击方法的派生许可需单独核对；本地基线 429 / 123 files。

**为什么契合**

官方 README 把 evaluation pipeline 分为生成 test cases、生成 completions、评估 completions
三个阶段，并提供 local、Ray 多 GPU 与 SLURM 模式。固定 commit 的
[`models.yaml`](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/configs/model_configs/models.yaml)
显式列出 model path、dtype、chat template、GPU 数量和 open/closed-source 类型；README 说明
框架支持 Transformers-compatible LLM、多个闭源 API 和 classifier models。这让同一个 case
覆盖 safety 定义、query budget、HF/API model identity、调度器捕获和多阶段 artifact lineage。

**推荐验证场景**

1. 当前版本：断言 `safety/evaluation=medium`、`finetuning/inference=high`，并把当前无
   lockfile/未 pin/Python 版本缺口作为 baseline。
2. M3/M4：manifest 明确 target、attacker、classifier/judge 三种 model role，数据/behavior、
   ASR/refusal definition、query budget、generation params；lock 每个 HF revision、tokenizer、
   chat template、config 与 API pinnability。
3. M5：先用 README 的单一方法/模型场景，而非 `all`：

   ```bash
   reprollm run -- python scripts/run_pipeline.py \
     --methods ZeroShot --models <one-model> --step all --mode local
   ```

   再在真实集群用 `--mode slurm`，验证 `SLURM_*` allowlist、GPU/driver、三阶段 JSON artifacts
   与失败后的 run record。
4. M6：每次只改 attack method、target revision、classifier、chat template 或 ASR/refusal 定义；
   都应高亮为 HIGH。另比较 local 与 SLURM，在科学配置相同时调度方式不应掩盖真正变化。
5. M7：export 的 Known limitations 应明确 gated/unresolved model 与 dataset fingerprint 未计算；
   discover 应找 method-specific attack knobs，但接受前必须人工判断。

**局限**

论文规模是 18 种 red-teaming 方法和 33 个目标模型/防御，完整复现成本极高；部分内容具有
双重用途。CI 只做 static audit/config hash/预生成 artifact diff，GPU/API/SLURM 场景放 nightly
或人工 dogfooding，并遵循项目安全使用说明。

### 5.5 jyhong836/llm-dp-finetune：LLM-PBE 的隐私微调子案例

**固定版本与实操信息**

- 固定到 [`7f8b5dff4b92aae90ceccce3ec959b48307bed9e`](https://github.com/jyhong836/llm-dp-finetune/tree/7f8b5dff4b92aae90ceccce3ec959b48307bed9e)，
  这是 LLM-PBE 官方项目所链接的 DP/scrubbing/undefended finetuning 子仓库。
- 代码为 [MIT](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/LICENSE)；
  本地基线仅 66 / 46 files，适合每次提交运行 static gate。

**为什么契合**

官方 README 说明同一 ECHR/Enron 路径可做 undefended、PII scrubbing 和 differential privacy
三种微调，并使用 PyTorch 2、CUDA、DeepSpeed 和定制 fast-DP。其
[`echr-llama2-7b-dp8.yml`](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/configs/fine-tune/echr-llama2-7b-dp8.yml)
把 dataset mode/duplication、training args、DeepSpeed、`target_epsilon: 8`、base model、PEFT、
NER 与 anonymization 放在一个 YAML 中；
[`deepspeed_stage3.json`](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/configs/fine-tune/deepspeed_stage3.json)
还决定精度与 ZeRO stage。这是 ReproLLM privacy profile 和 project rules 最聚焦的真实案例。

**推荐验证场景**

1. 当前版本：断言 `privacy/safety=medium`、`finetuning=high`；检查 requirements 中未 pin
   的 Transformers/Torch 有明确 finding，Git URL 依赖至少以 parser warning 安全降级，不得让
   audit 崩溃。
2. M3/M4：manifest 填 threat model、mechanism `dp-sgd`、`params.epsilon=8`、privacy metrics、
   attack/query budget、model/dataset/training；lock HF model/dataset revision、config/DeepSpeed
   hashes 和 backend packages。
3. M5：完整场景按官方命令需要四 GPU：

   ```bash
   reprollm run -- deepspeed --num_gpus=4 fine_tune.py \
     --config_path=configs/fine-tune/echr-llama2-7b-dp8.yml
   ```

   CI 不跑训练，只做 config capture/binding 单测；人工 GPU run 要验证 CUDA env、DeepSpeed、
   输出目录与失败记录。
4. M6：配对比较 undefended / scrubbed / DP，或保持 DP 不变只改 epsilon、sample duplication、
   pseudonymization；privacy mechanism 与其参数应是 HIGH drift。
5. M7：让 discover 从 YAML 提出 `privacy_args.target_epsilon`、`dataset_mode`、
   `sample_duplication_rate`、NER/anonymize 等候选。人工接受后，建议绑定示意：

   ```yaml
   # 语义值仍放在 manifest privacy.mechanism.params；project rule 用于补充代码库特有约束。
   bindings:
     privacy.mechanism.params.target_epsilon:
       config: configs/fine-tune/echr-llama2-7b-dp8.yml:privacy_args.target_epsilon
   ```

**局限**

ECHR/Enron 数据、Llama 权重和 PII 标注各有访问/使用条件；scrubbing 可耗时数小时，完整 DP
示例需要多 GPU。README 的 troubleshooting 明确指出 Transformers/Pydantic/DeepSpeed/tokenizers
版本敏感，这既是理想 lock/diff 失败案例，也意味着不能把 moving environment 当稳定黄金结果。
Beta 又不计算 dataset content fingerprint，所以 export 必须显式保留这一 known limitation。

## 6. 论文/研究工件案例

### 6.1 *Lessons from the Trenches on Reproducible Evaluation of Language Models*

Biderman et al. (2024) 从 lm-eval 维护经验出发，指出模型评测对 setup 敏感、跨方法比较困难，
且复现和透明度不足；这些问题直接支持 ReproLLM 对 model/task/prompt/chat-template/generation/
backend 状态的联合记录。[论文原文](https://arxiv.org/abs/2405.14782)与
[官方 lm-eval 仓库](https://github.com/EleutherAI/lm-evaluation-harness)构成“论文论点 → 真实大仓”
的首要验证对。

推荐协议：对同一小模型/任务制作两个仅差 chat template 或 seed 的 run，确认 `diff` 不把差异
埋在通用 config dump 中；再检查 export 能否单页表达重跑所需的模型 revision、task、few-shot、
prompt、generation 和 backend。局限是它偏方法论/经验总结，不是一张要求逐数值复现的结果表；
因此应验证“实验身份是否完整”，不应声称 ReproLLM 能验证指标正确性。

### 6.2 *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*

Zheng et al. (NeurIPS 2023 Datasets and Benchmarks)研究 LLM judge，并明确讨论 position、verbosity、
self-enhancement 与推理能力偏差；论文公开 MT-Bench、专家判断和偏好对话，官方实现位于
[FastChat `llm_judge`](https://github.com/lm-sys/FastChat/tree/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/llm_judge)，
见[论文原文](https://arxiv.org/abs/2306.05685)。

推荐协议：复现 single-answer grading 的最小子集，锁 judge prompt，记录 candidate/judge 两个
model role 与 judge sampling/repetitions；再只改 judge prompt 或 model 做 HIGH diff。它验证的是
ReproLLM 的 judge provenance，不验证论文所报告的人类一致率，也不能消除 judge bias。

### 6.3 *LlamaFactory: Unified Efficient Fine-Tuning of 100+ Language Models*

Zheng et al. 的 ACL 2024 System Demonstrations 论文提出统一高效微调框架；ACL Anthology 给出
[正式论文、页码和 DOI](https://aclanthology.org/2024.acl-demos.38/)，官方代码即
[LlamaFactory](https://github.com/hiyouga/LlamaFactory)。其方法跨度和 YAML 密度足以检验 manifest
是否可表达 base model、dataset、LoRA adapter、训练超参、精度、量化和 template。

推荐协议：不复现“100+ 模型”，只固定一个 LoRA YAML 和小数据；生成 run A 后仅改 rank，run B
仅改 template，分别验证 adapter/template HIGH drift 与 export。局限是 framework 版本发展快，
论文时点与当前功能差距大，必须固定 commit；硬件吞吐不是 ReproLLM 的验证目标。

### 6.4 *HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal*

Mazeika et al. (2024)设计标准化红队评测，并在论文中比较 18 种方法与 33 个 target LLM/defense；
[论文原文](https://arxiv.org/abs/2402.04249)、[项目官网](https://www.harmbench.org/)和
[官方仓库](https://github.com/centerforaisafety/HarmBench)互相链接。

推荐协议：选一个方法、一个 target 和一个 classifier，分别记录 test-case generation、completion、
evaluation 三阶段；修改 classifier 或 refusal/ASR definition 后检查 HIGH diff，并查看 export 是否
能说明 query budget 与每个模型身份。局限是完整论文规模不适合 CI，且 ReproLLM 不判断攻击或
防御是否科学有效；它只验证运行身份和变化是否可追踪。

### 6.5 *LLM-PBE: Assessing Data Privacy in Large Language Models*

Li et al. (PVLDB 2024)把 LLM 数据隐私评估组织为覆盖生命周期、攻击、防御、数据类型和指标的
工具包；见[论文原文](https://arxiv.org/abs/2408.12787)与
[官方 LLM-PBE 工具包仓库](https://github.com/QinbinLi/LLM-PBE)。官方 DP 微调子仓库明确支持 undefended、
scrubbing 与 differential privacy 三条路径，并给出 epsilon=8 的 YAML。

推荐协议：先静态审计三种配置，再在人工 GPU 环境运行一个 DP case；`diff` 分别比较 defense
类型和 epsilon，export 必须显示 threat model、mechanism 参数、privacy metrics 与未指纹化数据集
的限制。该论文覆盖的 LLM-PBE 整体比 `llm-dp-finetune` 子仓库更宽，因此此 case 只声称验证
private finetuning/defense 子流程，不把一个子仓库等同于整篇论文的完全复现。

## 7. 建议的落地顺序与验收门

### Gate A：每次提交、无 GPU/无 API

- 五个固定 commit 运行 Level 0 audit；JSON 去除时间字段后做 snapshot。
- 验证 profile、secret file、dependency pin、Python cap 与 parser warning。
- M4 后补 `lock --offline`，验证不发网络、unresolved/declared provenance 和稳定序列化。
- 对现成 YAML/JSON 做 collector dry-run；断言 forbidden/secret 文件绝不进入 discover payload。

### Gate B：每周或里程碑、低成本

- lm-eval：小模型 × 单 task × `--limit 10`。
- FastChat：使用预生成 model answers，只运行小规模 judgment/结果展示；若调用 API，设置硬预算。
- LlamaFactory/HarmBench/LLM-PBE：主要验证 config hashing、bindings、手工构造的 run/state fixture，
  不在普通 CI 训练 4B/7B 模型。
- 每个 case 产生两份“单变量变化”的 state，验证 diff 路径和严重度。

### Gate C：发布前人工 dogfooding

- 一次 HF/vLLM GPU eval；一次 OpenAI judge；一次 LoRA 训练；一次 HarmBench local/SLURM；一次
  DP training（资源不足时可轮换，不要求每周全跑）。
- 每次检查 run 目录不含 token、绝对路径、hostname、username；特别核对 LlamaFactory `.env.*`、
  FastChat API key 和集群环境变量。
- 对每个 case 生成 `REPRODUCIBILITY.md`，由未参与配置的人在 30 秒内回答：用了什么模型/版本、
  数据/提示、关键参数、运行环境、已知不可锁定项，以及两次 run 为什么不同。

## 8. 选择取舍

- HELM 与 OpenAI Evals 都是强评测候选，但与 lm-eval/FastChat 的 evaluation/API 覆盖重叠；当前
  五席更需要为 safety 和 privacy 留位。
- OpenRLHF 与 LlamaFactory 都很适合复杂训练 runtime；LlamaFactory 的 YAML、LoRA/QLoRA、template
  和多后端组合更直接覆盖 ReproLLM schema，因此只保留后者。
- DSPy 的 RAG/agent/config 场景适合 post-Beta；但 Beta 的 `rag`/`agent` profile 明确 report-only、
  尚未 shipped，在当前五席中优先级低。M9–M12 若交付这两个 profile，应把 DSPy 加为第六个案例。
- QLoRA 原始仓库是优秀的精简 finetuning paper artifact；若 LlamaFactory 的移动面导致 snapshot
  维护成本过高，可用 [artidoro/qlora](https://github.com/artidoro/qlora) 替换，但二者无需同时进入
  主回归组。

## 9. 证据边界

- GitHub 仓库事实均链接到固定 commit；论文事实链接论文原文或官方出版页。
- 本地 profile/file-count 结果只代表 2026-09-09 的 ReproLLM `v0.1.0` 与上述 commit。
- 仓库代码许可证不自动覆盖模型权重、数据集、API 输出或论文附件。
- “适合验证某功能”是基于 ReproLLM schema/rule 与上游公开配置所作的工程判断，已与上游事实
  分开陈述。
