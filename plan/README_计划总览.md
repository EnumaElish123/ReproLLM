# ReproLLM 开发计划总览（中文索引）

> 生成日期：2026-09-03
> 依据：`ReproLLM_项目目标背景与阶段性设计总纲_20260903.md` + 三轮设计问答（全部建议已采纳）+ 可行性与申请概率评估
> 本目录中的文档可直接交给 coding agent 使用；`00`、`01`、`AGENTS.md` 为英文（将进入公开仓库），`M*` 为中文（给你与 agent 的周计划）。

---

## 1. 文档地图

| 文件 | 用途 | 读者 | 何时读 |
|---|---|---|---|
| `00_architecture_and_decisions.md` | 产品定义、边界、核心原则、**42 条冻结决策（D-01…D-42）**、存储与仓库布局、路线图 | 所有人 / agent | 每次开工前；任何决策争议时 |
| `01_specification.md` | **规范**：CLI 契约与退出码、Manifest / Lock / Run record / Profile / Project rules / Config / Finding 的完整 schema、Audit 引擎语义、**69 条规则目录**（core 16 + Level 1 38 + Level 2 9 + consistency 6，另有动态 `project.*`）、Profile 检测信号、Integration 契约、Bindings、**Secret Redaction 规范**、ExperimentState、Diff 严重度表、Export、Discover、测试要求 | agent | 实现任何字段、命令、规则时；字段名以此为准 |
| `AGENTS.md` | agent 工作约定：阅读顺序、不可违反项、目录地图、命令、如何加规则/profile/integration、PR 流程、代码风格、完成标准 | agent | 放在仓库根目录，每次会话自动读 |
| `M1_foundation.md` | W1：仓库/CI/PyPI、全部 schema、registry+engine 骨架、首两条规则、fixture 基础设施 | 你 + agent | 2026-09-07 起 |
| `M2_audit_core_init.md` | W2：`code.*` `env.*` `exec.*`、确定性 profile 检测、profile loader、`init`、Level 0/1 | | 09-14 起 |
| `M3_llm_rules_profiles.md` | W3：38 条 Level 1 规则、7 个 profile 定稿、severity override、suppression | | 09-21 起 |
| `M4_lock.md` | W4：HF 解析、pinnability、`lock`、Level 2、9 条 L2 规则 | | 09-28 起（假期轻周） |
| `M5_run_capture.md` | W5：**Redaction（P0，首个合并）**、`run`、bindings 观测、consistency run 侧、泄漏金测试 | | 10-05 起 |
| `M6_diff.md` | W6：ExperimentState、drift 严重度表、`diff`、audit 迁移到 State | | 10-12 起 |
| `M7_export_discover_dogfooding.md` | W7：`export`、project rules、`discover`（3 天时间盒）、A/B/C 全流程 | | 10-19 起 |
| `M8_stabilization.md` | W8：只修不加、文档、examples、社区脚手架、**发布 0.5.0 Beta** | | 10-26 起；W8.5 缓冲 |
| `M9-M12_adoption.md` | Beta 后四周：GitHub Action、checklist 模板、生态集成、首次申请、指标与复盘 | | 11-09 起 |

阅读顺序（agent 每次会话）：`00` → `01` 相关章节 → `AGENTS.md` → 当周 `Mx`。每份 `Mx` 的 §0 已列出该周需要读 `01` 的哪些章节，避免全文加载。

---

## 2. 日程

| 周 | 日期（2026） | Sprint | 版本 | 关键交付 |
|---|---|---|---|---|
| W1 | 09-07 → 09-13 | M1 Foundation | 0.0.1 | 包骨架、CI、trusted publishing、全部 pydantic schema + JSON Schema、registry/engine/reporter、`doctor`、6 个 fixture、AGENTS/CONTRIBUTING/SECURITY |
| W2 | 09-14 → 09-20 | M2 Audit Core + init | 0.1.0 | 16 条 core 规则、profile 检测、loader、`init`、Level 0/1、Project A 首次 dogfooding |
| W3 | 09-21 → 09-27 | M3 LLM rules + Profiles | 0.1.1 | 38 条 L1 规则、7 profile、override/suppression、L1 snapshot、A/B dogfooding |
| W4 | 09-28 → 10-04 | M4 Lock | 0.2.0 | HF client/resolver、pinnability、`lock`、L2、A/B/C lock dogfooding |
| W5 | 10-05 → 10-11 | M5 Run + Redaction | 0.3.0 | redaction 100 % 覆盖、`run`/`runs`、bindings、consistency、泄漏金测试、GPU 节点真实 run |
| W6 | 10-12 → 10-18 | M6 Diff | 0.4.0 | State、drift 表、`diff`、四场景 snapshot、A 真实 diff |
| W7 | 10-19 → 10-25 | M7 Export + Discover + Dogfooding | 0.5.0a1 | `export`、`rules`、`discover`（可砍）、A/B/C 全流程、backlog |
| W8 | 10-26 → 11-01 | M8 Stabilization | **0.5.0（Beta）** | bug bash、文档、examples、roadmap issues、good first issues、冷启动测试 |
| W8.5 | 11-02 → 11-08 | 缓冲 | — | 收尾或 H3 反馈修复；不开新功能 |
| M9 | 11-09 → 11-15 | Action + 首次申请 | 0.5.1 | `reprollm/action`、`--format github`、**提交 Codex for OSS 申请** |
| M10 | 11-16 → 11-22 | Checklist 模板 + P1 | 0.5.2 | `export --template neurips/acl/acm`、P1 规则 |
| M11 | 11-23 → 11-29 | 生态集成 | 0.5.3 | lm-eval / lighteval / inspect-ai integration、上游文档 PR |
| M12 | 11-30 → 12-06 | 复盘 | 0.6.0 | 采用数据、retro、下一季度三件事 |
| — | 2027-02 ~ 03 | 第二次申请 | | 以 `docs/adoption.md` 数据重写文案 |

国庆假期 10-01 → 10-07 覆盖 W4 后半与 W5 前半；M4 已按轻周规划，M5 的 T01（redaction）不受影响。

---

## 3. 如何交给 coding agent

**每个 Sprint 开始**
1. 你：完成该周 `Mx` §2 的人工任务（建 issue、准备 dogfooding 仓库等）。
2. Agent 会话 1：`请阅读 docs/plan/00_architecture_and_decisions.md、docs/plan/01_specification.md 的 §<Mx §0 列出的章节>、AGENTS.md、docs/plan/Mx_*.md。然后用 gh 为 Mx §3 的每个任务创建 issue（标题 "Mx-Tnn: <title>"，正文含范围/验收/测试要求，label Mx，milestone Mx）。创建前先把命令列出来给我确认。`

**每个任务**
- Agent 会话：`请实现 issue #<n>（Mx-Tnn）。按 AGENTS.md §7 流程：先写验收标准对应的测试，再实现，跑完整质量门（pytest / ruff / mypy / schema freshness），提交到分支 mx/tnn-<slug>，开 PR，PR 描述按模板填写。不要修改 issue 范围之外的文件。`
- 第二个 agent（review）：`请 review PR #<m>：对照 docs/plan/01_specification.md 的相关章节与 issue 的验收标准，检查规范一致性、测试覆盖、是否违反 AGENTS.md §3 的任一条，并把发现以 review comment 形式提出。不要自行修改代码。`
- 你：看 PR 描述、CI、review 意见、以及（规则类 PR）粘贴的 FAIL 输出文案；合并。

**每周结束**：按 `Mx` §6 勾 DoD；§7 发布；把 dogfooding 发现写入下周 issue。

**规范争议**：agent 发现 spec 有问题时，按 AGENTS.md §7.6 开 `spec` issue 并停止该部分；你裁决后先改 `01`，再改代码。**`00` 的 D-nn 不在会话中修改**，只能由你新增条目。

---

## 4. 相对原总纲的主要调整（及理由）

| 调整 | 原总纲 | 现方案 | 理由 |
|---|---|---|---|
| Audit 分级 | 直接 audit 全部维度 | Level 0（无 manifest）/ 1（有 manifest）/ 2（有 lock/run） | 无 manifest 时无法可靠得知「用了哪个模型」；分级让零配置也有价值 |
| `init` 时间 | W4 | W2 | Level 1 需要 manifest；schema 在 W1 定死后 `init` 成本很低 |
| Manifest 结构 | 单数 `model:`/`dataset:` | 角色 map `models.primary`/`models.judge`/`datasets.eval` | safety/judge/finetuning 天然多模型多数据；发布后再改是破坏性变更 |
| Consistency 范围 | README/配置/运行时三方 | Beta 只做结构化来源（manifest/lock/run 观测） | README 散文解析不可靠；prose 一致性并入 post-Beta 的 `discover --paper` |
| 运行时参数观测 | 未定 | 只走声明式 `bindings`，不做启发式 flag 解析 | 确定性、可测；符合「Rules decide」 |
| Provenance | 每字段全 provenance | manifest 扁平；lock 仅解析字段带 provenance；run 全带 source | 可读性与 schema 体积 |
| Profile 数量 | 10 | Beta 7（core/inference/evaluation/llm_judge/finetuning/safety/privacy） | 保工期；`privacy` 因 Project C 保留 |
| 规则类别 | 8 个 audit 维度 | 13 个类别（新增 `train`、`privacy`、`consistency`、`project`） | finetuning 与 privacy profile 需要自己的规则 |
| `discover` | 待评估 | 实验性、opt-in、OpenAI-compatible、W7 三天时间盒、明确砍法 | 保护工期；仍保留「LLM discovers」的架构叙事 |
| Paper-code | 待评估 | 明确 post-Beta；`--paper` 保留接口并拒绝 | 同上 |
| Autofix | 待定 | Beta 零 autofix | 写用户文件的信任成本 |
| 版本号 | `v0.5.0-beta` | `0.5.0a1`（W7）→ **`0.5.0` 正式版即 Beta**（W8） | PEP 440 预发布不会被 `pip install` 默认安装，Beta 必须是默认安装版本 |
| 发布节奏 | W8 首发 PyPI | W1 起每周发 PyPI | 占名、真实 release 记录、尽早暴露安装问题 |
| 时间缓冲 | 无 | W8.5 缓冲周；W4 轻周 | 单人维护 + 国庆 |
| Beta 后 | 未规划 | M9–M12 采用阶段，量化指标 | 申请概率由采用数据决定，而非功能 |
| 采用指标 | 未规划 | `docs/adoption.md` 自 W1 起月更 | 申请表 500 字符里唯一有说服力的内容 |
| 依赖策略 | 未定 | 核心零重依赖：`httpx` 直连 HF API，不装 `huggingface_hub`/torch | 只想 audit 的机器不该被迫装 torch |
| 秘密处理 | P0 | P0 且规范化：分段名匹配、9 类值模式、白名单捕获、禁区文件、100 % 分支覆盖、泄漏金测试进发布流水线 | 「记录环境」是最容易泄密的功能 |

其余（CLI-first、local-first、Apache-2.0、Day 1 公开、org `reprollm`、`LLM discovers. Rules decide. Runtime verifies.`、不做 benchmark/平台/dashboard）与总纲一致。

---

## 5. 你每周的时间怎么花（约 8–10 小时）

| 时间 | 事项 |
|---|---|
| 周一 1 h | 建 issue（agent 起草你确认）、看上周 dogfooding 遗留 |
| 周二–周四 每天 1–1.5 h | 合并 PR：看 PR 描述 + CI + review agent 意见 + 规则文案；不逐行读代码（redaction、engine、schema 相关 PR 例外） |
| 周四/周五 2–3 h | dogfooding：在真实仓库上跑本周命令，记录问题 |
| 周五 0.5 h | 勾 DoD、打 tag、写 release notes（agent 起草） |
| 每月 1 日 0.5 h | 更新 `docs/adoption.md` |

如果某周只有 5 小时：优先 dogfooding 与合并，issue 创建与 release notes 全部交给 agent 起草。

---

## 6. 可行性与申请概率（摘要）

- 技术可行性高：8 周内发出 `0.5.0` 的概率约 70 %，10–11 周内约 90 %；主要风险在 W5–W6 真实仓库暴露的返工与单人节奏波动。
- 采用是真正瓶颈：Level 0 零配置价值、`export` 对齐会议 checklist、GitHub Action 三件事决定采用率，后两件在 M9–M10。
- Codex for Open Source：11 月首次申请入选概率约 1–3 %（该计划实际选择的是已有大量下游依赖的成熟项目；万星级项目亦有大量无回复案例）；2027 年 2–3 月带采用数据再申请约 10–20 %。首次申请视为零成本登记，不影响路线。

---

## 7. 交付物清单（本目录）

```text
plan/
├── README_计划总览.md                 ← 本文件
├── 00_architecture_and_decisions.md   ← 英文，进仓库 docs/plan/
├── 01_specification.md                ← 英文，进仓库 docs/plan/
├── AGENTS.md                          ← 英文，进仓库根目录
├── M1_foundation.md
├── M2_audit_core_init.md
├── M3_llm_rules_profiles.md
├── M4_lock.md
├── M5_run_capture.md
├── M6_diff.md
├── M7_export_discover_dogfooding.md
├── M8_stabilization.md
└── M9-M12_adoption.md
```

M1 的 H8 会把 `00`、`01`、`AGENTS.md` 放进仓库；`M*` 文档建议也放入 `docs/plan/`（中文，agent 可读），便于 issue 直接引用。
