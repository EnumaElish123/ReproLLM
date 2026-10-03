# Sprint 4：真实 recipe、分发验证与发布门

版本：v1.2 · 日期：2026-10-03 · 状态：PLANNED

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 目标与会话

交付一个声明、实际命令、运行观察和 diff 相互一致的 lm-eval 案例；让文档对应实际安装产物；让发布工作流在执行不可逆发布前完成同一提交的必要检查。

| 会话 | 按顺序执行 | 主要产物 |
|---|---|---|
| S4-A | D01 → D02 | recipe、三层验证记录、统一 wheel 验证入口、版本文档对齐 |
| S4-B | D03 | 发布 gate 改动、故障阻断证据、release readiness 报告 |

D01 输入准备依赖 [06](06_Validation_and_Adoption.md) 的 A01-A，可以在 S1 开始时开展。D01 的真实资源回放若阻塞，先交付静态校验、stdlib probe 和完整待运行输入；D02 / D03 可继续完成可审阅代码，正式发布状态保持 BLOCKED。

D01 正式验收和 A01-B 可分享证据包还依赖 R02-R 的 run 脱敏、R03 的有效值、R04-A 的环境来源及 R04-B 的输入采集时点。准备 recipe 可提前，但不能以当前 post-run 配置快照代替消费证明；这些实现或必要决定未完成时分别记录，不用静态文档通过填补。

禁区：不新增泛化框架绑定语言；不默认要求 32B 模型；不搭建新的发布服务；不重复建设两套 wheel 验证器；不为验证工作流创建并发布试验性正式 tag；不擅自决定下一个公开版本号。

## 2. D01：一个能够证明参数被消费的真实 recipe

### 当前问题与源码入口

`docs/integrations/lm-eval.md` 声明 `cais/mmlu / abstract_algebra`，执行命令却使用 `gsm8k`。manifest 绑定 `--max_gen_toks`，实际 run 命令未传该参数；文末对 exact revision、consumed config 的声明缺少与实际命令一致的证明。

关联入口：`src/reprollm/integrations/lm_eval.py`、`src/reprollm/core/bindings.py`、`scripts/gen_quickstart.py`、`docs/quickstart.md`、现有 examples / dogfooding 文件。

### 固定案例与输入选择

1. 框架源码优先固定 `val.md` 的 lm-eval SHA `b954108c9baaaa934b4ad842033b31a97ee30816`。
2. 任务统一为 GSM8K；模型优先沿用既有案例 `Qwen/Qwen2.5-0.5B-Instruct`。数据集、split、few-shot、metric、aggregation、随机种子、生成 cap 在实际配置与 manifest 中逐项对齐。
3. 优先恢复 `val.md §8.3` 已审阅输入：100 test items、5-shot、cap 32 → 48、`python -m lm_eval run --config validation/eval.yaml`。该命令是正式案例入口；必须核对固定源码和输入，不能只从本文件复制后假定已验证。
4. 如原输入无法取得，可创建一个新的、清楚命名的极小 recipe 输入，保留独立期望和哈希；它不替代原 formal gate。样本数和资源边界在运行前写明。
5. 以 `val.md` 中固定 revision 为已有候选，再确认传给框架的版本参数 / 本地 snapshot 与该 revision 相同。锁定的意图与实际消费证据分别记录。

不要直接把旧示例中的 MMLU 字段改成猜测值。先读固定版本的 `lm_eval/tasks/gsm8k/gsm8k.yaml` 与对应 CLI / config parser，再写最终可运行 YAML。

### 实施步骤

1. 生成映射：manifest 字段 → 实际框架配置 / 参数 → binding → 观测阶段 / 运行中变化 → 独立消费证据。必须涵盖 model revision、dataset/task/split、generation cap、seed、metric；启动前基线和退出后快照均不自动等于实际消费。
2. 优先使用固定框架支持且被实际消费的配置文件，配置中承载 cap，binding 读取同一字段；不声明一个命令没有传入的独立 CLI flag。
3. 基础 binding 不会解析 `--gen_kwargs key=value,...` 内部字段。若最终 CLI 只能用复合参数，先说明现有能力缺口，再实现非常窄且有测试的框架适配；不暗示通用 flag binding 已支持复合语法。
4. 让执行命令显式消费固定 revision / snapshot；如果没有这个能力，导出仅称 `resolved intent`，不称实际观察到 exact model。对 tokenizer、chat template 和文件哈希应用相同证据纪律。
5. 构造 A / B：只改变 cap 32 → 48 或新案例明确的单一参数；固定其他配置。若 config 文件哈希也必然变化，报告两个变化，但单独断言 `generation.max_tokens`，防止 HIGH 文件哈希掩盖 binding 失败。
6. 记录输入、run、lock、diff、export 的一致性；先保存 A 产物，再运行 B，防止输出覆盖。
7. 更新 integration 文档、必要 examples、生成 quickstart 输出；说明三层验证状态。

### 三层验收，分别记录

| 层次 | 内容 | 可以证明 |
|---|---|---|
| L1：静态 / dry-run | manifest load、固定框架 parser 校验、task / metric 对照、bindings 映射、输入 hashes、ReproLLM 无网络路径 | 配置合法、声明和准备的命令一致 |
| L2：stdlib probe | 小程序实际解析同形参数 / 配置并打印实际值，经 ReproLLM 包装为 A / B | 捕获、effective State、diff 与 export 链路正确 |
| L3：真实框架 | 固定版本 lm-eval 实际运行有限输入，生成真实 run / metrics | 真实工作负载消费了输入与参数；按可取得证据限定表述 |

L2 不替代 L3。L3 没资源时保留 BLOCKED 及精确恢复命令，不把 dry-run 写成“完整复现已通过”。运行产生的准确率和文本不是固定 gold；验证身份、有限执行、消费参数、输入完整性和预定 drift。

### 必须交付的文件

优先复用仓库现有 examples / docs/dogfooding 结构；新增目录时建议命名 `examples/lm_eval_replay/`，明确是拟新增路径。

- README：从安装到 A / B / diff / export 的完整命令与资源条件。
- 两份实际框架配置或一个基线加明确单字段补丁；可加载的 ReproLLM manifest。
- 输入和独立预期清单；每个文件 SHA-256；固定上游版本。
- 自动化的无网络 L1 / L2 回归；L3 的实际结果或阻塞报告。
- `docs/integrations/lm-eval.md` 改正；生成文档保持 freshness。

### 完成条件

- [ ] 声明 / 命令 / config / binding / task / metric 相互对应，无 MMLU 与 GSM8K 混用。
- [ ] 模型版本的“声明、解析、消费”三种证据明确。
- [ ] A / B 的目标语义叶子存在且数值正确；不以摘要 HIGH 替代字段断言。
- [ ] L1 / L2 有回归；L3 有真实结果或单列 BLOCKED。
- [ ] L2 增加“消费后改写 config”的案例：消费值有独立依据，记录遵循 R04-B，不能把改写后的值当作已消费参数；可分享产物经过 R02-R 检查。
- [ ] 全质量门、适用五项目 Gate A、文档 / CHANGELOG 完成。

建议提交：`docs(recipe): align lm-eval declarations with consumed inputs (D01)`。若必须增加 adapter，单列具体实现子任务与测试，保持一任务一提交。

## 3. D02：同一份候选 wheel 的实装与文档对齐

### 已确认现状

README 已区分 main 未发布功能，不能再把它描述为完全没有版本说明。`docs/community/roadmap.md` 与 CHANGELOG 已有状态来源，应复用。

`scripts/gen_quickstart.py::_run` 使用生成器自己的 `sys.executable`，环境中还可能保留 `PYTHONPATH`；教程中的 install 命令仅被渲染，并不证明它安装得到的 wheel 能完成教程。

### 实施步骤

1. 建立一张实际版本证据表：当前 SHA、代码 version、候选 wheel metadata、已发布版本及其功能范围。source 与 PyPI 都叫 0.6.1 不等于功能相同。
2. 新增或扩展一个分发验收入口，建议文件名 `scripts/validate_distribution.py`。这是待实现入口，当前不能假定存在；D03 直接调用它。
3. 输入为**已经构建好的 wheel 文件**。在源码目录外创建临时 venv，安装该 wheel，使用全新 cwd；清除 `PYTHONPATH` / 用户 site / editable source 注入，记录实际 import 路径属于新 venv。对外报告不保留机器绝对路径。
4. 从安装包运行离线 walkthrough：audit → init → lock offline / check → run A / B → diff → export → schema / profile / template 等包数据读取。优先复用已有 12 步 quickstart 的命令语义和独立预期。
5. runner 可以使用源码中的外部测试 fixture，但被测 import / CLI 必须来自 wheel；不能因 sdist 不带 tests / docs / examples 就从源码导入产品模块补齐。
6. 若扩展 quickstart 生成器，显式传被测 Python / CLI 路径，让它记录使用的可执行文件；避免无意继续使用生成器解释器。
7. README、roadmap、CHANGELOG、文档中的 install 与 feature availability 保持一致；使用既有单一状态来源，不再维护第二套同内容表。
8. 处理 Alpha classifier 与 beta 文案的一致性时，以维护者选定发布状态为准；不只改标签制造成熟度。

安装依赖可使用预置缓存或正常包分发源；离线 walkthrough 自身不发真实 HTTP。不要把 `--no-deps` 导致未安装运行依赖的失败误判为 wheel 缺陷，也不要把开发环境依赖全复制进新 venv 后宣称独立安装成功。

### 拟新增入口的验收调用

实现后，预期可从仓库根执行下述形式。尖括号是实际产物占位符，不是现有 CLI 参数值：

```bash
uv build
uv run python scripts/validate_distribution.py --wheel <built-wheel-path>
```

runner 不自行重新 build；输出包括 wheel SHA-256、分发版本、被测代码 SHA 的关联证据、import 隔离检查、各命令退出码和目标断言。源码 SHA 的关联来自构建步骤生成的产物清单；没有清单时标为未确认，不能用 validator 当前 checkout 的 HEAD 或相同 version 猜测 wheel 来源。必要时增加显式构建清单输入，并输出安全的 JSON 摘要供 release workflow 使用。

### 故障与成功验收

| 场景 | 预期 |
|---|---|
| 正确 wheel，干净 venv / cwd | 完成完整离线路径；schema、profiles、模板等 package data 可加载 |
| 刻意残留源码 `PYTHONPATH` | runner 清除影响或拒绝；不能从 checkout 导入后通过 |
| wheel 缺关键 package data | 在相应实际命令明确失败 |
| wheel metadata 与目标版本 / tag 不一致 | 明确失败；不继续发布 |
| 只有 `--version` / `--help` 成功 | 不足以通过 distribution gate |
| generator 的 source 测试通过，但候选 wheel 失败 | 候选仍失败，不以 source 结果覆盖 |

- [ ] D02 / D03 只有一个验证入口，源文件生成和候选 wheel 测试职责明确。
- [ ] wheel 的哈希和新环境导入证据可核对。
- [ ] 文档所示安装方式与验证对象一致；未来公开版本号由正常发布决定。
- [ ] 独立 ReproLLM Action 仓库 / tag 的更新另行协调；本仓库改动不等于 `@v1` 自动更新。
- [ ] 全质量门和 S4-A 的五项目 Gate A 完成。

建议提交：`test(distribution): validate walkthrough against the candidate wheel (D02)`。

## 4. D03：发布前验证同一提交和同一产物

### 已确认现状与需要保留的能力

`.github/workflows/release.yml` 已单次 build，上传 `dist` artifact，后续 publish 下载同一 artifact。保留这条产物链。

缺口是 build 前仅运行安全测试子集，没有结构性依赖同一 tag commit 的完整质量门；GitHub release notes 从 CHANGELOG 提取且检查为空，发生在 PyPI 发布之后。CHANGELOG 错误可能在不可逆发布完成后才暴露。

### 目标依赖关系

| 阶段 | 输入 | 必须阻断的失败 |
|---|---|---|
| quality | tag 解析后的同一 commit | 测试 / 类型 / lint / schema / 生成文档 / 必要平台检查失败或缺失 |
| preflight | 同一 commit 的 version、tag、CHANGELOG | tag 与版本不符、对应 notes 缺失 / 空白、资源验证不就绪 |
| build | 同一 commit，锁定依赖 | 构建失败或产物 / metadata 不一致 |
| distribution-check | 本次 build 的 wheel | D02 实装不通过或哈希不符 |
| publish | 上述全部成功的同一 artifact | 任一门未完成、取消、错误 SHA、缺证据均不可执行 |
| github-release | 已验证 notes 与同一 dist | 不重新生成一个可能不同的版本说明 / 发布包 |

quality 与 preflight 可以按仓库工作流合理安排先后，但 publish 必须依赖二者及 distribution-check 的成功，不能只读“最新 main CI 是绿色”。

### 实施步骤

1. 将现有 CI 质量门抽成可复用 workflow，或实现严格验证同一 SHA 的检查结果。优先复用，避免 CI 与 release 各维护一套漂移的命令。
2. 在 tag 事件正确解析目标 commit；质量检查、源码 checkout、build、D02 结果和资源证据绑定同一个 commit。缺失、取消、失败、来自另一个 SHA 的结果均阻断。
3. CI 与 release 的依赖安装统一使用锁定模式，失配显式失败，不静默更新 `uv.lock`。
4. 在任何 PyPI 写入前提取并验证 CHANGELOG 对应版本，拒绝只有空白的 notes；将准备好的 notes 作为 artifact 传给 GitHub Release job。
5. build 一次，生成含 commit、版本、wheel / sdist hashes 的构建清单；D02 验证该 wheel；publish 下载相同 artifact。`dist` 中只放可分发包；notes、构建清单与验证摘要放独立 `release-evidence` artifact，避免 PyPI job 尝试上传 JSON / Markdown。不要在 publish 前另跑一次 build。
6. 保留 PyPI OIDC 和最小权限，发布权限仅在所需 job。不要引入长期 PyPI token 或扩大整个 workflow 权限。
7. 正式 Gate A / B 证据必须来自当前候选 SHA。采用最小的结构化结果摘要 / artifact 关联现有报告即可，不建设新服务。摘要至少记录目标 SHA、适用矩阵、每项状态、输入 / 报告哈希；BLOCKED、缺记录、错误 SHA 均阻断发布。
8. 资源验证可在具备资源的既有环境完成，普通无资源 CI 不假装运行 GPU。把真实结果传入发布前检查；不能沿用早期版本的 resource waiver。

### 需要实际验证的失败路径

| 故障注入 | 必须观察到 |
|---|---|
| 任一质量检查失败 / 取消 / 未产生 | publish 不执行 |
| main 绿色，但 tag SHA 不同 | 无法代替候选质量结果 |
| 对应 CHANGELOG 段不存在或只有空白 | 在 PyPI job 之前失败 |
| tag 与包 metadata 不一致 | 在 build / publish 边界之前失败 |
| wheel 实装失败、wheel hash 被替换 | publish 不执行 |
| Gate B 结果 BLOCKED、缺失或属于旧 SHA | 候选报告可保存，正式 publish 阻断 |
| 全部检查满足 | 被验证的 wheel 与传给 publish 的文件哈希一致；release 使用预检 notes |

验证方式以无发布的 workflow 路径、可复用任务调用和对真正验收逻辑的测试为主。不要只断言 YAML 中出现某字符串；不要触发真实 PyPI 发布来验证门的条件。

### 完成条件

- [ ] 代码变更可审阅，成功及关键失败路径有证据。
- [ ] 同一 SHA、单次 build、同一 wheel、同一 notes 的关联完整。
- [ ] CHANGELOG 检查发生在 PyPI 发布之前。
- [ ] 本地质量门、CI 和 S4-B 五项目 Gate A 完成。
- [ ] Gate B 的实际状态逐项列出；只有适用矩阵全部通过才写 release-ready。
- [ ] 发布执行本身按届时授权和候选状态进行，本 Sprint 不要求为验收而发布版本。

建议提交：`ci(release): gate publication on candidate quality and artifacts (D03)`。

## 5. Sprint 收尾与证据交接

- [ ] 向 A01-B 提供最终 recipe、实际命令、候选 wheel hash 和三层验收状态。
- [ ] 向 A02 提供新用户可执行的安装方式及已知限制。
- [ ] 向 A03 提供有来源的质量、发布和维护事实，不预填采用人数。
- [ ] S4-A / S4-B 分别记录本次 Gate A；发布阻塞与代码完成分开。

依据：[lm-eval 文档](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/docs/integrations/lm-eval.md)、[quickstart generator](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/scripts/gen_quickstart.py)、[release workflow](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/.github/workflows/release.yml)、[CI workflow](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/.github/workflows/ci.yml)。
