# D-C：独立验收设计

状态：**PROPOSED / FUTURE_EXPECTATIONS_NOT_EXECUTED**。本页定义候选 A 的未来验收，
不声称已接受或运行新政策。候选 B 保留当前完整行为。与
[兼容性说明](compatibility.md)一起审阅；先冻结输入和独立预期，再记录当前产品观察。

## 候选 A 的精确边界

1. 仅影响 `_RequirementsGraph` 已捕获正文中的 ordinary requirement 分支。
   空行、整行注释、include、以 `-` 开头的 directive，以及原有完整行含字面 ` @ ` 的分支先按旧顺序分类。
   不先删除注释再重新分类，不修改其他 manager 使用的共享 requirement parser。
2. 对一个 captured file，若 `text.splitlines()` 的任意物理行经 `rstrip()` 后以反斜线结束，
   此文件全部禁用新增 comment 支持。该检查包含整行注释和指令，且不因出现位置或反斜线数量改变。
   这是本提案的保守限制，不是 pip 续行兼容性声明；不拼接行，不展开环境变量。
3. ordinary 分支先按现有 `Requirement` 解析完整原行；成功时原样保留该解析结果，
   不尝试 comment 前缀，不重新解释原本有效的 marker 或 URL。仅完整原行解析失败且没有文件 veto 时，
   寻找第一处 ASCII space/tab 序列紧接 `#` 的位置，即 `[ \t]+#`，只尝试其前缀一次。
   前缀须由现有 `Requirement` 成功解析，且解析结果 `url is None`，才按该前缀捕获声明。
   继续使用现有 canonical name、specifier、exact-version 和物理行号合同。
4. 原行失败后，若无候选分隔符、前缀解析失败、前缀为 URL，或命中文件 veto，
   保留原完整行的既有失败处理和诊断。不丢弃它，不试第二个 `#`，不新增 body issue。
5. 不增加文件读取、候选探测、include edges、深度预算或节点；不修改 D-G frontier 的定义。
   新增声明仍可能改变既有 closure 的 package set、completeness 和 requirements-as-lock 资格。

以下“原行”指既有 parser 对物理行做 `strip()` 后使用的完整文本；fallback 的诊断必须保留该文本，
而不是失败候选前缀。新声明的位置仍为该物理行，不是逻辑续行位置。

## 核心输入与独立预期

所有 case 都比较完整 `DependencyDeclaration` 列表及顺序、manifest presence、lock inventories、
qualified credit、project roots/barriers、body issues、D-G tuple、diagnostics、reader/candidate traces。
有图的 case 另比较每个 root 的 closure sources、declarations、complete、is_exact。
下表没有显式改变的字段保持旧合同；不是仅比较数量。

| ID | 输入或对照 | 候选 A 的独立预期 |
|---|---|---|
| C01 | `torch==2.5.1 # pin`，无其他特殊行 | 新捕获 torch、`==2.5.1`、exact `2.5.1`、原物理行号；删除且仅删除该行旧 unparsed；单独完整 root 可满足 requirements-as-lock |
| C02 | `torch>=2 # note`、`torch # note` | 分别捕获 loose 与 unversioned；不因删除注释授予 exact 或 requirements lock |
| C03 | 单空格、多空格、tab、混合 space/tab 后 `#`；尾部多个 `#` | 都只取第一个候选前缀；注释后缀不成为声明或 include |
| C04 | `torch==2.5.1#note`、仅非 ASCII 空白后 `#` | 不触发新增分支；完整原行仍按旧 parser 处理，不能无条件改判为 invalid 或 valid |
| C05 | blank、纯空白、整行 `#`、前导空白后的整行注释 | 原跳过行为；空 root 不成为 requirements lock，不创造包使用 |
| C06 | 额外缩进、extras、合法 marker、规范允许的 local/pre/post/epoch exact；range、wildcard、`===` 对照 | 仅去掉受支持尾注释，保持各自既有 exact 语义；不求解 marker 或安装环境 |
| C07 | 第一个 `[ \t]+#` 出现在带引号 marker 字符串内部，例如 `torch==2.5.1; os_name == 'posix # note'`；另附真实尾注释使完整行失败 | 旧完整行可解析时直接保留其声明和 exact，不尝试截断；仅原行失败时尝试第一个前缀，前缀失败则保留完整原行诊断，不试后面的注释位置 |
| C08 | 非法前缀 `not a requirement !!! # note`、多个疑似分隔符；空前缀的整行注释对照 | ordinary 原行与前缀都失败时保留原诊断文本和顺序，不添加截断前缀诊断，不以 grammar error 伪造 body issue；空前缀对照早已按整行注释跳过，不进入此分支 |
| C09 | `-r child.txt # note`、`--requirement child.txt # note`、quoted/attached include | include 原分支和 error 保持；不新增 normalized target、读取或 D-G frontier |
| C10 | `--index-url ... # note`、`-c constraints.txt # note`、`-e . # note`、其他 directive | 原分支保持；不读取 constraints，不运行包管理器，不把未知选项统一 SKIP |
| C11 | 原行含字面 ` @ `，包括 `torch==2 # mention @ place` | 在尝试截断前即按原分支处理；即使 ` @ ` 只出现在看似注释的后缀，也不借本片改变 route |
| C12 | 不含字面 ` @ ` 的 direct-reference 变体，如 tab 分隔 `@` 或紧邻 `@`，其注释前缀可解析且有 URL | 新候选因 `url is not None` 被拒绝，随后完整原行 fallback；不能仅因 prefix 可解析就新增 URL 来源、use 或信用 |
| C13 | 原本成功解析的完整 URL 行、URL fragment、bare VCS、带 URL/path 形式的旧对照 | ordinary 完整原行成功时直接保留，不尝试 comment prefix；旧失败且前缀为 URL 的对照仍失败。不把 `req.url is None` 限制下沉到共享 parser 或原有完整行分支；不联网 |
| C14 | 文件任意行 `rstrip()` 后以 `\` 结束；该行在目标 comment 行之前或之后 | 整文件所有 comment 候选都维持旧行为；先前无注释声明不撤销，不能只检查当前行或只向后 veto |
| C15 | 结束反斜线后有空格/tab；连续多个反斜线；整行注释或 directive 结束于反斜线；CRLF/LF | 均按明确定义触发文件 veto；不同换行形式保留物理行号。不得根据“看起来只是注释”绕过 veto |
| C16 | backslash 出现在行中间，或其后还有非空白内容 | 不因这一点触发文件 veto；是否捕获由 ordinary branch 和候选解析决定 |
| C17 | root 命中文件 veto、被正常 include 的 child 没有；反向再做一例 | veto 只属于各自 captured file，不传播成全图禁用；不提前读取尚未捕获的 child |
| C18 | 多个 root、共享 child、重复引用、物理行同包重复及 canonical alias | 既有 traversal、去重和声明顺序保持；只在原位置加入新声明，不重复 reader；first evidence 可以因新加入的更早声明而改变，须预写精确位置 |
| C19 | 完整 exact child、loose child、仍有其他 unsupported 行、cycle、depth frontier | comment exact 可修复其自身 grammar 缺口，但不消除其他 closure 缺口；cycle/depth/不可读和非 exact 仍按原合同阻止相应 requirements lock |
| C20 | 早前 depth target 被后续 shallow root 捕获，且目标正文含候选 comment | 继承 D-G final-node 语义；不因新声明重排 roots 或新增读取；新信用与最终 frontier 各自独立计算 |
| C21 | 相同字符串置于 PEP 621、Poetry/Pipfile 值或 environment 的 pip 列表 | 其他 manager 解析和其既有诊断完全不变；不复用普通 requirements 文件的 comment 预处理 |

## 规则、CLI 与生成物

每个 audit 预期必须是事先写出的完整 `AuditReport`：metadata/input hash、profiles、summary、
全 finding 的 evidence/hint/origin/suppression 字段。只允许规范列明的时间字段归一。
隔离 profile 用于证明指定 rule 的 exit 变化，随后再测与其他 finding 的组合。

| ID | 输入或对照 | 候选 A 的独立预期 |
|---|---|---|
| C22 | 已捕获 `torch>=2`，另有 `torch==2.5.1 # pin` | 新 exact 信用移除原缺 pin finding；完整 Python 视图下可由既有 engine 合成 rule PASS。隔离 WARNING/warning 或 promoted CRITICAL/critical 门可由 1→0 |
| C23 | 只有 `torch>=2 # note`，没有 import/其他 use | 新声明建立真实 captured use；原 applicability SKIP 可变 FAIL/WARNING。隔离 warning 门可由 0→1；FAIL-only override 的 CRITICAL 门也须验证 |
| C24 | 只有 `torch==2.5.1 # pin`，没有 import | 由无已知 use 的 applicability SKIP 变为有 use/有信用；完整 Python 视图下为 rule PASS，不把它描述成“新 SKIP” |
| C25 | exact-only comment root，无其他 lock；另做 loose-only 和含其他坏行对照 | `env.lockfile_present` 可由 WARNING→PASS，新增 requirements lock 的 package set 必须精确；loose/残余坏行不能获得该资格，manifest presence 规则保持 |
| C26 | 根、无关子项目、冲突 exact 及 qualified format-lock 信用与 comment 新声明共存 | 既有正信用保留；新 exact 按现有全仓 existential 合同生效。单独 requirements 声明不建立新的 format-lock 项目配对或 ownership；无 import/配对 manifest origin 的库存仍不得授予 format-lock 信用 |
| C27 | D-F/D-S、D-L、D-M/D-M-S、D-G 分别与新增 exact/loose use 共存 | 新 exact 或既有 qualified 信用仍先于不确定性；剩余包仍按 D-F/D-S→D-L→D-M→D-G 顺序；旧完整原因不得混入 comment 文案。新增 loose use 可能新增该原因的 SKIP，但不是通用 grammar-SKIP |
| C28 | 完整/有缺口/不可用/不一致 Python coverage；全包已有信用或无 use | 既有 applicability 和 empty-result veto 不改；新增 exact 导致 check 返回空时，不能绕过 Python veto 擅自 PASS，不创造每包 PASS |
| C29 | 一条新的 `vllm>=0.3 # note` 或 `peft>=0.1 # note`；新声明早于已有同包来源；已有 high import 对照 | 现有依赖 signal 可新增 medium profile 或改变代表 evidence；保留 high-confidence 优先规则。比较全部 profiles、confidence、evidence、hints，不能只比 profile 名称 |
| C30 | C29 做 `init`，分别默认 profile 选择和显式 override，再 L1 audit/default export | medium shipped profile 按原初始化合同进入默认选择，可能新增 required-field scaffold 和后续 finding。比较完整 manifest、config、project-rules、输出及 L1；显式 override 仍按其原合同，不自动代用户选环境 |
| C31 | C22/C23 分别与独立 WARNING/CRITICAL 共存，fail-on never/critical/warning 矩阵 | 按完整结果计算 exit；不能因一个包获信用而掩盖其他 finding，不能声称所有 CLI 都 1→0 |
| C32 | ignore/suppression、默认 text、show-skipped/show-passed、默认 export | 新 FAIL、PASS、SKIP 经原呈现/忽略规则处理；SUPPRESSED/INFO 保留原始严重度证据和 reason。export 可显露新增 WARNING，也可隐藏因信用消失的 WARNING；不改 renderer |
| C33 | 前缀从 exact 改 loose、恢复原注释、加入/移除任意结束反斜线行，随后 fresh scan | 各次根据实际输入重算，恢复相应信用/警告/lock/use；不留旧 comment 处理缓存或陈旧 closure |
| C34 | 重复 JSON/default export、普通与 verbose diagnostics、同输入不同路径副本、旧 audit JSON | 确定性与 schema 兼容；不新增持久化字段、不改历史报告、无绝对路径/凭据泄漏；默认与 verbose 的既有可见性边界保持 |
| C35 | 五个固定项目：L0、完整 facts/diagnostics、fresh init、L1、default export | 按下述独立来源差异验收；HarmBench 不得套用 D-G 零 facts delta，其余项目也须逐项证明，不只看 summary |

## 五项目来源与预写差异

原始参考是 D-G 的[固定来源记录](../requirements-depth/portfolio-source-evidence.json)
和[影响说明](../requirements-depth/portfolio-impact.md)。这些记录属于准备时输入证据，
不是 D-C 的新执行；本轮须核对固定 pins/origins、全部相应原文件字节和无结束反斜线行，
再冻结 D-C 预期。尤其不能把旧 depth-only 的零差异结论转用到 comment 支持。

| 项目 | 原始相关来源 | D-C 候选 A 的预期 |
|---|---|---|
| lm-evaluation-harness | `lm_eval/tasks/japanese_leaderboard/requirements.txt`，4 条普通依赖 | 无新候选，全部结果预期不变 |
| FastChat | 已登记来源没有 requirements 文件；pyproject 保持原解析 | 全部结果预期不变 |
| LlamaFactory | `docs/requirements.txt`，3 条普通依赖 | 无新候选，全部结果预期不变 |
| HarmBench | root requirements 18/19；另有 alignment-handbook requirements | 下列两条声明与两条诊断发生精确差异；其余字段按独立来源逐项核对 |
| llm-dp-finetune | root requirements 第4行 bare VCS，第5/6行整行注释 | 都不是本片新候选；不得意外接受 VCS，全部结果预期不变 |

HarmBench 固定 pin 为 `8e1604d1171fe8a48d8febecd22f600e462bdcdd`。
root `requirements.txt` 原始 SHA-256 为
`a342b21c680e1d3102953f7937c97db58f095791f311953465148a87f25f5e9d`。
独立原行是 `art  # for ArtPrompt`（18）和 `tenacity  # for ArtPrompt`（19）。

新增完整声明，在原物理位置及既有 traversal 顺序中插入：

```json
[
  {"name":"art","display_name":"art","specifier":null,"exact_version":null,"source_file":"requirements.txt","line":18},
  {"name":"tenacity","display_name":"tenacity","specifier":null,"exact_version":null,"source_file":"requirements.txt","line":19}
]
```

移除且仅移除相应原诊断：

```text
requirements.txt:18: art  # for ArtPrompt
requirements.txt:19: tenacity  # for ArtPrompt
```

root 的其余行都是现有普通声明，故在来源核验成立时，该 root 的 grammar closure
`complete` 从 false→true，package set 增加 art、tenacity；但已有 range/unversioned 条目仍在，
`is_exact` 仍 false，不新增 root requirements lock。嵌套 exact 信用和既有 format-lock
关联不变；body issue、D-G frontier、manifest presence、读取和候选集合不变。
这两包不在 shipped profile dependency signals 或 critical-package 集合，故不新增 critical finding、
profile 或 init 字段；完整 L0/L1 finding、hints、init 文件及 default export 预期不变，
而 verbose/audit 诊断和事实包必须体现上述删除/新增。此处是来源推导预期，仍须完整比较。

候选 B 的这些输入、输出和原诊断全部保持当前字节。若实际发现上述以外差异，先解释并审阅独立依据，
不能复制新产品输出改 gold。P-A 不执行未来政策；P-B 需要具体批准、先 RED 后 GREEN、
最终质量门与新鲜五项目 Gate A。资源 Gate B、真实采用、付费 API 与发布不由本片激活。
