# R07-B：默认披露 Python 文件预算截断

日期：2026-10-13。状态：**PROPOSED / REVIEW_READY**。
依据：[任务卡 §3](../../03_Scan_and_Runtime_Evidence.md#3-r07-b默认可见的扫描截断诊断)、
[统一总则 §5.9](../../00_Execution_Guide.md#5-统一实现与兼容性要求)、
[现行规范 §13](../../../01_specification.md#13-deterministic-profile-detection-m2)。
本提案不是已接受决定；S3-A 的总体执行授权不替代本次具体 §13 修改的接受。

## 现状与拟议变化

现行 §13 将超过 AST 上限的 warning 放在 `-v`。
`RepoScanner.python_files()` 对排序后的候选取前 500 个，并记录选中数量，
该数量不能证明 500 个文件都已成功解析。`scan_python()` 还可能因文本不可读、
512 KiB 读取上限、非文本或语法错误跳过已经选中的文件。
默认 audit 不显示数量截断；init 不转发这些诊断；export 调用同一 audit 构造
Markdown 审计摘要，但不请求诊断。用户因此可能把未发现信号误读为完整扫描结果。

拟议规范仅提升**Python 文件数量上限**触发的覆盖摘要。
受影响命令具名为 `audit`、`init`（包括 `--list-tasks` / interactive）及
`export` 内嵌的当前 audit。详细文件诊断及其他 verbose 信息不整体提升到默认模式。

## 数量与触发条件

| 名称 | 定义 |
|---|---|
| candidate | R07-A 静态排除和既有枚举 hard limits 后，确定排序的 `.py` 候选数量 |
| limit | 当前实际生效的 Python 文件预算，默认 500；不另加固定 500 分支 |
| selected | 本轮 `python_files()` 返回、实际送入 Python 扫描循环的路径数，最多 limit |
| parsed | 已选中路径中 `ast.parse` **成功返回**的数量；不以 selected、imports 数量或 warning 行数代替 |
| omitted | candidate − selected，仅指文件预算没有选中的候选 |
| selected skips | selected − parsed；可能涉及大小、读取/非文本或语法错误，不冒称每一种原因都已分别计数 |

仅在 candidate > limit 时输出该默认摘要。candidate ≤ limit 时，即使某个
选中文件因大小/不可读/语法错误跳过，也不新增这条默认 warning；该类已有诊断
维持现行渠道。本提案没有把所有扫描问题升级到默认输出。
候选不包含 R07-A 排除的环境/cache，也不把既有枚举 hard limit 移除的文件
算进分母；不声称候选数等于全部仓库 Python 文件数。

默认短诊断为一行 stderr，文案和前缀稳定：

```text
scan: Python analysis incomplete: parsed {parsed} of {candidate} candidate files; selected {selected} (limit {limit}), omitted {omitted}. Missing signals may be in unanalysed files.
```

若 selected skips > 0，在最后一句前插入：

```text
{selected_skips} selected files were not parsed.
```

因此，501 个可解析业务文件的文案为：

```text
scan: Python analysis incomplete: parsed 500 of 501 candidate files; selected 500 (limit 500), omitted 1. Missing signals may be in unanalysed files.
```

若 501 候选的前 500 个中有 1 个超过读取上限、1 个读不到文本、1 个存在语法错误，
文案必须是 parsed 497、selected 500、omitted 1、3 selected files were not parsed；
不得声称 500 processed。不能仅凭 `read_text()` 的 None 区分 size、binary 与读取失败。
每一种原因可以在测试中由独立输入确证，但摘要不捏造按原因拆分的计数。

## 输出兼容性与范围

- 默认文本、JSON、GitHub 格式及 `audit --output` 均将摘要写到 stderr。
  `audit --format json` 的 stdout 仍只有原来一份合法 JSON；report 文件也不混入文字。
- 同一命令每个相同覆盖摘要最多显示一次，`-v` 不重复新增摘要和旧
  `python file scan truncated ...` 行。公共 scanner 的旧 warning 保留兼容，
  CLI 显示层只去掉同一次预算事实的重复文案。
- audit 的其他现有 verbose scan/read/syntax/dependency 诊断继续保持 verbose。
  init/export 本轮只转发新增覆盖摘要，不为它们新建全部 verbose 诊断输出。
- 摘要只有固定文字及整数，不带绝对路径、文件名、身份或源代码值。
- 数量和摘要只使用内部对象/CLI stderr，不新增持久化字段、schema、Finding，
  不改 rule status/severity、summary、默认 fail-on 或退出码。
- `discover` payload 的 64 KiB/2000 entries/max_chars 和 AST snippet 收集不使用
  `scan_python()` 的 500 文件预算，维持 §20.2；不虚称本摘要覆盖那套预算。
- `lock`、`run`、`diff`、`doctor`、rules/profile 展示等没有这次 bounded Python AST
  检测调用的命令，不新增该诊断。R07-C 的“信息不完整时哪些规则可以 PASS”保持待决。

## 已核对的消费者与实施入口

| 入口 | 当前事实/建议 |
|---|---|
| `core/scanner.py::python_files` | 候选来自 `analysis_files`，预算选中、原 warning 去重；保留公共行为 |
| `core/pyscan.py::scan_python` / `PyScanResult` | 内部保存候选/selected/parsed 成功计数；构造固定摘要，不把未读/解析失败当成功 |
| `core/context.py::AuditContext.pyscan` | lazy cache 同一扫描事实，消费者不能重新猜算 |
| `core/engine.py::run_audit(..., diagnostics=...)` | 已合并 scanner/pyscan warnings；通过现有参数传递摘要，**不改 engine 文件** |
| `cli/audit.py` | 现行默认只输出 run warnings；显示新增摘要，verbose suppress 同一次旧 truncation 行 |
| `core/manifest_scaffold.py::InitPlan` / `plan_init` | 增加仅内部 diagnostics；从本计划实际 ctx.pyscan 保存摘要，不增加 manifest 字段 |
| `cli/init.py` | `--list-tasks` 返回前显示摘要；interactive 如重新计划只显示最终计划摘要一次 |
| `cli/export.py` | 通过既有 run_audit diagnostics 参数获得摘要，仅 stderr；Markdown/schema 内容不因诊断变化 |
| `profiles/detect.py`、`rules/env.py`、framework integrations | 消费同一 AST/候选事实，不新增 warning 解析语义，不调整规则政策 |
| `discover/collector.py::_argparse_snippets` | 独立 payload 边界，不是此次 500-cap 覆盖事实 |

可以新增共享 CLI-only 显示 helper：依据固定的摘要前缀识别该诊断，按文本去重，
只对该摘要使用默认输出。不能让规则通过解析 warnings 自然语言推导新业务事实。
Git/fallback 都使用 R07-A 同一候选视图；数量不能只从 Git 文件数估算。

## Tests-first 验收与独立预期

| 输入/命令 | 独立预期 |
|---|---|
| 499、500 个有效业务 `.py`；default text / JSON / `-v` | parsed/candidate/selected 各为 N，omitted 0；没有新增默认摘要 |
| 501 个有效业务 `.py`；同三种输出 | parsed 500/candidate 501/selected 500/omitted 1；stderr 精确一条摘要；JSON stdout 一份 document |
| 第 501 个业务文件含 framework import 或 HF ID | 未处理尾部信号仍缺失，但摘要明确没有 absence 保证；不改变规则政策 |
| 501 候选中前 500 有 oversize、受控读取失败、语法错误，分别及组合 | parsed 成功数真实降低；candidate/selected/omitted 不混算；default 只显示摘要，audit `-v` 保留详细原因 |
| 500 候选中仅 oversize / 读取失败 / 语法错误 | 不新增默认 file-cap 摘要；验证现有详细诊断渠道 |
| 非默认 budget 的 cap−1 / cap / cap+1 | 同样边界，以实际 limit 显示；没有新硬编码常量 |
| Git 与 fallback 同等业务文件；R07-A 环境排除控制 | candidate 与 AST 事实一致；环境文件不挤入预算，Git 安全/状态事实独立保留 |
| 重复 `python_files` / ctx.pyscan / `-v` | 单次扫描和诊断事实稳定；摘要不与旧 truncation 重复刷屏 |
| init 默认、`--list-tasks`、interactive 重新计划 | 摘要一次；任务/stdout/manifest 字节保持相同，后者在一次性副本中验证 |
| export 默认及 `-v` | 摘要一次；完整 Markdown/stdout 与既有相同输入 oracle 保持不变 |
| audit fail-on never / critical / warning | 新摘要不改变同一 finding 集合下的退出码 |
| 不可信文件名/源值 canary | 新 stderr 摘要只含固定文字与整数，不回显 canary 或绝对路径 |

固定五项目在最终 R07-A 候选分类上验证：lm-eval 历史候选 816，实际 limit 500。
若前 500 候选全解析成功，默认 stderr 应新增 parsed 500 / candidate 816 /
selected 500 / omitted 316 的精确上述文案。**500 parsed 必须由实际源码/扫描证据确认**，
不能把历史“500 selected”当成功解析证据；若实际存在跳过则只使用真实成功数。
其他项目没有 500-cap 时不新增摘要。完整 JSON/text stdout、rule 集合、manifest、
hints 和默认 fail-on 与 R07-A 冻结参考比较；预期 stderr 展示差异依据本具体规范，
不从当前输出更新五项目 gold。正式全质量与 fresh 五项目 Gate A 由主代理执行。

## 审议材料

`spec-13-proposed.patch` 是针对当前接受后的 §13 基线 SHA
`13db16f6f89971b5e971b03578de356aba6c5e5bf2f5087fc08e2f3545ba25a7`
生成的精确 unified diff，**尚未应用**。`proposal-inventory.json` 保留基线、规范前后 SHA、
提案/patch SHA 和未接受状态。R07-A 的独立规范补充若前进，实施时组合/rebase 核验
须记录，不能用本补丁掩盖其他正文变化。无新增依赖、持久化 schema 或 D-41 代码修改。
