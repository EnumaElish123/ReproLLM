# S2-A / R06-A 同名文件保留路径身份

日期：2026-10-10。前置 main：`f679570b657a1341778120e80a4cf895ed5281f0`。
按 S2 任务卡顺序执行；规范 §12.2、§13、§22。

同名文件从单值 basename 映射改为保留全部相对路径的候选列表，根文件
优先，其余按确定路径排序。依赖/manifest/四类普通 lock 均遍历支持候选，
manifest qualification 单独判断；Python 版本规则共用同一排序助手，
嵌套 `.python-version` 的来源使用实际路径。requirements 根仍保持原字典序，
保留 HarmBench nested evidence。没有新增子项目排除、lock ownership 或
跨项目覆盖政策，仓库聚合合同与 R06-B 的待决 scope 保持分离。

根合格 pyproject + tool-only 同名文件首对照实际 RED；29 初始格式矩阵
实际26 failed/3 controls passed，局部实现后29通过。新保留候选暴露的畸形
容器/锁包名/Python声明入口，以冻结 f679 与当前实现 paired 公开consumer
实证，再写失败回归并加最小类型保护；仅固定来源诊断、保留锁文件身份
与原存在性合同，不实现新的 lock 有效性或格式求解。

[完整质量门](r06a-quality.json) 14 项全部通过：2298 tests、2 既有 slow
excluded、1 既有 marker warning、总覆盖 93%、redaction statement/branch
100%、security124。pytest wall325.537秒；Ruff、strict mypy、四项生成
文档与十项 exported schema 完整集合/字节通过。沿用已验证的 Git init -b
临时 shim，不改系统 Git/依赖。

45项新增回归、270项定向测试和32项独立公开探针通过。
[TDD](r06a-tdd.json) 保留19次实际开发命令的原始退出、时长、前后SHA、
完整日志摘要；[独立审查](r06a-independent-review.json) 保留21个独立字面
场景及最初发现的真实新崩溃与修复证据。冻结时的
[candidate summary](r06a-candidate-summary.json) 仍如实记录 root gates pending，
最终状态以本报告、quality、Gate和提交后的binding为准。

[主五项目 Gate A](r06a-gate-evidence-index.json) 完整 PASS：actual=qualified100
leaf（fresh baseline45+affected55），842项完整比较/检查（180+662）全相等；
退出0共100，无失败、复用、unknown，gold delta=0。leaf时长218.770640秒
（baseline177.443956+affected41.326684），wrapper191.917560秒单列。
每项目21个独立路径身份场景，真实audit/default consumers、init/profile/hints
与offline discover完整核对。149文件source inventory前后均为
`3dd7e42f435b20f712833d6be4f38e1396a47f7311f59540230f30c5c3f80522`。
R06-G既有安全证据仅在index全部摘要、精确Git archive及保护源字节匹配后复用；
本项baseline和affected命令均fresh。

[补充 offline export](r06a-export-gate-evidence-index.json) 合格 PASS：10实际leaf
（冻结R06-G oracle5+当前consumer5），退出均0，64.138220秒；15项stdout、
stderr、完整Markdown原始字节比较全部一致，无版本/时间归一化。99项合格检查
由原89项PASS加10项独立模型/数据表完整literal controls组成；原92项检查中
3项observer false完整保留，不计入合格检查。总实际检查102，product重跑0。

验证脚本初版把仅含null字段/空params的角色占位对象视为已声明模型身份，
导致三项“not locked”词语断言失败；独立固定manifest和State的None/空字典
投影合同证明三项目不应有表行，另两项目只有已声明id且revision not locked。
[root独立复核](r06a-export-observer-root-review.json) 保存15完整字节比较与
10表格控制及源码SHA；原harness、失败summary/checks和全部raw保持不变。
纯证据校正另保留工具初次raw-versus-portable metadata断言失败；仅metadata
路径映射校正，原始字节比较及全部privacy/source/pin guards未放宽。
主Gate100+补充10共110实际leaf，所有原始输出和20个生成artifact摘要保存后，
仅删除本阶段五个disposable baseline clones。五原始pin保持SHA/origin/clean。

R05-A Python exact helpers 与 TOML source index 保持字节不变；Conda 版本
语义仍按后续 R05-B。既有 YAML declaration.line 为 dependency entry index，
与物理行不同，具名 backlog 单列；本项不声称已修复该索引。
五个原始 pin、gold、snapshot、依赖/schema/engine/redaction 不变。
提交后以完整 Git product tree 绑定验证字节，见 commit binding。
S2-A收尾报告将列三项任务提交并作为 S2-B R06-P → R05-B 的接续输入。
历史资源 VAL-R01–R03 为 BLOCKED；此 offline Gate A 不代替资源 Gate B。
