# S2-B / R06-P requirements include 图与精确闭包

日期：2026-10-10。前置 main：`57b1384f748f09ae2af674e31f80ec868eea1972`。
首先读取 S2-A / R06-A 报告，遵循 S2-B 的 R06-P → R05-B 顺序；
规范 §12.2、§13、§22，R05-S A/P 已接受。

每次scan建立一个私有graph，节点保存标准化相对source的读取/解析facts；
include边相对包含文件alias目录规范化，再经R06-G公共边界读取。可用语法
仅空白分隔的 `-r target` / `--requirement target`；attached、quote/expansion、
URL等保守诊断，不执行声明。绝对/根外目标保留R06-G已发布的固定
`include unreadable`字面；malformed、循环、超深、未读、未完成边有来源行诊断。

发现阶段按最小展开深度共享一次source解析，较浅访问可重展开已有边；
每根资格阶段使用active stack和剩余深度memo，先检查cycle/depth再复用。
深度根为0、最大子深度10，不让短路径缓存掩盖长分支depth11，亦不污染
独立浅根。packages与qualification都来自同一RootClosure：必须完整、
非空且全部exact；移除旧同目录前缀 `_declares_from` 借包近似。
每标准化source一次读取/解析，每source/行证据一次；不同合法alias保留各自
相对include目录及provenance，不承诺按物理inode合并。

实际第一 paired vertical RED：根 include 的锁包为空，以及同目录独立
requirements lock互相借包，2 failed（0.43秒）。
其后分别实际RED→GREEN：normalization2FAIL/7controls→9PASS，
cycle2FAIL/10controls→12PASS，depth5FAIL/13controls→18PASS，
边界/provenance14FAIL/20controls→34PASS。25逻辑scenario/34展开，包含
51节点、230边、多层扇出图与四种短/长路径及独立根排序组合。
最终定向310PASS（19.05秒，wall19.547785），scoped Ruff/format/mypy全通过。
独立112公开probe（99 uncached DFS literal graph oracle+10边界+3真实audit CLI）
通过，冻结源码c9cdd4...前后未变。

消费者检查最初2FAIL/308PASS属于新draft绝对/escape诊断措辞与已发布
R06-G字面不一致；保留旧 `include unreadable`并校正未批准的draft vocabulary，
既有security tests不改。独立review初次错误使用不存在module入口导致observer
JSONdecode，单列launcher错误与未记录最初child字段的限制，不冒充产品RED。
实际所有非零退出、source/test前后SHA、日志摘要与校正依据均保留。

[完整质量门](r06p-quality.json) 14项全部通过：2332 tests、2既有slow
excluded、1既有marker warning、精确总覆盖93.52%（term TOTAL四舍五入94%），
redaction statement/branch100%、security158。pytest wall327.345秒。
Ruff、strict mypy、四项生成文档与10 exported schema完整集合/字节全通过；
临时Git init -b shim保持，不改系统Git/依赖。

[开发证据](r06p-development-evidence-index.json)保存21完整portable logs和5个
schema1文档；[TDD](r06p-tdd.json)保留真实退出、walltime、前后source/test SHA、
原stdout/stderr字节摘要，[独立review](r06p-independent-review.json)绑定冻结源码
并明确112最终公开probe与历史harness错误。
[候选摘要](r06p-candidate-summary.json)仍保留冻结时root gates pending历史状态；
最终状态以quality、此报告、Gate及Git binding为准。

[五项目主验证](r06p-gate-execution-accounting.json)实际90条leaf，全部exit0，
712次完整比较（180 baseline + 532 affected）PASS；leaf总210.052325秒，
其中baseline176.074372秒、affected33.977953秒。wrapper190.588759秒单列。
原始五个固定checkout逐个SHA/origin/clean一致，完整L0、init生成manifest、
L1、离线discover及受影响公开依赖/真实audit均执行，gold无delta。

独立复核发现原relative-escape sentinel materialize位置与literal include
实际目标不一致。保留原90条执行及所有712比较，不将它证明为“存在目标未打开”。
[补充验证](r06p-relative-escape-gate-execution-accounting.json)逐pin使用正确且
真实存在的根外sentinel，10条新public/真实CLI leaf、60比较全部PASS，
exit0×10、4.857505秒；guard记录外部内容未尝试打开，原sentinel字节未变。
[CLI语义补充](r06p-gate-retained-cli-semantic-comparisons.json)只读取原35报告，
70个独立literal rule状态比较全部PASS、零产品重跑：合格闭包有lock，
escape/cycle不形成lock，精确torch声明仍通过critical pinned规则。

[最终合计](r06p-gate-session-total-execution-accounting.json)：actual=qualified
100条leaf、842比较、exit0×100、unknown/reused0、214.909830秒；无未解释gold
变化。主runner与原fixture缺口、修正runner、raw完整字节/摘要均分别保留，
不把历史harness错误改写为产品RED或抹去。
[主证据索引](r06p-gate-evidence-index.json)与
[补充索引](r06p-relative-escape-gate-evidence-index.json)绑定各portable artifact。
全部149产品file inventory始终为
`61a15814516cb298b85be66b31f60cfe8f4b902420c6a292d3ccbbfd4ec30013`。
完整保全15生成artifact及98 raw后，仅清理本项5个disposable baseline clone
（2.292519秒），不删除原pin或任何证据。26全局冻结文件逐字节一致。

R05-A Python exact/TOML source index、R06-A全路径候选与类型保护保留。
本任务提供每requirements根的实际可达闭包；独立requirements根仍按现有
仓库全局聚合评估，不决定R06-B的多项目scope或lock ownership。
普通非include malformed/unsupported诊断字节保留，不在此修复pip完整语法。
扫描结果捕获静态图，仍保留R06-G解析后文件替换竞态限制。

Conda规范与实现接续R05-B；YAML-physical-source-index列具名unassigned backlog。
五个原始pin、gold、fixtures/snapshots、依赖/schema/engine/redaction保持不变。
Git产品tree与完整验证inventory提交后绑定；历史VAL-R01–R03仍BLOCKED，
此offline Gate A不代替GPU/API/judge/weights资源Gate B。
