# R07-C D-M-PF：Pipfile 显式 version P-A

2026-10-24。**PROPOSED / REVIEW_READY**，推荐A；尚未接受、未实施。基线 `d7bc16b3a4f855ccd35546966ee6424dcd47cc96`。

- [具体A/B](proposal.md)、[兼容成本](compatibility.md)、[45组未来验收（未执行）](acceptance-cases.md)
- [精确未应用规范补丁](spec-proposed.patch)、[字节绑定](spec-patch-binding.json)、[决定](decision.json)、[未提交issue草稿](spec-issue-draft.md)
- [当前38例及重放](current-behavior.md)、[最终完整记录](replay-02-observations.json)、[首次失败](replay-01-observations.json)、[观察收据](replay-summary.json)
- [五项目影响](portfolio-impact.md)、[来源摘要](portfolio-source-summary.json)、[独立回读](portfolio-review.json)、[行为oracle独立审阅](behavior-oracle-review.json)
- [官方依据](official-sources.md)、[设计](design-review.md)、[具体草稿独立审阅](draft-review.json)、[补丁检查](patch-check.json)
- [文稿检查](document-checks.json)、[来源/公开边界](source-index.json)、[校验和](SHA256SUMS)、[会话报告](../../../../../dogfooding/2026-10-24-r07c-pipfile-version-pa.md)

建议A只在已有Pipfile两节原循环，对dict+显式version+非str记录既有invalid_structure；helper allow_bare=False、原声明/信用/line fallback/先因保持。
官方类型边界不能推出隐藏exact或全仓SKIP必然；必须独立接受repository-wide WARNING→SKIPPED、孤立exit1→0和text/export成本。
Poetry D-M-V的批准不适用于本片，当前规范与实现一致。本轮候选执行0，现行规范、产品、测试、CI、工具、依赖、schema、版本、gold与历史记录不变。
文稿检查通过不等于本地完整产品门/Gate A PASS；它们为NOT_APPLICABLE_DOCUMENTATION_ONLY。无里程碑或发布，资源Gate B不激活。精确推送HEAD的五项CI交付另核。
下一步先裁决A及精确补丁和成本；接受后P-B先RED，再最小实现、最终质量、fresh五项目Gate A及受影响验证。更广R07-C、资源、外部反馈保持OPEN，不发布版本。
