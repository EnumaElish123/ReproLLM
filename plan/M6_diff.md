# M6 — ExperimentState + Semantic Diff (`reprollm diff`)

> Sprint：Week 6，2026-10-12 → 2026-10-18
> 目标版本：`0.4.0`
> GitHub Milestone：`M6`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §6 D-16、D-27、D-28；§5 架构图（State 是 audit/diff/export 的唯一输入）
2. `01` §17（ExperimentState）、§18（Diff 全文，含 18.2 表）、§6（`drift_overrides`）、§10–§11、§12.12、§23
3. `AGENTS.md`
4. 本文档

---

## 1. 本周目标

回答「**为什么两次实验可能得到不同结果**」。本周结束时：

- `ExperimentState` 统一模型与三个投影（manifest / lock / run）、`merge` 与 `flatten` 实现；
- `drift_severity.yaml` 与严重度解析（模式匹配、版本分量语义、profile 覆盖）实现；
- `reprollm diff A B` 支持 run / lock 任意组合，text 与 json 输出，`--min-severity`、`--fail-on`；
- Level 2 audit 的 `consistency.*` 改为基于 State（行为不变，snapshot 回归通过）；
- 四个 diff 场景 snapshot；
- 在 Project A 的两次真实 run 上跑出有意义的 diff。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从 §3 创建 Issue，挂 `M6` |
| H2 | 在 Project A 上制造两次真实 run 的差异（推荐：同一命令，第二次改 `--temperature` 或换一张不同型号 GPU；若可行，换一个 vLLM 版本的环境），运行 `reprollm diff <run-a> <run-b>`，把输出贴到 issue，并回答一个问题：「这份 diff 让你 30 秒内看懂为什么结果可能不同了吗？」 |
| H3 | 审阅 `drift_severity.yaml`（T02）：这是产品判断，表里每一行的严重度是否符合你的直觉 |
| H4 | 合并 T08 后打 tag `v0.4.0` |

---

## 3. 任务清单

分支前缀 `m6/`。

### M6-T01 `ExperimentState` 与投影（L）

**范围**（`schemas/state.py`, `diff/state.py`）
- `Leaf`（`01 §17`）+ `alternatives: list[Leaf]`。
- `State` 树：`code`, `environment`, `hardware`, `models{role}`, `datasets{role}`, `prompts{role}`, `files{path}`, `generation`, `inference`, `training`, `evaluation`, `privacy`, `execution`, `custom`, `command`, `run_id`, `started_at`, `ended_at`, `duration_seconds`。
- `State.from_manifest(m)`：所有声明值 `source: manifest, confidence: declared`。
- `State.from_lock(l)`：Provenance 字段 → `value/confidence` 直接映射，`detail = source`；passthrough 字段 `source: lock, confidence: declared`；`environment.*` 来自 lock 的期望环境。
- `State.from_run(r)`：`code/environment/hardware/command/run_id/时间` 为 `source: run, confidence: observed`；`bindings_observed` 中每个观测 → 对应字段路径的 Leaf（`detail: "cli:--temperature"` 等）；`files.<path>.sha256` 来自 `files[]`；嵌入的 manifest/lock 快照通过 `from_manifest`/`from_lock` 再并入（保证单个 run 就能自洽地投影出完整 State）。
- `State.merge(manifest, lock, run)`：按 `01 §17` precedence 选主值，其余进 `alternatives`；缺哪个文档就跳过。
- `State.flatten() -> dict[str, Leaf]`：路径格式 `models.primary.revision`、`environment.packages.torch`、`files.configs/eval.yaml.sha256`（路径段含 `/` 与 `.` 时整体作为一个 key 段，用 `files.<path>.sha256` 形式；解析时以 `files.` 前缀 + 末尾 `.sha256` 切分）。
- 确定性：字典键排序输出。

**验收标准**：三个 fixture 的 complete manifest + `expected/lock.yaml` + `expected/run.json` 分别投影并 `flatten`，输出 snapshot（`expected/state_flat.json`）；`merge` 的 precedence 用例（cli 观测覆盖 config 覆盖 manifest；`alternatives` 保留全部）；单 run 自洽投影测试。

---

### M6-T02 Drift 严重度表与解析器（M）

**范围**（`diff/drift_severity.yaml`, `diff/severity.py`）
- YAML 内容严格按 `01 §18.2`；随包安装（`importlib.resources`）。
- `SeverityResolver(table, profile_overrides)`：`profile.drift_overrides` 条目前置；模式匹配：`*` 匹配单段，`files.*.sha256` 中 `*` 匹配含 `/` 的整个路径段；首个匹配胜出；无匹配 → `default`。
- 版本分量语义：路径以 `environment.packages.` 开头或等于 `inference.version` 时，用 `packaging.version.Version` 比较；解析失败按普通字符串；`major/minor` 不同 → 表值；仅 `patch`（及更细）不同 → 降一级（`HIGH→MEDIUM_HIGH→MEDIUM→LOW`，`LOW` 不再降）。
- `code.commit` 变化 → MEDIUM，但任一侧 `code.dirty == true` → HIGH（note `"working tree was dirty on <a|b|both>"`）。
- `added/removed` 状态的严重度与 `changed` 相同（一侧缺失同样破坏可比性），但 `run_id`/时间等 NONE 项例外。

**验收标准**：表中每一行至少一个匹配测试；`torch 2.8.0 → 2.8.1` LOW、`2.8.0 → 2.9.0` MEDIUM_HIGH；`vllm 0.10.0 → 0.11.0` MEDIUM_HIGH（`0.x` 的 minor 视为 minor）；profile override 前置生效；未匹配路径 → MEDIUM；dirty 逻辑。

---

### M6-T03 Differ（M）

**范围**（`diff/differ.py`）
- `diff_states(a: State, b: State, resolver) -> DiffReport`：flatten 两侧；union 路径；`same/changed/added/removed`；值比较用 M5 的 `values_equal`（normalization）；严重度；`summary.highest`（忽略 NONE）、`counts`、`same`。
- `changes` 排序：严重度降序 → 顶层 section 顺序（models, datasets, prompts, files, generation, inference, training, evaluation, privacy, custom, code, environment, hardware, command, execution, 其它）→ 路径字典序。
- 对 `alternatives` 的处理：diff 只比较主值；若某路径在任一侧存在 `alternatives` 且它们之间不一致，`note` 追加 `"a has inconsistent sources (see audit)"`。

**验收标准**：单测构造小 State 对；四类状态；排序确定性；`summary` 计算。

---

### M6-T04 CLI `diff` 与报告（M）

**范围**（`cli/diff.py`, `reporters/diff_text.py`, `schemas/diff.py`）
- 参数解析：`A`/`B` 各自可以是 run_id（含唯一前缀）、`run.json` 路径、`reprollm.lock` 路径、或 run 目录；`lock` 投影时附带同目录的 `reprollm.yaml`（若存在）以补全声明字段；两侧类型记录在 `a.kind/b.kind`。
- `--format json`：`01 §18.3`；`--min-severity` 过滤 `changes`（summary 仍按全量计算并在 JSON 中注明 `filtered_below`）；`--fail-on SEV` → 存在 ≥ SEV 的变化时 exit 1。
- 文本：按 section 分组；每行 `<path>  <a> → <b>  [SEVERITY]`；长哈希缩短为前 12 位（JSON 不缩短）；末行 verdict：存在 HIGH → `Highest drift: HIGH (n changes). These runs are not directly comparable.`；最高为 MEDIUM_HIGH/MEDIUM → `… Results may differ; review the changes above.`；仅 LOW/NONE → `No reproducibility-relevant drift detected.`。
- `schemas/diff.py` 替换 M1 占位；`schema export` 更新 `diff_report.schema.json`。

**验收标准**：CliRunner：run vs run、lock vs lock、run vs lock；前缀歧义 → exit 2 列出候选；`--fail-on HIGH` 退出码；JSON 通过 schema 校验；文本 snapshot。

---

### M6-T05 Level 2 audit 迁移到 State（M）

**范围**：`AuditContext.state`（Level 2 时 `State.merge(manifest, lock, latest_run)`）；`consistency.generation_params`、`consistency.model_identity`、`consistency.custom_fields`、`consistency.env_vs_lock`、`consistency.file_hashes` 改为读取 `state.flatten()` 中含 `alternatives` 的 Leaf（主值 vs 每个 alternative 不一致即 finding），删除对 `bindings_observed` 的直接遍历；finding 的 evidence 从 Leaf 的 `source/detail` 生成。

**验收标准**：M4/M5 的全部 `audit_L2*.json` snapshot **不变**（这是迁移的回归门）；新增一个「三来源不一致」用例（manifest 0.0 / config 0.7 / cli 1.0）evidence 三行。

---

### M6-T06 Diff 场景 fixture（M）

**范围**（`tests/fixtures/repos/hf_vllm_eval/expected/diff_*.json` 等）
- 场景 A（run vs run，HIGH）：M5 的 `expected/run.json` 为 a；b 由测试生成——同一 fixture，`prompts/system.txt` 追加一行后重新 lock（`hf_mock`）并 `run -- python -c pass --config configs/eval.yaml --temperature 0.7`；期望：`prompts.system.sha256` HIGH、`files.prompts/system.txt.sha256` HIGH、`generation.temperature` HIGH（主值 cli 1.0 → 0.7）、`code.commit` MEDIUM（或 HIGH 若 dirty）；verdict 为 not comparable。
- 场景 B（lock vs lock，HIGH）：`expected/lock.yaml` vs 手工修改 `models.primary.revision.value` 的副本 → 单条 HIGH。
- 场景 C（identical）：同一 run 与自身 → `highest: NONE`，changes 仅时间/run_id NONE 项。
- 场景 D（run vs run，LOW）：手工构造两份 run.json，仅 `environment.packages.torch` `2.8.0` → `2.8.1` → LOW；verdict "No reproducibility-relevant drift detected."（LOW 归为不影响可比性——在 `docs/diff.md` 中写明这一判断）。
- 各场景 `--format json` 与 `--no-color` 文本 snapshot。

---

### M6-T07 文档、README、Dogfooding（S + 人工）

**范围**：`docs/diff.md`（严重度表解释、版本分量规则、verdict 语义、如何用 `drift_overrides` 调整、为什么 LOW 不阻断）；README 加 `reprollm diff` 示例（用场景 A 的文本输出）；H2 的真实 diff 结果回收：若维护者认为某项严重度不合直觉 → 改表（记入 CHANGELOG）。

---

### M6-T08 发布 0.4.0（S）

CHANGELOG（含 drift table 版本 1）、版本、tag。Release notes 用 Project A 的真实 diff（脱敏）。

---

## 4. 本周禁区

- 不做普通 JSON diff 输出（所有变化必须经过严重度表）。
- 不在 diff 中比较 `alternatives`（那是 audit 的职责）。
- 不实现 `export`、`discover`、`rules`。
- 不修改 lock / run record schema；若 State 投影需要额外字段，用现有字段推导或开 `spec` issue。

---

## 5. Dogfooding

H2 为核心。附加：在 B 上把 `models.judge.id` 从 `gpt-4o-2024-08-06` 改为 `gpt-4o` 后重新 lock，对两份 lock 做 diff，确认 `models.judge.pinnability` MEDIUM 与 `models.judge.id` HIGH 同时出现。

---

## 6. Definition of Done（M6）

- [ ] State 三投影 + merge + flatten 实现，`state_flat.json` snapshot 通过
- [ ] `drift_severity.yaml` 每行有测试；版本分量与 dirty 逻辑测试
- [ ] `diff` CLI 三种组合可用，JSON 通过 schema
- [ ] Level 2 audit 迁移到 State，旧 snapshot 全部不变
- [ ] 四个 diff 场景 snapshot
- [ ] Project A 真实 diff 完成，H2 的问题得到肯定回答或形成改进 issue
- [ ] `docs/diff.md` 完成
- [ ] `v0.4.0` 发布

---

## 7. 发布步骤

同前，tag `v0.4.0`。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| State 投影把三种文档的差异「抹平」导致信息丢失 | `alternatives` 保留全部来源；flatten 输出 snapshot 让丢失可见 |
| 严重度表争议（例如 GPU 型号变化到底多严重） | 表是 YAML，可由 profile 覆盖；文档明确「表是默认判断，不是真理」；H3 人工审阅 |
| 路径中含 `/`、`.` 的文件键破坏 flatten/模式匹配 | 明确 `files.<path>.sha256` 的切分规则并测试含 `.` 的路径（`configs/eval.v2.yaml`） |
| Level 2 迁移改变现有 finding 文案 | 以旧 snapshot 为回归门；文案变化必须在 PR 中逐条说明 |
