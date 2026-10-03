# ReproLLM 开发执行总则与任务索引

版本：v1.1 · 日期：2026-10-03 · 文档状态：待执行

审查基线：`590ee1739484bd21e21594e294e7ddf14bfd093f`。本包承接 `ReproLLM_Agent_Development_Plan_2026-10-03_v1.0.md`，采用第二轮代码核对后的结论。旧文档保留为历史路线图；任务范围、拆分和验收以本包与执行时仓库规范共同确定。本包中的“已复现”是审查证据，“验收要求”是未来目标，二者不能互相替代。

## 1. 如何交给开发 Agent

每次提供本文件、当前 Sprint 文件及上一会话报告。Agent 还须读取仓库 `AGENTS.md`、`docs/plan/00_architecture_and_decisions.md`、`docs/plan/01_specification.md`、`val.md`。无需每次加载全部历史计划。

可直接使用以下启动指令：

```text
在 ReproLLM 仓库执行本包指定的 Sprint / Session。
先读 00_Execution_Guide.md、该 Sprint 文件、AGENTS.md、架构决策、规格和 val.md。
记录实际 HEAD 与工作区状态，核对任务是否已被后续提交修复；不要回退到审查 SHA。
按任务卡先建立失败回归，再实施最小改动；保留现有工作，遵守任务禁区。
每项任务记录独立提交、定向测试、完整质量检查和规格依据。
会话结束执行全部五项目 Gate A；里程碑或发布另执行适用 Gate B。
只暂停需要决策或缺少资源的子任务，继续完成不受影响的任务。
将命令、退出码、完整结果差异、资源状态和下一会话输入写入会话报告。
不要把历史成功、计划中的测试或缺少资源的检查标为本次通过。
```

计划进入仓库时，建议整体放到 `docs/plan/reliability-2026-10-03/`，保持文件名及相对链接；在现有当前计划入口登记本轮 Sprint。这里建议的是目录组织，不新增产品命令或自动执行器。

## 2. 文件与推进顺序

| 文件 | 工作目标 | 会话安排 | 开始条件 |
|---|---|---|---|
| [01_Persistence_and_State.md](01_Persistence_and_State.md) | init / lock 保全与 State 有效值 | S1-A：R00、R01；S1-B：R02、R03 | 首个开发 Sprint |
| [02_Dependency_Accuracy.md](02_Dependency_Accuracy.md) | 精确版本、同名文件、requirements 引用图 | S2-A：R05-A、R06-A；S2-B：R06-P、R05-B | R00；建议 S1 后合入 |
| [03_Scan_and_Runtime_Evidence.md](03_Scan_and_Runtime_Evidence.md) | 扫描候选集、截断提示、环境来源与时点 | S3-A：R07-A、R07-B；S3-B：R04-A | R00；R04-A 接续 R03 |
| [04_Recipe_and_Release.md](04_Recipe_and_Release.md) | 可执行 recipe、wheel 实装、发布前置检查 | S4-A：D01、D02；S4-B：D03 | 核心相关修复；输入准备可提前 |
| [05_Policy_and_Compatibility.md](05_Policy_and_Compatibility.md) | scope、覆盖率结论、judge 策略、必要的 schema 决策 | P-A：提出具体方案；P-B：处理决定与验收 | R00 后可准备；逐项独立审议 |
| [06_Validation_and_Adoption.md](06_Validation_and_Adoption.md) | 输入包、正式回放、试用反馈和申请材料 | 支持工作流，按活动交付 | A01-A 立即开始；其余按依赖推进 |

四个工程 Sprint 各两次会话，遵循 `AGENTS.md §7`。这是工作边界，不是工时承诺。单项超过会话容量时，将未开始的任务移入具名后续会话并说明原因；不得压缩验收来凑进度。策略和外部工作可在逻辑上提前准备；不要求启用多个 Agent，也不要求并发编辑同一模块。

## 3. 稳定任务编号与依赖

所有任务初始状态为 `PLANNED`。编号沿用 v1.0；后缀是此次拆分，不代表已实现。

| 任务 | 交付与关键依赖 | 执行文件 |
|---|---|---|
| R00 | 当前基线、问题复核、五项目输入清单、状态账本 | 01 |
| R01 | init 校验先于写入，失败保全，合法名称处理 | 01 |
| R02 | lock 持久化安全检查；保留已有原子写入 | 01 |
| R03 | repeated CLI last-wins；合并及序列化后选择稳定 | 01 |
| R05-A | Python 格式 exact-version 语义 | 02 |
| R06-A | 同 basename 文件保留路径身份；根文件优先 | 02 |
| R06-P | requirements 路径边界、引用图和包归属；依赖 R05-A / R06-A | 02 |
| R05-B | Conda 独立语法和语义表；依赖 R05-A 的内部合同 | 02 |
| R07-A | 静态候选过滤发生在预算之前；保留安全/Git 文件事实 | 03 |
| R07-B | 默认可见的截断诊断；同步修订规格 §13 | 03 |
| R04-A | recorder / child 来源及采集时点；消费端一致；接续 R03 | 03 |
| R06-B | 多项目依赖与 lock scope 方案；不能覆盖 HarmBench gold | 05 |
| R07-C | 不完整扫描下的逐规则结论合同；接续 R07-A / B | 05 |
| R08-A | Issue #9：judge 直接 params 叶子默认 HIGH | 05 |
| R08-B | privacy / training 自由参数风险清单和逐项提案 | 05 |
| R04-S | R04-A 确需持久化字段时的有界 schema 变更方案 | 05 |
| D01 | 单一真实框架 recipe 的三层验证；依赖相关修复与 A01-A | 04 |
| D02 | 源码、候选 wheel、发布版的文档和版本证据对齐 | 04 |
| D03 | 同一 SHA 的质量门、候选 wheel 验证、发布前 release notes 检查 | 04 |
| A01-A | 固定输入可获取性、校验和、资源阻塞表；可先做 | 06 |
| A01-B | 修复后的干净环境回放和证据包；依赖 D01 / D02 | 06 |
| A02 | 试用材料、反馈记录、问题转任务；外部反馈单独计状态 | 06 |
| A03 | 有来源的采用与维护证据、申请草稿 | 06 |

R06-P 是第二轮新增的明确缺陷任务。R04-S 是条件任务：若 R04-A 用现有合同即可准确表达，则记录 `NOT_NEEDED` 的理由，不为完成列表而增加 schema。

模块协调：`core/deps.py` 由 S2 连续处理；`diff/state.py` 先做 R03 再做 R04-A；扫描与 `core/engine.py` 语义分开；D02 / D03 共用一个 wheel 验证入口。接续任务读取前项的实际提交和测试，避免重复抽象。

## 4. 当前证据与执行前复核

在审查 SHA 上，R01–R07 的最小案例已重新复现。另确认 requirements 可以读取根目录外的 `-r` 文件，及通用 secret 字段单独经过 `RunPrivacy.value` 时可能不变。各 Sprint 文件保留可重建的案例，不依赖审查工作区的临时脚本。

历史质量基线：Python 3.12.14 / Linux；默认测试 1,930 passed、2 slow deselected；总覆盖约 93.27%，redaction 分支覆盖 100%；Ruff、Mypy 通过。源码与 PyPI 0.6.1 的离线 walkthrough 曾分别试用。以上只用于解释起点，未来执行必须重新记录；测试数量与覆盖率不能填作本次结果。

本轮审查没有完成全部 GPU、付费 API、受限模型在线 Gate B。资源阻塞不能以 CPU 探针、模拟请求或旧会话成功替代。

## 5. 统一实现与兼容性要求

1. **用户工作区优先。** 先检查 `git status`；保留未提交修改，必要时独立 worktree。不要以强制 reset 或批量清理制造干净输入。
2. **问题定位以当前代码为准。** HEAD 已前进时，复测行为并更新入口。已修复项附修复提交和回归证据；不再重复打补丁。
3. **冻结边界照常生效。** audit 不调用 LLM，不加入重依赖，不导入被审计框架获取版本；HTTP 单测使用 respx；Git / nvidia-smi 使用既有 proc 接口。
4. **仅写命令拥有的产物。** 不替用户改实验代码、prompt、训练配置或目录结构。测试用例在临时目录，真实项目的变更命令在一次性副本中执行。
5. **持久化隐私。** 不写绝对路径、明文主机名、用户名或密钥。诊断写字段位置和安全原因，不回显原始敏感值。测试用合成 canary。
6. **确定性保留语义。** 固定输入应产生确定输出；映射按既定规范排列。argv 和具有优先级含义的 observation 列表保留顺序，不能为了排序破坏 last-wins。YAML 字段顺序遵循现有序列化规范。
7. **错误与退出码。** 可由用户修复的问题用 `UserError` / exit 2；包装运行的采集失败不替换已完成子进程的退出码。不要悄悄改变 audit / diff 默认 fail-on。
8. **审核只作用于相关改动。** D-41 要求 redaction、engine、schema 改动经过明确维护者审阅。先准备具体 patch / 提案、对照测试和影响清单，等待该部分审阅；其他任务继续。
9. **规格冲突必须显式处理。** 遵循 AGENTS 的 spec issue / 维护者决定流程；没有外部操作授权时先准备完整 issue 草稿。不要把本包中“建议的新行为”当成已经修订的规范。
10. **schema 不随意扩展。** 当前模型严格拒绝额外字段；“加一个可选字段”也要核对旧读者。D-39：pre-1.0 的 breaking schema 只在 minor bump 引入，并同步版本、读写兼容策略、迁移说明、规格及导出 JSON Schema。

本包是开发方案交付。未来代码提交、推送遵循届时会话授权与仓库工作流；发布版本、付费资源、向外部人员发消息和提交申请按已有授权判断，不从“写计划”推导出这些操作已执行或已获准。

## 6. 质量检查：每项代码任务与会话

在仓库根执行，先检查实际命令是否仍适用：

```bash
git rev-parse HEAD
git status --short
uv sync --locked --dev
uv run reprollm --version
uv run pytest -q --cov=reprollm --cov-report=term --cov-fail-under=85
uv run coverage report --fail-under=100 --include='src/reprollm/core/redaction.py'
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -q -m security
uv run python scripts/gen_rules_doc.py --check
uv run python scripts/gen_profiles_doc.py --check
uv run python scripts/gen_cli_doc.py --check
uv run python scripts/gen_quickstart.py --check
```

先检查 coverage，再执行可能改动 coverage 数据的后续测试。`--locked` 失败需要调查，不能自动升级依赖掩盖失配。登记 slow marker 警告可作为独立小修复，但不把重型 slow 测试悄悄加入默认运行。

Schema freshness 必须生成到临时目录并比较完整集合与文件字节，避免先覆盖 tracked schemas 后失去差异：

```bash
uv run python - <<'PY'
from pathlib import Path
import subprocess
import tempfile

with tempfile.TemporaryDirectory(prefix="reprollm-schema-") as temp:
    target = Path(temp)
    subprocess.run(["reprollm", "schema", "export", "--out", str(target)], check=True)
    expected = {p.relative_to(Path("schemas")): p.read_bytes()
                for p in Path("schemas").rglob("*.json")}
    actual = {p.relative_to(target): p.read_bytes() for p in target.rglob("*.json")}
    if actual != expected:
        raise SystemExit("schema exports differ; inspect the diff before updating tracked files")
PY
```

每项代码任务先写目标回归、后实现、再跑完整质量门；一项任务一个 Conventional Commit，注明任务号、规格段落和快照变化理由。不要添加仅复述实现、没有独立业务预期的测试。单纯文稿改动采用链接、生成文档和内容核验；不得虚称它验证了产品行为。

Linux 本地通过不能替代 CI 中的 Python 3.10 / 3.11 / 3.12、macOS、Windows 矩阵。Windows 按现有 `linux_only` 策略处理，不随意删测试。

在外部案例目录运行时，显式使用本轮 `.venv` 中的 ReproLLM 可执行文件；不要让 `uv run` 因 cwd 变化切换项目。执行所需本机绝对路径只保留在本机操作上下文，分享报告用逻辑变量和相对路径。

## 7. Gate A：每次开发会话的五项目验证

`val.md` 是唯一 gold 来源；本表是定位快照，不授权修改 pins。

| 项目 | 固定 SHA |
|---|---|
| EleutherAI/lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` |
| lm-sys/FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` |
| hiyouga/LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` |
| centerforaisafety/HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` |
| jyhong836/llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` |

会话收尾步骤：

1. 核对每个 checkout 的 SHA、origin、tracked / untracked 全部状态；必须是正确且干净的输入。
2. 每个至少运行 `reprollm audit <checkout> --format json --fail-on never`。保留默认模式的 stdout / stderr；额外 `-v` 运行用于比较已有诊断。运行方式以当前 CLI help 为准。
3. 本会话修改的每个非资源命令都在全部五项目执行。涉及 init、检测、manifest 或 L1 规则时，在各自一次性副本运行 init 和随后 L1 audit；主 checkout 保持干净。
4. 比较完整规则状态、依赖集合、profiles、hints、路径、物理行号、扫描诊断、生成 manifest；摘要计数相同不足以通过。
5. 记录命令、被测 ReproLLM SHA、目标 SHA、退出码、耗时、expected / actual 和所有差异。失败时区分无效输入、既有缺陷、新回归、预期语义变化。

缺项目、脏输入、崩溃、静默跳过、无法解释的 gold 差异都阻止 Gate A 标记完成。修复导致 gold 变化时，基于上游源码独立论证，单独审阅更新；不得把当前程序输出直接变成预期。

## 8. Gate B 与完成状态

里程碑及每次发布执行 `val.md §8` 激活的资源场景：M4 在线 / 离线解析；M5 五项目真实最小推理或训练与 judge；M6 成对单字段变化；M7 export / discover 及已提供资源的 API 分支；发布时执行全部适用矩阵。详细输入恢复、资源记录见 [06](06_Validation_and_Adoption.md)。

建议在会话报告分别记录三个维度：

| 维度 | 允许状态 | 解释 |
|---|---|---|
| 工作 | PLANNED / IN_PROGRESS / REVIEW_READY / IMPLEMENTED / VERIFIED / NOT_NEEDED | IMPLEMENTED 不等于本轮全部 gate 通过 |
| 决策 | NOT_REQUIRED / PROPOSED / APPROVED / REJECTED | APPROVED 必须附具体决定，不用用户泛泛认可替代 |
| 验证 | NOT_RUN / PASS / FAIL / BLOCKED | BLOCKED 必须列缺失输入及恢复步骤 |

`VERIFIED`：任务验收、质量门、适用 Gate A、必要审阅和 CI 都有本次证据。会话完成还须满足 AGENTS 对报告与推送的要求。资源 Gate B 单列；存在阻塞时，工程改动可以达到可审阅状态，但不能写“release-ready / 全部验证通过”。

## 9. 会话报告与下一位 Agent 的交接模板

在现有 `docs/dogfooding/` 或本轮计划目录记录，沿用仓库组织，不另建报告平台。下列字段必填：

```markdown
# Sx-A / Sx-B 会话报告

## 版本与范围

- ReproLLM 起止 SHA；当前分支；保留的既有工作
- 当前 Sprint / Session；本次任务；实际环境

## 任务结果

| 任务 | 工作状态 | 提交 | 定向回归 | 规格依据 | 待决事项 |
|---|---|---|---|---|---|

## 验证证据

| Gate / 用例 | 命令 | 目标 SHA / 输入哈希 | 退出码 | 耗时 | 预期 | 实际 | 证据相对路径 |
|---|---|---|---|---|---|---|---|

## 语义与兼容性差异

- 每个 finding / profile / hint / 文件 / schema 变化及理由
- gold 独立依据及审议状态；隐私检查结果

## 阻塞与恢复

- 缺少的具体输入 / 决定 / 资源；已完成的独立工作；解除阻塞后的第一条动作

## 下一会话

- 可直接开始的任务号及所需输入
- 禁止重复或覆盖的改动；须衔接的模块或接口
```

## 10. 本包相对 v1.0 的关键收敛

- R01 的实际入口是 `plan_init` / `write_scaffold`；R04 的采集入口是 `_collect`，发生在 child 完成后。
- R02 已有原子写入，新增重点是持久化安全边界；`RunPrivacy.value` 不等于结构化秘密检测器。
- R03 增加合并幂等及旧记录回放验收，避免只修首轮投影。
- R05 拆分 Python / Conda 语法；R06 增加路径边界与引用图，scope 决策单列。
- R07 拆分候选过滤、默认诊断与不完整覆盖的规则结论，保留安全扫描事实。
- R04 保留 recorder 环境与宿主信息，明确来源 / 时点；不将整个 environment 清空。
- D02 / D03 共用 wheel 验证；CHANGELOG / release notes 在 PyPI 发布之前检查。
- A01 输入恢复提前开展；独立用户采用和资源 Gate B 不伪装成代码任务完成。

## 11. 依据

基线仓库：[ReproLLM @ 590ee17](https://github.com/EnumaElish123/ReproLLM/tree/590ee1739484bd21e21594e294e7ddf14bfd093f)。仓库路径均相对该根目录；执行时优先核对当前 HEAD 的同名文件。

- [AGENTS.md](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/AGENTS.md)
- [架构与冻结决策](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/docs/plan/00_architecture_and_decisions.md)
- [规范](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/docs/plan/01_specification.md)
- [五项目 gold 与验证门](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/val.md)

各分册中的源码入口、已复现行为、拟定测试预期分别标明；没有执行结果的复选框保持未勾选。
