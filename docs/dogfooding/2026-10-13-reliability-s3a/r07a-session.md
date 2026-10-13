# S3-A / R07-A：先过滤静态候选，再计算预算

日期：2026-10-13。前置 main：`798f064ca6704d3bc7b6adacb6f0608ebd7b436d`。
执行 [S3 任务卡 §2](../../plan/reliability-2026-10-03/03_Scan_and_Runtime_Evidence.md#2-r07-a扫描候选过滤先于预算)，
依据规范 §§11、12.2、13、16.4、20.2、22；接续 S2 的 R06-G 内容边界。

静态候选在 Git / fallback 两种枚举下共用已知目录与 `pyvenv.cfg` 排除，
过滤先于 Python 500 文件、依赖、profile、framework/task 与 discover 预算。
内部链接和显式 requirements/task 路径不能重新引入被排除内容；真实嵌套
研究项目及 `vendor` / `third_party` 保留。完整文件与 Git 事实仍由现有接口
提供，安全规则仍发现排除目录内被跟踪的 `.env.local`。

独立核对补充了环境标记权限异常及 fallback run 空目录两个失败回归。
标记不可检查时使用固定相对诊断；run 目录不再贡献伪 profile 名称。
外部链接仍交由 R06-G reader 拒绝，不检查根外环境标记。候选列表在同一
context 首次捕获后缓存，后续根内链接或标记改动不构成原子快照保证；
每次内容读取的根边界和目标缓存检查仍保持原合同。

开发 [证据索引](r07a-development/index.json) 保留 16 次真实命令：四组
真实 RED 共 13 项失败、一次旧 pytest garbage 清理中断（exit 130）、
两项 CLI oracle 错将既有空 inference 对象判断为 null 的失败，以及后续
修正与成功。没有把中断或 oracle 错误计为产品 GREEN。相关 focused
656 项通过，最终新增候选矩阵 53 项通过；原始日志在本地验证存储，
仓库的可移植副本记录原始摘要及净化方法。没有修改 golden snapshots。

[完整质量门](r07a-quality.json) 14/14 exit 0：2444 tests、160 security tests，
总覆盖率 93.58%，redaction statement/branch 100%，strict mypy、Ruff、
四项生成文档检查及十个 schema 完整集合/字节通过。全量 pytest 命令
352.928 秒；两项既有 slow deselection 和既有 marker warning 保留。
沿用 S1-A 验证过的临时 Git 2.25.1 `init -b` shim，系统和依赖未改动。
测试使用本批独立 basetemp，避免旧 pytest 临时目录的退出清理。

[质量输入](r07a-quality-inputs.json) 中 420 文件在质量门前后字节不变。
[受保护文件](r07a-frozen-files.json) 的 37 个 engine、redaction、schema、
profile 合同与依赖文件仍与前置提交一致；消费者清单与 58 个受保护
AST 定义见 development 包。产品共 149 文件，仅八个指定消费者改变。

[五项目 Gate A](r07a-gate-evidence-index.json) 已通过：155 条计划叶命令，
1,053 项完整比较（180 baseline + 873 受影响消费者/边界控制），五个
固定 SHA、origin 和 clean 状态有效；149 个产品文件前后字节一致。
完整 rule sets、profiles、hints、物理来源、诊断、scaffold、任务清单、
discovery 与四种 export 模板均无未解释差异。LlamaFactory 默认 fail-on
实际 exit 1，其他项目 exit 0，符合既定 `.env.local` CRITICAL；没有
修改 pin、gold 或 snapshot。init/export 仅在一次性副本执行，完整
生成字节保全后才清理各个成功副本；原始五仓库未改动。

[跨尝试计数](r07a-gate-execution-accounting.json) 区分 155 条合格计划
命令与 157 条实际执行：质量记录容器读取和监控 argv 过长两次 helper
启动问题分别为零产品叶；独立 facts helper 未注册规则的子进程实际
exit 1 / 40.947799 秒保留，随后小型业务 fixture 的同 DRIVER 检查
exit 0 / 0.525827 秒。仅复用原始六条成功命令及同一 Git fixture，原
stdout/stderr、monitor、source/oracle/quality 摘要严格绑定，不重复计数。
最后恢复实际执行其余 149 条计划命令。合格退出分布为 154×0 + 1×1；
跨尝试为 155×0 + 2×1，unknown 为零。合格叶耗时 1048.937649 秒，
全部实际叶耗时 1090.411275 秒；wrapper 耗时独立保存，不叠加进叶总时长。
恢复与打包的 [独立只读审查](r07a-gate-independent-resume-accounting-package-review.json)
确认只改变监控参数传输和 facts helper 的必要规则注册；产品未改动。

[成对计时](r07a-gate-paired-timings.json) 保留 30 个单次观察。完整输出
零差异不代表耗时不变：LM 默认文本 current 41.080939 秒、frozen
24.430768 秒；NeurIPS export current 42.107045 秒、frozen 24.635625 秒。
两者使用相同监控 DRIVER 与等价输入/Git 状态；该单次测量不能推出无
监控性能或稳定统计值。facts current 还含两项污染控制，批次工作量与
frozen 不同，单独说明，未宣称等负载。优化不属于本轮验收范围。

下一项 R07-B 的具体 §13 patch 已获维护者明确接受，见
[决定记录](../../plan/reliability-2026-10-03/proposals/R07-B/decision.json)。
该部分产品、默认诊断与规范正文在本 R07-A 提交阶段尚未实施。
R07-C 的规则结论政策及 S3-B 的运行环境/输入时点保持各自范围。
资源 Gate B 本批不激活；历史 VAL-R01–R03 仍为 BLOCKED。
本地记录不冒充最终 main 的五平台 CI，推送后另行核对精确 HEAD。
