# S3-A：静态候选过滤与默认扫描覆盖诊断

日期：2026-10-13。产品与本地验收已完成。本批按 R07-A → R07-B 执行；详细记录见
[R07-A 会话](r07a-session.md)、[R07-B 会话](r07b-session.md)及
[R07-B 开发交接](r07b-development/handoff.json)。

R07-A 已提交 `41122934a9c3ea2fc7bbee22fe870c44ba549a2e`。共享静态候选过滤先于预算，
Git 与安全规则保留完整文件事实。14 项质量门通过，2,444 tests、160 security tests、mypy 122 文件通过；五项目
155 条合格计划命令、157 条跨尝试实际执行、1,053 项完整比较通过，完整输出 gold 零差异。
单次带监控的 lm-eval 文本审计为 41.080939 秒，对照 24.430768 秒；NeurIPS export
为 42.107045 秒，对照 24.635625 秒。计时变化据实保留，只代表这些单次观察。

R07-B 的[具体 §13 修订已接受](../../plan/reliability-2026-10-03/proposals/R07-B/decision.json)，
规范 SHA 为 `363c4e9b00054f1c50387b108745dabd2f8e4b126d7f841cfd7e7363e027ff31`。
超过 Python 文件预算时，audit、init（含任务列出及交互）和 export 在默认 stderr
显示一次实际解析数、候选数、选中数及上限，并说明信号可能位于未分析文件。
选中后未解析的数量另列；stdout、持久化字段、规则结论和 fail-on 保持原合同。
产品已冻结：150 文件，清单 SHA `c638f7145b3ce755ca1f320fd98209731bf9d3aad8300b80a2166347c9f70eef`。
首次完整 pytest 的 1 项旧诊断列表期望失败及 2,487 项通过结果完整保留；
[仅测试兼容修正](r07b-compatibility-correction/index.json)后，失败项与原 44 项矩阵共 45 项通过。

R07-B 提交：`0e3ff8f0543d66904f237be1f9e5446294cc1f6a`。最终质量门：14/14 PASS（security 163、mypy 123 文件），
实际 tests：2,488；五项目 Gate A：PASS，
实际命令/比较/退出/耗时：126 合格命令 / 127 实际执行 / 987 完整比较，退出分布 {"0": 125, "1": 1}，合格叶耗时 1003.796315 秒，全部实际叶耗时 1005.492108 秒。

另有 30 项独立 AST/诊断核对通过。原七项 JSON oracle 别名错误完整保留，
仅补执行一次冻结公开 serializer，与原 CLI 输出重新比较；LlamaFactory
默认 fail-on 的 exit 1 符合 gold。获批的 LM 覆盖摘要以外，输出无未解释差异。

下一会话 S3-B 按 R04-A → R04-B 处理环境来源与输入时点。R07-C 的不完整覆盖规则政策
尚未交付；历史 VAL-R01–R03 资源验证仍为 BLOCKED。推送及精确 HEAD 的五平台 CI
状态见会话最终回复与本地 `final-ci.json`。
