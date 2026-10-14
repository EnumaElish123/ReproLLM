# S3-B / R04-B：输入基线与结束后变化

状态：IMPLEMENTED，任务提交暂定；最终共享质量门、五项目 Gate A 与精确 main
HEAD 的 CI 尚待会话验收。本报告不宣称资源验证或发布完成。

维护者已接受 R04-S 的具体规范、schema patch 和 0.6.2 → 0.7.0 两阶段合同。
R04-A 已冻结为 0.6.2 读取桥；本任务版本 0.7.0 写 run schema 2，读 1/2，
拒绝较新版本。其余九种导出 schema 字节完全不变，依赖/lockfile 不变。

输入 coordinator 在 child 启动前保留 manifest、lock、声明/argv 文件的原始
指纹、可用副本和 config bindings。manifest 解析与复制复用同一原始字节，
config 解析复用有界原始 buffer；2 MiB 上限独立于 snapshot 的大小/数量开关。
200/201 边界保留全部指纹，201 个可定位文件关闭文件副本；禁止文件不解析。
输出仍在 child 结束后按启动前声明的输出 globs 采集。

`input_capture` 明确 pre_child / post_child / unverified；变动状态包含
unchanged、changed、removed、created、unknown。后检查不覆盖 baseline，
缺失和不可安全读取分别建模。schema 对指纹、相对路径、重复路径、状态与
before/after 一致性、已有输入引用和 baseline 一致性作检查；v1 不虚构基线。

真实 stdlib child 先消费 0.1，独立写出 witness，再把配置改为 0.9；原公开
回归真实失败于记录 0.9，现 State / binding / snapshot 保持 0.1，检查记录
changed 与两次原始哈希。另一个 child 独立读取 manifest/lock/config/prompt
哈希再改写四种输入，exit 7 保持；输出 witness 在结束后采集。不可读、删除、
新建、复查失效、snapshot 关闭/超限、201 输入和安全采集失败有定向覆盖。
额外 RED 发现 baseline sanitizer 失败叠加 executable 不存在时泄漏内部异常；
现保留安全最小 failed 记录并返回既有 UserError 合同。

所有 State / consistency / diff / export / runs show 消费 typed context，
不搜索自然语言 warnings。规则比较值、严重度、last-wins 和 fail-on 不变。
四种模板把基线、结束后变动和未知消费分开；runs show 同样标注来源/时点。
原 JSON show 原始字节、list shape 与筛选行为保持。

受影响组合回归 647 项中 646 PASS，唯一 FAIL 为 legacy 导出版本标签从
0.6.2 改为 0.7.0。先在临时副本生成三份文件，完整 diff 确认每份只改变两个
工具版本标签后更新；32 项失败相关及 schema/codec 控制复查通过。真实包装、
输入 coordinator/schema/四模板组合 42 项通过；CLI/navigation 50 项通过，
最后阶段标签独立 2 RED/1 PASS → 3 GREEN。次数重叠，不能相加为测试总数。
旧隐私用例改为具体 input snapshot unavailable，并新增 hash-only/无副本断言；
所有原秘密泄漏断言保留。定向 ruff / format / 126 源文件 mypy 通过。

首次完整质量尝试为 2,624 PASS / 7 FAIL / 2 slow deselected，覆盖率 93.79%。
七项发现未纳入定向组合的旧 fixture/断言：四份 L2 金标的 EnvVsLock 说明、
一处 legacy config note、两处实际 writer 仍复用 run v1 金标。逐组核对后保留
原 run.json v1 字节，另增 run_v2.json；其原字段完全相同，四个 input checks
与独立 tracked manifest/lock/config/prompt 原始字节的 SHA 和大小完全相符。
after-run 金标因未确认的 lock producer 0.2.0 将 EnvVsLock PASS 改为 SKIP，
summary 相应 pass -1 / skipped +1；其他规则组、值/路径/严重度不变。两份
真实 v2 diff 金标只增加 pre-child scope notes。project-rules 根 timestamp/version
保留原值。49 项 fixture/core/integration 定向回归通过（25.69s）。该失败尝试
保留而不计为通过；测试/fixture 输入变化后重新执行完整最终质量门。

完整质量门以最后固定输入的通过尝试为准，结果及原日志哈希见会话报告。
五项目 pins 和独立 gold 不修改。原 VAL-R01 的 2 PASS/8 FAIL 快照保真阻塞
不属于本任务修复范围，不能用新基线合同把它改为 PASS。
