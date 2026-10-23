# R07-C D-M-P：PEP 621 依赖字符串提案

日期：2026-10-23。状态：**PROPOSED / REVIEW_READY**；推荐 A，未接受、未实施。
基线 `cc6e891c07aea9c8d585e80e2a14eff3b98b32af`。D-M-P 是 R07-C 的局部标识，不是新架构决策。

- [具体 A/B](R07-C_pep621_strings.md)、[兼容性](compatibility.md)、[38 项未来验收](acceptance-cases.md)
- [未应用规范补丁](spec-proposed.patch)、[本地 issue 草稿](spec-issue-draft.md)、[决定](decision.json)
- [当前输入/预期](cases.json)、[原产品完整观察](current-observations.json)、[观察器原文](current-observer.py.txt)、[观察边界](current-behavior.md)、[重放收据](observation-replay.json)、[版本元数据修复](metadata-repair.json)
- [五项目影响](portfolio-impact.md)、[源字节绑定](portfolio-source-evidence.json)、[官方依据](sources-and-scope.md)
- [设计审阅](review-design.md)、[受保护基线](delivery-baseline.json)、[文稿检查](document-checks.json)、[SHA256SUMS](SHA256SUMS)
- [会话报告](../../../../../dogfooding/2026-10-23-r07c-pep621-strings-pa.md)

只准备两个 PEP 621 入口的真实解析失败政策，不把共享 helper 的全部 unparsed 统一分类。
原产品观察不等于候选 A 执行；候选政策执行数 0。产品、测试、正式工具、现行规范、旧证据和版本均保持。
本片按[纯文稿验证流程](../../../../validation-workflow-2026-10-13.md)，本地完整产品质量门、
fresh Gate A、资源 Gate B 均 **NOT_APPLICABLE**，不是 PASS；精确提交的五项 CI 另核。
具体接受 A 及补丁后，P-B 才先 RED、实施、GREEN、最终质量门、五项目及受影响验证。
不调用付费 API，不使用 GPU，不发布版本，不对外发帖。

当前观察 P01–P24 与未来验收 P01–P38 分属各文件命名空间，不是一一映射或同一套已运行测试。
