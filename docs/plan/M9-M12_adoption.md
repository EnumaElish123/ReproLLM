# M9–M12 — Adoption Phase (post-Beta)

> 时间：2026-11-09 → 2026-12-06（四周；W8.5 缓冲周 11-02 → 11-08 之后）
> 目标版本：`0.5.x` 补丁随修随发；`0.6.0` 于 M12 末发布
> GitHub Milestones：`M9`、`M10`、`M11`、`M12`
>
> 定位：**这四周决定申请 Codex for Open Source 的实际概率，而不是 Beta 的功能完成度。** 功能开发只做「降低采用摩擦」的项。

---

## 0. 给 coding agent 的阅读顺序

1. `00` §2.1（叙事重点）、§6 D-37、D-38；§3（仍然有效的非目标）
2. `01` §19（Export 模板机制）、§13（检测信号——集成工作会扩充它）、§12 中标 P1 的规则
3. `docs/plan/backlog.md`
4. `AGENTS.md`
5. 本文档

---

## 1. 阶段目标与量化指标

到 2026-12-06 的目标值（记录于 `docs/adoption.md`，按周更新）：

| 指标 | 目标 | 说明 |
|---|---|---|
| PyPI 月下载（pypistats，去除镜像） | ≥ 300 | 真实安装信号 |
| 使用 ReproLLM 的外部仓库（提交了 `reprollm.yaml`） | ≥ 3（其中 ≥ 1 个非本实验室） | 最有说服力的指标 |
| 外部 issue / PR（非维护者、非 agent） | ≥ 5 issue，≥ 1 PR | 证明有人在用 |
| 论文 artifact 使用（`REPRODUCIBILITY.md` 出现在论文仓库） | ≥ 1 | 你自己的论文算 |
| 上游生态项目的文档/示例 PR 被合并 | ≥ 1 | lm-evaluation-harness / lighteval / inspect-ai 任一 |
| GitHub Action 被外部仓库使用 | ≥ 1 | Action 的 "used by" |
| Stars | 不设目标 | 记录但不追逐 |

第一次 Codex for OSS 申请在 **M9 提交**（11 月中旬）；无回复视为未入选；第二次申请预计 **2027 年 2–3 月**，届时以上表的实际数据为依据。

---

## 2. 人工任务（贯穿四周）

| # | 任务 | 时间 |
|---|---|---|
| H1 | 提交 Codex for OSS 申请（§7 文案） | M9 周二前 |
| H2 | 对外发布：实验室内部邮件/群、个人学术社交账号、相关 Slack/Discord/微信群各一条；语气克制、附 90 秒录制与 Quick start；不做重复推送 | M9 |
| H3 | 定向邀请 3–5 位同领域研究者试用（各自一个真实仓库），提供 30 分钟结对；收集反馈到 issue | M9–M10 |
| H4 | 在自己实验室推动 2–3 个进行中的项目提交 `reprollm.yaml` + `reprollm.lock`；下一篇论文的 artifact 仓库包含 `REPRODUCIBILITY.md` | M10–M12 |
| H5 | 每周一：triage 全部新 issue（48 小时内首次回复是硬指标）；每周五：若 `main` 有用户可见变化则发 `0.5.x` | 每周 |
| H6 | 每月 1 日更新 `docs/adoption.md` | 12-01 |
| H7 | M12 末：复盘会（自己或与合作者），决定下一季度方向；记录到 `docs/plan/retro_2026Q4.md` | 12-06 |

---

## 3. M9（11-09 → 11-15）：GitHub Action + 首次申请 + 发布

### M9-T01 `reprollm/action`（L）

- 新仓库 `reprollm/action`（composite action）：输入 `path`（默认 `.`）、`fail-on`（默认 `critical`）、`level`、`version`（默认 latest）、`check-lock`（默认 true）。步骤：`pip install reprollm==<version>` → `reprollm audit --format json --output reprollm-audit.json --fail-on <fail-on>` → 把 findings 写入 `$GITHUB_STEP_SUMMARY`（按严重度分组的 Markdown 表）并用 `::warning file=…::` / `::error …::` 注解到有 `path` evidence 的 finding → 可选 `reprollm lock --check` → 上传 `reprollm-audit.json` artifact。
- 在 `EnumaElish123/ReproLLM` 自身与 `examples/*` 上使用它（自举；身份见 D-43）。
- README：三行 YAML 用法 + 截图。Marketplace 发布。

### M9-T02 `--format github` 输出（S，主仓库）

`audit --format github` 直接输出 workflow commands（供不用 Action 的人在任意 CI 中使用）。

### M9-T03 Discover 收尾（若 M7 砍掉）（M）

按 M7-T04 验收完成；否则本项改为处理 discover 的 dogfooding 反馈。

### M9-T04 首次申请（人工，H1）

见 §7。

### M9-T05 发布 `0.5.1`（S）

Action 相关输出格式 + Beta 首周修复。

---

## 4. M10（11-16 → 11-22）：Artifact checklist 对齐 + P1 规则

### M10-T01 会议 checklist 模板（L）

- 调研并固化三份公开 checklist 的可复现性相关条目（NeurIPS Paper Checklist 的 experiments/reproducibility 部分、ACL Responsible NLP Research Checklist 的 B/C 节、ACM Artifact Review and Badging 的 "Artifacts Available / Evaluated" 要求）；在 `docs/checklists.md` 中给出**条目 → ReproLLM 字段/规则**的映射表（注明检索日期与版本，因为 checklist 会变）。
- `export --template neurips|acl|acm`：在默认模板基础上增加一节「Checklist mapping」，每条 checklist 条目给出：ReproLLM 提供的证据（字段值 / 哈希 / run id）或 `not covered by ReproLLM`；不替用户回答 Yes/No。
- 三个 example 生成三种模板的 `REPRODUCIBILITY.<venue>.md` 作为示范。

### M10-T02 P1 规则实现（M）

`code.remote_recorded`、`model.trust_remote_code_declared`、`dataset.subset_declared`、`gen.stop_declared`、`prompt.few_shot_declared`（若尚未实现）；均含测试与 docs 再生成。作为 good first issue 保留其中 2 条给外部贡献者，若 M10 末仍无人认领则由 agent 完成。

### M10-T03 试用反馈修复（M，持续）

H3 反馈的 crash / 误报当周修复。

### M10-T04 发布 `0.5.2`（S）

---

## 5. M11（11-23 → 11-29）：生态集成

### M11-T01 评测框架 Integration 与 Profile 增强（L）

- `integrations/lm_eval.py`、`lighteval.py`、`inspect_ai.py`：`detect()`（导入、CLI 入口 `lm_eval`/`lighteval`/`inspect eval`、任务 YAML 结构）→ `evaluation` high；`capture()` 版本；对各框架的**任务配置文件**（如 lm-eval 的 task YAML、inspect 的 `@task` 装饰器）在检测 `hints` 中提取任务名，供 `init` 预填 `evaluation.metrics[].name`。
- `docs/integrations/<framework>.md`：各框架的 manifest 写法示例（models/datasets/generation/bindings 如何对应到框架 CLI flag），并附 `reprollm run -- lm_eval …` 的真实 run 片段。

### M11-T02 上游文档 PR（M，人工主导 + agent 起草）

向 lm-evaluation-harness / lighteval / inspect-ai 之一提交「Reproducibility recipe with ReproLLM」文档或 examples PR（先在其 Discussions/issue 询问是否欢迎，得到肯定再提）。目标：至少一个被合并。

### M11-T03 Hugging Face 侧的可见性（S）

在 `docs/` 提供模型卡 / 数据集卡片段模板（"Reproducibility: this repository ships `reprollm.lock`; run `reprollm audit`"）；不提交任何 HF 官方仓库 PR（没有明确接口）。

### M11-T04 发布 `0.5.3`（S）

---

## 6. M12（11-30 → 12-06）：复盘、`0.6.0`、下一季度

### M12-T01 `0.6.0`（M）

汇总 M9–M11 的用户可见变化（Action、`--format github`、checklist 模板、P1 规则、评测框架集成、discover 状态）；CHANGELOG；Release notes 强调「谁在用」（列出已知使用仓库，须获对方同意）。

### M12-T02 采用数据与复盘（人工，H6/H7）

更新 `docs/adoption.md`；对照 §1 目标；写 `docs/plan/retro_2026Q4.md`：什么有效、什么无效、下一季度三件事。

### M12-T03 下一季度候选方向（讨论稿）

按用户反馈从 backlog 中挑选，候选包括：`rag`/`agent` profile；dataset content fingerprint（采样式）；`discover --paper`；多阶段实验（pipeline manifest）；SARIF 输出；Anthropic/Gemini/Ollama provider。**不在本阶段实现任何一项。**

---

## 7. Codex for Open Source 申请文案（M9 提交；第二次申请前重写）

申请表要点（以 `openai.com/form/codex-for-oss` 当时版本为准）：GitHub 用户名、仓库 URL、角色（primary maintainer）、为何符合（≤ 500 字符）、API credits 用途（≤ 500 字符）、OpenAI Org ID。

**「为何符合」草稿（英文，≤ 500 字符，提交前按实际数字更新）**

> ReproLLM is an Apache-2.0 CLI that makes LLM research experiments reproducible: a deterministic audit, a manifest/lockfile pinning model revisions, tokenizer and chat-template hashes, prompt hashes and judge configs, runtime capture with secret redaction, and semantic drift diffs. 8 releases in 2 months, N PyPI downloads, used by K research repos incl. M external. Maintenance is real and recurring: HF/vLLM/OpenAI API changes, new profiles, issue triage, releases.

**「API credits 用途」草稿**

> Bounded maintainer workflows: (1) PR review and issue triage automation for rule/profile contributions; (2) keeping Hugging Face, vLLM and OpenAI integrations current as upstream APIs change; (3) validating the opt-in `discover` feature (LLM proposes candidate reproducibility parameters, deterministic rules decide) across public research repos, with results published as fixtures.

提交后：不追问、不重复提交；无回复即视为未入选；下一次按 §1 数据在 2027 年 2–3 月重写后提交。

---

## 8. 本阶段禁区

- 不为「看起来活跃」而制造 commit / issue / release；每个 release 必须有用户可见变化。
- 不做 dashboard、hosted service、benchmark。
- 不改 rule ID；schema 变更只允许向后兼容的新增字段。
- 对外发布内容不夸大：不说 "guarantees reproducibility"，说 "records and audits reproducibility-critical state"。
- 上游 PR 未获对方肯定前不提交。

---

## 9. Definition of Done（M12 末）

- [ ] `reprollm/action` 发布并被 ≥ 1 个外部仓库使用
- [ ] `export --template neurips|acl|acm` 可用，`docs/checklists.md` 存在
- [ ] 全部 P1 规则实现
- [ ] ≥ 1 个评测框架 integration 合并；≥ 1 个上游文档 PR 被合并或明确排期
- [ ] 首次申请已提交；文案存档于 `docs/plan/application_text.md`
- [ ] `docs/adoption.md` 有 9、10、11 月数据与 12 月初快照
- [ ] `0.6.0` 发布
- [ ] `docs/plan/retro_2026Q4.md` 完成，含下一季度三件事

---

## 10. 风险与应对

| 风险 | 应对 |
|---|---|
| 邀请的研究者不试用 | 结对 30 分钟比发链接有效；准备好对方仓库的 `init` 结果再去找人 |
| 上游项目对文档 PR 不感兴趣 | 先问再提；被拒则把 recipe 放在自己的 `docs/integrations/`，不强推 |
| 采用数据远低于目标 | 这是信息而非失败：复盘时区分「没人知道」与「知道了不想用」，前者加曝光，后者回到产品（Level 0 的价值是否足够） |
| 申请无回复带来的挫败感影响节奏 | 已在预期内（概率评估 1–3 %）；H1 之后不再讨论申请，直到 2027 年 2 月 |
