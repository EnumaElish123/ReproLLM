# Spec issue 草稿：R07-C D-M-CS

状态：DRAFT_NOT_SENT。建议 label：`spec`。本片尚无具体接受决定。

## 标题

R07-C: decide the bounded retained-name Conda specifier uncertainty policy

## 问题及当前合同

当前 §12.2、§12.3.6及§12.3.13有意保留Conda named declarations及有限exact子集。
原helper在不能保留rest时仍append name并写固定占位；未记录这一分支的内部失败事实。
这符合现规范，不是已接受D-M-CE的漏实现。

完整提案、官方来源、当前观察、独立预期和两份精确未应用补丁位于本目录。
A仅在现placeholder赋值点增加独立typed cause并复用D-M；B保持captured-view WARNING。
不解析更多Conda语法，不改exact/声明/诊断/信用/engine/schema/gold。

## 需要的具体决定

是否接受A、两份具体patch、原首因规则及全仓保守成本？明确非exact的wildcard/compound
或无关非关键条目也可使其他剩余已用包WARNING→SKIPPED/INFO、孤立门1→0，
默认text可PASS+skipped而export少notable项。该成本不是官方语法的逻辑结论。
也可以选B保持现状。接受后才进入P-B的先RED/实施/完整验证和提交推送。

本草稿供维护者审阅，未对外发issue、通知或申请；不将总体开发授权视为新政策已接受。
