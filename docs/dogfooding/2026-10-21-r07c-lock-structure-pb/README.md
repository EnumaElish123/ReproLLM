# 2026-10-21 · R07-C D-S / P-B

状态：**已接受的 D-S 已实现，完整本地质量门、五项目 Gate A 和受影响验证全部通过**。
证据绑定产品任务 `d4f248d8c48e0d50672afe22d9f78ba0c65a8fb3`；文稿收尾不改变产品输入。
最终推送 HEAD 的五项 CI 是独立交付条件，不能用旧 HEAD 或本地成功替代。整个 R07-C 仍 OPEN。

起点 `603883fd8b7c7be2eac42d335a182ff654f93918`；
P-A `7694fc8cbd4ffd20083137c34065626c96dd3f0b`；
产品任务 `d4f248d8c48e0d50672afe22d9f78ba0c65a8fb3`。
依据规范 §§12.2、12.3.1–12.3.5 和执行方案 05 §5。
[具体接受](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/decision-accepted.json)
承接[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/R07-C_associated_lock_structure.md)。
原 416 文件 P-A 快照、PROPOSED 决定和条件观察保持原字节，接受记录另立。

## 行为与兼容性

仅在 deps 增加内部 `invalid_structure`：四种已捕获格式锁的有限根容器、package 集合和 list/name 条目检查。
现有读拒绝和 decoder 失败保留原 reason；存在的错误假值类型不能当成字段缺失。
缺失/空集合及 Conda 顶层 None 按明确旧边界保留。不增加版本、build、hash、包值或完整管理器格式验证。
旧 unparsed 文本和全部已提取包名保持，部分可用成员仍有原信用。

任一 exact 声明或 qualified-lock 信用优先；剩余待警告包具有既有 R06-B 合格来源关联时，
经 D-F 原分支 SKIPPED/INFO，独立于 Python coverage。无关联、错误 manager、近项目和 barrier 控制保持原结果。
没有修改 env/engine/scanner/redaction/schema、依赖、默认配置、锁存在性、历史结果或 gold。

FAIL-only override 不提升 INFO/SKIP；孤立 WARNING 或提升 CRITICAL 的门可能 1→0，其他警告与 suppression 保持。
默认文本可能显示 Findings: PASS 并列 skipped 数，默认 export 不列 SKIP 数，完整 JSON 保留未验证项。
这是有限缺证据分类，不证明整个锁或实验完整可复现。

## 真实 TDD 与最终输入

原测试草稿 109 个新例 / 15 函数，明确修订旧 7 个结构例，其余 100 个旧函数 AST/全文不变。
初次 RED **91 failed / 25 passed**，pytest 5.16 秒、命令 6.070440 秒。
初次 GREEN **1 failed / 365 passed**，pytest 36.49 秒、命令 37.400075 秒；原始失败保留。
唯一问题是 Conda 夹具使用既有合同不支持的 `>=`，却期望 unparsed=[]。
只将该行变为已支持的非 exact 前缀 `pytorch=2` / `numpy=1`，全部 assert、实现及规范不变。
原已接受补丁不改写；单行差异、原因和前后哈希另存。

纠正例在旧源码重新 RED **1 failed / 4 deselected**，命令 1.176625 秒；随后精确恢复接受源码。
最终六个完整模块 **366 passed**，pytest 35.32 秒、命令 35.756827 秒；四项检查墙钟 37.393261 秒。
受影响 Ruff/format、严格 Mypy 全部通过。
实施独立回读验证六目标、四份 reverse apply-check、P-A 416 文件和唯一接受 sidecar。

## 同一候选的最终验证

[最终归档](final/README.md)及[汇总](final/summary.json)包含原始来源索引、完整比较和隐私投影说明。
[独立归档回读](archive-readback.json)与[归档器静态复核](packager-static-review.json)另存。
以下产品门均在最终干净任务提交上首次正式执行通过，前后输入逐字一致：

| 门 | 实际结果与比较范围 | 耗时 |
|---|---|---|
| [完整质量门](final/quality/summary.json) | 24 检查、24 来源 guard；3419 passed、2 deselected；覆盖率 94.36%；脱敏分支 100%；security 345 passed；lint/type、生成文档/schema、examples、自审计、wheel/隔离安装通过 | 墙钟 672.535758 秒；命令合计 667.258024 秒；guard 另计 1.811633 秒 |
| [五项目 Gate A](final/gate-a/summary.json) | 全部五个固定版本与干净状态；51 命令、32 检查、10 份完整 L0/facts 比较；规则、依赖、profiles、hints、路径、行号、框架、诊断均无 gold delta | 墙钟 89.944927 秒；命令合计 87.593142 秒 |
| [受影响扩展](final/affected/summary.json) | 197 编排行、20 产品调用、154 检查；五份完整 L1、15 初始化文件（含十个隐藏文件）、五份完整普通默认导出、四份专项完整 JSON 通过 | 墙钟 194.247224 秒；命令合计 179.010297 秒 |

五项目为 lm-evaluation-harness、FastChat、LlamaFactory、HarmBench、llm-dp-finetune。
各 SHA、origin、命令、退出码、实际/期望字节、stderr 和诊断均在归档。
变更命令只在一次性 clone 执行；原 checkout 始终正确且干净。
LlamaFactory 原禁止文件 CRITICAL、HarmBench 嵌套 exact 信用及 lm-eval 截断诊断保持。
没有从候选输出生成新 gold。

专项为 uv-false-collection、uv-partial-credit、unpaired-control、uv-valid-empty，保留 P-A 原输入字节和执行前预写完整 expected。
部分 torch 信用保持，缺证据的关联 openai 才 SKIP；有效空锁和无关联控制仍 WARNING。
另一次结构失败默认导出保留全文，只验收预写 summary/notable 语义，不声称独立整份 Markdown gold。
完整审计 JSON 仅豁免规范根 T-02 metadata；列表顺序、类型、嵌套业务字段及 schema 均严格核对。

质量门保留已核验通用 runner 的历史 A01 标签；本轮 wrapper、完整任务 SHA 和 inventory 明确绑定 D-S。
已在隔离环境锁定离线同步 Python 3.12.14 的 41 包；generic 的 environment_synced=false 表示未在内部重复同步。
Git shim、22 个离线 wheel cache、工具 SHA 和来源 guard 明确保留。

## 准备与归档修正

P-A 的静态行长/外部导入分类提示、root docstring 范围核对停止、SORMAT 显示标签勘误和并发结果段增补回读均保留原记录；
它们不作为产品门通过或失败。AFFECTED 外部驱动两条行长准备提示格式修正后通过，原输入/oracle 不改。

Git 兼容准备探针误从候选 cwd 传显式 init 目标，令隔离 worktree symbolic HEAD 指向 unborn branch。
暂停后恢复精确 codex 分支，原 index、源码和三测试修改均不变；root 独立确认 main 的 HEAD、完整状态和三项原 WIP 指纹。
原探针、异常、恢复和独立回读保留；纠正探针使用实际 quickstart 的 disposable cwd/无目标参数形式，前后全部 tracked 字节与 index 不变。
已有 shim 不改，不将其当作通用 Git 替代品。正式质量门及五项目执行未受影响。

最终归档器第一次构建失败：新增 provenance 循环变量覆盖已有 gate-folder 列表，汇总来源键生成错误。
保留失败目录、原源码/静态回执、真实日志和 451 文件部分产物 inventory；只重命名局部循环变量，数据/来源合同不变。
新版本重新独立复核，在全新目录第二次构建通过。独立回读首次因检查脚本继承的旧用例名称 mixed-warning 停止；仅按冻结的本轮 plan 修正为 partial-credit，保留原脚本、失败流和差异。最终包及纠正后的独立回读通过后才复制。
补充文稿两次复制分别因历史代码 diff 及诊断引述系统路径字面量触发隐私 guard，保留部分复制与原记录；这些内容转为外部哈希引用，全部可分享字节预检后再复制，最终归档不变。相关[归档修正记录](preparation/README.md)区分原始字节、隐私投影和重建的历史 diff；没有重跑或修改产品、测试与三项成功门。

报告和数据收尾仅修改文稿，不改变最终测试、规范、工具执行输入或 CI 配置，按 validation-workflow 文稿例外不重复产品门。
真实 pytest 诊断尾随空格与原始流 EOF 保留；本机路径只按明示固定根和 pytest 临时根作隐私投影，原件哈希留存。

## 交付与剩余边界

main 原三项 WIP 排除在提交之外，快进/推送前后核对状态与指纹。
最终远端 HEAD、五项当前 CI 及原修改保全分别在外部交付回执确认，不以旧 603883f CI 替代。
GPU、Hub、provider、付费和原生 Gate B 为 **NOT_APPLICABLE**：普通规则政策不激活里程碑或 release，历史资源结论归原候选。
没有发布 release/tag/PyPI。

read_issue=None 仍不保证完整 grammar。其他包名/包值/版本、一般依赖/requirements、遗漏候选/import、listing、README/config/framework
以及广义充分证书继续 OPEN。D-S 完成不关闭整个 R07-C。
