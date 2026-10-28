# R07-C：主 Python 解析递归失败恢复

日期：2026-10-28。任务提交`40c92d2e639b0991cae759315576803d4ff16410`，
基线`d512301f00e96f5646ba8dc1b8ad7d79f3be252a`。状态：本地适用验收通过，
最终交付提交的五项CI在推送后另核。版本仍为未发布0.7.0。

## 计划与合同依据

上一批D-M-CS已完成，精确`d512301`的[五项官方CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40492274192)
于本轮开始再次确认成功。15份历史PROPOSED都有独立接受记录，不当成15个新阻塞。
公共模型VAL-R03及其他既有资源结果保持各自候选，旧Llama-2权限不再是当前开发前置。

本批选择一个当前合同缺陷，先于新的开放政策提案处理：主Python解析器抛出
`RecursionError`时，audit原本退出3，无法完成已接受的selected-but-unparsed合同。
规范§13只将`ast.parse`成功计入parsed；§12.3.1–2已有扫描缺口的两规则消费。
此次只恢复该合同，不新增状态、信用或完整性判定，因此不需要把它伪装为已接受的新政策。
范围与独立依据见检查摘要；当前规范原字节保持。

## 实施与测试

产品改动只有`core/pyscan.py`的三行：在原解析try后单独捕获`RecursionError`，
追加固定相对路径诊断`{path}: Python parser recursion limit exceeded; skipped`，
然后继续扫描，不增加parsed。SyntaxError原行号/诊断、成功兄弟、预算、默认阈值和
规则消费保持；预算内不新增默认覆盖摘要，超过文件预算仍用原默认摘要并计selected skip。
不输出异常正文，不提取部分AST，不重试或调整递归阈值；AST遍历位于捕获范围之外。
MemoryError、RuntimeError及遍历阶段RecursionError继续作为错误上报。

主验证接口沿用公开audit、init（含list-tasks）、export CLI；只在标准库ast.parse/ast.walk
系统边界做可移植故障注入，不mock自有scanner/rule/engine，不新增私有产品测试接口。
首条tracer旧源码1FAIL，新源码1PASS，都是业务结果而非准备ERROR。
最终新增15项：默认/verbose、真实501文件预算、独立WARNING门、声明profile缺证据、
list-tasks/init/export、输入实际bytes与重复输出、正常解析、旧SyntaxError及窄捕获边界。
受影响Ruff、format和mypy通过；完整案例名及范围见[case-map.json](case-map.json)。

冻结最终测试后，新测试加既有pyscan/扫描诊断/audit回归共167PASS，墙钟43.669387秒。
同一最终15项对冻结旧源码实际11FAIL、4PASS、0ERROR/SKIP，墙钟4.149869秒。
失败正文独立分类为10个AssertionError与1个JSONDecodeError：后者是原异常退出后未产生
有效JSON的业务失败，不是setup ERROR。保留全部控制和原失败，没有为得到统一错误类型改测试。
runner在同进程验证目标pyscan路径及哈希、前后source/test bytes；143份冻结payload另有
Git字节绑定，其余142份与新候选相同，不声称对所有实际import逐个动态设防。

原生实证在Python3.12.14、原递归阈值1000下完成：
`"value = " + " + ".join(["value"] * 10000) + "\n"`为80,006字节，小于512KiB，
原真实cli入口退出3，修后退出0，输入原字节保持、正常兄弟inference信号及parsed1/2缺口均核对。
这是fail-on never的非Git最小案例，不是整个实验没有其他finding的证明。
100/5000项表达式对照可以解析；不把10000当作通用阈值。
新增测试把原生探测和真实console都放在独立子进程；仅在当前解释器确实给出可捕获
RecursionError时声称该原生证明。其他解释器能解析、探测超时或native进程失败时，
该单例按明确前提SKIP；可移植注入用于各平台的目标分支回归，实际跨平台结果由精确交付HEAD CI核验。
本机最终专项运行0SKIP。

[Python官方AST文档](https://docs.python.org/3.12/library/ast.html#ast.parse)说明复杂输入受AST编译栈深限制。
网页当时为3.12.16文档，具体RecursionError是本轮3.12.14实测；不借用unparse/literal_eval条目
替parse作异常保证。本修复只处理可捕获的Python异常，不提供所有资源异常或native硬崩防护。

## 最终会话验证

干净detached候选以`uv sync --locked --dev --offline`安装41份锁定轻量包。
先核Git兼容shim、init分支能力、工具来源、22份离线wheel，再做一次最终完整质量门。
24项检查通过：5133 tests PASS、2 slow deselected、0 skipped，
security 362PASS，覆盖率94.56249078%，redaction全语句和分支覆盖。
pytest报告932.79秒，质量层墙钟1118.590844秒，候选输入前后字节一致。
还包含schema/生成文档freshness、examples、自审计、wheel全部143份包载荷，及隔离非editable
安装后13项检查/26条命令。三个失败路径按预期退出1并验收；构建manifest保留其PENDING原值，
最终distribution PASS用manifest哈希关联。通用工具历史任务标签由当前wrapper与commit/inventory绑定解释。
原wrapper收据的一处说明尾句误沿用前批日期/任务名；本轮task、40c提交、24项来源及库存均正确。
另存勘误保留原wrapper和收据，不将该展示字符串当运行身份，也不为文稿勘误重跑产品门。

fresh五项目基础层：50命令/31检查/10份完整JSON，墙钟84.969245秒。
受影响层：130命令/111检查/15份完整JSON，墙钟223.753738秒；
另15份init文件、5份默认export和10份可移植stdout全文逐字节比较。合计180命令、142检查、
25份完整JSON，五个pin/origin/clean均正确，完整profiles/hints/路径/finding/诊断符合预期，gold差异为空。
验收按完整预期，保留上游已有FAIL/SKIP；不同层耗时不相加冒充整会话墙钟。
57份oracle从冻结Git及既有D-C独立修订核对，未从候选输出更新；86项纯工具控制先于产品执行。
条件零delta预期基于同pins、Python3.12.14和旧成功过程，既不证明所有文件已解析，也不代替fresh运行。
AuditReport比较仅豁免根generated_at/reprollm_version，其他类型/键/数组顺序/正文严格比较；
init/export及诊断采用既有已预检的有限可移植路径归一化，版本另由来源守卫核验。

Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE。没有GPU、Hub或付费API调用，不改绑历史资源成功。

## 证据、范围与接续

准备差错保留原件：init草稿错误期待自动backend及显式metric implementation:null，
经既有源码/独立gold纠正；一个未使用的import观察器原型被静态检查拒绝，未启动任何pytest。
另有旧provenance字段读取假设修正；这些均不计产品RED。所有实际失败、修正与工具限制由原收据记录。
公开[session-checks.json](session-checks.json)及[source-index.json](source-index.json)引用私有原件哈希，
不重复分发raw/JUnit/coverage正文。哈希只标识原件，不能独立恢复未公开内容；分享材料不包含机器身份或凭据。

用户README、docs/index、additional-cases-gold三份修改保持原字节；原D-M-CS材料不重写。
报告提交时CI尚待最终交付HEAD推送；五项官方CI及Ubuntu3.12的12个必需步骤交付时另核并写私有闭环收据，
不为更新该历史状态再引入报告提交循环。
独立InspectAI任务解析器、YAML配置自环仅登记为后续静态候选；一般listing、遗漏use、framework、
filtered requirements include和充分性证书仍是更广R07-C工作，不因本片关闭。新政策按独立P-A再审议，不发布版本。
