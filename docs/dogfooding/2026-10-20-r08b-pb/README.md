# 2026-10-20 · R08-B A4 / P-B

状态：**产品实现与定向验收通过；最终共享质量门、五项目及交付 CI 待执行**。
起点 `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`；纯 P-A 快照提交
`dfefce06513a0ce0f32a8a54c10fac8e5f6cdde5`。

维护者已[具体接受 A4、规范和前瞻补丁](../../plan/reliability-2026-10-03/proposals/R08-B/decision-accepted.json)。
产品仅在默认表逐条加入四个 HIGH：
`privacy.mechanism.params.target_epsilon`、`privacy.mechanism.params.target_delta`、
`privacy.mechanism.params.max_grad_norm` 和 `training.params.num_train_epochs`。
这些等级描述已记录配置变化的比较风险，不证明参数已消费、隐私保证成立或结果因果。
用户 LOW/NONE、profile 继承、first-match、单层 wildcard 和其余字段保持。
不改 schema、State、matcher、profiles、依赖或版本，不发布 release / tag / PyPI。

原 P-A packet / PROPOSED 决定及历史 native / judge 报告原字节保留；
前瞻 `val.md §8.3.1` 只规定新候选 diff 的 epsilon HIGH，不重写旧 MEDIUM 结果。
原始 metadata 缺失与 HF 403 仍是独立外部缺口；本次静态默认表任务不启动新的资源里程碑。

## 定向验收

[RED→GREEN 原始证据](tdd/summary.json)：新增 86 项参数化验收先在旧默认运行，
25 failed / 61 passed / 218 deselected，失败均为四条新默认缺失或 MEDIUM→HIGH 预期差异。
应用接受补丁后，两个完整受影响模块 **304 passed**；Ruff check / format 均通过。
验收覆盖四字段 changed / added / removed、实际 Manifest→State、用户 LOW/NONE、
profile 继承、broad / exact first-match、深层与别名控制、完整 CLI JSON、过滤 / 阈值、
全量 summary、无额外 HIGH 掩盖、重复确定性、自 diff、只读及 schema。

完整质量门、五项目 fresh Gate A 与受影响 diff 结果将在最终收尾记录；当前不冒充 PASS。
五项目 diff 将逐份比对 P-A 预先写好的独立预期，并新增每项目单一配置差异与覆盖场景。
只影响 diff 消费者，不重新执行未受影响的 init / lock / run / export 或付费 / GPU 路径。

## 证据保留与交付

原始 unified patch 的空白上下文行按已接受哈希保留；Git 将其识别为 trailing whitespace，
这是不可改写的补丁语法，不将该检查报告为全文件无例外 PASS。
源文件及手写文档另行检查。报告收尾只补证据与导航，保持最终验证产品输入。
main 原有 README、docs index 修改及额外案例草稿保持原字节，不纳入本轮提交。
最终交付以实际推送 main HEAD 的五项 CI 为准，不复用起点或任务提交的旧结果。
