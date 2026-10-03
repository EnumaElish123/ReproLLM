# ReproLLM 可靠性开发执行方案 v1.1

日期：2026-10-03。审查基线：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

本目录保存本轮七份执行方案及可复制的开发 Agent 提示词。实现任务当前均待执行；后续会话从实际 HEAD 复核行为，不回退到审查基线。

## 从这里开始

1. 阅读 [统一执行总则](00_Execution_Guide.md) 以及仓库 [AGENTS.md](../../../AGENTS.md)、[架构决策](../00_architecture_and_decisions.md)、[规格](../01_specification.md)、[val.md](../../../val.md)。
2. 从 [Agent 提示词](AGENT_PROMPTS.md) 复制与本次任务对应的启动指令。
3. 第一次实现执行 **S1-A：R00、R01**；后续会话读取上一会话的实际报告。

## 执行文件与会话

| 文件 | 工作范围 | 会话 |
|---|---|---|
| [00 执行总则](00_Execution_Guide.md) | 任务编号、依赖、质量门、五项目验证、兼容性和交接 | 每次必读 |
| [01 产物保全与有效参数](01_Persistence_and_State.md) | R00、R01、R02、R03 | S1-A / S1-B |
| [02 依赖准确性](02_Dependency_Accuracy.md) | R05-A、R06-A、R06-P、R05-B | S2-A / S2-B |
| [03 扫描与运行证据](03_Scan_and_Runtime_Evidence.md) | R07-A、R07-B、R04-A | S3-A / S3-B |
| [04 Recipe 与发布](04_Recipe_and_Release.md) | D01、D02、D03 | S4-A / S4-B |
| [05 策略与兼容性](05_Policy_and_Compatibility.md) | R06-B、R07-C、R08-A/B、条件 R04-S | 按具体决定推进 |
| [06 验证与采用](06_Validation_and_Adoption.md) | A01-A/B、A02、A03 | 输入准备可提前开展 |

四个工程 Sprint 各分两次会话。策略提案和资源准备按依赖推进；只暂停受待决事项影响的工作。完整任务状态、验收矩阵和完成定义见各分册，勿把计划中的检查写成已经通过。

## 本次入库任务：PLAN-IMPORT

维护者本次授权的范围是将上述方案和已给出的开发 Agent 提示词纳入合适的仓库目录并推送。该文档任务包含：

- 保存七份 v1.1 方案，保留其任务范围和待决语义。
- 提供首个会话和后续会话的可复制提示词，并接入仓库导航。
- 检查文档链接和内容，执行既有质量门与五项目 L0 Gate A。
- 记录验证结果，提交并推送本次文档变更。

本任务不执行 S1 的产品修复，不修改 schema、drift policy 或 gold，也不触发发布/付费资源。它不替代后续 R00 的问题复核。

入库验证记录见 [PLAN-IMPORT 会话报告](../../dogfooding/2026-10-03-reliability-plan-import.md)。后续实现报告按照总则模板记录任务、提交、测试、完整 gold 差异及接续输入。
