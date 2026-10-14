# S3-B：R04-A → R04-B

日期：2026-10-14。**产品与本地验收 PASS**；本报告在推送前生成，远端五项
CI 必须按推送后的精确 main HEAD 核对，结果见本次交付最终回复及本地
`final-ci.json`。不从本地通过推断 CI、资源矩阵或发布完成。

执行起点 `52ecc504b3795c46220f68ef24728e0666638df0`；按当前 v1.2 方案实施
S3-B，先读取规范、架构、执行总则、任务卡、最新验证流程和 val.md。维护者
明确接受具体 R04-S、run/State schema patch 和两阶段版本策略后实施完整批次。
最初的 main 用户文档修改保留；产品在独立 worktree 验证后 fast-forward main。

| 任务 | 提交 | 最终交付 |
|---|---|---|
| R04-A | `a9a3942651901cc2450ec01b0881cd76140000bd` | typed source/phase，recorder 与 child 区分，保守 unknown，冻结 0.6.2 run-v1 读取桥 |
| R04-B | `a2ff1ff9ced40f4c05bcc338317727c654f44bf8` | 0.7.0 写 run v2；启动前原始输入/bindings 基线和独立 post-child checks；所有消费者限定证据 |

任务 commit 最初暂定，以上两项由同一最终质量门、fresh 五项目 Gate A 和
实际冻结桥兼容证据共同验收。详见[R04-A](r04a-task.md)、[R04-B](r04b-task.md)
及[向 D01 / A01-B 的证据交接](runtime-evidence-handoff.md)。没有 engine 政策、
core/redaction、第三方依赖或规则 ID/默认严重度/fail-on 变更。

## 行为与兼容决定

真实 child 读取 config 温度 0.1 后改为 0.9，旧行为把结束后的 0.9 记录成
运行观察值；run v2 现保留原始启动前 0.1、原 SHA/副本，并在 `input_capture`
单独记录 post-child changed 和新 SHA。声明文件缺失/新建/删除/不可读分别处理，
不把结束后才出现的 argv 文件发明成启动前输入。输出仍在结束后采集。
config bindings 从同一原始 buffer 解析，2 MiB 与 snapshot 1 MiB/200 文件
边界相互独立。201 文件仍全部保留指纹，关闭全部文件副本；禁止文件不解析。

环境事实明确 recorder/post_child、host/post_child、inherited_environment/pre_child
以及 lock_resolution；hostname hash 来自启动前。未知 producer/不合 schema
组合保守 unknown。State、audit、diff、runs show 和四模板使用 typed context；
既有 values/precedence/last-wins 与 fail-on 保留。child Python、包与实际消费
仍 unverified；未改写输入不证明消费。独立 child witness 仅作验证者依据。

维护者批准记录及原规范/模型 patch 见[R04-S](../../plan/reliability-2026-10-03/proposals/R04-S/R04-S_runtime_evidence.md)。
读取桥读写 v1 并拒绝新格式，minor reader 读 v1/v2、拒绝 future v3。桥 wheel
为本地冻结实装，未发布到 PyPI；现有 0.6.1 的旧限制保留，不虚称已远端回补。
仅 run_record 导出 schema 改变，其余九份逐字节相同。迁移说明与规范同批更新。

## 最终共享质量门

最终候选为 R04-B 提交，输入库存 SHA
`3e0ed8b1abfad93b3caee2cd8bd4e8d8f468c88d3864e3c31528b02cccaa5ba0`。
每命令都核对候选模块、独立 worktree Python 和 source/distribution 0.7.0。
Git 2.25.1 采用已审定进程级 init-b 兼容器，先让 quickstart freshness 通过。

| 检查 | 本次结果 |
|---|---|
| 全量 pytest + coverage | 2,631 passed，2 slow deselected；93.80% |
| redaction | 59 语句/24 分支全覆盖，100% |
| security | 175 passed，2,458 deselected |
| Ruff / format / strict mypy | PASS；mypy 包括 src 与 compare_gold |
| rules/profiles/CLI/quickstart | freshness PASS |
| 十份 JSON Schema | fresh export 集合/字节全等；九份非-run schema 与桥前完全相同 |
| 三个 examples | L1 audit 与 lock --check 全通过；self-audit 通过 |
| 源码兼容与 wheel | 126 文件按 Python 3.10 grammar 通过；141 package payload 字节与源全等 |

共 22 条最终质量命令，全部 exit 0；累计检查耗时 468.862796s，完整门墙钟
471.774349s。原/最终文件库存完全相同，第三方工具版本与 uv.lock 相符。
source/test/schema/generator/依赖最终固定后只有本报告、证据归档及进度索引
补充；按验证流程的纯报告例外不重复产品质量门。

0.6.2 wheel SHA `3132cfdddb8abe75129e0c1bd44d2e40cc147a52f6a58fd15d6f4eecf83c2480`；
0.7.0 候选 wheel SHA `5c8b3125a30d0daf1f9d8dfb24849eb8c7b6d3046d535f8670db2581a1dce29d`。
二者只作为本地实装/打包证据，不构成发布、D02 clean-wheel 回放或 D03 验收。

## 五项目 Gate A

原 checkout 开始/结束均核对完整 tracked/untracked 干净状态、SHA 和公开 origin；
所有写入、stdlib child venv 与受控 experiment overlay 仅在新一次性 clone。
overlay 明确存在，原项目代码/HEAD 不改，不把受控 child 称作原生模型实验。

| 固定项目 | pin | fresh 核心场景 | State |
|---|---|---:|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 17 PASS | 2 PASS |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 17 PASS | 2 PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 17 PASS | 2 PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 17 PASS | 2 PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 17 PASS | 2 PASS |

每项目 fresh L0 + 完整 facts、offline lock、真实 stdlib A/B run、两次 L2、
完整 pair/self JSON diff、pair text、历史 A/B default export、B 三种 venue、
runs list JSON/show text。三个 venue 与 pair text 为受影响消费端扩展；五项目
都包含改动过的公共 checklist 来源/输入表。A ordered CLI 0.1→0.2 选 0.2，
独立 child parser 同样消费 0.2；B 消费 0.1 后改写 0.9，基线、State/export
保持 0.1，current file consistency 的 CRITICAL gap 如实保留。

共 **85 fresh core + 10 State = 95 产品/消费者命令**；另外 10 完整基础比较与
75 Git/setup/独立 metadata 命令，共 180 顶层记录。外层 300 检查、完整独立
oracle 内 455 检查均 PASS；两层不相加冒称唯一检查数。360 个完整 stdout/stderr
流逐文件核对 SHA、大小、UTF-8。core 422.205954s、State 2.463020s、全部顶层
累计 452.307799s，门墙钟 507.999020s。

基础完整 gold 零 delta：lm-eval 默认摘要仍一次 500/816、HarmBench 嵌套依赖和
语法诊断、LlamaFactory tracked secret、全部 findings/profiles/hints/path/line
保留。只复用不可变独立 expected/source，所有 actual 命令 fresh；pin/gold 不改。
扩展预期来自固定输入、独立 recorder/host control 和逐源审阅的完整规则/模板
合同，未复制当前结果为 expected。全部十个 run-v2 envelope 内值/版本保留。

## 实装兼容矩阵

冻结桥的实际 binary/metadata/source payload 与候选来源分别核验，桥环境无
PYTHONPATH/PYTHONHOME；旧输入、run、manifest/lock/snapshots 前后全树字节相同。
第一批 17 产品命令覆盖两个真实 writer、bridge 实际 run2 的八种读取与新 reader
legacy1/new2/future3，74 检查 PASS。对照批准计划再补 10 个未覆盖 reader 分支：
旧桥 new2 的 diff ID/latest-successful，以及旧桥 synthetic future3 的完整八种
公开 surface，47 检查 PASS。future3 仅更改版本，原正文/ID/时间/副本保持。

合计 **27 产品命令、121 检查 PASS**；另 3 origin + 2 Git 命令，总 32 顶层
记录，分两批计数，未重跑已通过场景。产品耗时 9.923681s + 4.267196s。
list 按既有合同 warning/skip 并保留支持记录；explicit show/diff/export 安全
exit 2、清晰升级提示，latest export 拒绝最高未知格式不默选旧记录。
latest-successful 警告跳过不支持记录后按原“需要两个成功记录”合同 exit 2。
无内部 exit 3、未知 timeout、半输出文档或原地迁移。

## 失败尝试、差异及剩余范围

首次完整质量尝试为 2,624 PASS / 7 FAIL / 2 deselected，93.79%；没有填成 PASS。
遗漏的 fixture/source-note 预期逐组审阅后修正：原 run.json v1 不变，另增 v2，
四个 input fingerprints 独立对应 tracked 文件；旧 lock producer 0.2.0 未确认，
after-run EnvVsLock PASS→SKIP，summary pass -1 / skipped +1。其余规则组和值/
路径/严重度保持；JSON/text diff 只增加来源说明。49 相关回归通过后固定新输入，
重新执行上表完整最终质量门。三份 export 版本快照也先在临时副本生成并完整审阅。
纯验证器准备/封包错误另标工具错误，不计产品 RED，不以它们复跑产品。

本轮非 milestone/非 release，GPU 推理/训练、付费 API、受限 Hub 在线 Gate B
均 `NOT_APPLICABLE_FOR_THIS_SESSION`，不是 PASS。原 VAL-R01 的 10 native exit 0
并不能抹去 **2 capture PASS / 8 FAIL，snapshot fidelity BLOCKED**；本批保持
其状态，不借 source/phase 合同修 RunPrivacy slash/regex/source 保真缺陷。
VAL-R02/03、D01/D02/D03/A01-B 和 Issue #9 仍按原独立范围推进。

下一工程批次为 S4-A：D01 → D02；使用[证据交接](runtime-evidence-handoff.md)，
在真实 recipe 验收前处理保真阻塞并取得相应 child/parser/request 证据。
GitHub spec issue 草稿保留，未虚称已创建远端 issue；维护者具体批准已记录。

## 可复核证据

- [最终质量门、完整五项目及第一批兼容索引](final/evidence-index.json)：每命令完整流、原/便携 SHA、源码/预期/批准和读取来源。
- [定向 RED/GREEN 与 snapshot 审阅](focused/evidence-index.json)：保留旧失败、根包桥证据；32/42 项仅有终端结果，明确无原日志/原 SHA。
- [补充选择器与旧桥 future3](compatibility-supplement/evidence-index.json)：独立的 10 新场景、47 检查及全树保留。

证据 JSON 文档根为 schema 1；run 2/未来版本与 list 数组使用明确 envelope，
内层所有字段/版本保持。raw stdout/stderr 为完整 UTF-8 流，不删字段；机器路径
仅作确定性逻辑标识映射，原 raw 在本地留存并以 SHA 引用。二进制 wheel、venv、
原 clone、cache 与 coverage.data 不入库；归档验证器为 `.py.txt`，不新增执行器。
用户三份未提交文档原字节保留；仅 editable 根包刷新至 0.7.0，40 个第三方
分布均未增删或升级，安装元数据与当前 CLI 一致。
