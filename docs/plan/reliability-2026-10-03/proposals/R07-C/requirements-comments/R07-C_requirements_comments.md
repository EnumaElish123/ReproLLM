# R07-C D-C / P-A：有界 requirements 行内注释

状态：**PROPOSED**。推荐 A；本文件及补丁是待决方案，不是当前产品合同。

## 1. 当前进度与问题

S1 至 S4-B 工程已交付；已接受的 R06-B、R08-A/B 和 R07-C 窄片分别按各自报告验收。
D-G 在 `d823f90` 实施，最终交付导航为 `e52e0a2`；其余 R07-C 未因 D-G 完成而关闭。
本次从当前执行计划的 P-A 阶段继续，不把未来单包值 grammar、listing、framework 或整个 R07-C 一并实施。

当前 `core/deps.py::_RequirementsGraph._node` 先按原 stripped 物理行区分空行/整行注释、include、
directive/字面 `" @ "`，再把普通行完整交给 `_add_requirement_line` / `Requirement`。
普通行内注释通常导致解析失败并进入原始 `unparsed`，故合法 pin 可能丢失。
例如 `torch>=2` 后接 `torch==2.5.1 # pin`，当前只有 loose 声明，关键包仍 WARNING；
若另有 D-M 或 D-G 事实则为相应 SKIPPED。实际 HarmBench 的 `art  # for ArtPrompt` 和
`tenacity  # for ArtPrompt` 也会丢失，虽不属于关键包。

当前观察见 [32 组预写输入](cases.json)与[完整观察](current-observations.json)。
它们证明旧产品行为，不证明 A 已实现。独立投影仅是有序 `(name, exact_version)`、原始关键规则 statuses、
body issue 字典及 D-G frontier；没有执行 engine/CLI 的 PASS 合成、profile/provider detection 或未来 policy。

## 2. 依据与取舍

2026-10-22 核对 [pip 官方 requirements 格式说明](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
（页面标注 v26.2.2）：行内注释和续行有先后处理关系，完整格式本身与 pip 实现紧密相关。
本方案只支持以下明确子集，不引入 pip 解析器、manager 执行、续行拼接或完整安装语义。

**A（推荐）**：只为已采集 requirements 图中原普通行的失败解析增加一个有界前缀回退。
这是 grammar 改动，会影响实际 use、exact、closure、lock、profile/init 和退出码。
保留已有信用与不确定性分支优先级，不把全部 `unparsed` 泛化为 SKIP。

**B**：保留当前实现和规范，不增加行内注释支持。32 组当前结果保持，HarmBench 两行继续漏入依赖清单，
该缺口仍 OPEN。B 是延期选择，不意味着已修复，也不把现行为宣称为完整 pip 支持。

## 3. A 的精确算法边界

1. 只复用 `_RequirementsGraph._node` 已有 `read_text` 成功返回的文本。仍按原 `raw.strip()`
   先分支：空/整行注释、原 include 识别、原 `line.startswith("-")` 或字面 `" @ "`。
   不得先去注释再把行重新分类成 include/directive，也不新增读文件或探测。
2. 对原 ordinary route，先保留原完整行的解析成功结果，包含既有 marker 和已成功的 URL 形式。
   只有原完整行解析失败，才可能启用下述新增支持。
3. 对该文件全部 `text.splitlines()`，任一物理行经 `rstrip()` 后以反斜杠 `\` 结尾时，
   **整个文件禁用新增支持**。原成功解析、原 include 和原诊断照旧。
   这是保守 veto：包括整行注释末尾、双反斜杠和晚于候选行的反斜杠；不识别转义或拼接。
   veto 不扩散到其他已捕获文件，父文件 veto 不禁止无 veto 的子文件自身获得新增支持。
4. 无 veto 时，查找原 stripped 行中**第一个** ASCII SPACE 或 TAB 紧接 `#` 的位置。
   取其之前的前缀并 strip。只有前缀可由当前 `Requirement` 解析且 `req.url is None`，才新增声明。
   不尝试后续 `#`，不把 NBSP 或其他 Unicode 空白当成新增分隔符。
5. 无位置、前缀失败、前缀是 URL 时，保留原完整行失败结果及原始诊断字节；不截短失败诊断。
   `torch@https://… # note` 等不能借新逻辑获得 URL 声明；原成功 URL 结果也不能被撤销。
6. 新声明仍使用原 source path 和物理行号，按现行 name/specifier/exact 算法构建；成功后不再保留该行旧
   unsupported 事件。闭包和 lock membership 使用同一图、同一批声明，按既有规则重新计算。
7. 只改 graph 普通行路径；共享 `_add_requirement_line` 的 PEP 621、embedded pip 等调用不获得这项支持。
   不改边、根发现、候选过滤、深度预算、去重、cycle、schema、renderers、engine 或规则优先级。

例外必须直说：`torch==2.5.1 # contact @ team` 仍被原 `" @ "` 分支排除；
marker 内第一个 ` #` 若使前缀非法，就不再寻找外层注释；这些输入不能写成“pip 等价支持”。

## 4. 兼容性与可观察变化

已有 exact/qualified → D-F/D-S → D-L → D-M（含 D-M-S）→ D-G → WARNING 的优先级不变。
新增 exact 可能先于已存在的不确定性分支取得信用，故 WARNING→PASS 或 SKIPPED→PASS 均可能发生；
body/frontier 事实仍保留，不能因包获得信用而删除事实。新增全 exact 完整闭包可使
`env.lockfile_present` WARNING→PASS，并新增对应 root 的 lock package 集合。

新增 loose/unversioned 关键包也可能是首次识别的 use，导致原“不适用”变成 WARNING；
severity promotion/config suppression/fail-on 原合同继续适用。
隔离其他失败后的 `--fail-on warning` 既可能 **1→0**，也可能 **0→1**。
依赖 profile 的 medium 证据、init 的 profile 选择/生成 manifest、完整 diagnostics 同样需验收；
不得只比较 summary。详见[兼容矩阵](compatibility.md)和[未来独立验收](acceptance-cases.md)。

无 persisted schema 改动，无重依赖、无网络、无 LLM audit、无用户输入文件写入。
未来 P-B 在同一提交更新 §12.2、CHANGELOG 和窄范围测试，历史记录与原始 gold 不改。
五项目预测为[源码影响表](portfolio-impact.md)中的逐项 delta，不能先把当前输出复制成新 gold。

## 5. 未来实施顺序及验收

具体接受 A 和[规范补丁](spec-proposed.patch)后：先新增/窄改回归并记录 RED，再实施 graph-only 回退，
执行 focused tests、受影响 lint/type/security 检查；最终输入只跑一次完整质量门，随后五项目 Gate A 及全部受影响
audit verbose/JSON、init、lock/diff/export 消费者，完整比较 profiles、hints、findings、路径、诊断和 manifest。
两个已有“不支持语法”测试只更新 comment 参数，不整体删除 URL、directive、continuation 控制。
P-B 每项按 Conventional Commit，报告 product hash、fixture差异和最终证据；推 main 后核对精确 HEAD 的五项 CI。

本轮仅 P-A，依验证流程文稿例外，完整本地质量门/Gate A/Gate B 为 NOT_APPLICABLE。
已准备本地 spec issue 草稿；未获对外发帖授权，不向 GitHub 新建 issue。

### P-B 精确文件清单（待批准后）

| 文件 | 预期动作 |
|---|---|
| `src/reprollm/core/deps.py` | 仅 graph ordinary-line 的原解析失败回退和文件级 veto；不改变共享其他格式入口 |
| `docs/plan/01_specification.md` | 应用本包精确 §12.2 补丁 |
| `CHANGELOG.md` | Unreleased 记明有界支持、use/lock/profile 和双向退出码变化；本轮 P-A 不先写成已交付功能 |
| `tests/unit/core/test_requirements_inline_comments.py`（新增） | C01–C21 的 literal graph/grammar/读取/闭包与其他格式隔离回归 |
| `tests/unit/core/test_requirements_graph.py` | 只窄改既有 `test_safe_legacy_noninclude_bytes` 的两条 comment 预期 |
| `tests/unit/core/test_requirements_depth_frontier.py` | 只窄改 G23 comment 参数，保留其他 unsupported controls/frontier 定义 |
| `tests/unit/rules/test_env.py` | 信用/use、lock、D-F/D-S/D-L/D-M/D-G 优先级和 Python veto 回归 |
| `tests/unit/profiles/test_detect.py` | medium dependency profile、代表 evidence 和既有 high 信号控制 |
| `tests/unit/core/test_manifest_scaffold.py` | 新 profile 的默认 scaffold 与显式选择控制 |
| `tests/unit/cli/test_requirements_inline_comments.py`（新增） | 完整 report/diagnostics、阈值/override/ignore、fresh init/L1/default export 和确定性组合 |

未来 P-B 的报告、证据包、导航状态单独新增/登记；若验收暴露所列范围外的产品问题，先登记，不静默扩张。
不改 snapshot 的旧期望来制造通过；若确需补充 prospective gold，先按 val.md 的独立来源审阅政策处理。

| D-41 受审类别 | 本方案是否触及 |
|---|---|
| `src/reprollm/core/engine.py` | 不触及；保持 PASS/SKIP 合成与 override/suppression |
| `src/reprollm/core/redaction.py` | 不触及；不更改安全边界 |
| `src/reprollm/schemas/`、`schemas/` | 不触及；不增加持久化字段或版本 |

因此本片没有 D-41 文件改动申请；具体政策本身仍须批准，D-41 不适用不等于政策已获授权。

## 6. 待决与剩余阻塞

待维护者具体接受 A 及上述有界限制，或选择 B 保留现状。原“继续所有后续开发”和 D-G 的裁决委托
没有替代本片具体政策批准。本轮不会更改现行规范或产品。

其他单包值/字符串语法、requirements 续行/约束/完整 pip 语法、未知 use、listing/framework 及广义覆盖证书仍 OPEN。
五份原始 metadata 缺失和最新已记录 HF403 仍阻塞 VAL-R03；VAL-R01/R02 沿历史候选验收，不自动更新为本轮 PASS。
A02 外部反馈与 A03 申请人信息/提交授权仍待实际来源；不调用付费 API，不执行推理训练，不发布版本。
