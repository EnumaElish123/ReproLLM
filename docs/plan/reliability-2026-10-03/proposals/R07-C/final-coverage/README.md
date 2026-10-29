# R07-C 最终结论合同方案

## 独立复核补充

Makefile与shell注释续行不同，已用独立回归及GNU Make dry run纠正，第三项修复为`28de938`。
原先已启动的质量门已安全中止130，未产生最终PASS或五项目结果，后续在新候选重跑。
[已实现修复审阅](existing-fixes-review.json)核实30项新增及合并69个独立相关案例。

原三份patch及九文件政策保持历史字节；[机械重基实现patch](implementation-rebased.patch)
仅保留这项独立Makefile修复，[AST与来源资格](rebase-qualification.json)证明六规则政策不变。
补丁尚未应用。

原“默认export全文不变”的预测有误：LF的PASS数减少1，既有模板的通过数也会从9变8。
[修正的完整字面预期](portfolio-expected-qualified.json)与[修正gold补充](gold-amendment-qualified.patch)
替代该描述；这是同一已提议summary变化的派生，不增加规则或导出实现改动。
前瞻57份oracle中2份改变（LF L1及LF默认export），55份字节保持，原57份均不改。

[资格边界说明](scope-clarifications.md)明确：仅改变六规则指定分支。
无法合格的pyproject、失败的requirements闭包等仍按旧资格合同可能产生FAIL/WARNING，
不表示已证明物理文件不存在。具体决定仍PENDING，新政策执行仍0。

日期：2026-10-29。状态：**PROPOSED，未应用，未来政策执行 0 次**。
本方案基于两项现行合同修复后的源码；精确提交与九份源码前后哈希见
[source-bindings.json](source-bindings.json)。接受前继续保持现行规范。

建议采用 A：把 R07-C 剩余范围合并为有限的六规则政策，一次完成开发与验收。
不再按单个包管理器的任意语法不断追加任务；同时明确受支持视图的边界，不授予全仓完整性证书。

## 已完成的独立工作

任务 YAML composition 的 RecursionError 已作窄捕获：11 新例在旧代码 8F/3P、修复后 11P，
原生 audit 与任务列举旧退出3、新退出0。整行 shell 注释的尾反斜线不再吞下一行命令：
10 新例最终字节旧6F/4P、新10P，恢复真实命令的物理行号。
两项均属于现行规范 §§13–14 的修复，已作本地暂定提交；最终共享质量门与五项目验收仍需执行。

本次现行行为观察为8个合成案例、9次公共run_audit，覆盖枚举失败、读取/解码/分词失败、
已有正向违规及隐藏未知use。额外一次为作者预期排序修订后的重放，原失败保留。
五项目来源盘点发现lm-eval有5962个自定义tag使配置值构造失败，但任务node composition成功；
LlamaFactory有7个JSON、HarmBench有1个JSON超过现行512KiB读取上限；FastChat/DP未见这些缺口。
这些是旧源码观察/来源推断，不能代替未来政策验收或fresh Gate A。

## A 的具体范围

[69条规则处置矩阵](rule-dispositions.md)列出每个当前ID；6条消费新的已观察typed缺口：

| 规则 | 处理 |
|---|---|
| dependency_manifest_present | 有存在性证据保持；枚举失败时不下“没有manifest”的CRITICAL结论。 |
| lockfile_present | 保留格式锁存在性及合格requirements闭包；枚举失败且未找到时SKIP。 |
| llm_critical_deps_pinned | exact/合格信用及全部旧SKIP先赢；剩余包在枚举有缺口时SKIP。 |
| python_version_declared | 保留原有正证据；枚举或相关源实际读/解码失败时不推断缺失。 |
| secret_files_ignored | 已发现的禁止文件继续FAIL；枚举失败时空结果改SKIP。 |
| profile_detection_mismatch | 保留已发现的high违规；已知检测缺口时缺证据/空PASS改SKIP，旧Python理由优先。 |

生产者只记录实际失败，包括Git枚举、walk错误、已捕获stat/根resolve/环境marker失败；
实际README/config/framework读取、既有解码或shell分词失败；以及已采集的依赖失败事实。
单独目录名启发式walk失败只影响检测，不追溯早先文件列表。规则只使用评估时已观察到的事实，
不宣称原子快照。未访问的早停候选不是失败；有意排除、size范围外和未支持语法维持文档边界。

依赖文档六处decoder只新增RecursionError恢复，内部标parser_limit，复用D-M/D-F与原barrier；
不吞MemoryError/任意ValueError，不增加读/重试、语法、预算、求解器或第三方重依赖。
新Gap及parser_limit仅为内部事实，不改engine/redaction/持久化schema、规则ID、版本或默认严重度。

精确差异：[实现](implementation-proposed.patch)、[规范](spec-proposed.patch)、
[前瞻gold补充](gold-amendment-proposed.patch)。补丁可适用性与静态语法/格式检查不是未来实现已通过。

## 明确接受的兼容代价

缺证据CRITICAL/WARNING或用户提升的CRITICAL可能改为SKIPPED/INFO，孤立门可退出1→0。
已观察的禁止文件和其他具体违规继续有效。无关子项目、已知非精确条目或坏配置也可能保守影响
profile结论；不声称缺失内容必含隐藏证据。默认text可能显示PASS与skip计数，默认export可能
少一项notable缺证据警告；完整JSON保留SKIP。此成本不能由“继续开发”的总体授权代替接受。

五项目前瞻差异仅LlamaFactory初始化L1的一条profile PASS→SKIP及对应排序/summary；
其余完整结果、任务、manifest与默认export预期不变。详见[字面预期](portfolio-expected.json)。
历史57份oracle、原输入pin和既有资源成功身份保持。

## 关闭条件与选择

接受后先写独立验收测试并在旧源码实际失败，再原样应用具体补丁、完整定向回归，
最终一次完整质量门及fresh五项目audit/init/export/list与完整差异比较，推送main并核对最终五CI。
69条规则及generated规则均有明确处置、既有正向违规不压制后，才将当前R07-C标为完成。
文件系统全知、所有包管理器语法、动态import/执行完整性、通用充分性证书均为明确非目标；
这是具体关闭边界，需要一并接受，不能靠报告自行把未完成内容移走。

A：接受有限六规则合同、两项补丁、前瞻gold补充及上述关闭条件，完成P-B。
B：保持现规范，交付两项现合同修复；更广R07-C仍OPEN，另行设计其他策略。

普通静态会话不激活里程碑/发布资源矩阵；GPU、judge、discover、metadata成功仍绑定各原候选。
A02实际独立反馈、A03身份/提交与版本发布各自登记，本方案不授权发邀请、提交申请或release。

具体决定依据：[执行总则§5.9](../../../00_Execution_Guide.md)、
[现规范](../../../../01_specification.md)§12.3.1、§12.3.2及§12.3.15明确保留当前分支。
[原始观察索引](source-index.json)冻结357份本轮原件；[独立静态复核](independent-review.json)通过。
索引不分发原始流正文，hash不能恢复未公开内容。当前不把提案写作已接受或全部开发完成。
