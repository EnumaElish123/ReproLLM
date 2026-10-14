# R04-S 兼容性与局部版本策略

**状态：PROPOSED。** 本文件与[实际旧读者证据](compatibility-observed.json)是可审阅材料，不代表批准、实现、发布或未来验收通过。主提案与规范/schema patch另由维护者审议。

当前观测产品为 `52ecc504b3795c46220f68ef24728e0666638df0`，CLI与本地安装元数据均为0.6.1。提案不是向已发布0.6.1倒写修复，而是分两步建立可验证的迁移边界：

1. **R04-A：0.6.2 本地兼容桥。** 仍只读写run schema1，不写v2字段。集中处理未来schema2/3，给清晰升级提示，使export未知schema不再成为内部错误3。冻存本地wheel、对应二进制/安装环境、源提交/源码库存及wheel哈希，供下一步真实反向检查；不把尚未构建的候选写成可用或通过。
2. **R04-B：0.7.0 minor候选。** writer明确写run schema2；new reader读1/2，future3拒绝。新增环境来源/输入阶段字段按主提案处理，只有run格式升级。保持旧run字节不变；不知道的时点/child消费事实保持unknown。

0.6.1的旧诊断缺陷不能retrofix。文档明确建议升级到受支持桥/新读者；不能称0.6.1已向前兼容，也不能把升级建议当成已完成验收。本范围不创建release tag、不上传PyPI，不提前完成D02/D03/A01-B。

## 当前0.6.1实际行为

schema2/3各8条公开命令，加1条`--version`，实际17叶命令，总7.388841s，退出集合0×3、2×10、3×4。两夹具仅改变schema_version，不含尚未批准的v2新字段。全部临时输入前后完整文件集合与hash一致，未写出Markdown，0GPU/API。完整argv、相对逻辑cwd、退出码、耗时、全stdout/stderr及原字节SHA保留在 `compatibility-observed.json`；原始日志独立保留，未重跑或擦除失败。

| 命令 | schema2 exit | schema3 exit | 当前消息/行为 |
|---|---:|---:|---|
| `runs list --json` | 0 | 0 | `[]`并warning：cannot read / ValidationError；不表示记录被接受 |
| `runs show ID --json` | 2 | 2 | generic cannot read / inspect run.json |
| `runs show ID` | 2 | 2 | 同上，没有升级提示 |
| `export --run ID` | 3 | 3 | internal unexpected ValidationError；Input should be1 |
| `export`默认latest | 3 | 3 | 同上 |
| `diff run.json run.json --format json` | 2 | 2 | cannot load input；提示schema_version1 |
| `diff ID ID --format json` | 2 | 2 | generic cannot read / ValidationError |
| `diff --latest-successful --format json` | 2 | 2 | invalid-run warning后0 qualifying成功run错误 |

这些实际观察证明旧读者拒绝未知记录，却没有D-39要求的清晰版本升级诊断；export还分类成内部错误。只增加optional字段也会受严格`extra=forbid`影响，因此不能称双向可读兼容。当前实测不是实际0.7.0新格式的验收，后者须使用未来生成的完整run2与冻存桥wheel实测。

## 未来兼容矩阵

以下全部为 **NOT_RUN**。完成时记录实际命令、源码/候选wheel哈希和结果，不能引用这张计划表作为PASS。

| Writer → Reader | 目标合同 |
|---|---|
| 旧0.6.1 run1 → 新0.7.0 | 可读；缺失来源/时点保持unknown；原文件不改写 |
| 桥0.6.2 run1 → 新0.7.0 | 可读；只按明确producer合同解释可证明来源，不虚构child验证 |
| 新0.7.0 run2 → 新0.7.0 | approved字段roundtrip，State primary/alternatives来源不丢；读选中run自己的snapshot |
| 新0.7.0实际run2 → 冻存0.6.2桥 | 安全拒绝并升级提示；show/export/explicit diff exit2；listing保留warning/skip合同，不产生半读取 |
| future run3 → 0.6.2/0.7.0 | 明确升级拒绝；不fallback到另一run，不改写原文件 |
| 旧run1 → 0.6.2桥 | 原字段与旧字节可读，桥writer仍schema1 |

listing原有exit0+warning/skip语义单列，不把它当未知run解析成功。child success仅指exit0，不代表capture、环境或输入消费完整验证。future版本错误不得回显host路径、username、秘密值或parser原文。

## Schema与版本局部化

`schemas/manifest.py::SchemaVersion`目前`Literal[1]`，被manifest、lock、profile、project rules、rule archive、config、audit/diff report、discover candidates共用。**不得扩大共享别名。** run使用自己的版本类型/验证调度：桥支持1；minor读1/2，写2。v1不能因一体模型的optional字段默认而悄悄接受v2专用字段；字段与版本关系要有明确校验。

十个公开JSON Schema中，只 `run_record.schema.json` 预期有批准的变更；其余九个须最终fresh导出逐byte相同。State是内部typed JSON模型，不在这十个导出文件中；其context仍需完整JSON往返验证。没有新的manifest/lock版本或依赖升级。

`pyproject.toml`使用`dynamic=[version]`；Hatch从 `src/reprollm/__init__.py` 读取版本。bridge/minor在该唯一源更新，由本地根包安装刷新后核对CLI、distribution metadata、wheelMETADATA一致。uv.lock的本地editable包没有version值，不借此更新第三方包。`release.yml`的tag/version检查留待真正release；本提案不执行发布。

## 读者与消费者影响清单

| 边界 | 相关入口 | 必要变更/验证 |
|---|---|---|
| sharedrun decode与runs | `run/reader.py::_read/list_runs/read_run`；`cli/runs.py` | 按版本统一安全诊断；raw show保持原字节；listing透明warnings |
| selected/latest export | `cli/export.py::_select_run/_latest_run` | 直接model_validate也接共享version处理；未知格式exit2而非3，拒绝前不写MD |
| explicit/latest diff | `diff/inputs.py::load_input/from_selected_run`；`cli/diff.py` | directJSON、ID、folder与快捷筛选同合同；不接受/改写future记录 |
| Level2审计 | `core/engine.py`；`core/context.py`；`core/audit_state.py` | invalidrun不得隐形为有效runtime；currentintent/workingtree与historical baseline分开 |
| State及一致性 | `schemas/state.py`；`diff/state.py`；`rules/consistency.py` | legacyunknown、typedcontext、roundtrip、R03 last-wins/multiplicity保留；不把recorder/baseline当child验证 |
| writer与安全fallback | `run/wrapper.py`；`schemas/run_record.py` | bridgev1/minorv2显式写入；安全prewrite/final/fallback同版本；childexit合同不变 |
| default及checklist export | `export/exporter.py`及两个模板 | 四现有模板default/neurips/acl/acm的来源标签准确，selectedrun不被currentB替换 |
| 规范与工具 | spec§0/5/15/17/19/23、CHANGELOG、`scripts/compare_gold.py` | §0全docsv1改为run2例外；迁移说明；比较工具root1限制不得删内层run2版本绕过 |

`compare_gold.py`现仅接受outer schema1，可把完整run2放进schema1比较envelope或另审localized工具支持；不得将current输出晋升gold。历史v1 fixtures保留作兼容测试，新的v2样本按独立预期加入。新`reprollm_version`展示变化与真正语义delta分开记录。原pins、历史raw、commitbindings及resourceFAIL证据不改。

## D-39 / D-41 审核对象

D-39（architecture行236）要求pre1.0 breaking仅minor、整数schema版本及CHANGELOG迁移；D-41（architecture行269）要求schema、engine或redaction改动明确维护者审核。具体审核对象为：

- 主R04-S提案、规范§0/5/15/17/19/23实际patch及完整before/after示例、枚举/unknown定义。
- `schemas/run_record.py`及run专用版本检查、legacy兼容调度、仅run_record导出schema的实际diff。
- R04-A/bridge与R04-B/minor每项明确版本、source inventory、loader/engine/State实际patch和RED/GREEN预期。
- 旧0.6.1真实限制、local0.6.2桥wheel/bin冻结材料、0.7run2→桥的真实拒绝测试、future3等全部矩阵。
- child退出码/原子fallback/隐私回归，以及最终sessionquality、五项目GateA/affected消费者证据。

没有D-41决定前，本文件不授权写新格式；也不顺手修复已知RunPrivacy snapshotfidelity缺陷或扩展childhook/容器/远程探针。
