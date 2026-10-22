# 本地 spec issue 草稿：R07-C D-C requirements 注释子集

状态：PROPOSED / NOT_POSTED。仅本地草稿，无外部发帖授权。

当前 requirements 图会把普通行 `torch==2.5.1 # pin` 记录为 unparsed，真实 pin 可能未被识别。
HarmBench 还有 `art  # for ArtPrompt` 和 `tenacity  # for ArtPrompt` 两条真实非关键声明输入。

建议接受[具体方案 A](R07-C_requirements_comments.md#3-a-的精确算法边界)及[精确未应用补丁](spec-proposed.patch)：
只在原普通行完整解析失败、该文件无任一物理行末尾反斜杠时，尝试第一个 ASCII SPACE/TAB + `#`
之前的合法非 URL requirement 前缀。保留原路由、既有成功解析和其他格式，不扩展读取、include 或续行语法。

信用和现有不确定性优先级保持；新增声明会改变 use、lock、profile/init、diagnostics，并可能使
隔离后的 warning threshold 退出码向任一方向变化。五项目的已知非零差异和不变理由分别记录在
[影响分析](portfolio-impact.md)，未来验收尚未执行。

## 可直接裁决的问题

是否接受 **D-C 方案 A 和本包 `spec-proposed.patch`**，明确接受：

- 文件级反斜杠 veto、原字面 `" @ "` 分支、完整原行解析优先、只尝试首个 ASCII 分隔且禁止新增 URL；
- exact/完整 closure 信用及新 use 的双向状态/退出码成本，HarmBench 两条依赖与诊断的预期变化；
- P-B 先补回归、最小实现、一次最终质量门、五项目 Gate A 与受影响消费者，然后提交推送 main 并核对 CI？

选择 B 则保持现行合同，此缺口继续 OPEN。两种选择均不授权付费 API或版本发布。
