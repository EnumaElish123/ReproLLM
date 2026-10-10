# S1-B / R02-R run 捕获脱敏

日期：2026-10-10。前置 R02 提交
`2a025afc8f0204f350df7dd07c50592418791fc3`，其 148 文件 byte binding 见
[R02 commit binding](r02-gate-commit-binding.json)。按
[R02-R 任务卡](../../plan/reliability-2026-10-03/01_Persistence_and_State.md#41-r02-rrun-结构化值与文本快照的密钥脱敏)
实现，不使用 lock 的拒绝回归替代真实运行验收。

## 行为与安全边界

普通密钥经 mapping/list 的原始键上下文识别；绑定叶子使用 field 和实际
config key / CLI flag 的上下文。RunRecord 的 typed metadata 单独处理，
不把绑定来源、schema 字段或 `{present: true}` 当密钥值。
JSON/YAML 的 quoted/escaped key、flow/list/block/anchor 与 patch/log fragment
按原始 scalar span 处理。TOML 使用既有 stdlib/tomli 解析器，覆盖普通、引号、
点分隔及数组表、inline container、multiline string，并核对替换后解析树。
安全值和类型保持，不能核对的敏感片段不回退保存原文。
沿用 §16.2 六种 generic_kv 别名和至少八字符值，
不修改规范 regex 或扩展为任意 secret 格式。

所有新 run 产物在写入之前完成脱敏，包括 record、manifest/legacy lock、声明
文件、patch、saved argv 和 stdout/stderr。保留 benign 字节和 scalar 类型；
原始文件哈希与脱敏快照/标记分开。原始 child argv、环境及终端输出保持。
适用范围是新写入，不自动重写旧产物；替代值不宣称为原始可执行参数。

捕获/脱敏失败使用固定无原值 warning，不能回退保存原文。
输出保存失败后仍排空并转发 child 输出；完成后 sanitizer 失败保存已安全
初始记录的最小 completed/interrupted 副本，保留 child 实际退出码。
永久文件系统 replace 失败仍可能只留下此前安全记录；返回值保留 completed
状态及失败说明，不声称无法写出的最终状态已成功落盘。
未触及 D-41 文件、schema、依赖、漂移 severity 或一致性规则。

## TDD 与质量

真实 stdlib child 读取 `config.json:settings` 并提供独立哈希 receipt，绑定
`custom.settings` 与秘密叶子；扫描整个 run 目录。对精确 R02 HEAD 首先取得
有效 RED：21 failed / 1 passed / 1.21 秒，包括退出 7、泄漏和输出故障断管。
修复后覆盖 snapshot/output 开关组合、JSON/YAML 各表示、argv 两种形式、
metadata、provider corpus、正反例、失败时最小记录及临时文件清理。
before-child 脱敏无法完成时，安全 UserError 阻止启动，不回显输入。

新增 contextual parser 会在不安全歧义时拒绝捕获；R02 writer 的对象隐私检查
原先位于异常转换之外，consumer 回归实际复现 CLI exit 3。将其移入既有
validation try 后，lock 继续以 UserError / exit 2 保全旧字节；该兼容修正
由本任务的新失败行为触发，不扩大 freshness 或 writer 功能。

独立复核用真实 child 追加三项安全回归：YAML indentless secret sequence，
secret block 中短于 generic 门槛的 PEM body，以及 argparse 实际接受的负数
形式 password。保存 argv 的安全上下文独立于 observation 的 §15.1 token
解析边界；不以此次修复改变后者。流式处理先保留原始 PEM 边界供公共
redact_lines 消费，再处理安全输出的键上下文，防止先改 BEGIN 导致 body 泄漏。

后续真实运行复核补充 TOML 表上下文在 snapshot、stdout/stderr 和 dirty patch
中的传递；普通/quoted/dotted/array 表、inline container 与 multiline 值均
验证原始 child 输入和安全输出。JSON 密钥片段的注释与键位置也独立检查，
不能只依赖解析后的数据树，因为解析器会丢弃注释。
未闭合 PEM 分别在快照和绑定 observation 验证：处理 decoded scalar 中的
原始边界之后再应用键上下文，保留独立的 `max_tokens` sibling。
真实 Git hunk 没有 TOML 父表上下文时采用有界安全失败，不能保存原文补丁。

定向矩阵：213 passed / 12.52 秒；独立 security selection：82 passed /
1984 deselected / 7.46 秒。六组有效 RED/GREEN 与精确命令、原始日志 SHA
见 [TDD evidence](r02r-tdd.json)。
独立审阅另执行 22 次真实包装运行，全部保持 child exit 7、原始输入/终端、
原始文件哈希及 source key；全部 owned 文件无明文，实际写出的快照保留
预期 benign 结构。具名安全失败包括部分 TOML 流、不能确认来源的 TOML
patch 与不安全键语义；不能把省略的捕获标记为完整内容已保存。
见 [independent approval](r02r-independent-review.json)，其 source SHA 与
最终被测五个 source 文件逐字节一致。

全量质量门共 14 项全部通过，见 [quality evidence](r02r-quality.json)：
2064 passed / 2 slow deselected / 1 既有 slow marker warning，pytest 用时
313.623 秒，总覆盖 93.00%；redaction statement/branch 覆盖 100%；
security 82 passed / 1984 deselected。Ruff check/format、strict mypy、四项
生成文档 freshness 均通过，十项 exported schema 的完整集合与字节完全相同。
沿用 S1-A 已验证的临时 Git `init -b` shim 兼容本机 Git 2.25.1；没有修改
系统 Git、仓库实现或依赖。未为此次任务扩大默认 slow 测试范围。

## 五项目 Gate A 与消费者

质量门通过后完成五项目 Gate A：185 条独立 leaf 命令（45 baseline + 140
lock/consumer），180 项 baseline 完整 gold 对照 + 618 项扩展检查，零产品/gold
delta。qualified exit 分布：145 exit 0、35 预期 security exit 2、5 保持 child
exit 7。baseline 子进程合计 159.233013 秒，扩展 183.568699 秒，共
342.801712 秒。命令、pins、退出码、耗时、完整 expected/actual 与索引见
[Gate A summary](r02r-gate-summary.json) 和
[evidence index](r02r-gate-evidence-index.json)。

初次执行在 FastChat 临时副本准备时，`.gitignore` 忽略合成配置，`git add`
失败。只对本次 owned fixture 使用 force-add；产品无修改。通过核对 149 个
产品文件、规范 hash、五个 pins、既有对照与 fixture/probe/consumer oracle，
复用已通过的 45 条 baseline 及 28 条 lm-evaluation-harness 命令，修正尝试
新增 112 条命令；两次实际执行共 203 条 leaf attempts / 358.968852 秒。
失败尝试与修正没有作为产品通过证据丢弃，见
[harness correction](r02r-gate-harness-correction.json) 和
[qualified reuse](r02r-gate-qualification-reuse.json)。

Gate 前后产品 149 文件完全相同，inventory digest
`e4cf045b2a45f6d9e4b6ad134d13f7459007a989e586252cadf1a740ce0cb4dc`；
五个原始 checkout 的 SHA、origin、tracked/untracked clean 状态不变。
基础完整 gold 与 pin 不变。RunPrivacy 变更会影响 R02 writer，因此本任务再次
执行相应 lock 安全回归。run/diff/export 采用一次性 clone 内的真实 stdlib
child，未经网络、GPU 或付费资源；不把这类合成运行计入 resource Gate B。

不同原始秘密统一成为安全标记，diff 不宣称恢复其值差异；原始文件哈希仍能
反映字节差异。完整 export 和 run 目录仍检查两份原始值均未出现。
当 manifest 声明整对象且 observation 又投影父对象时，已有 State parent/child
路径冲突不属于本任务；consumer fixture 分别声明和绑定字段，避免混入 R03
或后续 scanner/bindings 改造。

本报告冻结提交前证据。R02-R 独立 commit、精确 source byte binding、main push
及远端 CI 在各自完成后核对；下一任务 R03 只改变有效 CLI 选择及合并，保留
任何 observation 与声明冲突的既有一致性语义。
