# R07-C D-M-CE P-B：Conda 省略声明的不确定性

日期：2026-10-27。状态：初次产品验收及Windows测试修订本地补验通过；最终交付CI另行核对。
基线 `582df6194de788fb4d7ba2dd2fd69854e4507d4e`；产品任务
`c9ee53d6e1e4000f5383ce9d66434bd2792396bd`，版本仍为未发布0.7.0。

维护者明确回复“接受方案 A及具体补丁，继续 P-B”，接受范围及原问题的全仓成本
见[独立接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/conda-omissions/decision-accepted.json)。
原[P-A提案及PROPOSED快照](../../plan/reliability-2026-10-03/proposals/R07-C/conda-omissions/README.md)
保留原字节，不回写成已执行的政策测试。

## 实施

产品和规范精确匹配已接受patch的目标字节。只在内部Literal增加`unparsed_conda`，
并在现有native Conda helper的两个提前返回点setdefault：原name-pattern fullmatch
无匹配，或原rest以`::`/`/`开头。没有新增解析、包名推断、读取、barrier或信用。
所有仍append的数字范围/复杂suffix、原诊断、部分有效声明、行序号和锁关联保持。
保留更早已存在的原因；native省略先于pip失败时，新原因可按已接受顺序取代旧pip原因。

沿用信用→D-F/D-S→D-L→D-M→D-G。无关/空白省略也可通过现有全仓D-M，让其他
剩余已用、未获信用包WARNING→SKIPPED/INFO，孤立WARNING/提升CRITICAL门可1→0。
完整JSON保留SKIP；默认text可PASS+skipped、export可少notable条目；这不证明隐藏pin或复现成功。
未改engine/scanner/redaction/persisted schema/依赖/规则ID/版本/gold。

## 测试先行与独立预期

已接受验收明确指定扫描结果、规则及CLI接口；按TDD先各写一条tracer：
旧实现三条均有效RED（非setup ERROR），应用精确补丁后三条GREEN。
随后逐组补回归：96 core、41 rules、35 CLI，共172新增；七个旧政策结果在两份
既有测试中同步，保留全部声明/诊断/锁存在性及调用轨迹断言。原7FAIL收据保持。
五份新/适配文件最终定向316PASS；已有deps/env基础回归376PASS；受影响ruff/format/mypy通过。

另将最终五份测试绑定到冻结旧源码，实际结果为89FAIL/227PASS、无ERROR或SKIP，
失败均为政策断言；124个实际导入模块和143份包文件的来源/字节均核验。
这不是把旧环境与新环境的汇总计数相减。三条tracer的GREEN用例耗时为pytest报告0.55秒，
没有单独记录的外层墙钟保持null。

新测试采用已接受的literal边界和完整Finding/报告/导出预期，不用候选输出生成gold。
独立审阅检查精确实现/spec字节及core/rule覆盖；CLI作者不冒充自己代码的独立审阅者，
root另审完整报告、阈值、suppression、init/hints与export字节。

CE-A30另有先冻结输入/预期的实际调用观察：旧、新源码各一个进程，各执行两份固定输入，
共四次真实parser调用。每例实际观察4次native helper、5次Requirement构造、
15个非空graph节点、3个closure及读取/候选/诊断状态；只允许预先指定的一处先因变化。
完整严格比较、错误源码拒绝和graph字段扰动检测通过；未替换parser/graph/Requirement，
不将这两份有限输入表述为36组实际图状态运行或所有Conda语法的证明。

## 最终会话门

在干净detached候选工作区用`uv sync --locked --dev --offline`安装41份锁定轻量包。
Git兼容shim哈希、init分支能力、依赖/来源及生成文档检查先于昂贵pytest核验。
一次完整质量门：24项全通过，4,888 tests PASS、2 slow deselected、无ERROR/SKIP；
security 359PASS，覆盖率94.56088561%，redaction 59/59 statements和24/24 branches。
pytest报告848.04秒，完整质量层墙钟1031.770874秒；候选输入前后逐字节一致。
检查还包括lint/type、schema及生成文档freshness、examples、自审计、wheel完整包载荷、
隔离非editable安装后的26条命令；该次收据绑定初次候选，后续测试修订另记。
fresh五项目Gate A：50命令、31检查、10份完整JSON比较，墙钟85.609611秒。
受影响消费者：130命令、111检查、15份完整JSON，另15份init文件及5份完整默认export
逐字节符合独立预期，墙钟225.352283秒。合计180命令、142检查、25份完整JSON；
profile/hints/paths/findings、默认及详细诊断均核对，五个pin/origin/clean正确，gold delta为空。
完整审计比较沿用`compare_gold.py --audit-metadata`，只忽略根generated_at/reprollm_version；
其余JSON严格比较类型、列表顺序及全部字段，候选版本另由来源守卫核验。
验收通过指符合完整预期，保留上游既有FAIL/SKIP；各层耗时不相加冒充完整会话墙钟。
跨平台CI：最终报告提交推送后核验精确HEAD。

五项目独立来源中无supported Conda环境文件，预期完整delta空；零适用性不代替
合成触发回归，也不免除fresh Gate A。复用的57份oracle已逐字节核对其固定Git来源及
既有D-C独立修订；不从候选输出更新预期。

Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE。本次没有GPU、付费API或HF
资源回放；VAL-R01/R02和公共模型VAL-R03旧成功保持各自候选，不改绑或重开。
更广R07-C、实际A02反馈、A03身份/提交条件和发布准备继续独立登记。

原README、docs/index及additional-cases-gold三份用户修改保持原字节，不纳入提交。
完整检查摘要见[session-checks.json](session-checks.json)，原始输出、失败/更正、coverage/JUnit、
观察器、验收映射及来源清单由[source-index.json](source-index.json)引用，保存在外部会话目录。
公开哈希只能标识原件，不能独立重现未公开正文；公开包不分发凭据、机器身份、权重或生成内容。
精确最终HEAD五项CI在交付时独立核对；本报告生成时尚未推送，不预先声称CI通过。

## Windows 测试修订

初次交付`79ce007`的[官方CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40458202141)
为四项成功、Windows失败；公开测试注解给出唯一新增失败：
`test_new_captures_preserve_input_bytes_and_do_not_disclose_omitted_text`。
原始报告/检查JSON/索引保留该次候选及报告生成时身份，不改写为最终CI通过。

根因是新增测试把`Path.write_text`创建的Windows CRLF文件与逻辑字符串的LF编码比较。
最小标准库对照在任何扫描前已重现差异；同一真实测试的Windows换行模拟先1FAIL，
修订后1PASS，故意实际改写文件的负例仍1FAIL。未替换产品解析器。
修订`b200e34`只在写入后保存实际bytes，再在扫描后逐文件比较；保留全局写入方式、
全部解析/隐私断言和96项用例，未改变产品、规范、gold、依赖或工作流。

依据验证流程§3，在独立干净的`b200e34`候选重跑完整质量门：24项通过，
4,888 tests PASS、2 slow deselected、无FAIL/ERROR/SKIP，security 359PASS，
覆盖率94.56088561%，redaction 59/59 statements和24/24 branches。
pytest报告839.91秒，质量层墙钟1024.211215秒；输入前后完全一致，
143包文件及隔离安装后的13项检查/26命令通过。
本修订Gate A为`NOT_APPLICABLE_TEST_ONLY`：初次`c9ee53d`产品字节及全部五项目结果
保留原身份；没有把旧产品运行声称为新HEAD的fresh重跑。最终五项CI仍须核对交付HEAD。
完整补验及失败/修订原件的哈希引用见[windows-followup.json](windows-followup.json)。
后续保真测试直接采用实际写入字节作为基线，覆盖平台原生换行。
