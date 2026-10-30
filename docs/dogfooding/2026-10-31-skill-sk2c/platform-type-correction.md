# SK15 平台类型检查修正

`ea0a7dc` 的[正式 CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/41118259829)
三项 Linux 成功，Windows/macOS 在类型检查失败。原始失败保留。
最终产品修正 `fc44c2de7d06119b738e7868cbca69d49aeaba3c` 的本地验收已完成，
本报告推送后再核对同提交五项 CI；本地类型模型不替代实机 CI。

依据：SK15、规范 §22、[验证工作流](../../plan/validation-workflow-2026-10-13.md)。
只修改 operation helper 的平台类型声明和四项针对性测试，不改 native 源码、依赖、schema、
规则、gold、安装 catalog 或 Windows/macOS 后台支持边界。

可提交[收据](evidence/platform-type/receipt.json)与[证据索引](evidence/platform-type/evidence-index.json)
引用一次保存的完整原始输出、命令、退出码、耗时、失败与保全 hash。

## 原因与修正

已匹配的锁定依赖下，Windows 类型模型出现 12 项错误，macOS 模型出现 3 项错误：
Linux 专用的 no-follow/nonblocking flags、uid、file lock、pidfd 和信号接口虽受运行平台门保护，
静态类型检查仍检查这些访问。模块导入和只读功能必须能在其他平台工作。

修正使用仅参与类型检查的三个小 Protocol 和惰性模块 identity cast。
常量、函数、参数和调用顺序仍为原 `os`/`fcntl`/`signal` 对象；没有 flags=0 回退，
没有忽略整个模块或降低 mypy 严格度，也不在导入时解析 Linux 属性。
六个受改函数去掉 identity cast 后 AST 与原版一致，另 37 个函数 AST 完全相同。

四项针对性测试覆盖非 Linux 导入/状态不访问专有属性、缺少必要属性继续拒绝，
以及已核对 pidfd 的精确调用。修正前模型错误、修正后模型通过和 Linux 行为证据分开保存。

## 最终验收

| 门 | 结果 |
|---|---|
| 完整质量门 | 24/24 PASS；6,193 测试，无失败/错误/跳过；24 次来源校验；15,259 个输入前后相同 |
| 新鲜五项目基础门 | PASS：50 次命令、31 项检查、10 份完整 L0/facts JSON |
| Linux/Windows/macOS 类型模型 | 三者锁定严格检查均通过；不计作后两者实机运行 |
| 正式隔离离线安装 | 新环境由 installer 创建；33 个缓存 hash、148 个 native 源文件及 wheel/来源证明通过，无 venv 复制 |
| 五项目受影响操作 | 130 次进程调用；其中 85 次无插桩最终入口调用、15 次原生 CLI、10 次 typed reader、20 次 clone/checkout；全部通过 |
| 保全 | 原五项目 pin/origin/clean、九份维护者 WIP、开发环境及 927 项模型环境 metadata 均不变；自有 worker 已结束、lease 为零 |

每个固定项目均核对：缺失 lock/check 的原生与 helper exit 1；101 MiB 本地合成权重的真实 hash
及完整原生 lock 对照；PREPARED 不启动/不写入；启动、状态、结果和同 ID 去重；
manifest 变更触发的严格 stale exit 1/完整有序原因；自有 32 GiB sparse hash 运行后取消，
保留旧 lock 的全部字节。合成文件不代表模型推理。

本次影响层只重跑实际修改的 operation 路径，并在全部五项目执行新鲜基础门。
原 C 的 init/export/rules 函数及其消费路径未改；[原 80 项完整矩阵和 56 次实际入口](README.md)
作为有来源的未变业务历史证据，不重新计作当前候选的新鲜调用。

第一次操作矩阵的验证器错误地用本地模型 config 变更触发 staleness。
原生和 helper 都正确返回 up to date；现行 `lock --check` 比较 manifest/project-rules，
并不重读模型内容。保留这轮 21 次调用和失败后，仅修正一次性 fixture，
使用 manifest.project.name 变化，在新的五组副本完整重跑。未修改产品或放宽断言，旧调用不重复计数。

本会话零网络解析、凭据、推理、训练或 GPU 消费。在线/发现/实验/真实宿主仍由后续批次单列验收。
修正后的实机 CI 是推送后的独立门，不能用上表的模型检查代替。
