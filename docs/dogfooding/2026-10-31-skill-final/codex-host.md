本记录整理 2026-10-31 的七次真实 Codex Linux 宿主流程，均为限定范围 PASS，独立审阅发现 0 项可行动问题。完整安全字段和逐流程证据哈希见 [宿主收据](evidence/codex-host.json)。这是本轮宿主的限定范围验收；最终会话状态见[主报告](README.md)。

使用 Codex 既有登录机制与默认模型，没有复制认证材料。用户输入的 ReproLLM CLI 命令数为 0；实验命令由用户提供。首次离线安装逐项核对了 148 个 native 文件、24 个 Skill 文件及 catalog，工具环境没有加入实验 PATH。工具记录器 Python 为 3.12.14，子实验的 launch 产物自报 3.9.13；后者不代表完整实验环境证明。

| 流程 | 本轮实测结论 |
|---|---|
| 能力介绍 | 只读取 Skill 文档，项目、工具域和安装素材未变。 |
| 检查项目 | 首次独立离线安装成功；完整 12 条 audit findings 与独立预期一致。audit 自身未通过，退出 1，未运行实验。 |
| 保存并运行、导出 | 首条命令保留末尾空参数；唯一一次运行正常退出。first-report.md 与原生 helper body 字节完全一致，无手工追加。 |
| 第二次运行、比较 | 显式 argv 改为 temperature 0.4，保存的首条 0.2 命令及首份报告未变；完整 native diff 为 1 项 MEDIUM 命令变化和 4 项 NONE 身份/时间变化。无 runtime binding，不声称 generation HIGH。second-report.md 同样保持原生字节。 |
| 长任务启动 | 同一操作经过 PREPARED、STARTING、RUNNING；存在独立实际 launch 产物。capture_output=false，没有 stdout/stderr 日志。 |
| 新宿主重连、取消 | 重连同一操作，仅取消一次，无重复启动；实际子进程 interrupted/-15，操作 COMPLETED，未升级强制终止，租约已释放。unknown_descendants 保持未知。 |
| 卸载并读回 | 只移除自有环境；active 为 null、history 为空，未重新安装。三次运行、三份 launch、两份报告、保存命令、24 个 Skill 文件、31 个 wheelhouse 文件和 33 个缓存文件保留。同一操作状态和结果仍可读取。 |

本轮只观察到三次实验启动；普通两次退出 0，长任务在取消后退出 -15。实验记录不证明科学结果复现。脚本快照不可用、身份锁缺失、子实验包集合及输入消耗未验证等限制仍明确保留。信号送达、子进程退出和租约释放不能证明所有后代进程已清理；结果读回发生于 24 小时保留期内。

原 a81 尝试中，Agent 曾向正确的原生报告追加机器身份路径，该次仍保留 FAILED_HOST_ARTIFACT_PRIVACY。修订仅涉及 SKILL.md、workflows.md 与 CHANGELOG.md 的文稿约束；本轮在新域重新执行全部七流程，原生报告没有追加或改写，生成的公开产物已检查隐私。旧原始证据与失败审阅尝试均保留。

工程质量证据仍属于代码提交 a81aa7a3b2fb5b9a323ee09146dfeefa2cf47c29：24 项质量命令通过，pytest 为 6666 passed、2 deselected，五个固定项目的完整基础比较通过。文稿提交 a6f7e018b92465f6b530fe8029272abdde292736 通过桥 bd70a96b1e731c6fc7b41760cb52a4c702ce9b9c7ac86170b9fba2a9c784dbf5 绑定：15292 项 Git 身份中 15289 项未变，仅三个 Markdown 文件改变。这里没有宣称对新文稿提交重新运行完整产品质量门或资源门。

Claude Code 为 DEFERRED_BY_MAINTAINER，外部用户反馈为 UNOBSERVED；跨平台、模型或提供方 API、GPU 与付费资源另见主报告，不能由本次 host PASS 推断。同一最终交付提交的 CI 单独核对。本记录没有包含私有原始记录、机器路径、身份或登录信息，没有写入 accepted.json，也没有修改产品源码。
