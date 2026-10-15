# S4-A：D01 → D02

日期：2026-10-15。本报告随本地验收提交；推送后按最终 main HEAD 核对五项 CI，
结果见会话最终回复与本地 `final-ci.json`。不从本地结果推断远端 CI 或发布完成。

执行起点 `507481eec4db91e36e312bfd8bc39818387366b2`。任务遵循可靠性
方案 v1.2 的 S4-A，验证遵循 2026-10-13 工作流。用户原有三份文档修改在 main
保留，任务在独立 worktree 完成；不修改 gold、固定项目版本、规则、schema、
第三方依赖、公开版本号或发布工作流。

| 任务 | 提交 | 交付 |
|---|---|---|
| D01 | `d32645ada35ca31f20ccaaf017832739cdada70b` | 可运行 GSM8K recipe、独立输入预期、三层验证，以及必要的输入快照保真修复 |
| D02 | `b86c014cf9f15f1efddb6902979dcc6ddf79be9f` | 同一候选 wheel 的独立安装验收入口、来源绑定、成功/失败案例与版本文档 |
| D01 CI 补充 | `707d5778470e558d35b2b558c612c0559ed51da5` | 明确 native recipe 的运行时锁合同，保留所有示例审计及旧例锁检查 |
| D02 Windows 补充 | `13830addfd19389d61ec0256e728bbf4b57ab02a` | 隔离子进程显式 UTF-8，实际输出与 reader 回归 |

D01/D02 产品以 b86 候选的共享质量门、五项目 Gate A 和同一 wheel/真实 GPU
证据验收。首推 CI 发现示例接线和 Windows 工具编码问题，随后仅修改 CI、
验证工具、相关测试与生成索引，并重新完成全部质量门及 D02 实装正反例。
最新完整门为 **2,692 tests / 205 security / 93.83% / 21 命令 PASS**，详见
[CI 反馈与修复](ci-followup.md)。产品与原生证据保留准确的 b86 来源；509 个
受保护输入和 141 个 wheel payload 另有字节守卫，不将旧资源执行改称新 SHA。

## D01：声明、实际命令和消费证据

固定 lm-eval `b954108c9baaaa934b4ad842033b31a97ee30816`，恢复已审阅的 Qwen2.5
0.5B / GSM8K 正式输入：100 test items、train 5-shot、四项种子 42，唯一实验
参数变化为生成 cap 32 → 48。配置绑定 `gen_kwargs.max_gen_toks`，实际入口为
`python -m lm_eval run --config validation/eval.yaml`；无需增加框架适配器。
metric、aggregation、filters、模型和数据版本均与固定源码、实际输出逐项核对。

可复制案例见 [recipe](../../../examples/lm_eval_replay/README.md) 和
[integration 文档](../../integrations/lm-eval.md)。manifest、两份配置、固定任务、
原上游文件和许可、stdlib probe 的 SHA 与独立预期同目录提供。恢复的实际配置
使用 `max_num_seqs=8`；不把早期文字中的 1 当作原输入。运行环境仅 GPU 0、
vLLM memory fraction 0.12、CPU threads 2；逐次资源 guard 和独占验证 lease。
原生环境仅将 ReproLLM 0.6.1 更新为同一份 0.7.0 候选 wheel，274 个第三方
distributions 前后完全一致；实际 lm-eval import 来自固定版本的测试 clone。

| 层次 | 本次结果 | 证明范围 |
|---|---|---|
| L1 | PASS；真实 parser/cache 检查 | 固定框架实际 parser、任务映射、模型缓存和完整数据身份 |
| L2 | PASS；3 项完整离线回归 | stdlib 实际读取 A/B；State、目标 diff 叶子和 export；消费 32 后改写 96 |
| L3 | PASS；A/B 各 100 docs、200 filter rows | 同一候选 wheel 包装真实固定框架的有限 A/B GPU 执行 |

A/B wrapper 耗时分别为 114.676672s / 97.967367s，run duration 分别为
112.824209s / 96.225075s。两次 child、capture、消费与输出检查均 PASS。
文档/提示样本身份一致，请求 cap 分别为 32/48。完整 pair diff 共七项：
目标 cap HIGH、config SHA HIGH、干净输入 commit MEDIUM，以及四项运行身份/
时间 NONE；没有需额外解释的变化，self diff 为空，完整 findings/profiles 相同。
默认 export A/B 均成功并选择正确历史 run；两份既有导出的独立投影各 77 项
检查全部通过。将 A 导出 cap 32 篡改为 96 的副本会触发两项失败并 exit 1，
未重复产品或 GPU 命令。

run v2 的启动前副本仍只证明输入基线，未变化也不自动证明消费。真实 framework
result/request 与独立 probe receipt 才是本案例限定范围的消费依据。chat template
未被请求，lock 的模板哈希不用于宣称实际使用；环境包版本仅说明 recorder。

原 VAL-R01 的 slash/regex/source 快照损坏阻碍本案例验收。本次在
`run/privacy.py` 和 `run/input_capture.py` 修复既有合同：仅对 Python 副本使用
AST 确认的除法运算符区间，普通 argv/config 不获得代码豁免；保留精确任务正则、
模板相对路径和关闭标记，同时保留真实绝对路径、UNC、identity/secret 脱敏。
未改 `core/redaction.py`、engine、schema 或政策。新增隐私语料及安全回归。

此前失败的十份独立原始源文件经新的公共 CLI 采集后逐字节相同，九份 Python
均通过语法检查，run v2 完成且无警告。这是源文件回归和本次 lm-eval 证据；
不能据此宣称其他四个项目完成了新的原生模型验收。

## D02：实际 wheel 验收

统一入口 [validate_distribution.py](../../../scripts/validate_distribution.py)
消费已构建的 wheel；D03 将复用此入口。新 venv 和 cwd 位于源码外，运行依赖
正常独立安装，清除 PYTHONPATH/PYTHONHOME/user-site，产品命令使用安装环境
的 Python。实际 import、console entry point、wheel payload、direct URL/hash
分别核对；源码 fixture 仅提供外部输入。离线 walkthrough 的网络请求被阻断。

单次构建 wheel SHA：
`fea3b655cd8deade320fd8d39636e2b10ae8efecc3084e366f9dea912ae74371`。构建清单将其绑定到 D02 候选提交和 0.7.0；
缺清单时只报来源未确认，不从同名版本或当前 checkout 猜测来源。

| 实装场景 | 本次结果 |
|---|---|
| 正确 wheel，干净安装，12 步 walkthrough + package data | PASS；26 条实际产品命令 |
| 恶意残留 PYTHONPATH | PASS；26 条产品命令全部来自安装环境，poison 未执行 |
| 删除关键 package data 的 wheel | 按预期 FAIL；version 成功，第 12 步 export exit 3，validator exit 1 |
| metadata 与指定版本/tag 不符 | 两例均按预期 exit 1，在安装前阻断 |
| 构建清单 wheel hash 不符 | 按预期 exit 1，在安装前阻断 |

实际验收覆盖完整 audit/init/offline lock/check/run A/B/diff/export，精确断言
32 → 48 的 HIGH 目标叶子和 export generation section，加载八个 profiles、
十份 schemas、四种模板；只通过 version/help 不能通过此门。

可用性以 [roadmap](../../community/roadmap.md) 为单一索引。2026-10-15 的 PyPI
元数据仍为 0.6.1；本地源码与候选 wheel 为 0.7.0，run v2 已在 S3-B 引入。
Alpha classifier 和历史 Beta 里程碑名称不作成熟度决定，独立 Action `@v1`
也不因本仓库更新而自动变化。详细安装区别见 [分发说明](../../distribution.md)。

## 产品候选共享质量门与五项目 Gate A

产品验收候选 b86 的输入库存 SHA
`96f9f205fda9b6202401b2b73b02d69a0aad71427d478e60f36e3a0670ba886d`。
24 条最终命令和 24 次解释器/包来源检查均 PASS；检查累计 515.559727s，
完整门墙钟 518.777930s。输入文件与验证器前后字节不变。

| 检查 | 本次结果 |
|---|---|
| 全量 pytest + coverage | 2,690 passed，2 slow deselected；93.83% |
| 核心 redaction 行/分支 | 100% |
| 独立 security 回归 | 205 passed |
| Ruff / format / strict mypy | PASS |
| 四份生成文档 | freshness PASS；quickstart 先于全套测试验证 |
| 十份 JSON Schema | 文件集合与 fresh export 逐字节一致 |
| 三个既有 examples / self-audit | PASS |
| wheel 完整 package payload | 文件集合/每文件字节与候选源码一致 |
| 同一候选 wheel 实装 | PASS；完整教程与包数据消费 |

Git 2.25.1 使用已审阅的进程级 init-b 兼容脚本；锁定环境由新 worktree 预先创建，
最终门内不调整依赖。构建清单先于 distribution acceptance 固定，清单里的
`distribution_acceptance: PENDING` 表示构建时阶段；实装结果独立记录于
`distribution.json`，不事后改写已绑定的清单哈希。

五个固定项目每项 15 个 fresh 核心场景，共 **75/75 PASS**。总计 165 条命令：
75 条 Git/setup/preparation、75 条产品命令和 15 条完整 JSON 比较。285 项顶层
检查、50 份独立 proof 内的 340 项字段/字节检查均 PASS；两层不相加冒称唯一
检查数。门墙钟 482.665236s，产品命令累计 400.805606s。

| 固定项目 | pin | 核心场景 |
|---|---|---:|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 15 PASS |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 15 PASS |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 15 PASS |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 15 PASS |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 15 PASS |

每项目覆盖完整 L0 / facts / init / L1、offline lock、dry-run、stdlib A/B capture、
L2 A/B、pair/self JSON diff、pair text、历史 A/B default export。捕获对照包括
slash/regex/source 保真与独立秘密 canary。完整 findings、profiles、hints、路径、
诊断、manifest、环境、State 和消费者预期零 delta；lm-eval 仍准确报告默认
500/816 文件预算。只复用独立 expected/source，所有 actual 都是本批新执行。
其他模板由 D02 实装覆盖，不重复五项目 Cartesian 矩阵；其他受影响隐私写入
边界由完整安全测试覆盖。五个原 checkout 前后 SHA/origin/clean 均相同，全部
写入只在 disposable clones，候选产品输入前后逐字节不变。

## 差异、边界与交接

测试先失败再实施；保留修复过程中的失败记录，正式结果只采用最终冻结输入。
实际原源文件保真修复为 D01 的必要前置，并纳入同一任务；无规范/政策偏离。
完整原始流与可分享副本分别记录哈希，仅机器路径映射为逻辑标识，不删字段。
模型、数据缓存、venv、wheel 和巨大生成样本留在验证环境的仓库外目录，Git 保存检查结果、
输入身份与可复核索引。

本轮不是 milestone 或 release。仅 D01 所需 lm-eval 原生 GPU 场景适用；其他
四项目原生回放、VAL-R02 付费 judge、VAL-R03 受限凭据验证不写为 PASS。尚未
达到完整发布就绪，未创建 tag、GitHub release 或发布 PyPI。

下一工程批次 **S4-B：D03**。继续处理同 SHA quality/preflight、单次 build、同一
artifact 发布链和 Gate B evidence 阻断。另记一个不影响 fail-closed 的验证器
健壮性边界：产品异常地 exit 0 却不产生唯一 run.json 时，共享 quickstart 抛
RuntimeError，当前入口会失败退出，但未统一形成 JSON 失败摘要；D03 可补齐。

可复核入口：

- [共享最终 QA、五项目 Gate A、D02 实装及失败原貌](validation/evidence-index.json)：931 个逻辑来源去重为 396 份完整 payload，10,243,010 字节。
- [独立完整性与隐私复核](portable-final-1-review.json)及[主执行者复核](root-evidence-review.json)。初次扫描记录保留，最终残留均经合成安全语料或正则常量证明，无未知凭据或本机身份。
- [实际版本和构建关联](version-evidence.json)。
- [原生 GPU 三层与完整消费证据](native/evidence-index.json)及[独立 A/B 产物核对](root-native-artifact-review.json)：126 个索引 payload、577,342 字节；16 个产品运行文件保持原始字节。索引 SHA `81edf1764e5e14928a20e6e95aa6cbecf73e9c6d590c6952f2971bac8ff86470`。
- [首推 CI 失败、两项修复及最新完整门](ci-validation/evidence-index.json)：381 个逻辑来源、175 份完整 payload，详见 [CI 跟进](ci-followup.md)。

根 JSON 均带 schema_version；原始无版本 JSON 流与 source scripts 保留为 inert
`.txt`，不修改原业务正文。逻辑来源索引同时记录原始 SHA/字节数、便携 SHA/
字节数及路径替换事实。原始大体积生成文本仅在资源卷，以完整哈希和元数据引用。

原始流、独立 oracle 和核验器原文保留其结尾空行/行尾空格；Git whitespace
检查只在这些归档文件提示，所有本次编写的文档通过检查，未为消除提示改写证据。
