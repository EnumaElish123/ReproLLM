# R07-C D-M-V：Poetry 显式 version 字段 P-A

日期：2026-10-23。状态：**PROPOSED / REVIEW_READY**；推荐 A，未接受、未实施。
基线 `237cd903fde777ede75a415bd75f2dc592ac5d7a`。D-M-V 仅是 R07-C 局部标识，不是架构 D-nn。

- [具体 A/B](proposal.md)、[兼容性](compatibility.md)、[未来验收](acceptance-cases.md)
- [未应用规范补丁](spec-proposed.patch)、[字节绑定](spec-patch-binding.json)、[决定](decision.json)、[未提交 issue 草稿](spec-issue-draft.md)
- [当前行为及重放](current-behavior.md)、[冻结输入](cases.json)、[当前完整内部记录](current-observations.json)、[观察器](current-observer.py.txt)、[所有调用](observation-replay.json)
- [五项目影响](portfolio-impact.md)、[逐项目源证据](portfolio-source-evidence.json)、[独立源回读](portfolio-review.json)
- [官方依据](sources-and-scope.md)、[设计审阅](review-design.md)、[受保护基线](delivery-baseline.json)、[来源索引](source-refs.json)、[文稿检查](document-checks.json)、[公开边界](publication-review.json)、[元数据换行](publication-lines.json)、[校验和](SHA256SUMS)
- [本轮报告](../../../../../dogfooding/2026-10-23-r07c-poetry-version-pa.md)

推荐 A 只在已遍历 Poetry 依赖 value 为 dict、显式含 version 且值不是 str 时，在原 caller 中 setdefault 记录既有 invalid_structure。
不从 helper(None,None) 或非 exact 推断失败，不扩全文件预检，不改变声明或信用。缺失、任意字符串和多约束数组保持旧行为。
Poetry schema 支持这一字段类型边界；全仓保守 SKIP 是另需接受的政策选择，不能由 schema 推导为必然。

候选执行数 **0**。当前观察不是新政策测试，未来验收不是 PASS。现行规范、产品、测试、CI、工具、依赖、schema、版本、gold 和历史报告保持。
本地完整质量门、fresh Gate A 为 NOT_APPLICABLE_DOCUMENTATION_ONLY；无里程碑/发布，资源 Gate B 不激活。精确推送 HEAD 的五项 CI 交付时另核。
下一步先对具体 A、精确补丁和全仓 WARNING→SKIPPED／孤立 exit 1→0 成本裁决；接受后 P-B 才先 RED 再实施与验收。
不调用付费 API、不使用 GPU、不提交外部 issue 或申请、不发布版本。
