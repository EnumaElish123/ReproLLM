# 未提交 spec issue 草稿：R07-C D-M-CE

建议标签：`spec`。状态：仅草稿，未发送 GitHub issue。

当前 Conda 提取器在两个原 early return 丢弃已经访问的 native 字符串，只保留
固定 unsupported 诊断。规范目前把这类额外语法边界留为 OPEN；不能直接改变
`env.llm_critical_deps_pinned` 的非空 WARNING 合同。

提议：只为这两个分支增加内部 `unparsed_conda`，复用既有 D-M；保留所有已采集
声明、诊断、读取、信用、配对和先因。完整 A/B、成本、反例与精确规范/实现差异
见本目录 proposal.md、acceptance-cases.md 及两份 proposed.patch。

需裁决：是否接受 A、精确补丁和全仓保守 WARNING→SKIPPED、孤立 exit1→0 成本。
Conda 有效性、完整 MatchSpec 支持与广义 R07-C 不在此范围。
