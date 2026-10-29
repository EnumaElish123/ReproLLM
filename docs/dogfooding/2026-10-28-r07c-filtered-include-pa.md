# R07-C D-I / P-A：filtered include 的有界方案准备

日期：2026-10-28。基线e3aa653；上一批5项CI及Ubuntu3.12十二个必需步骤已成功。
当前P-A状态PROPOSED；[具体方案与补丁](../plan/reliability-2026-10-03/proposals/R07-C/filtered-include/README.md)
可审阅，但未应用到产品/规范，没有具体新政策接受，future executions=0。

独立范围审阅确定：原candidate=False的已达supported target既不是D-M正文读取失败，
也不是D-G缺最终节点。推荐独立私有拒绝set+final readable-parent include交集，
消费顺序放在全部旧信用和D-F/S、D-L、D-M、D-G之后；不增加读取、候选、预算或语法。
A要求接受全仓保守SKIP、目标可不存在、无关项目影响以及孤立WARNING/CRITICAL门1→0；
B保留现有WARNING。engine/scanner/redaction/schema/默认严重度/依赖/版本/gold均不改。

两份patch的只读apply-check、before/after字节绑定、内存postimage/AST和Ruff静态检查通过，
没有导入或执行候选政策。独立审阅0阻断项；新tuple/collector投影和实际symlink/marker条件
限制已写入未来验收。24组未来验收只是设计，不能称已通过。

现行24case先冻结literal再运行，27次真实CLI（24JSON+1repeat+2现行D-M文本）符合预期。
连同Git与完整重复报告比较共35记录；原34计数保留，额外1次Git追踪查询单列。
逐case完整目标finding、完整stderr诊断、detected profiles、level/target/exit和bytes通过。
24份完整report只私有保存；权威完整AuditReport比较仅C01首次/重复1项，两根元数据豁免。
没有把目标rule finding比较冒称全AuditReport独立gold；C12文本也不是D-I的未来行为。
三模块同进程origin/hash及143份Git冻结源载荷绑定，复用旧轻量解释器但不冒称新wheel安装。

五pins/origin/完整tracked/untracked状态及源码盘点完成，5份requirements原文均无supported
include；source-only条件零delta不等于新触发通过，不改历史gold或复用上批PASS作新验收。
本轮只读源码Git盘点与现行CLI观察不使用GPU、Hub、付费API或外部issue操作。

本轮文稿/提案适用文档链接、JSON/隐私、补丁只读适用性和来源一致性检查。
产品完整质量门/Gate A/Gate B均NOT_APPLICABLE_PROPOSAL_ONLY，绝非新政策PASS。
具体接受后P-B才先做公开CLI RED→GREEN、最终完整质量、fresh全部五项目与受影响命令，
提交推送main后再核精确交付HEAD五CI。当前材料先本地审阅，未冒充新的推送或CI完成。

主仓产品、测试、规范及用户三份未提交工作保持；旧1163/836原件不改。
本地原始记录和失败/准备快照按各hash保留。私有命令的机器路径不分发，公开hash不能恢复正文。
更广R07-C仍OPEN；listing/遗漏use/framework、资源边界及发布分别处理。
