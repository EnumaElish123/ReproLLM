# R07-C D-M-E / P-A：environment 嵌入 pip 提取失败提案

日期：2026-10-23。状态：**P-A 准备完成，PROPOSED；推荐 A，未接受、未实施，规范补丁未应用**。
本报告为推送前快照，精确最终提交的五项 CI 在交付时另核。本轮不发布版本。

## 任务、基线与禁止区

从干净 main `72bf2fc150b8b00cc32a5a75d2ffa13387edbc3e` 开始，按已有代理 git pull --ff-only，
exit 0 / Already up to date。前项 D-M-P 产品 26a4d30 及收尾 72bf2fc 的[五项 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39917945752)
是已核实的历史结果，不替代本轮新提交 CI。
[当前计划](../plan/README.md)、[政策任务](../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md)和
[前项交接](2026-10-23-r07c-pep621-strings-pb/README.md)明确下一步是 environment 嵌入 pip 的独立 P-A。
本次继续执行这项准备，不将旧 D-M-P 接受扩张为新政策批准。

本轮只增加提案、源证据与报告、同步三处活跃导航。产品、测试、正式验证工具、CI、现行规范、schemas、
依赖、版本、gold 和所有旧证据保持；[基线](../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/delivery-baseline.json)
绑定 521 项输入及原 14,875 个 tracked 文件的私有完整清单。

## 具体方案与交付

[提案入口](../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/README.md)集中提供 A/B、兼容性、
38 条未来验收、精确规范 patch、PROPOSED 决定、本地 issue 草稿、当前观察、五项目来源和独立审阅。

推荐 A：只在现有 environment pip str 已经通过非空过滤、以 strip 后文本送入原 Requirement 调用，
且该既有调用失败时，setdefault 记录已有内部 unparsed_requirement。复用 D-M，不改 helper、grammar、
读轨迹、Conda／锁信用、项目资格、barrier、其他原因或优先级。空白仍跳过；行值保留外层 dependencies
的一基序号，不趁机改成物理行。pip 可能支持原解析器未提取的 directive/comment；A 不宣称它们非法，
不扩展 include、注释回退、安装器或 solver 执行。B 保留现行 captured-view 有界 WARNING，缺口仍 OPEN。

必须一并接受的成本是全仓作用：无关 environment 的失败也可使剩余未获信用关键包 WARNING→SKIPPED，
孤立门可 exit 1→0；这不是授予 pin 信用或证明复现成功。更早信用／原因、独立 warning、suppression、
threshold 和完整 JSON 保持；default text 可显示 PASS 加 skipped 计数，export 不再列相应旧 notable warning。

规范补丁拟新增 §12.3.10 并精确调整 §12.3.9 的独立 caller opt-in 和相关引用。patch SHA-256：
`2ccb8860b2e7333f721e4dda4d8b5300a39d4e070226a26179080878f81f6d17`。git apply --check 成功，仅检查而未应用。当前规格 hash 保持。
不请求 D-41 的 engine/redaction/schema 变更；未接受前不实施产品。如果接受，下一次 P-B 才先 RED、
最小现有 caller 改动、GREEN、最终质量、五项目 Gate A／受影响验证、main 推送与精确五项 CI。

## 当前源码观察与全部真实更正

当前源有 27 个 E01–E27 合成案例，每次 162 项预写投影断言；指定 03/04 两次重放分别 exit 0，
实际进程 0.4034523 秒／0.3917994 秒。完整 174,347 字节记录逐字节相等，SHA-256：
`f210406d2e48d24d77027f4a15762f2cf4e355d9417a3fccafa1181a69bf8ef7`。
完整 Declarations／读轨迹／Python／锁关联／三条 raw rule 的 Finding 全部记录，但只对指定投影预写独立断言；
不能把记录完整或重放相同解释为所有业务字段已独立 gold 审定。

最初冻结后首轮 161/162 通过，E21 既有 depth/incomplete 诊断预期错误：实际深度上限 10，对应 chain9，
且向每个 parent 追加 incomplete。按当前 _closure 和既有 depth 回归更正这一个诊断字段；原件／差异／依据保留。
E27 的 include 目标先在首次执行前改为不匹配独立 requirements 根的 extras/pins.in；
否则同名 requirements 根本来会被独立发现并提供信用，不能误当 embedded include 扩展。
此前两次修正后观察亦保留，总计 **5 次当前源码 observer 调用**；指定双重放不是总调用数。
最终 E21 字面值是在首轮观察后修正，不能宣称所有最终预期都在第一次观察前盲写。

实际 producer 从 __version__ 读取为 0.7.0；128 个源码文件前后不变，53 个已加载产品模块来源／hash 绑定。
使用真实 non-Git scanner、安装版本固定空，身份核对后禁止网络、子进程和重库导入。
E20/E22 的 Python coverage 缺口是显式元数据 seam，真实 imports 保留。原生 symlink、CLI/engine、
init/export 或整体退出码未在这些观察中执行，不能冒记 PASS。候选政策执行数 **0**。

[当前行为与复验](../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/current-behavior.md)、
[原始业务观察](../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/current-observations.json)、
[重放摘要及更正](../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/observation-replay.json)
保留精确命令模板、退出、耗时及原始流 hash。合成输入、观察器和指定最终记录公开；含真实运行路径的命令
原件及早期失败原件整件留本地，由源索引引用，不删改业务字段来公开原件。

## 五项目来源与未来验收

固定五项目在前后身份核验中 pin／origin／clean 一致。独立 Git tree/ls-files 及当前候选清单覆盖
17,724 tracked paths／17,675 static candidates；exact environment.yml、environment.yaml、conda-lock.yml
均为 0。没有 pip 条目、YAML/Requirement 实际调用为 0，不能写成这些业务分支实测通过。
42 个显式 Git 命令原始流与约 8 MB 完整路径清单留本地；公开紧凑逐项目摘要、清单 hash 与复验入口。

因此方案 A 对五个固定输入的预写完整 delta 为 ZERO_DELTA，包括 findings、profiles/hints、diagnostics、
graph、init 文件与后续 L1/default export；这只是独立未来预期，没有执行候选或 fresh Gate A。
不将 D-C 的 HarmBench 47 条声明／两条原 Python 诊断等历史变化重新计入本片，不更新 gold。

[38 条未来验收](../plan/reliability-2026-10-03/proposals/R07-C/environment-pip/acceptance-cases.md)
用 A01–A38 命名空间，区别 E01–E27 当前观察；38 是设计行数，不是新增测试／执行／通过数。
覆盖 strip/blank/ordinal、部分提取、所有信用／原因优先级、独立 root 与未跟随目标、全仓成本、
完整 CLI/threshold/text、init/export/history、安全 alias 和五项目门。独立审阅推荐 A、无阻断，
但不是维护者政策批准。B 的措辞已按现行“有界告警而非完全证明违规”纠正，旧稿及修订留本地。

## 验证类别、资源与后续

本轮按[文稿验证流程](../plan/validation-workflow-2026-10-13.md)核链接、内容/证据/哈希一致性、
patch check、未改动基线与隐私；没有修改生成文档输入，相关生成 freshness 为 NOT_APPLICABLE。
完整本地产品质量门、fresh Gate A 与资源 Gate B 皆 NOT_APPLICABLE_DOCUMENTATION_ONLY，不是 PASS。
普通 staged whitespace 检查把 patch 文件必需的空白上下文前缀误报为尾随空格，补丁原字节保持。
另核 patch 载荷无尾随空白、私有文稿副本应用 exit 0 且结果 SHA 精确相同；首个副本因继承全局 Git EOL
产生仅 CRLF 的字节差异，原件保留，显式匹配仓库 LF 配置后重新通过。仅私有副本应用，现行规范未改；
其余文稿仍执行普通 staged 检查。
实际新提交 CI 在推送后单独核验；历史本地产品通过不移用为本轮新结果。

VAL-R03 五份原 metadata 缺失／最近 authenticated HF403 仍 BLOCKED，本轮没有新的资源预检。
VAL-R01 仍绑定 948d164，VAL-R02 绑定 75d1b0；本轮未重跑 GPU、paid judge 或其他资源实验。
A02 独立试用反馈仍 PENDING，A03 身份/角色/组织和提交授权另待输入。没有向外部发 issue／申请。
本轮不调用付费 API、不使用 GPU、不发布版本。更广 R07-C 仍 OPEN；下一步是对具体 A、补丁及保守成本
逐项裁决，再决定 P-B，不因本次 P-A 合入自动实施。
