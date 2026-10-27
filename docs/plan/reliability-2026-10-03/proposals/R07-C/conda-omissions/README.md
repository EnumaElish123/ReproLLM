# R07-C D-M-CE：Conda 字符串省略分支 P-A

日期：2026-10-27。状态：**PROPOSED / REVIEW_READY**，推荐 A；未接受、未实施。
基线：`38b59cc41f8870b63f00321b8278cfc88b14a86b`。D-M-CE 是本任务局部标签。

本包执行维护者已指定的下一步 P-A，准备 Conda 声明提取问题的具体合同。
当前实现符合现行规范；新政策需要独立接受，不沿用 Poetry/Pipfile 的接受记录。

- [具体 A/B 与兼容成本](proposal.md)
- [36 组未来验收，均未执行](acceptance-cases.md)
- [精确实现补丁](implementation-proposed.patch)、[规范补丁](spec-proposed.patch)、[字节绑定](patch-binding.json)、[临时副本检查](patch-check.json)
- [当前行为与重放](current-behavior.md)、[冻结输入](integrated-cases-frozen.json)、[完整当前记录](current-observations.json)、[观察器文本](current-observer.py.txt)
- [独立五项目源码证据](portfolio-source-evidence.json)、[影响说明](portfolio-impact.md)
- [官方依据](official-sources.md)、[来源设计复核](design-review.md)、[验收设计复核](review-design.md)
- [具体补丁复核](concrete-patch-review.json)、[当前观察复核](current-observation-review.json)
- [决定状态](decision.json)、[未提交 issue 草稿](spec-issue-draft.md)、[文稿检查](document-checks.json)、[外部证据索引](source-index.json)
- [会话报告](../../../../../dogfooding/2026-10-27-r07c-conda-omissions-pa.md)

A 仅为现有 native Conda helper 的两个提前返回分支新增内部 `unparsed_conda`：
原 name-pattern fullmatch 没有匹配，或原 rest 以 `::` / `/` 开头。
不扩语法、不推断包名、不从 unsupported 诊断触发；所有仍生成声明的 range／复杂
后缀保持原行为。产品只需 Literal 增项和两处 setdefault；无 engine/schema 改动。

代价明确：空白或无关包的省略也可能通过既有全仓 D-M，把其他已使用但未获信用包
的 WARNING 改为 SKIPPED/INFO；孤立 WARNING／提升后 CRITICAL 门可从 1→0。
默认文本可显示 PASS+skipped，默认 export 可少一条 notable warning；JSON 保留 SKIP。
这不是隐藏 exact、完整分析或复现成功的证明。

本 P-A 已运行 32 项独立当前 helper 观察和 36 项当前解析／raw 规则观察；
后者 216 条 literal 断言通过，三个新目录产物逐字节一致。
这些不是候选策略执行、RED/GREEN、engine/CLI 验收或 fresh Gate A。
未来候选执行次数为 0。五项目 supported environment 文件均为 0，预期完整 delta 空；
零适用性不能验证新触发分支，需未来合成回归覆盖。

正式源码、规范、测试、schema、依赖、工具、CI、版本、gold 与历史包保持。
按验证频率，完整本地产品门/Gate A 为 NOT_APPLICABLE_DOCUMENTATION_ONLY；
没有新里程碑/发布，资源 Gate B 不激活。当前资源补验已完成的事实保持原候选绑定。
P-B 接受后按测试先行、一次最终完整门、五项目 Gate A 与受影响扩展推进。
