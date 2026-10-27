# R07-C D-M-CS P-A：保留名称的 Conda specifier 边界

日期：2026-10-27。起点`22e3dbcb799a18b8ef096c6fc42e5f5ab7ae9a0d`，main，
版本仍为未发布0.7.0。本轮响应“确认下一步的开发计划并执行”，按R07-C相邻OPEN范围
完成独立P-A；计划没有规定CE后的固定子任务序号，不把推荐接续说成既定批准顺序。

上一批D-M-CE、Windows换行测试修订、适用质量及五项目门已闭合，精确`22e3dbc`
[五项CI全部通过](https://github.com/EnumaElish123/ReproLLM/actions/runs/40462446381)。
历史PROPOSED记录均保留其独立接受记录，不是14个未完成P-B。
VAL-R01/R02及公共模型VAL-R03保持各自候选身份；本轮不重开或重新绑定资源成功。

## 结果及具体接续

[完整P-A材料](../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/README.md)
为PROPOSED/REVIEW_READY，推荐A，尚无具体接受决定，候选政策执行0。
现行规范和实现一致；本片没有修订产品或规范，也不声称新策略已验证。

A只在现helper保留name、非空rest不匹配既有VERSION且不匹配既有RANGE后、
原specifier-placeholder赋值点，增加内部`unparsed_conda_specifier`及一次setdefault。
CE两早退、六种legacy range、regex、声明/用量、诊断、specifier/exact、信用和优先级保持。
源产品拟仅改core/deps.py，规范拟增加§12.3.14及有限交叉引用；精确patch未应用。
B维持当前captured-view WARNING，是有效选择。

新的全仓保守成本必须具体接受：明确非exact wildcard/compound、无关非关键条目也能
把其他剩余已用未获信用包WARNING改成SKIPPED/INFO，孤立WARNING/提升CRITICAL门可1→0。
默认text可PASS+skipped，默认export可少notable条目，完整JSON仍保留SKIP。
这不证明隐藏exact、Conda-invalid、完整扫描、安装或复现成功。
既有D-M-CE/Poetry/Pipfile接受不扩展为本片接受。

## 实际证据

| 层 | 本轮实际结果 | 计时/身份边界 |
|---|---|---|
| 官方来源 | 7份primary资料；CEP24/29/33及版本化源码，区分合法version-exact、非exact和未认证文本 | stable API显示26.9.3、guide显示26.9.4；未安装/执行Conda，不绑定immutable网页正文 |
| 当前helper | 32个literal案例，保持完整Declarations及实际调用参数 | 两个独立新目录各执行一次当前源码，非候选 |
| 当前集成 | 24例public scan/真实Context、每例3条env raw规则，共72完整对象；每轮464literal断言通过 | 两轮命令0.964595/0.967369秒；不相加冒充完整会话墙钟 |
| 严格JSON及重放 | 完整类型/列表/字段符合独立冻结预期；current和metadata逐字节重放一致 | 默认compare_gold，无metadata豁免；布尔/整数、列表顺序、Finding severity负例均退出1，分别1/6/1处差异 |
| 五项目来源 | 40只读命令、80原始流全部留存；pins/origins/全状态前后正确；supported environment路径0 | 命令0.481148秒，盘点层墙钟0.609843秒；不是fresh Gate A或触发证明 |
| 精确补丁 | before/after哈希、内存静态应用、git apply --check、Python3.10 AST与静态Ruff/format通过 | 完整AST仅新增一个Literal成员及现分支的一次setdefault；没有运行候选 |
| 未来验收 | 38组独立合同，包含完整Finding、CLI阈值、文本/export/init、信用/优先级和LF/CRLF保真 | 全部NOT_RUN；接受后才先RED实施 |

当前critical规则的24例分布为9个WARNING案例（10条warning）、7个既有SKIP、
6个信用使raw check为空、2个无known use。raw check为空不等于engine合成PASS；
本轮观察不运行engine、audit/init/export CLI或新fail-on语义。
53份输入实例、143个源文件及71个实际导入模块每轮核验，源/输入字节和原函数身份保持。
真实installed critical metadata为空并按冻结预期核对，没有mock版本或导入框架。

图观察每轮24个，其中23为空，只有CS-I08为单节点/单closure且无include边。
没有把它描述为多层include/depth证明、上一批15节点探针或38组图状态验收。
额外call/order/version/listing轨迹保留，但不把所有观察字段声称为新增literal oracle。
H31的旧known-nonexact标签只描述有限提取器不授信用，不能证明buildglob使version非exact；
冻结标签不回写，另有显眼资格说明。真正已知版本非exact成本以版本wildcard案例说明。

## 类别、保全及验证边界

依据验证流程§3，本轮仅文稿/计划/导航及其冻结证据快照，没有新增受支持验证工具、
产品代码、测试、CLI、默认配置、profiles、模板、依赖、schema或打包行为。
文档链接、JSON/哈希、范围、隐私和内容一致性通过；未受影响的生成文档输入保持。
产品full quality和Gate A记`NOT_APPLICABLE_DOCUMENTATION_ONLY`，Gate B按无milestone/release不激活，
不使用GPU、Hub、付费接口。上述当前行为实验是提案复现，不冒充产品会话验收。
推送后的精确文稿HEAD五项CI在交付时核对，不在报告生成时预先写PASS。

原README、docs/index及additional-cases-gold三份用户工作保持字节，不纳入提交。
未修改既有CE等P-A/PROPOSED/接受记录、old gold、产物或资源证据。
公开current/expected各保留一次；冗余expected/actual投影全文不重复提交。
CS-H32的输入及内部实参采用带原长度/哈希的明确封装，产品Declarations/诊断/Finding未改；
原hash与public表示hash分别记录，不能凭hash重建opaque私有参数。
observer.py.txt原字节公开、参数化且不含本机身份，只是证据快照。
所有原始命令、真实cwd/解释器、流、冻结计划、strict比较和更正/负例均留在外部会话。
具体[文稿检查](../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/document-checks.json)、
[原件哈希索引](../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/source-index.json)
及[独立当前观察回读](../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/current-observation-review.json)
保留各层范围；静态设计审阅不是维护者的具体政策接受。

下一步是对[具体A/B及补丁](../plan/reliability-2026-10-03/proposals/R07-C/conda-retained-suffix/proposal.md)
作决定。需要具体决定的依据是执行总则§5.9及policy§1：当前规范明确保持该分支，
总体继续开发授权不能把建议当成规范修订。接受后直接P-B：先独立RED、最小实现、
一次最终完整质量门、fresh五项目及受影响消费者、精确最终HEAD CI。
更广R07-C、实际外部试用反馈/申请条件和版本发布保持独立OPEN。
