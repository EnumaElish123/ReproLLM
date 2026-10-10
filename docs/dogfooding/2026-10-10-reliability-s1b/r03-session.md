# S1-B / R03 有效 CLI 参数与 State 合并

日期：2026-10-10。前置 R02：`2a025afc8f0204f350df7dd07c50592418791fc3`；
R02-R：`5e8e7844d55dd7c2971b81f4f9098a1d0409483a`。见
[R02-R commit binding](r02r-gate-commit-binding.json)。按
[R03 任务卡](../../plan/reliability-2026-10-03/01_Persistence_and_State.md#5-r03repeated-cli-的-last-wins-与-state-合并)
执行。任务内先验证真实 child oracle，再验证有界证据合并，不改变 drift
severity、默认 fail-on、绑定解析或任何 observation 与声明冲突的既有语义。

## 实现与独立预期

在有 argv 时间线的 ordered observations 投影处选最后一次 CLI，包括映射
alias；config/env 的同来源 tie 沿用 location/value 字典序。CLI、config、env、
lock、manifest 的优先级不变。

再次 merge 只在各输入的已选 primary 中选择，不重新提升旧 alternatives。
证据 identity 包括 source/detail/confidence/canonical value；重叠投影按
identity 的最大 multiplicity 合并，然后扣除一个 primary。保留同一投影中
真正重复的 observation，重合并与 JSON round-trip 不无界膨胀。
旧 v1 run 根据已有有序 observations 恢复，不增加 ordinal 或 schema 字段。

真实 argparse A：`--temperature 0.1 --temperature 0.9`，child 为 0.9；
B 反序为 0.1。effective State、audit 与 export 分别匹配 child，现行 HIGH
diff 检测温度变化并退出 1。self-diff 保持确定性并没有无关变化。
manifest 为 0.9、CLI 早先 0.1 最后 0.9 时，effective 为 0.9，既有一致性
规则仍报告早先冲突。该既有断言只调整 evidence 的顺序，不减去任何来源。

## 测试与质量门

真实提交 `5e8e784` 上先执行 paired child 单一回归：RED 1 failed / 0.94 秒，
最小 selection 修复后 GREEN 1 passed / 5.05 秒；再加入 bounded evidence
回归：RED 1 failed / 0.59 秒，multiplicity 修复后 GREEN 2 passed / 0.60 秒。
随后完整新验收 15 passed / 1.14 秒，相关消费者 106 passed / 10.74 秒。
实际 argv、退出码、wall time、原始日志 SHA 及各步 source SHA 见
[TDD ledger](r03-tdd.json)。

三个完整 State golden 文件没有修改；9 次投影及 427 个 leaves 与原文件、
前置提交逐字节一致，见 [golden proof](r03-golden-bytes.json)。仅修改一个
既有 runtime consistency evidence 顺序断言，旧 CLI 冲突值仍保留。
[applied source review](r03-independent-review.json) 已通过；源文件 SHA
`0422584106dd0aad09a033dd23bab956890e6d6010a88daa59041819241f304d`
与先前审阅候选逐字节相同。

全量质量门 14 项全部通过，见 [quality evidence](r03-quality.json)：
2079 passed / 2 slow deselected / 1 既有 slow marker warning，pytest 用时
316.070 秒，总覆盖 93.00%；redaction statement/branch 覆盖 100%；
security 82 passed / 1999 deselected。Ruff check/format、strict mypy、四项
生成文档 freshness 与十项 exported schema 完整集合及字节比较均通过。
沿用已验证的临时 Git `init -b` shim 兼容本机 Git 2.25.1；没有修改系统 Git、
依赖或扩大默认 slow selection。

## 五项目 Gate A 与提交绑定

五个原始固定版本 checkout 均 clean、SHA 与 `val.md` 相同。完整 baseline
45 个 leaf / 180 项完整比较全部通过；新增 R03 consumer 155 个 leaf /
498 项检查全部通过，合计 200 个 qualified leaf / 678 项比较与检查。
退出码为 195 次 0 与 5 次预期 HIGH semantic diff 的 1，没有未解释的失败。
baseline leaf 用时 160.984611 秒，consumer 250.851286 秒，合计
411.835897 秒。规则集合、profile、hints、paths、diagnostics 和生成 manifest
与 S1-A 完整 gold 比较 zero delta；没有更新 pin 或 gold。见
[Gate summary](r03-gate-summary.json)、[consumer commands](r03-gate-commands.json)、
[baseline commands](r03-gate-baseline-commands.json) 与
[full baseline comparison digests](r03-gate-baseline-comparisons.json)。

每个项目重新执行真实 argparse A/B、重复值、alias 与 mixed-source cases，
四种 State 投影/merge、JSON round-trip、证据 multiplicity、最新 run、
任何 observation 冲突检查、export、现行 HIGH diff、完整 self-diff，以及
脱敏 run 的 audit/diff/export consumers。R02-R 的七类 lock 拒绝、旧字节
保留、freshness-only 和 capture/snapshot 组合复用已通过的前置提交证据；
验证完整 retained-document digests、commit binding 与 13 个未改安全文件
SHA 后才允许复用。见 [regression reuse](r03-gate-prior-qualified-regression-reuse.json)。

首次 baseline 的 240 秒汇总 wrapper 超时，原因是验证文件系统只剩约
43 MB，HarmBench checkout 不完整。没有 orphan writer 后，保留全部
ledger、raw payload、harness 和五个原始 checkout，按 rename 保全 391 份
owned artifacts，清理已完成的五个临时 source-copy roots；清理用时
60.822143 秒，可用空间恢复到至少 1,237,712,896 bytes。
source、pins、contracts 和 raw digests 不变时复用 30 个完整 leaf，
在新 HarmBench clone 补执行 15 个 leaf，完成原定 45/180 baseline。
另一次成功 clone 仍计入全部实际执行，但不计入最终 qualified matrix；
中断 checkout 的退出码与 child 时长未知，明确单列，不当作通过。
共 201 个已完成实际 leaf，用时 418.716223 秒，另有 1 个状态未知的
checkout，实际尝试共 202 个 leaf；wrapper 的 240.096133 秒独立保留，
不叠加到 leaf 时长。见
[environment recovery](r03-gate-environment-recovery.json) 与
[execution accounting](r03-gate-execution-accounting.json)。

验证前后 149 个 product files 的完整 inventory SHA 相同：
`00af555641ebfa45e1b975f50b40a68c0b0159d02c26a6454ae9a9ddf28e9c76`。
候选基于前置提交 `5e8e784`，仅 State 产品文件变化；提交前再次核对
quality evidence 的三个 source/test SHA 与已审阅候选一致。见
[evidence index](r03-gate-evidence-index.json)。最终提交后用完整 Git tree
逐文件绑定本次已验证 product bytes，再推送 main。

## S2 / S3 交接

- S2 保持公共内容读取边界的任务顺序 R06-G → R05-A → R06-A；本批不修改
  scanner/config-read 或 requirements 引用范围。R05-S 规范决定继续单独处理。
- R04-A 消费正确的 selected State；不能重新展开 alternatives 选择旧 CLI，
  也不能把 recorder metadata 当 child 实际环境。来源与采集时点仍由 R04 处理。
- R04-B 读取 R02-R 的实际捕获合同：原始哈希与脱敏副本分开，安全替代不能
  恢复秘密值；有界失败的 omitted capture 必须保留 warning，不能解释成完整证据。
- 已有 State parent/child 路径碰撞留作 backlog；本批 consumer fixture 使用
  独立声明与绑定字段，避免把该既有问题混入当前验收，不在 R03 中重写
  State 层级模型。
- 未修改 judge Issue #9 漂移提案、schema、core engine/redaction 或依赖。
  历史资源检查见 [pending-resource-validation](../pending-resource-validation.md)，
  VAL-R01–R03 继续 BLOCKED。本批不是里程碑或发布，不用 CPU 合成 child
  代替正式 GPU、付费 judge 或成功 gated-file Gate B。

报告冻结提交前的本地证据；最终 main push 和对应 HEAD 的五平台 CI 在完成后
单独核对，不将计划运行或历史 CI 写作本次通过。
