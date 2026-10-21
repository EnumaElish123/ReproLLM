# R07-C P-A：已解码声明的结构缺口与部分提取（D-M-S）

日期：2026-10-22。状态：**PROPOSED；规范补丁未应用，产品政策未改变**。
基线 `88a26ee270c92c939140fe347b71f2909f8c7d97`。
D-M-S 是本提案的局部标识，属于既有 R07-C，不是新的全局里程碑。
前置为 [D-M 的 P-B 报告](../../../../../dogfooding/2026-10-21-r07c-declaration-read-pb/README.md)。

## 问题与当前行为

现行规范 §12.3.6 只捕获声明正文的已知读取／文档解码失败，明确将成功解码后的结构留为 OPEN。
`core/deps.py` 在若干分支使用 `value or []`、`value or {}`；错误容器或非字符串成员可能被跳过，
但有效兄弟条目仍会成为声明和 exact 证据。`DeclarationReadIssue` 目前只有
`unreadable`、`invalid_syntax`，结构被跳过不建立该内部事实。

例如，`project.dependencies = ["torch>=2", 7]` 能提取 torch 的宽泛声明；7 被跳过。
当前 torch WARNING 符合现行有界合同，但若修正第二项得到 `torch==2.5.1`，
全仓 existential exact 合同就会改变结论。结构错误本身既不证明有 pin，也不证明没有 pin。
若同一列表已经含 `torch==2.5.1`，保留该正面信用，不能因另一项错误反向撤销它。

[实际旧政策观察](observations/README.md)保存合成输入、预写预期和真实结果；
[五项目来源核查](portfolio/source-evidence.md)给出独立影响预期。
本轮不执行未来政策，不把建议结果或旧报告当作 P-B 已通过。

## 推荐的有限结构表

推荐 **A：只记录下表明确的结构缺口，复用 D-M 的缺 pin 不确定性分支**。
在现有成功解码后检查原始值，早于 `or []` / `or {}`，不增加文件读取、重试、候选或引用边。
“存在”指 key 真正存在；false、0、空字符串、错误种类的空容器不因 falsey 变成缺失。

| 已采集格式／位置 | 新结构缺口 | 不触发本检查的边界 |
|---|---|---|
| pyproject 根的 `project`、`tool`，以及有效 tool 映射内的 `poetry` | key 存在但值不是映射 | 缺失或映射，包括正确的空映射；`[tool.ruff]` 等正常工具配置 |
| 有效 project 的 `dependencies` | 存在但不是列表，或任一列表成员不是字符串 | 缺失、空列表；字符串的内容语法另议 |
| 有效 project 的 `optional-dependencies` | 存在但不是映射；任一组值不是列表；任一组列表成员不是字符串 | 缺失、空映射、空组列表；组名合法性另议 |
| 有效 poetry 的 `dependencies` | 存在但不是映射 | 缺失、空映射；**所有单包值内部形状和版本语法均不检查** |
| Pipfile 的 `packages`、`dev-packages` | 存在但不是映射 | 缺失、空映射；所有单包值不检查，其他类别不纳入 |
| environment 根 | 解码结果既不是 None，也不是映射 | None 保留旧空 YAML／顶层 null 兼容行为，**不表示有效环境文件**；空映射不触发 |
| environment 映射的 `dependencies` | 存在但不是列表，或成员既不是字符串也不是映射 | 缺失、空列表、字符串、映射；未知安装器／selector 映射不据此判错 |
| dependencies 内任一映射的 `pip` | key 存在但不是列表，或列表含非字符串成员 | 缺失、空列表；同一映射的其他键与字符串语法不检查 |

因此 `dependencies: null`、`pip: null` 会触发；顶层 YAML null 不触发。
这项空值边界是明确的兼容取舍，不是声称 Conda 规范允许无依赖的环境文件。
映射／列表是现有解码器返回的 dict／list；不执行包管理器，不做任意对象递归、字符串转换或额外类型推断。
同一文件可有多个坏位置，本次仅记录一条文件级原因；不能宣称精确列出了每个损坏字段。

## 内部事实与规则合同

建议只扩展 `DeclarationReadIssue` 为 `unreadable | invalid_syntax | invalid_structure`。
继续使用 `Declarations.declaration_read_issues` 的相对路径到单一原因字典，默认空；不新增持久化字段。
读取／文档解码失败仍优先，成功解码后的任一指定检查失败记录 `invalid_structure`。
检查不能依赖最终 `manifest_present` 或项目根是否合格，否则会丢掉 malformed project/tool/Pipfile 分支。

完整保留旧提取结果：所有声明及顺序、exact 版本、lock 包集合与来源信用、manifest/lock presence、
项目根、uncertain barrier、现有诊断和行号均不改变。不增加新的 `unparsed` 文本，也不从诊断 prose 反推类型。
有效条目与坏条目共存时继续提取有效条目；不以“整文件无效”为由清空声明或撤销已获信用。

仅 `env.llm_critical_deps_pinned` 按既有顺序消费：

1. 任一 exact 声明或合格 lock 信用优先。
2. 已有 D-F/D-S 关联 lock 不确定性、D-L Python 缺口分支保持消息、证据及优先级。
3. 剩余本应 WARNING 的当前已知使用包，若声明失败字典非空，沿 D-M 逐包输出 SKIPPED/INFO。

复用 D-M 的现有字面 message、fix_hint、首个声明／import 证据和排序后的全部失败路径。
message 的 “could not be read or parsed” 在本提案下包含结构未完整提取，**不表示正文不可读或零条目解析成功**。
实现预期仅涉及 `core/deps.py` 的类型与三个 manager 入口；`rules/env.py` 已有 D-M 分支无需新增分支。
这是拟定改动范围，未经批准不应用；若实施发现必须改 engine/redaction/schema，另行提交具体审阅。

失败影响范围沿现行全仓 existential exact 合同：坏结构可能藏在无关子项目或仅可能含工具配置的 pyproject，
仍可使全仓剩余已知关键包保守 SKIP。不能套用格式 lock 的同目录限制缩小它。
此保守成本必须与方案一起接受；SKIP 不授予任何 exact/lock 信用或完整性证书。
没有已知关键包、全部包已获信用、原 Python 空结果 veto、其他规则与生成规则均保持现行合同。

## 兼容性与可见结果

| 情况 | 当前 → 提案 A 的预期 |
|---|---|
| 有已知未获信用包，指定结构缺口是唯一新增事实 | WARNING → SKIPPED/INFO；已有来源证据后附失败文件 |
| 部分提取已有同包 exact 或 qualified lock | 保留信用；不能因坏兄弟条目撤销 |
| 一个包获 exact，另一个已知包无信用 | 前者保留信用，后者可能 SKIP；不添加每包 PASS |
| 已有正文失败与新结构失败混合 | 原 D-M 状态可不变，但排序后的失败证据新增路径；不能误称完整输出零变化 |
| D-F/D-S 或 D-L 已先触发 | 原消息／证据保持，不混入较低优先级 D-M 路径 |
| 无结构缺口、只存在排除的合法／未知形式 | 原结果保持；不认证这些形式已完整支持 |
| 孤立 WARNING 或 FAIL-only override CRITICAL 门 | 可由退出 1 变为 0；SKIPPED 不接受 FAIL-only severity override |
| 同时存在独立规则 WARNING | 仍可退出 1；阈值未改变 |
| suppression／用户 ignore | 保持现有 SUPPRESSED/INFO 合同 |
| 默认文本、默认 export、完整 JSON | 沿现有展示：文本可显示 PASS 加 skipped 数；export 隐去 SKIP；JSON 保留 finding |

无 rule ID、schema、CLI 参数、默认阈值、版本或依赖变更。现有 JSON 读者继续使用已有状态和 evidence 结构；
语义／门行为有变化，获批后的 P-B 必须记录在 CHANGELOG。历史 gold、报告及资源结果不回写。

## 官方事实与政策推断

- [PyPA pyproject 规范](https://packaging.python.org/en/latest/specifications/pyproject-toml/)定义依赖字符串数组及 optional-dependencies 的映射到字符串数组。仅使用类型依据，不据此扩展 ReproLLM 的构建依赖或 dynamic 支持。
- [Poetry 依赖规范](https://python-poetry.org/docs/dependency-specification/#multiple-constraints-dependencies)允许多条件数组及丰富来源表达；不能把所有包值非字符串统一标为错误。
- [Pipenv Pipfile 文档](https://pipenv.pypa.io/en/latest/pipfile.html)展示 table、版本字符串及不含 version 的来源映射；不要求所有映射有 version。
- [Conda CEP 24](https://conda.org/learn/ceps/cep-0024/)定义依赖列表、安装器子映射及 pip 字符串列表，允许其他子段／selector；未知映射不自动无效。

以上于 2026-10-22 查阅。**文件级保守 SKIP、全仓影响、顶层 None 兼容、排除包值语法**是本项目提案选择，
不是上述标准强制的审计结论。详见 [独立设计审阅](review-design.md)。

## 验收与五项目影响

[验收矩阵](acceptance-cases.md)覆盖容器／成员形状、有效空值、部分正面信用、恢复、优先级、展示与退出码。
本轮实际观察只执行旧产品；未来矩阵不是已经运行的测试。
五项目应分别核对全部受支持声明候选和字节、相关容器类型、完整源 pin/origin/clean；
不能仅凭没有环境文件或 warning 总数相同推断无差异。独立来源预期见 portfolio。

具体接受后 P-B：预写验收测试 RED → 最小实施 GREEN → 完整受影响模块及 lint/type →
最终相同产品输入上一次完整质量门 → 全五项目 fresh Gate A → 全部 init/L1/default export 与结构专项。
正式完整 JSON 只允许规范根 T-02 metadata 豁免；不忽略 evidence、顺序、类型、路径或诊断。
旧测试若刻意断言 malformed structure 仍 WARNING，需逐项说明批准的预期变更；不可批量复制新输出作 gold。
本 P-A 按文稿/计划分类：本地完整产品门、fresh Gate A、资源 Gate B 均 NOT_APPLICABLE；
旧政策有界观察和来源核查是证据，不冒充这些门。最终推送提交另查五项 CI。

## 备选、待决与未覆盖范围

- 推荐 A：上述封闭类型表，保留部分正面证据，复用 D-M；代价是保守影响全仓剩余关键包。
- 备选 B：保持现行 WARNING，只继续披露有界采集；保留恢复结构可能推翻缺 pin 判断的缺口。
- 不推荐无条件以全部 `unparsed` 或全部非字符串 package value 触发：混入合法形式、语法和其他读取域。

待决：**是否接受 D-M-S 方案 A 及 [具体规范补丁](spec-proposed.patch)，进入上述 P-B？**
见 [PROPOSED 决定](decision.json)和 [spec issue 本地草稿](issue-draft.md)。
执行总则 §5.9 要求具体规范决定；本轮准备和推送不代表政策已批准。
本提案不附已执行的未来实现，不要求接受未展示的实现代码。

requirements 行／指令／include 图、PEP 508 字符串语法、单包值内部结构、版本／名称合法性、
dependency-groups、Poetry group、Pipfile 自定义类别、Conda 未知安装器／selector、动态声明、
未知 use／遗漏候选、listing、README/config/framework 和充分性证书仍 OPEN。
本地证据不解除缺失原始 metadata 或 HF 授权阻塞，不使用付费 API，不发布版本。
