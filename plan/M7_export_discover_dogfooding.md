# M7 — Export + Project Rules + Experimental Discover + Full-flow Dogfooding

> Sprint：Week 7，2026-10-19 → 2026-10-25
> 目标版本：`0.5.0a1`
> GitHub Milestone：`M7`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §4（LLM discovers. Rules decide.）、§6 D-05、D-23、D-24、D-25、D-26；§9
2. `01` §7（Project rules）、§12.13、§19（Export）、§20（Discover 全文）、§16（discover 也受 redaction 约束）、§23
3. `AGENTS.md`
4. 本文档

---

## 1. 本周目标

补齐 Beta 功能面并在三个真实仓库上跑通全流程。本周结束时：

- `reprollm export` 生成 `REPRODUCIBILITY.md`；
- Project rules 全链路：`rules add/list` 手动路径、`project.*` 规则在 audit 中生效、`consistency.custom_fields` 有真实数据；
- `reprollm discover --experimental`（**3 天时间盒：10-20 周二 → 10-22 周四**）：收集 → 确认 → 调用 → 候选文件 → `rules accept/ignore`；若周四 18:00 前 T04 未达可合并状态，执行 §4 的砍法；
- A / B / C 三仓库完成 `init → audit → lock → run → audit → diff → export` 全流程，发现的问题修完或归属；
- 发布 `0.5.0a1`。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从 §3 创建 Issue，挂 `M7`；在 issue `M7 discover time box` 中写明截止时间 |
| H2 | 准备一个 OpenAI-compatible endpoint 与模型（任意；用于 T04 真实验证与 C 仓库 discover），设置 `REPROLLM_LLM_*` 三个环境变量 |
| H3 | **全流程 dogfooding（T06）**：本周最重要的人工任务，预计 4–5 小时。三个仓库各走一遍完整流程；每一步的输出与困惑都记到对应 issue；对 C 运行 `discover --dry-run` 先看文件清单，再决定是否 `--yes` |
| H4 | 周四 18:00 判定 discover 是否砍；决定写进 issue |
| H5 | 合并 T08 后打 tag `v0.5.0a1` |

---

## 3. 任务清单

分支前缀 `m7/`。

### M7-T01 `reprollm export`（M，周一）

**范围**（`export/exporter.py`, `export/templates/REPRODUCIBILITY.md.j2`, `cli/export.py`）
- 输入：`State.merge(manifest, lock, run)`；`--run RUN_ID`（默认最新）；无 run / 无 lock 的降级文案按 `01 §19`。
- 模板章节与顺序严格按 `01 §19`；表格用 GitHub-flavored Markdown；哈希显示前 12 位并在括号给全量（可被 grep）；所有路径相对；输出经 `redact_text`。
- 「Audit summary」章节：在导出时**实际运行一次 audit**（同一 root，自动 level），嵌入 summary 与 CRITICAL/WARNING 列表；「Known limitations」列出所有 `unresolved` / `unpinnable` / `not_computed` 与 `warnings[]`。
- `--output` 默认 `REPRODUCIBILITY.md`（root 下）；已存在 → 覆盖（这是生成物，允许）；结尾打印路径与一句「commit this file with your paper artifact」。
- 确定性：同输入两次导出字节一致（模板中不放时间，只放 run 的时间字段与 lock `generated_at`）。

**验收标准**：三个 fixture（complete + `expected/lock.yaml` + `expected/run.json`）导出 `expected/REPRODUCIBILITY.md` snapshot；无 run 场景 snapshot；输出不含绝对路径 / 主机名（复用 T07 泄漏断言）。

---

### M7-T02 Project rules 全链路（M，周一–周二）

**范围**（`rules/project.py`, `cli/rules.py`, `core/engine.py`）
- 加载 `.reprollm/project-rules.yaml`（schema `01 §7`；错误 → exit 2 指明条目）；为每条生成 `ProjectRule` 实例（`id`、`default_severity`、`min_level=1`、`fix_hint` 自动生成：`Set <field> in reprollm.yaml (reason: <reason>)`）并注入 registry 的**会话级**作用域（不污染内置 registry：engine 用 `RuleSet = builtin ∪ project`）。
- `check`：字段路径解析支持 `custom.*` 与 schema 路径；缺失/null → FAIL。
- `bindings` 并入 M5 的 bindings 观测（run 时读取 project-rules），`consistency.custom_fields` 因而有数据。
- CLI：`rules list [--json]`（激活规则 + 最新 discover 文件中的 pending/ignored 候选）；`rules add --field F --severity S --reason R [--cli] [--config] [--env]`（id 自动为 `project.<最后一段字段名>`，冲突时追加 `_2`；可 `--id` 指定）；`rules accept/ignore` 在 T04；写文件保序、原子。
- lock 的 `project_rules_sha256` 已在 M4；`consistency.lock_fresh` 第二分支现在可被真实触发。

**验收标准**：`privacy_custom_params` 加两条 project rules（`custom.privacy_method.alpha` CRITICAL 带 config binding；`custom.privacy_method.delta` WARNING）→ complete manifest 全 PASS；删除 manifest 中 `delta` → `project.delta` WARNING；run 后修改 `configs/privacy.yaml` 的 alpha → `consistency.custom_fields` CRITICAL；`expected/audit_L2_project_rules.json` snapshot；`rules list` 文本 snapshot。

---

### M7-T03 Discover 收集器（M，周二——时间盒第 1 天）

**范围**（`discover/collector.py`）
- 严格按 `01 §20.2`：包含/排除规则、大小上限、二进制排除、forbidden 文件排除、redaction 计数 > 0 的文件**整体丢弃**并列入 `dropped_files`、AST 片段提取（`argparse.add_argument` 调用原文、`@dataclass` 类源码、`hydra`/`omegaconf` 相关类）、仓库树（≤ 2000 条）。
- 预算：`max_chars` 按优先级装填：README → 配置文件（小到大）→ AST 片段 → 树；超出者进 `truncated_files`。
- `Payload` 数据类：`files: list[(path, text)]`, `tree: list[str]`, `dropped`, `truncated`, `total_chars`。
- `--dry-run` 输出：每个文件路径与字符数、丢弃/截断清单、总字符数；不发请求。

**验收标准**：三个 fixture 的 dry-run 输出 snapshot；`privacy_custom_params` 的 `.env` 不在清单中；人为在某 yaml 中放入伪造 `sk-…` → 该文件进入 `dropped_files`；预算截断测试。

---

### M7-T04 Discover 客户端、候选 schema、CLI 与 accept/ignore（L，周三–周四——时间盒第 2–3 天）

**范围**（`discover/client.py`, `discover/prompts/system.md`, `schemas/discover.py`, `cli/discover.py`, `cli/rules.py` 扩展）
- 门控：`--experimental` 或 `config.discover.enabled`；三个环境变量缺任一 → exit 2 并列出缺哪个；`--paper` → exit 2 固定文案。
- 确认：非 `--yes` 时打印 dry-run 清单 + `Send these N files (M chars) to <model> at <base_url>? [y/N]`；非 TTY 且无 `--yes` → exit 2。
- 请求：`POST {base_url}/chat/completions`，`temperature: 0`，`response_format: {type: json_object}`（返回 400 时去掉该字段重试一次）；system prompt 要求：只输出 JSON、schema 内嵌、每个候选必须引用输入文件中的具体行、不得建议已在 manifest 中出现的字段（把当前 manifest 的字段路径列表作为上下文一并发送）；user 内容为 payload 序列化。
- 响应：`json.loads` → pydantic 校验（`01 §20.4`）；失败重试一次（附错误）；再失败 → 保存 raw、exit 3。`id` 计算；evidence 路径不在 `input_files` → 降为 `low`；写 `.reprollm/discover/<ts>.json`；打印候选表（id、kind、name、confidence、suggested_field）与下一步提示 `reprollm rules accept <id>`。
- `rules accept ID [--severity] [--field]`：从最新 discover 文件取候选 → 追加 project rule（`source: discover`, `candidate_id`, bindings 复制）；重复 accept 同一 id → exit 2。`rules ignore ID` → `ignored_candidates`。`rules list` 显示 pending/accepted/ignored 状态。
- `schemas/discover.py` 替换 M1 占位；`schema export` 更新。
- 测试：respx mock endpoint 返回预置 JSON（`tests/fixtures/discover/privacy_response.json`，含 4 个候选：`alpha`（parameter, high）、`delta`（parameter, high）、`safe_interval`（parameter, medium）、一个 evidence 路径不存在的候选 → 降级 low）；无效 JSON → 重试 → 成功路径；两次失败 → raw 文件 + exit 3；`--yes` 与非 TTY；accept/ignore 状态机。

**验收标准**：上述测试；`privacy_custom_params` 上 mock discover → `expected/discover_candidates.json` snapshot（忽略时间与 model）→ `rules accept` 两条 → `audit` 出现 `project.alpha`/`project.delta` PASS。**周四 18:00 前 PR 未达「CI 绿 + 验收标准全部满足」→ 触发 §4 砍法。**

---

### M7-T05 文档（S，周五）

`docs/export.md`（章节含义、如何随论文 artifact 提交、局限）；`docs/discover.md`（**开头即写隐私声明**：发送什么、不发送什么、如何 dry-run、endpoint 由用户控制、候选不是判定）；`docs/project-rules.md`（手动 add 与 discover accept 两条路径、bindings 写法、与内置规则的关系）；README「Full workflow」小节：init → audit → lock → run → audit → diff → export，每步一行输出示例；README 的 discover 段落标注 Experimental。

---

### M7-T06 全流程 Dogfooding A/B/C（L，全周，人工主导 + agent 修复）

**流程**（每个仓库各一个 issue：`M7 full-flow: Project A/B/C`）
1. `reprollm init --force`（对比手写 manifest，看 init 预填是否进步）→ 用已有 manifest。
2. `audit` L1 → 修 manifest 直到无 CRITICAL。
3. `lock`（在线）→ 检查 unresolved 项是否合理。
4. `run -- <真实短任务>`（A 在 GPU 节点；B 走 OpenAI；C 在 GPU 节点）。
5. `audit` L2 → 关注 `consistency.*` 是否有误报。
6. 改一个参数再 `run` → `diff` → 判断可读性。
7. `export` → 打开 `REPRODUCIBILITY.md` 通读，标出「审稿人会看不懂的地方」。
8. 仅 C：`discover --dry-run` → 审阅清单 → `discover --experimental --yes` → 评估候选质量（多少个是真的关键参数、多少噪声）→ `rules accept` 合理者。
9. 每一步的 crash / 误报 / 文案问题 → agent 当天修复；设计层面问题 → 记入 `docs/plan/backlog.md`（本周创建）。

**验收标准**：三个 issue 中每条问题有 PR 或 backlog 归属；三个仓库各有一份可提交的 `REPRODUCIBILITY.md`（脱敏后附在 issue）。

---

### M7-T07 `docs/plan/backlog.md` 与 post-Beta 候选清单（S）

**范围**：把 M2–M7 期间被推迟的项（P1 规则、`rag`/`agent` profile、dataset fingerprint、paper-code consistency、SARIF、GitHub Action、mkdocs、启发式 flag 解析的替代方案、多阶段实验）整理为带优先级与理由的列表；M8 将据此创建 roadmap issues。

---

### M7-T08 发布 0.5.0a1（S，周五）

版本、CHANGELOG（Added: export, project rules, discover [experimental]；标注 discover 若被砍则写 "discover: deferred to 0.6"），tag。PyPI pre-release（`0.5.0a1` 为 PEP 440 预发布，`pip install reprollm` 默认不会装到它，需 `--pre`——在 README 注明）。

---

## 4. 本周禁区与「砍法」

**禁区**
- discover 之外的任何路径不得调用 LLM；discover 不得写入 `project-rules.yaml`（只有 `rules accept` 能写）。
- discover 不得发送 forbidden 文件、含密钥的文件、`data/`/`checkpoints/`/`outputs/` 下的任何内容。
- 不实现 `--paper`。
- 不新增规则类别或修改 schema 字段名。

**Discover 砍法（周四 18:00 触发）**
1. 保留 T03 收集器与 `--dry-run`（无网络，安全，可测）。
2. `reprollm discover` 在非 dry-run 路径输出 `discover (LLM-assisted) is deferred to 0.6.x; use 'reprollm rules add' to declare project-specific parameters manually.` 并 exit 2。
3. `rules add/list` 保留（T02 已完成），`rules accept/ignore` 隐藏。
4. CHANGELOG 与 README 明确写出推迟；未完成 PR 保留为 draft，转入 M9。
5. 不因砍 discover 而调整 `0.5.0a1` 的发布时间。

---

## 5. Dogfooding

T06 即本周主线。若维护者本周只能投入 4 小时，优先级：A 全流程 > C（含 discover）> B。

---

## 6. Definition of Done（M7）

- [ ] `export` 三个 fixture snapshot + 无 run 场景
- [ ] Project rules：`rules add/list`、`project.*` 生效、`consistency.custom_fields` 有真实数据、snapshot
- [ ] Discover：完整实现并通过 T04 验收，**或** 已按 §4 砍法处理且文档一致
- [ ] A/B/C 全流程 issue 中所有条目有归属；三份 `REPRODUCIBILITY.md` 存在
- [ ] `docs/export.md`、`docs/discover.md`、`docs/project-rules.md`、`docs/plan/backlog.md` 完成
- [ ] `v0.5.0a1` 发布

---

## 7. 发布步骤

同前，tag `v0.5.0a1`。GitHub Release 标记为 pre-release。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| Discover 输出质量差（候选大多是噪声） | 这正是「LLM discovers, rules decide」的理由：候选不进 audit；system prompt 要求引用行号；evidence 缺失自动降级；文档如实写明质量随模型变化 |
| 用户对「把仓库内容发给 LLM」有顾虑 | 默认关闭、dry-run 先看、`--yes` 显式、endpoint 自选、丢弃含密钥文件；文档首段写清 |
| 全流程 dogfooding 暴露大量小问题挤占时间 | 当天修 crash 与误报；文案与设计问题进 backlog；M8 有一整周修 bug |
| `export` 的审稿人可读性不足 | H3 第 7 步专门评估；M8 允许只改模板不改逻辑 |
| `0.5.0a1` 是预发布，用户 `pip install reprollm` 装到 `0.4.0` | README 注明 `--pre`；这只持续一周——M8 的 Beta 以正式版 `0.5.0` 发布（D-34），届时默认安装即 Beta |
