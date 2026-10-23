# R07-C D-M-E：environment 嵌入 pip 提取失败 P-A

日期：2026-10-23。状态：**PROPOSED / REVIEW_READY**；推荐 A，未接受、未实施。
基线 `72bf2fc150b8b00cc32a5a75d2ffa13387edbc3e`。D-M-E 是 R07-C 的局部标识，不是架构决策编号。

- [具体 A/B](R07-C_environment_pip_strings.md)、[兼容性](compatibility.md)、[未来验收](acceptance-cases.md)
- [未应用规范补丁](spec-proposed.patch)、[未提交 issue 草稿](spec-issue-draft.md)、[PROPOSED 决定](decision.json)
- [当前输入](cases.json)、[当前源码观察](current-observations.json)、[观察器](current-observer.py.txt)、[行为边界](current-behavior.md)、[两次重放与更正](observation-replay.json)
- [五项目影响](portfolio-impact.md)、[独立源证据](portfolio-source-evidence.json)、[核查补充](portfolio-review.json)
- [本地来源 hash](source-refs.json)、[公开范围核查](publication-review.json)、[元数据换行说明](publication-lines.json)
- [官方依据](sources-and-scope.md)、[独立设计审阅](review-design.md)、[受保护基线](delivery-baseline.json)、[文稿检查](document-checks.json)、[校验和](SHA256SUMS)
- [本轮报告](../../../../../dogfooding/2026-10-23-r07c-environment-pip-pa.md)

本轮只完成计划要求的 P-A。当前 environment pip 非空字符串经 strip 后的既有 Requirement 调用失败，
目前只保留诊断；A 提议通过既有返回值记录内部 unparsed_requirement，复用 D-M。
空白仍跳过，不执行或扩展 pip/Conda、include、comment grammar，不猜包名，不改变有效声明和信用。
解析器未提取不等于 pip 会拒绝，也不等于整个环境文件无效。

本轮当前源码观察不是候选 A 的测试。候选政策执行数 **0**，现行规范、产品、测试、CI、正式工具、
依赖、schema、版本、gold 和历史记录原样保留。本地完整产品质量门、fresh Gate A 和资源 Gate B
按纯文稿类别记 NOT_APPLICABLE，不记 PASS；本次精确提交的五项 CI 仍在交付时核验。
具体接受 A、精确补丁及全仓 WARNING→SKIPPED／孤立 exit 1→0 成本后，下一次 P-B 才先 RED 再实施。
不调用付费 API、不使用 GPU、不对外提交 issue 或申请、不发布版本。
