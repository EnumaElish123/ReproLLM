# R07-C D-M-CS：保留包名但未提取 Conda specifier 的具体提案

状态：PROPOSED。日期：2026-10-27。基线：`22e3dbcb799a18b8ef096c6fc42e5f5ab7ae9a0d`。
D-M-CS 是本片的本地标签，不是架构决策 D-nn。P-A 不实施候选政策。

## 当前合同与问题

规范 §12.2 的 Conda exact 子集和 §12.3.13 的两处省略事实已经实施。
当前实现与规范一致。本片不把既有的有界解析行为宣称为违约或漏实现。
§12.3.13 明确保留所有到达 append 的分支，并将 retained-name grammar 留为 OPEN。
上一批 D-M-CE 的具体接受不包括这一范围。

在 `_add_conda_entry` 中，字符串通过 name fullmatch 和 channel/subdir 两道提前返回后，
保留原 head。rest 不匹配有限版本形式时仍追加声明。如果它也不匹配原数字 range
形式，则其 specifier 被替换成固定占位值 `(unsupported conda declaration)`，exact 为 None。
原诊断保留，但这个特定的信息丢失尚不产生声明失败事实。

这一分支同时容纳官方语言中的版本精确形式、明确非精确形式和未确认/错误形式。
例如版本后缀、build wildcard、逗号复合范围、bracket 约束、内空白乃至 URL-looking
head 可以进入该分支。这里没有运行 Conda，不能从分支反推有效性、可安装性或隐藏 pin。
官方语义的范围与限制见 [official-sources.md](official-sources.md)。

## A：在现有占位赋值点记录有限提取不确定性（推荐，待具体接受）

为内部 `DeclarationReadIssue` 增加独立 `unparsed_conda_specifier`。只在原有
`if _CONDA_RANGE_RE.fullmatch(rest) is None:` 内、原占位赋值之前增加：

```python
result.declaration_read_issues.setdefault(path, "unparsed_conda_specifier")
```

该到达路径是完整定义：原 name fullmatch 成功；原 rest 不以 `::` 或 `/` 开头；
rest 非空；原 `_CONDA_VERSION_RE` fullmatch 失败；原 `_CONDA_RANGE_RE` fullmatch 失败。
使用已有分支，不新建语法识别器，不从诊断、`exact is None`、声明数量或占位字符串反推事实。
不重新解释、复制或持久化 rest，不尝试恢复 exact，也不增加包名推断。

独立新 code 表示“已保留 name 的既有提取器没有保留其限制条件”，不扩大原
`unparsed_conda` 的两个省略返回，不复用 Python `unparsed_requirement`，不是 Conda-invalid。
它是内部 dataclass 的事实，不是持久化 schema 字段或新规则。

### 保持不变的边界

- 原 regex、outer strip、raw rest、诊断、specifier 占位、exact、声明及顺序全部保持。
- 裸名、有限数字 `=` 前缀、数字 `==`、literal build 及原六种数字 range 路径不新增原因。
  六种 range 指现代码接受的形状，包括 `~=`；不以该名单宣称 Conda 接受每种形状。
- D-M-CE 的两个早退继续只产生其原原因；未知 installer/selector 映射及未访问内容不扩展。
- 原整段 structure precheck 先于 entry 遍历，已有原因保持。实际 CS/pip/CE 调用之间按
  `setdefault` 保留该逻辑 source 的首因；不增加或覆盖其他原因。
- 部分有效兄弟、物理外层序号、same-basename 逻辑路径、internal alias、项目边界、
  barrier、读取/候选预算、requirements 图、lock inventory/关联及 presence 保持。
- 原已保留 head 继续形成同样的使用证据，既不添加未知包，也不删除原使用。

### 规则、完整 Finding 和消费者

直接复用已接受的 D-M 消费：exact/合格 lock 信用 → D-F/D-S → D-L → D-M → D-G。
本片不修改规则/engine。新原因只影响原本仍会产生缺 pin WARNING 的已用未获信用包。
原 D-M message、fix_hint、首 declaration/否则首 import evidence 和 distinct sorted
source 路径保持；已有更高优先级 Finding 全文保持。此前已 D-M SKIP 时可能只增加文件证据。

不改变 no-known-use applicability、空结果 Python veto、其他 Finding、severity override、
suppression、排序和默认 fail-on。声明库存保持，因此 profiles/hints/init 预期也保持；
必须完整验证，不能用 count 相同替代。audit JSON/text/GitHub 与 export 将沿现合同展示状态变化。

## 具体兼容成本

全仓 existential exact 信用和现 D-M 的全仓保守影响保持。即使占位内容明确是合法非精确的
wildcard/复合范围，或属于无关子项目的非关键包，也可以让其他所有剩余已用、未获信用
关键包 WARNING → SKIPPED/INFO。此项是明确待裁决的产品取舍，不是官方语法要求。
新原因也不能证明该条原文包含 exact、恢复它会得到信用或整个扫描不完整到何种程度。

例如现已保留 `numpy==1.*` 及另一文件的 `import torch`：A 可令 torch 缺 pin WARNING
成为 SKIP，即使该 wildcard 本身不提供 torch pin。相反，`numpy>=1` 保留原数字 range
路径，虽有相同 unsupported 诊断，却不会仅因本片新增原因。该不对称来自接受的有限
提取边界，不是对两个声明有效性或风险高低的排序。

孤立 WARNING 或用户提升为 CRITICAL 的门可能 exit 1→0；FAIL-only override 不提升 SKIP。
独立达阈值 finding 仍可令命令失败，suppression 仍按现合同。默认 text 可以显示
Findings: PASS 加 skipped count；默认 export 可以少原 notable warning；完整 JSON 保留 SKIP。
这不授予 pin、完整性、安装或复现成功证明。B 可以合理拒绝这项新增保守放宽。

## B：保持已采集视图上的 WARNING

不增加 code，不应用任何补丁；原声明、诊断和缺 pin Finding 保持。
避免新增全仓 SKIP/退出码放宽，继续明确其 captured-view 和有界 exact 限制。
保留名称但丢失限制条件的问题继续 OPEN，不称为已解决。B 是有效裁决结果。

## 精确文件和兼容矩阵

待实施产品文件仅 `src/reprollm/core/deps.py`；规范为 `docs/plan/01_specification.md`
的新增 §12.3.14 及有限交叉引用。P-B 还应有独立测试、CHANGELOG 和验收报告。
两份精确 patch 与哈希绑定见 [patch-binding.json](patch-binding.json)。P-A 不应用到产品。
不触碰 D-41 的 engine/redaction/schema；不改 scanner、依赖、版本、gold 或历史产物。

| 输入/读写路径 | A 的预期 |
|---|---|
| 旧 manifest/lock/run/report/手动 Declarations | 格式与旧字节保持；内部新字典默认仍为空 |
| 无新触发的当前输入 | 完整结果保持，包括旧 CE、range 和 exact |
| 已获 exact/合格 lock 信用 | 信用和完整优先级保持 |
| 新触发且剩余已用未获信用包 | 现 D-M SKIP；不写新字段 |
| 同输入重复 audit、text、export | 除规范列出的元数据外确定；所有历史输入字节保持 |
| 旧/新读者读取产物 | schema/字段不变，无迁移、无版本 bump；不能把语义变化说成零兼容成本 |

## 裁决与接续

裁决对象是 A 的精确实现/spec 补丁、首因语义、全仓影响及上述阈值/展示成本，或选择 B。
本轮总体继续开发授权用于完成 P-A，不替代这项新的具体规范决定。
P-B 接受后，先在 public scan、真实规则和 CLI 三个接口写独立回归并证明 RED，再最小实施；
完整验收组见 [acceptance-cases.md](acceptance-cases.md)。一次最终质量门、fresh 五项目 Gate A
与受影响扩展完成后提交推送 main，并核对精确最终 HEAD 的五项 CI。

本片不实施新 grammar、solver、workspace 选择、遗漏 use/listing/framework 或充分性证书。
不发布版本，不调用 GPU、Hub 或付费接口，不对外发送 issue/反馈/申请。
具体 spec issue 草稿另存；其他 R07-C 仍 OPEN。
