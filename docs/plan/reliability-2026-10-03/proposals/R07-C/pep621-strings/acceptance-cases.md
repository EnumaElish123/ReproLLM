# D-M-P：独立验收预期（未来 P-B，尚未执行）

状态：**PROPOSED / NOT_IMPLEMENTED**。本页基于 `cc6e891` 的既有 §12.2、
§12.3.6–§12.3.8 设计候选 A 的未来验收；不是本次 pytest、RED/GREEN 或产品门的通过记录。
候选 B 保持当前合同。具体兼容成本见[兼容性说明](compatibility.md)。

## 输入和断言边界

候选 A 只在现有 `_parse_pyproject` 已经实际送入 `_add_requirement_line` 的
`project.dependencies`、`project.optional-dependencies` **字符串**遇到现有
`Requirement` 解析失败时，为该源增加内部 `unparsed_requirement` 原因。
不改变原解析器的接受集合、传入字节、成功声明、原 `unparsed` 或读取轨迹；已有正文／解码／
结构原因优先，不被新原因覆盖。空串和空白字符串按同一实际解析失败路径处理。
不得通过新增一次解析、预扫描其他成员或对失败内容做修复来制造这个事实。

除逐行另述，基准 fixture 为 `z.py` 中 `import torch`、完整 Python 采集、没有 exact、
格式 lock 或其他失败；安装版本查询固定为空，使完整预期不依赖本机包。
W = `env.llm_critical_deps_pinned` 的 FAIL/WARNING；S = 沿现有 D-M 的 SKIPPED/INFO。
隔离用例只启用待测规则，混合用例明确加入独立规则，不能用其他 FAIL 遮蔽退出码变化。

“原样保留”要求完整声明字段及次序、物理行号、manifest 资格、项目根／barrier、lock
包及关联、诊断字节、scanner 调用序列逐项一致；不以数量相同代替。
预期必须在实现前写成独立字面值，禁止从候选实际输出生成 gold。

## Core 与完整性边界

| ID | 输入／分别参数化的维度 | 候选 A 独立预期 |
|---|---|---|
| P01 | 合法 project，`dependencies = ["torch=="]` | 现有解析实际失败；仅新增 `{path: "unparsed_requirement"}`；无失败条目的 declaration；原 unparsed 保留，W→S |
| P02 | 每个 optional group 中放同一失败字符串；错误在首／中／末组 | 同一文件级原因，所有已成功兄弟及次序／位置保留；不新增组名合法性检查 |
| P03 | 两种列表分别含 `""`、空格、tab、换行空白字符串 | 仅按现有调用实际解析失败记录；不预先忽略空白，也不声称整个 TOML 文档解码失败 |
| P04 | 字符串 `"torch=="`、`"not a requirement"`、看似名为 torch 的其他失败片段 | 不从失败内容猜包名、specifier、exact 或 profile signal；只有已捕获 use 才能消费 D-M |
| P05 | `dependencies` 缺失、`[]`；optional 缺失、`{}`、空 group 列表 | 无新原因；保留 W 或其他既有结果；没有内容不是解析失败 |
| P06 | 所有条目均被现有 Requirement 接受：unversioned、range、exact、extras、合法 marker、合法 direct reference | 完整结果不变；不新增 comment 回退、marker 求值、URL 或版本政策；合法不等于 exact |
| P07 | deps 与 optional 各含合法 loose／exact 及失败字符串，失败位置前／中／后 | 部分声明全保留；同包 exact 原信用仍优先；失败条目不清空整个列表或文档 |
| P08 | 同一文件多个失败字符串，重复相同条目，跨 deps／多个 optional group | 单一文件级新原因；每条原诊断／顺序保留；不新增重复诊断或失败条目恢复 |
| P09 | 两个失败 pyproject、一个合法 pyproject，路径顺序与发现顺序不同 | 原发现／声明顺序保持，失败字典按原模型存储；规则 evidence 按既有路径排序稳定列出失败源 |
| P10 | 同一 pyproject 已有 D-M-S `invalid_structure`，仍有实际被解析的失败 str | 保留 `invalid_structure`，不覆盖为新原因；其余成功提取及既有 qualification/barrier 不变 |
| P11 | read 返回 None 或 TOML decoder 失败 | 保留 `unreadable`／`invalid_syntax` 及现有 early return；不为不存在的 str 调用产生新原因 |
| P12 | 非 str 成员、错误列表／组容器、错误 project/tool/poetry 类型 | 仅沿已批准 D-M-S 处理；不得将类型错误改名为 `unparsed_requirement`，或额外遍历原来未解析的成员 |
| P13 | build-system、dependency-groups、Poetry group、tool-only 配置及未读取候选含失败文本 | 本片不扩展来源；不新增原因、读取、use 或 manifest 资格 |
| P14 | Poetry／Pipfile 单包值，Conda 字符串、environment.pip 中的坏字符串 | 全部保持现合同；共享 helper 不能把 PEP 621 限制泄漏到其他调用者 |
| P15 | requirements ordinary／D-C 注释回退／unsupported directive／include／D-G frontier | 完整图、读次数、诊断、closure、requirements-as-lock、现有失败原因不变；不借机增加通用 grammar issue |
| P16 | 同一输入重复采集；先修复失败 str 为合法 exact，再改成合法 loose／删除该失败条目 | 重复采集确定；新采集不残留旧原因；exact 恢复信用，合法 loose／删除后按剩余真实输入恢复 W |
| P17 | 手工构造无新原因的既有 Declarations；有效同目录 uv/poetry lock 配对，外部路径／内部别名控制 | 默认空字典与旧对象行为保持；新原因不添加 uncertain directory、ownership barrier、额外读或物理身份 |

## 规则消费、信用及优先级

| ID | 输入／分别参数化的维度 | 候选 A 独立预期 |
|---|---|---|
| P18 | 失败源同包另有 exact；同文件／其他 group／无关子项目 exact；冲突 exact | 仓库级 existential exact 保留；不产生该包 missing-pin finding，不新增 per-package PASS 或 conflict finding |
| P19 | 合格格式 lock 对该包提供信用，且 pyproject 的另一条 str 失败 | qualified credit 保留；失败不撤销 manifest 资格／同目录关联或已捕获包集合 |
| P20 | 新失败源与 D-F／D-S 的关联坏 lock 共存 | D-F／D-S 的原 finding 全字段优先，不能追加或替换成低优先级 D-M reason/evidence |
| P21 | 新失败源与满足 D-L 的 Python gap＋格式 lock 包集合共存 | D-L 原 finding 优先；完整 message、hint、evidence 保持；不因 D-M-P 改名 |
| P22 | 新失败源与其他 D-M 失败源及 D-G frontier 共存 | 使用现有单个 D-M S；先原 use evidence，再按路径列全部 declaration issue 源；不追加 D-G finding／target evidence |
| P23 | 有 `unrelated/pyproject.toml` 失败字符串，另一项目有 torch、numpy 两个 uncredited use | 两包 W→S；与失败文件是否像同一项目无关，不套用格式 lock ownership；这是明确保守的全仓成本 |
| P24 | exact 包、D-F/S 包、D-L 包、D-M-P 影响包同时存在 | 逐包保留各自已赢分支；不能整条规则 short-circuit，不能压制仍应输出的其他 finding |
| P25 | Python coverage 完整／gap／内部不可用，新失败源均被实际捕获 | 本片 D-M 路径独立于 Python coverage；其余 applicability／空结果 veto 仍按现有合同 |
| P26 | 只有失败字符串且无已捕获关键包；或只有非 critical 成功声明 | 仍是原 no-critical-use applicability SKIP；不猜 use、不凭内部原因新增 aggregate finding |
| P27 | 所有已捕获关键包均获信用，另有失败字符串；分别完整／不完整 Python | 无额外 D-M-P finding；保留既有空结果 PASS／primary-Python veto 条件，不能一律写成 PASS |
| P28 | 已存在 D-M 原因的文件增减失败 str；新路径导致 D-M 证据集合扩大 | 只按实际新源改变完整 evidence，原状态相同也须解释 evidence delta；原文件原因优先级不变 |

优先顺序不变：**已有 qualified／exact 信用 → D-F/D-S → D-L → D-M（含本片）→ D-G → 原缺 pin WARNING**。
本片不新增规则分支或独立 finding 文案。

## 公共 CLI、初始化、导出与历史

| ID | 输入／分别参数化的维度 | 候选 A 独立预期 |
|---|---|---|
| P29 | 隔离 pin rule，默认 warning 阈值、以及 FAIL severity override 为 CRITICAL 后的 critical 阈值 | 当前 W／CRITICAL exit 1，候选 S/INFO exit 0；FAIL-only override 不提升 S；分别预写两份完整 AuditReport、summary、stderr、退出值 |
| P30 | 同 P29 加独立 `env.python_version_declared` WARNING，使用 warning 阈值 | pin 仍 W→S，但独立 warning 原样保留，exit 仍 1；不能把相同 exit 写成零差异 |
| P31 | `--fail-on never`、ignore/suppression、规则别名及显式 severity override | 门槛合同保持；ignore 按现有流程把 finding 转为 suppressed/INFO，附原 severity 为 INFO 的配置 evidence，保留完整 D-M 原证据及 reason；不修改 renderer/engine |
| P32 | 同输入默认 text、`--show-skipped`、`--show-passed`、完整 JSON、verbose diagnostics | JSON 保留 S；默认 text 不显示 skipped 明细但计数反映 skipped，并可显示既有 Findings: PASS；show-skipped 显示原 D-M message；原解析诊断保留既有可见性（普通依赖解析诊断仅 verbose 显示；固定 coverage/run warning 特例不变） |
| P33 | fresh disposable clone 执行默认 init、显式 profile init、L1；无历史 run 的 default export | 声明/profile signals/初始化全部文件应不变；L1 可按本片变化 pin finding；export 移除旧 WARNING/CRITICAL notable 条目并更新原 summary，S 不作为新 notable 展示；完整文件比较，不只查包含词 |
| P34 | 原失败 str 不变且不含新 use；合法 profile signal 与失败 str 混合 | profile/hints、代表 evidence、默认 scaffold 原样；不能根据失败片段猜新 profile 或自动修复配置 |
| P35 | 同输入重复 audit/export，不同 disposable 路径；存在历史 audit/run/export 与 snapshots | 按 §22 T-02 仅豁免已列根时间／版本元数据，其他完整结构与字节比较；原路径敏感内容不入持久化；旧记录不重写、不重新解释为候选政策已通过 |

## 五项目与 P-B 实施后的门

| ID | 固定输入／验收范围 | 独立预期 |
|---|---|---|
| P36 | val.md 五个固定 pin 的全部已实际解析 PEP 621 字符串，按项目／source／字段路径绑定来源 | [独立来源盘点](portfolio-source-evidence.json)为 163 个有效字符串；须逐条核对原文、位置、当前 Requirement 成功及原始 hash；不能以总数替代来源清单 |
| P37 | 五项目 fresh L0/facts、完整 profiles/hints、disposable init 全部生成文件、L1/default export、受影响 verbose | 163 条均成功意味着本片无触发；预写完整零差异，分别与身份一致的独立 oracle 比较；不改五项目 gold，不把历史 D-C 的 HarmBench 非零变化算入本片 |
| P38 | 最终产品／测试输入冻结后一次完整质量门、五项目 Gate A、受影响扩展与原件最终身份核查 | 所有适用检查实际完成后才 PASS；资源不适用／阻塞分别标明，不移用旧候选 CI／资源成功；推送精确 HEAD 的五项 CI 另核 |

## 未来测试映射及当前状态

- Core：现有依赖采集测试模块承载 P01–P17；新增参数化失败 str 回归前先固定完整字面预期，
  RED 应证明缺少新内部事实，GREEN 仍核完整副作用边界。
- Rule：现有 env／dependency-scope 测试模块承载 P18–P28，逐包预写全 Finding，而非只看 status。
- Consumer：公共 audit／text／export／profile-init 测试承载 P29–P35；既有历史对象／文件留原 hash。
- 五项目：P36–P38 从固定源和独立预期出发，不允许用候选输出补写预期。

以上 ID 是**未来验收设计，不是已运行测试 ID、测试数或通过数**。
本 P-A 不添加或执行未来产品测试，不应用产品／规范补丁；仅核验现有行为和提案材料。
资源 Gate B 不因本地 P-A 或后续普通政策 P-B 自动激活；现有 BLOCKED 继续按资源账本登记。
