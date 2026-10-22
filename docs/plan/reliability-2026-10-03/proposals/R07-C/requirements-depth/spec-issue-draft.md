# Local spec issue draft: R07-C D-G requirements depth frontier

状态：**LOCAL_DRAFT_NOT_SENT / PROPOSED**。拟用 label：`spec`。
依据执行总则 §5.9、策略方案 §2：本地准备完整议题，不写入 GitHub，不把本草稿当成维护者决定。
本片属于现有 R07-C 工作；提交线上议题前须核对是否已有对应讨论，不创建重复议题。
本草稿没有查询或创建线上 issue，也不把既有 Issue #9 当成这项新政策的决定。

## 当前合同与可复核缺口

规范 §12.2 接受全仓任意已捕获 exact 声明的正面信用；现有 requirements include 深度上限是10。
在 [22 个字面输入](cases.json) 的 `depth-unseen-exact` 中，深度10的 `deps/9.txt` 已捕获
`-r 10.txt`，深度11的 `deps/10.txt` 内确有 `torch==2.5.1`，但正文未展开。
[当前观察](current-observations.json)仍输出 torch WARNING。D-M 只处理已发生的正文读取/解码失败；
D-M-S 的有限结构表没有处理该图捕获缺口。

这不等于所有 `closure.complete=False` 都含潜在缺失声明：cycle、unsupported option 和旧的
depth 诊断都不够。`depth-later-shallow-root-loose` 在后续浅 root 捕获了该目标，却保留先前
不完整闭包，是禁止把旧诊断直接提升为未知的反例。

## 推荐 A 与备选 B

A：增加内部 `Declarations.unexpanded_requirement_targets: tuple[str, ...] = ()`。
只在全部现有 roots 展开之后，从已捕获可读 node 的现有 `_RequirementInclude` events
取非空的 normalized target，且 target 在最终 `graph.nodes` 仍不存在；去重字典序。
不增加读、探测、根、边、预算、语法支持或持久化字段。预算先终止时，目标是否存在、可读、
物理路径安全或将被 candidate filter 排除都没有验证；仍记录目标，明确接受这项保守成本。
预算内已达到的 excluded/read-failed node 不因此产生新事实；实际正文失败保持 D-M。

只在现有规则的剩余缺 pin 分支消费新事实。优先级严格为：
exact/qualified lock → D-F/D-S → D-L → D-M/D-M-S → D-G → 原 WARNING。
不创造 use，不加每包 PASS，不改变 no-use applicability/empty-result Python veto。
D-G 独立于 Python coverage，沿现有全仓 existential exact 合同影响全部当前无信用包。

新分支为 SKIPPED/INFO，精确 message：

```text
{display} is used; a supported requirements include was not expanded within the depth budget, so missing pin evidence is not established
```

精确 fix hint：

```text
Review {display} declarations and unexpanded requirements include targets; restructure the supported include graph within the depth budget before deciding that exact pin evidence is absent.
```

证据先保留现有声明/import 首项，再按字典序输出 normalized target 的 file evidence，note 为
`{display} include target unexpanded at the depth limit`。它记录已知引用，不声称目标实际存在或已读取。
完整字段预期见 [独立未来 finding](future-finding-example.json)。高优先级分支保持原证据和文案。

B：保持当前 WARNING 与 diagnostics，这个已证明的捕获缺口继续 OPEN。
不提出所有不完整闭包、全部 unparsed 或一般 grammar 统一转换 SKIP 的宽泛方案。

## 精确修改与验收

- [精确规范补丁](spec-proposed.patch)：新增 §12.3.8 与有限交叉引用；保持未应用。
  SHA-256：`b10605effffcaabcee8d988ea1ce524c3e3acf35fe8231f273d749f2cb9a5dc8`。
- 预期未来产品文件仅 `src/reprollm/core/deps.py` 与 `src/reprollm/rules/env.py`；
  回归覆盖 core graph/deps、rule priority、CLI，另更新 CHANGELOG 和报告。
  不触及 D-41 engine/redaction/schema、scanner、依赖或版本。
- [30 组未来验收](acceptance-cases.md)覆盖最终图、多个 roots、预算边界、candidate 成本、
  所有既有信用/优先级、repair/recompute、退出门、suppression/export 和历史不改写。
- [兼容矩阵](compatibility.md)：孤立 WARNING 或 FAIL-only CRITICAL override 可由退出1变0；
  其他 qualifying finding 仍使退出1。schema 和历史记录原样保留，无迁移。
- [五项目来源与独立预期](portfolio-impact.md)：40 条只读 Git 命令，五固定干净输入中
  5 份 requirements、60行、零 include；本窄片预期完整 findings/profiles/hints/diagnostics/
  init/L1/export 零变化。此为 PREDICTED_NOT_EXECUTED；未来批准后仍须新鲜五项目 Gate A。

## 可直接裁决的问题

是否接受 **方案 A 及该精确规范补丁**，包括最终图判定、未验证目标存在/candidate 状态的
保守边界、全仓无信用包的 SKIPPED/INFO 成本、精确文案与既有优先级？
若接受，P-B 先补失败回归，再作最小实现，完成最终质量门、五项目 Gate A 及受影响验证。
若选择 B，保持当前产品合同并记录该缺口 OPEN。

请在 [正式决定记录](decision.json)对应的具体提案上给出选择。此草稿没有记录接受，
没有执行未来政策，没有创建线上 issue；整个 R07-C 的行语法、遗漏候选/listing/framework
及充分证据问题仍 OPEN。付费 API 和版本发布不在本次授权内。
