# S1-B / R02 lock 持久化检查

日期：2026-10-10。前置提交为 `834db1951d771c16c641a23c29a650bb8b075698`，
续接 [S1-A 报告](../2026-10-10-reliability-s1a/r01-session.md)，按
[S1-B 任务卡](../../plan/reliability-2026-10-03/01_Persistence_and_State.md#4-r02lock-的持久化安全检查)
完成 R02。R02-R 和 R03 独立验证、独立提交。

## 行为与边界

writer 在创建临时文件之前检查最终 Lock JSON 对象及完整 YAML。
共享纯函数保留原始 mapping 键上下文，递归检查列表和嵌套对象；复用 §16.2
六种 generic_kv 键别名及至少八字符的匹配值，不宣称识别任意未知密钥格式。
RunPrivacy 保留既有 provider/JWT 等值模式、路径及机器身份检查。
新增明确拒绝绝对本地 `file://` URI，HTTPS URL 仍允许。

完整 YAML 必须重新解析为同一对象，以 canonical JSON 比较保留标量类型。
检查文本中只屏蔽已单独检查的 mapping-key 语法，保留所有值、注释和换行，
避免 `password` 容器下的 `max_tokens` 被跨行误认为密码。
实际写出字节不改变。已有临时写入、flush/fsync、replace 和清理机制复用。

不安全输入返回 UserError / exit 2；诊断只给 `reprollm.yaml` 修复动作，不回显值。
旧 lock 字节完全保留，且检测发生于 mkstemp 之前。
凭据应移至 child 自身读取的环境或安全机制，未增加 manifest 插值。
原始 prompt 只进入哈希时不检查其正文。`lock --check` 仍只判断既有 freshness；
没有清理或重写历史 lock，没有 unsafe 开关、schema 或依赖变更。
未修改 `core/redaction.py`、`core/engine.py` 或 schema，不触发这些文件的 D-41 审阅。

## 回归与质量

公开 writer 的普通 keyed-secret 回归首先 RED（未抛 UserError），随后 GREEN。
独立审阅追加 safe nested-container、绝对 file URI 和 serializer 引入带引号
secret key 的回归，分别取得有效 RED 后修正。安全输入精确比较 dump_yaml 字节，
失败输入比较旧 lock 字节；mkstemp 故障哨兵证明检查先于任何临时创建。

覆盖 inference/training/privacy 自由参数、nested dict/list、secret dict key、
provenance note、provider/JWT、POSIX/Windows/UNC、机器身份、真实 CLI exit 2、
安全模型 ID/HTTPS/relative path/glob/closing token/max_tokens、短值及 hash-only prompt。
原子 replace 失败回归继续通过。最终定向 **110 passed / 9.94 秒**。

最终完整质量结果见 [r02-quality.json](r02-quality.json)：14 条命令全部 exit 0；
**2,008 passed、2 deselected、1 既有 warning，总覆盖 93.00%**；redaction 分支
覆盖 100%，security 29 passed，Ruff check/format、Mypy 121 源文件、四份生成文档
freshness 和 10 份 schema 完整集合及字节一致检查全部通过。
全量 pytest 耗时 306.511 秒；完整命令耗时及原始日志摘要哈希保留于 JSON。
延续 S1-A 验证的临时 Git 2.25.1 `init -b` 兼容 PATH；系统 Git、依赖和仓库脚本
没有改动。保留既有 slow marker 警告和默认 slow 排除策略。
没有重生成 fixture、snapshot 或 schema。

## 五项目与交接

质量门之后的五项目 Gate A 全部 PASS：基础 45 命令 / 180 完整比较，另有
86 条扩展 ledger 记录（其中一条为基础 wrapper）/ 152 检查，合计实际
130 条 leaf 命令 / 332 比较，零 gold delta。
基础子进程耗时 157.827887 秒，包含扩展的总耗时 254.908065 秒。
完整证据见 [r02-gate-summary.json](r02-gate-summary.json) 及
[r02-gate-evidence-index.json](r02-gate-evidence-index.json)。
验证包含全部五项目离线 lock、check、完整 timestamp-normalized 重复输出，
嵌套/键名/普通密钥/已知模式/绝对路径拒绝、training/privacy 参数及 hash-only prompt，
旧 lock 字节、诊断与临时文件检查，以及旧锁 freshness 不自动升级成秘密扫描的合同。
五个原始 checkout 前后均为正确 pin、origin 存在且 clean。
148 个产品/schema/dependency 文件前后 inventory 相同，摘要为
`a6f3fa8551ef95a98c10891f1747361d8d16df876018eb68f8c23dca10b220ba`。
未从当前 ReproLLM 输出更新 pin 或 gold；完整 L0/L1 findings、profiles、hints、
paths/lines、diagnostics 和 generated manifest 比较均沿用已审阅 oracle。
原始 pins 不变，所有 mutating 命令限一次性 clone；完整 gold 不从当前输出生成。
本次普通可靠性任务未激活 milestone/release Gate B，
[资源验证记录](../pending-resource-validation.md) 的 BLOCKED 不计通过。

本报告冻结提交前证据；包含本报告的独立 R02 commit 之后验证 source-byte binding。
main 推送和精确 head 的远端 CI 待 S1-B 三任务完成后执行，实际哈希和结果由最终
交付记录提供。下一任务 R02-R 必须经真实 child 检查整个 run 目录，不能以 lock
拒绝测试替代运行捕获安全验收，也不能改变已完成 child 的退出码。
