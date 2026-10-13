# R07-A 性能跟进：Windows CI 的 20k 文件预算

日期：2026-10-13。原最终提交 `fd8fe1244e5cd4f3fc4bec97947dc7f09693a2ff`
推送后，四项 CI 通过，Windows 的 `test_large_repo_audit_budget` 用时 11.8 秒，
超过原 10 秒预算。本记录追加修复和重新验收；原 R07-A/R07-B 提交、失败与合格证据保留。

## 变化与边界

一次静态候选视图捕获只解析一次根目录，显式候选和每次内容读取仍核对当前根。
严格单段文件名省去重复规范化；特殊路径沿用原规范化，带冒号的父段保留原生
Path 语义。私有解析入口保留 absolute/Windows anchor → NUL → resolve/contains
的原校验顺序。POSIX 的普通单段文件可用当前 lstat 元数据结束资格判断；链接、
复杂路径、非普通文件、reparse 标志或元数据检查异常都回到完整解析。Windows
始终使用完整目标解析，因为 lstat 对部分 reparse 类型仍可能进行遍历。
[Python 3.10 官方合同](https://docs.python.org/3.10/library/os.html#os.lstat)。

公共内容读取、路径校验、完整文件事实和 marker 的 19 个原定义逐字节保持。
未新增 marker、元数据或内容读取缓存，未更改 500 文件/512 KiB 预算、
规则、fail-on、字段、依赖、gold、pins 或快照。捕获仍不是原子文件系统快照；
内容读取沿用现有重新核对边界，未提供 descriptor sandbox 保证。

源码：scanner `8fef58be578d0ffd63f96fc2342462af9ee76cbc5008ecb2d1a7945240781503`。
产品 150 文件清单：`daad7e9aa7614a5bd73b54d7919c1e6bda11ae9cdcf5db1953e105f1607b4314`。
规范 SHA 仍为 `363c4e9b00054f1c50387b108745dabd2f8e4b126d7f841cfd7e7363e027ff31`。

## 本地验证

新增 17 个参数展开案例，候选测试共 70 项通过；开发记录保留三次实际 RED。
完整 14 项质量门通过：pytest 2,505、security 174、总覆盖率 93.64%，
redaction 59 statements/24 branches 为 100%，mypy 123 文件、Ruff、4 个文档生成器
及 10 个 schema 的完整文件集合与字节均通过。426 个质量输入始终不变，
清单 SHA `00aeb5e1e688ed46459fd42a2d883dcd8d93fed506190214e4c5d5d2758986ee`。
完整质量门命令叶耗时合计 410.660 秒，pytest 命令 370.185 秒。

20,002 文件固定仓库（500 Python、19,500 dat、2 文本）的 coverage 反馈：
初始原测试审计 15.171152 秒；仅根复用的并发观察 12.367746 秒、
无并发 12.477371 秒；再省重复规范化为 11.564903 秒；
最终正常产品为 8.348113 秒，低于原 10 秒预算。
原 audit/init 两个 performance tests 开启 coverage 后均通过，整组 15.96 秒。
pytest 的 audit call 13.99 秒含造仓库与 Git 设置，不能代替其内部审计计时。

同平面 fixture 仅暂时移除候选视图工作的受控对照为 7.621119 秒，
它是未交付的私有诊断 harness，不是产品验证或晋升的 gold。
所有反馈的完整规范化 JSON SHA 均为
`3a1fb0e6bb80e60f854e32cb8116fecaaac40882d7216a4e1e75b6fafa6a2431`，
只忽略允许的 generated_at，完整原输出和失败观察均保留。
所有这些计时是单次观察；Windows 的修复后实测等待最终提交的实际 CI。

## 五项目与交接

最新源码重新执行全部 126 条 Gate A 命令，无旧原始结果复用，
987 项完整比较通过；另有 30 项独立 AST/诊断核对通过。
实际=合格=126，未知=0；退出分布 125 个 0、1 个符合 LlamaFactory gold 的 1。
命令叶耗时合计 927.135519 秒，wrapper 1258.111340 秒单列。
会话中断后未取得 parent wrapper 最终工具退出收据；126 个真实 child 的退出、
完整输出与比较全部保留，source/pin/monitor 复核通过，无未完成命令或失败文件。
这项收据缺口单独记录，不把它冒称 wrapper exit 0，也未因此重新执行命令。
所有五个原 pinned checkout 保持有效、干净和原 SHA；55 个生成制品、
252 个完整输出流及 111 个 monitor 保全后，仅清理成功的本阶段 5 个 owned clone。
完整规则、profile、hint、路径、任务、manifest 与导出无未解释差异。

LM 单次受监控 text 为 36.415286 秒、对照 24.376493 秒；NeurIPS export
为 36.808659 秒、对照 24.559236 秒。这些受监控观察仍较对照慢，
不据此宣称所有真实仓库加速，也不以监控时间替代上面的独立性能预算。

这是 R07-A 的追加修复提交，因为首次推送的 Windows CI 揭示性能预算失败，
不改写已推送历史。实际任务提交由后续 commit binding 和交接文档记录；
最终 main 的五项 CI 以推送后实际 HEAD 核对，结果见最终回复及本地 final-ci.json。
下一批仍为 S3-B：R04-A → R04-B。R07-C 政策、D01 与历史 VAL-R01–R03
资源门保持其原待决/BLOCKED 状态。

证据：[质量门](r07a-perf-quality.json)、[质量输入](r07a-perf-quality-inputs.json)、
[开发记录](r07a-perf-development/index.json)、[性能记录](r07a-perf-performance/index.json)、
[源码只读审查](r07a-perf-source-readonly-review.json)、
[五项目摘要](r07a-perf-gate-summary.json)、[独立 30 项](r07a-perf-gate-boundary-AST-source-qualification.json)。
