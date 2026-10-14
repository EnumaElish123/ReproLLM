# S3-B / R04-A：来源说明与 0.6.2 读取桥

状态：本地共享验收通过。任务提交 `a9a3942651901cc2450ec01b0881cd76140000bd`；
最终质量门、五项目 Gate A、冻结桥实装兼容证据共同覆盖 R04-A / R04-B，见
[会话报告](README.md)。推送后的精确 main HEAD CI 由最终回复核对。
本记录不宣称 VAL-R01 或发布验证完成。

R04-S 的具体规范、run/State schema patch 和两阶段版本方案已于 2026-10-14
得到维护者明确接受，见[提案](../../plan/reliability-2026-10-03/proposals/R04-S/R04-S_runtime_evidence.md)。
任务顺序仍为 R04-A → R04-B；0.6.2 桥保留 run v1，仅下一个 0.7.0 任务写 run v2。
没有新增重依赖、child 解释器探针、engine 政策或 core/redaction 修改。

真实 child venv 的 dist-info 元数据为 torch 0.0.123、实际 torch 模块不存在，
recorder 包集合为空；子进程内部 OMP 从 2 改成 3，而记录保留继承基线 2。
来源缺失的公开回归先失败，环境与 State context/往返的 11 项回归后通过。
集中 registry 分别用历史 run 和 lock 源码确认九个具体 producer，新增桥合同；
未知、custom/local producer 保守 unknown，旧文件字节不改。

EnvVsLock 保留已知 recorder 差异 WARNING、单侧缺项 INFO，匹配 PASS 限定
recorder 元数据；未知/不兼容 SKIP。四模板按每个实际 effective leaf 保留来源，
不能用 run Python 的时点概括来自 lock 的包或硬件。Diff 仍比较原有效值和严重度，
使用已有 note 限定观察范围；等值文本不宣称 child 环境或消费已验证。

读取桥的公开两轮 TDD 为 4 RED→4 GREEN 和 8 RED→17 GREEN；额外整数控制
证明旧 parser 可把 true/1.0 接受为 schema 1，现明确拒绝 supplied 非整数版本。
新 codec 模块共 27 项通过；缺失 schema 字段的原 legacy 默认不变。所有显式
runs/diff/export 更新版本错误都给安全升级提示；list 继续 warning/skip，export
不再把较新格式报内部错误。真实旧 0.6.1 限制保留在提案兼容矩阵。

任务组合定向回归：**388 passed、1 deselected，15.01s**；排除的是尚未实现的
R04-B consume-then-rewrite 回归，该用例此前已真实复现 0.1→记录0.9。
受影响源码 mypy 通过；最终格式/生成文档检查及完整质量门以会话证据为准。
source/phase 的消费者另有 53 项通过、diff/reporters/CLI/fixtures 327 项通过。
这些是有重叠的检查，不能相加为独立测试总数。

三份 State snapshots 的全部非-context 字段、原参数/来源/alternatives 完全相同；
仅加入批准的 context。三份 export snapshots 先生成在临时副本，完整 diff 确认
只改变 scoped 文案、可用平台/OS 信息和桥版本，身份/参数/code 段完全相同后更新。
diff snapshots 只修改固定 unverified 说明、scope note 与 recorded-values verdict；
既有值、路径、严重度、计数与排序保留。五项目 pins/gold 未修改。

最终共享证据将收录命令/退出/耗时、原日志 SHA、完整 snapshot 审阅及冻结桥 wheel。
GitHub issue 当前没有已验证的 authenticated 写入能力，具体 spec issue 草稿已保存，
不虚称远端 issue 已创建；维护者的具体决定已记录。资源 Gate B 本工程会话不激活，
原 VAL-R01 snapshot fidelity 的 2 PASS/8 FAIL 和阻塞状态保留。
