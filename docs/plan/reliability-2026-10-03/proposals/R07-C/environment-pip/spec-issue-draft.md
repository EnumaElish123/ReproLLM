# 本地 spec issue 草稿：R07-C D-M-E

状态：DRAFT_ONLY；建议标签 spec。没有向外部仓库发帖。

当前规范 §12.3.9 明确不包含 environment embedded pip。现有提取器对非空字符串先 strip，再交给 Requirement；
失败保留诊断但没有内部 declaration issue。pip 安装器可能接受该内容，所以本提案不是完整格式有效性裁决。

推荐 A：[精确补丁](spec-proposed.patch)只增加 §12.3.10 的独立 caller opt-in，记录同一内部
unparsed_requirement，用 setdefault 保留旧原因。保留空白跳过、外层 dependency ordinal、部分声明、
Conda／格式 lock 信用、资格、barrier、读轨迹及既有优先级；不增加 grammar／读文件／安装器执行。
B 保持当前合同，缺口继续 OPEN。

裁决应同时覆盖：A、精确 patch SHA、全仓 WARNING→SKIPPED 与孤立 exit 1→0 成本。
同意后进入下一次 P-B：先 RED、最小实现、GREEN、最终质量、五项目 Gate A 与受影响检查、main 推送及精确 CI。
本轮 P-A 不实施候选、不发布版本、不调用付费 API／GPU、不修改旧报告或 gold。
