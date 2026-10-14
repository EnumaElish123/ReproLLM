# R04-S / S3-B 验证计划

**状态：PROPOSED；以下计划全部 NOT_RUN。** 本文不批准 schema、规则语义或版本发布，不将计划写成 PASS。当前旧读者的17叶实际观察仅引用[既有兼容证据](compatibility-observed.json)，不重复执行，也不冒充未来 bridge/minor 的验收。

依据：[S3任务卡 §§4–5](../../03_Scan_and_Runtime_Evidence.md)、[执行总则](../../00_Execution_Guide.md)、[验证频率](../../../validation-workflow-2026-10-13.md)、[规范 §§5/15/17/19/22/23](../../../01_specification.md)、[val.md](../../../../../val.md)及[兼容性方案](compatibility.md)。分析基线为 `52ecc504b3795c46220f68ef24728e0666638df0`。

## 1. 冻结输入与一次最终质量门

R04-A/0.6.2 bridge及R04-B/0.7.0 minor按各自任务先真实 RED→GREEN，跑受影响lint/type/security。D-41要求具体schema/engine/redaction patch、测试及消费端影响清单经过明确维护者审阅；D-39 minor、run-local版本与迁移说明先决定，才写新格式。任务总体启动不替代这些决定。

最终产品、测试、schema、生成器、相关配置和工具冻结后，运行**本轮一次全新完整质量门**，之后才执行本轮fresh Gate A。旧VAL-R01的2,527 tests/174 security、旧QA日志或旧产品run均不能填成本轮结果。最终源码或这些输入再改变，相关收尾证据失效；纯报告补充无需产品重跑。

质量门包含：pytest整体覆盖≥85%、redaction语句/分支100%、security、Ruff/format、strict mypy、生成rules/profiles/CLI/quickstart freshness及全部十JSON Schema的集合/字节比较。检查coverage后再运行可能改变coverage数据的测试。普通CI仍排除slow；nightly独立保留原预算，不用coverage墙钟预算替代其合同。

先核对锁定Python/uv/Git、依赖及模块来源。Git2.25.1不支持quickstart的`init -b`，只使用已审定兼容器原字节（SHA `87a9309323f9e82d8721b7bd58cac0c1a8f08e44a4348fbf6d476854aa19b298`）或真正支持的Git；先让quickstart freshness成功，再启动完整pytest。bridge/minor刷新本地根包元数据后核对CLI、源码版本、distribution metadata及wheel METADATA；不借此升级第三方依赖。

只run_record的已批准Schema变化可进入新格式；其余九个导出Schema须fresh逐byte不变。State不在十个导出文件内，但typed context仍需序列化测试。共享manifest.SchemaVersion仍为1；不以放宽共享别名实现run2。

## 2. 最小fresh五项目矩阵：65 core product leaves

在全部五个val.md固定pin执行。基础层在原干净checkout只读；mutating扩展在本轮新owned disposable clones。每项目开始/结束均核验准确SHA、公开origin、tracked/untracked完整干净状态；不修改正式checkout、用户并行文稿、原始gold或旧run。

| pin项目 | 固定HEAD |
|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` |

每pin13个fresh product leaves，共65；helper比较、Git/venv/输入准备、source-context观测和兼容probe另计，不混入这个数。表中的A/B ID只由本次实际run生成，绝不替换成历史run ID。

| #/pin | 命令/消费者 | 完整验收目标 |
|---|---|---|
| 1 | `audit . --level 0 --format json --fail-on never` | 完整L0 JSON、stdout/stderr、profiles/evidence、所有规则结果；root正式元数据豁免外不丢字段 |
| 2 | 轻量static facts collector | 完整hints、profiles、Python/analysis路径、imports、dependency declarations、framework evidence和诊断；一个AuditContext，不调用task inventory/init planning |
| 3 | `lock . --offline`（owned clone） | 本轮合成manifest的lock-time recorder事实和原输入哈希；无网络，未解析身份gap保留 |
| 4 | `run --name s3b-evidence --capture-output -- <owned-child-python> r04-child.py --temperature 0.1 --temperature 0.2` | A：有序CLI最后0.2、config基线0.1不改；独立child parser实际使用0.2；recorder与child主体区分 |
| 5 | `audit . --format json --fail-on never` | A：完整L2 findings/profiles/evidence，source/phase约束及全部冲突证据；未知child不被称为匹配 |
| 6 | `run --name s3b-evidence --capture-output -- <owned-child-python> r04-child.py --rewrite` | B：无temperature CLI，child先消费config0.1再写0.9；正确before基线、post变化与消费未验证合同 |
| 7 | `audit . --format json --fail-on never` | B：current工作树变化仍是真实文件一致性gap，不强求全部PASS；不把post0.9当实际运行参数 |
| 8 | `diff <A_ID> <B_ID> --format json --fail-on HIGH` | 有效温度0.2→0.1的HIGH，预期exit1；其余全部delta逐项独立预写，不仅断言一条leaf |
| 9 | `diff <B-run.json> <B-run.json> --format json --fail-on HIGH` | 完整self-diff为空、exit0；覆盖显式JSON读取入口，不能解读为child环境已验证 |
| 10 | `export . --run <A_ID> --output <owned-out>/A.md` | B已改current config时，历史A自身snapshot/CLI0.2仍有效；current audit scope明确 |
| 11 | `export . --run <B_ID> --output <owned-out>/B.md` | B保留baseline0.1、变化/未知说明、recorder/host事实和post outputs；不显示0.9为消费值 |
| 12 | `runs list --json` | 新run可读、有序筛选/元数据真实；未知版本warning/skip按具体合同，不把exit0当新格式被接受 |
| 13 | `runs show <B_ID>`默认text | source/phase/unknown的人类标签准确；不得仍将recorder Python/packages展示成已验证child |

本轮overlay使用明确的轻量合成validation manifest、config和stdlib child，不称作原M5输入或新的五项目gold。child venv仅建`torch-0.0.123.dist-info`，用stdlib importlib.metadata读取，不导入torch；recorder锁定环境不改。child的独立`consumed.json`是**验证者oracle**，产品不得自动解析它或新增child hook来宣称已验证。

输入原字节在运行前固定；child脚本不得隐式改argv或实验外文件。A记录/输出在B覆盖同名文件前立即归档，保留独立parser回执、before/post字节和所有hash。运行的参数变化、package事实、phase和raw数据各有独立依据；不从当前run输出复制expected。

以上65是受影响公共命令核心，不是全部测试数。最终consumer inventory须再次确认：若实际改到模板专属映射或其他命令，添加相应变体并说明原因。default/neurips/acl/acm均有source-label focused fixtures；若checklist公共映射逻辑改变，全五至少再执行一个实际affected venue，专属模板改动按其真实影响扩展，不做无依据格式笛卡尔积。recency diff、show rawJSON、dry-run/preflight及坏记录选择用定向消费者回归覆盖。

## 3. 独立source gold及完整比较

### 基础层

可引用不可变旧oracle，但须重核其pins、输入、schema、Python/依赖、配置和来源SHA适配本轮。候选本次运行全新，旧实际stdout不得重新标fresh。已审定材料包括：

- S1-A独立expected inventory SHA `b98ff6124f5b56f1d1f5e4b76e3f6ed28996833a5c41678c96a9f633d4a48d3d`，建立于审定旧源和固定上游文件，而非本轮输出。
- 最近完整source-tree oracle SHA `65ca244e5d6ecf2da8b736763c45595784270d9779e52a5fbb11ec24722a196f`，其AST/源字节方法可用于核对路径/行号，不等于本次product执行。
- VAL-R01前置完整bundle index SHA `06d04134b580257b5c63fc297a50f4635fba874e24f5176737b0b7655bc9cf80`，只引用不可变expected/来源；其旧QA/Gate结果不复用为fresh。

S3-B未改静态扫描/检测时，基础L0语义预计零delta：LlamaFactory tracked `.env.local` CRITICAL、HarmBench嵌套精确依赖、全部profiles/hints/evidence/path/line保留；lm-eval默认stderr仍仅一次获批500/816摘要，HarmBench语法skip不额外升级默认warning。若实际改到这些路径，先声明影响和独立新预期，不能用“summary一样”掩盖。

完整AuditReport用`compare_gold.py --audit-metadata`，只豁免根generated_at/reprollm_version，实际版本及UTC时间另验；facts严格全比较。stderr/文本/生成MD单独保留完整字节及预期。不得任意drop findings、数组顺序、类型或未知字段。

### R04语义层

| 来源事实 | 独立gold合同 |
|---|---|
| recorder Python/packages | 来自已测recorder metadata及明确采集phase；empty集合仅指recorder，不代表child empty |
| host OS/hardware | recorder所在host实际采集可见事实，不等于远程/容器child硬件 |
| inherited env/argv | prelaunch基础及原argv；保留ordered observations，child内部改写不可反向伪造 |
| lock environment | 创建lock时的recorder事实，不是未来child的安装验证 |
| 同源/异源/unknown比较 | 按具体获批规则逐项确定recorder比较保留及不足说明；未知/不兼容不能输出child verified成功结论 |
| A重复CLI | 原顺序0.1、0.2完整保存，effective0.2；earlier conflicts仍参与consistency |
| B改写config | independent消费0.1，post字节0.9；primary不升为0.9；变化事实定位清晰但不宣称消费验证 |
| selected export | 使用该run的可用snapshot及typed context；current audit仍单列current-working-tree scope |

`consistency.env_vs_lock`、generation/file consistency、default/venue标签的具体status/wording及新context如何投影diff，必须在规范决定后先填入literal expected和before/after完整finding表；本文不替代该决定。不能新增rule ID、放宽severity或解析warning文本作为phase协议，也不修改R07-C全局PASS合成政策。

当前compare_gold只接根schema_version1对象。新run2可完整嵌入schema1比较envelope，list数组亦使用明确envelope；**内层版本/全部值保留**。typed新schema验证另做。原始stdout仅保留一份，envelope转换协议及SHA可重建，避免多处大JSON副本。不得剔除version或用coercing model_dump填expected；如改变比较工具，列独立正反例工具验收。

## 4. 0.6.2 bridge及新旧兼容实际probe

以下均待执行。0.6.1当前实际17叶观察仍按兼容证据记录：schema2/3的list exit0+warning，show/diff exit2但无升级提示，explicit/latest export exit3。不得把这些旧诊断写成已满足新合同。

1. R04-A桥仍读写run1；冻结**实际0.6.2本地wheel/安装环境/bin**、source commit/inventory、wheel SHA和版本metadata。未构建前不写“可用”。桥不是新schema writer，不自动完成R04-B。
2. 在新0.7.0真实writer已生成的完整run2上，使用冻结桥实际公开命令probe，而非只把旧run1的version改2后声称兼容完成。桥拒绝run2并提示升级；future3拒绝在body解释前发生。
3. 桥的八个公开surface：list JSON、show JSON、show text、export explicit、export latest、diff JSON path、diff ID、diff latest-successful。对实际run2/future3覆盖其读者分支；listing原有warning/skip合同单列，不把exit0当接受，其他未知格式应exit2，不能internal3或半读取/写MD。
4. 新0.7.0 reader读旧0.6.1/桥0.6.2的run1和本轮run2；future3清晰拒绝。unknown较新record不能无声fallback到其他run制造“最近记录验证成功”；按主提案明确的selector合同检查warning/error。
5. 对所有legacy fixture及其相邻manifest/lock/snapshots，读前/后完整文件集合及每文件SHA相等；raw show原字节输出。旧run不原地迁移，不用目前文件内容/时间戳猜造pre-phase或child consumption。
6. 未知producer的旧run仍unknown；已知producer只恢复明确能证明的recorder/phase合同。旧post config观测不升级成新before/consumed事实。

桥反向probe与new/future兼容是小型CPU读取，不运行GPU/API/原训练，不重复前述0.6.1负例。桥与minor各记录真实模块/二进制来源、actual argv/exit/time、版本和raw SHA；更换reader/source后不得沿用旧PASS。

## 5. typed State context round-trip

建立包含有序CLI[0.1,0.2]、before config0.1、post changed0.9、recorder-after、inherited-before及child unknown的最小fixture。每个context字段/enum以获批schema为准，以下全部NOT_RUN：

- Run JSON→typed model→State JSON→State往返，subject/phase/consumption及原始alternatives完整保留。
- source-compatible/unknown/legacyunknown各独立用例，unknown不变成empty packages或verified。
- repeated/overlapping State.merge仍选CLI0.2；primary不被旧alternative复活；证据multiplicity有界，真实重复不被删除。
- 无CLI的B按before合同选0.1；post0.9只作变化事实。phase变化不冒充实验参数变化。
- audit、explicit/selected diff、default及四模板export共享同一解释；current audit与historical selected evidence继续分开。
- minimal running/prewrite/final/fallback record同版本、同source语义，失败不生成不存在的环境或baseline证明。

## 6. 有界读取、文件阈值及故障/信号矩阵

这些定向边界不乘以全部五项目，单独用实际stdlib child与安全fault injection；平台限定只遵守既有test marker合同，不把整文件标linux_only。全部待执行：

| 边界 | 完整预期 |
|---|---|
| 200/201个有效输入文件 | 200可按policy snapshot；201仍哈希全部201，关闭全部**file** snapshots并说明原因，不变成只保存200个hash。post复查只限冻结candidate路径，不扫新目录 |
| 默认1MiB snapshot | 原字节hash独立完整streaming；1MiB及±1byte控制；超限只取消snapshot，不伪造缺失hash；UTF-8/NUL/binary及forbidden file分别保留正确决定 |
| 2MiB bindings inspection | 当前actual config reader并无2MiB上限，只有preflight已有该界限。新增actual-baseline inspection bound是本提案的规范修订，批准后测2MiB及±1byte；过限标unavailable，不parse截断文档或自动升限；仍完整stream hash |
| 一次original baseline来源 | hash/snapshot/parsed binding取自同一before原字节基线；不重新读已脱敏copy作真实值，也不混用child结束后的字节 |
| `--no-snapshot` | file snapshot禁用但hash保留；现有manifest/lock document snapshots仍启用，不能假定全部快照关闭 |
| changed/deleted/end-only | unchanged不证明consumed；删除不编造before-null；end-only不伪装pre-input；post读取失败保持unknown，不误报unchanged |
| 根外/loop/symlink retarget/unreadable | 每phase重新核对既有根内读取边界；外侧sentinel open=0，无绝对路径/exception canary泄漏；不声称原子FS sandbox |
| manifest/lock/prompt/config改写 | before refs/hash/snapshot一致，post状态独立；基线失败不能拿post字节顶替；current hash conflict照实保留 |
| child期间recorder-visible metadata变化 | 仅修改owned临时metadata目录；after-child phase准确；不修改锁定主venv或猜造启动时package快照 |
| env内部改写 | capture保留prelaunch inherited基础；independent witness可说明child改了值，但产品不自动导入它做verified证据 |
| child exit7 + before/post/copy失败 | 仍返回真实7，完整status/诊断/部分安全证据；未发生的观察不写成功；no unsafe retry/original-value fallback |
| SIGINT/SIGTERM | 真实独立进程中按已有平台合同转发；保存interrupted、实际child code/CLI既有映射、可得baseline及post不足说明；恢复handlers，不把信号算正常完成 |
| stdout/stderr/privacy失败 | 保留R02-R的PEM、nested secret、unsafe fragment、bounded drain、原argv/terminal/exit行为；saved文件无canary、真实host/user/absolute path |
| atomic save/retry/fallback | 失败阶段分开；安全minimal record不丢child结果/版本，不重写unsafe内容；持续不可写则保留已有safe evidence并警告 |

各读取故障和privacy失败独立建模，不能把所有采集移到before而误伤post outputs、硬件/scheduler时点或中断路径。实际execute不自动执行dry-run preflight；真实run路径必须有回归。201文件与1/2MiB阈值不以缩小测试数据/省略断言声称通过。

## 7. GPU/API和历史资源状态

本轮S3-B是产品会话，**非milestone/非release**，因此本轮新GPU推理/训练、付费API、online HF/Gate B重放均标`NOT_APPLICABLE_FOR_THIS_SESSION`并说明范围，不写PASS，也不利用“现有GPU已可用”触发无关实验。若会话后来变为milestone/release，重新按val.md激活完整适用矩阵和明确资源授权。

[52ecc50记录的VAL-R01](../../../../dogfooding/2026-10-13-val-r01/README.md)仍是10native exit0，但2capture PASS/8FAIL、20snapshot失败。旧数据仅供legacy读取/独立缺陷依据；新的CPU phase fixture或export不能关闭原snapshot fidelity BLOCKED。既有RunPrivacy slash/regex/source语法错误不借本提案修复，R04-S也不引入active child probe、容器/远程observer或自动消费hook。VAL-R02/03、D01/D02/D03/A01-B同样不自动关闭。

## 8. 最终报告和验收边界

每个actual命令只保留一份raw stdout/stderr；汇总引用SHA、完整delta和生成产物，分preparation/product/comparison/pure-observer计数。记录最终candidate及质量inputs库存、五pins before/after、模块来源、退出/timeout、elapsed与independent expected来源。command累计与wall分开，失败attempt不混为PASS，helper重比只称same-input资格化，不称fresh rerun。

最低完成条件是：任务定向RED/GREEN、必要D-39/D-41决定、实际bridge/minor读取矩阵、一次最终全新QA、65 coreleaf及真实affected扩展全部适用断言通过、CI/报告/提交符合本会话流程。未决定字段为REVIEW_READY；未执行gate为NOT_RUN；历史FAIL/BLOCKED原样保留。不能用计划表、旧成功或summary相同宣称S3-B VERIFIED。
