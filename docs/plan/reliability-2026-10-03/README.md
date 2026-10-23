# ReproLLM 可靠性开发执行方案 v1.2

日期：2026-10-03。审查基线：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

补充代码审查：`781366e89362a54d9036d3aed070fad169ba8204`。v1.2 经维护者要求纳入 run 脱敏、公共读取边界、输入采集时点和已知依赖规范冲突四项调整；当前版本替代 v1.1 作为执行方案。

本目录保存本轮七份执行方案及可复制的开发 Agent 提示词。S1-A 至 S4-B 的工程任务已交付；资源回放、采用活动和未批准的政策提案分别登记状态。会话从实际 HEAD 复核，不回退到审查基线。

2026-10-20：[先行补验报告](../../dogfooding/2026-10-20-validation-followup/README.md)在 `948d164` 完成 fresh quality、五项目 Gate A、H2、10 原生 child / 5 pair / 20 export 和新输入 discover 接受链。正式 judge 仍绑定 `75d1b0`；原始 metadata 缺失及 HF 403 保持 BLOCKED。后续 R06-B 不把这些资源执行改绑到新产品提交。

## 从这里开始

1. 阅读 [统一执行总则](00_Execution_Guide.md) 以及仓库 [AGENTS.md](../../../AGENTS.md)、[架构决策](../00_architecture_and_decisions.md)、[规格](../01_specification.md)、[val.md](../../../val.md)。
2. 从 [Agent 提示词](AGENT_PROMPTS.md) 复制与本次任务对应的启动指令。
3. 读取前置 [S3-B报告](../../dogfooding/2026-10-14-reliability-s3b/README.md) 和 [runtime evidence交接](../../dogfooding/2026-10-14-reliability-s3b/runtime-evidence-handoff.md)，核对R04-A/R04-B实际提交、批准的R04-S、完整本地Gate及冻结桥兼容证据。
4. 读取 [S4-B 报告](../../dogfooding/2026-10-18-reliability-s4b/README.md)：D03 发布门已交付，S4-A 的 D01 / D02 成果继续保留。A01 按 [06](06_Validation_and_Adoption.md) 的输入与候选身份继续推进，工程交付不授权发布版本。
5. [A01 本地证据报告](../../dogfooding/2026-10-18-a01-local/README.md)保留 10-18 当地环境的 12/50 恢复及两路径 stdlib 回放。后续 [10-19 资源实跑](../../dogfooding/2026-10-19-resource-completion/README.md)在已提供的 Linux 节点恢复 45/50 个精确 slot，节点上 0 ACCESS_BLOCKED、5 个原始 metadata manifest 仍 MISSING；不代表本机已持有这些文件。Linux H2、五项目原生 GPU A/B 和 20 个默认 export 状态在 `750270b` 通过，VAL-R01 对这些产品字节关闭。
6. [R02-R snapshot 修复与新 judge A/B](../../dogfooding/2026-10-19-judge-snapshot-fix/README.md)在 `75d1b0` 通过完整捕获、语义配对及已授权 provider 验收，关闭 VAL-R02；旧 `750270b` judge A FAIL / B NOT_RUN 原样保留。[Windows 测试 ID 跟进](../../dogfooding/2026-10-19-judge-snapshot-fix/windows-ci/README.md)的 `409a1a7` 仅改测试元数据，产品不变。前一进度核对已确认 [`af8adea` 五项 CI 成功](https://github.com/EnumaElish123/ReproLLM/actions/runs/39209260394)；后续提交另行核对，不改写历史 CI receipt。VAL-R03 仍因 HF 小文件 403 和原始 manifest 缺口阻塞；`75d1b0` 未重跑 GPU/H2，完整同候选发布矩阵仍未完成。
7. 不依赖新增资源的接续路线是 **A02 试用材料 → A03 本地事实整理 → P-A/P-B**。读取 [A02 任务卡和反馈入口](../../trials/a02-local/README.md)、[A03 事实与草稿](../../adoption/a03-2026-10-18.md)和[A02/A03 接续报告](../../dogfooding/2026-10-18-a02-a03-local.md)。材料可审阅、真实试用 PENDING、持续采用未观察到，三种状态分别记录。[2026-10-22 A03 补充](../../adoption/a03-2026-10-22.md)已完成公开字段匹配、草稿长度与来源核验；申请人信息、账号／角色／组织标识及提交授权仍待确认，申请未提交。
8. 维护者已于 2026-10-18 [接受 R08-A 方案 A](proposals/R08-A/decision.json)，并按 P-B 实施直接 judge params 叶子默认 HIGH，保留用户 LOW/NONE 与历史记录。验收/资源状态见 [P-B 报告](../../dogfooding/2026-10-18-r08a/README.md)；[原提案快照](proposals/R08-A/R08-A_direct_judge_params.md)继续保留当时状态。R06-B 方案 A 已于 2026-10-20 [获具体批准](proposals/R06-B/decision.json)，P-B 实施及独立 CPU 验收见[接续报告](../../dogfooding/2026-10-20-r06b/README.md)；[原提案](proposals/R06-B/R06-B_dependency_lock_scope.md)保持准备时快照。R07-C 的局部 A、具体规范与 D-41 engine patch 已获[明确接受](proposals/R07-C/decision-accepted.json)，P-B 仅实施两规则在 primary-Python 缺口 / 内部 coverage 不可用时的空结果 PASS veto，见[本轮实施及验收报告](../../dogfooding/2026-10-20-r07c-pb/README.md)。这是有意保守的局部政策；更广 mixed evidence 范围仍 OPEN。原 [P-A 材料](proposals/R07-C/R07-C_incomplete_scan_conclusions.md)和[P-A 报告](../../dogfooding/2026-10-20-r07c-pa/README.md)保留准备时状态，不冒充 P-B 结果。R08-B A4 四条精确路径及规范 / 前瞻补丁已获[具体接受](proposals/R08-B/decision-accepted.json)，P-B 默认 HIGH 实施与当前验收状态见[P-B 报告](../../dogfooding/2026-10-20-r08b-pb/README.md)。原[提案](proposals/R08-B/R08-B_exact_parameter_risk.md)、PROPOSED 决定及[P-A 报告](../../dogfooding/2026-10-20-r08b-pa/README.md)保留准备时快照；匹配、用户覆盖和历史资源结果归属保持。


2026-10-21，维护者已[接受 R07-C profile-absence 局部 P 与具体补丁](proposals/R07-C/profile-absence/decision-accepted.json)，
P-B 实施及当前验证状态见[接续报告](../../dogfooding/2026-10-21-r07c-profile-pb/README.md)。
原[提案](proposals/R07-C/profile-absence/R07-C_profile_absence.md)、PROPOSED 决定和[P-A 报告](../../dogfooding/2026-10-21-r07c-profile-pa/README.md)
保留准备时状态。更广 dependency/listing/framework 和充分证书仍 OPEN。

本批已实施 [R07-C D-L：格式 lock 中出现的包与 Python 缺口](proposals/R07-C/dependency-lock-credit/R07-C_dependency_lock_credit.md)，
具体 D-L 与补丁已[明确接受](proposals/R07-C/dependency-lock-credit/decision-accepted.json)，
仅对可能受遗漏 import 信用影响的待警告包 SKIP；[P-B 报告](../../dogfooding/2026-10-21-r07c-dependency-pb/README.md)记录实现、已通过的完整质量门与五项目验证；最终 HEAD CI 另行核对。
[原 P-A](../../dogfooding/2026-10-21-r07c-dependency-pa/README.md)与 PROPOSED 快照保留，不冒充本轮正式结果。

维护者已[具体接受 R07-C D-F 与补丁](proposals/R07-C/format-lock-read/decision-accepted.json)：
已关联格式锁的已知读取/解码失败逐包 SKIP，独立于 Python coverage，既有 exact/qualified 与 D-L 保留。
[P-B 报告](../../dogfooding/2026-10-21-r07c-lock-read-pb/README.md)记录已完成实施、完整本地质量门与五项目/受影响验证；最终 HEAD CI 另行核对。
[原提案与 P-A 快照](proposals/R07-C/format-lock-read/R07-C_associated_format_lock_failures.md)原字节保留，整个 R07-C 仍 OPEN。

交付来源：[S1-A](../../dogfooding/2026-10-10-reliability-s1a/README.md)、[S1-B收尾](../../dogfooding/2026-10-10-reliability-s1b/r03-session.md)、[S2及scope交接](../../dogfooding/2026-10-10-reliability-s2/s2-handoff.md)。S3-A来源：[交付报告](../../dogfooding/2026-10-13-reliability-s3a/README.md)；S3-B来源：[交付报告](../../dogfooding/2026-10-14-reliability-s3b/README.md)。历史PLAN-REVISE/PLAN-IMPORT状态及资源BLOCKED记录保留。

R07-A [性能跟进](../../dogfooding/2026-10-13-reliability-s3a/r07a-perf-session.md)
提交 `110087b1e416c12c25253c07365944935e986470`，修复首次推送的 Windows CI 预算失败。
该性能会话的本地质量门为 2,505 tests / 174 security tests；当时源码的五项目 Gate A
126 条全新命令、987 项完整比较及另列的 30 项独立核对全部通过。

维护者已[具体接受 D-S 与补丁](proposals/R07-C/format-lock-structure/decision-accepted.json)，
P-B 已实施有限格式锁结构失败和部分信用保留，最终验收状态见[P-B 报告](../../dogfooding/2026-10-21-r07c-lock-structure-pb/README.md)。
原[P-A 报告](../../dogfooding/2026-10-21-r07c-lock-structure-pa/README.md)和 416 文件 PROPOSED 快照保留。
一般依赖/requirements、listing/framework 和充分证书仍 OPEN。

## 执行文件与会话

| 文件 | 工作范围 | 会话 |
|---|---|---|
| [00 执行总则](00_Execution_Guide.md) | 任务编号、依赖、质量门、五项目验证、兼容性和交接 | 每次必读 |
| [01 产物保全与有效参数](01_Persistence_and_State.md) | R00、R01、R02、R02-R、R03 | S1-A / S1-B |
| [02 依赖准确性](02_Dependency_Accuracy.md) | R06-G、R05-A、R06-A、R06-P、R05-B | S2-A / S2-B |
| [03 扫描与运行证据](03_Scan_and_Runtime_Evidence.md) | R07-A、R07-B、R04-A、R04-B | S3-A / S3-B |
| [04 Recipe 与发布](04_Recipe_and_Release.md) | D01、D02、D03 | S4-A / S4-B |
| [05 策略与兼容性](05_Policy_and_Compatibility.md) | R05-S、R06-B、R07-C、R08-A/B、条件 R04-S | 按具体决定推进 |
| [06 验证与采用](06_Validation_and_Adoption.md) | A01-A/B、A02、A03 | 输入准备可提前开展 |

四个工程 Sprint 各分两次会话。策略提案和资源准备按依赖推进；只暂停受待决事项影响的工作。完整任务状态、验收矩阵和完成定义见各分册，勿把计划中的检查写成已经通过。

## 本次修订任务：PLAN-REVISE

维护者要求按代码审查建议优化方案并上传。本次只更新任务卡、优先级、依赖、验收及提示词，并执行文档检查、质量门和五项目 L0 Gate A。该历史修订当时未执行产品修复；当前S1/S2及S3-A状态见上方实际报告。其他规范决定、D-41 审阅、Issue #9 和资源验收单独推进。

- R02-R 纳入 S1-B，以 P0 处理 run 结构化值及文本快照脱敏。
- R06-G 放在 S2-A 第一项，在普通文件内容读取入口阻断根外访问；R06-P 保留 include 图职责。
- R04-B 纳入 S3-B，明确输入基线、结束后变化和消费证据，并成为 D01 / A01-B 验收依赖。
- R05-S 提前处理已确认的 Conda 规范冲突，R05-B 合入须引用具体决定。

详见 [v1.2 调整记录](00_Execution_Guide.md#101-v12-根据当前代码补充的四项调整) 和 [本次会话报告](../../dogfooding/2026-10-03-reliability-plan-v1.2.md)。单项超过原会话容量时登记具名接续会话，不能缩减质量门。

## 历史入库任务：PLAN-IMPORT（v1.1）

首次入库时维护者授权将上述方案和已给出的开发 Agent 提示词纳入合适的仓库目录并推送。该文档任务包含：

- 保存七份 v1.1 方案，保留其任务范围和待决语义。
- 提供首个会话和后续会话的可复制提示词，并接入仓库导航。
- 检查文档链接和内容，执行既有质量门与五项目 L0 Gate A。
- 记录验证结果，提交并推送本次文档变更。

本任务不执行 S1 的产品修复，不修改 schema、drift policy 或 gold，也不触发发布/付费资源。它不替代后续 R00 的问题复核。

入库验证记录见 [PLAN-IMPORT 会话报告](../../dogfooding/2026-10-03-reliability-plan-import.md)。后续实现报告按照总则模板记录任务、提交、测试、完整 gold 差异及接续输入。

## R07-C D-M proposal follow-up (2026-10-21)

The maintainer has [specifically accepted D-M](proposals/R07-C/declaration-read/decision-accepted.json).
The [P-B report](../../dogfooding/2026-10-21-r07c-declaration-read-pb/README.md) records its bounded implementation and current acceptance status.
The original [proposal](proposals/R07-C/declaration-read/R07-C_declaration_body_failures.md) and
[P-A report](../../dogfooding/2026-10-21-r07c-declaration-read-pa/README.md) retain their preparation-time state.
No gold or historical result is rewritten; whole R07-C remains OPEN.

## R07-C decoded declaration structure P-B (2026-10-22)

The maintainer has [accepted D-M-S option A and its concrete specification patch](proposals/R07-C/declaration-structure/decision-accepted.json).
The [P-B report](../../dogfooding/2026-10-22-r07c-declaration-structure-pb/README.md)
records the bounded structure checks, retained partial declarations/credit/priority
and final validation status. The original
[proposal](proposals/R07-C/declaration-structure/R07-C_declaration_structure.md),
PROPOSED decision and [preparation report](../../dogfooding/2026-10-22-r07c-declaration-structure-pa.md)
remain unchanged. Package-value/string grammar, requirements graphs and wider
R07-C stay OPEN. No release is authorized.

## R07-C requirements depth frontier P-A (2026-10-22)

The next narrow [proposal](proposals/R07-C/requirements-depth/R07-C_requirements_depth_frontier.md)
is PROPOSED; its concrete spec patch remains unapplied and the future policy unexecuted.
The [P-A report](../../dogfooding/2026-10-22-r07c-requirements-depth-pa.md) records the
accepted product baseline, separate PB closure/CI status and unchanged current observations.
Specific acceptance of [option A, the exact patch and conservative boundaries](proposals/R07-C/requirements-depth/spec-issue-draft.md)
is required before P-B. Requirements grammar, omitted candidates/listing/framework and
the whole R07-C scope remain OPEN. No release is authorized.

## R07-C D-G delegated decision and P-B (2026-10-22)

The preceding P-A paragraph retains its preparation-time state. The maintainer
has explicitly delegated the D-G A/B adjudication; the agent
[selected A and the concrete patch](proposals/R07-C/requirements-depth/decision-accepted.json),
including the stated conservative repository-wide costs. The [P-B report](../../dogfooding/2026-10-22-r07c-requirements-depth-pb/README.md)
records implementation at `d823f90`, final local quality, fresh five-project Gate A
and affected D-G consumer acceptance. Exact pushed-head CI remains a separate delivery check.
A separate [ordering evidence correction](proposals/R07-C/requirements-depth/decision-evidence/README.md)
preserves the original observations and adds actual deep-first/reverse-order evidence.
Other OPEN R07-C policies and release remain outside this specific delegated choice.

## R07-C ordinary requirements comments P-B (2026-10-22 to 2026-10-23)

The maintainer specifically [accepted D-C A and its exact patch](proposals/R07-C/requirements-comments/decision-accepted.json).
P-B implements the bounded ordinary-line fallback at `0f8c4df`, preserving original
route/full-line success, the file-wide trailing-backslash veto, existing credit and
uncertainty priorities, and other manager grammars. The [P-B report](../../dogfooding/2026-10-22-r07c-requirements-comments-pb/README.md)
records 141 new regression cases and their complete RED/GREEN history, the full local
quality gate, fresh five-project Gate A, affected and CLI replay, final source identity
checks and independent archive readback, all PASS. Final pushed-head CI and Linux exact
schema verification are independently checked at delivery. The [P-A report](../../dogfooding/2026-10-22-r07c-requirements-comments-pa.md)
and original PROPOSED packet remain historical snapshots. Other R07-C policy, resource
gates, real adoption and version release remain separately bounded.

## R07-C PEP 621 requirement-string failures P-B (2026-10-23)

The [contextual acceptance record](proposals/R07-C/pep621-strings/decision-accepted.json)
binds the maintainer's specific next-step direction to the presented A and exact patch,
including repository-wide WARNING-to-SKIPPED and isolated exit 1-to-0 costs.
Implementation at `26a4d30` changes only the two existing PEP 621 parse-failure sites;
partial declarations, prior causes, credit and rule priority remain.
The [P-B report](../../dogfooding/2026-10-23-r07c-pep621-strings-pb/README.md) records
170 new cases, final full quality, fresh five-project Gate A, affected checks,
24 complete internal records and archive readback, all locally PASS.
Exact final-head five-job CI and Linux exact schema are checked at delivery.
The [P-A packet](proposals/R07-C/pep621-strings/README.md) remains an immutable historical snapshot.
The original [environment embedded-pip P-A](proposals/R07-C/environment-pip/README.md) remains an immutable preparation snapshot.

## R07-C environment embedded-pip P-B (2026-10-23)

The maintainer [explicitly accepted D-M-E A and its exact specification patch](proposals/R07-C/environment-pip/decision-accepted.json), including conservative costs.
Implementation at `a221e9d` changes only the existing nonblank stripped pip caller's failure handling.
The [P-B report](../../dogfooding/2026-10-23-r07c-environment-pip-pb/README.md) records 154 new cases,
final local quality, fresh five-project Gate A, affected validation, 27 full internal records and archive readback, all PASS.
Blank filtering, ordinals, diagnostics, partial declarations, credit and priorities remain.
Exact final-head five-job CI and Linux exact schema/docs/examples are checked separately at delivery.
Poetry explicit-version extraction may be investigated in a new independent P-A; other policies,
resources, adoption and release are not automatically approved. Wider R07-C remains OPEN.

## 当前接续：R07-C D-M-V P-B（2026-10-23）

维护者已[接受D-M-V A、精确补丁及全仓成本](proposals/R07-C/poetry-version/decision-accepted.json)。产品`b18ed19`仅在原Poetry循环记录显式非str version的invalid_structure，保留先因/声明/信用/line fallback。
[P-B报告](../../dogfooding/2026-10-23-r07c-poetry-version-pb/README.md)记录171新增回归、最终质量、fresh五项目Gate A/受影响、35完整record和归档回读，适用本地门均PASS；最终精确HEAD五项CI交付另核。
原[P-A](proposals/R07-C/poetry-version/README.md)、PROPOSED决定和原观察保持字节。下一步只建议独立P-A核Pipfile显式version、packages/dev-packages两节和allow_bare=False；不套用本次批准。更广R07-C、资源及外部反馈仍OPEN，不发布版本。
