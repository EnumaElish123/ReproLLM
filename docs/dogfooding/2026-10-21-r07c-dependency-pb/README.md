# 2026-10-21 · R07-C D-L / P-B

状态：**已接受的 D-L 已实现，本地完整质量门、五项目 Gate A 与受影响验证全部通过**。
本地证据绑定产品提交 `2693f5fcd88d666483ee05d47b8441923dda69f3`；后续报告归档提交只改文档和证据。
最终推送 HEAD 的五项 CI 另行核对，不能用本地结果或旧 HEAD 的 CI 替代。
整个 R07-C 仍 OPEN。

源码起点 `9cabdc80ecab7728b1ee08c79fc408dd202a6e28`；
P-A `44141ec7ec9643be92c85f53d50343541ac36c60`（`docs(spec): propose bounded dependency lock-credit conclusions (R07-C)`）；
产品任务 `2693f5fcd88d666483ee05d47b8441923dda69f3`（`fix(audit): skip unresolved format-lock credit under scan gaps (R07-C)`）。
依据规范 §§12.2、12.3.1、12.3.3；接受的 §12.3.2 引用修订同批应用。

[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/decision-accepted.json)
承接[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/R07-C_dependency_lock_credit.md)。
用户明确接受 D-L 与四份具体补丁；原 PROPOSED 决定、190 文件 P-A 快照和条件观察保持原字节。
实施独立复核确认五个补丁目标逐字一致，其余 9,440 个旧 tracked 文件未变，HEAD、index、工作文件一致。

只修改 `env.llm_critical_deps_pinned` 的待警告包：先保留现有 exact 声明与 qualified-lock 信用；
若 primary-Python coverage 有缺口或不可确认，且该 in-use 包出现在已采集的
`uv.lock`、`poetry.lock`、`Pipfile.lock` 或 `conda-lock.yml` 包集合，逐包产生 SKIPPED/INFO。
其余包和完整视图保留 WARNING；requirements 闭包、R06-B 信用及旧空结果 veto 保留。
没有改 engine、依赖采集、扫描器、脱敏、schema、profiles、依赖版本或历史 gold。

[TDD 记录](tdd/summary.json)：旧实现 **23 failed / 8 passed / 44 deselected**，pytest 3.05 秒，命令墙钟 4.008277 秒。
所有失败均为预期的新状态、消息或门差分；应用四份接受补丁后，env rules、engine、audit、export、scan diagnostics
五个完整模块 **158 passed**，pytest 29.49 秒，墙钟 29.901394 秒。
31 项新验收、11 个新函数，旧测试函数 AST 不变；触及文件 Ruff/format 和单源 Mypy 通过。
预算内解析失败且默认 stderr 为空的 CLI 回归实际执行通过。

[最终归档](final/README.md)保留[汇总](final/summary.json)、原始来源索引、隐私投影说明、全部文件哈希及[独立归档复读结果](archive-readback.json)。
下列门均对同一已提交的干净候选首次正式执行通过，执行前后产品输入逐字不变：

| 门 | 结果与完整比较 | 实际耗时 |
| --- | --- | --- |
| [完整质量门](final/quality/summary.json) | 24/24 命令；3236 passed、2 deselected；覆盖率 94.23%；脱敏分支 100%；安全测试 345 passed；lint/type、schema、生成文档、examples、自审计、wheel/隔离安装通过 | 墙钟 655.636132 秒；检查合计 650.642935 秒；来源 guard 另计 1.819698 秒 |
| [五项目 Gate A](final/gate-a/summary.json) | 全部五个固定目标；51 命令、32 检查、10 份完整 L0/facts JSON 比较；规则、profiles、hints、依赖、路径、框架、诊断无 gold 差异 | 墙钟 90.917994 秒；命令合计 88.781512 秒 |
| [受影响命令](final/affected/summary.json) | 197 编排行、20 次产品调用、154 检查；五份完整 L1 JSON、15 个初始化文件（含十个隐藏文件）、五份完整默认导出；四份专项完整 JSON 无差异 | 墙钟 199.634887 秒；命令合计 183.921420 秒 |

五项目为 val.md 固定的 lm-evaluation-harness、FastChat、HarmBench、verl、TRL；
每个目标的 SHA、origin、干净状态、命令、退出码、实际/期望文件及诊断保存在归档中。
初始化只在一次性 clone 执行。普通导出和初始化文件完整按字节比较；audit JSON 仅排除规范允许的根 T-02 元数据，
不排除嵌套字段。原独立 oracle 保留，本轮未用实际结果重新生成 gold。

专项覆盖 new SKIP、混合 WARNING、完整视图旧 WARNING、无格式 lock member 的旧 WARNING；
预期来自 P-A 提交中在对应条件执行前由 baseline 与固定转换产生的 expected 文件。
另一次专项默认导出保留全文，但只验收预写的 summary/notable 语义，未声称存在独立整份 Markdown gold。
lm-evaluation-harness 普通 init/L1/export 合计 139.314455 秒，是受影响验证的主要耗时；没有重试或挂起。

完整质量门沿用已核验的通用 runner，历史任务标签保留，实际候选由本轮调用 binding、commit 和输入 inventory 绑定。
执行前已用锁定依赖离线同步 Python 3.12.14 的 41 包环境；runner 中 `environment_synced: false` 仅表示 runner 内未重复同步。
Git 2.25 兼容 shim 和离线 wheel cache 的来源及哈希均保留。
本轮没有失败的正式质量门、Gate A 或受影响产品门。
受影响驱动准备曾因旧 stderr 文件名定位和随后禁止覆盖空准备目录而停止两次；
只修复两个 oracle 路径定位，未执行产品、测试或资源调用，原停止记录及修正均归档。

格式 lock membership 是保守上界，可能包含 unpaired、错误 manager 或 barrier 项，并不赋予 lock 信用。
INFO/SKIP 不受 FAIL-only severity override 提升，孤立 WARNING/CRITICAL 门可能从 1→0；其他 WARNING 保留，现有 suppression 保留。
默认文本可显示 `Findings: PASS` 并列 SKIP 数；默认 export 不显示 SKIP 数，完整 JSON 保留未验证项。
独立 dependency/parser/read/listing/framework/README/config 完整性及更广充分证书仍 OPEN。

GPU、Hub、provider、付费与原生 Gate B 为 **NOT_APPLICABLE**：本轮是普通规则政策变更，未激活里程碑或 release。
历史资源结果及阻塞保留原候选绑定，不作为本轮结果。未发布 release、tag 或 PyPI。
适用依据为 validation-workflow 的普通产品变更与最终证据文档收尾例外；归档提交不改变产品输入，无须重复完整产品门。

原始 TDD RED stdout 中 36 行 pytest 异常缩进行含尾随空格，归档流和部分原始文件末尾按真实字节保留；
这些证据格式不作为产品/手写文档空白问题修写。main 中 README、docs/index 和额外案例 gold 草稿三项既有 WIP 排除在交付之外，
快进前后核对完整状态与哈希；最终 push/远端 HEAD、五项 CI 和 WIP 保全回执保存在会话外部交付记录。
