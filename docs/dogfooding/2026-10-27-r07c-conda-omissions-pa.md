# R07-C D-M-CE P-A：有界 Conda 字符串省略

日期：2026-10-27。基线 `38b59cc41f8870b63f00321b8278cfc88b14a86b`，未发布0.7.0。
维护者在确认下一步为 Conda 声明提取边界 P-A 后要求“执行下一步开发”。
本轮完成具体提案准备，状态 **PROPOSED / REVIEW_READY**，推荐 A。

## 交付

[完整提案包](../plan/reliability-2026-10-03/proposals/R07-C/conda-omissions/README.md)
含A/B、精确未应用规范及实现补丁、旧新字节绑定、兼容成本、36组未来验收、
当前输入和完整记录、源码资格、独立复核、文稿检查与外部证据哈希索引。

A只为原native Conda helper的两处提前返回新增内部unparsed_conda：name-pattern
fullmatch失败，或已有rest以`::`/`/`开头。保持原诊断、return、所有append路径及
exact/qualified信用；不推断省略的包名，不扩Conda语法，不运行solver。
数字范围、复杂后缀等即使出现相同unsupported诊断，只要仍append声明便保持。

全仓D-M的保守影响必须独立接受：空白或无关子项目的省略也可把剩余已使用、
未获信用包WARNING改为SKIPPED/INFO；孤立WARNING/提升CRITICAL门可1→0，
text可PASS+skipped，default export可少旧notable条目，完整JSON保留SKIP。
SKIP不是exact信用、完整分析或复现成功证书。无engine/redaction/schema改动需求。

## 已执行检查

| 层次 | 真实结果与限制 |
|---|---|
| 独立 current helper oracle | 32份literal预期先冻结，原helper32/32匹配；12省略、20保留控制；候选执行0 |
| Current集成观察 | 36例、216项literal断言通过；真实non-Git scanner、原parser和3个raw规则对象 |
| 观察确定性及身份 | 三个新目录完整JSON逐字节一致；128源码前后相同、53个导入模块核hash |
| 独立完整回读 | 未执行候选，通过源码重建核对216断言、108个完整raw规则对象、输入/模块身份 |
| 五项目源码资格 | 所有pin/origin/clean正确；完整tracked路径中environment.yml/.yaml均0，条件完整delta空 |
| 精确补丁检查 | 临时副本4次check/apply exit0，目标字节吻合；private compile/ruff检查通过；正式源码/规范保持 |
| 文稿与公开边界 | 链接、strict JSON/schema_version、LF、哈希、隐私和已有用户修改保全；收尾检查见提案包 |

36个观察保留完整Declarations、Python捕获、锁/credit、roots/barriers、read/list/
candidate及Requirement/helper轨迹与raw规则Finding。没有记录完整RequirementsGraph
节点/closure，也没有engine/CLI/阈值/export/override/suppression验收。
installed_versions固定为空；CE34是显式coverage seam，不是实测预算截断。
纸面推演有23例未来原因触发、其中12例WARNING→SKIP；它不是执行新策略的结果。

第一次集成观察成功，但未单独记录耗时；两次带收据重放为0.433496/0.445853秒，
exit均0。不得把它们的累计时间当作整会话墙钟。原始观察和收据均保留。

独立审阅发现首版规范补丁的若干全局交叉引用未覆盖新§12.3.13；已修正并重新
完整复核通过。原批评、补丁版本和临时副本保留在外部证据中，没有应用到规范。

## 验收与范围

本P-A仅文稿/计划，完整本地产品质量门、fresh Gate A为
NOT_APPLICABLE_DOCUMENTATION_ONLY；受影响生成文档没有输入变化。
当前观察不是RED/GREEN或P-B验收，未来36组政策验收均NOT_EXECUTED。
没有新milestone/发布，资源Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE。
五项目零适用性来源于固定源码，并非候选跑出零差异；未来P-B仍须正式五项目门。

正式产品、测试、规范、schema、依赖、CI、工具、版本、gold和历史包保持。
README、docs/index及additional-cases-gold三份已有用户修改保持原字节，不纳入提交。
本次无GPU或付费请求、外部issue/申请写入或版本发布。公开包提供synthetic输入/
观察器和完整当前记录；仅凭hash不能独立复验未公开的helper/原始命令/路径清单。

当前资源补验已完成：VAL-R01/R02保持6afe8f4绑定，公共DistilGPT2的VAL-R03按
§8.1.2通过；旧gated成功门SUPERSEDED_NOT_PASSED。本P-A不把这些结果重绑或重开。
更广R07-C、独立A02反馈和A03身份/提交条件继续独立登记。

具体A及精确补丁接受后，进入P-B：先core/rules/CLI回归RED，再最小实现、规范与
CHANGELOG、一次最终完整质量门、fresh五项目Gate A/受影响消费者，提交推送main
并核精确最终HEAD五项CI。P-A自身的最终推送HEAD CI在交付时另核，不从基线成功推定。
