# 2026-10-21 · R07-C D-F / P-A

P-A 的具体方案、原 PROPOSED 决定及全部预期保持准备时快照；维护者随后已明确接受 D-F 与具体补丁，P-B 接续实施。
基线 `60aa97f91b09c56e118c434c954ebc451679423e`。本提交归档提案和准备证据，尚未应用产品、规范或测试补丁。

[具体提案](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/R07-C_associated_format_lock_failures.md)、
[完整实现差异](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/implementation-proposed.patch)、
[具体规范](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/spec-proposed.patch)、
[原决定快照](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/decision.json)。
仅对已捕获的现有 R06-B 合格声明/import 来源关联到已知读取/解码失败格式锁的待警告包 SKIPPED/INFO，独立于 Python coverage；
exact/qualified 信用优先，既有 D-L 及其他警告保留。None 只表示未登记两种失败，不是完整 grammar 证书。

[25 组条件对照](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/observations/README.md)
实际完成 50 workers（22 API / 3 CLI 输入各执行 baseline/conditional）、25 份 T-02-only 完整 JSON 比较、175 条命令及 350 次产品只读 Git 查询。
首次正式执行通过，墙钟 54.086346 秒、命令合计 52.354039 秒。完整 expected 在相应 conditional 之前由 baseline 与固定转换派生，
没有从 conditional 输出复制业务预期。CRITICAL 1→0、混合 WARNING 1→1、suppressed/never 0→0。
[独立实际复读](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/review-actual-final.json)
重建所有 25 份 expected 并递归严格核对类型/键/顺序/值；210 归档文件、159 有限唯一 JSON、486 原来源、原流/输入/查询/隐私核对通过。
9,869 个原 tracked blob、拟议两源和三项 main WIP 保持。条件执行只做双源进程内替换，不是应用补丁或正式验收。

[五项目来源](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/portfolio/README.md)
重新核验 lm-evaluation-harness、FastChat、LlamaFactory、HarmBench、llm-dp-finetune 的固定 SHA、origin、干净状态和完整路径。
无四种格式锁，预写完整结果零差异。43 次只读 Git 查询、210 仓库来源及完整历史 L0/L1/facts、15 初始化文件、五份导出绑定。
这些是旧 oracle 资格与独立影响设计，**fresh Gate A NOT_RUN**。

[74 项测试草稿](../../plan/reliability-2026-10-03/proposals/R07-C/format-lock-read/tests-proposed.patch)
有 15 个新函数，71 个旧函数 AST 与文本不变。Python 3.10、逻辑文件名 Ruff、format、apply-check 通过；**RED/GREEN NOT_RUN**。
源码/规范、观察/测试草稿、打包工具和实际证据分别经独立复核。[文稿检查](document-checks.json)核对原 236 文件提案包、235 checksum 条目、176 严格 JSON 和 22 手写链接。
完整产品质量门和 fresh Gate A 在本 P-A 文稿阶段为 **NOT_APPLICABLE**；P-B 会对最终产品重新执行，不将条件结果升级为验收。

静态准备停止记录均保留：CHANGELOG 标题唯一性假设、观察工具 deps 哈希常量笔误、外部测试路径 first-party 分类提示。
未改变业务预期，没有失败的正式观察或打包尝试。仅修正文稿的上轮五项目名称误写：实际原归档一直是 LlamaFactory/llm-dp-finetune，
其原始数据和哈希未改；见原报告的明确勘误。

本批不触及 engine/redaction/schema，不扩大预算、不改 manager/项目关联、规则 ID、severity 默认值、存在性或 gold。
孤立 WARNING/提升 CRITICAL 门可以 1→0；默认文本可能显示 Findings: PASS 并列 SKIP，默认 export 不列 SKIP 数，完整 JSON 保留未验证项。
一般依赖/requirements、错误结构/部分提取、未捕获 import、listing/README/config/framework 和更广充分证书仍 OPEN，整个 R07-C 未关闭。
GPU/Hub/付费/原生 Gate B 未激活，历史结果归原候选；未发布 release/tag/PyPI。原三项 main WIP 排除在提交之外。
