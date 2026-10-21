# R07-C：已关联格式 lock 的已知读取/解析失败（局部 D-F）

状态：**PROPOSED / P-A**。起点 `60aa97f91b09c56e118c434c954ebc451679423e`。
本提案承接已交付的局部 A、P、D-L。准备材料和进程内条件观察不表示新政策已接受，
正式产品、规范及测试补丁尚未应用；整个 R07-C 仍 OPEN。

## 问题与下一步范围

现[规范 §12.3.3](../../../../01_specification.md#1233-possible-format-lock-credit-with-primary-python-gaps-r07-c-d-l)
明确保留读失败/格式错误且没有采集匹配包名的旧 WARNING。
`core/deps.py` 的四种格式 lock 解析器遇到现有安全读取返回 None 或已捕获的解码异常时，
返回空包名列表，仍登记格式 lock 的存在；下游不能区分“读过但没有此包”和“包集合没有读到”。

最小反例：根 PEP 621 `pyproject.toml` 声明 `torch>=2`，同目录 `uv.lock` 语法损坏，
Python 视图完整。现行为是 torch WARNING；仅将锁内容恢复为包含 torch 的合法记录，
就可通过现有 R06-B 声明关联取得信用。因此，在锁内容未确认时，缺 pin 结论会被补读证据推翻。
这与 Python 文件预算无关，也不能由 D-L 的已捕获 membership 条件处理。

本批只处理 **已捕获格式 lock 的已知 body-read/decoder failure，且包具有已捕获的合格关联来源**。
不把本批扩成全依赖语法、所有文件可读性或全仓覆盖工程。

## 备选与推荐

| 方案 | 结论与代价 | 判断 |
| --- | --- | --- |
| 保持现 WARNING | 继续当前有界合同，保留已知未读包集合反例 | 可拒绝新政策时保留 |
| 任一格式 lock 失败就跳过全部待警告包 | 实现简单，但无关联、错误 manager、跨项目锁也压低稳定警告 | 本批不选 |
| **D-F：只有已捕获的现有合格关联来源才 SKIP** | 仅因缺失包集合而不确定的包逐项 SKIPPED/INFO，保留其他包和现有信用 | **推荐** |
| 一次实现所有依赖/枚举/解析充分证书 | 范围宽，需要各通道的完整性合同和迁移设计 | 后续独立任务 |

## 具体合同

仅在内部 `Lockfile` 增加 `read_issue: Literal["unreadable", "invalid_syntax"] | None = None`。
`unreadable` 表示现有 `RepoScanner.read_text` 返回 None；`invalid_syntax` 表示现有 TOML/JSON/YAML
解析器捕获的解码异常。None 只表示没有登记这两类已知失败，不保证 grammar 完整、包版本有效或实际安装成功。
保持既有安全路径、二进制、读预算和候选过滤；不重试、不读被拒内容、不从原始错误文本猜包名。

四种格式仍是 `uv.lock`、`poetry.lock`、`Pipfile.lock`、`conda-lock.yml`。
把现有 R06-B manager / 同目录声明 / 最近项目根 import / uncertain barrier 的关联判断，
提取成共享的“先判断来源，后判断包集合 membership”。旧 qualified-lock 信用仍是完全相同的关联与包集合交集，
requirements 闭包信用原样保留。新 `Declarations.unverified_lock_paths` 只报告既有合格来源对应的已知失败锁路径。
直接声明与 import 的 barrier 行为分别保持原算法，不新增项目根、来源或 manager 委派。

对原 in-use canonical 包依次处理：

1. 现有 qualified lock 或任一 exact declaration 先获信用。
2. 若仍待警告，且至少一个合格关联格式锁有上述已知失败，产生 D-F SKIPPED/INFO。
3. 否则继续现有 D-L 与旧 WARNING；不短路整个规则。

新 D-F 独立于 Python coverage，包括零候选和完整视图；同时满足 D-F/D-L 时 D-F 消息优先。
使用证据仍取现有首条声明，否则首个 import；之后追加去重、按逻辑路径排序的失败关联锁文件证据。
锁本身不创建 in-use 包，不因新 SKIP 获得信用。

完整 message、fix hint、evidence note 已固定在[实现补丁](implementation-proposed.patch)与[规范补丁](spec-proposed.patch)：

```text
{display} is used; an associated format lock could not be read or parsed, so missing pin evidence is not established
```

```text
Review {display} declarations and associated format-lock files; restore readable, valid lock contents before deciding that exact pin evidence is absent.
```

追加 `kind: file`，`path` 为失败关联锁的逻辑相对路径，
`note` 为 `{display} associated; lock package contents unverified`；不保存异常原文。
其他 finding 字段、排序、身份与默认来源保持。

## 已知边界和兼容成本

- 有效空锁、有效但不含该包、无关联/错误 manager/较近项目或 barrier 阻断的失败锁，均保留原路径。
  exact 或另一个合格锁继续优先；同列表中其他 WARNING 保留。
- 语法已解码但 top-level/collection/entry 形状错误、部分提取、未触发捕获异常的不支持语法保持旧行为。
  `read_issue=None` 不将它们认证为完整有效。
- 没有采集到的依赖候选、一般声明解析与 requirements 失败、未发现 import 来源、listing、README/config/framework
  完整性和广义充分证书继续 OPEN。本批不声称整个 R07-C 关闭。
- class 默认 WARNING、rule ID、schema、CLI fail-on 常量保持。新 INFO/SKIP 不接受 FAIL-only severity override；
  孤立 WARNING 或被提升的 CRITICAL 门可能从 exit 1→0，其他警告仍触发门。suppression 继续适用于全部状态。
- 默认文本可能显示 `Findings: PASS` 并列 skipped 数；默认 export 可能移除原 notable warning，且不显示 skipped 数；
  完整 JSON 保留未验证条目。沿用现 renderer，不把这个表现当成完全可复现证明。
- `env.lockfile_present`、manifest 存在性、包使用集合与旧空结果 Python veto 保持，缺内容的 lock 存在性可 PASS。

## 禁区与验证

仅拟改 `core/deps.py`、`rules/env.py`，以及具体规范、CHANGELOG、验收测试。
不改 engine、registry、scanner/pyscan、redaction、schema、profiles、依赖或版本；不扩大读取/扫描预算。
不修改上游输入、历史 gold 或已接受提案快照，不发布 release/tag/PyPI。
普通政策任务不激活资源里程碑；GPU、Hub、付费 API 为 NOT_APPLICABLE，历史结果仍归原候选。

P-A 冻结输入和逐包预期后，baseline 与未应用的进程内候选做完整 JSON 对照。
保留实际时间戳、原流、来源与输入 guard；完整 JSON 仅豁免规范 T-02 根 metadata。
expected 由 baseline 与事先固定的场景转换产生，不能从 conditional 输出复制。
读失败用明确标记的受控文件打开拒绝，语法失败为真实 fixture 内容；不伪称真实权限验证或 fresh Gate A。
五项目影响基于固定源码完整路径、完整历史报告和初始化/导出 oracle 预写，不冒充新产品运行。
测试草稿仅静态检查，不宣称 RED/GREEN。

接受具体 D-F 与补丁后执行 P-B：

1. 应用验收测试，先取得预期失败，再应用接受的实现/规范/CHANGELOG 并取得通过；完整旧依赖信用回归守护共享关联。
2. 定向 lint/type、安全边界检查后，冻结最终输入，执行一次完整质量门。
3. 五项目 fresh L0/facts、受影响 init→L1/default export，以及关联失败/恢复与稳定警告专项；完整 JSON、证据、诊断和文件比较。
4. 同候选全部适用门通过后归档，任务与报告分别提交；保护 main 原三项 WIP，推送并确认最终 HEAD 的五项 CI。
5. 原 PROPOSED 快照不重写，具体接受另立 sidecar，剩余 R07-C 工作继续登记 OPEN。

## 实际准备证据

- [独立对照](observations/README.md)：25 组（22 API / 3 CLI）、50 workers、25 份完整 JSON 比较，首次正式尝试通过。
  墙钟 54.086346 秒，命令合计 52.354039 秒；350 次产品只读 Git 查询，源码、HEAD/index 和全部案例输入逐字保持。
  完整 expected 在对应 conditional 之前由 baseline 与固定的包名/路径转换产生，保留实际时间戳，只豁免 T-02 根字段。
- [观察归档复读](observations-readback.json)：210 文件、486 原来源，完整输入重建、原始流哈希与 25 份比较通过。
  读失败是明确标记的 Path.open 拒绝，语法失败为真实文件内容；没有运行拟议 pytest 或应用产品补丁。
- [五项目来源与预写影响](portfolio/README.md)：210 份仓库来源、43 次只读 Git 查询，固定项目全部干净且无四种格式锁。
  全部历史 L0/L1/facts、15 初始化文件、五份导出及原完整比较绑定；五项目零差异是独立设计结论，尚非 fresh Gate A。
- [74 项验收测试草稿](tests-proposed.patch)与[静态资格](tests-static-qualification.json)：15 个新函数、三个既有模块，
  71 个旧测试函数 AST 及文本不变；Python 3.10、逻辑文件名 Ruff/format、apply-check 通过，未运行 RED/GREEN。
- [实现/规范初步独立复核](review-source-spec-initial.json)、[观察与测试静态复核](review-observation-tests-static.json)
  及[归档工具静态复核](review-observation-packager-static.json)通过；[完整实际证据最终独立复核](review-actual-final.json)首次通过，
  独立重建 25 份 expected，严格递归核对类型、键、顺序和值；9,869 个原 tracked blob 和原三项 main WIP 保持。

准备阶段有明确保留的停止记录：规范准备首次误以为 CHANGELOG 的 Changed 标题唯一；观察工具首次误写 deps 源哈希常量；
外部测试路径的 Ruff first-party 分类首次产生两条旧 import 排序提示，之后用同字节和仓库逻辑文件名核对通过。
这些都发生在正式产品对照前或静态草稿准备中，不是被隐藏的产品失败或 pytest 重试；未改变业务预期。
首次 50-worker 观察和首次数据打包均通过。

## 决定依据

[执行总则 §5.9](../../../00_Execution_Guide.md#5-统一实现与兼容性要求)要求“不要把本包中‘建议的新行为’当成已经修订的规范”。
现 §12.3.3 明确保留本分支的旧 WARNING，D-L 接受记录只处理固定已采集包集合与 Python 缺口。
因此需要本项具体规范决定；总体继续开发授权覆盖完整提案准备，不等同于已经接受新合同。
本补丁不触及 D-41 的 engine/redaction/schema，无须额外请求那些受保护模块批准。
