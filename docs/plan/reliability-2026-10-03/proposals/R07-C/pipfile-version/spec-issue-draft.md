# 未提交的 spec issue 草稿

建议标签：spec。标题：R07-C D-M-PF — bounded Pipfile explicit version-field type fact。

当前合同/实现一致地未记录个别 Pipfile version 的非str类型。建议仅在现有 packages/dev-packages 原循环按 dict+present version+non-str 谓词 setdefault invalid_structure，原 helper(allow_bare=False)、append、信用和先因保持。
具体裁决材料：[A/B](proposal.md)、[兼容性](compatibility.md)、[未应用规范补丁](spec-proposed.patch)、[验收](acceptance-cases.md)。

裁决问题：是否接受 A 及精确补丁，并接受其 repository-wide WARNING→SKIPPED、孤立 exit1→0、text/export 展示成本？或选择 B 保持现状？
状态 PROPOSED，无批准日期。之前 Poetry 的批准不扩展到本片。当前只完成准备，未写产品、现行规范或测试。
这是完整草稿，本轮未对外创建 issue；沿用当前 P-A 工作流既有外写授权边界，不把准备视为已提交。
