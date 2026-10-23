# R07-C D-M-V / P-A：Poetry 显式 version 字段提取边界

日期：2026-10-23。状态：**P-A 准备完成，PROPOSED；推荐 A，未接受、未实施，规范补丁未应用**。
本报告是推送前快照；精确最终 main HEAD 的五项 CI 在交付时另核。不发布版本。

## 任务和基线

从干净 main `237cd903fde777ede75a415bd75f2dc592ac5d7a` 开始，经7897进程级代理 git pull --ff-only，exit0 / Already up to date。
[当前计划](../plan/README.md)、[政策任务](../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md)及
[前项 D-M-E P-B](2026-10-23-r07c-environment-pip-pb/README.md)指向本项独立 P-A。
D-M-E产品a221e9d、前项收尾237cd90及其[历史CI5/5](https://github.com/EnumaElish123/ReproLLM/actions/runs/39945849254)已完成；不代替本轮新结果。
用户“继续执行下一步”授权推进本项准备，未把旧接受记录扩为新政策批准。D-M-V仅为R07-C局部标识。

当前规范 §12.3.7 明确排除此字段，实现与规格一致。本项不宣称修复既有规范违背。
仅增加提案/证据/报告并同步三处活跃计划；产品、测试、正式工具、CI、现行规格、schema、依赖、版本、gold、旧提案和报告保持。
[基线](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/delivery-baseline.json)绑定524受保护输入；完整14912 tracked字节清单私存。

## 推荐 A 与具体材料

[提案包](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/README.md)包含具体A/B、兼容说明、48行未来验收、精确未应用规范patch和PROPOSED决定。
推荐只在当前已遍历 Poetry 依赖 value 为dict、显式含version且值非str时，在原循环 setdefault(path, invalid_structure)。
仍调用原helper、追加原具名声明，不增加诊断；保持原line值及索引fallback，不重建version物理行位置。
不扩全文件预检，避免抢先覆盖同文件PEP621的unparsed_requirement。缺失、所有str（包括空白/范围/看似错误语法）、整体非dict、多约束数组、未遍历groups与Pipfile不触发。
transport+非str是明确纳入的字段类型决策；不宣称Poetry安装拒绝、transport优先级或隐藏exact。

[官方schema/文档](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/sources-and-scope.md)支持string字段边界及合法替代形态。
2.5.0与2.2.1 schema原件相同SHA；稳定文档访问时显示2.5。浏览2.5.0 schema曾cache-miss，独立HTTP200原件保留，未把下载冒充那次浏览成功。
它们不能证明错误字段里存在合法exact，也不能必然推出全仓SKIP。A复用D-M是明确的保守政策选择；B保留当前captured-view有界WARNING和OPEN缺口。

A必须一并接受的成本：unrelated/noncritical条目也可全仓使其余已用未获信用关键包WARNING→SKIPPED/INFO，孤立exit1→0；
默认text可PASS+skips，默认export移除原notable warning，完整JSON保留SKIP。信用→D-F/S→D-L→D-M→D-G优先级不变；独立warning仍可失败。
SKIP不授予信用、不证明完整分析。没有engine/redaction/schema的D-41变更，也不扩大grammar/reads/roots/barriers/lock association。

精确规范补丁拟新增§12.3.11并调整相关引用与排除条款；其[字节绑定](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/spec-patch-binding.json)
以当前spec SHA为前提。仅git apply --check及私有文稿副本应用核字节，现行规范未应用。
独立初审发现生成器strip丢失末尾上下文空行使首稿patch损坏；已从完整候选重生成并重绑SHA，失败与复查记录均私存。
另按审阅将“物理行”收窄为原line值和fallback保持，避免扩大修复范围。

## 当前源码观察和更正

35个Q01–Q35案例，指定03/04双重放均211/211投影断言通过、exit0、耗时0.3750385/0.3853999秒。
216238字节完整内部记录同SHA `96ce5f636d96e17881111d76c728ef8f698956336707af2867f04bd047d13877`。
先前01/02均209/211：Q26 requirements exact仍保留specifier、Q29失败Poetry锁另有原诊断，两个预期疏漏已依据源码更正。
原v1/失败完整记录/命令流均保留，总调用4次；最终预期并非全部在首次观察前盲写。
[当前行为](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/current-behavior.md)、
[全部调用/更正](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/observation-replay.json)和[完整记录](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/current-observations.json)明确区分投影gold与记录完整性。

128个源码文件前后不变、53导入模块hash绑定，producer实际读取0.7.0；36次version helper和2次Requirement调用。
真实non-Git scanner、installed_versions固定空；初始身份核对后防网络/子进程/重库导入。Q34使用明确coverage元数据seam并保留真实imports。
TOML date/time预先定义typed ISO trace，原TOML保留，JSON严格禁NaN/Infinity；没伪造TOML null。
22个匹配狭窄predicate的当前案例含15WARNING、2正信用empty、5旧SKIP；这是源分类，候选执行数0。
无CLI/engine/profile/init/export或整体exit比较，本观察不能冒充这些门PASS。

## 五项目与验证类别

独立源码盘点17724 tracked、17675当前scanner候选。五项目pin/origin/clean前后保持，48个Git命令exit0；
lm-eval/FastChat/LlamaFactory各一份pyproject完整解码并与HEAD blob同字节，原tool均无poetry；HarmBench/llm-dp没有pyproject，五项目都无Pipfile。
所有Poetry条目、显式version输入均0，只支持source-only zero-applicability，未来限定A的完整delta预期ZERO_DELTA_NOT_EXECUTED。
不把历史D-C等变化重算成本片，不更新gold。完整路径/命令原件私存，[公开源证据](../plan/reliability-2026-10-03/proposals/R07-C/poetry-version/portfolio-review.json)保留来源hash和物理section行。

本轮按[验证流程](../plan/validation-workflow-2026-10-13.md)仅做文稿链接/内容、hash/严格JSON、补丁、受保护输入、隐私和独立回读检查。
未改生成文档输入，generated freshness为NOT_APPLICABLE；本地完整产品质量门和fresh Gate A为NOT_APPLICABLE_DOCUMENTATION_ONLY，非PASS。
无里程碑/发布，资源Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE。精确本轮CI在推送后核验，不拿历史门替代。
标准diff whitespace对.patch必需的空白上下文行有误报；补丁保持原语法，另核payload无尾随空白，其余文稿执行普通diff检查。
首次两次文稿检查因独立元数据及新写收据的Windows默认CRLF停止，原记录保留；显式LF后第三次通过。7份非业务元数据的仅换行转换另记原/公开hash，合成业务记录、cases、observer均原字节保留，未删改业务字段。

## 资源和接续

VAL-R03五份原metadata缺失／最近authenticated HF403仍为历史BLOCKED；本轮未新作资源预检。VAL-R01仍绑定948d164、R02绑定75d1b0，未重跑GPU或paid judge。
A02独立试用反馈PENDING；A03身份/角色/组织和提交授权待输入，未提交外部issue/申请。
更广R07-C保持OPEN，不调用付费API、不使用GPU、不发布版本。

下一步对具体A、精确补丁、全仓成本裁决；接受后执行P-B：先RED回归，再原caller最小实现，GREEN、最终质量门、fresh五项目Gate A和受影响验证、main提交推送及精确CI。
本P-A合入不自动接受或实施新政策。
