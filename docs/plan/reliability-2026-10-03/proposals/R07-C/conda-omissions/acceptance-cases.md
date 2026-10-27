# D-M-CE：P-B 未来验收设计

状态：**PROPOSED；以下所有组均为 NOT_EXECUTED**。这是具体策略接受后的验收要求，
不是 P-A 测试通过记录。不得将当前源码的 32 项 helper 观察或五项目零适用性写成新策略 PASS。
未来先建立会失败的 core／rule／CLI 回归，再实施最小补丁；比较完整记录和完整 finding，不能只比较数量。

本片只针对既有 `_add_conda_entry` 的两处提前返回：
`_CONDA_NAME_RE.fullmatch(entry.strip()) is None`，或已提取的 `rest` 以 `::`／`/` 开头。
建议只在这两处增加 `declaration_read_issues.setdefault(path, "unparsed_conda")`，
并为内部 `DeclarationReadIssue` 增加该字面量。未接受前不执行候选策略。

| ID | 层次／输入 | 独立预期（全部 NOT_EXECUTED） |
|---|---|---|
| CE-A01 | core：两处提前返回各至少一例 | 只增加文件级 `unparsed_conda`；仍不追加 declaration。原 `unparsed` 固定文案、顺序及调用次数不变，不回显输入字符串。 |
| CE-A02 | core：空字符串、空白字符串及首字符不能进入既有 name 匹配的字符串 | 仅因现有 native helper 实际访问并提前返回而触发；不预先过滤空字符串，不断言这些输入是否可被 Conda 安装。 |
| CE-A03 | core：channel 前缀、subdir／slash 前缀与外层空白 | 精确沿用 `strip`、fullmatch 和 startswith 的顺序；不解析 channel、提取隐藏包名或赋予信用。 |
| CE-A04 | core：YAML 解码后的内嵌换行、尾部换行与多行标量 | 内部换行导致现有 fullmatch 失败时才触发；仅尾部换行被现有 strip 去掉而保留声明时不触发。不改变原 list index，也不声称它是物理 YAML 行号。 |
| CE-A05 | core：YAML aliases 重复指向 native str／pip mapping，及嵌套容器 | 只执行现有 dependencies 列表和 pip 列表遍历，不新增 alias 展开／去重／递归。重复原访问保留重复诊断，每个逻辑文件最多一个 issue；非 str／dict 的既有结构错误保留。 |
| CE-A06 | core：普通包名、大小写／pytorch 规范化及前后空白 | 保留现有 canonical/display name、specifier、exact、source、line 和声明顺序。仅没提取声明的两处返回能够增加 CE。 |
| CE-A07 | core：数字 `==`、单 `=`、版本加字面 build | `==` 或数字版本加字面 build 保留既有 exact；单 `=` 无 build 仍是非精确前缀，不产生 CE。不引入 Python／Poetry 版本语义。 |
| CE-A08 | core：已保留的数字 range、通配／复合／其他 suffix | 即使旧 helper 增加 unsupported 诊断或 exact 为 None，也不能因此产生 CE。数字 range 原 specifier、其他原 placeholder 均保持。 |
| CE-A09 | core：带空白的 channel／slash、URL-looking、backslash、unicode suffix | 以现有两处返回为界；当前仍保留 head 的形式继续保留。不能凭看似复杂或不合法的语法扩大 CE。 |
| CE-A10 | core：未知 installer mapping、任意嵌套 mapping／list | 不搜索其中字符串。未知 mapping 保持忽略；原结构错误继续使用既有 invalid_structure，不将所有未知 installer 认作 CE。 |
| CE-A11 | core：embedded pip 合法 exact／range、空串／空白串 | 继续调用现有 Python Requirement helper 或现有空串跳过；不增加 unparsed_conda。保持 pip declaration 和信用。 |
| CE-A12 | core：embedded pip 中 channel-looking 或其他不可解析的 requirement | 保留既有 unparsed_requirement 及诊断；不把 Python requirement 失败更名为 native Conda 失败。 |
| CE-A13 | core：native omission 与 malformed pip／非字符串 sibling，改变物理先后顺序 | 现有结构 precheck 在整个循环前完成；即使结构错误在文本较后位置，已有 invalid_structure 也必须被 setdefault 保留。保留部分有效 sibling。 |
| CE-A14 | core：失效 pip requirement 在 native omission 前／后 | 已有 setdefault 原因优先：先 pip 时保持 unparsed_requirement；先 CE 时保留 unparsed_conda。每路径一个原因，不额外预扫描 CE。 |
| CE-A15 | core：已有 unreadable／invalid_syntax 或未进入 entry 循环 | 保留既有原因和 return，不重读／重试、不从诊断推断 CE；无候选内容读取就无新事实。 |
| CE-A16 | core：缺 dependencies、null／空文档、显式空列表 | 无实际 native helper 访问就无 CE；保留当前 manifest presence、project qualification 和空结构兼容边界，不声称完整。 |
| CE-A17 | core：root／nested、两个扩展名及同目录双 environment 文件 | 维持原 candidates、根文件优先、路径排序和双文件歧义处理；每个实际访问文件独立记录原因，不新增读取或候选。 |
| CE-A18 | core：多次 omitted entry、多个 distinct failure source | 保留原全部诊断／声明；每文件一个 issue。后续 D-M evidence 按逻辑路径排序，不能重复同一文件。 |
| CE-A19 | rule：仅 omitted 的 critical-looking 字符串，没有其他声明／import | 保持原 in-use 集合为空、applies=false 及当前 no-use 结果；不能从遗漏原文制造包名或逐包 finding。 |
| CE-A20 | rule：无关子项目的非关键 native omission，另有 torch／transformers 等实际用例 | 现行全仓 D-M 会把每个剩余已使用、无信用 critical 包由 WARNING 改为 SKIPPED/INFO。明确这是保守策略成本，不是隐藏 exact 的证明。 |
| CE-A21 | rule：同文件有效 exact sibling、或其他管理器／子项目的已采集 exact | 现行仓库级 existential exact 信用优先；保留所有部分有效声明，不新增逐包 PASS。CE 不授予任何信用。 |
| CE-A22 | rule：合格 conda-lock 的现有 declaration／import origin | 原 qualified lock 信用优先。被省略 native 字符串不创建 origin、不使包 membership 自动合格；保留可用 sibling／import 的原关联。 |
| CE-A23 | core／rule：不合格、未配对、错误目录／格式／双 environment 歧义的 lock | 保留 package sets、关联与不授信结果。新 CE 不改变 nearest-project 边界，也不新增 uncertain-directory barrier。 |
| CE-A24 | core／rule：父 lock 与含 CE 的子 environment | 区分原已存在 project root 与 uncertain barrier，分别比较；entry 事实不增加 barrier。其他所有原项目隔离与关联结果保持。 |
| CE-A25 | rule：有关联的 format-lock D-F／D-S 失败，同时有 CE | 原 D-F／D-S finding 完整优先，message／hint／evidence／顺序不变，不追加较低优先级 CE 路径。exact／qualified 信用仍先于两者。 |
| CE-A26 | rule：Python gap／unavailable、possible lock membership 与 CE | 原 D-L finding 完整优先，不追加 CE 路径；无 D-L 条件时，D-M 不依赖 Python coverage。 |
| CE-A27 | rule：requirements D-G depth frontier 与 CE | D-M 先于 D-G；使用原 D-M 文案／hint 及自身 failure 路径，不把较低优先级 D-G target 加入 evidence。 |
| CE-A28 | rule：原本已被其他声明失败 D-M 跳过，再增加 CE source | status 可以保持 SKIPPED，但 sorted file evidence 增加新路径；逐项比较完整 finding，保留第一 declaration，否则第一 import evidence。 |
| CE-A29 | rule：完整／有缺口／不可用 Python coverage 与已存在正向信用 | 不改变 empty-result primary-Python veto、不合成已遗漏包 finding。SKIP 不证明分析完整、没有 pin 或环境可复现。 |
| CE-A30 | core／rule：完整内部记录不变量 | 除允许的新 issue 外，declarations 全字段／顺序、lock 集合／来源／issue、presence、project roots／barriers、graph、unparsed、read／native helper／Requirement traces 完全相同。 |
| CE-A31 | CLI：default text、完整 JSON、default export 与 skipped 展示 | 完整 JSON 保留 SKIP；默认文本可能显示 Findings PASS 和 skipped 数，默认 export 可失去原 notable warning。沿用 renderer／exporter，不为此改引擎或 schema。 |
| CE-A32 | CLI：warning threshold、提升 CRITICAL、suppression、独立其他 finding | FAIL-only override 不提升 SKIP；孤立 WARNING／提升 CRITICAL 可使退出 1→0；独立达阈值 finding 仍退出 1。suppression／threshold 及 exit 2／3 合同不变。 |
| CE-A33 | consumers：profile detection、hints、init 与已采集 inventory | 保持已采集包、profiles、hints、生成 manifest 全文；不得从被省略原文补推包名。受影响 audit 命令按新规则预期比较全文。 |
| CE-A34 | compatibility：legacy/manual defaults、重复输入、隐私 canary | 字典默认仍每实例独立且为空；确定性不变，不新增 raw value／绝对路径／主机名／用户名／secret，不重解释历史产物。 |
| CE-A35 | session：五项目源码清单及最终质量门 | 先独立盘点实际 native environment 项再作条件影响预测；零适用性不等于触发验收。接受后按验证流程执行 RED→GREEN、一次最终完整质量门、fresh 五项目 Gate A 和受影响扩展。 |
| CE-A36 | scope：禁区及未完成工作 | 无 engine／scanner／redaction／persisted schema／dependency／package version／gold 改动；无新 grammar／solver／manager／网络／资源调用。广义 R07-C 继续 OPEN，P-A 门的文稿例外必须明确 NOT_APPLICABLE 并说明。 |

32 项当前 helper 观察仅验证既有源码，覆盖 12 个提前返回和 20 个保留声明控制。
本表中的未来政策 full-parser、规则、CLI、consumer 和质量门均未执行。
另有 36 个现行 full-parser/raw-rule 观察及独立回读，详见 current-behavior.md；
它们不从当前行为推导候选政策已通过。
