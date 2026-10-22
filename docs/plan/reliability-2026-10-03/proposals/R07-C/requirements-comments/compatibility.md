# D-C：候选兼容性与保守成本

状态：**PROPOSED / NOT_IMPLEMENTED**。候选 A 的具体行为与验收见
[独立验收设计](acceptance-cases.md)；候选 B 保持当前合同。本页不批准 A，
不以既有 D-G 委托裁决代替本片决定，也不宣称 P-A 已跑新政策。

## 改变的是捕获和信用

本片不是把一类 WARNING 统一改为 SKIP。候选 A 让特定普通 requirements 行尾注释之前的
有效非 URL 声明进入已有依赖模型；后续规则、检测和初始化照现有合同消费这些新事实。
因此正信用增加、包使用增加、来源位置改变以及新失败都可能发生。

| 可见结果 | 具体触发 | 必须披露的代价 |
|---|---|---|
| 缺 pin WARNING/CRITICAL 消失 | 先有 `torch>=2`，新捕获 `torch==2.5.1 # pin` | 全仓 existential exact 可让无关子项目的声明消除 warning；不是已证明选定环境安装同一 build |
| 原 applicability SKIP 变 WARNING/CRITICAL | 原先只有 `torch>=2 # note`，没有其他 use | 新包进入 in-use，隔离阈值可从 exit 0→1；并非所有使用者都会得到更少问题 |
| 原 applicability SKIP 变 PASS | 原先只有 `torch==2.5.1 # pin` | 有信用的真实 captured use 经既有 engine 汇总；Python empty-result veto 仍可能改为 SKIP，不能承诺总是 PASS |
| `env.lockfile_present` WARNING 变 PASS | 一个此前仅因此类注释不完整的 root，所有捕获声明都 exact，其他 include 均完成 | requirements-as-lock 资格与包集合可能新增；不能只测试 pin rule 或只说“诊断减少” |
| 新依赖触发 profile 或改变 evidence | 新增 vllm/peft 等 shipped dependency signal，或新来源排在旧来源前 | medium profile、代表 evidence、默认 init profile 和 required-field scaffold 可能变化；不能只比较 profile 名字 |
| init 后 L1 与 export 改变 | 默认选择新增 medium shipped profile，或新增/移除 notable finding | 用户可看到更多待填字段或告警，也可看不到原 warning；显式 profile override 与输出格式合同保持 |
| 既有不确定性保留 | 新声明为 loose，仍有 D-F/D-S、D-L、D-M 或 D-G | 使用各自原原因和优先级；本片不新增通用 comment-SKIP，也不把原不确定性改名 |
| 全量包/诊断事实改变但 findings 不变 | HarmBench 新增非 critical 的 art/tenacity | summary 不变不是零差异；需接受完整事实、物理行号和诊断 delta |

WARNING/CRITICAL 门的 1→0 与 0→1 都属于待批准兼容成本。独立 qualifying finding 仍可让
命令退出1；FAIL-only override、ignore/suppression、默认 text/show-skipped/show-passed、
JSON 和 default export 均保留现有处理方式。无需也不得顺手改变 engine 或 renderer。

## 为什么边界必须逐字保留

- **原 route 优先。** 原完整行含字面 ` @ ` 就沿用该旧分支；即使它只出现在看似注释的后缀中，
  也不先截断后转为 ordinary。例如 `torch==2 # mention @ place` 仍不获本片新支持。
- **完整原行成功优先。** ordinary 分支先按旧 parser 解析完整原行，成功就原样保留；
  不尝试前缀，不重新解释旧合法 marker 中的 ` # ` 或旧 URL。仅完整原行失败且无文件 veto，
  才尝试一次新 comment 前缀；因此本片是有界补充，不撤销或重写旧成功声明。
- **新的前缀必须没有 URL。** 原有 route 对 ` @ ` 是字面检测，不能覆盖所有 tab/紧邻 `@` 变体。
  仅要求 `Requirement(prefix)` 成功可能意外新增 direct-reference use。额外的 `req.url is None`
  只限制本片新候选；完整原行原本成功的 URL 不被撤销，其他 manager 的共享 parser 不受影响。
- **只试第一个候选。** `[ \t]+#` 可能出现在 marker 的引号内部。旧完整行有效时早已原样保留；
  仅旧完整行失败时尝试截断，若前缀仍失败则保留原完整行诊断，不继续找第二个 `#`，
  因此某些更复杂尾注释仍不支持。
- **ASCII 分隔符是有意边界。** 不将所有 Unicode whitespace 都当成新 comment 分隔符，
  不按“看起来像注释”模糊修改原行；无分隔符的 `#` 和 URL fragment 继续按旧 parser。
- **文件级反斜线 veto 不判断作者意图。** 任意物理行 `rstrip()` 后以 `\` 结束就禁用该文件全部
  新 comment 支持，含整行注释、directive、前后无关行、多个尾反斜线及其后的空白。
  这会让本来独立的简单 comment 行继续落在旧支持范围之外，属于明确接受或拒绝的保守成本。
  它不能传播到没有命中 veto 的其他已捕获文件，也不能引入预读来检查未到达目标。
- **不借机做续行。** 不 join，不猜测逻辑行号，不展开环境变量，不提高文件或图预算；
  它既不是完整 pip parser，也不对未支持的安装语义作有效/无效认证。

原完整行成功时保持声明；原完整行失败且候选前缀未被接受时，保持原完整行诊断。
不得把候选解析异常转为 `DeclarationReadIssue`、吞掉原行或输出新的前缀诊断。
不增加包管理器、网络、provider、重依赖或安装行为。

## 原合同与历史

- 保留 Python exact 判据、canonical 名称、extras/marker 的现有静态解释、声明顺序和物理行号；
  同包冲突 exact、全仓正信用及 first captured evidence 的选择规则不变。
  新捕获更早的来源可改变选中的 evidence，这是输入事实变化，不应重排旧声明来掩盖它。
- 只改 RequirementsGraph 的 ordinary 分支；PEP 621、Poetry、Pipfile、Conda/embedded pip
  共享解析入口保持原语义。requirements 声明不会因此成为 format-lock 项目边界或配对 manifest。
- include/constraint/directive/URL/VCS/editable 的原 route、读取边界、节点、depth 10 和 D-G
  final-node frontier 定义不变。删除一个 grammar error 可以使 closure complete；仍有 cycle、
  depth、不可读、unsupported 或非 exact 时，相应 requirements-as-lock 仍受原合同约束。
- 新 exact 与既有 qualified 信用仍在 D-F/D-S→D-L→D-M→D-G 前处理；剩余包的旧完整
  message/hint/evidence 不添低优先级原因。未知 use、applicability、Python veto 不扩大。
- 不改规则 ID、schema、持久化字段、依赖、版本或 audit/diff 的默认 fail-on。
  历史 audit/run/export/资源证据仍绑定原候选，不能批量更新成新结果。

## 五项目的具体非零边界

[D-G 来源记录](../requirements-depth/portfolio-source-evidence.json)固定了五份 requirements、
60 行原文；它的 depth-only 零差异判断不能移用。
HarmBench root 第18/19行分别是 `art  # for ArtPrompt`、`tenacity  # for ArtPrompt`，
候选 A 在没有文件 veto 的前提下新增两条 unversioned 声明，移除对应两条原诊断。
完整记录、SHA-256 和位置在[验收设计](acceptance-cases.md#五项目来源与预写差异)。

这还使该 root 的 closure 从 grammar incomplete 变 complete，但 range/unversioned 成员使
`is_exact` 仍为 false，不能把这条差异误写成新增 root lock。两包不属于现有 critical 集合或
shipped dependency signals；其他既有 nested exact、format-lock 和检测来源保留。
因此预期完整 findings、profiles/hints、init/L1/default export 不变，完整 facts 和诊断有上述
非零差异。若后续独立源核验或当前观察发现其他项，必须先解释和更新提案依据，不能拿实际
未来输出反填预期。其他四项目按原来源预期无新候选，仍须逐项核对全部输出。

如需新的前瞻 gold/基线补充，它应以独立源码事实和明确审阅为依据，保留旧 oracle 字节。
本 P-A 不修改历史 gold；具体接受前不应用 parser 补丁，不执行未来政策或标记产品 Gate PASS。

## 本片之后仍开放

续行语法、一般 include 支持、constraints 求解语义、URL/VCS/editable、环境替换、manager
单包值 grammar、未知/遗漏 use、listing、README/config/framework 覆盖及充分证据仍需另行 P-A。
候选 B 保留当前捕获/诊断/退出行为，可以明确记录该已知限制；不能把“不支持”称作外部格式非法。
两候选都不授权付费 API、GPU、外部邀请、申请提交或版本发布。
