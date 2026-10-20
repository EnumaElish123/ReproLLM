# R06-B A：开发、测试及独立审阅证据

2026-10-20。维护者具体接受方案 A 后，本批仅修改格式 lock 的关联信用，保留仓库级 existential exact、requirements 闭包、presence、规则、严重度、阈值和 schema 合同。

[汇总](summary.json)记录 **15 条 TDD 命令、5 个 RED/GREEN 纵切、60 个新规则用例、最终固定输入 486 例通过**（pytest 32.41 秒，命令 32.914341 秒），以及真实 CLI 的 1 例通过（2.43 秒）。完整质量门、五项目 Gate A、受影响消费者和 CI 由会话主报告另行给出；此包不声称它们通过，不声明发布就绪。前一轮资源证据的候选与日期保持原义，不升级为新政策验证。

## 决议、设计与审阅

- [具体接受记录](planning/accepted-option-a.json)、[测试边界](planning/test-boundaries.json)、[设计说明](planning/design-note.md)、[39 项独立输入](planning/39-independent-cases.json)、[结构解释](planning/structure-interpretation.json)。保留原设计文档的 DESIGN_ONLY 状态和历史描述；它们本身不是执行收据。
- [独立审阅](review/peer-review.json)和[68 项离线观察](review/68-independent-observations.json)：39 项设计输入、23 项原提案输入、6 项路径 probe 全匹配；无网络、子进程、重依赖导入，无产品问题。唯一 Pipfile dev-packages 文档遗漏已修正。
- [最终源码/测试身份](identity/final-source-and-tests.json)。各原始 TDD 收据保留当时输入 hash；未恢复的历史源码字节不被宣称已归档。当前四份源码/测试文件由独立审阅及固定输入回读绑定。CLI 最终输出原件存在，未单独持久化的调用/输入收据不补造。

## RED、观察器修正及限制

[TDD 交接](tdd/handoff-summary.json)列出15项原始收据。真正首个政策 RED 是“foreign lock 旧 PASS → 接受 A 后 WARNING”；随后五组纵切的 RED 失败数为 1、4、4、8、2，各对应 GREEN 均保留。最终 [固定输入收据](tdd/final-fixed-source-dependency-regressions/receipt.json)与[完整 pytest 输出](tdd/final-fixed-source-dependency-regressions/stdout.txt)绑定前后相同源码/测试；早先 486 例观察与 formatter 重叠，不能替代最终固定输入验收。

CLI [政策 RED](cli/red.txt)、[GitHub title 断言失败](cli/green.txt)、[export HTML 断言失败](cli/green-final.txt)、[最终通过](cli/green-fixed.txt)和[修正说明](cli/oracle-corrections.json)完整保留。Evidence 的 field:null/expected:null、GitHub `%3A`、export HTML escape 三项均为测试期望修正，没有为它们新增产品修复。首次补 null 前的失败仅有会话工具结果、未落原始文件，明确标成 parent 回溯说明；不伪造日志、hash或时间。

## 来源与安全投影

[source-index](source-index.json)将每个 retained 原字节、明确投影或仅 hash 的外部原件绑定原始大小/SHA256；[retained-index](retained-index.json)和[独立审计](audit.json)用于校验包内字节。`source_relative` 定位会话外部原件，`retained_relative` 才是包内路径；原 handoff/source 引用不是需要在本包解析的链接。

完整私有 argv 和 helper 源码仅保留原件 hash，收据投影删去 command/argv/diff_command；失败日志只替换私有 pytest 目录和瞬态对象地址，保留其余断言与完整结果。规范化负例中的 `/project`、Windows drive 等是手写合成输入，不是机器路径。未读取任何凭据，也未运行产品、资源或提供商请求。审计核对已有四个证据包字节不变。
