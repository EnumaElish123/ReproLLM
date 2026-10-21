# 2026-10-21 · R07-C D-L / P-B

状态：**具体 D-L 已接受并实现，定向验收通过；最终完整质量门、五项目与本轮 CI 待执行**。
源码起点 `9cabdc80ecab7728b1ee08c79fc408dd202a6e28`；P-A 固定快照 `44141ec7ec9643be92c85f53d50343541ac36c60`。

[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/decision-accepted.json)
承接[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/dependency-lock-credit/R07-C_dependency_lock_credit.md)；
原 PROPOSED 决定、190 文件 P-A 和条件观察保持原字节。
只在既有 in-use 包无 exact/qualified 信用、primary-Python gap/unavailable 且已捕获格式 lock 包集合包含该包时逐包 SKIPPED/INFO。
保留其他包/完整视图 WARNING、R06-B 信用、requirements 闭包、空结果 veto；不改 engine/deps/scanner/pyscan/redaction/schema/profiles/依赖/版本。

[TDD](tdd/summary.json)：旧实现 23 failed / 8 passed / 44 deselected；所有失败为新 SKIP 状态、字段或门差分。
应用四份接受补丁后，env rules、engine、audit、export、scan diagnostics 五个完整模块 **158 passed**；
31 项新验收、11 个新函数，旧测试函数 AST 不变。触及文件 Ruff/format 和单源 Mypy 通过。
定向证据不冒充最终完整质量门。预算内解析失败、空默认 stderr 的独立 CLI 回归已实际通过。

最终适用矩阵：fresh 五项目 L0/完整 facts 与独立 oracle；五个一次性 clone 各 init→L1→default export，
完整三初始化文件/JSON/Markdown；真实500/501隔离 audit 的 newSKIP、混合WARNING、完整视图旧WARNING、无格式member旧WARNING，
以及一次新SKIP默认export的预写摘要/notable语义。后者保留全文但无独立整份Markdown gold声明。
GPU/Hub/provider/付费门 NOT_APPLICABLE：普通规则政策，不激活新里程碑/release，历史资源结果归原候选。

保守上界可能包含不合格配对或 barrier 的 lock；它不获信用。新INFO/SKIP不接受FAIL-only overrides，门可1→0。
默认文本可显示 Findings: PASS 并列SKIP数，默认export不显示SKIP数；完整JSON保留未验证项，沿用现renderer。
独立dependency/parser/read/listing/framework/README/config完整性与更广证书仍OPEN，整个R07-C未关闭。
最终命令/完整比较/耗时/归档及精确main HEAD CI待本轮收尾填写；main原三WIP不纳入提交。
