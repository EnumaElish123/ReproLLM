# 2026-10-21 · R07-C D-F / P-B

状态：**已接受的 D-F 已实现，本地完整质量门、五项目 Gate A 与受影响验证全部通过**。
证据绑定产品提交 `14560ca91b858c1e2bba6bc01dbd48d45bbb9875`；后续报告归档提交只改文档和证据。
最终推送 HEAD 的五项 CI 另行核对，不以本地结果或旧 HEAD 的 CI 替代。整个 R07-C 仍 OPEN。

源码起点 `60aa97f91b09c56e118c434c954ebc451679423e`；
P-A `544c105d00b3bb3d14600d7b9e01a7d875f0416a`（`docs(spec): propose associated lock read-failure conclusions (R07-C)`）；
产品任务 `14560ca91b858c1e2bba6bc01dbd48d45bbb9875`（`fix(audit): skip missing pins after associated lock read failures (R07-C)`）。
依据规范 §§12.2、12.3.1–12.3.4；P-A 文稿阶段同时明确更正上轮人类报告的两个项目名称，原实际验证数据不变。

[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/decision-accepted.json)
承接[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/R07-C_associated_format_lock_failures.md)。
用户明确接受 D-F 与四份具体补丁；原 PROPOSED 决定、236 文件 P-A 快照和条件观察保持原字节，接受另立 sidecar。
独立实施复核从补丁重建七个目标文件并逐字核对，10,116 个 HEAD/index/工作文件 blob 核对通过；
除七个接受目标和三个导航外，其余 10,097 个原 tracked 文件不变。

只修改 deps 的 typed known-failure、等价共享来源关联和 `env.llm_critical_deps_pinned` 的新分支。
四格式锁的现有 safe read 返回 None 或捕获到现有 decoder 异常时，记录内部 `read_issue`。
对既有 in-use 包先保留任一 exact declaration 或 qualified-lock 信用；
若仍待警告，且具有现有 R06-B 合格捕获声明/import 来源关联的格式锁有已知失败，逐包 SKIPPED/INFO。
D-F 独立于 Python coverage、优先于现有 D-L。无关联/错误 manager/被近根或 barrier 阻断的失败锁、有效空锁和非 member 保留原路径。
没有改 engine、scanner/pyscan、redaction、schema、profiles、依赖版本或历史 gold；锁存在性、使用集合和旧空结果 veto 保留。

[TDD](tdd/summary.json)：旧实现 **60 failed / 14 passed / 100 deselected**，pytest 6.62 秒，墙钟 7.514030 秒。
失败均为新 known-failure 属性、SKIP 字段或退出码差分，没有收集/导入/NameError。
应用接受补丁后，env rules、deps、engine、audit、export、scan diagnostics 六个完整模块 **257 passed**，
pytest 69.83 秒、墙钟 70.751497 秒。74 项新验收 / 15 函数，71 个旧测试函数 AST 与文本不变。
五个触及文件 Ruff/format、两源 Mypy 通过；四份补丁 reverse apply-check 通过。

[最终归档](final/README.md)包含[汇总](final/summary.json)、原始来源索引、隐私投影说明和完整文件清单。
[独立归档回读](archive-readback.json)与[打包工具静态复核](packager-static-review.json)单独保留。
下列门均对同一已提交的干净候选首次正式执行通过，执行前后输入逐字一致：

| 门 | 结果与完整比较 | 实际耗时 |
| --- | --- | --- |
| [完整质量门](final/quality/summary.json) | 24/24 命令；3310 passed、2 deselected；覆盖率 94.32%；脱敏分支 100%；安全测试 345 passed；lint/type、schema/生成文档、examples、自审计、wheel/隔离安装通过 | 墙钟 668.952551 秒；检查合计 663.787724 秒；来源 guard 另计 1.837073 秒 |
| [五项目 Gate A](final/gate-a/summary.json) | 全部五个固定目标；51 命令、32 检查、10 份完整 L0/facts JSON 比较；规则、profiles、hints、依赖、路径、框架、诊断无 gold 差异 | 墙钟 90.165535 秒；命令合计 87.972988 秒 |
| [受影响命令](final/affected/summary.json) | 197 编排行、20 次产品调用、154 检查；五份完整 L1 JSON、15 初始化文件（含十个隐藏文件）、五份完整普通导出、四份专项完整 JSON 全部无差异 | 墙钟 196.312743 秒；命令合计 181.070765 秒 |

固定项目为 val.md 的 lm-evaluation-harness、FastChat、LlamaFactory、HarmBench、llm-dp-finetune。
各目标 SHA、origin、干净状态、命令、退出码、实际/期望文件和完整诊断都在归档中。
初始化仅在一次性 clone 执行；全部三初始化文件与普通默认导出按完整字节比较。
audit JSON 只豁免规范允许的根 T-02 metadata，不忽略嵌套字段或列表顺序。
LlamaFactory 的既有禁止文件 CRITICAL、HarmBench 的嵌套 exact 信用及 lm-eval 截断诊断保持。
没有从候选输出重建或更新 gold。

四组专项保持 P-A 原输入字节：已关联语法失败、混合 WARNING、无关联失败、有效空锁，均实际完整解析一个 Python 文件。
预期来自 P-A 提交中，在对应条件观察前由 baseline 和固定转换产生的完整 expected 文件。
另一次失败关联默认导出保留全文，但只验收预写 summary/notable 语义，不声称独立整份 Markdown gold。
正式受影响验证没有重试；五项目非资源比较和专项结果都绑定本轮质量回执。

完整质量门沿用已核验通用 runner，历史任务标签保留；实际候选由本轮 invocation binding、commit 和输入 inventory 绑定。
执行前已锁定离线同步 Python 3.12.14 的 41 包环境；runner 的 `environment_synced: false` 仅表示未在内部重复同步。
Git 2.25 兼容 shim、离线 wheel cache 和通用工具来源哈希均保留。本轮没有失败的正式质量门、Gate A 或受影响产品门。

准备阶段停止记录保持：规范准备误判 CHANGELOG 标题唯一；观察工具初次 deps 哈希常量笔误；
测试草稿外部路径的 first-party 分类提示；包装器准备使用无 tomllib 的解释器、把 editable 项目误当 version pin 的静态假设。
P-A 文稿 checker 初次没有容许标准 unified patch 空白上下文，临时文稿提交发生在检查返回未复读时；
修正 checker 又识别到末尾空白上下文。之后逐项验证标准 patch 空白/EOF、全部四补丁 apply-check、所有 committed/index/工作 blob 和原快照通过。
原失败和纠正均记录，没有改写补丁或原始观察字节，也未在这些步骤推送或改变产品。
外部 CI 工具首次隐式 Ruff 配置检查提示继承的旧规则，改用现有仓库显式配置后通过，未改代码或加忽略。
这些静态准备停止不冒充产品门失败或隐藏重跑。

None 只表示未登记两种已知 lock 失败，不证明 grammar 完整。错误结构/部分提取、一般依赖/requirements、遗漏 import 来源、
listing/README/config/framework 和广义充分证书继续 OPEN。整个 R07-C 不因 D-F 交付而关闭。
新 INFO/SKIP 不受 FAIL-only override 提升，孤立 WARNING/CRITICAL 门可 1→0；其他警告与 suppression 保留。
默认文本可显示 `Findings: PASS` 并列 SKIP 数，默认 export 不显示 SKIP 数，完整 JSON 保留未验证项。

GPU、Hub、provider、付费与原生 Gate B 为 **NOT_APPLICABLE**：普通规则政策不激活里程碑或 release，历史资源结果归原候选。
未发布 release/tag/PyPI。最终证据文稿收尾不改变产品/测试/相关工具或 CI 输入，按 validation-workflow 的报告例外不重复产品门。
TDD RED 中 48 行真实 pytest 异常缩进尾随空格，以及原始流 EOF 和标准 patch 空白上下文均按真实字节保留；手写文档和产品格式检查通过。
main 原三项 WIP 排除在提交外，快进前后核对完整状态与哈希；最终 push/远端 HEAD、五项 CI 和 WIP 保全在外部交付回执记录。
