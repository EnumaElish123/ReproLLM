# 2026-10-21 · R07-C profile absence / P-B

状态：**局部 P 已接受并实现，最终本地质量门、五项目 Gate A 与受影响命令全部通过**。
本报告截点在推送前；最终 main HEAD 的五项 CI 由交付阶段另行核对，以下本地证据不代替 CI。

| 提交 | 作用 |
|---|---|
| `bb98e67c6e108822c62842d738f42af2eda871e4` | 本轮代码起点，R08-B A4 已交付 |
| `36ea937c8b45039a5b1c61769b55eb6bdde631b5` | R07-C profile-absence P-A 具体提案、补丁与独立预期 |
| `2b0a10ad156b512cf5d53a49467e5b0c5ddf59ee` | 接受后的产品任务与最终完整验证候选；规格 §12.3–§12.3.2 |
| 后续纯报告提交 | 仅归档本报告及证据；产品、测试、配置、依赖、schema、工具和 CI 设置与上述任务提交相同 |

维护者[明确接受局部 P 与具体补丁](../../plan/reliability-2026-10-03/proposals/R07-C/profile-absence/decision-accepted.json)。
仅在 `exec.profile_detection_mismatch` 的 declared-but-undetected 非 core 分支遇既有 typed
primary-Python incomplete/unavailable 结果时，逐 profile 返回 SKIPPED/INFO、固定新文案与 field evidence。
已发现的 high/shipped 未声明 FAIL、完整视图旧 absence 合同、旧 empty-result veto 均保持。
engine、registry、pyscan、redaction、schema、profiles、依赖和版本不变。
四份接受补丁重构的原五文件逐字一致；新增的旧测试夹具补正另行记录，不改提案。
原 P-A 224 文件（223 checksum 条目加清单本身）、PROPOSED 决定及历史报告原字节保留，接受记录单列。

新 SKIP 使用 INFO，既有 FAIL-only severity overrides 不提升它；用户将缺证据 finding 提升为
WARNING/CRITICAL 的门可能从 exit 1 变 0，真实高置信违规仍可触发门。suppression 继续适用于所有状态。
无 AST signals / 空 detect 的未检出 profile 也保守处理，不构造逐 profile 充分证书。
完整 Python 视图不证明其他检测域或实验执行完整。

## 验收与首次失败

[先测试证据](tdd/summary.json)：旧实现 17 failed / 6 passed / 26 deselected，均为预期的新状态、文案或门差分；
应用接受补丁后，engine / exec rules / audit CLI / default export CLI 四完整模块 **76 passed**。
新增 18 参数化案例，覆盖 cap、读取/解析失败、未知或不一致计数、多 profile、完整/零候选、混合真实违规、
WARNING/CRITICAL 阈值、JSON/schema、重复、默认诊断、文本、suppression、export 和只读。

首次完整质量在原临时候选 `c03aea317b580e3aa7eb834d06386f9aa4fe3c64` 上停止于 pytest：
3203 passed / 2 failed / 2 deselected，覆盖率 94.21%；剩余 21 项没有执行，不能记为 PASS。
[完整失败日志和命令](final/initial-quality-failure/summary.json)与[诊断](diagnosis/summary.json)保留原身份。
旧 export diagnostic 测试声明 evaluation 却无检测证据，其完整与不完整视图的结论现应不同；仅加入 evaluation
见证仍触发此前已接受的空结果 PASS veto。最终只在该测试始终选中的首文件固定 `evaluate` 与 `peft` imports，
使声明有见证且保留非空的正向 finetuning mismatch。完整 stdout、完整 Markdown、default/verbose 与精确 stderr 断言均保留。
产品及共享 fixture helper 不变；补正后整个 scan diagnostics 模块 **44 passed（66.10 秒）**，Ruff/format 通过。
三个窄诊断探针仅留当时工具输出观察，未留存原流；完整初次失败原流与最终模块 JUnit 的哈希来源分别说明。
最终任务提交随后重新执行完整质量门，没有复用失败候选的结果。

## 最终共享证据

[归档总览](final/README.md)、[来源与隐私投影](final/source-index.json)、[全文件清单](final/file-manifest.json)
绑定同一候选 `2b0a10a`；原始私有路径流、内联代码、大型输入清单及 wheel 以哈希外部引用，完整共享报告与差异保留一次。

| 门 | 最终实际结果 | 时间 |
|---|---|---|
| [完整质量](final/quality/summary.json) | 24/24 命令退出符合预期；**3205 passed / 2 deselected**；总覆盖率 **94.22%**，redaction 分支 **100%**；345 项 security、Ruff/format、Mypy、生成文档、schema 全集字节、三示例 audit/lockcheck、自审计、wheel 内容与隔离安装通过 | 墙钟 720.788397 秒；命令累计 715.926532 秒 |
| [五项目 Gate A](final/gate-a/summary.json) | 51 命令、32 检查、10 份完整 JSON 比较；全部五个 fresh L0 及完整 detection/hints/dependencies/paths/frameworks/diagnostics 与独立 oracle 零差异 | 墙钟 92.771524 秒；命令累计 90.683728 秒 |
| [受影响命令](final/affected/summary.json) | 20 次产品调用、197 总编排命令、153 检查；五份完整 L1 与四份完整合成 audit JSON、15 初始化文件及五份完整普通导出全部通过 | 墙钟 200.516752 秒；命令累计 184.513475 秒 |

所有命令、预期/实际退出、各自耗时及完整差异均在对应归档。两项 Gate A 层在质量门后并行，
不得把命令累计时间、各层墙钟简单相加当作会话墙钟。
环境使用既有 locked/offline Python 3.12.14 环境与已核验 Git 2.25 兼容器；完整质量 wrapper 保留原通用 runner 的
历史 metadata task label，新的 invocation binding、完整候选与 inventory 才标识本轮执行。
各命令核对当前 worktree 来源；候选完整输入清单、原 pinned checkout 身份/干净状态及文件字节在前后保持一致。

| 固定项目 | 提交 | 本轮结果 |
|---|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | fresh L0 / init / L1 / default export 全通过 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 同上 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 同上 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 同上 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 同上 |

每个项目的 init→L1→export 均在一次性 clone 内执行。三个初始化文件包含 hidden `.reprollm` 两文件，
五项目共 15 文件均整份字节比较。L1 按 `compare_gold --audit-metadata` 验证全报告，
仅豁免规范 T-02 根字段；默认导出及 stdout 整份字节比较。旧 oracle 具有原 source/pin/hash 绑定，
P-A 的零差异预期先于本轮执行，未以当前输出改写 gold。

四个合成场景使用真实默认 500/501 文件及 Git 仓库：missing-cap 为 SKIP/INFO（exit 0），
mixed-positive 保留真实 CRITICAL FAIL（exit 1），完整视图 absence 保留原 CRITICAL FAIL（exit 1），
suppression 场景 exit 0；各自完整 JSON、固定诊断、输入只读及干净状态均核对。
额外一次 missing-cap 默认 export 保留全文，**仅验收预写的摘要/notable 语义**，不宣称有独立全文 Markdown gold。
产品子进程只允许当前一次性仓库内的明确只读 Git 查询；本轮没有网络、重包导入、GPU 或 provider 调用。

## 交付边界与后续

本轮是普通规则政策切片，没有新增里程碑或 release；GPU、Hub、付费 API 门为 **NOT_APPLICABLE**，不是新 PASS。
以前资源成功继续归属原候选；五份原 metadata manifest 缺失和 HF403 等外部缺口保持，
不宣称同候选发布矩阵完整，不发布 tag/release/PyPI。
A02 独立真实试用与 A03 实际表单匹配/提交没有因本次开发完成。
广义 R07-C 的 dependency absence、listing/framework/README/config 覆盖与充分证书仍 **OPEN**；
后续必须单独准备具体方案并按执行总则接受，不能从局部 P 扩展授权。

[独立归档回读](archive-readback.json)核对 417 个文件、1113 份原来源、394 retained 来源与 19 派生记录，
92 份 JSON 无重复键/非有限数，隐私扫描与原 P-A 保留通过。
来源、文件清单与 hidden 文件 Git 持久化还由交付前检查核对，纯报告收尾不重跑相同产品命令。
归档保留原始生成文件的末尾空行和 pytest 异常行空白：diff whitespace 检查的 25 项提示均限这些原样证据，
手写报告无空白问题；不为消除提示改写已绑定哈希的原流。
推送及五项 CI 绑定实际 main HEAD，交付回执单列；本报告截点不把历史或本地结果冒充该 CI。
主工作区三项原有 WIP 不纳入本轮提交，推送前后核对完整 status 和原字节哈希。
