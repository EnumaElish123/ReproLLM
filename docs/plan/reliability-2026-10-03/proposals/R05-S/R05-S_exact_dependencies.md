# R05-S：精确版本与 requirements-as-lock 规范提案

状态：**PROPOSED，尚未批准**。核对日期：2026-10-10。审阅基线：e9ed0991089f50ce1b3369344dda87d8c0cbfa7c（S1-B R03）。任务：R05-S；关联 R05-A / R06-P / R05-B。本文件只提出规范与验收合同，不修改 normative spec 或产品行为，不表示任何测试/资源 Gate 已通过。

## 1. 供维护者直接裁决的范围

建议分别批准 **A/P：Python exact 与实际 requirements 闭包**、**C：Conda 的有限 MatchSpec 子集**。两个范围当前都为 PROPOSED。接受 A/P 不代表接受 C；未明确接受 C 时 R05-B 保持 blocked，Conda 当前行为保持旧合同。接受两者后，才按 S2-A R06-G → R05-A → R06-A、S2-B R06-P → R05-B 顺序实施和验收。

A/P 接受：排除 wildcard 的 exact 判断；识别合法 local/pre/post/dev/epoch；保留 Poetry bare-version 语法而不扩展其他格式；exact、requirements-as-lock 和 finding 共用结论；requirements lock 仅由完整、非空、实际根内 include 闭包证明。

C 接受：无 build 单等号是 prefix；双等号和精确三段 export 形式在下列有限子集内是 version-exact；不新增 Conda runtime/solver 或持久化 build 字段。下述保守负例属于支持边界，不意味着官方 Conda 不支持这些表达式。

不在本决定范围：R06-B 全仓/子项目环境选择政策；任意 lock 覆盖整个仓库；root-only 扫描；新增 schema；engine/redaction 改动；网络求解、安装依赖或执行文件内容；完全相同 wheel/build/index/platform/hash 保证。

## 2. 当前合同、明确缺陷和真实冲突

规范 §12.2:876 将 requirements-as-lock 写为每个非注释行使用双等号；:877 将 Conda 无 build 的单等号加完整版本视为精确。任务卡 R05-A:69/76 要求 wildcard 不能使 requirements 成为 exact lock；R06-P:153-154 要求完整图与真实可达包；R05-B:200-214 要求不同的 Conda 语义。纯 parser 的合法版本误判、同名路径覆盖和根外读取是明确缺陷；但变更上述规范字句所直接规定的 consumer 判断，需要具体 R05-S 决定。开发方案批准或“执行 S2”并不等于批准本提案的新字句。

既有授权允许继续 R06-G 读取保护和 R06-A 完整路径身份/root 优先，不需要等待 R06-B。05_Policy_and_Compatibility.md:18/101 明确只停依赖新语义的部分、不机械阻塞明确缺陷。R05-A 可准备独立支持矩阵与 parser 回归；若包括 wildcard → env.lockfile_present 联动，则先接受本 A/P 合同。R06-P 的路径保护/图来源修复可推进；新的闭包 lock 资格判断采用本 A/P 合同后合入。R05-B 必须有 C 的明确接受记录。

当前源码：core/deps.py 的 requirements/PEP621 只检查单个双等号，不排除 wildcard；Poetry/Pipfile 使用数字点正则；Conda 按等号拆字符串；requirements lock package 归属使用同目录子树近似，并把已访问 cycle 当成功。rules/env.py 使用 is_exact 或 lock packages 抑制 critical-package warning。这些是源码推导，本文不冒充已经执行过 RED 的结果。

## 3. 当前官方 primary sources

以下 URL 已通过 browser 在 2026-10-10 核对；不引用二手文章，不导入或安装 Conda。

| 来源 | 直接支持的事实 |
|---|---|
| [PyPA Version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-matching) | 非 wildcard 双等号为版本相等；带末尾 wildcard 为前缀。合法版本包含 pre/post/dev/epoch/local；未指定 local 时不区分候选 local 变体。 |
| [PyPA Dependency specifiers](https://packaging.python.org/en/latest/specifications/dependency-specifiers/#grammar) | 版本、extras、markers 和 URL 是不同的语法部分；marker 限定环境。 |
| [pip Requirements file format](https://pip.pypa.io/en/stable/reference/requirements-file-format/) | 文件包含 requirement、指令、URL/path 等不同条目；include 与 constraints 不等同；完整 pip 语法不适合冒充本工具的小型静态支持子集。 |
| [Poetry Dependency specification](https://python-poetry.org/docs/dependency-specification/#exact-requirements) | Poetry version field 的 bare version 与双等号可为 exact；caret/tilde/wildcard 表达范围。 |
| [Pipenv Pipfile](https://pipenv.pypa.io/en/latest/pipfile.html#packages-section) | Pipfile 使用双等号表示 exact，支持 version 字段及 extras/markers/URL/path 结构。 |
| [Conda MatchSpec](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/) | 无 build 单等号被规范化为前缀；export 的三段形式可以是 exact version/build；完全指定包还需要 channel/subdir 等独立维度。 |

Browser 可见的文档版本为 Conda 26.7.2、pip 26.2.1、Pipenv 2026.8.0。这里只用其语法合同建立有限支持子集，不声称运行过这些工具。PyPA equality 中省略 local label 的限制尤其说明，version-exact 不等于相同 CUDA build 或安装产物。

## 4. §12.2 精确 before / after

原始两行如下，来自审阅基线文件，severity/min_level/applies/rule ID 不变：

~~~markdown
| `env.lockfile_present` | WARNING | dependency manifest present | no `uv.lock` / `poetry.lock` / `Pipfile.lock` / `conda-lock.yml` and no `requirements*.txt` where every non-comment line uses `==` |
| `env.llm_critical_deps_pinned` | WARNING | any LLM-critical package (§4.4) appears in declarations **or** imports | for each such package, no declaration pins it exactly: pip-style `==`, conda-style `name=version` in `environment.yml` (single `=` with a full version), or presence in a lockfile; one finding per package. `pytorch` in conda counts as `torch`. |
~~~

A/P 单独接受后的两行：

~~~markdown
| `env.lockfile_present` | WARNING | dependency manifest present | no `uv.lock` / `poetry.lock` / `Pipfile.lock` / `conda-lock.yml` and no `requirements*.txt` satisfying the complete exact requirements closure contract below |
| `env.llm_critical_deps_pinned` | WARNING | any LLM-critical package (§4.4) appears in declarations **or** imports | for each such package, no declaration pins its version exactly under the Python contract below, the existing Conda-style `name=version` in `environment.yml` contract (single `=` with a full version), or presence in a lockfile; one finding per package. `pytorch` in conda counts as `torch`. |
~~~

A/P 与 C 都接受后的两行：

~~~markdown
| `env.lockfile_present` | WARNING | dependency manifest present | no `uv.lock` / `poetry.lock` / `Pipfile.lock` / `conda-lock.yml` and no `requirements*.txt` satisfying the complete exact requirements closure contract below |
| `env.llm_critical_deps_pinned` | WARNING | any LLM-critical package (§4.4) appears in declarations **or** imports | for each such package, no declaration pins its version exactly under the Python or supported Conda contracts below, or presence in a lockfile; one finding per package. `pytorch` in conda counts as `torch`. |
~~~

在 env.reprollm_initialized 行后追加以下 A/P normative text：

~~~markdown
**Python exact-version contract.** For requirements declarations, PEP 621 project dependencies and optional dependencies, embedded pip declarations, and Pipfile version fields, a supported valid version constraint is exact only when its parsed specifier contains one non-wildcard `==` version clause. A valid PEP 440 version may contain local, pre-release, post-release, development-release, or epoch components. Poetry dependency version fields also accept a valid bare PEP 440 version as exact, in addition to the same single `==` form. Ranges, wildcard/prefix matching, unversioned declarations, URL/VCS/path dependencies, unsupported syntax, arbitrary equality (`===`), and multiple distinct clauses are not accepted as exact by this bounded static contract. Preserve each format's grammar; do not treat a bare requirements or Pipfile version as a Poetry version field.

Exact means a version constraint, not identity of a build, wheel, index, platform, or file hash. A public `==` pin does not distinguish local variants unless a local label is explicitly included. Extras and markers do not remove an otherwise exact version constraint, but this audit does not claim the same installation on every platform or resolve transitive dependencies.

**Complete exact requirements closure.** Evaluate each discovered `requirements*.txt` root from its actual supported `-r` / `--requirement` include edges, relative to the containing file's directory, after normalization and root-containment checks. Allow normalized internal `..`; reject absolute or escaping targets before reading. A qualifying closure has at least one valid package declaration, every reachable package declaration meets the Python exact-version contract, and every include edge is resolved. Cycles, depth-limit exhaustion, unreadable/missing/escaping files, malformed declarations, and unsupported directives prevent that root from qualifying. Blank lines and comments do not count as declarations. Repeated/shared nodes are deduplicated and are not cycles unless encountered on the active recursion stack. The lock's package set contains only declarations actually reachable from that root, never an unreferenced sibling. Use one graph/result for qualification and package membership. This does not replace the existing L0 repository aggregation contract or decide ownership of unrelated subproject lockfiles (R06-B).
~~~

仅在 C 也被明确接受后追加以下 normative text，替换 A/P 阶段保留的 Conda 旧句：

~~~markdown
**Supported Conda exact-version contract.** Parse the bounded simple MatchSpec subset independently of Python/PEP 440 grammar. For a literal package name and a numeric release version (`N(.N)*`), `name==version` is version-exact. The export forms `name=version=build` and `name==version=build` are version-exact when the build is a non-empty literal composed of ASCII letters, digits, `.`, `_`, `+`, or `-`. Single `name=version` without build is prefix matching and is not exact, regardless of the number of version components. Unsupported channel/subdir/bracket/regex/range/compound forms, wildcard versions or builds, empty or malformed parts, and version forms outside this explicitly supported subset are not accepted as exact; diagnose them conservatively without running Conda or a solver. Preserve the original supported version/build declaration as evidence. Build equality is a separate fact; the audit adds no build field and does not infer channel, platform, or artifact-hash identity. Embedded `pip:` entries follow the Python contract above. `pytorch` retains its canonical mapping to `torch`.
~~~

两份完整 unified diff 分别是 spec-A-P-proposed.patch 与 spec-A-P-C-proposed.patch。它们只是 proposal 附件，没有应用到当前规范。建议用户一次裁决 A/P 与 C；如果只接受 A/P，明确保留 Conda 的兼容冲突及 R05-B blocked 状态，不把 C 的目标例表用作当前测试期望。

## 5. 有限格式支持与独立负例

表中的版本实例是合成输入。合法判断依赖各格式语法；“非 exact”不自动意味着该表达式在该生态无效。多个不同限制可能数学上等价于单版本，本轮也不求解这种交集。

| 格式/输入 | 提议 A/P exact | 当前实现（源码推导） | finding 方向 |
|---|---|---|---|
| requirements 或 PEP621 torch==2.5.* | 否 | 是 | 该包从无 warning → WARNING；纯此根 requirements 从 lock PASS → WARNING |
| requirements 或 PEP621 torch==2.5.1 | 是 | 是 | 不变 |
| requirements 或 PEP621 torch==2.5.1+cu121 | 是 | 是 | 不变；local 精确不保证 wheel/hash |
| requirements 或 PEP621 torch==2.5.1rc1 / .post1 / .dev1 / 1!2.5.1 | 是 | 是 | 不变；Poetry/Pipfile 同类合法值当前会误拒，修复后不再 warning |
| Poetry torch = "2.5.1" | 是 | 是 | 不变 |
| Poetry torch = "==2.5.1" | 是 | 否 | 该包 WARNING → 无 warning |
| Poetry torch = "2.5.1+cu121"，或 version field 相同值 | 是 | 否 | 该包 WARNING → 无 warning |
| Pipfile torch = "==2.5.1+cu121"，或 version field 相同值 | 是 | 否 | 该包 WARNING → 无 warning |
| Poetry ^2.5 / ~2.5 / 2.5.*；Python >=2.5 / ~=2.5 / * / 无版本 | 否 | 否 | 保持 WARNING；不引入 solver |
| 多个不同 specifier clause；任意 === 值 | 否（有限子集） | 否 | 保持保守 WARNING；不推断数学上的单版本 |
| requirements torch2.5.1 / torch=2.5.1；Pipfile bare 2.5.1 | 否 | 否 | 不将 Poetry bare 语法移植到其他格式 |
| torch[extra]==2.5.1; python_version<"3.12" | 版本是 exact | 是 | 保持现有 L0 声明汇总；不把 marker 当全平台安装证明 |
| URL/VCS/path、malformed、非法 local wildcard、unsupported directive | 不作为 exact 证明 | 既有保守路径 | 不执行或联网；诊断安全、不崩溃；不算完整 requirements lock |

Python 各格式 PASS/FAIL 例必须成对覆盖，验证 name canonicalization、source_file 与物理行号、原 specifier/raw evidence 保留、decl.is_exact、lock.packages、两个 env 消费规则以及 JSON 的完整 warning 集。

C 的有限子集单独列出。先保留旧 Conda 结果，取得 C 决定后才变更以下期望：

| Conda 输入 | 当前 exact（源码推导） | 提议 C exact / 维度 | 相关 finding |
|---|---|---|---|
| python=3.11 | 是 | 否，prefix | Python 版本“已声明”仍 PASS；python 非 critical 包，没有新增 critical-package warning |
| torch=2.5 或 torch=2.5.1 | 是 | 否，prefix；不按点数猜 | 新增 torch WARNING |
| torch==2.5.1 | 否 | 是，version | 移除 torch WARNING |
| pytorch==2.5.1 | 否 | 是，映射到 torch | 移除 torch WARNING，包名别名不变 |
| torch=2.5.1=cuda12.1 | 是 | 是，version 与 literal build 分别精确 | warning 集不变；不声称 channel/platform/hash 相同 |
| torch==2.5.1=cuda12.1 | 否 | 是，canonical version/build 形式 | 移除 torch WARNING |
| torch=2.5.1=cuda* | 是 | 本轮子集外，保守不接受 exact 证明；不把版本维度与 build 维度混为官方语义 | torch WARNING + 安全 unsupported 说明 |
| torch==2.5.*、torch>=2.5、channel::torch==2.5.1、bracket/regex/compound、空/畸形字段、非数字发布 version | 子集不可靠 | 否，保守且说明 unsupported / malformed | 不推断 exact，不调用 Conda；audit 不崩溃 |
| environment.yml 嵌套 pip: torch==2.5.1+cu121 | 是 | 使用 A/P Python helper，保持是 | 不改 Conda 语法来解析 pip 子项 |

C 不新建 build schema。支持 literal build 仅保留现有源字符串/证据。未支持的合法 Conda 表达式可产生保守 warning，不可静默当成完全固定。

## 6. requirements 图与 consumer 独立验收表

| 图/内容 | 提议锁资格与 package membership | 消费者预期 |
|---|---|---|
| requirements.txt: torch==2.5.1 | 合格，{torch} | lockfile_present PASS、torch 无 warning |
| requirements.txt: torch==2.5.* | 不合格 | 无其他 lock 时 lockfile_present WARNING；torch WARNING |
| root -r deps/base.txt；base torch==2.5.1；未引用 deps/unused.txt transformers==4.45.2 | 合格，只有 {torch} | unused 不是此根 lock 的包；不得以它抑制另一个进口包的 warning |
| base -r ../common.txt；common numpy==2.1.2，规范化仍在 root | 合格，{torch,numpy} | 内部 .. 合法，全部 source_file 规范化相对 root |
| root 含 torch>=2.5；未引用 sibling 有 torch==2.5.1 | 此 root 不合格 | sibling 不“修复”该 root；如 sibling 本身另为独立发现的合格 requirements 根，既有全仓声明聚合仍独立存在，此提案不决定 R06-B |
| 重复边/diamond shared node | 合格时按真实闭包去重 | 不重复读取或重复声明、不误报 cycle |
| A→B→A，包括空循环；超深/缺文件/不可读/malformed/unsupported | 不合格 | 有来源路径/引用行定位；audit 不崩溃；不能报完整 exact lock |
| 绝对 target、外部相对 target、symlink escape | 读取前拒绝；不合格 | 外部 open spy 为零；无绝对路径/用户名/主机/内容回显 |
| empty / comments-only root | 不合格（无声明） | 不因 vacuous truth 宣称 lock |

本图仅由 -r / --requirement 的实际边建立。支持哪些紧凑拼写沿 R06-P task card 的 bounded parser 明确记录；若 -c、index/hash/editable/URL 等指令不在本轮支持表中，记为 unsupported，不假装解析完整 pip CLI。正常可读声明可继续汇总，但不用于证明不完整图的 lock 资格。

## 7. 五个 pinned repositories 的独立 expected finding/gold 差异

独立 source-provenance 表由固定 Git 源、tomllib 对 PEP621 原值、packaging 的语法及 bounded AST 导入建立，完全没有 ReproLLM import/命令/当前输出。接受的 warning 集来自 val.md §4，来源派生集合与它们逐包一致；不是把当前输出升级为 gold。完整源 hash、raw declaration、物理行、首个导入/计数见 source-critical-provenance.json。

| 项目 | pin | current accepted → proposed warnings | lock finding | 预计 delta |
|---|---|---|---|---|
| lm-evaluation-harness | b954108c9baaaa934b4ad842033b31a97ee30816 | 13 → 13 | WARNING → WARNING | 无 |
| FastChat | 587d5cfa1609a43d192cedb8441cac3c17db105d | 15 → 15 | WARNING → WARNING | 无 |
| LlamaFactory | 673048c6a543cbbeaed5b8444b8223dc4e23c721 | 14 → 14 | WARNING → WARNING | 无；tracked .env.local CRITICAL 保持 |
| HarmBench | 8e1604d1171fe8a48d8febecd22f600e462bdcdd | 5 → 5 | WARNING → WARNING | 无；nested nine exact 保持 |
| llm-dp-finetune | 7f8b5dff4b92aae90ceccce3ec959b48307bed9e | 5 → 5 | WARNING → WARNING | 无 |

固定源没有 environment/Pipfile/标准格式 lock、active Python == wildcard、requirements include 指令或冲突 basename。因而 A/P 与 C 对未变更五 pins 没有 version/graph/basename gold 集合变化；Conda 新例只在 disposable fixture/copy 中验收。absence of these inputs 不证明 parser 正确，所以合成矩阵仍是必需。L0 root/子项目来源聚合保留：HarmBench 的 nested alignment-handbook 并非由根 requirements include 引入，九个 pin 本来就是已接受的仓库级声明证据。R06-P 不可把“不属于根 lock”偷换为“整个 L0 丢弃它们”。

### lm-evaluation-harness：逐包 source 与 current accepted → proposed

| critical 包 | 固定源声明或 import-only 依据（物理行） | current accepted → proposed | delta |
|---|---|---|---|
| accelerate | [pyproject.toml:56](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L56)：accelerate>=0.26.0 | WARNING → WARNING | 无 |
| anthropic | import-only [lm_eval/models/anthropic_llms.py:47](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/models/anthropic_llms.py#L47)：anthropic | WARNING → WARNING | 无 |
| datasets | [pyproject.toml:21](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L21)：datasets>=2.16.0 | WARNING → WARNING | 无 |
| evaluate | [pyproject.toml:23](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L23)：evaluate>=0.4.0 | WARNING → WARNING | 无 |
| lm_eval | [pyproject.toml:98](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L98)：lm_eval[discrim_eval]<br>[pyproject.toml:99](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L99)：lm_eval[ifeval]<br>[pyproject.toml:100](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L100)：lm_eval[japanese_leaderboard]<br>[pyproject.toml:101](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L101)：lm_eval[longbench]<br>[pyproject.toml:102](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L102)：lm_eval[libra]<br>[pyproject.toml:103](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L103)：lm_eval[math]<br>[pyproject.toml:104](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L104)：lm_eval[multilingual]<br>[pyproject.toml:105](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L105)：lm_eval[ruler] | WARNING → WARNING | 无 |
| numpy | [pyproject.toml:22](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L22)：numpy<br>[pyproject.toml:65](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L65)：numpy<br>[pyproject.toml:70](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L70)：numpy<br>[pyproject.toml:95](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L95)：numpy | WARNING → WARNING | 无 |
| openai | import-only [lm_eval/models/openai_completions.py:382](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/models/openai_completions.py#L382)：openai | WARNING → WARNING | 无 |
| peft | [pyproject.toml:56](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L56)：peft>=0.2.0 | WARNING → WARNING | 无 |
| sentencepiece | [pyproject.toml:83](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L83)：sentencepiece<br>[pyproject.toml:91](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L91)：sentencepiece>=0.1.98 | WARNING → WARNING | 无 |
| sglang | import-only [lm_eval/models/sglang_causallms.py:25](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/lm_eval/models/sglang_causallms.py#L25)：sglang | WARNING → WARNING | 无 |
| torch | [pyproject.toml:56](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L56)：torch>=1.8 | WARNING → WARNING | 无 |
| transformers | [pyproject.toml:56](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L56)：transformers>=4.1<br>[pyproject.toml:65](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L65)：transformers<br>[pyproject.toml:70](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L70)：transformers | WARNING → WARNING | 无 |
| vllm | [pyproject.toml:57](https://github.com/EleutherAI/lm-evaluation-harness/blob/b954108c9baaaa934b4ad842033b31a97ee30816/pyproject.toml#L57)：vllm>=0.18 | WARNING → WARNING | 无 |

### FastChat：逐包 source 与 current accepted → proposed

| critical 包 | 固定源声明或 import-only 依据（物理行） | current accepted → proposed | delta |
|---|---|---|---|
| accelerate | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：accelerate>=0.21 | WARNING → WARNING | 无 |
| anthropic | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：anthropic<br>[pyproject.toml:25](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L25)：anthropic>=0.3 | WARNING → WARNING | 无 |
| datasets | import-only [fastchat/serve/monitor/dataset_release_scripts/arena_33k/upload_hf_dataset.py:5](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/monitor/dataset_release_scripts/arena_33k/upload_hf_dataset.py#L5)：datasets | WARNING → WARNING | 无 |
| deepspeed | import-only [fastchat/train/train_lora.py:24](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/train/train_lora.py#L24)：deepspeed | WARNING → WARNING | 无 |
| flash_attn | [pyproject.toml:24](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L24)：flash-attn>=2.0 | WARNING → WARNING | 无 |
| numpy | [pyproject.toml:16](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L16)：numpy | WARNING → WARNING | 无 |
| openai | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：openai<br>[pyproject.toml:25](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L25)：openai<1 | WARNING → WARNING | 无 |
| peft | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：peft | WARNING → WARNING | 无 |
| safetensors | import-only [fastchat/model/compression.py:184](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/model/compression.py#L184)：safetensors.torch | WARNING → WARNING | 无 |
| sentencepiece | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：sentencepiece | WARNING → WARNING | 无 |
| sglang | import-only [fastchat/serve/sglang_worker.py:17](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/sglang_worker.py#L17)：sglang | WARNING → WARNING | 无 |
| torch | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：torch | WARNING → WARNING | 无 |
| transformers | [pyproject.toml:22](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/pyproject.toml#L22)：transformers>=4.31.0 | WARNING → WARNING | 无 |
| vllm | import-only [fastchat/serve/vllm_worker.py:15](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/serve/vllm_worker.py#L15)：vllm | WARNING → WARNING | 无 |
| xformers | import-only [fastchat/train/llama_xformers_attn_monkey_patch.py:14](https://github.com/lm-sys/FastChat/blob/587d5cfa1609a43d192cedb8441cac3c17db105d/fastchat/train/llama_xformers_attn_monkey_patch.py#L14)：xformers.ops | WARNING → WARNING | 无 |

### LlamaFactory：逐包 source 与 current accepted → proposed

| critical 包 | 固定源声明或 import-only 依据（物理行） | current accepted → proposed | delta |
|---|---|---|---|
| accelerate | [pyproject.toml:45](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L45)：accelerate>=1.3.0,<=1.11.0 | WARNING → WARNING | 无 |
| bitsandbytes | import-only [src/llamafactory/extras/env.py:75](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/src/llamafactory/extras/env.py#L75)：bitsandbytes | WARNING → WARNING | 无 |
| datasets | [pyproject.toml:44](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L44)：datasets>=2.16.0,<=4.0.0 | WARNING → WARNING | 无 |
| deepspeed | import-only [scripts/stat_utils/cal_flops.py:20](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/scripts/stat_utils/cal_flops.py#L20)：deepspeed.accelerator | WARNING → WARNING | 无 |
| numpy | [pyproject.toml:55](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L55)：numpy | WARNING → WARNING | 无 |
| openai | import-only [scripts/api_example/test_image.py:17](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/scripts/api_example/test_image.py#L17)：openai | WARNING → WARNING | 无 |
| peft | [pyproject.toml:46](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L46)：peft>=0.18.0,<=0.18.1 | WARNING → WARNING | 无 |
| safetensors | [pyproject.toml:63](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L63)：safetensors | WARNING → WARNING | 无 |
| sentencepiece | [pyproject.toml:59](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L59)：sentencepiece | WARNING → WARNING | 无 |
| sglang | import-only [src/llamafactory/chat/sglang_engine.py:36](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/src/llamafactory/chat/sglang_engine.py#L36)：sglang.utils | WARNING → WARNING | 无 |
| torch | [pyproject.toml:40](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L40)：torch>=2.4.0 | WARNING → WARNING | 无 |
| transformers | [pyproject.toml:43](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L43)：transformers>=4.55.0,<=5.8.0,!=4.57.0,!=5.6.0 | WARNING → WARNING | 无 |
| trl | [pyproject.toml:47](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml#L47)：trl>=0.18.0,<=0.24.0 | WARNING → WARNING | 无 |
| vllm | import-only [scripts/vllm_infer.py:35](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/scripts/vllm_infer.py#L35)：vllm | WARNING → WARNING | 无 |

### HarmBench：逐包 source 与 current accepted → proposed

| critical 包 | 固定源声明或 import-only 依据（物理行） | current accepted → proposed | delta |
|---|---|---|---|
| accelerate | [adversarial_training/alignment-handbook/requirements.txt:1](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L1)：accelerate==0.23.0<br>[requirements.txt:15](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt#L15)：accelerate | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| anthropic | [requirements.txt:8](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt#L8)：anthropic | WARNING → WARNING | 无 |
| bitsandbytes | [adversarial_training/alignment-handbook/requirements.txt:2](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L2)：bitsandbytes==0.41.2.post2 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| datasets | [adversarial_training/alignment-handbook/requirements.txt:4](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L4)：datasets==2.14.6 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| deepspeed | [adversarial_training/alignment-handbook/requirements.txt:5](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L5)：deepspeed==0.12.2 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| evaluate | [adversarial_training/alignment-handbook/requirements.txt:7](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L7)：evaluate==0.4.0 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| numpy | [adversarial_training/alignment-handbook/requirements.txt:13](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L13)：numpy>=1.24.2 | WARNING → WARNING | 无 |
| openai | [requirements.txt:7](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt#L7)：openai>=1.25.1 | WARNING → WARNING | 无 |
| peft | [adversarial_training/alignment-handbook/requirements.txt:16](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L16)：peft==0.6.1 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| safetensors | [adversarial_training/alignment-handbook/requirements.txt:19](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L19)：safetensors>=0.3.3 | WARNING → WARNING | 无 |
| torch | [adversarial_training/alignment-handbook/requirements.txt:22](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L22)：torch==2.1.0 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| transformers | [adversarial_training/alignment-handbook/requirements.txt:23](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L23)：transformers==4.35.0<br>[requirements.txt:4](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt#L4)：transformers | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| trl | [adversarial_training/alignment-handbook/requirements.txt:24](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/adversarial_training/alignment-handbook/requirements.txt#L24)：trl==0.7.4 | 无 WARNING → 无 WARNING（exact declaration） | 无 |
| vllm | [requirements.txt:3](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt#L3)：vllm>=0.3.0 | WARNING → WARNING | 无 |

### llm-dp-finetune：逐包 source 与 current accepted → proposed

| critical 包 | 固定源声明或 import-only 依据（物理行） | current accepted → proposed | delta |
|---|---|---|---|
| datasets | import-only [data/echr/echr.py:6](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/data/echr/echr.py#L6)：datasets | WARNING → WARNING | 无 |
| numpy | import-only [src/llm_pft/models/language_model.py:9](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/models/language_model.py#L9)：numpy | WARNING → WARNING | 无 |
| peft | import-only [src/llm_pft/models/language_model.py:101](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/models/language_model.py#L101)：peft.peft_model | WARNING → WARNING | 无 |
| torch | [requirements.txt:1](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/requirements.txt#L1)：torch | WARNING → WARNING | 无 |
| transformers | [requirements.txt:2](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/requirements.txt#L2)：transformers | WARNING → WARNING | 无 |


以上是预期集合与来源，不是产品 Gate A PASS。实现后必须在五个清洁正确 pin 上比较完整 finding/rule/profile/hint/path/diagnostic/manifest；现有独立 gold 仍被冻结，不按当前输出重生成。若出现 source 不能解释的 delta，停止该结果并先查原因。源/物理行表的维护是 proposal 证据修正，不是修改 val.md 或 gold。

## 8. RED → GREEN、质量门与真实验证

1. 接受决定前：可准备 tests 和官方例表、只读 source 验证；本文没有运行产品 RED/GREEN，没有产生 Gate A PASS。
2. R06-G 先写所有 public-reader 路径/外部 open spy 的 RED，再修读取边界；不得只验证输出没有 canary。
3. R05-A 在未修代码上对 requirements/PEP621 wildcard 与 Poetry/Pipfile local/pre/post/dev/epoch、Poetry double equality、源位置及 exact→lock→finding 一致性建立 public-seam RED。每个修复的独立 oracle 是本支持矩阵和 source，而不是实现自调用。同样的 exact normal case、ranges/malformed/URL、多 clause、marker/extras 是 paired controls。
4. R06-A 在两个 qualified 同名文件、根依赖加 tools-only、nested-only、全枚举顺序中证明 root 与完整候选身份，保持五 pins 的聚合语义；不实施 R06-B。
5. R06-P 单独 RED 图 package 集/未引用 sibling/根内 .. / cycle versus diamond / depth / unresolved，并验证两 consumer 只用同一图。正常 case GREEN 后完整安全回归。
6. C 接受后才为 Conda 的 single/double/triple/canonical build、alias、nested pip、unsupported 子集以及真实 CLI finding 运行 RED→GREEN。C pending 时不得更改旧 Conda expectation 来假绿。
7. 每 task 独立 Conventional Commit、CHANGELOG/spec 引用，full pytest、security、ruff、mypy、schema freshness、tutorial/generated-doc、all applicable local checks；不得因为本提案没有 schema 改动而漏掉 freshness。
8. S2-A/S2-B 各自完整五项目 Gate A，至少 L0，加受影响 init/L1、offline discover inventory 和其他实际修改的非资源 consumer；mutating command 只在 disposable copies。固定 sources/gold 独立验证，有 source/review 决定才能专门改 gold。
9. 本轮语法/静态图决定不新增 GPU/API/受限模型资源 Gate B。历史 VAL-R01～R03 与付费/API/GPU/judge 未 provision 的 resource gates 保持 BLOCKED；到 milestone/release 按 val.md 激活，CPU probe 不能替代。

建议 focused 指令（最终按实际新增文件补齐，不冒充已执行）：

~~~bash
uv run pytest -q tests/unit/core/test_deps.py tests/unit/core/test_scanner.py tests/unit/rules/test_env.py
uv run pytest -q -m security
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
~~~

不要在本文、future evidence 或 golden snapshots 写运行主机/用户名、绝对文件路径或 synthetic canary 明文。源码中的公开仓库文件路径是相对对应 pinned root。

## 9. 文件、D-41 与读写兼容

提案文件只新增本文件和源证据/patch。接受后规范变更限 docs/plan/01_specification.md §12.2（必要限定 §13 reader 合同由 R06-G 独立说明），实现限 assigned deps/scanner/path/env consumer seams、相关测试/文档/CHANGELOG。具体 patch review 时记录最终文件清单；不通过本提案授权任何 core/redaction.py、core/engine.py 或 schemas/ 改动。不新增依赖；packaging 已为 D-29 现有轻依赖。

| 读写组合 | 兼容性与要求 |
|---|---|
| 旧 manifest/config/lock/run → 新 reader | schema v1 不变；不迁移或重写用户文件；旧依赖字符串按更新的静态合同重新审计 |
| 新审计报告 → 旧报告读者 | 不新增字段/rule ID/severity，schema v1 不变；finding status/集合可能有按上表解释的变化 |
| 新 source metadata → 旧 parser internals | Declarations/Lockfile 等未持久化内部 dataclass 修改仍应保留现有公开 consumer 行为并有 roundtrip/compat tests；不能据此给持久化 schema 加字段 |
| 历史 gold/报告/资源验证记录 | 保留原 SHA、当时行为、BLOCKED 与 PASS 状态；新增前瞻性 delta，绝不重写历史 |

退出码不改默认策略。新增 WARNING 可能让显式 --fail-on WARNING 的 audit 从 exit 0→1；默认 CRITICAL gate 若没有新增 CRITICAL 则不因本版本语义变化失败。unsupported syntax 通常为保守 finding/安全诊断，不将整个 audit 变为 exception；真实使用错误仍按既有 UserError/exit2 合同。无规则严重度、默认 fail-on、schema_version 迁移。

备选 A：维持规范字面不修相关 consumer，只完成独立安全/path bug；仍保留被确认的 false exact，R05-B blocked。备选 B：本轮加入完整 resolver/monorepo scope/build schema；代价与 forbidden zone 冲突，不推荐。推荐有限 A/P+C，公开支持边界，并保持五 pins 聚合证据。

## 10. 决定记录（尚未发生）

| 项目 | 当前记录 |
|---|---|
| A/P Python + requirements closure | PROPOSED |
| C Conda bounded MatchSpec | PROPOSED |
| 审批者 / 日期 / 原话或链接 | 未提供；须保存用户对本具体提案接受的记录 |
| 已接受范围 | 无 |
| 未接受范围 | 全部提议暂未生效；R06-B 及其他 policy tasks 不在本决定范围 |
| R05-B | BLOCKED，直到明确接受 C；不把 S2 总体授权算作接受 |
| 后续 | 接受后同步规范与每 task 测试/CHANGELOG，按顺序质量门/Gate A/提交；任何拒绝或缩小范围写入记录 |

如维护者同时接受 A/P 和 C，记录应明确引用本提案版本/摘要及两份 after text 中的全范围 patch；如果只接受 A/P，只应用对应 patch，Conda 仍按旧合同，R05-B 等待 C。若要求放宽 numeric Conda subset、支持 wildcard build 的独立 version certainty、constraints 或完整 pip option，应先补例表与前瞻性 oracle，再执行新增范围。

## 11. spec issue 完整草稿（未发布）

标题：Clarify exact dependency and complete requirements closure semantics (R05-S)

建议 label：spec。

问题：规范 §12.2 用“每行双等号”识别 requirements lock，没有区分 wildcard 或实际 include 完整性；并把 Conda 无 build 的 single equality full version 当 exact，与当前 primary-source MatchSpec prefix 语义冲突。R05-A/R06-P/R05-B 的已计划验收与这些字句不一致；不能在保留规范旧句时改 consumer gold。

提议：接受本文件 A/P 与 C 的精确 before/after、有限语法支持和负例，保留版本与 build/channel/platform/hash 的保证边界。保持 rule IDs、severities/default exits、schema v1、L0 仓库级来源聚合及五 pins 原 gold；不同项目 lock scope 留给 R06-B。未接受 C 时 R05-B 不合入。

来源：本文件 §3 的六个官方链接，核对日 2026-10-10；§7 的固定源码/物理位置/hash 表与 val.md 独立 accepted warning 集。实现与 consumer 变更见 §5–6；预期五 pins zero semantic delta，合成用例解释所有状态变化。

验收：§8 tests-first 的 exact/lock/finding 同源矩阵、图安全 spy、Condabounded grammar、negative controls、全质量门和 S2-A/S2-B 各自完整五项目 Gate A。历史 resource gates 继续按真实资源 BLOCKED。

决定请求：明确接受/拒绝/缩小 A/P 和 C 两范围，保存具体决定；再同步规范、实施、回归/CHANGELOG 与任务提交。此 issue 草稿不会通过工具自动对外发送。
