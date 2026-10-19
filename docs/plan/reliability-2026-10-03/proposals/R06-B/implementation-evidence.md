# R06-B 当前实现证据：声明汇总、requirements 闭包和格式 lock 信用

日期：2026-10-19。源码候选：`af8adea8ec37fb5db57373432f4ced58cec9fb9e`。
状态：**P-A / PROPOSED**；本证据未实施方案 A，未修改产品、规则、规格、测试或 gold。
完整输入、每个来源的字节数/SHA-256、当前声明/图/lock/完整 findings、源码库存和可重放观察器见 [current-implementation.json](current-implementation.json)。

## 结论与三层事实

当前 L0 聚合全仓候选，不选择一个实验环境，也不求解冲突版本。
`env.llm_critical_deps_pinned` 对每个在声明或 import 中出现的关键包，先查任意 lock 的包名并集，再查任意 exact 声明；任一成立即无该包的 warning。
因此无关联子项目 lock 可以影响根声明的结论；收紧这项信用需要先批准 R06-B 政策，不能冒充已批准修复。

| 层次 | 当前事实 | 推荐 A 的边界（尚未执行） |
|---|---|---|
| Manifest / lock artifact 是否存在 | `manifest_present` 与 `lockfiles` 的仓库级存在判断；空/损坏格式 lock 仍可占一个 lock 条目 | 原样保留；存在不证明格式有效、可安装或环境完整固定 |
| 包是否有足够 pin 证据 | 任意全仓 exact 声明，或任意 lock 的包名 | 全仓 exact 不变；仅格式 lock 包名信用增加明确同项目、同 manager、在用来源关联 |
| 某实验能否重建为同一环境 | 当前规则没有选择环境、解冲突、验证 lock 版本/freshness 或执行安装 | A 仍不证明；显式实验选择/workspace 委派留给 B |

例如 E13 的循环 requirements 不构成 lock，但其中已读 exact 声明仍消除包 warning；E16 的损坏 uv lock 消除“缺少 lock”warning，却不能消除 torch warning。两者均为当前行为，不能合并成一个 PASS。

## 实际调用链与定位

源码的完整 raw-byte SHA-256 和行号起点保存在 JSON 的 `sources`，以下链接对应上述候选。

| 位置 | 已核对行为 |
|---|---|
| [context.py:92](../../../../../src/reprollm/core/context.py#L92) / [context.py:99](../../../../../src/reprollm/core/context.py#L99) | `deps` / Python AST 懒加载，每 context 缓存 |
| [scanner.py:134](../../../../../src/reprollm/core/scanner.py#L134)、[149](../../../../../src/reprollm/core/scanner.py#L149)、[241](../../../../../src/reprollm/core/scanner.py#L241) | Git/fallback 列举、静态候选过滤与缓存读取；已有大小、读取和 Python 文件数边界不由 R06-B 改动 |
| [deps.py:105](../../../../../src/reprollm/core/deps.py#L105)、[121](../../../../../src/reprollm/core/deps.py#L121) | 保留所有同名候选，按格式遍历；同 basename 根目录优先，其余确定排序；不是“根声明覆盖子声明”或全局版本优先级 |
| [deps.py:35](../../../../../src/reprollm/core/deps.py#L35)、[78](../../../../../src/reprollm/core/deps.py#L78) | 每条声明独立判 exact，保留 source/line；无同包冲突求解或选定版本 |
| [deps.py:186](../../../../../src/reprollm/core/deps.py#L186)、[227](../../../../../src/reprollm/core/deps.py#L227)、[307](../../../../../src/reprollm/core/deps.py#L307) | 每个 requirements 根的实际可达图：非空、完整、所有声明 exact；active-stack cycle / depth 10 / 缺失或不支持边使该根不合格；不借 sibling |
| [deps.py:92](../../../../../src/reprollm/core/deps.py#L92)、[660](../../../../../src/reprollm/core/deps.py#L660) | 当前 `Lockfile` 只有 path/packages，无 owner/manager-origin 关联；requirements 的资格和包集合复用同一个闭包 |
| [deps.py:692](../../../../../src/reprollm/core/deps.py#L692)、[706](../../../../../src/reprollm/core/deps.py#L706)、[721](../../../../../src/reprollm/core/deps.py#L721)、[740](../../../../../src/reprollm/core/deps.py#L740) | uv/Poetry 读取 package.name，Pipfile 读取 default/develop 键，Conda 读取 package.name；无版本、content-hash、平台或 freshness 校验 |
| [env.py:77](../../../../../src/reprollm/rules/env.py#L77)、[123](../../../../../src/reprollm/rules/env.py#L123)、[151](../../../../../src/reprollm/rules/env.py#L151) | lock 存在与关键包 pin 是独立规则；关键包信用为全仓 lock 包名并集或任意 exact；warning evidence 取首个匹配声明，否则首个 import |
| [lock/writer.py:57](../../../../../src/reprollm/lock/writer.py#L57)、[lock/resolver.py:214](../../../../../src/reprollm/lock/resolver.py#L214) | `reprollm.lock` 是另一产物：绑定 manifest 等来源并捕获当前解释器/已安装元数据；不是原生包管理器 solver，不消费上述 owner 关系；本次未调用 |

`test_lockfile_counts_as_pinned` [现有测试](../../../../../tests/unit/core/test_deps.py#L209) 刻意允许 uv 的 name-only 条目。不能以 A 之名新增格式版本/freshness 校验。
`pytorch` 规范化为 `torch`。environment 的 legacy `line` 是 dependency entry index，未声称为 YAML 物理行；见 [S2 交接](../../../../dogfooding/2026-10-10-reliability-s2/s2-handoff.md#yaml-physical-source-indexunassigned_backlog)。

## 23 个离线当前实现样例

实际输入共 **54 文件 / 1860 bytes**；23 个独立预期全部匹配，观察主体 0.144516 s。
实际直接检查 23 次 critical rule、23 次 lock-presence rule；critical findings 共 3，presence findings 共 2；AST 读到 3 个 import。
以下 C/P 是当前两条规则的 finding 数，不是全 audit 结果；A 列仅为提案的预期设计，**执行数为 0**。

| ID | 最小情景 | 当前 C/P | A 的包 warning 设计预期 |
|---|---|---:|---|
| E01 | 根 loose torch，无 lock | 1/1 | torch |
| E02 | 根 loose + 无 owner 的 tools/uv.lock | 0/0 | torch |
| E03 | 根 pyproject loose + 根 uv.lock | 0/0 | 无 |
| E04 | 根 loose + 无 owner 的 tools/poetry.lock | 0/0 | torch |
| E05 | 根 Pipfile loose + 无配对子 Pipfile.lock | 0/0 | torch |
| E06 | 根 environment pytorch + 无配对子 conda-lock | 0/0 | torch |
| E07 | 同目录 Pipfile loose + uv.lock，无 import | 0/0 | torch；manager 不匹配 |
| E08 | 根 loose + 嵌套 exact requirements | 0/0 | 无；全仓 existential exact 保留 |
| E09 | 同一 requirements 同包两个冲突 exact | 0/0 | 无；不解冲突，两条均 exact |
| E10 | requirements 引 base；普通 sibling 未引用 | 0/0 | 无；closure 只有 torch，未引入 sibling vllm |
| E11 | 另有独立 requirements-extra 根 | 0/0 | 无；两个根分别是 vllm / torch，不合并闭包 |
| E12 | torch loose 根缺 include，独立 vllm exact 根 | 1/0 | torch；另根满足 presence，不覆盖 torch |
| E13 | requirements 循环，但实际读到 torch exact | 0/1 | 无；exact 声明不等于闭包 lock 合格 |
| E14 | tool-only 根 pyproject + 嵌套研究 exact | 0/0 | 无；不能回退 root-only |
| E15 | 同项目 uv 只有 package.name，无 version | 0/0 | 无；不借机扩展格式有效性判断 |
| E16 | 根 loose + TOML 损坏 uv.lock | 1/0 | torch；空 package 集合与 artifact 存在分开 |
| E17 | 根 pyproject / 嵌套 requirements 冲突 exact | 0/0 | 无；不选一个版本或一个环境 |
| E18 | 根 loose；子项目自己 loose + 合格 uv pair | 0/0 | 无；子项目有自己的在用来源，仍 existential |
| E19 | 子项目 qualified pyproject + import + uv | 0/0 | 无；最近项目内 import 可配对 |
| E20 | workspace 形状祖先 uv + 成员声明 | 0/0 | torch；A 不推断父到成员委派，可能产生兼容 warning |
| E21 | 子 pyproject 损坏 + import，祖先 uv | 0/0 | torch；已观察损坏候选为 uncertain barrier |
| E22 | 子 tool-only pyproject + import，祖先 uv | 0/0 | 无；tool-only 不是项目边界 |
| E23 | 同目录两份 environment + conda-lock | 0/0 | torch；不猜唯一 Conda owner |

E02/E04–E07 是当前格式 lock 包名跨项目或跨 manager 误授信用的最小反例；E18 是必须保留的反向边界。
E20 只构造 workspace 形状输入，未用 uv 生成或原生验证 workspace lock，不能称原生 workspace 验收。

## 可复制重放

使用已有本地开发环境，从仓库根执行。输入内容直接来自公开 JSON；观察器先核对 12 个源码/规格/测试来源的原始字节和本 checkout 的导入位置，再精确比较全部观察字段。
仅观察器和合成输入写入新建私有目录，不修改仓库产品文件；临时根的父目录必须可写，失败时保留输入。无需网络或重新安装依赖。

```powershell
$evidencePath = 'docs/plan/reliability-2026-10-03/proposals/R06-B/current-implementation.json'
$evidence = Get-Content -LiteralPath $evidencePath -Raw | ConvertFrom-Json
$observerPath = Join-Path $env:TEMP ('r06b-observer-' + [guid]::NewGuid().ToString('N') + '.py')
$workspace = Join-Path $env:TEMP ('r06b-inputs-' + [guid]::NewGuid().ToString('N'))
[IO.File]::WriteAllText($observerPath, $evidence.reproduction.observer_python, [Text.UTF8Encoding]::new($false))
.\.venv\Scripts\python.exe $observerPath $evidencePath $workspace
```

本次从公开 JSON 提取观察器，在新的显式可写私有根重放：退出 0，`cases_compared=23`，结果 `MATCHED_CURRENT_OBSERVATIONS`。
此前一次 Windows sandbox 的 `tempfile` 目录 ACL 在首个 case 的 mkdir 前报 WinError 5（退出 1、已执行 case 0）；保留为环境设置失败，不算产品失败或通过。
首次生成与最终重放均使用真实解析器/AST/规则；Git 固定为非仓库模式，`installed_versions` 仅为稳定建议文本模拟为空映射。
Python audit hook 禁止 subprocess、socket 连接/解析和重模型导入。未执行完整 CLI/engine、pytest、安装、原生 manager、锁解析网络、模型、GPU 或提供商。
本材料是文档/有界观察证据，不替代最终质量门、五项目 Gate A 或资源门，也不新增/替换 gold。

## A 的最小实施边界和验收缺口

建议只在 `core/deps.py` 内增加可解释的 manager/候选状态/配对信息，并由 `rules/env.py` 的格式 lock 包名信用分支消费；不改变公开 finding 字段、未受影响 evidence、warning 文案/提示、manifest/presence 或 exact 聚合。
声明只配对应 manager 文件：uv ↔ 同目录 `[project]` pyproject；Poetry ↔ 同目录 `[project]` 或 `[tool.poetry]` pyproject；Pipfile.lock ↔ 同目录合格 Pipfile；Conda ↔ 唯一同目录带 dependencies list 的 environment 文件。
同目录不同 manager 声明不互作证据；requirements 仍只按现有实际 `-r` 图，不新增 format-owner 根。
import 使用规范化逻辑 path components 的最近合格项目根；tool-only 不建根；已观察不可读/损坏候选构成 uncertain barrier，不能向祖先借 import 信用。
多 manager 同目录可独立配声明；import 仅在最近根无 uncertain 候选时用合格 pair。其他 manager 的坏文件不取消已明确配对的声明。双 Conda 候选不猜 owner。
保留 existential：存在一个配对的在用来源即可消除该包 warning；E18 说明 A 仍不证明根环境完整锁定。

这与 [05 的 A 方向](../../05_Policy_and_Compatibility.md)一致，但 **收紧现行 [spec §12.2](../../../01_specification.md#122-env-l0-m2)** 的“presence in a lockfile”，须先接受精确新合同并同步规格；现规则不是已经按该未来合同实施。
不需要新 workspace/schema 字段。仅内部 deps/env 调整无需触及 [D-41](../../../00_architecture_and_decisions.md) 的 redaction/engine/schema；如实现扩大到这些文件，仍须单独明确审阅，不能以本证据豁免。
Conda 复杂语法、解析深度、格式 lock validity/version/freshness、选定实验、workspace 委派、冲突求解、完整 installability 都不在 A 范围。

P-B 应先为以上关系写独立红例，再补多 manager 声明/import、显式不可读候选、相邻目录名误前缀、规范化路径、缺失 owner、空合格根与 dual-Conda 的回归；当前 23 例未执行 future A，也未覆盖权限/符号链接/竞态或全格式 fuzz。
五项目须保留完整规则/profile/hint/path/diagnostic 集合；预计现有 gold 无 delta，但该预期尚未重跑验证。
[val.md §4](../../../../../val.md#4-unpinned-llm-critical-dependency-gold) 的 HarmBench 九个 nested exact 及 [S2 的 61-row 历史 provenance](../../../../dogfooding/2026-10-10-reliability-s2/s2-handoff.md#r06-bpending_scope_decision)保持原字节，不得据当前输出重写。
