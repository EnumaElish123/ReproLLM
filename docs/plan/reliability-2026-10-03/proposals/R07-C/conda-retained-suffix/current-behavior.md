# D-M-CS 当前行为及观察范围

状态：当前`22e3dbc`观察；候选政策执行0，不是P-B验收。
预期由执行前冻结的literal案例及扩展字段给出，不从实际结果生成。
源包143文件及实际导入来源受哈希守卫；观察器拒绝包含候选新Literal的源码。

## 已观察的区别

| 当前路径 | 当前捕获/规则结果 | A的未来影响（尚未执行） |
|---|---|---|
| bare、数字单=prefix、数字==、literal build | 保持原specifier/exact及信用 | 不新增原因 |
| 原六种numeric RANGE | 可能有unsupported诊断，但保留raw specifier，无CS原因 | 仍不新增原因 |
| 非空rest不匹配VERSION及RANGE、原placeholder赋值 | name/用量保留，specifier为固定占位，exact=None；没有其他信用/不确定性时缺pinWARNING | 在同一现分支记录新原因，复用D-M；不恢复exact |
| CE的两处原早退 | 原unparsed_conda及省略声明的行为 | 保持CE，不扩展为CS |
| 原pip/shape/CE已有原因 | 保留原先因和部分有效声明 | 新setdefault不得覆盖更早原因 |
| exact/合格lock、已关联失败lock | 原信用或更高优先级Finding | 原优先级保持 |
| 无已知critical use | applies=false的原原因 | 不凭被忽略/URL内部文字造包 |

观察覆盖32条direct-helper输入及24个真实public scan/Context集成案例。
每个集成案例读取三条真实env规则，记录applies/skip_reason/pass_skip_reason和完整raw findings，
共72份raw rule对象；这不是72份完整audit CLI报告，也不将空check结果冒充engine合成PASS。
同一份冻结输入在两个新目录各执行一轮，全部464项literal断言匹配，原始current及metadata
各自两轮逐字节一致。调用使用真实轻量环境的installed version metadata，没有导入被审框架。

## 类型严格性及不变量

观察器内部Python相等判断只作为第一层断言。另以冻结cases/extensions单独构造expected
projection、保存的current构造actual projection，使用仓库`compare_gold.py`默认严格模式
补核完整类型、字段及列表顺序，不使用metadata豁免。bool/int、列表顺序和完整Finding
severity三种语义扰动必须被拒绝；比较原件及失败退出码另留收据。

`sys.setprofile`只观察实际native helper、Requirement、scanner及真实requirements graph；
没有替换产品函数、factory或构造假图。每轮24个集成graph中23个为空，CS-I08有一个
exact requirements节点及一个closure。这是有限非空捕获，不是多层include/depth、所有图形
或38组未来验收的图状态证明。D-L/D-G等更广优先级由源码审阅及未来P-B专门回归覆盖。
源文件、输入字节、原函数身份及profile恢复都受守卫，未运行engine/CLI/Conda/候选/资源门。

CS-H31冻结标签`wildcard-build-known-nonexact-proposed-cost`只表示本工具当前不授exact，
**不能据此断言build glob令版本非精确**；官方version与build是独立维度，见来源说明。
明确版本非exact的保守成本用版本wildcard H12/H13及CS-I02说明；不重写冻结标签或冒充新实验。

## 公开副本限制

合成canary在产品Declarations/诊断/Finding中未出现；内部参数轨迹/输入计划可包含它。
公开副本对指定参数使用带原值哈希的封装，并保留原私有整件哈希和精确变换映射。
这种副本是审阅表示，不是未删改原件，单凭公开哈希不能恢复未公开正文。
观察器源码快照是本次证据，位于计划资料中；不是新增受支持CLI、产品测试或通用验证工具。
原始命令、实际解释器/路径、计时、输入及输出均保存在外部会话目录。
