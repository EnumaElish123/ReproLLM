# R07-C 最终合同实施与开发方案收尾

日期：2026-10-29。最终验收候选`3157ae7a9b66bccb13d07195e60845ce603dd76a`，产品提交`7e578090ac1830a507fd16ec65d43041a14cba7a`，接受记录提交`d68f036`。
本轮23项工程／策略开发任务的实现与适用本地验收已完成；最终交付HEAD的五项CI在报告推送后另核。
当前版本仍为未发布0.7.0。本报告保留提交时的CI待核快照，推送后用独立闭环确认，不制造文稿提交循环。

## 已接受的有限合同

维护者明确接受“A与三份补丁，完成全部开发收尾”，见
[具体记录](../../plan/reliability-2026-10-03/proposals/R07-C/final-coverage/decision-accepted.json)。
依据规范§12.3.16，69条builtin及generated规则均有处置，6条消费实际typed静态缺口。
已捕获安全违规、高置信度profile违规、正向存在性证据、exact／合格lock信用和所有旧SKIP优先级保留。
仅指定缺证据分支改SKIPPED/INFO；孤立CRITICAL/WARNING或提升门可1→0，默认text/export沿既有显示合同。

实现只在既有枚举、读取、解码与分词失败处记录内部事实，不增加读／重试／遍历、语法或预算。
依赖decoder仅窄捕获RecursionError为parser_limit，不新增吞MemoryError/任意ValueError。
不改engine/redaction/持久化schema、规则ID、默认严重度、依赖、版本或历史产物。
9份产品postimage全等接受的机械重基；8份原样，integration模块只另携带独立Makefile修复，精确AST归一化复核通过。

这是captured eligible-view合同，不是全文件系统／任意语法／动态use／执行完整性或通用充分性证书。
规则依据评估时已捕获事实，后续lazy读取不追溯旧结果；有意排除及支持范围外不是观察失败。
不把每个body缺口都全局SKIP：无法合格的pyproject或requirements闭包仍保留具体旧资格结论。
这些边界经本次具体接受后接替早期宽泛OPEN描述，不能再当成隐含待开发任务，也不能称已验证支持那些能力。

## 开发与实际回归

| 提交 | 范围 | 实际旧／新对照 |
|---|---|---|
| f980e36 | 任务YAML composition递归恢复 | 11新例，旧8F/3P→新11P；原生audit/list退出3→0 |
| 60d2087、28de938 | shell独立注释续行，保留Makefile旧语义 | 10例旧6F/4P→10P；Makefile9例旧4F/5P→9P |
| 7e57809 | 六规则有限政策与decoder内部原因 | CLI30旧20F/10P→30P；core14旧8F/6P→14P |

合计74新增case。framework最终相关集合69个独立case；政策相关339与668是两组实际调用集合，
相互有重叠，不能把它们直接相加当独立测试总数。CLI旧20F分别为18业务断言、1旧递归异常和1新增API缺失；0pytest ERROR/SKIP。
最终CLI草稿有一次继承闭包期望错误：safety已继承inference，改用未被包含的peft/finetuning验证正违规。
只修测试fixture并用最终字节完整重放旧／新，原稿与首29P/1F保留，产品未迎合测试改动。

首轮质量因独立复核发现Makefile语义回归中止130；修正后第二轮因维护者接受最终政策、
需要合并最终源／测试而中止130。两轮均无最终PASS，未运行五项目门；原流和中断记录保持。
第三轮完整pytest实际5294P/1F：唯一老断言把坏语法pyproject的Python版本结果仍当WARNING，
与已接受的新SKIP合同冲突。仅同步这一参数的完整Finding、summary与退出码，
保留其余三种decoded结构的独立WARNING和全部恢复后断言；产品9份源码不改。
当前第四轮在最终源／测试冻结后完整通过；前述中断和失败均不作当前PASS替代。
GNU Make dry run独立确认注释续行且未执行目标配方；本机原生证明限定Python3.12.14/Linux，跨平台由最终CI确认。

## 最终完整质量门

24项检查与24份origin守卫全部通过，tracked输入前后字节一致。
实际5295 tests PASS、0失败/错误/skip，普通门另外排除2个slow；
覆盖率94.69387755%，redaction语句与分支100%。
含security、lint/type、schema／生成文档freshness、examples、自审计、wheel载荷与隔离安装故障路径。
质量层墙钟1154.855秒。 构建清单写出时的PENDING保留，最终distribution PASS另行绑定其hash；
隔离安装13检查/26命令含3个预期exit1，wheel144份载荷逐字匹配。实际离线同步41锁定轻量包并完成新readiness，
generic历史environment_synced=false只是旧metadata旗，本次真实同步与readiness另有绑定。

## Fresh五项目及前瞻差异

全部五pins/origin/干净状态核对，命令拥有产物仅在一次性副本写入，原checkouts保持。
基础50记录/31检查，受影响130记录/111检查，
list 45记录/26检查（5产品+40只读Git），
新typed 5public context采集/16检查。
合计230外层记录、184检查、460原始流，四层墙钟合计432.948秒。

25份完整JSON比较（15份AuditReport、5份dependency facts、5份requirements graph）、15份init文件、5份完整默认export及5份完整任务列表通过；
lm-eval仍13,123，其他四为空。旧57oracle保留，来源独立的前瞻派生仅LF2份变、55份逐字保持：
LF一条profile PASS→SKIP（原Python完整但7个JSON超读取上限），summary与排序相应；
其默认export依现有模板仅通过数9→8。原“export全文不变”预测已单独纠正，错误材料未回写。
LM/HB保留原Python缺口优先理由；其他4项目的完整L1与全部L0、profiles/hints/路径/行号/诊断保持。
无复制当前输出改期望或覆盖历史gold。[完整差异说明](portfolio-deltas.json)。

新tuple逐来源完整比较：lm-eval5962、FastChat0、LlamaFactory7、HarmBench1、DP0；
listing/python_version五pins均为空。旧facts投影与5次新typed结果分别验收，后者不是5次audit CLI。
typed内部132个只读Git调用单列，不重复计入230外层。
新增gap包括lm-eval自定义tag构造限制与LF/HB读取上限，不能解释为权限错误或隐藏信号必存在。

## 完成状态与保留边界

[27任务状态账本](../../plan/reliability-2026-10-03/07_Completion_Status.md)
区分23开发任务与4支持活动。最终CI与远端核验完成后，当前方案的23项开发任务可整体关闭。
A01输入与候选回放材料已有交付；A02实际独立反馈、A03身份/提交和最终发布资源验收继续分别登记，
不把作者自测或代码复核计为外部采用，也不把材料准备写成已提交申请。

Gate B为NOT_APPLICABLE：本次普通可靠性政策收尾不是原M1–M8里程碑或release准备。
没有GPU／Hub／付费调用，不重绑历史VAL-R01/R02/公开模型VAL-R03；实际release仍需同最终候选完整适用矩阵与新预算。
无版本发布、邀请或申请提交。主工作区原三份用户修改保持字节。

[session-checks.json](session-checks.json)与[source-index.json](source-index.json)只公开所选原件hash与安全摘要，
不重复分发全部raw argv／流正文；hash不能恢复未公开正文。所有准备错误、失败尝试与两个中断原件保留。
本报告之后仅追加文稿／导航与闭环，不更改已验收的产品／测试输入；最终推送HEAD五CI独立确认。
