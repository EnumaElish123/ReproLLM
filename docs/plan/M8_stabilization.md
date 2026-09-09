# M8 — Beta Stabilization and Release (`0.5.0`)

> Sprint：Week 8，2026-10-26 → 2026-11-01；缓冲周 W8.5：11-02 → 11-08
> 目标版本：`0.5.0`（**Beta**；PyPI 正式版，GitHub Release 标题 "v0.5.0 — Beta"）
> GitHub Milestone：`M8`

---

## 0. 给 coding agent 的阅读顺序

1. `00` §6 D-34、D-36、D-37、D-42；§3 Non-goals（本周任何「顺手加个功能」都违反它）
2. `01` §22（测试要求最终核对）、§23
3. `AGENTS.md`
4. `docs/plan/backlog.md`（M7 产出）
5. 本文档

---

## 1. 本周目标

**只修不加。** 把 `0.5.0a1` 变成一个陌生研究者能在 10 分钟内装好、跑通、看懂的 Beta。本周结束时：

- M7 dogfooding 遗留的 crash / 误报全部修复；
- 文档完整：Quick Start（可对 `examples/` 直接执行）、概念、CLI 参考、规则与 profile 参考、FAQ；
- `examples/` 含三个可运行示例仓库，各自带真实 `reprollm.lock` 与 `REPRODUCIBILITY.md`；
- 大仓库性能与错误信息达标；
- 社区脚手架就位：roadmap issues、good first issues、CITATION.cff、Discussions；
- `0.5.0` 发布至 PyPI，`pip install reprollm` 默认得到 Beta。

---

## 2. 人工任务

| # | 任务 |
|---|---|
| H1 | 从 §3 创建 Issue，挂 `M8`；把 M7 三个 dogfooding issue 中未关闭条目全部转为独立 issue 并标 `M8` |
| H2 | 在有网络的机器上为 `examples/*` 生成真实 `reprollm.lock`（T03 需要）；检查 lock 内容后提交 |
| H3 | 找 1–2 位同组同学做「冷启动测试」：只给 README 链接，计时从 `pip install` 到看到第一份 `REPRODUCIBILITY.md`，记录卡点（本周最有价值的反馈来源） |
| H4 | 审阅 T06 的 roadmap issues 与 good-first-issue 文案 |
| H5 | 合并 T09 后打 tag `v0.5.0`；发布后在 `docs/adoption.md` 记录 10 月数据 |
| H6 | W8.5 缓冲周：若 M8 未按时完成，本周用于收尾；若已完成，用于 H3 反馈修复与 M9 准备，**不提前开始 M9 功能** |

---

## 3. 任务清单

分支前缀 `m8/`。

### M8-T01 Bug bash（L，全周持续）

**范围**：处理所有 `M8` 标签 issue，优先级：crash > 泄漏/安全 > CRITICAL 级误报 > WARNING 级误报 > 文案。每个修复必须带回归测试（fixture 或单测）。不接受「顺手重构」。

**验收标准**：周五前 `M8` 标签下无 open 的 crash/安全/CRITICAL 误报 issue；其余有明确归属（修复或转 M9）。

---

### M8-T02 文档（L）

**范围**（`docs/`）
- `quickstart.md`：以 `examples/hf_vllm_eval` 为对象，逐命令给出**真实输出**（由脚本 `scripts/gen_quickstart_outputs.py` 在 CI 中重新生成并 diff，保证文档不过期）：install → audit L0 → init → audit L1 → lock → run → audit L2 → diff → export。
- `concepts.md`：Intent / Resolved / Runtime truth 三层；Level 0/1/2；severity 语义；precedence；pinnability；为什么不做 score。
- `cli.md`：由 `scripts/gen_cli_doc.py` 从 typer 的 `--help` 生成，CI 检查新鲜度。
- `manifest.md`：逐字段说明（从 pydantic 模型的 `description` 生成 + 手写示例；因此本周需补全所有模型字段的 `Field(description=...)`）。
- `rules.md`、`profiles.md`（已自动生成，检查可读性）；`lockfile.md`、`run.md`、`diff.md`、`export.md`、`discover.md`、`project-rules.md`（M4–M7 已有，统一术语与链接）。
- `faq.md`：至少 12 条（例如：gated 模型怎么 lock；无网 GPU 节点怎么办；API 模型为什么是 WARNING；`.reprollm/runs` 要不要提交；如何抑制规则；如何写自定义 profile；Windows 支持范围；discover 到底发了什么）。
- `docs/index.md` 导航；可选 `mkdocs.yml`（material 主题）与 `gh-pages` workflow——仅当 T01–T05 已完成且周四前有余量。
- README 重写为最终 Beta 版：positioning statement（`00 §2`）→ 30 秒示例（audit 输出截图或代码块）→ 五类 LLM-specific state 列表（`00 §2.1`）→ Quick start 链接 → Status/Roadmap → Contributing → License。

**验收标准**：`quickstart.md` 的输出由 CI 再生成且 diff 为空；H3 冷启动测试者能不问人完成流程。

---

### M8-T03 `examples/`（M）

**范围**：`scripts/refresh_examples.py` 把 `tests/fixtures/repos/{hf_vllm_eval,openai_judge_eval,privacy_custom_params}/tree` + `manifests/complete.yaml`（重命名为 `reprollm.yaml`）复制到 `examples/<name>/`，并写 `README.md`（该示例展示什么、故意植入的问题、建议的练习命令）。维护者按 H2 生成真实 `reprollm.lock`；`REPRODUCIBILITY.md` 由 `export` 生成（无 run，降级文案）。`examples/README.md` 索引。CI 增加一步：对每个 example 运行 `reprollm audit --level 1 --fail-on never` 与 `reprollm lock --check`（后者在 CI 无网但 `--check` 只比 hash，可行），确保示例与代码同步。

**验收标准**：三个示例目录完整；CI 步骤通过；`examples/privacy_custom_params/.reprollm/project-rules.yaml` 含 M7 的两条规则作为示范。

---

### M8-T04 健壮性与体验（M）

**范围**
- 性能：`tests/perf/test_large_repo.py`（生成 20 000 个小文件 + 500 个 `.py` 的临时仓库；`audit` L0 < 10 s，`init` < 15 s；标记 `slow`，CI 每日定时跑一次而非每 PR）。热点优化仅限 `RepoScanner`/`pyscan` 的缓存与早停。
- 错误信息审计：grep 所有 `UserError(`，确认每条都包含「哪个文件/字段」与「怎么修」；补齐缺失。
- `--help` 文案统一（每个命令一句话 + 关键选项说明）；`reprollm` 无参数显示概览与「start with: reprollm audit .」。
- 边界：非 UTF-8 文件名、空仓库、只有 `reprollm.yaml` 没有代码的目录、manifest 为空文件、lock 被手工改坏——全部有明确错误而非 traceback。
- Windows：核心单测通过；`run` 在 Windows 上至少能记录并给出「GPU/SLURM capture unavailable on Windows」warning，不崩溃。

**验收标准**：上述每一项有测试或 CI 步骤；`slow` 任务在 nightly workflow 中运行。

---

### M8-T05 打包与元数据（S）

**范围**：`Development Status :: 4 - Beta`；`py.typed`；README 在 PyPI 的渲染检查（`twine check`）；wheel 内容检查（含 `profiles/*.yaml`、`drift_severity.yaml`、模板、`discover/prompts/system.md`；不含 tests）；`CITATION.cff`（软件引用，作者、版本、URL）；`CHANGELOG.md` 的 `0.5.0` 段汇总 0.1–0.5 全部用户可见变化并列出「Known limitations」（与 `00 §3` 一致）。

---

### M8-T06 社区脚手架与 roadmap（M）

**范围**
- 从 `docs/plan/backlog.md` 创建 roadmap issues（每条：动机、范围、验收、优先级），挂 Milestone `M9`–`M12`（本周创建这四个 milestone，due date 见 `M9-M12_adoption.md`）。
- 5–8 个 `good first issue`，每个自包含且 ≤ 半天：例如「为 `gen.stop_declared` 补 P1 实现」「为 `safety` profile 增加关键词 `wildjailbreak`」「新增 nvidia-smi 三卡 fixture」「为 FAQ 增加 conda 用户示例」「`doctor` 显示 `HF_ENDPOINT` 镜像配置」。
- 开启 GitHub Discussions（分类：Q&A、Show and tell、Ideas）；README 链接。
- `CONTRIBUTING.md` 终稿：开发环境、测试、如何加规则/profile（指向 AGENTS.md §6）、PR 流程、行为准则。
- `.github/ISSUE_TEMPLATE/new_rule.yml` 要求填写：规则 ID 建议、类别、默认严重度、FAIL 条件、fix_hint、所属 profile。

---

### M8-T07 安全复核（S）

**范围**：对 `examples/*` 与 A/B/C 的 run 目录再跑一次泄漏断言脚本（`scripts/check_no_leaks.py <dir>`，复用 M5 T07 的模式集）；复核 discover 排除规则；`SECURITY.md` 终稿（支持的版本、报告渠道、响应时间承诺、redaction 覆盖范围）；CI 增加 `pip-audit`（dev 依赖漏洞扫描，失败不阻断但发 warning）。

---

### M8-T08 发布物料（S）

**范围**：`docs/why.md`（问题陈述：研究者遇到的十类不可复现场景 → ReproLLM 分别用哪条规则/哪个命令回应；这是未来博文与申请文案的底稿）；`asciinema` 或 `vhs` 录制 `examples/hf_vllm_eval` 全流程（≤ 90 秒），嵌入 README（gif/svg）；准备一段 500 字符以内的项目介绍（Codex for OSS 申请表用，`00 §2.1` 叙事）。

---

### M8-T09 发布 `0.5.0`（S，周五）

版本号 `0.5.0`；CHANGELOG 定稿；tag `v0.5.0`；GitHub Release 标题 "v0.5.0 — Beta"，正文：一段定位、安装、Quick start 链接、Known limitations、Roadmap 链接、致谢。干净环境验证 `pip install reprollm`（无 `--pre`）得到 `0.5.0`，`reprollm doctor`、`reprollm audit examples/hf_vllm_eval` 正常。

---

## 4. 本周禁区

- 不新增命令、选项、规则、profile、schema 字段（修正错误行为除外，且需 issue 引用）。
- 不重构；不升级依赖大版本；不改 rule ID。
- 不引入 mkdocs 以外的任何新工具链；mkdocs 本身也是可选项。
- 不在 W8.5 缓冲周开始 M9 功能开发。

---

## 5. Dogfooding

H3 冷启动测试为本周核心反馈源。A/B/C 上重跑 `0.5.0` 候选版本的全流程一次，确认 M7 之后无回归。

---

## 6. Definition of Done（M8 / Beta）

- [ ] `M8` 标签下无 open 的 crash / 安全 / CRITICAL 误报
- [ ] `docs/` 全部页面完成；`quickstart.md`、`cli.md`、`rules.md`、`profiles.md` 由 CI 校验新鲜度
- [ ] `examples/` 三个示例含真实 lock，CI 校验通过
- [ ] 性能与边界测试通过；nightly workflow 存在
- [ ] `CITATION.cff`、`CONTRIBUTING.md`、`SECURITY.md` 终稿；Discussions 开启；roadmap issues 与 ≥5 个 good first issue 存在
- [ ] `docs/why.md` 与终端录制完成；500 字符介绍存档于 `docs/plan/application_text.md`
- [ ] 至少 1 位冷启动测试者完成全流程，卡点已修复或记录
- [ ] `v0.5.0` 发布；`pip install reprollm` 默认得到 `0.5.0`
- [ ] `docs/adoption.md` 记录 9 月、10 月数据

---

## 7. 发布步骤

1. 周四：冻结 `main`，只允许 T09 与 P0 修复合并。
2. 周五：合并 T09；tag `v0.5.0`；release workflow（含 `pytest -m security`）；批准 `pypi` environment。
3. 验证；填写 GitHub Release；更新 `docs/adoption.md`。
4. W8.5：按 H6 使用缓冲周。

---

## 8. 风险与应对

| 风险 | 应对 |
|---|---|
| Bug bash 发现需要改 schema 才能修的问题 | 评估能否用兼容方式（新增可选字段）解决；否则记入 M9 并在 Known limitations 写明；Beta 不因此延期 |
| 文档工作量被低估 | `quickstart`/`cli`/`rules`/`profiles`/`manifest` 五份由脚本生成，手写只剩 concepts/faq/why；mkdocs 可砍 |
| 冷启动测试者找不到 | 至少让一位没参与过设计的人（可以是 agent 以外的任何人）按 README 走一遍；不可替代为你自己 |
| 发布当天 CI 或 PyPI 故障 | 有 W8.5 缓冲；tag 不因外部故障改名，修复后重推同一 tag |
