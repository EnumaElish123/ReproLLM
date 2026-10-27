# R07-C D-M-CS P-B：Conda 保留名称但丢失限制条件

日期：2026-10-27。状态：产品及本地适用验收通过；精确交付提交的CI在推送后另行核对。
基线`17daaaafc1b6f49bb8b71cd30da577fa6c451ad2`；产品任务
`1607ee0f349a402c709c7fb49e25ad6f117f02a1`；测试预期补齐及最终验收候选
`bd74330aecbedf681df08553a56be34f594555b4`，仍为未发布0.7.0。

维护者明确回复“接受A及具体补丁，执行P-B（推荐）”。
[独立接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/decision-accepted.json)
绑定具体实现、规范补丁及全仓成本；原[P-A材料](../../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/README.md)
和PROPOSED快照共29份保持原字节。

## 实施与兼容成本

产品及规范精确匹配已接受补丁。只在内部Literal增加`unparsed_conda_specifier`，
并在原native Conda helper已有的specifier-placeholder赋值分支`setdefault`。
原name匹配及两个CE早退已排除，非空rest未匹配原VERSION或RANGE才到达此处。
未改regex、outer strip、原rest、六种数字RANGE（含原`~=`形状）、声明/占位/exact、
原诊断、dependencies条目序号（非物理行号）、逻辑路径、读取/候选/图、barrier或锁关联。
structure precheck仍在遍历前，实际entry首因保持；没有新增Conda语法解析或求解。

继续使用信用→D-F/D-S→D-L→D-M→D-G的现有优先级，不改规则或engine。
即使明确非精确的wildcard/compound或无关非关键条目触发，也可经全仓D-M使其他
剩余已用、未获信用关键包WARNING→SKIPPED/INFO；孤立WARNING或提升CRITICAL门可1→0。
默认text可PASS加skipped，默认export可少notable warning；完整JSON保留SKIP。
这是已接受的保守取舍，不是隐藏pin、Conda有效性、完整分析、安装或复现成功证明。
未改scanner/redaction/persisted schema/依赖/规则ID/历史产物/版本/gold。

## 测试先行与独立预期

按已接受的public scan、真实规则和CLI接口，先各写tracer，旧实现有效RED，
再应用精确补丁取得GREEN；后续分组补回归。新增125 core、56 rule、49 CLI，
共230项。最终五份旧测试同步51个受影响政策预期，保留完整声明、诊断、信用、presence
及原读取/图断言；85项environment-pip核心回归未改。

最终八份定向测试546PASS，pytest42.10秒、外层42.579673秒；已有deps/结构/env/pip
基础回归551PASS，pytest5.00秒、外层5.385937秒。受影响ruff、format和类型检查通过。
相同最终八份测试在冻结旧源码上实际为193个AssertionError、353PASS，无ERROR/SKIP，
外层36.194425秒；143份包文件及125个实际导入模块的来源/字节守卫通过。
这不是将旧新摘要相减，也未用候选输出生成预期。独立审阅分别复读core、rule与CLI；
38组的具体测试与有限证据映射见[acceptance-map.json](acceptance-map.json)，
其引用的完整只读回读及原始收据保持在私有会话目录。

首轮完整质量在`1607ee0`发现此前定向范围遗漏的两项P14跨管理器旧预期：
native `torch==`先于pip失败，已接受的CS首因应优先；旧期待仍为`unparsed_requirement`。
首轮实际5,116PASS、2FAIL、2slow deselected，pytest911.31秒；只完成3/24命令，
保持FAIL原件，不写成质量门通过。`bd74330`仅改这两处environment期待值，
该94项模块94PASS，对冻结旧源则2个AssertionError、92PASS，无ERROR/SKIP。
原八文件546/193/353证据保持原范围，不与94项模块重复计入最终全套数。
产品全部143包文件及规范在两个候选间逐字节相同；以下旧定向和CS-A36证据
保留其初次任务身份，最终完整质量及五项目则绑定`bd74330`。

规则模块七份legacy Python覆盖视图是手动构造的内部fixture，另四项使用真实畸形Python造成gap；
CLI另有一个真实syntax-gap用例，不将手工视图冒充真实不可用扫描。指定run的完整export使用typed静态v1 RunRecord，
非空lock及不同的当前/捕获manifest、lock、observed值，核对来源优先级与历史文件原字节；
它是消费者保真检查，不是本轮新运行child。此处直接核默认模板，通用模板另由最终质量门覆盖。

CS-A36在初次任务`1607ee0`按冻结输入及唯一预期差异执行：旧、新各一次隔离进程，每进程两份固定输入，
共四次真实`scan_dependencies`调用。每例观察4次native helper、5次Requirement、15个graph节点、
3个closure、16次读取、15次候选检查及2次分析列表；143份源码中仅deps接受变化，
其余142份一致，实际导入模块来源守卫通过。唯一完整capture差异是main首因
`unparsed_requirement`→`unparsed_conda_specifier`；control不变，零忽略字段严格比较通过。
错误源码在导入/创建输入前拒绝，保存的graph.readable故意改写被检出；未替换产品协作者。
这是两份有限输入的图检查，不是38组或完整语言的图状态证明。

LF/CRLF/native换行检查以实际写入bytes为基线，三次采集及历史输入前后逐文件比较。
另一个外部负例仅包装测试自有Scanner adapter，在真实读取后故意改写自有CRLF输入，
最终bytes断言按预期1FAIL，无准备错误，产品/测试源码保持不变；不将此负例当政策RED。

## 最终会话验证

在干净detached候选工作区用`uv sync --locked --dev --offline`安装41份锁定轻量包。
先核对Git兼容shim、分支初始化能力、工具版本、源码/安装来源和22份离线wheel缓存。
在最终`bd74330`输入上的一次完整质量门24项全通过：5,118 tests PASS、2 slow deselected、无FAIL/ERROR/SKIP；
security 361PASS，覆盖率94.56128699%，redaction全语句及分支覆盖。
pytest报告914.1秒，质量层墙钟1097.230216秒；全部候选输入前后字节一致。
还包括lint/type、schema与生成文档freshness、examples、自审计、wheel全部包载荷、
隔离非editable安装后13项检查/26条命令。通用执行器历史任务标签未重写；本轮wrapper、
精确候选commit和完整inventory共同绑定D-M-CS的实际运行。
隔离命令中的三个失败路径按预期退出1并通过验收；构建时manifest的PENDING原值保持，
结束后的distribution PASS用manifest哈希关联，不回写旧构建收据。
第二次wrapper收据的两个展示字符串仍写candidate，实际ROOT/解释器、readiness、
逐命令来源和inventory均为candidate-final；单独勘误保留原件，不据展示字符串推断运行路径。

fresh五项目Gate A：50命令、31检查、10份完整JSON，墙钟85.319777秒。
受影响消费者：130命令、111检查、15份完整JSON，另15份init文件及5份默认export
按完整bytes比较，墙钟222.242005秒。合计180命令、142检查、25份完整JSON；
五个pin/origin/clean正确，完整profile/hints/paths/findings、默认及详细诊断均符合独立预期，
gold delta为空。验收指符合完整预期，保留上游既有FAIL/SKIP；各层耗时不冒充整会话墙钟。

复用57份oracle逐字节核对冻结Git来源及已接受D-C独立修订；86项纯比较/adapter控制
在候选执行前通过，预期未从候选输出更新。五项目supported Conda环境文件为0，
零适用性不代替合成触发回归，也不免除fresh Gate A。
完整审计比较用既有`compare_gold.py --audit-metadata`，仅忽略根generated_at/reprollm_version；
候选版本另由来源守卫核验，其余JSON按全部类型、顺序及字段严格比较。
init/export和诊断文本只采用已预检的有限可移植路径归一化，未忽略任意正文。

Gate B为`NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE`。没有GPU、Hub、付费请求或发布动作；
VAL-R01/R02和公共模型VAL-R03的旧结果保持各自候选，不改绑为本轮通过。

## 证据与接续

早期准备更正保留原件：archive目录守卫在提取前拒绝；旧表编辑定位失误、rule草稿
放置错误、CLI的换行/backtick预期和无效run-id fixture均在有效源码绑定RED前纠正。
补验runner一次未设置当前源码优先路径，被来源守卫在pytest前拒绝；原stdout/stderr保留，
修正外部runner路径后才有上述94PASS。准备错误、格式问题不计作政策RED，没有借机改产品边界或oracle。

公开[session-checks.json](session-checks.json)提供完整摘要；
[source-index.json](source-index.json)以相对标识、大小和哈希引用保留的私有原始命令、
收据、JUnit、coverage、观察器、验收映射、严格比较及独立复核。
哈希只能标识原件，不能独立重现未公开正文；公开包不复制凭据、机器身份、权重或生成内容。
用户README、docs/index及additional-cases-gold三份原修改保持字节，不纳入本轮提交。

报告提交时尚未推送，精确最终HEAD的五项官方CI及Ubuntu3.12必需步骤在交付时另核，
结果记入私有CI收据和交付回复，不预先声称通过。
更广R07-C仍OPEN；Conda其余grammar、遗漏use/listing/framework和充分性证书不因本片关闭。
后续继续按执行总则准备独立、具体的相邻P-A；本轮接受不扩展到其他新合同或版本发布。
