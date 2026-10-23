# R07-C D-M-P / P-A：成功解码后的 PEP 621 字符串未提取

日期：2026-10-23。状态：**PROPOSED；规范补丁未应用，产品政策未改变**。
前置为[D-C P-B](../../../../../dogfooding/2026-10-22-r07c-requirements-comments-pb/README.md)，基线 `cc6e891`。
本片细分 D-M-S 明确保留的字符串内容，不重新裁决其结构表，也不沿用 D-G/D-C 的批准扩展范围。

## 目标与例子

`project.dependencies = ["torch>=2", "not a requirement !!!"]` 能成功 TOML 解码，列表成员也是字符串。
当前提取器保留 torch 的宽松声明，失败项进 unparsed，声明失败字典仍为空。
在无其他信用时缺 pin 规则仍 WARNING。失败既没有证明 pin 存在，也没有证明声明已被完整提取。

推荐 A：只把两个既有 PEP 621 调用点的真实失败记录为文件级 `unparsed_requirement`，
沿 D-M 把剩余当前使用、未获信用的关键包改为 SKIPPED/INFO；保留原声明和原诊断。
若同一列表已有 `torch==2.5.1`，保留该正面信用，不因坏兄弟条目撤销。
这是保守产品选择，不是 PyPA 要求审计 SKIP，也不是认证整个文件无效。

## 为什么选择这个下一片

现计划按独立 P-A/P-B 推进；D-C 后没有已批准待实施的产品切片。
D-M-S 与现行 §12.3.7 明确把字符串内容留为 OPEN。
本片可本地完成并复用现有失败现场，比验证全部 manager 包值或 pip grammar 更有界。
五 pins 的 163 条 PEP 621 字符串均可独立解析；五项目不变不能代替坏值分支验收。

## A 的精确边界

| 原入口 | 新事实触发 | 排除边界 |
|---|---|---|
| `project.dependencies` 原 list 内 str | 原来的 Requirement 调用在既有捕获分支失败 | 非 str 仍归原 D-M-S，不增遍历 |
| `project.optional-dependencies` 原 mapping 内 list 的 str | 同上 | 非 list、缺失、空组保持原结构合同；不验证组名 |

只在成功解码且现有提取器确实到达该字符串时处理。空/纯空白 str 也实际解析失败，纳入；
缺失、空列表/空映射本身不触发。保留成功的 marker、extras、URL、任意相等、范围、通配符与 unversioned 输入。
新原因表示本次提取失败，不能作为完整标准校验或可恢复 pin 的证明。

从现有唯一解析调用的真实失败反馈记录，不解析 unparsed prose、不复解析、不猜包名、
不修复内容、不剥注释、不重读文件。D-C 只限 requirements 图，不能扩散到 PEP 621。
共享 helper 也供 requirements 图/embedded pip 使用，P-B 必须有明确 PEP 621 context/result；
其他调用者不选择新事实。本 P-A 没有运行候选 parser/规则补丁。

## 事实、部分信用与优先级

内部 `DeclarationReadIssue` 仅拟新增 `unparsed_requirement`；路径到单一原因字典保持。
同文件最多一项；已有 unreadable/invalid_syntax/invalid_structure 时保留原原因，等价 setdefault。
旧/手动对象仍默认空字典，不增 persisted schema。

保留全部原声明、顺序、物理行、specifier、exact、unparsed、lock 集合/关联、presence、
project roots、uncertain barriers、read traces 和预算。不能因字符串失败新增项目屏障或清空有效部分。
profile/init 所见的捕获 inventory 不变。

沿现规则：exact/qualified 信用 → D-F/D-S → D-L → D-M 声明失败字典 → D-G。
只替换该点本应 missing-pin 的当前已知使用包，复用 D-M 原 message/fix_hint/排序后的失败路径。
已有高优先级分支保留其消息/evidence；已有 D-M 可仅增加新失败源路径。
保留 first declaration/import evidence，不添加 per-package PASS、不从坏输入推断 unknown use。

## 兼容成本与验收

影响仍沿全仓 existential exact 合同，不套用格式 lock 的局部归属。
无关子项目乃至空白失败字符串可能使全仓剩余关键包 WARNING → SKIPPED/INFO。
不声称隐藏 pin 存在、恢复后有 pin，SKIP 不授予信用或完整性证书。
孤立 WARNING 或 FAIL-only promoted CRITICAL 门可能退出 1→0；独立 qualifying finding 仍可退出 1。
suppression、阈值、FAIL-only override、默认 text 的 PASS+skipped、export 隐去 SKIP、完整 JSON 保留 finding 均保持。

详见[兼容表](compatibility.md)、[38 项独立未来验收](acceptance-cases.md)和[五项目来源](portfolio-impact.md)。
历史报告、gold、正式输入和 R01/R02 资源结果不回写或改绑。
[当前观察](current-behavior.md)只执行现产品，不是新政策验收。

## 文件范围和批准后次序

本 P-A 新增本包、报告和三处当前导航，521 个受保护产品/测试/规范等文件原字节保持。
[精确补丁](spec-proposed.patch)只拟修规范交叉引用并新增 §12.3.9，未应用。
P-B 最小产品范围预期是 `core/deps.py` 内部原因类型和两个调用点的失败反馈，
以及相关 core/rules/CLI/profile/init 回归、规范和 CHANGELOG；现 `rules/env.py` 消费应能直接复用。
不需要 engine/redaction/schema；若实际必须触碰 D-41 区域，另出具体审阅材料。

具体接受后：先 RED → 最小实施 GREEN → 受影响模块/lint/type →
最终同一输入的一次完整质量门 → 五项目 fresh Gate A、init/L1/default export 与受影响合成验证 →
报告、提交推送 main、精确新 HEAD 五项 CI。未来矩阵不是已运行测试。
普通政策片不完成里程碑/不准备发布，资源 Gate B 不适用；资源账本 BLOCKED 保持。

## 选择与待决

- A（推荐）：上述两个 PEP 621 失败入口，保留部分正面证据，复用 D-M。
- B：维持现 WARNING 和诊断，字符串缺口继续 OPEN。

待具体接受 A、精确规范补丁及全仓保守成本后进入 P-B；本次准备或推送不代表政策被批准。
Poetry/Pipfile 包值、embedded pip、requirements 其他 grammar、dynamic/build/groups、
unknown use、listing/framework 和充分证书仍 OPEN。不调用付费 API，不发布版本。
