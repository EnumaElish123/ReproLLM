# 未发送的 spec issue 草稿

Title: R07-C: bound synthetic PASS under known incomplete Python analysis
Label: spec
Status: DRAFT_ONLY_NOT_SENT

在 `055c5fb`，规范 §11.5 要求 applicable rule 的空 check 合成 PASS，而 §13 的数量诊断有意不改变状态。
11 个受控公共 audit 输入证明：cap 外唯一 vLLM import 或一个不可读候选可令 profile mismatch PASS；
完整解析同一输入后可成为 INFO finding。不能把规范允许的现行为静默改成新语义。

提议接受 [A 的具体局部范围](R07-C_incomplete_scan_conclusions.md)，以及
[规范 patch](spec-proposed.patch)与[引擎/内部接口 patch](implementation-proposed.patch)。
仅 critical-deps / profile-mismatch 两 rule 的空结果路径在 primary Python gap 或未观察时 SKIP；
保持其他结果、所有 schema、fail-on 和 R07-B stderr。
A 有意保守，五项目预期只有 lm/Harm L1 两处 PASS→SKIP，完整预期已附；不重写 gold。

本 issue 还应保持 OPEN 的事项：非空 absence 分支、listing/deps/framework coverage 和充分证书。
不能因 A 合入就关闭整个 R07-C。D-41 engine maintainer review 是独立必需的接受内容。
没有新 GPU、付费或发布请求。详细 evidence、兼容矩阵和后续独立测试均在同目录。

本轮未创建 issue、未发评论；本草稿不是外部平台的已受理状态。
