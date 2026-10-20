# 2026-10-20 · R07-C P-A：扫描缺口结论的具体审阅材料

本次从 `055c5fb880f4e374555a1d229b79d0d612c80350` 更新并核对计划。
R06-B 方案 A 已实施、完整 CPU 验收及精确提交五项 CI 通过；没有重开其实现。
下一项是 R07-C P-A。**本次交付审议材料，未改变产品规则或全局 PASS 合成行为。**

主入口：[具体方案](../../plan/reliability-2026-10-03/proposals/R07-C/R07-C_incomplete_scan_conclusions.md)、
[决定记录](../../plan/reliability-2026-10-03/proposals/R07-C/decision.json)、
[规范 patch](../../plan/reliability-2026-10-03/proposals/R07-C/spec-proposed.patch)、
[D-41 engine / 内部接口 patch](../../plan/reliability-2026-10-03/proposals/R07-C/implementation-proposed.patch)。
两个 patch 未应用，决定仍 PROPOSED。D-41 维护者具体审阅与新政策批准均 PENDING。

## 完成的 P-A 工作

- 全部 69 个 builtin ID、间接 helpers 和动态 project rules 逐项核对，区分正向证据、absence 条件、空合成与显式 PASS。
- 11 个当前公共 audit 输入覆盖 cap 前/后、有无信号、不可读、恢复完整解析、隐藏另一个 critical 包及未读 exact 来源；13 个当前行为条件符合。
  生产源码没有修改，网络/子进程/重依赖真实执行为零；合成 Git 走统一 proc gateway。
- 设计独立 typed primary-Python candidate coverage，不从 warning 文案猜原因；listing、deps、framework 等独立缺口明确保留。
- 重新核验五个 pinned checkout 身份与 clean、26 份历史材料哈希；十个完整 L0/L1 报告、690 条逐 rule 对比形成条件预期。
- 具体规范与五文件实现 patch、兼容矩阵、先测试验收设计、未发送 issue 草稿和决定记录完整；源证据与 patch 经独立只读复核。

推荐 A 的范围仅为两个 opt-in rule 在 `applies=true/check=[]` 下的 Python gap / unavailable veto，改为现有 SKIPPED/INFO。
其他规则、非空 finding、显式 PASS、generated rules 和默认阈值保持现合同。
五项目设计差异只有 lm/Harm 初始化 L1 profile mismatch 两条 PASS→SKIP；这是有意保守的代价，
不是证明它们一定有隐藏违规。**广义 R07-C mixed evidence 仍 OPEN**，A 合入也不能勾选整个任务完成。

## 本次验证与不适用项

分类：[validation workflow](../../plan/validation-workflow-2026-10-13.md)的纯文档 / 计划材料。
新增 JSON 为原行为观察或清楚标注的设计预期；没有新增可执行脚本、测试、产品源码、schema 或 fixtures。

本地检查的逐项结果见 [document-checks.json](../../plan/reliability-2026-10-03/proposals/R07-C/document-checks.json)：
链接与 JSON、来源身份、条件报告 schema 形状、两份 patch 适用性、diff whitespace、隐私和受保护工作区检查。
全量内容哈希见 [SHA256SUMS](../../plan/reliability-2026-10-03/proposals/R07-C/SHA256SUMS)。
这些检查验证审阅材料，不是未来 P-B 规则实现的 RED/GREEN 或产品质量验收。

| 门 | 本会话状态 | 理由 |
|---|---|---|
| 文档/来源/补丁一致性 | 见本次 document-checks 和独立审阅 | 仅文档与未应用 patch |
| 本地产品完整质量门 | NOT_APPLICABLE | 纯文档例外，不用旧 PASS 冒充本次运行 |
| fresh 五项目 Gate A / 消费者矩阵 | NOT_APPLICABLE | 未改产品；五项目仅分析已有完整证据，未重新运行 audit/init/export |
| GPU / H2 / Hub / paid judge / discover | NOT_APPLICABLE | 无受影响资源执行路径，不使用旧预算触发新请求 |
| generated/schema freshness 生成 | NOT_APPLICABLE | 无影响生成输入；具体 proposed patch 未生效 |
| 推送后 CI | 精确最终 HEAD 单独核对 | 最终结果见交付回复；不将上批 CI 当作本批通过 |

若 A 获具体批准，P-B 须先 RED 后实现，再执行最终完整 quality、fresh 五项目 Gate A 与受影响 L1/export/threshold/determinism，
通过后才合入；D-41 patch 如实质变化需补相应审阅。旧 gold 不重写。

## 既有验证缺口与交接

[先行补验](../2026-10-20-validation-followup/README.md)在 `948d164` 的 H2 / GPU / discover，
以及 `75d1b0` 的正式 judge，仍只对各自产品字节成立；R06-B 的 CPU 验收见[上一批报告](../2026-10-20-r06b/README.md)。
五份原始 metadata manifest 仍缺失，指定 HF 小文件的 authenticated 403 未解决；本次不记作 PASS，也不重复无关资源矩阵。
没有发布、打 tag、更新依赖、发送 issue/comment 或改写用户文件。

`README.md`、`docs/index.md` 及未跟踪 additional-cases-gold 文件属于本轮开始前的用户改动，完整保留且不提交。
P-A 审阅材料提交与报告收尾提交分开：

| 任务 | 提交 | 验收 |
|---|---|---|
| R07-C P-A | `3a46b58685e6a0d11a0b43ccbedb65b706c8c473` | 47 个材料文件哈希、38 个 JSON、72 个本地链接、21 份既有 schema 报告验证通过；534 个产品/配置等文件与基线相同 |
| 共享报告收尾 | 本报告所在后续提交，精确 hash 见交付回复 | 只记录上述材料结果和交接，不变更产品 |

初次 P-A 材料检查耗时 4.784687 秒；两份 patch 仅做 apply-check 与虚拟文本语法解析，未应用或执行。
提交后的精确 CI 仍待推送后核对，不能将此处写成预先通过。


## 推送后 CI 格式修正

首次报告提交 `f336756788b70427a82b5b6de19f97c374a8943a` 的
[CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/39365111686)五项均停在 Format check，后续测试未执行；
原始失败保留在 [failed-ci.json](ci-format-followup/failed-ci.json)，不回写为通过。
本地同一 `ruff format --check .` 复现唯一失败：覆盖设计文档内 `pass_skip_reason` 的 Python stub 应写成单行。
只修正该 Markdown 示例排版后，同一检查返回 0、666 files already formatted。
[修正记录](ci-format-followup/format-correction.json)绑定前后字节与原失败；两份具体 proposed patch、实际 engine / policy / schema 均不变。
材料哈希及文档检查随这次文档修正更新（74 个本地链接、4.871457 秒）；原 P-A 检查与文件可从 `3a46b58` 读取。
再次推送后的精确 HEAD CI 在最终交付回复中确认，不用本地格式通过替代跨平台测试。
