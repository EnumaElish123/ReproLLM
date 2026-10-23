# D-M-E 独立设计审阅与未来验收草案

状态：PROPOSED / NOT_IMPLEMENTED。审阅基线 `72bf2fc150b8b00cc32a5a75d2ffa13387edbc3e`。
本稿只读当前规范、实现与既有测试；没有运行候选产品、实现测试或改写规范，也不是本轮产品门的通过证明。

## 独立结论

推荐方案 A：只在 `_parse_environment` 现有 successfully-decoded mapping 的 `dependencies` list，且其既有 mapping 成员含 list 型 `pip` 时，对原来已经遍历的 str 且 `.strip()` 非空的成员，复用其已有 `_add_requirement_line(pip_line.strip(), path, lineno, result)` 的 False 反馈，以 `setdefault` 给该逻辑源记录已有的 `unparsed_requirement`。它只表达某条已实际解析的字符串未被现有 Requirement 接受，不是整份 YAML 读失败或完整包管理器格式验证。

方案 B：保持当前合同，失败字符串仍只留原 unparsed 诊断，不追加这一 typed cause。B 保留当前捕获视图下的有界 WARNING/exit 1；规范 §12.3.1 已明确它不是完全证明的违规结论，尚未表达的 typed uncertainty 缺口仍保持 OPEN。A 把这一已知提取失败接入已接受 D-M 的保守消费方式，不过必须单独接受其具体范围及全仓保守成本；旧 D-M-P 授权并不自动包含这里。

最小实现仅需在现有环境 caller 检查 helper 的 bool 并 setdefault；不应改 helper 的输入、异常边界、语法、返回约定或 env rule。现有 cause vocabulary 已包含该值，无需 schema、引擎、scanner、redaction 或依赖改动。

## 共同独立字面预期

除逐行另述，fixture 含 `control.py` 第 1 行 `import torch`，完整 Python 采集、无 exact/lock/其他失败、安装版本 seam 固定为空。W 指 pin rule 的 FAIL/WARNING，S 指原 D-M SKIPPED/INFO。完整报告必须先独立写出，不得由候选输出填充。

A 的 S 必须完全复用规范 §12.3.6：message 为 `{display} is used; a dependency declaration body could not be read or parsed, so missing pin evidence is not established`；fix hint 为 `Review {display} declarations and failed dependency source files; restore readable, valid declaration bodies before deciding that exact pin evidence is absent.`。保留原 rule ID、aliases、category、level、origin/suppression 默认值。先保留该包原 first declaration evidence，若无则 first import evidence；再按不同失败逻辑路径字典序各附一个 file evidence，note 恰为 `{display} possible exact declaration unverified`，不增加 entry evidence/行号。原 first-import evidence 是 `control.py:1`、note imported；其他字段按 Finding/Evidence 原 schema 默认值，不用只比 status。

Core 的“其余不变”要求完整声明每字段及次序、源、line、unparsed 每字节及顺序、manifest presence、project manifests、uncertain directories、lock inventory/packages/read_issue/association、完整 requirements graph、scanner/read 调用轨迹逐项比较。S 不给予信用、不推测失败字符串的包名、不增加 in-use。规则优先序为 qualified/exact credit → D-F/D-S → D-L → D-M（含 A）→ D-G → W。隔离退出码用例只启用目标规则，不允许其他 WARNING 遮蔽变化。

## 未来验收表（A01–A38：38 行，不是本轮已执行测试）

A01–A38 属于本页验收设计命名空间，区别于 root 既有行为 observer 的 E 系列案例。38 是设计行数，不是 pytest 收集数、执行数、通过数或候选政策门。

| ID | 独立输入 / 分别参数化的维度 | 方案 A 的完整业务预期 |
|---|---|---|
| A01 | `environment.yml`，`dependencies: [{pip: ["torch=="]}]` | 一次现有 Requirement 失败，新增该源 `unparsed_requirement`；零失败条目 declaration；原 `environment.yml:1: torch==` 诊断保持；W→S；manifest true，project 对 conda-lock.yml 的资格和空 barrier 保持 |
| A02 | 同 A01 改为 environment.yaml、嵌套目录、两种 basename 各自单独存在 | 仅按发现的逻辑源路径记录，相同 cause；不硬编码 yml；不扩大候选 basename/目录；其余完整结果与当前合同一致 |
| A03 | pip 缺失、空列表、`""`、space/tab/newline-only str | 原缺失/空列表不调用；原空白 str 经 `.strip()` 为空即跳过，零新增 Requirement 调用/诊断/cause；只有原 import 时保留 W，不与 PEP 621 空串行为混同 |
| A04 | 首尾空白的有效/失败 str，含内层空白 | 仅传入既有 strip 后字符串一次；失败诊断保留 trimmed 文本，成功声明与当前一致；不得传原 raw、再 strip 内层、做第二次解析或生成新诊断 |
| A05 | dependencies 的第 1/2/3 个元素为 pip mapping；一个 pip list 多个条目；加空行/注释移动 YAML 物理行 | line 保留 dependencies 的 1-based 序号，列表内全部使用父序号，不能改成 YAML 物理行/子序号；原诊断精确不变 |
| A06 | 成功 str：bare、range、wildcard、arbitrary equality、extras、marker、direct URL、valid exact/local/pre/post/dev/epoch | Requirement 原成功接受集合、声明与 exact 规则保持，无新 cause；合法不等于 exact；marker 不求值、URL 不解析网络 |
| A07 | 同一 pip 列表/多个 pip mapping 中失败前后有 valid exact/loose、Conda 声明 | 成功兄弟和原次序全部保留；有一失败即仅文件级 cause；同包 exact 继续胜出；不清空列表/文件，不重排条目 |
| A08 | 同一文件多个失败/重复失败、两个 pip mapping，及重复出现同一个非空 str | 每已有调用一次、每原诊断一次；cause 单一文件级项；不去重原诊断或新增失败 entry 恢复 |
| A09 | 多个 environment 失败源及既有 PEP 621 失败源，路径顺序不同 | 保留原采集次序和各源 cause；D-M evidence 包含全部 distinct 失败逻辑路径并排序；不按物理文件身份折叠 |
| A10 | 同源已有 invalid_structure，如 pip list 含非 str 又含真正失败 str，或另一 dependencies 成员类型错误 | 仍解析原来可用 str/兄弟；保留 invalid_structure，不覆写；原因字典/manifest/project/barrier/诊断的其他字段遵从原 D-M-S，无额外结构检查 |
| A11 | existing read_text None / yaml decoder 已捕获异常 | 原 unreadable/invalid_syntax 与原 early return、barrier、诊断保持；不遍历未解码条目、不调用 Requirement、不降级原因 |
| A12 | 顶层 None/empty YAML/explicit null、非 dict、dependencies 非 list，pip 非 list/非 str 成员 | 顶层 None 的既有例外与 D-M-S 既有 wrong-type 原因保持；未进入原调用的条目不制造新 cause；不把结构错误改名 |
| A13 | missing dependencies、`[]`、unknown-only mapping、shape-compatible empty manager values | 不新增 cause/声明/use；manifest presence 与 dependency-list 项目资格的既有区别不变，空内容不是 completeness 证书 |
| A14 | unknown installer/selector mappings、extra keys、嵌套的 pip key、mapping 非 str 值 | 只解析 dependencies 直接成员原来的 pip list；其他 key 仍忽略，不递归，不从文本 `pip` 或错误结构恢复条目 |
| A15 | 只有 Conda entry 有坏 grammar/unsupported channel/build，或其与空白 pip 同存；另加实际 pip parse fail 对照 | Conda 原诊断、partial declarations、pytorch→torch 与 exact subset 不变；坏 Conda 自己不产生新 cause；仅对照中实际 pip 失败产生该源 cause |
| A16 | requirements 图/D-C comments/D-G frontier、Poetry/Pipfile 值、PEP 621 字符串；pip 有 `-r pins-extra.txt`/comment 等 directive；配对 `-r requirements-extra.txt` 对照 | 本片不会从全 helper 调用普遍开关；requirements/manager 值保持旧合同，PEP 621 保留 D-M-P；D-C comment 回退不延伸。`pins-extra.txt` 非既有独立 requirements root，不新增读取/include expansion；`requirements-extra.txt` 本来独立发现且可授 exact 信用，不能误称 embedded include expansion。pip 可支持但当前 Requirement 不提取的 directive/comment 只记 extraction failure，不判非法 pip/environment |
| A17 | logical internal alias、outside-root symlink、filtered/oversize/binary candidate，以及手工旧 Declarations | 旧默认空字典保持；不新增 candidate/probe/read 或物理 ownership；安全拒绝仍按现有 unreadable 路径，不读外部内容；真实 symlink case 不能以权限 skip 冒充 PASS |
| A18 | 同输入两次 fresh scan；失败改 exact、改 valid loose、改 blank、移除条目/文件 | 失败重复确定；修复/移除后的新对象无旧 cause；exact 信用恢复，其余按真实剩余 use 恢复 W；先前对象/历史文件不修改 |
| A19 | 同包 exact 来自同 pip/Conda/PEP621/另子项目；含冲突 exact | 原仓库级 existential credit 胜出，无该包 pin finding，不新增 per-package PASS/conflict；不因失败撤销此前 exact |
| A20 | 唯一同目录 environment + conda-lock.yml，成功 declaration 或 qualifying import 给同包合格锁信用；坏 pip 另条目 | lock 内容/资格/包集合和已有信用保留，无该包 pin finding；不把新 parse cause 误作 uncertain directory/barrier 或 invalid manager |
| A21 | 两个 environment basename 同目录，与 conda-lock 并存；跨目录/近项目/已有 barrier 对照 | 保留既有 ambiguous pairing 和 ownership 合同，不借 cause 新增/撤销锁信用；未获信用且实际失败的包按 D-M S；bad basenames 的存在不读取新来源 |
| A22 | 新 cause 与关联坏/结构坏 lock 的 D-F/D-S 同存 | D-F/D-S 全 Finding 原样优先，不能追加低优先级 D-M 源 evidence/message；锁存在性规则不变 |
| A23 | 新 cause 与 Python gap + captured format lock package 的 D-L 同存 | D-L 全 Finding 原样优先；未在锁列出的其他未信用 use 可走 D-M，不能整规则统一换文案 |
| A24 | 新 cause 与旧 D-M/body/structure/PEP621 cause 及 D-G targets 同存 | 单个原 D-M S，distinct declaration paths 一并排序；已有 S 也可能 evidence delta；不附 D-G target evidence，不新增原因优先级 |
| A25 | unrelated/subproject environment 的一个失败非空字符串，另一项目 import torch、numpy | 无信用两包 W→S，保守影响全仓，不套用 format-lock ownership；失败串无须像相关包/可修复 exact，不宣称真的存在 pin |
| A26 | Python coverage 完整/gap/内部 unavailable，且相同失败源已实际捕获 | D-M 分支独立于 Python coverage；完整优先级保留；不扩大 Python scanning 或把依赖原因等同 Python gap |
| A27 | 仅失败 str、无 captured critical use；或所有 critical 均获信用，各自完整/不完整 Python | 不从失败词猜 use；no-critical applicability SKIP 不变；有信用空结果仍按既有 Python PASS veto，不能统一给 PASS/额外 D-M aggregate |
| A28 | exact 包、D-F/S 包、D-L 包、新 cause 影响包同时存在 | 逐包保留原获胜分支和 first-use evidence；规则不能因全仓字典非空提前结束；无额外 aggregate/逐包 PASS |
| A29 | isolated pin rule，warning 阈值；FAIL-only override→CRITICAL 后 critical 阈值 | 当前 W/CRITICAL exit 1，A 的 S/INFO exit 0；原 message/hint/evidence 按共同预期，root report summary 全量预写；无新 status/severity |
| A30 | A29 加独立 python-version WARNING，warning 阈值 | pin W→S，独立 finding 全字段保持，exit 仍 1；既有 lock-presence WARNING 也不可被本片吞掉，不能把相同 exit 声称零差异 |
| A31 | fail-on never、default/explicit severity overrides、alias/ignore/suppression | 原阈值/override/suppression 合同保留；FAIL-only override 不提升 S；ignore 仍 suppressed/INFO，原 D-M evidence、mandatory reason 与原 INFO severity 配置 evidence 保留；全部 Finding 比较 |
| A32 | default text、show-skipped/show-passed、JSON、global verbose 正确位置 | JSON 保留 S；默认 text 可 Findings: PASS 但 skipped count 保留，默认隐藏其明细；show-skipped 展示原 D-M；原 pip unparsed 只按现有 verbose 可见性显示，stderr 字节与旧诊断一致 |
| A33 | disposable clone 的默认/显式 profile init、L1，成功 signal 与失败串混合 | 失败不新增 profile/use；完整 detection、hints、代表 evidence、init 全部生成文件不变；L1 仅适用 pin finding 按 A 变化，不写用户源/配置 |
| A34 | 无历史 run 的默认 export，原有 pin WARNING 与独立 notable finding | S 不再列入原 WARNING/CRITICAL notable 列表，原 summary 按变化更新；不增加 skipped notable；其他 notable 条目完整不变；比较整个 export 文件 |
| A35 | 重复 audit/export、不同 disposable root、已有历史 audit/run/export/snapshots | 仅 AuditReport 根 generated_at/reprollm_version 按 T-02 豁免；其他完整结构/字节严格比较；原历史对象及文件 hash 不变，不回写或重解释为新政策验收 |
| A36 | 五固定 pins 的 environment 每个既有实际 caller input，逐 source/hash/ordinal/raw str/strip 分类盘点 | 在源审计完成前不许宣称零触发或零差异；有真实失败时逐条预写 cause/full Finding/consumer delta，再与独立旧 oracle 比较；无失败才预期本片零差异，不能复制当前输出为 gold |
| A37 | P-B 最终 product/tests 冻结后一次完整质量门 → 五项目 Gate A + affected → 原 originals SHA/origin/clean 复核 | 每门确实执行并记录退出/耗时/完整差异才 PASS，缺项目/dirty/crash/未解释 delta 失败；资源 Gate B 依适用规则 NOT_APPLICABLE/BLOCKED，不拿旧 CI/资源结果当 current；精确最终 HEAD 五 CI 另核 |
| A38 | P-A 本轮自身以及未来 P-B patch review | 本轮不应用政策/运行未来测试；给精确 §12.3.10 proposal、所有 forward refs、兼容性、批准边界及输入证据；产品/引擎/scanner/redaction/schema/version/依赖不变。获具体接受后才先 RED、再最小实现、最终质量/GateA；整个 R07-C、其他语法/充分证书仍 OPEN |

## 兼容性与可能漏项

- A 可把全部剩余 uncredited in-use 包由 WARNING/升级 CRITICAL 变 S/INFO，使 isolated exit 1→0；无关子项目或看似不可能是 exact 的坏片段也能触发。这是明确政策成本，不伪称 false-negative 已消除。
- 原 cause 同源 invalid_structure 已先存在时，新失败不改 cause；不同源 cause 会扩大原 D-M evidence。必须断言这些“不变状态但 evidence 改变”的场景。
- 空白-only pip 与 PEP621 空白不同：前者原来跳过，后者原来确实解析且失败。本片不能为统一风格更改任一合同。
- YAML 依赖序号作为 line 是既有限制，不能顺带改成物理行。YAML aliases/merge/duplicate-key decoder 行为、重度 recursive input、Conda grammar/manager semantics 都不在本片修复范围。
- 若未来测试用 pip marker containing `#` 或 malformed inline-comment，需要首先独立确认是现有成功还是捕获失败；不以“看起来是注释”代替真实 parse boundary。不能把 D-C graph-only 回退迁入这里。
- basename 双存在时，`_project_manifests[path]` 被设为空 frozenset；新的 parse issue 不应改变这一特殊 association logic。
- 外部 symlink 是原 safe-read None/unreadable，不是“无逻辑读”；Read spy 应区分逻辑 read_text 调用和物理外部内容读取，避免重犯上一轮 alias 预期错误。
- 本轮只读审阅未执行真实字符串分类。已复核独立 portfolio 来源审计及五份完整清单 hash：五 pins 共 17,724 tracked、17,675 static candidates，精确 environment basename、Conda lock、pip strings 均 0，实际 YAML/Requirement 调用均 0。因此仅预期此五固定输入无新触发/零差异；零适用输入不证明未来政策门通过，不由上一 D-M-P 的 163 PEP621 字符串类推。

## 精确规范连接点（基于当前行号，不是已应用补丁）

新 §12.3.10 应仅复用既有 vocabulary，写清实际 str/nonempty/strip/caught-failure、原 cause 优先、序号与原诊断、读轨迹、Conda/其他 caller 排除、部分提取、信用优先序及全仓/退出/输出成本。

需要扩展终点至 §12.3.10 的总括 forward refs：919、946、986、988、1046、1067、1200、1269。
需要给现有 D-M cause/consumption 连接新增 section：1165（含 7/9/10），1277（unparsed_requirement 来源是 9 和 10），1353（remaining readable grammar outside 9/10），1491（D-M 包含 7/9/10），1539（manager value grammar outside 9/10）。
1558–1559 必须明确 §12.3.9 仅 PEP621，requirements caller 仍不 opt in，而 embedded-pip 仅按新 §12.3.10 的独立合同 opt in；1602–1603 的本片 exclusion 不能被误读成全局永久排除，可指明 environment strings covered separately by 12.3.10。
§12.3.7 的 1374 表格及 1428–1432 “string grammar not checked here”可保持：它声明的是结构 slice 自身范围，不应把新字符串规则伪装成结构检查。§12.2 的 Python/Conda exact grammar不改。


## 具体补丁只读审阅结果

已审阅 publication/spec-proposed.patch 和 spec-after-proposed.md。逐字重建统一 diff 与 supplied patch 完全相等；原 normative spec hash 未变。补丁保留全部列出的 forward refs、§12.3.9 独立范围和 §12.3.10 的现有 call/nonblank/strip/False/setdefault 边界；明确 pip 支持但 extractor 不接受不等于非法语法；partial/信用/优先级/全仓成本/退出/输出/历史边界齐全。未发现须阻塞的政策或 frozen-decision 矛盾。A 和 B 均 accepted=false；此意见是推荐与提案审阅，不构成维护者批准。
