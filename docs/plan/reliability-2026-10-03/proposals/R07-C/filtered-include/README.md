# R07-C D-I / P-A：候选过滤后的 requirements include

日期：2026-10-28。基线 `e3aa653`。状态 **PROPOSED**，候选政策执行0。
上一批配置深度修复和精确e3aa653五项CI已通过；本片尚无具体接受记录。

- [方案A/B、兼容成本和边界](proposal.md)
- [实现patch](implementation-proposed.patch)、[规范patch](spec-proposed.patch)、[规范节预览](proposed-section.md)
- [字节绑定](patch-binding.json)、[PROPOSED决定](decision.json)
- [24组未来验收设计](acceptance-cases.md)、[未来Finding字面设计](future-finding-example.json)
- [24现行案例与27CLI观察](current-behavior.md)、[五项目源码与条件预期](portfolio-impact.md)
- [独立静态审阅](design-review.md)、[已完成前批基线](delivery-baseline.json)
- [本地spec issue草稿](spec-issue-draft.md)

推荐A只记录现有candidate=False的已达supported include target，不增加读取、候选或预算；
逐包消费放在全部旧信用及D-F/S、D-L、D-M、D-G之后。
必须另行接受全仓保守SKIP、目标可能不存在和孤立门1→0的成本；这不是隐藏pin或完整性证明。

24现行案例、27真实CLI（35总记录）、1份完整重复报告比较及独立静态审阅均完成；
五项目无include边只支持条件零delta，未来验收尚未执行。完整记录与观测限制见对应材料。
本批P-A的产品质量门/Gate A/B为NOT_APPLICABLE，不借用上一批成功作为新政策PASS。
接受具体两份patch后才实施P-B，并运行最终完整质量及fresh五项目、推送main与精确HEAD CI。
