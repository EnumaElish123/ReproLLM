# S1-A / R00 当前执行基线

日期：2026-10-10。范围来自
[S1-A 任务卡](../../plan/reliability-2026-10-03/01_Persistence_and_State.md#2-r00建立可继续的执行基线)
及[执行总则](../../plan/reliability-2026-10-03/00_Execution_Guide.md)。

## 版本与范围

- 实际起始 main HEAD 为 `d7d9d63390335788e1804e0b5af87c6d64f319cd`；初始工作区干净。
  不回退到审查 SHA。已核对审查 `590ee17` 之后的 `781366e` / `d7d9d63` 两份方案提交：
  `src`、`tests`、`schemas`、`pyproject.toml`、`uv.lock` 无差异，没有后续产品修复可复用。
  以下复核仍以实际 HEAD 为准，未因为产品树相同而省略行为重测。
- 环境为 Linux、Python 3.12.14、ReproLLM 0.6.1、Git 2.25.1；
  `uv sync --locked --dev` 成功，未更改依赖或 lock。
- 本报告只记录 R00：质量基线、最小问题复核、五项目输入与状态账本。
  根会话随后实施 R01；其新增失败回归、实现、最终质量门与 Gate A 单独登记，
  不改变这里已经冻结的故障观察。
- 合成复核只创建一次性输入；无网络、真实凭据、GPU、受限模型或重依赖。
  Git 通过 `core.proc.run_cmd`；GPU capture 使用 unavailable stub。
  child 环境案例只创建 stdlib venv 和 `dist-info` 元数据，未安装或导入 torch。

## 任务账本

R00 的本地质量、问题复核与冻结候选五项目 Gate A 已完成；五项目输入全部有效。
提交、推送与 CI 由根会话完成。下表记录的是复核状态，不是产品修复完成状态。
完整值、退出码、耗时及代码定位见
[r00-reproductions.json](r00-reproductions.json)。

| 任务 | 工作状态 | 当前复核 | 提交 | 规格依据 / 下一步 |
|---|---|---|---|---|
| R00 | REVIEW_READY | 质量与 Gate A PASS；13 个最小缺陷仍复现；输入 5/5 有效 | 本报告随 R00 独立提交；当前尚未提交 | 执行总则 §§4、6、7、9；提交、推送与 CI 由根会话登记 |
| R01 | PLANNED（冻结时点） | 仍复现 | 无产品修复提交 | 规格 §§3、11、21；进入 S1-A 实现，先建立保全回归 |
| R02 | PLANNED | 仍复现 | 无 | 规格 §§4、16；S1-B 默认拒绝不安全 lock 写入 |
| R02-R | PLANNED | 仍复现 | 无 | 规格 §§5、15、16；S1-B 保护真实包装运行的全部持久化副本 |
| R03 | PLANNED | 仍复现 | 无 | 规格 §§15.1、17、18；S1-B 修复 CLI 选择与 merge 不变量 |
| R04-A | PLANNED | 仍复现 | 无 | 规格 §§4.4、5、17；S3-B 明确 recorder/child 来源与时点 |
| R04-B | PLANNED | 仍复现 | 无 | 规格 §§5.1、15、17；S3-B 明确输入基线、后续变化与消费证据 |
| R05-A | PLANNED | 仍复现 | 无 | 规格 §12.2；S2-A 修正 Python exact 语义 |
| R05-B | PLANNED | 仍复现；R05-S 决定未取得 | 无 | 规格 §12.2 仍允许单等号完整版本；先处理具体冲突再合入修复 |
| R06-A | PLANNED | 仍复现 | 无 | 规格 §§11、12.2；S2-A 保留同名文件的路径身份 |
| R06-G | PLANNED | 仍复现 | 无 | 规格 §§11、13、16；S2-A 首先限制所有静态内容读取 |
| R06-P | PLANNED | 仍复现 | 无 | 规格 §§11、12.2；S2-B 接续公共读取边界并建立真实 include 图 |
| R07-A | PLANNED | 仍复现 | 无 | 规格 §§11、13；S3-A 在预算前过滤环境候选 |
| R07-B | PLANNED | 仍复现；UX 合同需同步修订 | 无 | 规格 §13 当前只要求 verbose warning；S3-A 改默认披露 |
| R05-S | PLANNED；决策 PROPOSED | 已知 Conda 规范冲突明确登记 | 无 | 仅阻塞依赖它的 R05-B；不把执行整个方案等同于批准具体语义 |
| R06-B / R07-C / R08-A / R08-B | PLANNED；决策 PROPOSED | scope、覆盖率与漂移策略提案，不作为既有缺陷的默认验收 | 无 | 按策略分册形成具体决定；Issue #9 不由本报告自动批准 |
| R04-S | PLANNED；条件任务 | 尚未确定是否需要 schema | 无 | R04-A/B 先确定来源与时点合同；必要时履行 D-39/D-41 |

## 最小重建场景与实际观察

所有输入在空的一次性项目根构造；每个 manifest 都带 `schema_version: 1`、
合法 `project.name` 和 `experiment.profiles`。普通合成密钥没有服务商前缀；
前缀密钥、绝对 cache 路径仅用于安全边界复核，原值不进入共享证据。
任务卡保留完整输入合同，可直接重建，不依赖本机临时目录。

| 任务 / 最小输入 | 独立依据 | 实际行为 | 退出码 / 耗时（秒） |
|---|---|---|---|
| R01：中文目录，已有合法 saved-project manifest；`init <case> --force --profiles inference` | 已独立以 YAML + Manifest 校验原始字节合法；保存旧字节 | manifest 消失，旧字节未保全；辅助目录已经创建 | CLI 2 / 0.478 |
| R02：inference/training/privacy 自由参数各放普通 keyed secret、前缀值、绝对 cache、list 内 secret 四类输入；旧 lock marker；`lock <case> --offline` | 12 个最终 lock 检查与旧字节比较 | 12/12 写入不安全值并覆盖旧 lock；诊断未回显值 | 每个 CLI 0；12 场景合计 0.8001 |
| R02-R：`config.json` 的 settings 对象含普通 api_key，绑定 custom.settings 并声明配置文件；child 真正读取 JSON | 对整个实际 run 目录扫描合成值 | run.json 和 files 配置快照同时包含原值；warnings 为空 | child 0 / 0.0704 |
| R03：真实 argparse A 为 temperature 0.1 后 0.9，B 反序；绑定同一字段 | child 将实际解析值写入独立 consumed.json，分别为 0.9 / 0.1 | 有序 observations 正确；from_run、两次 merge 和序列化重载后两边都选 0.1；temperature diff 缺失；HIGH gate 0 | child 0、diff 0 / 0.217 |
| R04-A：另一个 stdlib venv 只创建 torch 0.0.123 dist-info | child 用 importlib.metadata 独立读取 0.0.123 | recorder packages 为空；没有 source/phase 字段，warnings 为空 | child 0 / 0.2539 |
| R04-B：配置初值 0.1；child 先记录消费值，再改成 0.9 | consumed.json 为 0.1；比较开始前/结束后文件哈希 | observation 与 effective State 为 0.9；文件哈希只匹配结束后内容，warnings 为空 | child 0 / 0.0653 |
| R05-A：requirements/PEP621 wildcard、requirements local、Poetry local/pre、Pipfile local | 独立版本表达式分类表 | wildcard 被判 exact，requirements 同时成为 lock；requirements local 正确，Poetry/Pipfile suffix 漏识别 | driver 0 / 0.0036 |
| R05-B：`python=3.11`、`torch=2.5`、`torch==2.5.1`、版本/build 三段形式 | 计划的 Conda 独立语义表；现行 spec 冲突单独登记 | exact_version 依次为 3.11、2.5、空、2.5.1 | driver 0 / 0.0009 |
| R06-A：根 pyproject 有项目依赖/Python；zz_tools 同名文件只有 Ruff | 两个真实路径均存在 | 根依赖丢失，dependency-manifest rule FAIL；Python declaration rule PASS | audit 0（fail-on never）/ 0.0691 |
| R06-G：普通 requirements/Python symlink 指向外部合成文件；另测显式 max_bytes 与绝对参数 | Path.open spy 实际记录外部打开 | 外部包与 import 被扫描；8 次外部 open，两种额外读取同样成功，warnings 为空 | driver 0 / 0.0025 |
| R06-P：外部 -r；另用根 include deps/base.txt 与未引用 sibling requirements | 可达图只含 torch；外部目标存在 | 外部 openai 被读入且 unparsed 为空；根 lock 包集合为空；未引用 nested lock 反而借入 torch | driver 0 / 0.0025 |
| R07-A：业务 peft 源码 + 501 个 venv vllm 文件，同样内容分别无 Git / Git | 相同业务内容；只允许 Git 事实不同 | fallback 只扫描业务；Git 选 500 个 venv 文件并漏掉业务，截断 502 候选 | driver 0 / 0.2706 |
| R07-B：501 个实际业务 Python 文件；默认 text、默认 JSON、verbose JSON | 三次输出分别检查 stdout/stderr，JSON 独立解析 | 默认两种模式无截断提示；verbose stderr 显示 500/501；JSON stdout 有效 | 三次 audit 0（fail-on never）/ 合计 0.6893 |

委派的 12 个场景合计 2.4452 秒，driver 最终退出 0；R01 单独计时。
driver 成功表示缺陷观察与基线断言成立，不表示产品已通过修复验收。

## 质量基线与环境失败

完整命令数组、每次退出码、耗时、schema 文件集合与原始日志摘要哈希保存在
[r00-quality.json](r00-quality.json)。原始输出含机器路径，因此共享证据保留
测试名称、关键原因、完整命令结果与哈希，不复制原始 traceback。

| Gate / 用例 | 命令 | 输入 | 退出码 | 耗时（秒） | 实际 |
|---|---|---|---:|---:|---|
| 锁定安装 | `uv sync --locked --dev` | frozen HEAD | 0 | 0.035 | 依赖未升级；Python 3.12.14 / ReproLLM 0.6.1 |
| 首次 full pytest | `uv run pytest -q --cov=reprollm --cov-report=term --cov-fail-under=85` | 原始 Git 2.25.1 | 1 | 188.141 | 1,927 passed、3 failed、2 deselected、1 warning；覆盖 93.29% |
| 首次 quickstart freshness | `uv run python scripts/gen_quickstart.py --check` | 原始 Git 2.25.1 | 1 | 0.134 | 内部 git init -b 返回 129 |
| Git 兼容定向复核 | `uv run pytest -q tests/unit/test_generated_docs.py tests/unit/test_onboarding_examples.py` | 临时 Git shim PATH | 0 | 约 68 | 23 passed；精确小数/原始日志未保留，未伪造 |
| 兼容 full pytest | 同首次 full pytest 命令 | 临时 Git shim PATH | 0 | 294.839 | 1,930 passed、2 deselected、1 warning；覆盖 93.29% |
| redaction 分支门 | `uv run coverage report --fail-under=100 --include=src/reprollm/core/redaction.py` | 完整 pytest coverage | 0 | 0.183 | 59 statements、24 branches，100% |
| Ruff check / format | `uv run ruff check .`；`uv run ruff format --check .` | frozen HEAD | 0 / 0 | 0.090 / 0.094 | 全部通过 |
| Mypy | `uv run mypy src/` | frozen HEAD | 0 | 0.324 | 通过 |
| security | `uv run pytest -q -m security` | 合成/离线测试 | 0 | 9.400 | 29 passed、1,903 deselected、1 warning |
| 生成规则/档案/CLI/quickstart 文档 | 四个 `scripts/gen_* --check` | frozen HEAD + Git shim | 全部 0 | 0.395 / 0.412 / 10.428 / 11.308 | 全部通过 |
| Schema freshness | `reprollm schema export --out <temporary-directory>` 后完整集合/字节比较 | 10 份 tracked schemas | 0 | 0.493 | 文件集合与字节全部一致 |

三个首次 pytest 失败都来自 quickstart 相关生成检查；直接 quickstart 命令揭示
本机 Git 2.25.1 不支持 `init -b`。临时 shim 只在验证进程的 PATH 中生效，
把带分支参数的 init 转为普通 init 加 symbolic-ref，其他命令交给原 Git；
定向 23 个案例和完整质量门随即通过。未修改仓库脚本、测试、依赖或系统 Git。
这属于明确记录的环境兼容处理，不是产品修复，也不是将原始失败隐藏为 PASS。
既有未知 `slow` marker 警告保留；未扩大默认 slow 测试集合。

## 五项目输入与 Gate A

输入清单见 [r00-input-inventory.json](r00-input-inventory.json)。五项目均存在，
origin 与 pin 正确，tracked/untracked porcelain 都为空；无需 fetch 或恢复。

| 项目 | 固定 SHA | Python 文件数 | 输入状态 |
|---|---|---:|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | 816 | PASS，clean |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | 148 | PASS，clean |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | 311 | PASS，clean |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | 123 | PASS，clean |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | 46 | PASS，clean |

Gate A 使用冻结 `d7d9d63` 的逐字节核验 Git archive（`source_mode=frozen_candidate`），
避免根会话正在实施的 R01 混入 R00 的 baseline。独立 expected 来源为 UX3 retained
完整 L0/hints/diagnostics 和 UX2 `b00f06c` 的审阅记录。缺失的完整 L1/manifest payload
只由该历史代码在一次性副本中重建，且先满足已审阅摘要哈希；没有把候选输出复制成 gold。

第一次历史 oracle 恢复的 45 个命令全部退出 0（157.077170 秒），完整报告、manifest、
hints 摘要都匹配；三个 FastChat 独立源码定位检查失败，因为检查假定模型 ID 字面量与
AST 调用起始行处于同一物理行。上游实际是多行表达式。修正仅让检查在原始起始行锚定的
AST 表达式范围查找准确 ID，没有更改产品路径、既有报告行号或 gold。
[首次检查失败](r00-gate-initial-oracle-summary.json)与
[独立修正证明](r00-gate-harness-correction.json)分别保留，不把首次恢复标为 PASS。
修正后重新完整恢复：45 命令、145 完整比较、156.295895 秒全部通过，详见
[历史 oracle summary](r00-gate-historical-oracle-summary.json)。
这个 PASS 属于 `source_mode=reviewed_oracle` 的历史输入恢复，不能代替实际候选执行。

执行内容包括五项目默认/verbose L0、完整 hints、普通 init、随后 L1 和 manifest load；
所有 mutating 命令在一次性副本执行。完整比较保留 rule sets、profiles、hints、路径、
物理行号、诊断和 manifest，而非只比摘要数。实际冻结候选 Gate A 已全部通过：
**45 个主要命令、180 项完整/独立源码比较，退出码全部为 0、零 delta**，
主要 subprocess 合计 157.769166 秒。证据见
[Gate A summary](r00-gate-a-summary.json)、[完整命令](r00-gate-a-commands.json)、
[完整比较](r00-gate-a-comparisons.json)及五份项目完整 payload。

| 项目 | 主要命令数 | 主要 subprocess 总耗时（秒） | 预期 / 实际 | 完整证据 |
|---|---:|---:|---|---|
| lm-evaluation-harness | 9 | 115.862744 | 历史 full L0/L1、manifest、hints、诊断及 source gold 完全匹配 | [完整 payload](r00-gate-a-lm-evaluation-harness.json) |
| FastChat | 9 | 9.173257 | 全部匹配，零 delta | [完整 payload](r00-gate-a-FastChat.json) |
| LlamaFactory | 9 | 12.291328 | 全部匹配，零 delta | [完整 payload](r00-gate-a-LlamaFactory.json) |
| HarmBench | 9 | 15.644522 | 全部匹配，零 delta | [完整 payload](r00-gate-a-HarmBench.json) |
| llm-dp-finetune | 9 | 4.797315 | 全部匹配，零 delta | [完整 payload](r00-gate-a-llm-dp-finetune.json) |

另外 15 个来源 metadata 复核命令全部退出 0，合计 0.563270 秒，
单列于 [input-check commands](r00-gate-input-check-commands.json)，不混入 45 个主要命令计数。
候选 archive inventory SHA-256 为
`cdd9a0b0838603627600a655ac367a2101ed6a72b0841737b03fad4abf374e37`，
[frozen-source provenance](r00-gate-frozen-source.json)绑定实际 SHA 和完整源码集合。
只从 audit JSON 去掉 `generated_at`，另验 UTC 秒级格式；完整比较保留
`reprollm_version: 0.6.1`。LlamaFactory 既有 tracked secret-file CRITICAL、
各项目未精确固定依赖与 lm-eval 816/500 截断保持不变，没有把它们改成产品 PASS。
R00 的本地证据已齐备，但仍须提交、推送与对应 CI，故当前工作状态是 REVIEW_READY。

## 语义与兼容性差异

R00 未更改产品行为、schema、gold、pin、漂移等级或 fail-on；所有最小场景均属
既有问题的当前复核。记录中的外部相对 source_file 是越界缺陷观察，不是接受的新路径合同。
当前执行环境唯一调整是已说明的临时 Git 兼容 PATH。保留结果 JSON 中没有绝对机器路径、
主机名、用户名、真实或合成密钥原值；临时 run 目录中的泄漏样本未入库。

## 阻塞与恢复

- R05-S 的具体 Conda/spec 语义决定未取得；先准备可审阅规范提案，继续 R06-G/R05-A 等独立任务。
- R08-A/B、R06-B 和 R07-C 均为策略 PROPOSED；本报告不改变默认漂移/scope/规则结论。
- R04-S 为条件 schema 工作；必要字段方案与 D-39/D-41 决定取得后才写新格式。
- 本次普通 S1-A 会话未激活里程碑/发布 Gate B。VAL-R01/R02/R03 继续依照
  [pending-resource-validation.md](../pending-resource-validation.md) 和 `val.md` 保留 BLOCKED；
  未用 stdlib/metadata/离线探针替代 GPU、paid API 或 restricted model 成功验证。
- 本地质量通过不能替代远端 CI；R00 提交、main 推送与 CI 状态由根会话报告登记。

## 下一步与交接

现在进入 R01，按任务卡先编写字节/权限保全失败回归，再实施内存校验、必要辅助文件准备、
原子替换与正常异常清理。保持 project.name schema；非法目录名使用任务卡允许的合法 fallback。
不得顺便修 lock、run redaction、State、scanner 或 dependency parser。

S1-B 从 R02 → R02-R → R03 继续；读取本次完整观察与 R01 最终报告。
R02/R02-R 的安全分类分别验收拒绝写入和 run 脱敏；R03 保留所有有序 observations，
同时覆盖 from_run、多次 merge 和 roundtrip。后续 R04 接续这一选择合同。
冻结缺陷证据不改为修复后结果；新验证另存，避免覆盖本报告中的原始故障基线。
