# R06-B P-B 接口与独立验收预备

日期：2026-10-20。状态：只读设计；本轮补验结束前未实施、未写测试、未运行新政策。
本线程维护者已具体接受 A；当前仓库提案中的 PROPOSED/null 是待 root 同步的历史状态，不应重新索要相同批准。

## 最小内部接口

保留 `Lockfile(path, packages)`、所有声明顺序、`unparsed`、`manifest_present`、格式 lock inventory 和 R06-P closure 原语义。不要把 inventory 直接过滤为 eligible locks，否则 presence 规则会误变。

建议在 `Declarations` 增加一个仅内存事实容器，提供单个查询：

```python
qualified_lock_packages(import_origins: Iterable[tuple[str, str]]) -> frozenset[str]
# tuple = (canonical_package_name, normalized_logical_source_path)
```

由 env 将当前已经扫描的 ImportInfo 转成 canonical 包名/path，调用一次替换全 lock 包名并集；exact 分支和 `_evidence` 原样保留。此接口不导入/执行用户模块，不新增扫描，不依赖 AuditContext，避免 deps 与 pyscan 的接口耦合。只给查询传现有 AST import，不补扫被预算省略的文件。

事实容器至少需要：

1. 合格 runtime manifest 的完整逻辑 path、可配对 lock basename 集合。同一个事实即定义项目目录；空 `[project]`、空 `[tool.poetry]`、空合法 Pipfile table 和 `dependencies: []` 都可以建根。Conda 双文件时仍可存在 runtime 根，但不可建立 Conda pair。
2. 候选 manifest 的 uncertain 目录（仅当前 observed analysis candidates）；不需要新增外显诊断文案。
3. 可由原 inventory lock path + manifest facts 推导的同目录 pair。也可存 private pair tuple，但不需要给 persisted schema 或 Lockfile 原有公开字段加 owner。
4. requirements 原有已资格化闭包；不要建立格式项目根。其包都已有 exact declaration，所以原 exact 分支已充分覆盖；如查询返回 requirements 包，也只能来自原闭包，不能引入 sibling。

manifest/parser 读取时顺手捕获事实，不能重新解析并改变原有诊断数量/顺序。`_parse_pyproject` 已返回资格 bool，但 UV/Poetry 的区别需要保留是否有 `[project]` / `[tool.poetry]`；Pipfile/env 当前返回 None，需要增加 private parse status 或直接填事实，保留现有 Declarations 的内容。

资格查询按声明来源和 import 来源分两路：

- 声明：lock 有包，paired manifest 的实际 supported declaration 有该包。requirements/Pipfile/environment 声明不能跨 manager 借 uv/Poetry 信用。另一个 manifest 的 malformed 状态不取消这个已明确声明的信用。
- import：以路径 component 比较，在该文件所有祖先中的合格项目根及 uncertain barrier 里找到最近目录；最近为 uncertain（含与 root 同目录）则不可推断；最近为干净 runtime 根则只能用该目录 pair。外层 barrier 不压倒更深干净根。没有合格祖先不能凭 lock 或文件物理同一认 owner。

返回包集合只在有至少一个实际来源时加入，lock 自己的 package 行不是来源。存在一个有效来源即足够，不要求覆盖所有来源。

## TDD 顺序与独立预期

先从已审阅 E02/E04/E05/E06/E07/E20/E21/E23 建 RED，断言完整 WARNING ID/severity/message/hint/evidence 和 inventory/presence 保留。然后补四个 manager 的 same-dir declaration/import 正例、nearest-root/barrier 的反向边界，最后 CLI consumers。

附 `additional-cases.json` 是手写输入/预期矩阵，不导入产品、不运行政策；`torch` 的 expected warnings 直接来自已接受 A。原 E01–E23 的完整输入已保存在提案 `current-implementation.json`，沿用输入时只使用 `proposed_a_design_expectation_not_executed` 作为经审阅设计依据，不能复制 observation 的原政策结果做新 gold。

重点原有回归入口：

- `tests/unit/core/test_deps.py`：现有 `test_lockfile_counts_as_pinned` 只断言 inventory 有包，**应继续通过**，名称不能误导为需要删掉 name-only lock 支持。
- `test_dependency_paths.py`：同 basename、嵌套来源、原 unparsed、空 project、完整 CLI 确定性。
- `test_requirements_graph.py`：actual include、内部 `..`、共享/循环/深度/缺失，exact 在不合格 closure 中仍独立充分。
- `test_analysis_candidates.py` / `test_scanner_boundaries.py`：既有安全读取与排除，不修改 scanner 策略。
- `test_python_exact_versions.py` / `test_conda_exact_versions.py`：不得借 A 改版本合同。

核心/规则测试固定 `installed_versions={}` 或明确固定 torch version，断言原完整文本，不取本机 package 版本。完整 finding 采用现有原 evidence 顺序：首个 declaration，否则首个 import。一个 package 多个 uncovered origins 仍只能产生一条 WARNING。critical in-use 不能因新增 owner facts 扩张。

CLI 至少选择一个无关联 nested uv 的最小反例和一个正向 same-project case。固定日期/installed package 元数据后比较完整 JSON、summary、profiles、diagnostics、安全路径；默认 critical 阈值与 `never` 均 0，warning 阈值反例为 1。若样例含其他 WARNING，不能用整体 exit 来归因目标；应准备受控干净 repo 或使用原 profile/规则选择合同，只令目标成为 threshold 差异。Github annotation/export 应反映当前同一 WARNING。重复输出及枚举重排应保持现有时间归一化后的完整字节/JSON 不变。

## 需在实施时明确的窄歧义

1. **Malformed 的范围**：正文 2.1.3 写“语法损坏”，patch 写 malformed candidate；parseable 但 runtime 结构类型错误（`project=42`、`[packages]` 被 scalar 替代、`dependencies: 42`）是否 barrier 没有逐项明说。可在既有“valid runtime structure”封闭定义下保守认作 uncertain；不要把有效 tool-only/build-only 非项目当 barrier。需 root 在实施说明中明确这一解释并补测试；若认为将扩大批准语义，应先隔离该细节，不擅自加新 finding/诊断。
2. **同一 pyproject 同时有 project/Poetry**：表格写“仅该 pyproject 中现已支持的声明”，而非仅特定 table。因此有 `[project]` 时 uv pair 应可使用该文件已有 Poetry 声明；只有 Poetry table 时 uv 不可配，Poetry 可配。不要引入未经批准的 table/group/extras scope。
3. **内部结构部分坏**：合法 `[project]` + 错误 tool/Poetry 子结构已有诊断，正文未细分整文件是否 uncertain。宜以显式 facts 区分“有已证明 declaration pair”与“import 推断 uncertain”，保留前者；避免反过来删除已解析 exact 声明。需要窄回归界定。
4. **未观察文件**：barrier 仅涵盖 observed analysis candidates；scanner 已排除的根外 symlink/环境目录不是新增未知根。不要为找 barrier 扩大读取范围。不可读测试应 stub 列举为 observed + `read_text=None`，不要依赖 chmod（特权测试用户下不可靠）。
5. **alias 与 existential**：某个 alias import 与物理目标都被扫描时，目标的合法项目来源可能已经使整个包免警。不能据 alias 单条 origin 不覆盖就期待全仓 WARNING；要隔离来源或用 facts 查询级单元测试，并明确是逻辑来源测试，防止写出反 existential 测试。
6. Conda 两个 basename **存在即歧义**，即使其中一个损坏/不可读；不能只数合格文件。一个合格根和同目录 barrier 并存时 import 无信用，但明确另 manager declaration pair 保留。

## 验证/并行切分

补验完成后可让一名 agent 负责 deps facts/资格查询（含 parser-focused tests），另一名负责 env consumer/规则和 CLI 独立 acceptance，先约定上述查询签名以免同时编辑 deps。root 负责 accepted spec patch、CHANGELOG、文档/decision，最终整合一次完整质量门 + fresh all-five Gate A + 受影响非资源 consumers。五项目 package/warning/profile/path/diagnostic 预期零 delta；保留 HarmBench nested exact 和 DP setup.cfg 不支持边界。不得自动更新 fixtures/gold，不重复未触及合同的 GPU/paid/HF，不改 schema/engine/redaction。
