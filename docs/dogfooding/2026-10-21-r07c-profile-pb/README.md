# 2026-10-21 · R07-C profile absence / P-B

状态：**具体局部 P 已接受，产品与定向验收通过；最终共享质量门 / 五项目 / CI 待执行**。
源码起点 `bb98e67c6e108822c62842d738f42af2eda871e4`；P-A 快照
`36ea937c8b45039a5b1c61769b55eb6bdde631b5` 保留。

维护者已[明确接受局部 P 及具体补丁](../../plan/reliability-2026-10-03/proposals/R07-C/profile-absence/decision-accepted.json)。
只在 `exec.profile_detection_mismatch` 的 declared-but-undetected 分支遇既有 typed primary-Python
incomplete / unavailable 结果时，逐 profile 返回现有 SKIPPED/INFO 和固定新文案 / field evidence。
已检测到的 high/shipped 未声明 FAIL、完整视图旧 absence 合同、旧 empty-result veto 均保持。
不改 engine、registry、pyscan、redaction、schema、profiles、依赖或版本。
原 P-A proposal、PROPOSED 决定、全部观察/预写预期与历史报告原字节保留，接受记录另立。

[先测试证据](tdd/summary.json)：旧实现 17 failed / 6 passed / 26 deselected，均为预期的新状态 / 文案 / 门差分；
应用接受补丁后，engine / exec rules / audit CLI / default export CLI 四模块 **76 passed**。
新增 18 参数化案例并修订一条旧 absence case，覆盖 cap/read/parse/unavailable、多 profile、
完整/零候选控制、混合真实违规、WARNING/CRITICAL 阈值、JSON/schema、重复、默认诊断、文本、suppression、export 和只读。
受影响三文件 Ruff / format 与单源 Mypy 通过。首次共享门发现两条旧 scan diagnostic export 测试与新规范冲突，未通过（3203 passed / 2 failed）；
[诊断及夹具补正](diagnosis/summary.json)保留失败身份。仅在该旧测试的已选文件固定 evaluation + finetuning 正向信号，
保留全文字节与诊断断言；整模块 **44 passed**，产品及原接受补丁保持不变。最终共享门须在最终候选重跑。

| 改动 | 最终适用验证与独立预期 |
|---|---|
| profile absence 局部分支 | fresh five-project L0 + complete detection/hints/deps/paths/diagnostics 与既有独立 oracle 零差异 |
| L1 / init / 默认 export | 五个一次性 pinned clone 各 init→L1→default export；三生成文件和完整 L1/export 对 P-A 预写零 delta |
| 五项目未进入的缺证据分支 | 真实默认 500/501 边界的隔离 audit：missing/mixed/complete/suppression 完整报告；额外默认 export 的确切摘要与 notable 语义 |
| GPU/provider/Hub | NOT_APPLICABLE：普通规则政策切片，不激活新里程碑/release；旧资源成功和阻塞继续绑定原候选 |

新 SKIP 不接受既有 FAIL-only severity overrides，缺证据 finding 原被提升为 WARNING/CRITICAL 时可从 exit1变0；
真实高置信度违规仍可触发相同门。空 detect / 无 AST signals 的未检出 profile 也保守处理，
不构造逐 profile 充分证书；完整 Python 视图不证明全检测域或实验执行完整。
广义 R07-C 的 dependency absence、listing/framework/config/README 覆盖及证书仍 OPEN。
原 metadata 输入缺失与 HF403 保持，不宣称同候选完整发布矩阵完成，不发布 tag/release/PyPI。

最终质量、五项目和 consumer 完成后补充精确候选、命令/退出/耗时、完整比较和归档核验。
main 原三项 WIP 保留原字节；最终 CI 必须绑定实际推送 main HEAD，不能使用旧结果。
