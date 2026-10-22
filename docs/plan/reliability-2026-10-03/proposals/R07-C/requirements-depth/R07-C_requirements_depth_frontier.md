# R07-C P-A：requirements 深度预算后的未捕获目标（D-G）

日期：2026-10-22。**PROPOSED；规范补丁未应用、未来政策未执行。**
D-G 是本 R07-C 提案的局部标签，不是新增全局 Sprint。
原始材料在 D-M-S 验收期间私有预备；历史 [准备身份](preparation-identity.json)和
[准备稿](proposal-preparation.md)保持原字节。正式 P-A 在 D-M-S 本地验收及精确推送 CI 完成后登记，
产品、报告 closure、先前 CI 和本轮待执行 CI 分别见 [交付基线](delivery-baseline.json)。本地 PASS 不代替 CI。

## 问题与独立反例

现行 §12.2 允许全仓任意已捕获 exact 声明提供正面信用；requirements include 深度上限为10。
已支持且规范化的 `-r` 边可能在深度预算处停止，目标正文没有捕获。
现行 D-M 仅为实际正文读取失败记录事实；D-M-S 处理 manager 解码后的有限结构。
未展开的 requirements graph 仍为 OPEN。

`requirements.txt` 包含 `torch>=2` 和 `-r deps/0.txt`，经过每层一个 include 到深度10的 `deps/9.txt`，
其中 `-r 10.txt` 已解析；深度11的 `deps/10.txt` 实际含 `torch==2.5.1`，但未读取。
现行 torch WARNING 可由补充这份现有正面证据推翻。这是确切的捕获缺口反例，不是猜测文件一定有 pin。
本次当前政策观察保存了这组固定文件和全部实际读取轨迹。

但是 `closure.complete=False` 不是此问题的同义词：cycle、unsupported option、未解析字符串也可令闭包不完整，
即使相关正文都已捕获。另一个 shallow root 也可能在后续读取深层目标，使全仓不再缺它，
而首个 root 仍保留 depth-limit 诊断。因此新判断必须使用**所有 roots 扩展后的最终捕获图**。

## 推荐 A：只记录最终未展开深度边界

建议增加内部字段，放在 `Declarations` 既有字段之后：

```python
unexpanded_requirement_targets: tuple[str, ...] = ()
```

这是不可变 tuple 的默认空值，不新增持久化字段，不修改 `DeclarationReadIssue` 的原因表。
来源严格为已捕获、可读 node 的既有 `_RequirementInclude` event；满足：

1. `target` 非 None，已通过现有 include 语法及逻辑相对路径归一化。
2. 所有 roots 的现有 expansion 已结束。
3. `target` 仍不在最终 `graph.nodes`。
4. 目标去重、字典序排序后形成 tuple。

现有控制流中，active cycle 目标已有 node；预算内实际走到的普通目标也会产生 node，
即使 candidate 被排除或 reader 返回 None。因此这个最终缺失 node 表示受支持边没有越过深度预算展开。
P-B 必须用图边界、多 root 和重复边测试固定此证明；不能将来改变 traversal 后仍盲用结论。

保持上限10、root深度0、全部解析/图/锁资格/诊断/reader轨迹，不添加候选、根、边、探测、读取、重试。
“目标路径已规范化”不表示它存在、可读、经过物理路径安全检查或 candidate filter。
如果预算先停止，目标后来本会被 `.venv` 过滤、找不到或被物理读取边界拒绝，也仍可进入这个 tuple。
这是一项明确的保守成本；不会为判断它而访问该目标。
相反，预算内实际达到的 excluded node 已在图中，**不触发本新字段**；旧 body failure 继续由 D-M 处理。
absolute/escape/remote/unsupported include 若现有解析器没有得到 normalized target，亦不触发本片。

有 node 的深层目标若通过另一个 root 后续读到，就不得仅凭旧诊断重复标 unknown。
该已捕获节点自己的下层未捕获边仍可产生新的目标项。

## 规则合同、文案及优先级

只改 `env.llm_critical_deps_pinned` 的剩余缺 pin 分支，顺序固定：

1. existing exact／qualified-lock credit；
2. D-F/D-S；
3. D-L；
4. D-M（包含 D-M-S）；
5. 本片 D-G，非空 tuple 对剩余当前已知使用、无信用包输出 SKIPPED/INFO；
6. 无上述事实时维持 WARNING。

新片独立于 Python coverage；不创造 use，不加每包 PASS，不改变 no-use applicability 或 empty-result Python veto。
较高优先级分支的消息和证据完全保持，不追加较低级的 target 路径。
影响沿全仓 existential 合同，未展开目标可对任一当前无信用包造成保守 SKIP；不能套用 format-lock ownership。

精确 message：

```text
{display} is used; a supported requirements include was not expanded within the depth budget, so missing pin evidence is not established
```

精确 fix hint：

```text
Review {display} declarations and unexpanded requirements include targets; restructure the supported include graph within the depth budget before deciding that exact pin evidence is absent.
```

evidence 首项保留现有 first captured declaration/import；随后为每个目标添加 `kind: file`、相对 `path`，
精确 note：`{display} include target unexpanded at the depth limit`；其他可选字段保留默认。
目标去重字典序；不声称逐一报告了所有来源边，也不声称 `kind:file` 已验证实际文件存在。
[完整独立未来 finding 示例](future-finding-example.json)只表示验收预期，未执行。

不会将预算未展开称为 unreadable/invalid_syntax/invalid_structure；因此不复用会误导此原因的旧 D-M 文案。

## 用户可见兼容性

| 情况 | 预期变化／保持 |
|---|---|
| 唯一新增事实为最终未展开目标，已有无信用关键包 | WARNING → SKIPPED/INFO；新增相对 target evidence |
| 捕获到 same-package exact、其他 exact、qualified lock | 信用保留，不能因深度缺口撤销 |
| D-F/D-S、D-L 或 D-M 已触发 | 原消息、hint、evidence 原样，不追加 D-G 路径 |
| 最初 depth-limit 但最终目标从浅层捕获 | 不触发 D-G；根据最终实际声明评估 |
| cycle、unsupported grammar、reached excluded node | 维持原合同，本片不扩张 |
| 指向缺失／将被排除目标的边在预算之前已停止 | 保守 D-G；不猜测 reader/filter 的未执行结果 |
| isolated WARNING／override CRITICAL gate | 可能退出1→0；FAIL-only override 不作用 SKIP |
| 独立 qualifying finding | 仍可退出1；阈值不变 |
| ignore/suppression/default text/export | 沿现合同；默认 export 隐去 SKIP，JSON保留完整 finding |
| 旧 JSON 与已有 run/lock | schema不变，读者合同保持；历史字节不重写 |

## 已完成证据与未执行部分

22个当前政策案例的字面输入、预写预期及实际结果分别见 [cases](cases.json)、[observations](current-observations.json)。
全部当前预期匹配；两类关键反例是 depth 未捕获 exact、后来 shallow root 消除该缺口。
它们只覆盖当前 parser/graph/AST/rule，不是未来 policy、完整CLI、质量门或Gate A。
[观察器原始源码](current-observer.py.txt)与结果内 hash 一致；明确 Git非仓库、installed_versions空的控制。
附加源码哈希在准备材料时采集，未回填成原执行时元数据。

五项目 [独立来源记录](portfolio-source-evidence.json)的40条只读Git命令全部退出0：
固定pin/origin/前后clean；5份requirements与Gitblob、旧R06-B原始来源hash一致。
60行包含55普通依赖、2整行注释、2行内注释、1裸VCS，**没有 include**。
故本窄范围的全部 L0/facts/init/L1/export 预期零变化，见 [五项目影响](portfolio-impact.md)。
此为独立 PREDICTED_NOT_EXECUTED，不修改 gold、不替代具体批准后新鲜 Gate A。

[验收矩阵](acceptance-cases.md)与[兼容说明](compatibility.md)是未来 P-B 要求；
本 P-A 只有文稿/证据/未应用规范补丁，适用文稿校验，产品完整门/Gate A/Gate B 不冒充 PASS。

## 具体补丁、实施文件及决定

[规范补丁](spec-proposed.patch)增加 §12.3.8 并同步有限交叉引用；已执行 apply-check，保持未应用。
源规范字节hash和patchhash见 [PROPOSED决定](decision.json)。
预期 P-B 源码只需 `core/deps.py`（内部事实）和 `rules/env.py`（新原因分支），
测试覆盖core graph/deps、rule priority及CLI；更新CHANGELOG与当前报告。
不需要 engine/scanner/redaction/schema、依赖、版本、预算或gold修改。若发现必须触及冻结边界，另提供具体审阅。

**待决：是否接受 A、该具体规范补丁、目标存在/候选状态未验证的保守边界和全仓SKIP成本？**
备选 B 为保持现行 WARNING与diagnostics，将此已证明的捕获缺口继续留 OPEN。
不推荐把所有 `closure.complete=False`、全部 `unparsed`、一般 grammar 统一转换为SKIP。
只有具体接受之后，P-B 才先写失败回归，再最小实施，完成最终质量门、五项目Gate A与受影响扩展、推送及CI。

## 整个 R07-C 与后续路线

D-G 只处理最终 depth frontier，不关闭 R07-C。后续仍需逐项 P-A：

- requirements 行/续行/注释、unsupported include语法、constraints/VCS/editable等支持及信用边界；
- reached candidate exclusion、遗漏roots/candidates/use和listing完整性；
- manager单包值grammar、其他局部读取域、README/config/framework检测覆盖；
- 每rule的positive/negative充分证据与mixed-evidence结论，不能扩成全局PASS/SKIP开关。

这些不是本片自动批准的代码待办；可以继续做来源观察和具体方案。
A02外部真实反馈、A03带日期事实刷新与公开表单核验可独立推进；不发邀请或提交申请。
资源结果保留候选绑定，五原始metadata与HF403仍阻塞；本片不调用付费API、不发布版本。
