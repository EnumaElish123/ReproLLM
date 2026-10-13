# S3-A 交接与未实施范围

日期：2026-10-13。S3-A产品/本地验收状态：产品与本地验收已完成。
R07-A提交：`41122934a9c3ea2fc7bbee22fe870c44ba549a2e`；R07-B提交：`0e3ff8f0543d66904f237be1f9e5446294cc1f6a`。
Gate A：PASS（155 合格命令、157 实际执行、1,053 完整比较） / PASS（126 合格命令、127 实际执行、987 完整比较）。
最终 main 五项 CI 由推送后实际 HEAD 核对，见会话最终回复与本地 `final-ci.json`。

| 任务 | 完整本地质量门 | pytest | security tests | mypy 文件 |
|---|---|---|---|---|
| R07-A | 14/14 PASS | 2,444 | 160 | 122 |
| R07-B | 14/14 PASS | 2,488 | 163 | 123 |

原始资源记录、历史失败及验证工具修正由各任务报告保留，不用最终成功覆盖。

## 下一工程会话：S3-B，R04-A → R04-B

从实际当前HEAD和干净状态复核，不回退审查SHA；读取本交接、S2交接、
R03及R02-R报告、S3任务卡§§4–5、规范及冻结决定。R07-C和R04-S仍分别需要
其具体材料与适用决定；S3-A的交付不批准这些政策或schema变更。

R04-A需要区分recorder解释器/宿主记录与未经验证的child环境，并在State、
audit、diff、export消费端保持同一来源含义。R04-B需要区分启动前输入基线、
结束后改动与独立的真实消费证据。不能把结束时config内容称为child消费值，
也不能以文件未改写证明已经消费。两任务沿用R03的precedence/last-wins及
R02-R的安全采集、真实child退出码和有界失败处理。

若现有合同不能准确持久化来源或时点，准备R04-S具体字段/兼容提案，暂停
仅依赖新合同的部分；不擅增schema v1字段，不执行任意child解释器探测。
S3-B、D01/A01-B的真实recipe、R04-S在本交付中均未完成。

## R07-C：PENDING_POLICY_DECISION，提供事实来源

完整消费者、预算、保护证明与捕获限制见
[r07a-development/consumer-inventory.json](r07a-development/consumer-inventory.json)。
它记录20个消费者/事实入口及58个受保护定义，属于接口清单，不是已完成的
逐rule政策审议。以下直接规则读取点供R07-C起步；该任务仍须核对全部规则
及间接消费者、设计完整/截断/不可读矩阵，并取得必要的D-41决定。

| 来源 | 直接规则或消费者 | 交接事实与覆盖边界 |
|---|---|---|
| `ctx.git` / 现有Git文件事实 | `code.git_repo`、`code.git_commit`、`code.clean_tree`、`code.no_untracked`、`code.submodules_initialized`、`code.remote_recorded` | 不用Python 500预算；真实dirty/untracked可因环境文件改变 |
| `ctx.fs.files()` + Git ignore状态 | `env.secret_files_ignored` | 保留现有文件视图；tracked环境内`.env.local`仍按现行CRITICAL评估，未被静态候选过滤抹去 |
| `ctx.deps`的合格声明/lock/include closure | `env.dependency_manifest_present`、`env.lockfile_present` | 使用全部合格静态路径，维持root-first和独立requirements聚合；不受Python500选择，但保留各自读取、支持语法及closure限制 |
| `ctx.deps` + `ctx.pyscan.imports` | `env.llm_critical_deps_pinned` | 已发现的使用有明确来源；遗漏的Python文件可能含其他使用，现行无finding含义没有被S3-A改写 |
| `ctx.fs.analysis_files()` +安全读取 | `env.python_version_declared` | 全部合格声明路径按既有顺序检查；不是Python AST预算的complete证明 |
| `ctx.detection.profiles` | `env.reprollm_initialized`、`exec.profile_detection_mismatch`、init planning | 汇总AST、依赖、README/config键、目录/文件名及framework signals；存在不同预算，不能把Python计数当成全部检测完整性 |
| `ctx.detection.hints` | `model.adapter_declared`、`model.trust_remote_code_declared`及provider/backend hints | primary PyScanResult来自受限AST；没有hint不自动证明未扫描区域不存在该行为 |
| 明确manifest/lock/run/State与存在检查 | presence/consistency规则；`prompt.file_exists`、`eval.metric_implementation_referenced` | 与隐式候选视图分开，依各自现行来源合同评估；不把所有规则的结果统一改为FAIL或SKIP |
| 相同静态候选，独立64KiB/字符/tree预算 | `discover.collect`及AST snippet收集 | 不使用primary `scan_python()` 500预算；R07-B摘要不声称覆盖这套采集预算 |

R07-A的candidate视图在同一context首次捕获后缓存；根内marker/alias随后改变
不是原子快照保证。R06-G每次内容读取重新核对resolved根边界与缓存target，
但验证后任何路径组件/target可被并发替换；没有宣称descriptor sandbox。

## R07-B的内部计数与CLI合同

以下内部接口与 R07-B 冻结源码及实际提交绑定一致：

- `PyScanResult.python_candidate_count`：共享排除及listing hard limits后，排序的`.py`路径数。
- `python_selected_count`：实际bounded selection路径数；`python_file_limit`为生效预算。
- `python_parsed_count`：只有选中路径的`ast.parse`成功返回才加1。
- omitted为candidate−selected；selected skips为selected−parsed，不推断逐原因精确计数。
- `file_limit_diagnostic()`：仅candidate>limit生成固定文字/整数摘要。
- `show_scan_diagnostics()`：stderr严格整条匹配，去重，并仅抑制同预算旧truncation文案。
- audit保留其他既有verbose/run warning渠道；init含list-tasks/最终interactive计划及export仅转发该新摘要。

内部typed counts及默认stderr不增加持久化字段或finding，不改变severity、summary、
fail-on、全局PASS合成或rule applicability。R07-C不能解析warning自然语言
作为新业务事实；若需把coverage传入规则/engine或持久化，仍须具体设计与审议。

R07-C本批只获得上述事实清单，政策本身仍PENDING；R06-B scope、R08 judge/自由参数
政策保持其既有待决状态。S2的Conda/YAML物理line-index仍是UNASSIGNED_BACKLOG。

## 资源与后续验收

S3-A执行的是离线Gate A；历史VAL-R01–R03仍BLOCKED，需明确provision资源后
按val.md恢复。CPU/stdlib child、offline discover或模拟HTTP不替代GPU、真实
provider、paid API及正式judge Gate B。S3-B完成后才能继续其依赖的D01证据验收；
采用、发布和相关资源门不在本会话中宣布完成。
