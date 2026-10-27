# R07-C D-M-CS：Conda 保留名称的 specifier 提取边界 P-A

日期：2026-10-27。基线：`22e3dbcb799a18b8ef096c6fc42e5f5ab7ae9a0d`。
状态：PROPOSED，候选政策执行0。当前源码/规范不改，D-M-CS只是本地提案标签。

上一批D-M-CE及Windows测试修订已完成适用验收，包括精确`22e3dbc`的
[五项CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40462446381)。
当前没有已接受而未实施的新P-B。本片按R07-C开放的相邻边界准备独立P-A，
不是把14份历史PROPOSED快照误当作14个待决任务，也不重开已闭合的旧验证。

## 可审阅材料

- [具体A/B、兼容矩阵与全仓成本](proposal.md)
- [官方来源与语法边界](official-sources.md)
- [精确实现patch](implementation-proposed.patch)、[精确规范patch](spec-proposed.patch)
- [补丁前后字节绑定](patch-binding.json)
- [38组未来P-B验收](acceptance-cases.md)：设计，不是已执行测试
- [具体决定记录](decision.json)、[未发送的spec issue草稿](spec-issue-draft.md)
- [现状行为与有限观察范围](current-behavior.md)、[完整当前记录](current-observations.json)
- [冻结的当前案例](cases-frozen-current.json)、[扩展预期](extensions-frozen-current.json)、[接口](interfaces-frozen.json)
- [两轮重放及严格比较收据](replay-summary.json)、[解释/隐私限制](publication-qualification.md)
- [公开表示映射](publication-copy-map.json)、[独立静态补丁审阅](design-review.md)

本片只调查现helper已经保留name、但将rest替换成固定placeholder的分支。
推荐A仅增加独立内部`unparsed_conda_specifier`并在该现分支setdefault；
numeric RANGE、CE省略、regex、声明、诊断、exact/lock信用和优先级保持。
不从unsupported诊断或exact=None概括新事实，不增加Conda语法支持。

A的全仓保守成本须独立接受：明确非exact的wildcard/compound、无关非关键条目
也可以使其余已用未获信用包WARNING→SKIPPED/INFO，孤立门1→0；
默认text可以PASS+skipped，默认export可少notable条目。B保持当前captured-view WARNING。
官方语言更广不等于官方要求全仓SKIP；新原因不证明hidden pin或完整复现。

32helper及24集成当前案例各在两个新目录重放，每轮464项literal断言、72份完整raw rule
对象符合冻结预期；完整类型/顺序另经默认严格JSON比较，三类语义扰动均被检测。
候选执行仍为0。图范围仅23空图加1个单节点/closure，不宣称验证一般include/depth。
H31 frozen标签不是build wildcard导致上游版本非exact的证明，详见解释限制。
五项目source-only盘点均无supported Conda环境文件，不能当触发或fresh Gate A。
为避免重复全文，actual/expected投影正文留私有并以哈希绑定，完整current和冻结expected各公开一次。

P-A当前观察与来源收据、静态补丁检查和独立复核由[会话报告](../../../../../dogfooding/2026-10-27-r07c-conda-retained-pa.md)引用。
本轮是文稿/提案会话；产品质量门、Gate A/B不冒充PASS。接受具体patch和成本后，
P-B先写独立RED回归，再最小实施、最终完整质量、fresh五项目及精确交付HEAD CI。
更广R07-C、实际外部反馈、申请与发布条件保持各自状态。
