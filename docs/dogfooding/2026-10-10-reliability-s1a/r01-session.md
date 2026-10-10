# S1-A / R01 init 失败保全

日期：2026-10-10。任务来自
[S1-A / R01 任务卡](../../plan/reliability-2026-10-03/01_Persistence_and_State.md#3-r01init-在失败时保全已有文件)，
前置基线见 [R00 报告](r00-baseline.md)。本文件记录 R01 修复证据；保留 R00 的原始故障观察。

## 当前交付状态

| 项目 | 状态 | 证据 / 待补 |
|---|---|---|
| R01 实现与定向回归 | 本地定向 PASS | 101 passed，13.68 秒；平台兼容调整后追加 23 passed，3.57 秒 |
| 完整质量门 | PASS | 14 个命令全部 exit 0；1,984 passed，总覆盖 93.28%，redaction 100% |
| 五项目 Gate A | PASS | 45 命令、180 完整比较、零 delta；147 源文件前后相同 |
| 独立提交 / main 推送 | PENDING | 完成门禁后登记 R00、R01 各自提交及推送结果 |
| CI 矩阵 | PENDING | Linux 本地结果不能替代 Python 3.10–3.12、macOS、Windows CI |

本报告冻结提交前证据。提交、推送和远端 CI 的实际哈希及结果见本任务最终交付记录
与对应 GitHub checks；提交前不把这些步骤计为通过。

## 最终行为与实现范围

- `write_scaffold` 在任何 owned 写入前验证最终 YAML 文本；内存入口与
  `load_manifest` 共享 YAML mapping 解析和 `Manifest.model_validate`。
  校验失败保留旧 manifest 和辅助文件字节、权限，不产生半成品。
- manifest 通过同目录临时文件写入、flush/fsync；只创建缺失的辅助文件，
  准备成功后最后以 `os.replace` 提交 manifest。文件创建后立即登记，
  正常异常只清理本轮新文件、临时文件和本轮创建且为空的 `.reprollm`。
- 既有 `.reprollm/config.yaml` 和 `project-rules.yaml` 不覆盖、不删除；
  成功 `--force` 保留旧 manifest 支持的权限位，新 manifest 使用临时文件的安全默认权限。
- 写模式 CLI 在 detection 前检查 owned 输出节点，writer 再检查；
  `reprollm.yaml`、`.reprollm`、config、project-rules 的普通和 dangling symlink
  均拒绝，诊断不回显外部路径。`--list-tasks` 保留既有无写入合同。
- project-name schema 不放宽。合法目录名保持字符串语义；必要时引用 YAML 隐式标量。
  非法或命中既有 secret/machine-identity 检查的 basename 使用固定 `experiment`，
  仅显示编辑 `project.name` 的安全提示。
- generated YAML/OS 失败诊断只提 owned 位置及修复动作，不复制底层 YAML 内容、
  Pydantic 输入值或绝对机器路径。

修改仅涉及 init CLI/scaffold、共享 YAML 文本解析、相关测试、规格 §3.2 与 CHANGELOG。
R02、R02-R、R03、scanner、dependency parser、漂移策略及 schema 留待各自任务。
未增加依赖、unsafe 开关、通用多文件事务或项目名放宽。

## TDD 与验收证据

真实 CLI 保全回归首先取得有效 RED。随后故障矩阵首次运行遇到独立运行 core tests
缺少规则 registry 引导的问题；改用公开 writer 接口的最小合法 YAML 输入后才取得
该矩阵的有效 RED。这个测试准备错误不计为产品缺陷。有效 RED/GREEN 顺序如下：

| 阶段 | 有效 RED | 修复后的独立预期 |
|---|---|---|
| 真正 CLI `--interactive --force` 生成非法数值 | 1 个回归失败，旧 manifest 被删除 | exit 2；旧 manifest/config/rules 字节及权限完全不变 |
| 临时写入、config/rules 部分写入、replace，已有/新辅助目录 | 8 个故障回归失败 | 旧 manifest 保全；仅移除本轮创建内容 |
| 非法目录名与 YAML 隐式类型目录名 | 11 个命名回归失败 | 非法名称为 `experiment`；合法名称 load 后仍是准确字符串 |
| 扩展验收矩阵 | 定向全部通过 | 首建失败、普通/dangling symlink、安全 canary 诊断、成功权限、parser parity、既有 init selection/snapshots 均覆盖 |

定向命令：

```bash
uv run pytest -q tests/unit/cli/test_init.py tests/unit/cli/test_init_selection.py tests/unit/core/test_manifest_scaffold.py tests/unit/core/test_yaml_io.py
```

最后一次完整定向结果为 **101 passed / 13.68 秒**；随后将 Windows 无法准确创建的
省略号目录用例替换为可移植的 `1.0` 隐式数值用例，并采用既有 symlink 能力检测约定，
追加名称/symlink 定向结果为 **23 passed / 3.57 秒**。产品源码在最终质量门与
候选五项目运行期间保持不变。

权限失败回归比较实际 before/after 字节及 mode，适用于支持的全部平台。
严格 POSIX `0640` 成功断言仅在支持 POSIX 权限的平台执行；symlink 回归只在
runner 能创建 symlink 时执行，不把缺少平台能力标成产品通过。
独立复核已逐项核对任务矩阵、Python 3.10 API 边界与跨平台测试；未发现剩余
实现阻塞。本地完整质量门通过，远端 CI 另行核对。

完整命令与日志摘要见 [r01-quality.json](r01-quality.json)：

| 检查 | 退出码 | 耗时（秒） | 结果 |
|---|---:|---:|---|
| `uv sync --locked --dev` | 0 | 0.028 | 无依赖变更 |
| full pytest + branch coverage | 0 | 308.737 | 1,984 passed，2 deselected，覆盖 93.28% |
| redaction branch coverage | 0 | 0.187 | 100% |
| Ruff check / format | 0 / 0 | 0.088 / 0.092 | 全部通过 |
| Mypy | 0 | 0.462 | 120 source files 无错误 |
| security tests | 0 | 9.768 | 29 passed |
| generated rules/profiles/CLI/quickstart | 全部 0 | 0.401 / 0.410 / 10.646 / 11.371 | 全部 fresh |
| exported schemas | 0 | 0.497 | 10 份集合与字节完全一致 |

继承 R00 已验证的临时 Git 2.25.1 兼容 PATH，没有改仓库脚本或系统 Git。
既有未知 slow marker 警告仍为 1 条；2 个 slow 用例按现有默认配置不执行。
普通名称的三个 golden init snapshot 无字节变化，未重生成 fixture 或 schema。

## 真实 CLI 字节保全

[r01-preservation.json](r01-preservation.json) 保留三次真实 console 命令及各文件
before/after SHA256、权限位和完整字节相等断言：

| 场景 | CLI exit | 耗时（秒） | 独立结果 |
|---|---:|---:|---|
| 合法旧 manifest + 两辅助文件，非法交互数值，`--force` | 2 | 0.519951 | 三文件字节、0640 权限及目录权限完全保全；旧 manifest 仍可 load |
| 中文目录、合法旧 manifest，正常 `--force` | 0 | 0.549937 | 新 manifest 立即 load 为 experiment；辅助字节与所有权限保全 |
| 首次 init，非法交互数值 | 2 | 0.522760 | manifest、辅助目录和临时文件全部不存在 |

三次合计 1.592648 秒；没有 monkeypatch、网络、GPU 或重依赖。
所有诊断均未回显 case 根路径，共享证据只保留脱敏结果与原始 console 输出摘要。

## 规格与故障边界

规格 §3.2 原先未规定命名 fallback、失败保全、权限和 owned symlink 合同。
本任务同步补充任务卡已授权的具体行为；不存在冲突的冻结决定，Project schema 保持不变。
未触及 D-41 指定的 `core/redaction.py`、`core/engine.py` 或 schema 文件，
也未以本次修复代替后续安全任务所需的明确审阅。

保全承诺覆盖校验失败和正常 write/replace 异常；不宣称断电条件下跨文件全局事务，
不宣称并发写入隔离。已有产物只按原合同处理，其他命令的历史隐私缺陷未被自动清理。

## 五项目 Gate A 与发布边界

Gate A 使用 [R00 输入清单](r00-input-inventory.json) 中五个有效 pin。
原始 checkout 保持干净，init 与其后 L1 audit 仅在一次性副本运行。
完整 L0/hints/diagnostics 继承独立 source-reviewed 历史 oracle；缺失的完整 L1/manifest
由已审阅代码重建，先匹配既有摘要后才用于完整比较，不把修复输出复制成 gold。

最终候选 [r01-gate-a-summary.json](r01-gate-a-summary.json) 保留 **45 条命令全部
exit 0、180 项完整比较全部相等**，总子进程耗时 164.659178 秒。完整命令、比较及五个
payload 见 [r01-gate-evidence-index.json](r01-gate-evidence-index.json)。

| 目标 | pin | 命令耗时（秒） | 完整比较 | delta |
|---|---|---:|---:|---|
| lm-evaluation-harness | b954108c9baaaa934b4ad842033b31a97ee30816 | 123.604492 | 34 | 无 |
| FastChat | 587d5cfa1609a43d192cedb8441cac3c17db105d | 8.900466 | 37 | 无 |
| LlamaFactory | 673048c6a543cbbeaed5b8444b8223dc4e23c721 | 12.081617 | 43 | 无 |
| HarmBench | 8e1604d1171fe8a48d8febecd22f600e462bdcdd | 15.648086 | 33 | 无 |
| llm-dp-finetune | 7f8b5dff4b92aae90ceccce3ec959b48307bed9e | 4.424517 | 33 | 无 |

相对 R00 和独立 gold，完整 L0/L1 rule sets、profiles、hints、路径/物理行号、
默认/verbose diagnostics 与 manifest/config/rules 字节全部相同。没有改 pin 或 gold。
普通名称三份 fixture init snapshot 仍按原字节比较。五个原始 checkout 仍 clean。
候选基于 R00 提交 0750104，只有三份产品文件改变；147 份产品/schema/dependency 文件
前后 inventory 均为 `33bec7769e6f2c4aa0ea194064bafb17509dd0914b138dc328cd1fc6d4978e02`。
包含本报告的提交按同一 inventory 绑定；质量门和 Gate A 不含后续产品修补。

本次普通 S1-A 未激活 milestone/release Gate B。
[VAL-R01/R02/R03](../pending-resource-validation.md) 继续保留现有 BLOCKED 状态，
没有用合成或离线测试代替真实 GPU、paid judge、受限模型访问验证。

## 提交与交接

R00 已独立提交 `0750104576a08fc079b24e4df81c0c5eb62b3301`。R01 随包含
本报告的 `fix(init): preserve existing scaffold on validation failure (R01)` 独立提交。
main 推送与远端 CI 待核对，完成后由最终会话交付记录给出两个提交的实际哈希。
R01 commit 引用任务 R01、规格 §§3.2/21/22；ordinary-name snapshots、schema、
fixtures 均无变更。本报告与 JSON 保留候选证据，提交后通过 GitHub main CI 的
Linux Python 3.10/3.11/3.12、macOS Python 3.12 和 Windows Python 3.12 矩阵再核对。

S1-B 按 R02 → R02-R → R03 继续，先读取 R00 的当前泄漏/State 复核及本报告。
R01 的共享文本校验及 replace-last 只作为具体参考；lock 已有原子 writer，
后续任务不得为复用而扩大成通用事务框架或把拒绝策略直接搬到已完成 child 的 run 路径。
