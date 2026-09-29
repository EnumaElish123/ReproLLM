# M3 — LLM-specific Rules + Profile System

> Sprint：Week 3，2026-09-21 → 2026-09-27
> 目标版本：`0.1.1`（如有 breaking 的 manifest 变更则 `0.1.2`，仍属 0.1.x）
> GitHub Milestone：`M3`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §2.1（差异化重点——本周的规则就是这五类状态的 Level 1 版本）、§6 D-06～D-10、D-13
2. `01` §3（Manifest 全文）、§6.1（内置 Profile 表）、§8（Config）、§9–§11、§12.4–§12.11（**只做 `min_level = 1` 的行**）、§21、§22
3. `AGENTS.md` §6「How to add a rule」
4. 本文档

---

## 1. 本周目标

完成所有 **Level 1（presence）** 规则与 7 个 Profile 的最终内容，使 `reprollm audit .` 在有 manifest 的仓库上能对模型、数据、生成参数、prompt、评测、judge、训练、隐私八个维度给出完整的「缺什么」报告；实现 Profile 级 severity override 与用户级 suppression。本周结束时：

- `model.*`、`dataset.*`、`gen.*`、`prompt.*`、`eval.*`、`judge.*`、`train.*`、`privacy.*` 中全部 `min_level = 1` 的规则实现（38 条：model 6、dataset 5、gen 5、prompt 3、eval 6、judge 4、train 5、privacy 4）；
- 7 个 Profile 的 `rules`、`severity_overrides`、`drift_overrides` 完整；
- `.reprollm/config.yaml` 的 `audit.ignore`、`audit.fail_on`、`audit.show_passed` 生效；
- 三个正向 fixture 各有 `complete` 与 `gaps` 两份 manifest 及对应的 Level 1 snapshot；
- Project A、B 完成 Level 1 dogfooding。

Level 2 规则（依赖 lock 的 `*_pinned`、`*_hashed`、`*_locked`、`consistency.*`）在 M4。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从 §3 创建 Issue，挂 Milestone `M3` |
| H2 | 为 Project A、B 各手写一份 `reprollm.yaml`（用 M2 的 `init` 起步再补全）；这是本周 dogfooding 的输入，也是你亲自体验 manifest 易用性的机会。把「哪里不知道该填什么」记到 issue |
| H3 | 审阅 T06 的 Profile 内容：severity override 是否符合你领域的直觉（例如 `evaluation` 下 seed 缺失是否真该 CRITICAL） |
| H4 | 合并 T10 后打 tag `v0.1.1` |

---

## 3. 任务清单

分支前缀 `m3/`。每个规则任务的通用要求：每条规则 ≥1 PASS + ≥1 FAIL 单测（用内存构造的 `Manifest` 对象，不必落盘）；`fix_hint` 必须指明字段路径；evidence `kind: field` 必须给出 `field` 路径；多角色规则（per model / per dataset / per prompt）对每个角色分别产出 finding，message 含角色名。

### M3-T01 `model.*` Level 1 规则（M）

`model.primary_declared`、`model.provider_known`、`model.dtype_declared`、`model.quantization_declared`、`model.adapter_declared`、`model.trust_remote_code_declared`（P1）。

要点：
- `dtype_declared`/`quantization_declared` 的 `applies` 排除 API provider（`openai|openrouter|anthropic`）；若 `inference.dtype`/`inference.quantization` 已声明则视为满足（evidence 注明来自 inference 段）。
- `adapter_declared` 的 `applies` 依赖 `ctx.detection.hints.adapter`（M2 的 `peft` 导入/依赖信号）。
- `trust_remote_code_declared` 的 `applies` 依赖 `ctx.detection.hints.trust_remote_code`。

**验收标准**：`privacy_custom_params` gaps manifest 上 `trust_remote_code_declared` FAIL；complete 上 PASS；`openai_judge_eval` 上 `dtype_declared` 对 `models.primary`（openai）skipped。

---

### M3-T02 `dataset.*` Level 1 规则（S）

`dataset.declared`、`dataset.split_declared`、`dataset.subset_declared`（P1）、`dataset.preprocessing_declared`、`dataset.sampling_seed_declared`。

要点：`sampling_seed_declared` 仅当 `sampling.n` 存在；`split_declared` 仅 HF provider（local 数据集用 `files`）。

---

### M3-T03 `gen.*` 与 `prompt.*` Level 1 规则（M）

`gen.params_declared`（一条 finding，message 列出缺失字段）、`gen.seed_declared`（`applies`: `do_sample == true` 或 `temperature > 0`；temperature 为 None 时不 applies）、`gen.backend_declared`、`gen.backend_config_declared`（仅 `backend == vllm`，逐字段 finding）、`gen.stop_declared`（P1）；`prompt.declared`、`prompt.file_exists`（`text` 形式的 prompt 视为存在）、`prompt.few_shot_declared`（P1）。

**验收标准**：`hf_vllm_eval` gaps（temperature 0.0 only）上 `gen.seed_declared` skipped（温度为 0）、`gen.params_declared` FAIL 列出 `top_p, max_tokens`；complete 上全 PASS。

---

### M3-T04 `eval.*` 与 `judge.*` Level 1 规则（M）

`eval.metrics_declared`、`eval.metric_implementation_referenced`、`eval.aggregation_declared`、`eval.repetitions_declared`、`eval.definitions_declared`、`eval.query_budget_declared`；`judge.model_declared`、`judge.prompt_declared`、`judge.params_declared`、`judge.repetitions_declared`。

要点：
- `judge.*` 的 `model_ref`/`prompt_ref` 默认值 `"judge"`；`evaluation.judge` 缺失时 `judge.model_declared` 仍检查 `models.judge` 是否存在（llm_judge profile 下缺 judge 一定是 CRITICAL）。
- `eval.metric_implementation_referenced`：`implementation` 为相对路径时检查文件存在（不存在 → 同一规则 FAIL，message 区分「未声明」与「路径不存在」）。

**验收标准**：`openai_judge_eval` gaps（无 `evaluation.judge.params`）上 `judge.params_declared` CRITICAL；complete 全 PASS。

---

### M3-T05 `train.*` 与 `privacy.*` 规则（M）

`train.method_declared`、`train.hyperparameters_declared`、`train.optimizer_declared`、`train.precision_declared`、`train.lora_config_complete`；`privacy.threat_model_declared`、`privacy.mechanism_declared`、`privacy.metrics_declared`、`privacy.attack_config_declared`。

要点：`train.lora_config_complete` 在任意 model 的 `adapter` 上寻找 `rank`、`alpha`、`target_modules` 三者齐备；`privacy.mechanism_declared` 要求 `params` 非空。

**验收标准**：新增最小 finetuning manifest 单测（无 fixture 仓库）：`method: lora` 且 adapter 缺 `target_modules` → CRITICAL。`privacy_custom_params` complete 全 PASS，gaps 上 `privacy.mechanism_declared` CRITICAL（params 为空）。

---

### M3-T06 Profile 内容定稿与 severity override 机制（M）

**范围**
- 7 个 YAML 的 `rules`、`severity_overrides`、`drift_overrides`（按 `01 §6.1` 与 `§18.2`；`drift_overrides` 本周只写入文件、M6 才消费）填写完整；`core.yaml` 的 `rules` 列出 `01 §6.1` core 行的全部规则（含尚未实现的 L2 规则 ID——loader 校验 rule id 存在会失败，因此 **本周为所有 M4 才实现的 L2 规则先创建「占位类」**：`min_level = 2`、`check` 返回空、类上标记 `stub = True`，engine 对 `stub` 规则一律 `skipped`；M4 逐个替换）。
- `core/engine.py`：severity 解析顺序 `default → profile override（最派生者胜）→ project rule`；`Finding.severity_origin` 填 `default | profile:<name> | project_rule`；规则自身可在 `check` 中返回低于默认的 severity（用于 M4 `model.revision_pinned` 的 API 分支），但 override 只能提升或设定，不会被规则内部值覆盖——明确规则：**最终 severity = override 存在 ? override : 规则返回值**。
- `profiles show NAME` 输出增加 override 列。

**验收标准**：`evaluation` 下 `gen.seed_declared` 的 FAIL 严重度为 CRITICAL 且 `severity_origin == profile:evaluation`；`inference` 单独声明时为 WARNING；loader 对全部 7 个 profile 的规则 ID 校验通过（含占位）。

---

### M3-T07 Suppression、`fail_on`、config 生效（S）

**范围**：`audit.ignore[]`（按 `rule` 匹配 ID 或 alias；`reason` 空 → exit 2）；被抑制的 finding：`status: suppressed`，severity 改 INFO，原 severity 写入 `evidence[].note`（`"suppressed: original severity WARNING; reason: …"`）；`summary.suppressed` 计数；退出码只看未抑制的 fail。`audit.fail_on`、`audit.show_passed` 作为 CLI 默认值。文本输出中 suppressed 归到 INFO 组并带 `–` 符号。

**验收标准**：CliRunner 测试：抑制 `code.no_untracked` 后 `dirty_tree` 的退出码与 summary 变化；无 reason → exit 2 且消息指出规则 ID。

---

### M3-T08 Fixture manifests 与 Level 1 snapshot（L）

**范围**
- 目录约定：`tests/fixtures/repos/<name>/manifests/complete.yaml`、`manifests/gaps.yaml`；测试通过 `materialize_repo(name, manifest="complete")` 把对应文件复制为 `reprollm.yaml` 后再 commit（保证 `code.clean_tree` PASS）。Level 0 测试不传 manifest。
- `privacy_custom_params/tree/` 新增 `prompts/system.txt`（更新其 L0 snapshot 中的文件计数如有）。
- 三份 `complete.yaml` 的目标：**除 Level 2 规则外全 PASS**（`exec.run_recorded` INFO 例外）。内容要点：
  - `hf_vllm_eval`：profiles `[inference, evaluation]`；`models.primary` Qwen/Qwen3-32B bfloat16 quantization none；`datasets.eval` cais/mmlu abstract_algebra test，preprocessing description，sampling n=100 seed=0；`prompts.system`；generation 0.0/1.0/2048/seed 42；inference vllm + 四个 backend 字段；evaluation metrics accuracy→`eval.py`，aggregation mean，repetitions 1；execution command/seed/config_files；bindings：`generation.temperature`（cli+config）、`generation.max_tokens`（cli+config）、`models.primary.id`（config）。
  - `openai_judge_eval`：profiles `[evaluation, llm_judge]`；`models.primary` openai `gpt-4o-mini`；`models.judge` openai `gpt-4o-2024-08-06`；`datasets.eval` local `data` files `[data/pairs.jsonl]` preprocessing description；`prompts.judge`；generation 0.7/1.0/512/seed 1；inference openai；evaluation metrics win_rate→`judge.py`，aggregation mean，repetitions 3，judge params temperature 0.0 max_tokens 16 repetitions 1；execution；bindings `models.judge.id`（cli `--judge-model`）、`evaluation.repetitions`（cli `--n-trials`）。
  - `privacy_custom_params`：profiles `[inference, privacy, safety]`；`models.primary` meta-llama/Llama-3.1-8B-Instruct bfloat16 none `trust_remote_code: true`；`datasets.eval` 任一 HF 数据集 + split + preprocessing；`prompts.system`；generation 0.0/1.0/256/seed 7；inference transformers bfloat16；evaluation metrics asr→`attack.py`、utility→`method.py`，aggregation，repetitions 3，definitions.asr，query_budget 1000；privacy 段完整；execution；custom.privacy_method；bindings `privacy.mechanism.params.alpha`（config `configs/privacy.yaml:method.alpha`）。
- 三份 `gaps.yaml`：故意缺失以触发本周规则（见各任务验收标准），并在文件头注释列出预期触发的规则 ID。
- 生成 `expected/audit_L1_complete.json` 与 `expected/audit_L1_gaps.json`（六个文件），逐条人工核对后提交。

**验收标准**：六个 snapshot 通过；`complete` 的 summary 中 `critical == 0 && warning == 0`；`gaps` 的 summary 与文件头注释一致。

---

### M3-T09 覆盖率门槛提升与文档（S）

**范围**：CI `--cov-fail-under=85`；`docs/rules.md` 由脚本 `scripts/gen_rules_doc.py` 从 registry 生成（ID、类别、默认严重度、level、描述、fix_hint、所属 profile），CI 检查该文件新鲜度（与 `schemas/` 同一步骤）；`docs/profiles.md` 同理生成；README 增加「What it checks」一段链接到这两个文件。

---

### M3-T10 Dogfooding A/B + 发布 0.1.1（M）

**流程**：维护者用 H2 的 manifest 在 A、B 上运行 `audit`（text + json）；逐条判断每个 finding「对 / 误报 / 应更严重 / 应更宽松」；agent 修复误报、调整 profile override（需维护者确认）；记录「不知道该填什么」的字段 → 转成 `init` 模板注释改进或 docs FAQ。发布 `0.1.1`。

---

## 4. 本周禁区

- 不实现任何 `min_level = 2` 规则的真实逻辑（只允许占位类）。
- 不实现 `lock`、`run`、`diff`、`export`、`discover`。
- 不修改 Manifest schema 字段名；若 dogfooding 证明必须改，开 `spec` issue 并等维护者裁决后再动（本周允许一次 breaking 变更，版本号用 `0.1.2` 并在 CHANGELOG 写迁移说明）。
- 规则 `check` 内不得访问网络、不得导入 torch/transformers。

---

## 5. Dogfooding

见 T10。Project C（privacy）本周可选：若维护者有时间写 manifest，则一并跑；否则 M4。

---

## 6. Definition of Done（M3）

- [ ] 38 条 Level 1 规则实现且各有 PASS/FAIL 测试；`docs/rules.md` 自动生成并新鲜
- [ ] 7 个 Profile 内容定稿；`profiles show` 输出 snapshot
- [ ] suppression / fail_on / show_passed 生效并有测试
- [ ] 三个 fixture × {complete, gaps} 的 Level 1 snapshot 通过；complete 无 CRITICAL/WARNING
- [ ] 覆盖率 ≥ 85 %
- [ ] Project A、B dogfooding issue 关闭或条目有归属
- [ ] `v0.1.1` 发布

---

## 7. 发布步骤

同前，tag `v0.1.1`。Release notes 列出新增规则数量与 profile 列表，并附 `openai_judge_eval` gaps 的一段真实输出（展示 `judge.params_declared` CRITICAL——这是差异化叙事的核心例子）。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| 规则数量多导致 PR 质量下降、`fix_hint` 敷衍 | PR 模板要求粘贴每条新规则的 FAIL 输出；维护者 review 只看 message/fix_hint 文案与 severity |
| Profile override 让同一规则在不同 profile 组合下的严重度难以预测 | `profiles show` 显示最终严重度表；文档写清「最派生者胜」 |
| Manifest 在真实仓库上不够表达（例如多阶段实验、多个 eval 数据集） | 角色 map 已支持多数据集；多阶段先用多个 manifest 目录（不在 Beta 支持）；记录到 post-Beta backlog |
| 占位 L2 规则被误认为已实现 | `profiles show` 与 `docs/rules.md` 对 stub 标注 `(stub, arrives in 0.2.0)`；audit JSON 中 `status: skipped` 且 evidence note `not implemented yet` |
