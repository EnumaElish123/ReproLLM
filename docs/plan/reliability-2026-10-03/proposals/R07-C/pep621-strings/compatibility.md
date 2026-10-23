# D-M-P：兼容性、全仓保守成本与历史边界

状态：**PROPOSED / NOT_IMPLEMENTED**，观察基线 `cc6e891`。
本页只说明候选 A 的待裁决成本；候选 B 维持现合同。完整未来验收见
[验收设计](acceptance-cases.md)，不是已执行的 P-B 结果。

## 唯一新增事实

候选 A 仅覆盖已经成功 TOML 解码、并由现有 `_parse_pyproject` 流程实际解析的
`project.dependencies`／`project.optional-dependencies` str。
当现有 `Requirement` 解析失败时，为该文件补充内部 `unparsed_requirement` 原因。
这表示**该 PEP 621 声明字符串未被现有解析器解析**，不表示整个 TOML 文档无效，
不表示外部所有包管理器都拒绝它，也不推断失败字符串中的包名或可能 pin。

已有 `unreadable`、文档 decoder 的 `invalid_syntax`、有界 `invalid_structure`
必须优先保留；新事实不能覆盖它们。空串／空白 str 在当前实际调用失败时纳入，
缺失字段、合法空列表和空 optional group 不触发。非 str、未进入现有调用的结构和字段
不为本片增加检查。既有原始 `unparsed` 文本、行号及诊断仍保留。

新事实只复用 D-M 已有消费，不新增 finding 分支、公开原因码字段或输出 schema。
不得把共享 `_add_requirement_line` 的其他调用者一并扩展：requirements 文件、
environment.pip、Conda、Poetry 和 Pipfile 保持当前合同。

## 用户可见前后变化

| 情况 | 当前合同 | 候选 A | 兼容成本与保留边界 |
|---|---|---|---|
| 已知 torch use、无信用，另有本片失败 str | FAIL/WARNING，或 FAIL-only override 的 CRITICAL | 原 D-M SKIPPED/INFO | 声明缺口可能藏有全仓 existential exact；并未授予 pin 信用 |
| 上行情况只剩 pin rule 达到门槛 | warning／critical 阈值 exit 1 | exit 0 | 退出 1→0 必须明确接受；这不是复现实验已通过的证明 |
| 另有独立 warning 达到 warning 阈值 | exit 1 | 仍 exit 1 | pin finding 仍改变；独立违规不能被保守路径压制或用来掩盖差异 |
| 无关子项目一个 str 失败、其他项目有多个 uncredited use | 各包原 WARNING | 各包沿 D-M SKIP | 全仓影响是有意成本；不按同目录 ownership 限制该不确定性 |
| 同包 exact 或合格 lock 已提供信用 | 原信用 | 原信用 | 不撤销部分正面证据，不产生逐包 PASS，不新增版本冲突规则 |
| D-F/D-S 或 D-L 已赢分支 | 原 SKIP 及其原因 | 完整原 finding | 不追加较低优先级 D-M 路径、hint 或 evidence |
| D-G 是原先唯一原因，新增本片失败 str | D-G SKIP | 更早的 D-M SKIP | 状态不变但 message/hint/evidence 按原优先级改变，须全量比较 |
| 失败 str 存在，但无已捕获关键包 | 原 applicability SKIP | 原 applicability SKIP | 不创造未知 use，不从似乎含有 torch 的坏片段恢复名称 |
| 所有已知关键包均已获信用 | 原空结果处理 | 原空结果处理 | Python empty-result veto 仍在，不能一律承诺 PASS |
| 旧 D-M 原因已存在、再捕获新失败文件 | 已有 D-M SKIP | 同状态，可能增加源 evidence | 路径增量也须说明；不据 summary 不变宣称零差异 |

规则顺序保持为：**qualified／exact 信用 → D-F/D-S → D-L → D-M（含本片）→ D-G → 原 WARNING**。
这不是统一把 WARNING 转为 SKIP；仅当前已捕获的 use、未获信用且未被更早分支处理的包受影响。

默认 JSON 保留完整 SKIPPED/INFO finding；FAIL-only severity override 不改变它。
默认 text 按现有 renderer 隐藏 skipped 明细但显示 skipped 计数，因而可能同时出现
`Findings: PASS`；`--show-skipped` 可见原 D-M 提示。此显示不证明全仓无问题。
ignore 沿现流程转为 suppressed/INFO，保留源 evidence 并附配置 reason；不改变 suppression 机制。
default export 按现有合同仅列 WARNING/CRITICAL notable 项，故受影响旧 warning 可消失，
原 summary 相应改变，不把 S 冒充新增成功记录。

## 原始证据与项目关系不改变

- 成功捕获的声明、顺序、canonical 名称、specifier、exact、物理行号和原诊断原样保留；
  失败条目不作为 declaration，也不触发新的 profile/dependency signal。
- 不改 PEP 508 接受 grammar、exact 判据、marker 解释、URL 支持，不截断注释、不修复字符串。
  合法而非 exact 的现有声明不能被新事实误判为失败。
- 不添加 read/probe/预解析，不扩展扫描预算、source 集合或 requirements 图；
  不为本片新增 `_uncertain_directories`、barrier、manifest 资格变化或锁关联。
- 已合格 pyproject 仍提供原有项目根及 lock 配对；有效兄弟旁的一条坏 str 不撤销这些事实，
  原本已有结构错误及关联边界也不因此放宽。
- init 的 profile 检测、hints 和生成 scaffold 来源不变；后续 L1 audit／export 可因本片
  pin finding 改变，须把“初始化文件不变”与“后续报告不变”分别核对。
- 原始解析诊断不因新增原因删除或改写；不回显新的失败内容，不额外持久化字符串。

## 新旧对象和历史记录

| 对象／操作 | 兼容合同 |
|---|---|
| 内部 Declarations 新采集 | 只扩展内部原因的允许值；既有默认空字典、手工构造对象和无触发输入保持 |
| 同文件已有旧原因 | 原原因优先；不得替换为 `unparsed_requirement` |
| schema 及旧读者 | 不新增 persisted 字段、不变 schema_version；旧 Finding/AuditReport 读者接收既有 S/INFO 形状 |
| 同输入新 audit | 仅命中本片时按待批准规则重新求值；不是把旧报告自动迁移为新结果 |
| 旧 audit/run/export、snapshots、资源回执 | 保留原字节、候选归属与历史结果，不批量重写；后续导出仍遵守现有历史输入选择合同 |
| 字符串已被用户修复后的新采集 | 不保留过期原因；成功 exact 恢复原信用，合法 loose／删除按剩余输入恢复原缺 pin 判断 |

不变更规则 ID、aliases、依赖、产品版本、默认 fail-on、持久化 schema、engine 或 redaction。
若后续实现意外需要这些范围，应先独立提交具体审阅材料，不能从本片接受推导批准。

## 五项目的独立零差异预期

范围为 `val.md` 的五个固定 pin，不改变原件或 gold。[独立来源盘点](portfolio-source-evidence.json)的
**163 个有效 PEP 621 字符串**逐条绑定项目、相对路径、字段路径、原文位置、原始 hash 与当前
解析成功观察；总数本身不是充分证据，也不能把“没有此类字段”算成已解析成功。

| 固定项目 | project.dependencies | optional-dependencies | 总数 |
|---|---|---|---|
| lm-evaluation-harness | 14 | 84，分布在 31 组 | 98 |
| LlamaFactory | 31 | 字段缺失 | 31 |
| FastChat | 15 | 19，分布在 5 组 | 34 |
| HarmBench | 没有 PEP 621 来源 | 没有 PEP 621 来源 | 0 |
| llm-dp-finetune | 没有 PEP 621 来源 | 没有 PEP 621 来源 | 0 |

这些已成功解析的字符串不触发新原因，故候选 A 对五项目完整 facts、declarations、
issue 字典、diagnostics、profiles/hints、L0、init 全部文件、L1、default export 与 verbose
预写**零差异**。这只限定在固定输入和本片；D-C 已改变的 HarmBench art/tenacity、
两条诊断及 closure 是既有基线，不能重复计成本轮 delta。
若后续来源核验显示任何实际失败 str，须先更正提案和独立预期，不复制候选输出反填 gold。

本 P-A 不声称运行了候选政策。接受后的 P-B 必须先补回归，再执行一次最终完整质量门、
新鲜五项目 Gate A、受影响验证与精确推送 HEAD 的五项 CI；旧候选结果不能自动改绑。

## 备选与仍开放的边界

候选 B 保持当前 WARNING、诊断与现有不确定性；已知缺口继续 OPEN，不能声称现有
缺 pin 判断已排除失败字符串可能藏有的 exact 声明。

manager 单包值、environment.pip 的字符串 grammar、requirements 续行／constraints／URL／
一般 include、未知 use、遗漏候选、listing、README/config/framework 覆盖及充分证据仍须
另立具体 P-A。当前 D-C 接受和此前 D-G 委托不批准这些政策，也不自动批准本片 A。

资源账本中的原始 metadata 缺口／HF 访问阻塞、A02 独立反馈和 A03 申请授权保持各自状态。
本片不调用付费 API、不使用 GPU、不发送外部邀请、不提交申请、不发布版本。
