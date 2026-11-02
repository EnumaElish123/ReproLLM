# Skill v2 最终工程与资源验收

执行期间：2026-10-31 至 2026-11-02。本报告记录推送前的限定范围工程验收。
**SK10–SK21 的代码实现已齐；质量门、五项目基础/CPU、公开匿名 HF、五组 GPU A/B、安装通道和七次真实 Codex Linux 流程已通过。**
认证 metadata、正式 discover 和 judge 因本轮具体授权尚未回复，保留为 `BLOCKED_NOT_AUTHORIZED`。
Claude Code 按维护者决定为 `DEFERRED_BY_MAINTAINER`，外部研究者反馈为 `UNOBSERVED`。
因此本轮可交付已验收的工程范围，不能标为 `FULL_ACCEPTED`。本报告不预写自身提交的 CI 结果；
确切推送提交的五项官方 CI 在推送后独立核对并保留会话收据。

依据：[执行方案](../../plan/skill-2026-10-30/README.md)、[A01–A24 矩阵](../../plan/skill-2026-10-30/acceptance.md)、
[验证工作流](../../plan/validation-workflow-2026-10-13.md)与 [val.md](../../../val.md)。
原生规则、引擎、redaction、正式 schema、依赖和五项目科学 gold 均未改动。
MCP、PyPI/技能市场发布和外部联系不属于本次交付。

## 实现与当前范围

| 任务 | 任务提交 | 实现 |
|---|---|---|
| SK16 | `8a418419` | 原生在线 lock、API metadata 验证及显式网络 doctor；沿用原重试、代理和未验证 provenance |
| SK17 | `3de9bebd` | discover 原生预览、精确消息/输入绑定、逐 POST 预算预留、失败未知费用保留及独立候选接受 |
| SK18 | `2cd8694` | 保存/显式命令、准确 argv/cwd、recorder 与子环境区分、原生 run v2 与输入证据 |
| SK19 | `4cb8659` | 持久操作、防重复、断连查询、安全取消和有限脱敏日志；卸载后仍可读既有终态 |
| SK20 | `0c51cda` | 25 个 CLI 节点、85 个参数、33 种 typed actions 的覆盖表及行为检查；真实 Codex 工作流 |
| SK21 | `ce7bc79` | 一次配置、自然语言试用与恢复教程；`a6f7e01` 明确 Agent 自写文档和原报告的隐私合同 |

任务提交及后续修正共享最终门，不把每个中间提交当已验收。
[A01–A24 分层映射](acceptance-map.md)区分单元、原生、资源与宿主证据；
[静态选项清单](evidence/cli-option-inventory.json)不等于每个资源分支已实测。
SK17 的来源文本证明、平台 deadline 与 collection warnings 修正保留原始输入/请求；
SK14 的空 argv 与只读 Git 观察修正保留原生导出和真正源变动拒绝。
原尝试失败、独立审阅发现及修正后证据分别留存，不以新成功改写旧失败。

工程输入为 `a81aa7a3b2fb5b9a323ee09146dfeefa2cf47c29`，
文稿输入为 `a6f7e018b92465f6b530fe8029272abdde292736`。
后者仅改变三份 Markdown：15,292 项 Git 身份中 15,289 项保持一致。
遵循文档变更例外复用实际工程门，受影响的七次真实宿主流程已全部重跑；
没有宣称在文稿提交重新跑过完整产品测试。

## 已闭合的共享验证

| 门 | 实测结果 | 完整证据范围 |
|---|---|---|
| 最终质量 | 24/24 PASS；6,666 tests，0 failure/error/skip，2 slow deselected | [质量收据](evidence/quality.json)；组合覆盖率 91.904398%，redaction 24/24 分支 |
| 五项目新鲜基础 Gate A | 50 次命令、31 项检查、10 份完整 JSON，通过 | [基础收据](evidence/gate-a-base.json)；规则、profiles、hints、paths、diagnostics 全量比较 |
| 当前/历史 CPU 导出 | 40 exports、40 guards、5 discover previews；335 次实际调用，通过 | [完整说明](cpu-export.md)与[收据](evidence/cpu-export.json)；四模板、历史/当前、拒绝保全和完整消息比较 |
| 公开匿名 HF | 40 完整案例、199 原始执行记录、10 owned operations、6 doctor 对照；58 原生 GET，通过 | 仅公开匿名 HF 子矩阵；认证 API、付费和 GPU 不在此门 |
| 本地模型/数据预检 | 45 个模型文件及 2 份 canonical dataset 行集，通过 | 只读本地输入；无网络、下载或 GPU 模型加载；不是科学运行验收 |
| 离线 judge 捕获 | native/Skill 各一次真实 mock child，通过；外部请求 0 | [限定说明](offline-judge.md)与[收据](evidence/offline-judge.json)；保留 9 项完整差异，不替代正式 judge A/B |
| 真实 Codex Linux | 七次流程，通过；用户手输 ReproLLM CLI 为 0 | [逐流程说明](codex-host.md)与[完整宿主收据](evidence/codex-host.json)；仅此宿主和实际平台范围 |

完整 raw/JUnit、私有路径和运行日志不复制到公开报告；便携收据保存原证据哈希及判定边界。
公开 HF、本地输入、CPU 和宿主的接受哈希及独立复核见[组件索引](evidence/components.json)。
实际原生源码 148 文件与已发布可信来源逐项一致，安装身份不只按版本字符串判断。
CPU 门只证明其明确文件保护范围；[末尾保护收据](evidence/protected-inputs.json)另行核对全会话原始基线。
[555 份可执行输入逐文件一致](evidence/executable-inputs.json)，最终新增文稿单独检查，不宣称又执行过一轮完整产品测试。

## 资源边界与推送前交付快照

| 门 | 当前状态 |
|---|---|
| 五项目 GPU 原生/Skill A/B | PASS；20 次规范实验、10 份完整成对比较；[完整记录](gpu-resources.md)与[便携收据](evidence/gpu-resources.json)。另保留旧 HB 两次实验，实际 GPU 实验共 22 次 |
| DeepSeek 认证 metadata | `BLOCKED_NOT_AUTHORIZED`；未读取用户 key 或发认证请求 |
| 正式 discover | `BLOCKED_NOT_AUTHORIZED`；固定公开消息已核对，未发送 POST |
| 正式 judge A/B | `BLOCKED_NOT_AUTHORIZED`；本轮新预算未获回复，未发送 POST |
| 最终安装通道 | PASS；[专项收据](evidence/installation-channels.json)：当前 fresh online、卸载保全、cached offline 新建环境，以及最终 wheel/venv 和 Codex 离线源码通道 |
| 最终研究环境/九份 WIP 保护 | PASS；五个原始项目、九份 WIP、41 项开发依赖、927 份环境元数据与原基线一致，见[末尾收据](evidence/protected-inputs.json) |
| 本次最终交付提交与五项 CI | `PENDING_AT_REPORT_COMMIT`；推送后按确切提交检查五项官方 CI |

前置 `693c2c4` 的五项官方 CI 和 Ubuntu 3.12 十二个必需步骤已全部通过，
见[同提交收据](evidence/predecessor-ci.json)及[运行](https://github.com/EnumaElish123/ReproLLM/actions/runs/41130054173)。
这不替代本次新交付提交的 CI。

限定范围工程交付遵循计划 §8：未获本轮授权的三项线上门记 `BLOCKED_NOT_AUTHORIZED`，已验收部分可交付，矩阵未齐不能称全功能完成。
后续只补认证 metadata、正式 discover 和正式 judge 的当前候选验收；凭据用途/目标域名及新预算需得到具体确认。
此前认证请求在发送前被自动审批拒绝，原因是凭据用途和目标域名未获确认；没有读取真实 key 或发出该请求。
Claude Code 暂缓及外部反馈未观察不由脚本/子代理重放冒充通过。
