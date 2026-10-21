# 2026-10-21 · R07-C D-S / P-B

状态：**具体 D-S 已接受并实现；定向回归通过，最终会话验收正在执行**。
完整质量门、五项目 Gate A 和受影响扩展尚未执行（NOT_RUN），本临时任务记录不宣称会话已验收。
后续文稿收尾会写入实际最终结果与提交号，最终推送 HEAD CI 另行核对。整个 R07-C 仍 OPEN。

基线 `603883fd8b7c7be2eac42d335a182ff654f93918`；
P-A 提交 `7694fc8cbd4ffd20083137c34065626c96dd3f0b`。
[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/R07-C_associated_lock_structure.md)
416 文件快照及 PROPOSED 决定原字节保留，
[具体接受](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-structure/decision-accepted.json)另立记录。
用户明确接受 D-S 及具体补丁，依据规范 §§12.2、12.3.1–12.3.5。

只改 deps 的第三种内部 reason 和有限结构提取检查，继续既有 D-F 来源关联及输出。
保持部分包名信用、任一 exact/qualified 信用优先、空/null 明确兼容边界和旧 unparsed 诊断。
没有修改 env/engine/scanner/redaction/schema、锁存在性、依赖版本、原 gold 或资源验证合同。

真实 TDD：初次 RED 91 failed / 25 passed，pytest 5.16 秒、命令 6.070440 秒。
初次 GREEN 365 passed / 1 failed（pytest 36.49 秒），唯一失败是 Conda 测试夹具使用旧合同不支持的 >= 范围而预期无诊断。
只将该 fixture 行改为既有合法非 exact 的 pytorch=2、numpy=1，全部 assert 和产品/规范保持不变；原补丁和失败流保留。
纠正例在旧源码重新 RED 为 1 failed / 4 deselected，随后恢复接受源码。
最终六个完整模块 GREEN 为 366 passed（pytest 35.32 秒），受影响 Ruff/format/Mypy 通过。

Git 2.25 兼容探针曾从错误 cwd 传显式 init 目标，令隔离 worktree symbolic HEAD 指向 unborn branch。
暂停后恢复精确 codex 分支，原 index、源码及三测试修改不变，root 独立复核 main 原三项 WIP/HEAD 均不变。
原探针、恢复、纠正记录保留；实际生成器使用 disposable cwd 且无 init 目标参数，既有 shim 不改。
该准备停止不作为正式质量门失败，也没有隐藏 TDD 首次 GREEN 的实际失败。

本轮资源 Gate B 为 NOT_APPLICABLE：普通规则政策不激活里程碑或 release；不运行 GPU/Hub/付费请求，不发布 tag/PyPI。
下一步在相同已提交输入执行一次完整质量门，再执行全部五项目基础门与 affected init/L1/export，归档后推送 main。
