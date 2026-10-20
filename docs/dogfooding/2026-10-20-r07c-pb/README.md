# 2026-10-20 · R07-C 局部 A / P-B

状态：**本地最终验收 PASS**，产品任务提交 `b5564f0c7b94db132053cbe97abd8e824403a8bc`；
起点 `1ce5d18ec49b1b8ed4110586de1e24fd2fdb2cc4`。
报告收尾仅补充证据与导航，保持已验证的产品、测试、配置及工具字节。
交付时核对实际推送 main HEAD 的五项 CI，不能用起点或任务提交的旧 CI 代替。
本轮不发布 release、tag 或 PyPI。

维护者明确[接受局部 A、规范和 D-41 引擎补丁](../../plan/reliability-2026-10-03/proposals/R07-C/decision-accepted.json)。
实现只改变 `env.llm_critical_deps_pinned` 与 `exec.profile_detection_mismatch`
适用且 check 返回空列表时的结论：已捕获的 primary-Python 候选存在未解析文件，或内部 coverage
不可用 / 不一致时，返回现有 SKIPPED / INFO、固定计数或 unavailable 文本、空 evidence。
其余 67 条内置规则、所有非空 findings、显式 role PASS、generated rules、severity overrides、
suppression、fail-on、排序及 R07-B 默认 stderr 合同保持。
这是有意保守的局部政策，**广义 R07-C 仍 OPEN**：非空 absence findings、mixed evidence、
listing/deps/framework coverage 和输入充分证书均未在本轮实现。

产品 schema、profiles、依赖、版本、历史 fixtures / gold 不变。原 P-A packet、PROPOSED 决定、
补丁及条件 expected-A 原字节保留；另立 ACCEPTED 决定，不改写准备时历史。
历史 portfolio 的早期 unknown-message 元数据不是规范；实际 unknown / invalid 使用已接受补丁的固定 unavailable 文本。
五个源文件与接受补丁逐字核对，唯一等价调整是 `0 <= limit` 改写为 `limit >= 0` 以满足 SIM300；
engine hunk 与 D-41 接受版本逐字相同。

## 验收与范围

[先测试证据](tdd/summary.json)记录公共 run_audit / scan_python 的 RED→GREEN。
两条错误 PASS 在同一 tiny-cap 输入变为固定计数 SKIPPED。
最终定向 engine 14 项、pyscan 26 项、CLI/export 32 项通过；较早的 114 项回归另行保留，
不把它当作含后续 hook-lifecycle 用例的最终全量结果。
覆盖四格、真正缺席、受控不可读、未知 / 非法计数、有效零候选、大小 / 预算边界、
完整 69 个内置 ID、两个 generated rules、混合角色 PASS/FAIL、CLI 阈值 / suppression / 展示及默认导出。
[独立 Standards / Spec 复核](implementation-review.json)无未解决问题，公开 hook 生命周期测试建议已关闭。

| 改动 / 保留合同 | 本轮验证 | 独立预期 |
|---|---|---|
| 两规则的空结果结论 | 完整本地质量门、公共接口验收 | 仅已接受的缺口 / unavailable veto；非空结果保持 |
| 共享 primary-Python facts | 五项目新鲜 L0 + 完整 detection / hints / deps / 路径 / diagnostics | 与原独立 oracle 完全相同 |
| init / L1 消费者 | 五项目旧版与候选各 init→L1 | 三个生成文件逐字一致；完整 L1 仅两处接受差异 |
| 默认 export | 五项目旧版与候选各默认导出 | 完整字节只有 lm/Harm 的已接受 summary 通过数各减一 |
| GPU / provider / Hub | NOT_APPLICABLE 于本轮普通静态政策任务 | 不触发新里程碑 / release；历史资源证据及阻塞保持原候选归属 |

## 最终共享结果

| 检查 | 结果 |
|---|---|
| 完整质量门 | 24/24 PASS；3,101 tests、2 slow deselected；345 security tests；coverage 94.205719419%；redaction 59/59 行、24/24 分支 |
| 质量门耗时 | 609.805268 秒墙钟；pytest 464.01 秒；所有候选输入前后逐字一致；24 次 origin guard |
| 五项目 Gate A | 51 commands / 32 checks / 10 份完整 JSON 比较；零 gold delta；89.516886 秒墙钟 |
| 受影响消费者 | fresh baseline 15 + candidate 15 产品命令；314 commands / 198 checks；10 份完整 L1 与 5 份完整默认导出对比 |
| 消费者耗时 | baseline 产品 166.503809 秒，candidate 产品 163.131835 秒；总墙钟 402.259137 秒；命令累计 361.958818 秒，不能与墙钟相加 |
| 构建 / 隔离安装 | 新 wheel SHA256 `9f942491475f1034b75584bcdb22dd892db3215095c4cfa539e8da7f790386d6`；offline distribution PASS |
| 源码 / 环境 | 全部 tracked Git blob 与候选相符；旧版 `1ce5d18` 的 143 个 src 文件完整逐 blob 提取核验；相同锁定环境与版本 / 源 origin guard |

[完整本地证据](final/README.md)保留所有完整审计 / facts、strict 比较、两阶段初始化文件（含隐藏配置）、
默认导出、全部 stderr、命令 / 退出码 / 耗时及来源哈希。
质量门仅执行一次最终输入；环境已预先 locked / offline 同步，quickstart 先于完整 pytest 通过，
经核验 Git 兼容器支持本机 Git 2.25.1 缺少的 init 参数。
原通用 runner 的历史任务标签不改写；本轮 invocation binding、完整候选提交、输入 inventory、
模块 / 安装版本 origin guards 及新输出目录共同绑定本次执行。

受影响验证的旧版是新执行，并非复用旧 PASS。旧版 init 和完整 L1 先比对不可变历史来源，
候选 L1 比对 P-A 预先写好的条件 expected-A；候选输出从未用来生成 gold。
旧报告的默认导出是在 lock/run 后生成，因此本轮重建无 run 的旧版默认导出，保持输入一致。
导出完整预期只由旧版字节与已接受的 summary 差分派生；不加入运行记录元数据豁免。
[观察器独立复核](final/affected/qualification/independent-scope-review.json)及 strict 比较正反例在证据中保留。

仅有两处 L1 finding 差分，均为 `exec.profile_detection_mismatch`：

| 项目 | 实际 primary-Python coverage | 差分 |
|---|---|---|
| lm-evaluation-harness | parsed 500 / candidates 816，selected 500，limit 500 | PASS→SKIPPED/INFO；pass−1、skipped+1；默认导出 pass 9→8 |
| HarmBench | parsed 121 / candidates 123，selected 123，limit 500 | PASS→SKIPPED/INFO；pass−1、skipped+1；两条原语法诊断及 parse-only 默认 stderr 不变 |

其他 findings 的完整字段、profiles、hints、路径、诊断、初始化文件及其他三个项目的完整导出均不变。
HarmBench 原九个 exact exemptions 与 DP setup.cfg 现行支持边界保留。
全部原始 checkout 在前后均通过固定 SHA、origin、tracked/untracked 干净及源字节核验；
命令只修改一次性副本。没有调用 lock/run/diff、网络、模型导入、GPU 或付费接口。

## 证据资格与交付边界

旧 R06-B 归档的 initialized 文件集缺少 10 个隐藏配置原件；原 scratch 中完整文件仍在，
归档 source-index 含其独立哈希。本轮逐一校验这些原件，并完整保留两阶段共 30 个初始化文件，
包含 20 个隐藏配置。历史归档不改写，也不把缺失文件默认为一致。
准备工具曾把历史 wheel payload 数 148 当成 src 树数量；纯工具检查在产品执行前停下，
按 Git 实际完整 143 文件集修正，保留失败 helper 和资格记录，不增删文件凑数。
收尾修正定向 CLI 日志的引用：由格式化步骤 01 指向真实 pytest 步骤 04；
原始 receipt / streams 保留，32 项测试结果及产品字节未改变。
打包隐私检查的失败尝试保留在外部 scratch，修正只影响共享证据映射，不重跑或改写产品验证。

报告归档后核对整个 Git 文件集和 blob，特别包含受 .reprollm ignore 影响的 20 个隐藏文件，
避免磁盘保留而提交遗漏。[提交文件核验](staged-archive-verification.json)和[文档检查](closure-documentation-checks.json)保留结果；原始输出的 EOF 空行按哈希原字节保留，其余 whitespace 检查通过。main 原有 README / docs index 修改及额外案例草稿均保持原字节。
最终 CI 以实际推送 HEAD 五项成功为交付条件，完整结果在交付消息链接；本地 PASS 不冒充跨平台结果。
旧资源记录仍分别绑定 `948d164` / `75d1b0`；原始 metadata 缺失与 HF 403 仍是独立外部缺口，
本次不重新归属、不标为 PASS，不据此宣称同候选完整发布矩阵已完成。
