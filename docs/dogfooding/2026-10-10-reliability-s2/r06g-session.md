# S2-A / R06-G 公共静态内容读取边界

日期：2026-10-10。前置 main：`e9ed0991089f50ce1b3369344dda87d8c0cbfa7c`。
按 [S2 任务卡](../../plan/reliability-2026-10-03/02_Dependency_Accuracy.md#21-r06-g所有静态消费者共用的内容读取边界) 顺序执行；规范 §13、§20.2、§22。

公共 reader 在内容打开前解析实际目标并检查项目根边界，默认缓存和显式
max_bytes 均重新检查目标。合法内部 symlink、规范化内部 `..` 保留相对来源。
单次有界读取保留 UTF-8/NUL、通用换行与既有容量合同；拒绝内容仍保留
Git、文件存在和安全事实。用户 profile 共用边界，所有 profile 名称先按既有
grammar 校验，内置资源只读取 shipped names，包括自定义继承入口。

独立审查复现了 NUL 路径异常和真实 CLI profile 继承越界，两者均先 RED 后
修复。共有 42 个新 security cases、180 个 focused consumers 通过；32 次
开发命令的实际失败、退出码、时长、各步 source SHA 与日志 SHA 均保留于
[TDD ledger](r06g-tdd.json)。全部静态入口分类与缓存/竞态保证范围见
[reader inventory](r06g-reader-inventory.json)，[独立审查](r06g-independent-review.json) PASS。
检查后任何解析路径组件或最终目标被并发替换仍可竞态；本项不承诺 descriptor sandbox。

[完整质量门](r06g-quality.json) 14 项全部通过：2121 tests / 2 既有 slow
excluded / 1 既有 marker warning，总覆盖 93%，redaction statement/branch
100%，security 124 tests。pytest 318.369 秒；Ruff、strict mypy、四项生成
文档检查、十项 exported schema 完整集合及字节均通过。沿用已验证的临时
Git 2.25.1 init -b shim；[26 个冻结/依赖文件](r06g-frozen-files.json) 与前置提交逐字节一致。

五个原始固定 pin 的 SHA/origin/clean 前后相同。基础 Gate A 为 fresh
45 leaf / 180 完整比较，另有 150 leaf / 1038 检查，总计 195 qualified leaf /
1218 项全部相等；退出码 155 次 0、40 次预期 UserError 2。leaf 总时长
269.264191 秒（基础 174.157167 + consumer 95.107024）。完整报告、rule、
profile、hint、path、diagnostic 与 manifest zero delta，HarmBench 的嵌套
精确 pin 保留；pin、gold、golden snapshots 均未更新。

受影响 consumer 包括五项目完整 offline discover/profile 比较及 Git/fallback
小型子 fixture 的真实 audit default/verbose、init/L1、profile override/继承、
scanner default/capped/cache、内部 alias 和外部 sentinel never-open。
生成文件仅写 disposable roots，全部外部打开计数为 0。完整原始输出、生成
artifacts 和 harness 保留于验证存储，仓库的 [evidence index](r06g-gate-evidence-index.json)
保存 60 个可移植 JSON 的完整摘要与源字节摘要。

验证脚本两次中断（bytes 序列化、全局 -v 参数位置）与 init 成功 UI
路径的 10 项过严预期均保留原记录。独立核对 source149、规范、pins、DRIVER、
raw 摘要及实际 fixture/Git/cache 状态后复用 60 个成功 leaf，仅补 135 项。
随后按既有规范及冻结 S1-A init 输出合同精确重评首行 owned manifest 路径，
其余 stdout、全 stderr、持久化文件和所有安全断言不放宽，零产品重跑。
实际完成 196 leaf attempts / 269.830475 秒，其中 1 次错误 argv 的 exit2 / 
0.566284 秒，不计入 qualified；unknown 0。baseline wrapper 188.252262 秒
单列，不再叠加到 leaf 时长。见 [恢复审查](r06g-recovery-independent-review.json)、
[UI oracle 审查](r06g-init-ui-independent-review.json) 及 index 中的原失败与执行计数。

验证前后 149 product files inventory SHA：
`42b3c5a9cf665d468cbbae7cd4d124b63b4e662aeafca1bb674e3c3284614c0d`。
提交后以完整 Git tree 再绑定已验证字节；最终任务提交见
[commit binding](r06g-gate-commit-binding.json)。本地证据不冒充最终 HEAD CI。

下一项为 R05-A。具体 R05-S A/P+C 已获维护者明确接受，决定记录随后随
该任务的规范修订入库。include 图、同名归因、依赖 scope、静态过滤各按其
任务执行。资源 Gate B 本批不激活；历史 VAL-R01–R03 保留 BLOCKED。
