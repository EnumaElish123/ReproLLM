# D-I P-A：现行公开CLI观察及证据边界

状态：PASS_CURRENT_POLICY_OBSERVATIONS_ONLY；future policy executions **0**。
冻结源码为e3aa653的143份包载荷。24个case的literal输入/当前预期先冻结，先运行C01，
确认后才扩展。27次真实audit包括24JSON、C01重复1、C12两种文本2。
加6次Git准备/守卫、1次完整报告比较、1次额外追踪文件资格查询，共35命令；
原计划/原观察器的34计数保留，后加Git查询单独记录，不把35都称作产品命令。

- [冻结输入与独立当前预期](cases-frozen-current.json)
- [公开观察投影](current-observations.json)
- [原始记录哈希索引](current-raw-index.json)

24份完整AuditReport原文只保存在私有原件。逐case比对的是预先冻结的完整目标finding
（含message/hint/所有evidence/origins）、完整stderr诊断、detected profiles、level、target、
退出码及输入bytes/links。不能称为24份完整AuditReport对独立gold比较。
唯一的完整AuditReport比较是C01首次与重复，使用权威compare_gold入口，仅豁免规范T-02的
根generated_at/reprollm_version；该项单列，不放大为所有case的重复性证明。

当前C23 WARNING门及C24提升为CRITICAL门均exit1。C12两份文本演示现行D-M的SKIP：
默认Findings可PASS，show-skipped可见该skip；它们不是未来D-I文本或出口验收。
Linux symlink案例保留实际前提，不宣称已跨平台执行；C17的../outside.data是明确的
合成escaping include拒绝输入，不是机器实际绝对路径。没有mock自有scanner/graph/engine。

三目标模块deps/scanner/env有同进程路径/哈希守卫；143份冻结载荷另与Git归档及所用环境
的源载荷逐一比较。解释器为此前9903627轻量环境的Python3.12.14，安装metadata仍属于
此前环境；本次通过sys.path使用冻结e3aa源码，不声称安装了e3aa的独立wheel，也不将
三模块守卫说成动态验证全部import。

观察器与绝对argv/runtime原件留私有；公开投影只给logical argv、内容投影和hash引用。
哈希识别原件，但不能恢复未公开正文。图分支及无新增调用依据独立源码结构审阅，
公开规范化CLI输出不证明内部节点或探测次数。现行观察没有准备/reader失败。
新政策未接受、未执行；这些成功不代替P-B的RED→GREEN、最终质量或fresh五项目验收。
