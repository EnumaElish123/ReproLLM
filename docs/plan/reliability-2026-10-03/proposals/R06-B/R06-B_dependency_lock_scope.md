# R06-B：仓库依赖汇总与 lock 覆盖的具体提案

状态：**PROPOSED，尚未批准、尚未实施**。日期：2026-10-19。
审查候选：`af8adea8ec37fb5db57373432f4ced58cec9fb9e`。
本次授权是 P-A 材料、计划状态同步和 main 交付，不是改变依赖政策。
[决定记录](decision.json)中的接受选项仍为 null；本目录的规范补丁没有应用。

## 1. 当前合同、真实证据与问题边界

本提案落实 [05 §4](../../05_Policy_and_Compatibility.md#4-r06-b依赖和-lock-的-scope)，
以[规格 §12.2](../../../01_specification.md#122-env-l0-m2)、
[S2 scope 交接](../../../../dogfooding/2026-10-10-reliability-s2/s2-handoff.md)和
[val §§2–4](../../../../../val.md#4-unpinned-llm-critical-dependency-gold)为现行合同。
现行规格明确把 unrelated subproject lock 的归属留给 R06-B，不能把本提案倒写成早已批准的行为。

必须区分三个问题：发现了哪些声明/lock；哪些路径有精确固定证据；某个具体实验环境是否完整锁定。
当前 L0 回答前两者的仓库级汇总，不能回答第三者。

当前实现的完整观察见[实现追踪](implementation-evidence.md)和
[离线观察凭据](current-implementation.json)；独立固定源码见
[五项目逐行证据](portfolio-evidence.md)及[机器可读来源](portfolio-evidence.json)。
这些是原政策的观察，不是运行了未来 A，也不是新 gold。

- `scan_dependencies` 保留根及子目录来源；同 basename 不互相覆盖。requirements 的资格和包集合来自同一个实际 `-r` 闭包。
- `env.llm_critical_deps_pinned` 先汇总所有 lock 的包名；任意 lock 有该包即不报警，其次任意声明为 exact 也不报警。
- 它没有选出一个最终版本，没有要求所有来源一致，也没有确认 lock 和依赖来源属于同一项目。
- 格式 lock 当前只提供包名索引，不据此核验其版本字段、求解正确性、平台、内容新鲜度或实际安装。
- `env.lockfile_present` 是独立的仓库级存在性检查；发现格式 lock 与证明完整环境可重建不是同一事实。

HarmBench 是保留仓库汇总的真实约束：九个关键包在 nested alignment-handbook requirements
中有 exact 声明，根 requirements 没有引用该文件。现行 L0 仍使用这些声明；不能把它们描述为根文件的 include 闭包。
DP 的 `setup.cfg` 虽含版本文字，也不是当前 §12.2 支持的声明入口，不能据此擅自消除既有 warning。

## 2. 推荐 A：保留 existential 汇总，仅收紧格式 lock 的信用

推荐 A 是一项有意的政策修订，不是把所有来源合并成一个环境。对 canonical 包名 `p`：

```text
U(p) = 当前扫描范围内该包的所有声明与 import 来源，排除 lock 自己的 package 行
X(p) = U(p) 中符合既有 exact 合同的声明
qualified(p) = X(p) 非空，或者存在一个 U(p) 来源和一个包含 p 的合格关联 lock
```

只有 `qualified(p)` 为假才产生现有的一个 `env.llm_critical_deps_pinned` WARNING。
canonical 名称、包目录、每包一条 finding、严重度、修复提示和无变化场景的证据选择保持原合同。
这仍是“至少一个来源有固定证据”，**不是**“每个来源都固定”或“根实验的所有依赖已锁定”。

具体保留：任一子项目 exact 声明仍可免除同包的仓库 warning；不同文件的冲突 exact 版本仍按当前规则免警。
A 不新增冲突裁决，不决定实验所选 extras/markers/group，不验证一组 pin 能否共同安装。
若另一个子项目自己确实使用该包且有合格 lock，该项目可为仓库 existential 结论提供证据；
根项目同包是否被覆盖依然不能由这个 PASS 推出。

### 2.1 合格关联的封闭定义

以下都是**拟议的 ReproLLM 静态政策**。官方包管理器资料提供格式事实，不能替代维护者的选择。
所有路径沿用已有 scanner 的根内、已规范化逻辑相对路径和安全读取；按路径 component 比较，`app` 不包含 `app2`。
允许根内 alias 的既有读取合同不变；物理同一、symlink 或别名本身不建立额外 owner 关系。
不扩大扫描范围，不遍历根外，不凭目录距离猜测跨目录关系，不执行包管理器或运行用户代码。

| 格式 lock | 允许的同目录配对 manifest | 声明来源信用 |
|---|---|---|
| `uv.lock` | 可解析、含 `[project]` table 的 `pyproject.toml` | 仅该 pyproject 中现已支持的声明 |
| `poetry.lock` | 可解析、含 `[project]` 或 `[tool.poetry]` table 的 `pyproject.toml` | 仅该 pyproject 中现已支持的声明 |
| `Pipfile.lock` | 可解析且有 `packages` 或 `dev-packages` table 的 `Pipfile` | 仅该 Pipfile 中现已支持的声明 |
| `conda-lock.yml` | 唯一的、可解析且有 `dependencies` list 的 `environment.yml` 或 `environment.yaml` | 仅该 environment 中现已支持的声明，含其 pip 子项 |
| 完整 exact requirements 根 | 沿用 R06-P 的实际 `-r` 可达闭包 | 仅该闭包实际成员；不借未引用 sibling |

同目录不同 manager 的声明不互作格式 lock 信用：例如只有 loose requirements 声明、没有对应 pyproject 声明或 import，
不能仅因同目录有 uv.lock 就免警。Conda 两个环境文件都存在时，不猜应配哪一个；本阶段不使用
lock 中的跨目录 sources、workspace/glob、或用户未声明的安装命令推断关系。
requirements 根只提供已有闭包事实，不自动创建格式 lock 的项目边界。

import 没有对应的声明文件，按以下规则取得有限的同项目证据：

1. 在已观察的候选中，可解析的上述 pyproject / Pipfile / environment 结构创建项目根目录。
   同目录可以有多个 manager，各自配对；没有 runtime 项目结构的 tool-only/build-system-only pyproject 不创建根。
2. 对一个 import 文件，取其路径祖先中最近的项目根；不跨过更近的项目根借祖先 lock。
   有效 pair 的目录必须恰为这个根。仅仅同包名、相同 basename、字符串路径前缀均不够。
3. 已观察到但不可读或语法损坏的这些 manifest 候选形成 uncertain barrier。
   其目录下的 import 不向祖先借信用；该目录存在此不确定候选时，推断型 import 信用也不成立。
   已明确配对的另一个 manager 的声明证据不因此被取消。原诊断保留，不能把 unknown 伪装成已覆盖。
   barrier 只阻断跨越该目录向上的信用；更深的独立合格项目根仍可用自己的同目录 pair，不能被外层坏文件全局否决。
4. 对 Conda 的双文件歧义不建立 Conda pair。UV workspace 成员不向父级共享 lock 委派；
   需要该功能时另行设计明确的 membership/排除/兼容合同，不能悄悄加入 A。

未证明归属的 lock 仍保留在 inventory 中，不丢弃来源；只是不能借其包名免除这个包的 warning。
requirements 的读取安全、循环/深度/共享节点、支持语法及 closure qualification 完全沿用 R06-P。
`-c` 不是 `-r`，不在本方案中新增 constraints 支持；unsupported 指令仍使相应根不构成完整 lock。
官方 [pip requirements 格式](https://pip.pypa.io/en/stable/reference/requirements-file-format/)区分这两种引用，
[constraints 说明](https://pip.pypa.io/en/stable/user_guide/#constraints-files)也不把约束本身视作安装请求；
这里不据官方更宽的语法自动扩展 ReproLLM 的有界 parser。

### 2.2 保持独立的消费者

`env.dependency_manifest_present`、`env.lockfile_present` 不改。
后者继续按当前仓库 artifact 存在性逻辑判断：无 owner、空或损坏格式 lock 的存在性结果也不在 A 中修订。
这意味着 “lockfile_present PASS + critical 包 WARNING” 是有意允许的结果，不能视作相互矛盾。
版本字段验证、lock freshness、跨平台求解、哈希完整性与是否实际安装属于其他合同；A 不新增这类保证。

## 3. before / after、输出与退出行为

以下是独立验收设计；after 尚未实施或执行。未说明时没有其他 L0 finding，包为 `torch`，声明为 loose。

| 输入 | 当前包 warning | A 后包 warning | presence 变化 |
|---|---:|---:|---|
| 根 pyproject + 根 uv.lock，包在对应声明和 lock 中 | 无 | 无 | 无 |
| 根使用包，只有无关联 nested lock 记录该包 | 无 | 有 | 无，仍记录 lock 存在 |
| 根使用包，nested 有 own manifest 但没有该包声明/import，只有 lock 行 | 无 | 有 | 无 |
| nested 自己也声明/导入该包，own manifest/lock 合格 | 无 | 无；仅仓库 existential 结论 | 无 |
| 根 loose，独立 nested exact 声明该包，无 lock | 无 | 无 | 无 |
| 跨文件两个不同 exact 版本 | 无 | 无；不保证可共同安装 | 无 |
| 根 requirements `-r` 引用 exact 内部文件 | 无 | 无；包集合只取可达成员 | 无 |
| root closure 未引用的 sibling 包 | 不能给该 root 增加包集合 | 相同；其独立 exact 声明仍可参与全仓汇总 | 无 |
| 同目录 loose requirements + uv.lock，缺 pyproject 声明/import | 无 | 有 | 无 |
| 只有 tool-only pyproject + lock + import，无可配对项目 manifest | 无 | 有 | 无 |
| 子项目 import 被更近 manifest/uncertain barrier 隔开，仅祖先 lock 含包 | 无 | 有 | 无 |
| 外层 manifest 损坏，更深项目有有效 manifest/own lock 与 import | 无 | 无；更深项目可自行配对 | 无 |
| UV workspace 只有父 lock，成员有 loose 声明/import，父项目无该包来源 | 无 | 有，A 不实现共享 lock 委派 | 无 |
| Conda 双环境歧义，只有 loose/导入来源与 lock 包名 | 无 | 有 | 无 |

新增 finding 沿用现有字段、ID、WARNING 严重度、单条包粒度及安全路径。例子仅展示新出现的结论，不虚构已生成的完整 JSON：

```text
env.llm_critical_deps_pinned: torch is used but not pinned to an exact version
```

默认 audit 的 CRITICAL fail-on 不会仅因这条 WARNING 改变 exit；显式 `--fail-on warning` 在无其他 finding 的反例中由 0 变 1；
`--fail-on never` 继续 0。完整 summary、GitHub annotation 及 export 的当前 audit 会显示这条新增 warning。
实际 tests 应用受控 installed-version fixture 断言完整 message/hint/evidence，而不是照抄本机版本。

## 4. 备选、兼容与历史

| 选择 | 范围、代价 |
|---|---|
| **A（推荐）** | 保留 L0 全仓与 existential exact 语义；格式 lock 信用需上述关联。能修无关联 lock 掩盖，但不承诺 root 环境完整性；共享 workspace 可能新增保守 warning |
| B：显式实验 dependency scope | 对选定环境要求逐来源覆盖；须另提选择入口、默认解释、workspace/group/constraints 合同及旧文档迁移；当前不添加字段或提前实现 |
| C：默认 root-only | 会丢失 HarmBench 等有效 nested exact 来源，改变既有 gold；没有独立新 gold 与批准时不可采用 |

UV 官方 [workspace 文档](https://docs.astral.sh/uv/concepts/projects/workspaces/)明确成员可共享一份 lock，
因此 A 对共享成员的保守限制是已知兼容成本，不能宣传为 UV 原生行为。
[conda-lock 的来源文档](https://conda.github.io/conda-lock/basic_usage/)也涵盖多种格式；
A 不声称同目录唯一文件规则覆盖其全部语义。其余[官方资料与推断边界](official-sources.json)逐项区分事实和设计选择。

| 数据 / 读写组合 | 兼容承诺 |
|---|---|
| 已有 manifest1 / lock1 / run1、run2 | 格式及其原本支持的读取范围不变；不写入 scope 字段、不升级 schema、不迁移旧文件 |
| 新 audit1 / export 与旧读者 | 字段、规则 ID、合法 WARNING 枚举不变；某些原先被 foreign lock 掩盖的 warning 可新增 |
| 历史 audit/diff/export/run 与 provenance | 保留原字节、候选、日期和既有解释；不重写为新政策通过/失败 |
| 用户的 audit 阈值、suppressions、自定义规则 | 沿用现有合同；新 warning 可按原规则触发显式门槛 |
| 旧格式 lock、仅有新包管理器格式或不支持的声明 | 不增加格式支持、不运行 solver；保留当前 inventory/诊断及明确限制 |

A 不修改 persisted schema、profiles、默认严重度、source/runtime precedence 或 D-41 的 engine/redaction/schema 文件。
仅扩大内部 provenance 不自动构成持久化 schema；若实施发现必须暴露新结构，应停下那部分另提方案。
发布/版本决定另行处理，本次及未来 P-B 概括授权都不等于付费、GPU、HF 授权或版本发布。

## 5. 精确实施清单与独立验收

本次仅准备材料。接受 A 后的 P-B 预定文件：

| 文件 | 批准后变更 |
|---|---|
| `src/reprollm/core/deps.py` | 保留现有 inventory/closure，增加不持久化的合格 manifest、pair、来源关系与 uncertain barrier 事实 |
| `src/reprollm/rules/env.py` | 仅替换 critical 包的全仓格式 lock 名字信用分支；保留 exact 及 presence 两个独立合同 |
| `tests/unit/core/test_deps.py`、`tests/unit/rules/test_env.py` 及现有 audit CLI 测试 | 先用独立输入建立 RED，后实施 GREEN；真实消费者验证阈值/完整 JSON |
| 规格 §12.2、CHANGELOG、依赖说明 | 应用经接受的[规范草稿](spec-proposed.patch)，说明兼容成本与当前政策版本 |
| fixtures / 五项目 gold | 只有确实受影响且有独立依据时另审；当前五项目预期零 delta，不自动重建快照 |

未来验收至少覆盖上表全部 before/after、四种格式配对的正反例、nested 自身来源仍可提供信用、
同目录跨 manager、Conda 双文件、workspace 不委派、tool-only 与坏文件 barrier、component 边界、
根内规范化 `..` 和 alias、根外/绝对/符号链接逃逸拒绝、actual include 与未引用 sibling、shared/cycle/missing/depth 情形、
同包冲突及 namespace/case canonicalization。验证 inventory 不丢项、完整 finding 集、thresholds、确定性 JSON 和历史字节。
它们是待实现的验收测试，不能把本轮原程序的观察写成这些测试已经通过。

五项目的来源、原 warning 集及逐项预期在 portfolio evidence 中。
A 不改变它们的支持来源和 requirements 闭包，且没有格式 lock 可产生新的 ownership 差异，因此预期：

| 项目 | 现有关键包 warning 数 | A 后预期 |
|---|---:|---|
| lm-evaluation-harness | 13 | 完整集合、位置、提示、profiles、hints、diagnostics 不变 |
| FastChat | 15 | 同上 |
| LlamaFactory | 14 | 同上；保留 tracked `.env.local` CRITICAL |
| HarmBench | 5 | 同上；九个 nested exact 包继续免警，不能改成 root-only |
| llm-dp-finetune | 5 | 同上；不扩展 setup.cfg 支持 |

这里的完整输出不变是拟保留的验收目标，不是本轮新鲜产品 PASS。
若实施时新增 provenance 的外部展示改变完整 facts/message，必须先补充精确输出设计和独立审阅；
零 package-set delta 不能替代完整 JSON、paths、hints 与 diagnostics 的比较。

批准后必须运行一次最终完整质量门、fresh 五项目 Gate A，以及受影响的 audit/init/lock/run/export 消费扩展。
先审阅实际影响矩阵，不机械复制全部无关格式组合。P-B 不是里程碑/发布时不自动重复 GPU、付费或 HF gate；
触及对应合同或准备 release 时再按 val 激活，缺资源记 BLOCKED。

## 6. 本次检查与可裁决问题

本轮是**纯文档/提案会话**：现行实现、测试、schemas、profiles、依赖、CI 和验证工具均未改；
没有应用 patch，合成观察仅运行原程序。按[验证流程 §3](../../../validation-workflow-2026-10-13.md#3-执行频率唯一权威定义)，
完整本地产品质量门、Gate A/B 为 NOT_APPLICABLE，不能声称新鲜 PASS。
本轮执行链接、内容、来源/hash、unapplied patch 和范围检查；最终推送 main 的 CI 单独核验。
详见[会话报告](../../../../dogfooding/2026-10-19-r06b-pa.md)。

可接受 A 的精确定义、兼容边界与验收设计，随后授权单独 P-B；或选择 B 单独设计显式环境 scope；
或维持当前合同。选择 C 须先提出独立 gold 变更依据。当前没有 R06-B 接受记录。
接受 A 不批准 workspace 委派、∀环境完整性、格式扩展、版本/freshness 验证、未知扫描结论、
新 schema、R07-C/R08-B 或任何资源/发布动作。
