# 本地 spec issue 草稿：R07-C D-M-P

状态：**PROPOSED / NOT_POSTED**，没有对外发帖。
按[执行总则 §5.9](../../../00_Execution_Guide.md)先完成具体材料，尚未更改现行规范。

已解码 PEP 621 dependencies/optional-dependencies 中，失败字符串当前只产生 unparsed，
没有建立声明失败事实；剩余已知宽松包仍可有 missing-pin WARNING。
这不同于已处理的读取、文档解码和容器结构问题。

[推荐 A](R07-C_pep621_strings.md)只对两个原解析调用的真实失败记录 `unparsed_requirement`，
同源已有原因优先，保留部分声明、信用、诊断和读取；复用 D-M，不推断失败项包名。
[具体规范补丁](spec-proposed.patch)未应用，兼容成本、未来验收、当前观察和五项目来源均已备齐。

## 可直接裁决的问题

是否接受 **D-M-P 方案 A 和精确规范补丁**，明确接受空白失败字符串及无关子项目也可能
全仓影响剩余关键包、孤立门退出 1→0 的成本，并保留所有正面信用及既有不确定性优先级？
接受后先回归 RED，再最小实施和 GREEN，取得最终质量门、fresh 五项目及受影响门和精确提交 CI。

选择 B 则保持旧合同，本缺口 OPEN。两种选择均不授权付费 API、GPU 或版本发布。
