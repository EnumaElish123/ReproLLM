# 2026-10-21 · R07-C D-M / P-A

状态：**下一步 D-M 的具体方案、外部补丁及条件验证已完成，仍 PROPOSED；正式产品／测试／规范未应用**。
本批接续 D-S 的一般声明正文失败分支，不关闭整个 R07-C。

## 起点与范围

基线 main `aee6488078c3435dcc33b20a68cca8bda0d0ec57`；上一批 D-S 产品 `d4f248d8` 已交付，
最终 HEAD [五项 CI 成功](https://github.com/EnumaElish123/ReproLLM/actions/runs/39564792576)。
本轮远端只读核对仍为 aee6488，未发现上一批尚未补验的工作。
main 的 README.md、docs/index.md 和原未跟踪 gold 草稿保持原状态／指纹，不纳入提交；本提案在独立 worktree 准备。

范围来自[专项方案 05 §5](../../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md#5-r07-c扫描不完整时哪些结论仍成立)
和 D-S 已保留的 OPEN 分支。见[完整提案](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/R07-C_declaration_body_failures.md)、
[具体待决记录](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/decision.json)与附带 spec issue 本地草稿。

只记录三个 manager 入口现有 read None／已捕获的文档解码错误，以及 requirements 原图实际允许并调用 body reader 后的 None。
新内部 typed 字典默认空；不从 unparsed prose 推断，不增加读取／重试／include。
既有声明、lock／exact 信用、presence、barrier、诊断和 D-F/D-S→D-L 优先级保持。
仅剩余缺 pin WARNING 在字典非空时逐包 SKIPPED/INFO，独立于 Python coverage。
按现行全仓 existential exact 合同，失败源对任何已知未获信用关键包均可能有影响；不要求局部锁关联，不赋予新信用。
工具-only 候选或无关子项目也可能保守触发；无当前关键包／全已获信用及原空结果政策保持。

## 实际验证与独立预期

| 项目 | 本次实际结果 | 完成边界 |
|---|---|---|
| 实现／规范草稿 | 两源补丁静态 Ruff、format、外部完整副本 Mypy128文件及 apply-check；独立复核通过 | 仅5函数 AST 改动，正式源／spec／CHANGELOG 未改 |
| 验收草稿 | 105新增参数例／21函数；58core、39env、8CLI；四文件静态检查通过 | 11旧结果／7函数明确修订，其余137旧定义原文及AST不变；未 collection／pytest／RED／GREEN |
| [16组条件观察](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/observations/execution-1/summary.json) | 32隔离 workers，另4文本／导出CLI调用；16份完整 JSON 仅根 T-02 豁免全部相等；112命令、224原始命令流及8展示流 | 精确外部两模块源码只在隔离进程执行；不是已应用产品或正式验收 |
| [独立实际回读](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/observations/independent-readback.json) | 从旧报告及冻结字面合同独立重建16份完整 expected；核对32 metadata、252 Git查询、180读取、38候选检查及全部源／fixture指纹 | 不导入观察器、不重跑产品／门；只对已保留实际数据比对 |
| [五项目来源](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/portfolio/source-evidence.md) | 35只读Git命令；全部 exact/clean/public pins；8声明正文、3TOML、5requirements根，无实际include，无正文失败 | 预写五份完整 L0＋facts delta 为空；10份旧完整 gold 与不可变原件逐字节绑定；非新鲜 Gate A |

条件观察墙钟 **36.356148秒**；命令累计 **35.734094秒**，不相加。外层执行36.514935秒。
独立实际回读首次0.212510秒退出0。
16组包括三个 manager decoder、manager binary、requirements根／实际安全include binary、五类include排除控制、
全仓排序与两种正向信用、D-F/D-L/D-M优先级、no-use／全已获信用、warning／critical孤立门、独立warning、suppression及默认展示。
孤立门1→0，独立规则warning门1→1；正文失败影响全仓剩余包，不能误称还保留某个未获信用包的普通WARNING。
所有旧依赖／imports／coverage事实、read/candidate/open/Git轨迹和诊断严格一致；只有指定新字典及字面 finding 转换不同。
expected在每个 proposed worker 前由旧报告＋冻结字面合同写入并固定哈希，不从候选输出生成。
默认文本／export保留全文，仅验收预写summary/notable可见性，不声称整份Markdown独立gold。

原固定项目为 lm-evaluation-harness、FastChat、LlamaFactory、HarmBench、llm-dp-finetune。
金标准没有更新；普通规则政策不触发新里程碑／release或GPU、Hub、付费API、原生 Gate B。

## 原始来源、准备停止与隐私

[完整来源索引](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/source-index.json)区分精确字节、明确物理根投影和外部哈希源。
原始记录保留于本机；可分享JSON在明确投影后规范化，文本保持其余空白、NUL路径分隔符和EOF。
外部工具／候选全源和临时命令分片保留原哈希；最终命令表与原始流只归档一次。
完整补丁、fixture字节、旧／新完整报告、字面expected、完整差异、证据路径和诊断均可审阅。

准备停止如实保留：规范范围扩到声明正文后有三处旧“format-lock”标签，经独立复核发现并仅修文字；
测试组装首个同文片段定位 guard 停止，收紧到指定函数；一处E501改相邻字面量；元数据bytes改安全hex表达。
观察器两条B905静态提示修正后冻结；启动包装器首次误认为root回执在上级目录，产品未启动，纠正准确路径后首次实际执行全部通过。
证据复制两次预检分别发现静态缓存二进制和未映射的Git可执行路径，均在写入前停止；限缩选择／补明确映射后全部预检及复制通过。
原辅助源、诊断、哈希与更正保留。部分准备诊断明确为可见工具输出转录，不假称独立原始 subprocess 流。
这些是准备停止；实际条件产品观察和独立实际回读各首次通过，没有被失败重试覆盖。

本P-A属于方案文稿：完整产品质量门和新鲜 Gate A **NOT_APPLICABLE**，正式 TDD／P-B **NOT_RUN**。
生成器正式输入未变，受影响生成文档freshness **NOT_APPLICABLE**；不能把静态／条件观察替代正式产品验收。
P-A本地快照提交不宣称最终交付HEAD的CI，接受后仍须核对真正推送提交。

## 具体决定与接续

D-M 的 [规范](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/spec-proposed.patch)、
[实现](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/implementation-proposed.patch)、
[测试](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/tests-proposed.patch)、
[CHANGELOG](../../plan/reliability-2026-10-03/proposals/R07-C/declaration-read/changelog-proposed.patch)补丁均未应用。
需要具体接受的依据是执行总则§5.9及现规范§§12.3.1、12.3.4–12.3.5：一般声明失败尚在原接受范围外。
总体继续开发授权覆盖完整方案准备；不把建议自动当规范。无需额外D-41模块审阅，因为不触碰engine/redaction/schema。

接受具体D-M后直接执行P-B：测试RED→精确补丁GREEN→完整受影响模块／静态检查，
最终一次完整质量门→全部五项目新鲜Gate A→init/L1/default export及正文失败专项比较，
任务提交＋报告收尾后推送main，核对实际最终HEAD五项CI。原PROPOSED快照保持，接受另立sidecar。
其余decoded结构／entry语法、一般include图、未知包使用／遗漏候选、listing、README/config/framework与充分证书继续OPEN。
不发布tag/PyPI，不把历史资源结果回写成本候选结果。
