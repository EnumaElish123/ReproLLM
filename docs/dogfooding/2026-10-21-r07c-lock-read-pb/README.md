# 2026-10-21 · R07-C D-F / P-B

状态：**具体 D-F 与补丁已接受并实现，定向回归通过；最终完整质量门、五项目 Gate A/受影响命令及本轮最终 HEAD CI 待执行**。
基线 `60aa97f91b09c56e118c434c954ebc451679423e`；P-A 固定快照 `544c105d00b3bb3d14600d7b9e01a7d875f0416a`。

[具体接受记录](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/decision-accepted.json)
承接[原提案](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/R07-C_associated_format_lock_failures.md)；
原 PROPOSED 决定和 236 文件 P-A 快照保持原字节，接受另立 sidecar。
只在现有 in-use 包没有 exact/qualified 信用且具备现有 R06-B 合格捕获来源关联的格式锁有已知 body-read/decoder 失败时，逐包 SKIPPED/INFO。
D-F 独立于 Python coverage、先于现有 D-L。无关联/错误 manager/被近根或 barrier 阻断者、有效空锁和非 member 继续旧行为。
仅改 deps 的 typed known-failure、等价共享来源关联及 env 的该分支；无 engine/scanner/redaction/schema/profiles/依赖/版本或 gold 改动。

[TDD](tdd/summary.json)：旧实现 **60 failed / 14 passed / 100 deselected**，pytest 6.62 秒、墙钟 7.514030 秒，
均为预期的新 known-failure 属性、SKIP 字段或退出码差分，无收集/导入/NameError。应用接受的四份补丁后，
env rules、deps、engine、audit、export、scan diagnostics 六个完整模块 **257 passed**，pytest 69.83 秒、墙钟 70.751497 秒。
74 项新验收 / 15 函数，71 个旧测试函数 AST 与文本不变；五个触及文件 Ruff/format、两源 Mypy 通过。

最终适用矩阵为 fresh 五项目 L0/完整 facts 和独立 oracle；各一次性 clone init→L1→default export，完整三初始化文件（含隐藏文件）、JSON 与 Markdown；
四组完全保持 P-A 字节的专项完整 JSON（关联语法失败、混合 WARNING、无关联失败、有效空锁），另一次关联失败默认 export 只验收预写 summary/notable 语义并保留全文。
五个固定项目为 lm-evaluation-harness、FastChat、LlamaFactory、HarmBench、llm-dp-finetune，均无四格式 lock；完整 gold 预写零差异。

已知失败只包含 read_text None 和现有捕获的 decoder 异常；None 不证明 grammar 完整。错误结构/部分提取、一般依赖/requirements、遗漏 import 来源、listing/README/config/framework 与广义证书仍 OPEN。
INFO/SKIP 不受 FAIL-only override 提升，孤立 WARNING/CRITICAL 门可 1→0；混合警告和 suppression 保留。
默认文本可显示 Findings: PASS 并列 SKIP 数，默认 export 不显示 SKIP 数，完整 JSON 保留未验证项。整个 R07-C 未关闭。

GPU/Hub/provider/付费/原生 Gate B **NOT_APPLICABLE**：普通规则政策不激活新里程碑或发布；历史结果归原候选。未发布 release/tag/PyPI。
本批同时明确更正上轮人类报告中两个项目名称误写，原实际项目、产物、hash 与 gold 正确且不变。
P-A 归档检查先后遗漏了标准 patch 空白上下文和末尾空白上下文的例外，原失败与后续全量 committed readback 均在会话外部记录；
原标准补丁和原始观察流不改写。其他准备停止记录亦保留。最终质量门、完整比较、归档耗时和精确 main HEAD CI 将在本轮收尾填写；
main 原三项 WIP 不纳入提交。
