# S3-A / R07-B：默认显示 Python 文件预算覆盖

日期：2026-10-13。前置 R07-A：`41122934a9c3ea2fc7bbee22fe870c44ba549a2e`。
依照 [S3 任务卡 §3](../../plan/reliability-2026-10-03/03_Scan_and_Runtime_Evidence.md#3-r07-b默认可见的扫描截断诊断)，
执行维护者明确接受的 [具体 §13 patch](../../plan/reliability-2026-10-03/proposals/R07-B/spec-13-proposed.patch)。
规范由 `13db16f6…` 精确变为 `363c4e9b…`；patch SHA 为 `8df82d2d…`。
[接受决定](../../plan/reliability-2026-10-03/proposals/R07-B/decision.json) 与提案
四个历史文件保持原字节，实施阶段以独立 implementation/验证记录说明。

`PyScanResult` 增加仅内部使用的候选、选中、成功解析和实际 cap 计数。
候选数使用 R07-A 的过滤后集合及既有 2 MiB listing 上限；选中数来自
实际限定列表，解析数仅在 `ast.parse` 成功后递增。只有候选数超过实际
cap 才生成新默认摘要；cap 内的 read/size/syntax skip 沿用原诊断合同。
没有增加持久化字段或 schema。原 scanner 的 legacy warning 保留。

CLI 使用严格全消息匹配，仅提升固定文字与 ASCII 整数的覆盖摘要，
避免文件名伪造前缀。audit 保留其他诊断的既有可见性，verbose 只去除
同一预算的重复 legacy 展示；init（含 list-tasks/交互重规划）在最终
计划显示一次，export 仅转发新覆盖摘要。JSON stdout、报告文件、
Markdown、规则结论和 fail-on 不改变。CLI/quickstart 由真实生成器
重新生成，并同步 FAQ、export 用户说明和 CHANGELOG。

[开发证据](r07b-development/index.json) 包含 15 次实际命令，13 次 exit 0
与两次真实 RED：audit text/JSON 两项缺少默认 stderr；init/list-tasks/
交互/export 五项缺少摘要。最小实现后分别 2/5 GREEN，最终 44 个展开
验收用例与 208 个相关消费者回归全通过；Ruff、八文件格式检查及
123 个源码文件的 strict mypy 通过。完整原始日志与每步输入摘要保留，
没有 golden snapshot、pin、gold 或依赖改动。

源、测试、生成器、规范和用户文档已经冻结。[质量输入](r07b-quality-inputs.json)
捕获 426 个文件，完整质量门前后字节一致，inventory `1459fab4…`；
产品为 150 文件，inventory `c638f714…`。
[受保护合同](r07b-frozen-files.json) 的 37 文件相对会话起点保持原样；
开发 proof 另核对 R07-A 的 144 个完整产品文件与 29 个 AST 定义不变。
[首次完整质量门](r07b-quality-first-attempt/index.json) 的 14 条命令及
13 份完整日志全部保留：13 条通过，全量 pytest 2487 PASS / 1 FAIL。
唯一失败是旧内部诊断测试仍只期望 legacy cap 提示；按已接受合同，
内部列表同时保留新摘要和原提示，CLI 才去除同预算的重复展示。
[测试兼容修正](r07b-compatibility-correction/index.json) 只改变该测试
的精确完整列表期望与模块说明，产品字节、44 个新用例、初始开发与
实施快照均不变。该失败项与原矩阵共 45 项通过后重新冻结全部输入。

[最终完整质量门](r07b-quality.json) 14/14 exit 0：2488 tests、163 security
tests，总覆盖率 93.62%，redaction statement/branch 100%，strict mypy
123 文件、Ruff、四项生成文档检查与十个 schema 完整集合/字节通过。
全量 pytest 命令 373.245 秒，两项既有 slow deselection 和既有 marker
warning 保留；使用独立 basetemp 与既有临时 Git init shim，系统和依赖
未改动。14 条命令合计 413.064 秒。

[五项目 Gate A](r07b-gate-evidence-index.json) 已通过：126 条合格计划命令，
987 项完整比较（180 baseline + 807 受影响消费者/边界比较），另有
[30 项独立 AST 与诊断核对](r07b-gate-boundary-AST-source-qualification.json)
全部通过。五个固定 SHA、origin、clean 状态有效；完整规则、profiles、
hints、任务、物理来源、15 份 scaffold 及 40 份成对 Markdown 保全。
产品 150 文件前后字节一致，质量门 426 输入在 Gate 后仍匹配冻结摘要。

LM 的唯一展示差异是获批的 500/816 默认覆盖摘要，verbose 精确替换
同预算旧提示；stdout、finding、manifest 与 Markdown 保持原字节合同。
HarmBench 123 候选、121 成功解析仍无默认 cap 摘要，两条既有 verbose
语法诊断保留。LlamaFactory 的 `.env.local` CRITICAL 及默认 exit 1
符合旧 gold；其他默认 fail-on exit 0。未改 pin、gold 或 snapshot。

[跨尝试计数](r07b-gate-execution-accounting.json) 保留原 126 次完整执行及
七项 oracle 比较失败：冻结 API 的 `model_dump` 未启用 alias，错误期望
`summary.pass_`，CLI 按现行公开 schema 正确输出 `summary.pass`。仅补
一次相同四个业务文件树的冻结公开 `audit_report_to_json` batch，实际
exit 0 / 1.718491 秒；七项完整 JSON 比较据其真实输出重新核对，其他
980 项原比较与十条 boundary CLI 原始输出不变。原七项 false、wrapper
exit 1 及最终 wrapper 1337.895278 秒完整保留，未重跑 CLI 或五项目。
资格为 125 条原命令复用 + 1 条正确 oracle，实际为原 126 + 1 = 127。
合格退出为 125×0 + 1×预期 1；实际为 126×0 + 1×预期 1，unknown 为零，
真实 child 失败为零。合格叶耗时 1003.796315 秒，实际叶耗时
1005.492108 秒；被替换的旧 oracle 1.695793 秒另列。wrapper 与叶耗时
分别记录，不相加为一个指标。

[独立审查](r07b-gate-final-independent-readonly-review.json) 核对以上原始
文件、资格、monitor、来源和计数。计时说明只修正 B facts 两侧相同
pin + plain 工作量的描述；实际恢复账户来自独立纯 helper `187846b7…`，
未执行只适用于 fresh 126 的 prepared account。最终封装曾因工具源码
中的本机根目录字符串触发 privacy 检查；partial 与错误记录保留，
B 专用 packager 仅增加两项已知根目录的显示映射，原始 SHA 保全。
该步骤没有产品执行；A packager 及全部 A 证据未改。

[30 组成对计时](r07b-gate-paired-timings.json) 如实保留单次监控结果：
LM 文本 current 40.906116 秒 / frozen 24.405433 秒，四模板 current
165.025227 秒 / frozen 98.338274 秒；facts 同 pin + plain 工作量
109.866192 秒 / 61.471395 秒。不据此推断无监控性能或统计稳定性。
37 份可移植 JSON、55 份生成物与 252 个合格完整 stdout/stderr 流均以
原始摘要绑定；只在保全全部字节后清理五个成功一次性 clone，原 pin、
原失败目录及补充 oracle 证据保留。

本任务只交付覆盖说明。R07-C 的规则 PASS 政策、S3-B 的运行来源与
输入时点仍按其任务卡推进；本批不激活资源 Gate B，历史 VAL-R01–R03
保持 BLOCKED。最终 main 的五平台 CI 在推送后按实际 HEAD 单独核对。
