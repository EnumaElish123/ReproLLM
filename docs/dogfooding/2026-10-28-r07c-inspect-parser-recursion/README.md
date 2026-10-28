# R07-C：InspectAI 独立 Python 解析递归回退

日期：2026-10-28。任务提交`3c217497aabbb828f4acbe7cbc8930265e3208f1`，
基线`960a1fdb816775beb34c30f628a1555341159815`。本地适用验收通过；
最终交付HEAD的五项CI在推送后另核。版本仍为未发布0.7.0。

## 前置状态与本批范围

按维护者要求，先等精确`960a1fd`的[五项官方CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40625051941)
全部成功，并离线独立核对Ubuntu3.12全部12个必需步骤，之后才启动本批产品与测试。
上一批报告的“提交时待CI”保留历史原字节，本轮以新收据补齐，不重跑或改写旧身份。

最新方案登记的下一独立候选是InspectAI任务解析器。主Python扫描已能跳过解析递归错误，
但初始化规划随后调用的独立`ast.parse(text)`只捕获SyntaxError，仍可能让init/list-tasks中断。
本批只补一个既有回退的异常类型：`except (SyntaxError, RecursionError)`，继续同一原regex。
规范§3.2/§14规定静态安全候选库存、显式任务选择及不推断metric implementation；
规范没有逐项枚举这两类parser异常。此范围依据既有“AST无法解析时回退”的实现意图与
上述候选合同，经独立范围及实现审阅确认，不把新的OPEN政策当成已批准合同。

原regex并非完整Python解析器，既有未锚定匹配和有限bare-decorator语法保持；
不扩展called/qualified/async回退识别，也不把文字候选当成实际执行过的任务。
成功AST分支仍识别已有decorator形式。恢复的名字仅进入安全排序去重库存：
普通init仍空metrics，只有显式选择才填name，implementation仍由作者确认。
不改规范、规则、engine、schema、扫描预算/过滤、阈值、依赖或版本；
不执行被检查源码，不导入InspectAI，不重试解析或调整递归限制。
MemoryError、RuntimeError及AST遍历阶段RecursionError保持错误。

## 实证与专项回归

沿用已接受的公开init、list-tasks和task选择接口。可移植故障仅注入标准库
ast.parse/ast.walk系统边界，不mock自有scanner、规则或framework helper。
首条tracer旧源码1FAIL，新源码1PASS。最终新增18例，涵盖库存/不写入、无选择和显式选择、
重复排序/force字节重现、inference配置、三种无效选择写前拒绝、正常AST、旧SyntaxError、
同样的有限regex、双解析器同时失败、窄异常边界、过滤/512KiB上限、真实501文件预算、
敏感候选过滤，以及有前提的原生console案例。详见[case-map.json](case-map.json)。

冻结后，同一18例对旧Git源码实际12FAIL、6PASS、0ERROR/SKIP；12项均为业务断言失败。
新测试与相关framework/init/主解析器旧回归共59PASS、0FAIL/ERROR/SKIP。
定向测试墙钟11.664823秒，旧对照3.024170秒；Ruff、format和目标mypy通过。
同进程守卫检查实际InspectAI模块路径/哈希及测试前后bytes，143份基线包载荷另由Git绑定，
其余142份与新产品相同；不声称逐个动态保护所有import。

原生实证使用80,073字节源码，在本轮Python3.12.14、原递归阈值1000下实际触发
RecursionError。源码是bare任务定义加10000项二元表达式，小于512KiB读取上限。
独立`run.sh`中的`inspect eval`信号保证主扫描跳过坏文件后仍进入框架任务提取；
仅写`--profiles evaluation`本身不能代替框架检测。相同输入的真实CLI旧退出3，
新退出0并列出`recovered`，输入bytes及无写入均核对。
不把10000当通用阈值，不把最小任务库存恢复当成实验完整可复现。
冻结测试仅在独立AST probe未证明前提时按明确条件SKIP；后续console超时或进程失败
会使该测试失败，不计恢复PASS。可移植注入与真实跨平台CI分别承担各自证据；
本机最终专项原生案例0SKIP。本修复不保证防护native硬崩或其他资源异常。

## 最终会话验证

干净detached候选安装41份锁定轻量包；Python3.12.14、Git兼容shim及22份离线wheel已预检。
15,097份tracked输入在最终质量门前后字节一致。一次完整24项及24份origin检查通过：
5151 tests PASS、2 slow deselected、0 skipped，security 364PASS，
覆盖率94.62151394%，redaction全部语句与分支覆盖。
pytest报告940.21秒，质量层墙钟1125.79018秒。
包括schema/生成文档freshness、examples、自审计、143份wheel载荷完整比较，以及隔离
非editable安装的13项检查/26条命令；三个失败路径按预期退出1。
构建manifest的原PENDING不改写，最终distribution PASS通过manifest哈希关联。
通用工具历史任务标签由当前wrapper、exact commit及全输入库存明确限定，wrapper本批显示名已校正。

fresh五项目基础层50命令/31检查/10份完整JSON，墙钟84.864461秒；
受影响兼容层130命令/111检查/15份完整JSON，墙钟223.133173秒。
另比较15份init文件、5份默认export及10份可移植stdout全文；完整gold差异为空。
五个pin、origin、tracked/untracked干净输入均核对；上游已有FAIL/SKIP保留，不能只看计数。
额外5个真实`init --list-tasks`调用和40个只读Git命令共45份执行记录/26项检查，
逐字节核对完整库存与不写入：lm-eval为13,123个名字，
其他四项目为空。该补充独立计数，不冒充原180集合已包含task-selector变体。
新RecursionError选择语义由上述有限CLI案例直接验收。

57份既有oracle原字节不变，86项纯工具控制先于产品执行。
新增库存预期来自固定上游源码的独立top-level scalar声明清单，compact JSON集合摘要
精确等于val§7.1的`2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`；
没有把候选stdout复制为gold。零delta预期只由旧成功路径与相同环境条件支持，不能代替fresh运行。
Audit JSON仅豁免根generated_at/reprollm_version，其余JSON类型/键/顺序完整严格比较，
init/export/诊断使用已预检的有限可移植归一化。

Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE。本批没有GPU、Hub或付费API调用，
不把历史资源成功改绑至当前候选，不发布版本。

## 证据与后续

初稿样式检查、独立库存的条目/文件mode/摘要序列化假设，以及JUnit分类读取假设均保留原件，
按准备问题纠正；这些不计产品RED，也不据此改gold。独立源码库存中18个可执行regular YAML
并非symlink；修正该准备诊断没有扩大产品读取边界。
公开[session-checks.json](session-checks.json)与[source-index.json](source-index.json)
记录所选私有原件及转引日志哈希，不重复分发raw/JUnit/coverage正文；哈希不能恢复未公开原文。
用户README、docs/index和additional-cases-gold保持原字节，既有提案和接受记录不重写。

报告提交时最终交付HEAD的CI另待推送后核验；五项及Ubuntu3.12十二步闭环保留独立收据，
不为改写这一历史待执行状态引入新的报告提交循环。
YAML配置对象自环仍是下一独立静态候选，尚未实测；listing、遗漏use/framework、
filtered include和更广R07-C充分性政策继续OPEN，新合同按独立P-A审议。
