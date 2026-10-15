# S4-A：首次 CI 反馈后的工具修复

首推 `c8673701cc3894f45432558fbede4aa1f73264bd` 的远端 CI 未通过；此记录保留
失败原貌，不将本地 Linux 质量门写成跨平台完成。产品候选仍为 D02 的
`b86c014cf9f15f1efddb6902979dcc6ddf79be9f`，原单次 wheel、五项目 Gate A 和
真实 lm-eval A/B 均保留其精确来源，不事后改称新 SHA 的资源执行。

## D01 的示例检查接线

Ubuntu 3.12 的 `Examples stay valid` 仍对所有示例执行源目录 `lock --check`。
新 recipe 按合同在固定框架的 disposable checkout 里生成真实锁，源目录没有
预生成锁。本地同一 CLI 的 L1 audit exit 0，`lock --check` exit 1，明确报告
`reprollm.lock is missing`；公开 CI annotation 对应同一步骤。

修复提交 `707d5778470e558d35b2b558c612c0559ed51da5` 保留所有示例的 L1 审计，
仅对精确命名的 native recipe 断言源锁不存在；其余示例仍无条件检查锁。
新案例的离线 L1/L2 在完整 pytest 中执行，真实模型证据在独立原生包中。
不按“文件存在才检查”静默漏过任意新/旧示例。

六个实际 shell 接线正反例全部符合预期：正常四例、旧锁缺失、旧锁过期、
未知新例缺锁、audit 错误、native 出现意外静态锁。实际完整 workflow step
随后用真实 CLI 执行，四个 L1 audit 和三个历史锁检查全部通过，4.731358s。
示例索引生成器补上 native recipe 的不同准备方式；回归先 RED 后 GREEN，
重复 refresh 保留该目录全部原始输入字节且不伪造锁。

## D02 的 Windows 编码

同一首推 CI 的 Windows job 有三项 quickstart 测试失败、三项 distribution
fixture setup 错误，均为 `NoneType.rstrip`。公开 annotation 和来源哈希保留；
匿名访问不提供完整原 CI 日志，不补造未取得的 stack trace。

真实子进程回归证明 `-I` 会忽略环境中的 PYTHONUTF8/PYTHONIOENCODING。
在 Windows 的本机编码管道中，父进程按 UTF-8 读取可能使 reader 失败而留下
None。Linux 的实际 child 加控制 locale 与 CP1252 stderr 边界重现相同错误。
修复为 isolated walkthrough、pip install 和 import probe 显式传 `-X utf8`；
中文、非 ASCII 输出及完整 stderr 都有真实 child 回归，不将 None 吞为空串。

修复提交 `13830addfd19389d61ec0256e728bbf4b57ab02a` 仅改两个验证工具与
相关回归。两项新测试先 RED 后 GREEN，随后相关教程、生成文档、onboarding
和 distribution 合计 51 项通过，79.01s；Ruff / format / mypy 通过。

## 重新验收

按 [验证工作流](../../plan/validation-workflow-2026-10-13.md) §3，这次仅 CI、
验证工具、相关测试及生成索引的跟进仍须重跑完整质量门。最先启动的一次门在
发现 Windows 故障后仅终止本任务的进程树，保留 `ABORTED_AFTER_NEW_CI_FAILURE`
及部分输出，未计为 PASS；修复冻结后改用全新目录完成最终门。

最终工具候选为 `13830addfd19389d61ec0256e728bbf4b57ab02a`。
21/21 条命令、21 次来源检查全部通过：20 项规范质量检查，加同一原 wheel
的一次 canonical 实装。全量 pytest **2692 passed、2 slow deselected**，413.47s；
总覆盖率 93.83%，核心 redaction 行/分支 100%，独立 security 205 passed。
Ruff / format / strict mypy、四份生成文档、十份 schema、历史示例和 self-audit
均通过；输入文件与验证器前后不变。门墙钟 521.471154s，命令累计 518.358207s。

canonical 实装 26 个 CLI 命令、13 项合同检查全通过，29.194208s。修复后另在
新目录回放同一 wheel 的五个故障场景，50.96s，额外 38 个 CLI 命令
（缺模板 12、source injection 26）全部符合预期；133 项
原始流/摘要/工具来源完整性检查通过。旧记录及原 wheel 均未覆盖。

最终范围守卫核对 509 个受保护的非文档输入与 b86 产品候选逐字节相同，
只有七个精确命名的 CI/工具/测试/生成索引路径获得工具例外；141 份 wheel
package payload 另与当前 src 集合及每文件字节一致。两种核对有重叠，不相加
当作独立文件数。

这次工具跟进的 Gate A/B 为 `NOT_APPLICABLE`：受保护的产品、默认配置、
profiles、模板、依赖、schema 和打包输入与已验收产品候选逐字节相同。
原生 recipe 的仓库源输入及 wheel payload 另有完整 byte guard。D02 工具变动的相关实装正反例
使用同一原 wheel 新执行；没有第二次构建，没有重复 GPU 或五项目产品命令。
这是对工具变更的适用矩阵，不把原五项目 PASS 改名为最终工具提交的资源证明。

可复核证据见 [CI 补充索引](ci-validation/evidence-index.json)、
[独立包复核](ci-validation-review.json)和[主执行者核对](root-ci-evidence-review.json)。
包含首推 Ubuntu/Windows 失败、实际接线与工具回归、被中断的首次门、全新
最终门、相同 wheel 的新实装与负例；仅替换机器基础设施路径/身份并保留原 SHA。
最终推送 main 的准确 HEAD 与五项 CI 结果见会话最终回复和本地 final-ci.json。
