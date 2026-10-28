# R07-C：深层已解码配置的键遍历

日期：2026-10-28。任务提交`990362772d61be211e4d98f0c1a70b872ccc50d5`，
基线`a8806aa9698cd2495e544ecefb8d5dd02ab9149c`。本地适用验收通过；
最终交付HEAD五项CI在推送后另核。版本仍为未发布0.7.0。

## 当前进度与范围依据

上一批YAML对象循环修复的精确`a8806aa`已通过[五项官方CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40641554209)
及Ubuntu3.12全部12个必需步骤；本轮先核对其原始收据与独立闭环。
旧报告中的待执行状态保留原字节，不修改历史身份。更广R07-C仍OPEN。

规范§13既有配置键名检测通过dict/list值抵达嵌套键。合法且预算内的JSON可以在实际CLI中
成功解码，却使随后递归收集键的调用栈耗尽，令audit/init/export无法完成。
两份范围审阅先以实际“解码成功后walker失败”为前提，独立复读原生trace后才确认：
保持遍历语义、只替换执行方式属于既有合同修复，无需将新的OPEN政策视为已批准。

## 实施与原生实证

产品只改`profiles/detect.py`：用保存原迭代器的frame栈代替`_collect_keys`的Python递归。
字典仍先记录字符串键，再处理值；原列表/字典迭代器保持惰性和原顺序。
仅剪除active祖先回边，完成的共享无环alias仍重复遍历；离开容器和异常清理仅移除本次加入的identity，
保留调用者已有active成员。只在推进迭代器处处理正常StopIteration，意外walker异常继续传播。

不增加深度、节点、工作量或alias预算，不改递归限制；保留原decoder异常跳过、key-only、
扫描边界、规则、engine、schema、依赖与版本，不新增不完整证据结论。
移除调用栈依赖不保证任意图的内存、时间或高alias展开度安全。

原生配置的完整构造为`{"plain":`加1000个`[`、`{"judge":1,"rubric":1}`、1000个`]`及`}`换行，
共2033字节，SHA256为`accdc6433d1ad9283bd6c43831bf57bd72fe2a926ec52af26fa8d19e251643e4`。
在本轮Python3.12.14、各console进程实际记录的原递归上限1000下，冻结旧源码真实CLI退出3、无JSON；
trace明确先越过`_config_keys`的decoder捕获，再在`_collect_keys`重复调用中抛出RecursionError。
因此阶段归因不依赖独立解码探针。相同输入的新CLI退出0，保留llm_judge=medium及config.json的
judge/rubric两条证据；实际argv未替换decoder或修改递归上限。

旧源码另运行33字节健康浅层对照，退出0；其完整AuditReport与新深层结果按权威比较入口
仅豁免根generated_at/reprollm_version后相同。三次输入及产品字节保持，未写入命令产物。
深度1000只是本运行时的观察，不承诺跨平台parser阈值。
这是非Git、fail-on never最小恢复证明，不代表整个实验没有其他finding。

## 冻结回归与可观测边界

首条公开CLI tracer实际旧1FAIL→新1PASS。新增13例涵盖深列表、映射、混合容器与active回边、
后续键和兄弟文件、值文本负例、原decoder拒绝、两种意外迭代器错误、live列表、init及任务清单、
重复export与完整浅层对照，以及独立WARNING和warning/critical门。旧18项cycle测试原字节保持。

跨运行时的深图案例只在第三方json.loads接缝提供已解码对象；浅层marker的真实JSON含义与合成图
明确区分。自定义mapping/list案例刻意超出普通JSON语义，用于保持原live迭代和异常合同。
另有真实parser observer在实际CLI调用中记录原json.loads返回，之后迭代核验内置结构；
只有parser确实拒绝原生输入时允许条件SKIP，成功解码后丢失键或报错必须FAIL。
observer增加一层调用frame，不能冒称完全未观测的原生console；上节独立console证据另行保留。
没有mock自有walker、scanner、engine或规则。详见[case-map.json](case-map.json)。

相同最终13例对旧Git源码实际9FAIL、4PASS、0ERROR/SKIP；新专项及既有受影响接口共190PASS、
0FAIL/ERROR/SKIP。定向墙钟47.26310367695987秒，旧对照2.0407385379076004秒；目标Ruff、format、mypy通过。
同进程目标模块路径/哈希及前后源/测试字节受守卫；143份旧产品载荷由Git绑定，其他142份与新产品相同。
不将这些守卫称作逐个动态验证全部import。

CLI规范化证据不提供内部容器访问次数；原DFS顺序及无环alias重复保持由源码结构审阅支持。
本地原生observer本轮未跳过；其他平台若真实parser拒绝，仍按明确前提条件记录。

## 最终会话验证

最终detached候选离线安装41份锁定轻量包，Python3.12.14、Git兼容shim及22份离线wheel已预检。
一次完整24项和24份origin检查通过，全部committed输入前后字节一致：
5182 tests PASS、2 slow deselected、0 skipped；security 368PASS；
总覆盖94.63260197%，redaction全部语句和分支覆盖。pytest 942.72秒，质量层墙钟1129.353739秒。
包括schema/生成文档freshness、examples、自审计、143份wheel载荷完整比较，及隔离非editable安装的
13检查/26命令，三个失败路径按预期退出1。构建manifest原PENDING保留，最终distribution结果单独绑定。
通用工具的历史标签由当前wrapper任务、精确commit与完整库存限定，没有借用旧结果作本轮PASS。

fresh五项目基础层50命令/31检查/10份完整JSON，墙钟85.833683秒；
受影响层130命令/111检查/15份完整JSON，墙钟223.017205秒。
另比较15份init文件、5份完整export、10份可移植stdout及完整诊断，gold差异为空。
额外五个完整list-tasks加40个只读Git守卫，独立记录45命令/26检查；
lm-eval为13,123个任务，其余四项目为空，符合独立源码预期，所有输入字节保持。
合计225命令收据/168检查/450原始流，不能称作225次产品CLI。

五个pin/origin和完整tracked/untracked干净状态均核对，上游既有FAIL/SKIP保留。
57份旧oracle及独立任务正文不改；86项原纯工具控制与35项清单控制通过，与产品执行分开记数。
独立任务集合的compact JSON摘要仍为val§7.1的
`2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`。
零delta预期只作条件预测：相同pin/codec旧消费者已完成，本批保持健康键输出；
不据此声称所有配置都被成功解析，也不以旧成功替代fresh门。
完整JSON仅豁免AuditReport根时间/版本，其余严格；init/export/诊断沿用已预检的有限可移植归一化。

Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE：本批普通缺陷修复不完成里程碑或准备发布，
没有GPU、Hub或付费API调用，不改绑历史资源结果，不发布版本。

## 证据与下一步

首轮测试样式检查有一行101字符及四处布局问题，修正前后AST相同；原稿和失败日志保留。
原生replay私有准备器曾把换行写入生成的`-c`字符串，导致编译期SyntaxError；尚未进入产品代码，
只将该换行表达改为chr(10)后重跑，失败原件与修正均保留，不计作产品FAIL。
验证准备器的字段形状/原仓origin表示假设也保留原尝试，不据此修改产品或gold。
独立复读曾额外假定先后两次export整份文档相同；中间schema导出增加了既有untracked警告，
该非合同断言已移除。四模板选择第二run/cap48等实际安装验收仍逐项核对，原始产物未改。

[session-checks.json](session-checks.json)与[source-index.json](source-index.json)导出所选私有原件及转引哈希，
不重复分发raw/JUnit/coverage正文；哈希不能恢复未公开正文。
用户README、docs/index和additional-cases-gold三份工作保持原字节，旧836份索引原件不改写。
报告提交时最终交付HEAD的CI仍待推送后另核；随后保留五项及Ubuntu3.12十二步的独立闭环，
不为改写历史待执行快照引入报告提交循环。

更广R07-C保持OPEN。建议下一独立P-A聚焦filtered include：规范§12.3.8明确把预算内候选过滤
排除在已接受D-G新事实之外，需要先给出现有行为、具体政策补丁、兼容成本和验收，再独立裁决。
listing、遗漏use、framework覆盖与充分性政策仍分域OPEN；本批不代其接受新的完整性结论。
