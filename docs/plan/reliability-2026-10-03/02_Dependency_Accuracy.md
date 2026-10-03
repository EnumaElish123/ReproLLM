# Sprint 2：依赖版本、文件身份与引用关系

版本：v1.1 · 日期：2026-10-03 · 状态：PLANNED

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 目标与会话

修正依赖扫描中可以由源码与格式规范确定的误判：通配版本当 exact、合法非纯数字版本漏识别、同名文件相互覆盖、requirements include 越界读取及错误包归属。

| 会话 | 按顺序执行 | 主要产物 |
|---|---|---|
| S2-A | R05-A → R06-A | Python 格式版本表、完整路径索引、回归与 Gate A |
| S2-B | R06-P → R05-B | 安全 include 图、精确包闭包、Conda 语法表、回归与 Gate A |

R06-B 的仓库 / 子项目 scope 策略单列在 [05](05_Policy_and_Compatibility.md)。它不阻塞上述明确缺陷的修复。若 Conda 规则与执行时冻结规格发生冲突，先交付具体语义表和测试提案，独立推进 R06-P。

禁区：不添加依赖求解器、Conda 运行时、重型包；不执行依赖文件中的命令；不把所有子目录都排除；不把现有 HarmBench gold 改成程序当前输出；不把 exact version 宣称为相同构建或位级复现。

## 2. 共同代码入口

- `src/reprollm/core/deps.py`：`scan_dependencies`、格式 parser、`_collect_lockfiles`、`_requirements_all_pinned`、`_declares_from`。
- `src/reprollm/core/scanner.py`：文件枚举与读取。
- `src/reprollm/core/paths.py`：现有路径边界工具。
- `src/reprollm/rules/env.py`：manifest / lock / Python 版本 / critical dependency 规则；尤其 `PythonVersionDeclaredRule._declared_where`。
- `tests/unit/core/test_deps.py`、`tests/unit/rules/test_env.py` 及相关 fixtures。

## 3. R05-A：Python 格式的 exact-version 语义

### 已确认问题

requirements 路径用 `len(specs) == 1 and operator == '=='` 判定 exact，因而把 `torch==2.5.*` 记录成 exact。Poetry / Pipfile 使用仅匹配数字与点的正则，又把合法的 local / pre-release 等单版本当成不精确。

### 实施步骤

1. 在现有依赖单测中加入参数化格式矩阵，分别覆盖 requirements、PEP 621、Poetry、Pipfile；保存物理行号与 source_file 的断言。
2. 建立小型内部辅助函数用于已支持的 Python 版本表达式；使用已有 `packaging` 解析和验证，不新增依赖。
3. 不含通配符的受支持单版本声明才进入 exact_version；保留各格式语法入口。不能把 Poetry 的 caret、tilde 或 bare version 原样当 requirements 语法。
4. 保持 `is_exact`、requirements-as-lock、`env.lockfile_present` 和 critical dependency pinned 判断使用相同结果。
5. 声明格式不受支持、多个约束或 URL / VCS 等情况保持明确的保守语义，不在这次实现完整约束求解。

### 验收表

| 输入语义 | 格式示例 | 预期 |
|---|---|---|
| prefix match | requirements `torch==2.5.*` | 非 exact；不能只因此成为 exact lock |
| 单一 release | `torch==2.5.1` | exact_version 为 `2.5.1` |
| local version | requirements / Pipfile 的 `==2.5.1+cu121`，Poetry 合法单版本写法 | exact；不是仅 requirements 支持 |
| pre / post / dev / epoch | `2.5.1rc1`、`2.5.1.post1`、`2.5.1.dev1`、`1!2.5.1` | 按各格式受支持的单版本语法识别；无纯数字正则误拒 |
| 范围或兼容版本 | `>=2.5`、`~=2.5`、Poetry `^2.5` / `~2.5`、`*` | 非 exact |
| 多约束 / arbitrary equality | `==2.5.1,>=2`、`===...` | 本轮可维持保守非 exact；写入支持边界，不做臆测求解 |
| 带 marker / extra 的合法 requirement | `torch==2.5.1; python_version >= '3.10'` | 版本限制可识别；不声称所有平台都安装该包 |
| malformed / URL / VCS | 既有 parser 不支持的语法 | 不崩溃；按既有 unparsed / 诊断合同记录 |

具体期望指版本约束的精确性。未指定构建、wheel 哈希、index 来源或平台时，不能据此宣称产物完全一致。

### 验收与提交

```bash
uv run pytest -q tests/unit/core/test_deps.py tests/unit/rules/test_env.py
```

- [ ] 独立的格式表驱动测试，不从 parser 输出自动生成期望。
- [ ] wildcard 修正与合法 suffix 修正均覆盖消费端 finding 状态。
- [ ] 断言 rule status / dependency 集合，不能只看默认 exit code；WARNING 未必触发失败退出。
- [ ] 全质量门及 S2-A 的五项目 Gate A 有完整差异说明。

建议提交：`fix(deps): distinguish exact Python versions from ranges (R05-A)`。

## 4. R06-A：同名文件必须保留路径身份

### 已确认问题

`scan_dependencies` 与 `_collect_lockfiles` 使用 `{basename: path}`。根 `pyproject.toml` 可被字典序靠后的 `zz_tools/pyproject.toml` 覆盖，即使后者只有 Ruff 配置。Python 声明规则却可能取第一个文件，导致 audit 各部分对同一仓库给出矛盾判断。

### 实施步骤

1. 建立 `basename -> ordered paths` 或等价的路径保留结构；同名文件不再在枚举时丢失。
2. 对需要选一个入口的现有行为，首先选择根目录同名文件，再按确定路径顺序处理候选。selection 与文件是否具备依赖声明资格分开；不把 Ruff-only pyproject 当 dependency manifest。
3. 复用选择函数或同一事实结果给 Python 声明规则和 dependency / lock 检测，消除不同消费者 first / last 的矛盾。
4. 将这一改动限定为覆盖恢复与确定选择；不悄悄引入“任何 lock 覆盖所有声明”或“子项目一律不扫描”的新 scope。
5. 以当前规格已支持的文件类型建立矩阵：pyproject、environment.yml / yaml、Pipfile、uv.lock、poetry.lock、Pipfile.lock、conda-lock.yml。无根文件时维持或明确记录兼容行为。

### 验收表

| 目录结构 | 预期 |
|---|---|
| 根 pyproject 有项目依赖，`zz_tools/pyproject.toml` 只有工具配置 | 根 manifest / Python / 依赖证据保留，来源指向根文件 |
| 根与子目录均有同名合格文件 | 两个路径都在候选事实中；根优先合同确定，不因排序偶然覆盖 |
| 只有嵌套合格文件 | 不凭本任务将其消失；按已批准的现行 scope 处理 |
| 根与子目录各有 lock | 文件身份不丢失；不跨边界冒认覆盖；不擅改整个 scope 政策 |
| 文件枚举次序变化 | 同一文件集合的选择和报告字节稳定 |
| 同一输入由 PythonVersionDeclared 与 dependency 扫描消费 | 入口来源一致，或因明确规则不同而给出可解释证据 |

如果修复同名覆盖必然触发尚无合同的多项目归属，保留明确的根选择修复，把新增归属决定交给 R06-B；不可用不确定性继续容忍根文件被工具文件覆盖。

### 验收与提交

定向测试同 R05-A，必要时加 `tests/unit/core/test_scanner.py`。

- [ ] 根 pyproject 覆盖用例失败回归通过。
- [ ] 已支持声明 / lock 类型都有重复 basename 的测试。
- [ ] 路径与物理行证据保留；选择函数消费者一致。
- [ ] HarmBench 嵌套 requirements gold 未被 root-only 规则破坏。

建议提交：`fix(deps): preserve source identity for duplicate filenames (R06-A)`。

## 5. R06-P：requirements 安全路径与实际 include 图

### 已确认问题

`_parse_requirements` 对 `-r` 目标直接拼接路径后交给 scanner 读取，没有充分的项目根边界检查。审查用根 `requirements.txt` 中的 `-r ../external.txt` 成功读到项目外的合成声明，且 unparsed 为空。

同时 `_declares_from` 用同目录子树近似 include 归属。它可能把未引用文件的包算进某 lock，也可能在根 include 场景遗漏实际引用包，出现“lock 存在但 packages 为空”的不一致。

### 实施步骤

1. 将 include 解析变成“解析目标 → 规范化 → 边界验证 → 读取 → 建边”，任何读取发生前完成边界检查。
2. 目标相对**包含它的文件目录**解析；归一化后必须在所选实验根内。允许合法的 `subdir/../common.txt` 内部引用，不按字符串出现 `..` 一律拒绝。
3. 绝对 include、指向外部的相对 include、symlink escape 在读取前拒绝，并输出来源文件 / 行号与稳定原因。不要回显外部完整路径或未经净化的原始行。
4. 检查 `core/paths.py` 现有工具的合同：其中直接拒绝任何 literal `..` 的路径检查不能未经适配套用于本任务。先规范化再执行边界验证，并验证 symlink 行为。
5. 建立明确的 include 图和每文件解析结果，供 `_requirements_all_pinned` 与包闭包共用；不重复扫描出两份不一致归属。
6. 保留有限深度 / 访问集合保护，重复边去重；区分已缓存的重复引用与当前递归栈中的循环。循环、超深、不可读、未支持指令都输出可解释诊断且不崩溃；存在这些未解决边的 include 闭包不能被当作完整 exact lock。
7. requirements-as-lock 的 packages 只来自该根文件真实可达的有效声明；不能借用同目录未引用文件。部分图不可读 / 越界时不得宣称完整 exact lock。

本任务实施文件边界和 requirements 图，不决定不同独立项目之间的全局 dependency scope。后者由 R06-B 处理。

### 可直接重建的测试树

```text
project/requirements.txt           内容：-r deps/base.txt
project/deps/base.txt              内容：torch==2.5.1
project/deps/unused.txt            内容：transformers==4.45.2
project/common.txt                内容：numpy==2.1.2
external.txt                      内容：openai==1.51.0
```

上述是文件清单，不是依赖图；测试再分别替换 include 行：

| 场景 | 预期 |
|---|---|
| 根引用 `deps/base.txt` | 包闭包仅含 torch；不含未引用 unused.txt 的 transformers |
| `deps/base.txt` 引用 `../common.txt` | 合法根内读取；闭包包含 common 声明，路径规范化 |
| 根引用 `../external.txt` | 读取 spy 证明 external 从未被打开；有安全诊断；不能判为完整 lock |
| include 为绝对路径或 symlink 指向外部 | 同样先拒绝后读取；不泄漏真实路径 |
| 重复引用 / 菱形引用 | 可达声明与证据按确定合同去重，不重复读到失控 |
| A → B → A；空循环 | 有定位到引用行的循环诊断，终止且不判为完整 exact lock；共享子节点的菱形引用不能误判为循环 |
| 超过现有深度限制 | 有明确不完整证据；不静默视作完整 pin |
| malformed、缺文件、权限失败、unsupported option | audit 不崩溃；诊断定位 include 来源行 |
| 根有不精确声明，未引用 sibling 精确 pin | sibling 不能“修复”此根 requirements lock 的精确性 |

### 验收与提交

```bash
uv run pytest -q tests/unit/core/test_deps.py tests/unit/core/test_scanner.py tests/unit/rules/test_env.py
uv run pytest -q -m security
```

- [ ] 越界读取由“从未调用外部读取”验证，不能只断言最终结果没显示外部包。
- [ ] 合法内部 `..`、include 闭包与未引用 sibling 三者都测试。
- [ ] exact 与 lock packages 使用同一图，source_file 均为根内相对路径。
- [ ] 全质量门、S2-B 五项目 Gate A、文档和 CHANGELOG 完成。

建议提交：`fix(deps): constrain requirement includes and track their closure (R06-P)`。

## 6. R05-B：Conda 的 exact 语义单独处理

### 已确认问题与预期表

当前 `_add_conda_entry` 用等号拆字符串：单等号前缀版本被标 exact，双等号精确版本反而可能丢失。Conda 的单等号具有前缀语义，不能直接使用 PEP 440 parser 代替 Conda 语法。

| 输入 | 当前审查观察 | 本轮目标语义 |
|---|---|---|
| `python=3.11` | exact_version 为 3.11 | 前缀范围，非 exact |
| `torch=2.5` | exact_version 为 2.5 | 前缀范围，非 exact |
| `torch==2.5.1` | exact_version 为空 | 受支持 exact MatchSpec，版本为 2.5.1 |
| `torch=2.5.1=cuda12.1` | exact_version 为 2.5.1 | 版本为 exact `2.5.1`，build 为精确字符串 `cuda12.1`；保留原声明作为构建证据 |
| channel / build / glob 的其他形式 | 未充分覆盖 | 支持的子集明确；复杂形式保守诊断，不推断未知 exact |

2026-10-03 核对官方 MatchSpec 文档：`foo=1.0=py27_0` 的规范化形式为 `foo==1.0=py27_0`，区别于无 build 的单等号前缀形式。因此上述三段示例应保留精确版本判断，修复的是解析方式及边界。含 wildcard 的版本 / build 按自身维度说明不确定性；仅版本和 build 相同仍不证明 channel、平台与文件哈希相同。本任务不为 build 单独新增持久化 schema。

### 实施步骤与验收

1. 对照官方 Conda MatchSpec / 导出依赖格式，完成小型支持表及源码备注；Python 格式仅复用“exact / non-exact”的内部含义。
2. 为单等号、双等号、合法构建形式、通配 / 区间、malformed 建立测试。
3. 当前测试存在将 `python=3.11` 认定 exact 的预期；根据独立官方语义说明为什么要改，不为保持绿灯保留错误。
4. 保留嵌套 `pip:` 列表走 Python requirement 解析的路径。
5. 不 import Conda，不调用用户 Conda 环境，不增加 SAT 求解。

- [ ] 来源链接、支持子集、错误输入行为写入文档。
- [ ] `DependencyDeclaration.is_exact` 和消费端 finding 的期望一致。
- [ ] 全质量门与 S2-B Gate A 完成；范围外语法进入 backlog。

建议提交：`fix(deps): apply format-specific Conda pin semantics (R05-B)`。

## 7. Sprint 收尾与 scope 审议交接

- [ ] S2-A / S2-B 各有完整 Gate A；不是分别只测几项目。
- [ ] 对 HarmBench 的嵌套 alignment-handbook 精确 pin 保留独立来源说明；任何变化逐包解释。
- [ ] 向 R06-B 提供已实现的完整路径候选和 requirements 图接口；不预先承诺跨项目 lock 覆盖。
- [ ] 公共 API 或 dataclass 调整仅在必要范围；无重依赖与网络单测。

依据：[core/deps.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/core/deps.py)、[rules/env.py](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/rules/env.py)、[PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/)、[Conda package specification](https://docs.conda.io/projects/conda-build/en/latest/resources/package-spec.html)、[Conda MatchSpec 官方 API 文档](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/index.html)。外部规范在实施时核对当前官方内容并记录日期。
