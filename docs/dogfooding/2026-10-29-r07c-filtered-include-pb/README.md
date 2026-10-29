# R07-C D-I：已到达但被候选过滤的 requirements include

日期：2026-10-29。产品提交 `3aadb9a3ab84a25e9af1d55c54e8831042921c96`；接受记录提交
`67c0ed7393b5aa51f79769ff0e601c2f188f0736`，产品基线为 `e3aa653`。
本地适用验收通过，最终交付 HEAD 的五项 CI 在报告提交并推送后独立确认。
版本仍为未发布0.7.0。

## 已接受方案与范围

维护者于2026-10-29明确接受
[A与两份具体补丁](../../plan/reliability-2026-10-03/proposals/R07-C/filtered-include/decision-accepted.json)。
原P-A二十份材料、PROPOSED决定和旧零执行快照保留原字节，接受记录单独追加。
此前精确e3aa653的[五项官方CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40653994798)
及Ubuntu3.12十二个必需步骤已经成功；那些结果不是本批新政策验收。

本批原样实施接受补丁：在原 candidate=False 分支记录私有拒绝集合，全部现有roots
扩展后，从可读父节点的规范化supported include目标与该集合求交，排序去重为内部tuple。
它不把所有unreadable节点、incomplete closure或诊断文字都解释为候选拒绝。
只有既有检查实际到达且拒绝的目标加入；未到达的深度frontier仍只按D-G独立合同处理。
目标扩展名不限于requirements命名，既有发现root的命名规则保持。

顺序为qualified/exact → D-F/S → D-L → D-M → D-G → D-I → 原缺pin WARNING。
新分支只影响剩余已知使用、未获信用的关键包，保留旧优先分支完整message/hint/evidence。
原package use evidence先保留，再附distinct sorted逻辑目标路径；不推断未知包、文件存在或pin。
不改scanner、候选/正文调用、根/边、缓存、深度/读取预算、语法、engine、redaction、
持久化schema、规则ID/默认严重度、依赖、版本或五项目gold。

此成本已具体接受：不存在、正文非精确或无关子项目的被拒绝目标，也可全仓保守影响
剩余缺pin包；孤立WARNING或提升CRITICAL门可从1→0。默认text可显示PASS并保留skip计数，
默认export可少一条notable警告；完整JSON保留SKIPPED/INFO。
它不授予exact/lock信用，不证明隐藏pin或完整复现；独立违规仍可使命令失败。

## 回归、旧期望修订与原生门对照

沿已约定公开audit、init/list-tasks、export与外部文件系统边界验收。
首条tracer先在原源码实际FAIL，再精确应用后PASS；所有三份postimage逐字等接受绑定。
产品143份载荷只变deps/env两份，其他141份相同；规范只按已接受patch更新。
现有图、扫描候选、规则和CLI回归八文件合计688PASS，墙钟48.91242448799312秒。

两处旧期望先实际5case/2FAIL，再修订为5PASS：只把旧excluded-include参数的WARNING改为
接受的D-I SKIP，其余三参数保留WARNING；内部dataclass字段列表末尾追加默认空tuple，
不移动旧构造参数。未据当前输出改gold、fixture或其他规则的结果。

最终新增39例通过，墙钟6.729749256744981秒；相同最终测试bytes在冻结旧源码
实际20FAIL、19PASS、0ERROR/SKIP。完整测量与作者验收映射见
[case-map.json](case-map.json)。机器提取的old/new node名集合相同；作者说明原样保留，
不假定其内部JSON列表格式。目标模块三份同进程origin/hash及前后源/测试bytes受守卫；
143份Git归档绑定另行记录，不把它称为动态验证每一个import。

另用原生console重放两个隔离门：WARNING与提升CRITICAL各旧1→新0，四次调用实际退出
[1,0,1,0]。相同源输入字节保持，两份新完整AuditReport与预先独立写下的字面D-I Finding/
summary预期通过权威比较，仅豁免根generated_at/reprollm_version。
这不是被别的违规遮蔽的“状态数看起来相同”，也没有GPU、Hub或付费API请求。

新tuple为空/marker故障/symlink/动态输入的案例按各自实际前提报告；CLI规范化结果不能
证明内部probe或节点访问次数。无新增原调用和保留缓存/预算的承诺还由有界源码审阅支持。
内部dataclass/asdict消费者可能看到新字段，不能把不变的旧facts投影说成覆盖了新字段。

## 最终完整质量与五项目验收

干净detached候选离线安装锁定轻量环境，并核对Git兼容shim与离线wheel缓存。
一次最终24项及24份origin检查通过，tracked输入前后字节相同：
5221 tests PASS、2 slow deselected、0 skipped；security 372PASS；
覆盖率94.63615628%，redaction语句和分支全覆盖。pytest 964.11秒，
质量层墙钟1151.468242秒。包括文档/schema freshness、examples、自审计、143份wheel载荷，
隔离非editable安装的13检查/26命令与3个预期exit1失败路径；原manifest PENDING与最终
绑定该hash的distribution PASS分别保留，不改写历史状态。

fresh基础50命令/31检查/10完整JSON，墙钟86.173916秒；受影响130命令/111检查/
15完整JSON，墙钟224.632477秒。另有15份init文件、5份完整export和10份可移植stdout
逐字节比较，完整profiles/hints/诊断与既有金标准相符，gold差异为空。
独立list层45记录=5真实list-tasks+40只读Git守卫，墙钟72.86842秒；完整任务清单
lm-eval仍为13,123，其他四项目为空，compact集合摘要符合val§7.1。

原225记录/168检查/450原始流的旧投影保留；新增独立typed层五次public dependency collector，
墙钟20.252235秒，直接确认五pins的新字段确为tuple、值为空及legacy默认空值。
空预期来自独立固定源码无supported include边，不是复制当前输出。
该层有自己的输入完整快照、pin/origin/干净状态与源码来源检查；它不是五次audit CLI。
合计230外层记录/184检查/460原始流。typed collector内嵌Git调用单列，不重复计作外层记录。
五项目不触发该新分支，只能证明条件零delta和空fact，不能替代前面的触发回归。

旧57份oracle不改，86+35纯工具控制与实际产品执行分开；完整JSON仅允许规范列出的两个
AuditReport根元数据豁免，其他类型/顺序严格。旧collector的完整facts比较只覆盖其原投影，
新tuple由上述五次额外事实验证单独覆盖，没有暗中扩大旧gold或声称旧工具已验证新增字段。

Gate B为NOT_APPLICABLE：本批普通政策切片不完成里程碑或准备发布，没有资源调用，
不改绑历史GPU、metadata、judge或discover结果，也不发布版本。

## 原件、限定与后续

[session-checks.json](session-checks.json)与[source-index.json](source-index.json)
只分发所选私有原件及转引hash，原始argv/流/JUnit/coverage正文不重复公开；hash不能恢复
未公开内容。原准备器假设/reader错误、未绑定快照和失败尝试保留，其修订不能称作新的产品重跑。
测试草稿最后一组曾有两项字面预期错误：suppression证据原本追加在末尾，inspect_ai按§4.4
本就属于关键包；按原engine/规范修正测试后通过，产品未改。初轮8处E501/格式问题及原稿保留，
formatter前后AST相同。原接受patch的统一diff空白context及规范节预览EOF触发暂存whitespace检查，
只对这三份已冻结文稿限定处理并保留原hash；产品和测试源码没有whitespace检查例外。
本批源/测试冻结后仅添加报告；用户README、docs/index、additional-cases-gold三份工作保持。

最终交付HEAD的五CI在推送后另核，随后追加独立闭环；此报告内原CIpending状态保留，
不为改写该历史快照而产生新的报告提交循环。
更广R07-C的遗漏roots/use、listing/framework、其他grammar及充分性政策仍OPEN，
没有从本片接受推断其他新合同或发布授权。
