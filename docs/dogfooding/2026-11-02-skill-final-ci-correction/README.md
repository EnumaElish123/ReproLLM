# Skill v2 最终交付的 CI 修正

后续 CI 核验：交付 `b526d6e` 的[五项官方 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/41386824410)
和 Ubuntu 3.12 十二个必需步骤均通过，见[确切 head 收据](evidence/delivery-ci.json)。
下文 `PENDING_AT_REPORT_COMMIT` 保留原报告提交时的状态，不是当前失败或待执行结论。

日期：2026-11-02。原最终交付 `4089594` 的五项官方 CI 中，一项通过、四项失败。
[原运行](https://github.com/EnumaElish123/ReproLLM/actions/runs/41376576272)与
[失败收据](evidence/original-ci-failure.json)保留；先前本地成功不替代该失败。
本轮仅修正测试夹具和补齐可跨平台的纯逻辑测试，产品行为、依赖、schema、打包及 CI 配置均不变。

依据：[Skill 方案](../../plan/skill-2026-10-30/README.md)、
[验证工作流 §3](../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义)和
[原最终会话报告](../2026-10-31-skill-final/README.md)。

## 失败原因及修正

| 原失败 | 修正和保留的合同 |
|---|---|
| Ubuntu Python 3.10/3.11 默认过滤 compiler warning，使专门的警告去重测试未观察到警告 | 仅为该测试显式选择 `always`；生产代码继续沿用调用者的 warnings filter；原计数、类别和隐私断言保留 |
| doctor 的 retry 测试替换共享 `time.sleep`，混入无关的 subprocess wait | 用模块自己的 clock namespace 替代共享标准库；三次请求、精确退避 `[0.5, 1.5]` 和隐私断言保留 |
| Windows 隔离 worker 缺少合成身份环境变量，且没有 `pwd` fallback | 为测试 worker 提供固定的 USER/USERNAME/HOME/USERPROFILE；不读取或复制真实身份 |
| macOS/Windows 产品+Skill 组合覆盖率低于 85% | 去掉纯 run-plan 测试的整文件 Linux 限制；真实 FD/worker 检查仍保留平台条件。新增 BytesIO 日志边界和取消证据的纯回调测试，不模拟完整平台支持、不降低门槛 |

任务提交：`54127f6`（SK16–SK20 夹具与 portable unit 修正）、`ffc2afb`（SK19 取消证据）。
适用规范为 §5 运行记录、§22 测试要求及 Skill SK19/A23；`ffc2afb` 提交说明中的“section 24”是引用笔误，以此更正。
后者的 61 例包含原六例完整保留和新增 55 例：代际变化、有限枚举、虚拟句柄关闭、状态复用/拒绝及公开投影。
无真实信号、pidfd 或进程身份读取；实际 Linux 控制器测试和断言均保留。
独立审阅无 P1/P2；[源桥](evidence/ci-candidate-source-bridge.json)与
[审阅概要](evidence/ci-correction-scope-review.json)列明文件范围和原证据的适用边界。
两份准备快照保留封存时的 `accepted:false` 与 Q-running 状态；实际质量结论以本轮质量收据为准。

## 最终本地验证

完整质量门绑定干净的 `ffc2afbf3ed0219badc5d54b378e9320a546648a`，前后输入逐字节一致。
24/24 检查通过；6,731 tests，0 failure/error/skip，2 slow deselected；组合覆盖率 91.989757%，redaction 分支 100%。完整门墙钟 1617.564 秒。
详见[本轮质量收据](evidence/quality.json)；这是一轮新的完整门，不复用旧测试结果。
既有 85% 组合覆盖率与 redaction 100% 要求保持；包含安全、ruff、mypy、十份 schema、生成文档、示例、wheel 内容及实际隔离安装。
quickstart 先核对已审阅 Git 包装器哈希，再执行 freshness；没有省略生成器。

定位期间平台过滤的 Linux 诊断曾出现 6,465 tests 全通过但覆盖率仅 84.900489%，明确记为 FAIL。
新增取消纯测试后的 trace 合并诊断为 85.255402%，仅用于判断是否值得启动完整门；
它不是新的全量运行，也不是实际 macOS/Windows 验证。
[诊断收据](evidence/portable-diagnostic.json)保留两个范围，实际跨平台结论由推送后 CI 决定。

本轮为测试/文稿会话，产品 Gate A/B 为 `NOT_APPLICABLE_TEST_ONLY`，按验证工作流解释，不增加新的产品 PASS。
188 个产品及包装输入与原资源候选逐项一致；原五项目基础/CPU、匿名 HF、五组 GPU A/B、安装与 Codex 结果
按其原候选和限定范围保留，不冒充在修正提交重跑。
原报告的 6,666 tests 和 555 份可执行输入证明是历史快照；本轮测试输入已经变化，以新收据和源桥为准。

[末尾保护收据](evidence/protected-inputs.json)核对五个原始项目、九份用户 WIP、41 项开发依赖和
927 份环境元数据；不是对研究环境所有字节的扫描。没有安装或更新研究依赖。

## 交付边界

本报告提交时，修正交付的五项官方 CI 为 `PENDING_AT_REPORT_COMMIT`，推送后按确切 head 独立核对。
旧 `4089594` 失败不会因为后来通过而改为 PASS；前置成功 CI 也不替代新交付 CI。

SK10–SK21 的代码实现已完成。三个线上分支仍为 `BLOCKED_NOT_AUTHORIZED`：
DeepSeek 认证 metadata、正式 discover、正式 judge A/B。本轮没有读取用户 key 或发送这些认证/付费请求。
Claude Code 为 `DEFERRED_BY_MAINTAINER`，外部反馈为 `UNOBSERVED`；不宣称 `FULL_ACCEPTED`。
此前认证请求在发送前被自动审批拒绝，原因是凭据用途和目标域名未获具体确认。
本轮不创建 PR、发布 PyPI/Skill 市场包或实现 MCP。
