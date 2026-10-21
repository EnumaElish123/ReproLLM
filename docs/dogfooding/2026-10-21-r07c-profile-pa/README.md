# 2026-10-21 · R07-C profile absence / P-A

状态：**P-A 具体提案和证据已准备；局部政策 PROPOSED，P-B 未实施**。
起点 `bb98e67c6e108822c62842d738f42af2eda871e4`；隔离分支 `codex/r07c-profile-proposal-20261021`。
本轮保留 main 原 README、docs index 修改及额外案例草稿，不纳入提交。

## 任务与交付

按 [05 §5](../../plan/reliability-2026-10-03/05_Policy_and_Compatibility.md)继续 R07-C 已登记的
非空 absence / mixed evidence 范围。[具体提案](../../plan/reliability-2026-10-03/proposals/R07-C/profile-absence/R07-C_profile_absence.md)
推荐只在 declared-but-undetected 分支遇 primary-Python gap/unavailable 时逐 profile SKIPPED/INFO，
保留有实际检测证据的 high/shipped 未声明 FAIL、旧 empty-result veto 和完整视图有界合同。
[具体补丁与待决记录](../../plan/reliability-2026-10-03/proposals/R07-C/profile-absence/decision.json)
只涉及拟议规则、规范、CHANGELOG 及两份测试模块，不改 engine/registry/pyscan/redaction/schema。
全部补丁仍未应用。既有局部 A 的接受不自动授权本次规范变化。

## 已执行与未执行

| 检查 | 实际结果 / 边界 |
|---|---|
| 当前 / 条件观察 | 16 API 输入＋4 CLI 输入，各 baseline/conditional，40 次真实产品观察；20 份完整 JSON strict 比较通过，无字段豁免 |
| 门的独立验证 | 单一目标规则夹具无其他失败遮蔽：WARNING / CRITICAL 的 gap 门 1→0；suppression 0→0；complete absence 1→1 |
| 正向 / 混合 / 不确定 | cap 内真实 peft witness 保留；cap 外 vllm、read/parse gaps、unknown/invalid、多个 profile、dependency/README/自定义见证按预写映射处理 |
| 来源保全 | 全部 8,602 个原 tracked 文件 / Git blob、61 份合成输入逐字保全；40 次 worker 单次耗时与退出码保留 |
| 五项目影响设计 | 71 份仓库报告/manifest/export来源、36 份 pinned 上游来源、105 个完整检测见证核验；普通 L0/L1/default export 预写零 delta。不是 fresh Gate A |
| 未应用测试草稿 | 18 新参数化用例 / 6 函数 / 2 文件，另修订既有 legacy absence row；AST、Ruff/format、apply-check通过，无 pytest / RED/GREEN 主张 |
| 独立复核 / 读回 | 条件结果、原流、source/input guards、proposal/patch/test/portfolio 范围复核无阻塞；分享版 198 文件、266 原始来源完整读回 |
| 本地 full quality / Gate A / Gate B | NOT_APPLICABLE：本次仅新文稿、未应用补丁和条件设计证据；不更改正式产品、测试或工具。P-B 接受后再执行其完整门 |
| 最终 CI | 推送后的实际 main HEAD 单独核对，不以原 bb98e67 的成功替代 |

[完整条件证据](../../plan/reliability-2026-10-03/proposals/R07-C/profile-absence/observations/results.md)
区分 fixture timestamp 与实际单次耗时；API 的完整 expected 在 worker 后仅由 baseline＋预写差分派生，
CLI 补段在 conditional 前写入；不声称所有精确 expected 文件都早于运行。
比较器的 20 次耗时没有记录，不冒充已知。conditional 仅进程内替换单一规则类，无代码落地、
网络 / GPU / provider / native child / 凭据使用，也不绑定新的资源通过结果。

首尝试已完成 32 API，但 CLI launcher 错将包装函数当成 Typer app，在命令进入前失败。
保留该 attempt 为 partial / failure，原 stdout / stderr 与 source/input postguards 完整保留；
唯一 main.cli→main.app 辅助纠正后，只补 8 CLI，不重复合格 API。
另有纯工具的 CHANGELOG anchor、旧 expected value-wrapper 和 Ruff 格式预检纠正，均保留其资格与原哈希。
这些不改变产品、独立预期或历史记录，也不把失败改写成 PASS。

## 兼容代价与接续

新 SKIP 不接受 FAIL-only severity override，用户提升后的 WARNING/CRITICAL 门可能放宽；
对无 AST signals / 空 detect 的 profile 也保守 SKIP，不建立逐 profile 充分证书。
完整 primary-Python view 仍非其他检测域或整个实验完整证明。suppression 延用既有所有 status 合同。
依赖 absence、listing/framework/config/README 充分性和更广 R07-C 保持 OPEN；原资源 metadata 缺失、
HF403、历史 native/judge 候选归属不变，不授权发布。

需要维护者接受具体局部 P 与规范 patch 后才实施 P-B，依据执行总则 §5.9 及原接受记录的范围边界。
接受后先 RED→GREEN、单次最终 full quality，再五项目 fresh L0、一次性 init→L1、default export 与
完整独立比较，提交推送 main 并确认最终五项 CI。原提案与本次 PROPOSED 快照保持原字节。
