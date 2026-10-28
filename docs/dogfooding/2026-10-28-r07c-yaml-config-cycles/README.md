# R07-C：配置键遍历的 YAML 对象循环

日期：2026-10-28。任务提交`ccf9bafeaef3856f4662476dad8a0c7bcb27cb99`，
基线`347eae7fb7ac1ee8326e71bafdb8552191b25f60`。本地适用验收通过；
最终交付HEAD的五项CI在推送后另核。版本仍为未发布0.7.0。

## 当前进度与范围依据

上一批InspectAI修复已完成，精确`347eae7`的[五项官方CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/40630856299)
及Ubuntu3.12全部12个必需步骤成功，本轮先核对其离线原始收据和独立闭环。
旧报告提交时的CI待执行状态保留原字节，不重写历史身份。
当前计划登记的下一独立候选是配置YAML对象自环；更广R07-C政策仍OPEN。

规范§13要求从配置键名检测关键词，不扫描值。原实现已用SafeLoader解码YAML，
再递归遍历dict/list键。成功解码的合法引用图可以含循环，原遍历会无限重复直至
RecursionError，使audit/init/export无法完成，也失去循环之后的健康键证据。
这次修复只恢复既有键检测合同，不新增不完整证据政策、规则状态或覆盖率表示；
两份独立范围审阅均确认无需先把新的OPEN政策视为已批准。

## 实施与实证

产品仅修改`profiles/detect.py`的`_collect_keys`：当前路径记录dict/list对象identity，
再次遇到当前祖先时跳过该值边；进入字典时仍先记录字符串键，再递归值。
离开容器时finally移除identity，因此正常共享别名仍按原顺序重复展开，
不把“已访问过”误当“当前路径成环”。循环边自己的键、后续分支及兄弟文件的证据都保留。
没有全局去重、深度/节点截断、重试或递归阈值调整。

配置读取边界、parser原有Exception→空键列表行为不变；parser阶段的MemoryError等
仍按原合同跳过该输入，遍历阶段的意外异常则继续传播，不能一概称所有异常都被修复。
不执行被审计配置中的代码，沿用原SafeLoader的标签处理；不扩展解析语法，
不改规范、规则、engine、schema、预算、依赖或版本。
本批不提供所有深层结构、高别名展开度或资源异常的防护承诺。

实际最小输入为46字节：

```yaml
plain: &loop
  link: *loop
judge: 1
rubric: 1
```

Python3.12.14与本轮锁定依赖实际解码出的plain映射，其link确实指回自己。
冻结旧源码的真实audit CLI退出3、无JSON；同一输入修后退出0，报告保留
llm_judge=medium及来自config.yaml的judge/rubric两条证据，输入字节及无写入均核对。
旧源码另运行39字节健康无环对照；其完整AuditReport与新自环报告，经权威比较入口仅豁免
根generated_at/reprollm_version后逐类型、键、顺序和值完全相同。
这是非Git最小案例、fail-on never的恢复证明，不代表整个实验没有其他finding。

## 冻结测试与边界

沿用公开audit、init（含list-tasks）、export接口。首条tracer实际旧1FAIL→新1PASS。
最终新增18例：映射/列表/混合/互环、回边键与前后健康分支、兄弟文件、值文本不检测、
canonical关键词、正常共享别名报告、JSON/TOML、坏语法/未知YAML标签、初始化、导出、
独立WARNING门、已发现的高置信违规，以及decoder和walker两个第三方边界。
主体使用真实YAML；仅异常边界包装第三方decoder，不mock自有walker、scanner或规则。
详见[case-map.json](case-map.json)。

同一最终18例对旧Git源码实际10FAIL、8PASS、0ERROR/SKIP，10项均为业务AssertionError。
新专项及既有profile检测/audit/init/export共177PASS、0FAIL/ERROR/SKIP；
定向墙钟44.775053秒，旧对照2.541912秒。Ruff、format和目标mypy通过。
目标模块同进程路径/哈希及测试前后bytes均受守卫；143份旧包载荷另由Git绑定，
其余142份与新产品相同，不冒称逐个动态检查所有import。

CLI按distinct canonical concepts选证据，无法据其输出计数共享容器访问次数。
公开别名案例证明报告兼容；内部原DFS顺序和重复展开依据源码结构审阅，不伪称独立CLI计数证明。
本轮真实YAML案例没有依赖某个复杂表达式阈值或人为改变解释器限制。

## 最终会话验证

干净detached候选安装41份锁定轻量包；Python3.12.14、Git兼容shim及22份离线wheel已预检。
15,102份tracked输入在最终质量门前后字节一致。一次完整24项及24份origin检查通过：
5169 tests PASS、2 slow deselected、0 skipped，security 367PASS，
覆盖率94.62666765%，redaction全部语句和分支覆盖。
pytest报告941.66秒，质量层墙钟1129.557978秒。
包括schema/生成文档freshness、examples、自审计、143份wheel载荷完整比较，
以及隔离非editable安装的13项检查/26条命令；三个失败路径按预期退出1。
构建manifest的原PENDING不改写，最终distribution PASS通过manifest哈希关联。
通用工具历史标签由当前wrapper任务、exact commit和全输入库存限定，没有借用旧结果作本轮PASS。

fresh五项目基础层50命令/31检查/10份完整JSON，墙钟85.394089秒；
受影响层130命令/111检查/15份完整JSON，墙钟222.993639秒。
另比较15份init文件、5份完整export、10份可移植stdout及完整诊断；gold差异为空。
额外5个真实list-tasks与40个只读Git命令单独计45份执行记录/26项检查：
完整任务清单符合独立源码预期，lm-eval为13,123名，其余四项目为空，全部输入bytes保持。
225份总命令收据、168检查、450份原始流分层计数，不能把全部记录都称作225次产品CLI。

五个pin/origin/完整tracked与untracked干净状态均核对，上游原有FAIL/SKIP保留。
57份旧oracle和独立任务正文原字节不变；86项原纯工具控制及35项额外清单工具控制通过，
与实际产品检查分别记录。独立任务集合compact JSON摘要仍为val§7.1的
`2a5d98bfd121e95919da7d472c40d89a2580746672a2109e79fcd407c06c36f3`。
条件零delta预期基于同pin/codec的旧消费者成功及本批仅剪循环边；不宣称所有config都曾成功解析，
也不以旧成功替代fresh验证。完整JSON仅豁免AuditReport根时间/版本字段，其余严格；
init/export/诊断使用已预检的有限可移植归一化，不自动更新gold。

Gate B为NOT_APPLICABLE_NO_MILESTONE_OR_RELEASE；本批没有GPU、Hub或付费API调用，
不改绑历史资源结果，也不发布版本。

## 证据与交接

导出草稿曾错误期待未转义的profile名，而既有exporter使用Markdown文本转义；
原3PASS/1FAIL执行、原字面预期、基线源码依据和更正后通过均保留，不计产品RED。
首轮样式检查及验证准备器的直接/传递oracle引用假设也按准备问题记录，不据此改gold。
旧测试稿的事后重建明确标为重建，字节哈希等于原run记录，不能伪称当时保存的副本。
作者交接的案例数是整数、分类是另一个列表；报告准备器已显式适配，原件不改写。

公开[session-checks.json](session-checks.json)与[source-index.json](source-index.json)
仅分发所选私有原件及转引日志哈希，不重复分发raw/JUnit/coverage正文；哈希不能恢复未公开内容。
用户README、docs/index和additional-cases-gold三份修改保持原字节，旧提案/接受记录及814份前批索引原件不重写。

报告提交时最终交付HEAD的CI仍待推送后另核；独立闭环收据确认五项及Ubuntu3.12十二步，
不为改写这一历史待执行状态引入报告提交循环。
更广R07-C的listing、filtered include、遗漏use/framework与充分性政策仍OPEN。
深无环/别名展开资源边界需独立核对与审议，本批不暗中新增截断或完整性结论。
