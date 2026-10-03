# 专项方案：语义决策、策略变更与兼容性

版本：v1.2 · 日期：2026-10-03 · 状态：PROPOSED

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 使用方式与交付边界

本文件处理需要明确产品语义或兼容性决定的工作。每个任务先产出完整提案、源证据、测试预期和可审阅改动，再按仓库要求取得适用决定。已在当前会话 / 仓库记录中获准的决定直接沿用，不重复索要许可。

| 会话 | 交付 |
|---|---|
| P-A | 核对已有决定；提前准备 R05-S，并按 R08-A、R06-B、R07-C、R04-S、R08-B 的相关性准备具体提案；没有触发的 R04-S 标明 NOT_NEEDED |
| P-B | 根据逐项决定落实被接受的范围、测试和迁移；被拒绝或待决事项保持原合同并记录理由 |

这是独立的设计 / 审议工作流。实际代码任务仍按“一任务一提交、先测试、完整质量门、每会话五项目 Gate A”执行；范围不足以在一次会话完成时记录后续会话，不压缩验收。

下列项目互不构成全局批准开关。R05-S 只阻塞依赖新版本语义的部分，R06-B 不能阻塞同名文件 / 公共读取边界 / include 越界修复，R07-C 不能阻塞候选过滤，R08-B 不能阻塞窄范围 judge 政策，R04-S 只阻塞确实依赖新增字段的部分。R02-R 的脱敏模式补充和 R04-B 的输入时点合同也须形成具体材料，按相同审议流程处理，不因纳入任务表而自动视作规范已修改。

## 2. 统一决策材料

每份提案包含以下内容，建议放在本轮计划下 `proposals/<task-id>.md`：

1. 当前规格、实现、真实输入来源，以及它们是否冲突。
2. 修改前 / 后的字段、finding、severity、退出码、输出示例。
3. 推荐方案与最多两个备选；说明受影响用户和默认行为。
4. 精确文件清单；是否触碰 D-41 的 redaction / engine / schema。
5. 新旧读写兼容矩阵、迁移或保持历史记录的策略。
6. 独立预期测试；五项目 gold 逐项差异；必要 Gate B。
7. 可直接裁决的问题和决定记录：接受范围、未接受范围、来源、日期、后续任务。

不要只写“请确认方案”。不要为了获得许可留下本可完成的复现、来源核验和样例设计。需要 issue 时遵循 AGENTS；Issue #9 已存在，不另开重复议题。没有对外写入授权时，保留完整草稿供维护者审阅。

## 3. R08-A：judge 直接参数叶子的 HIGH 策略

### 当前合同与推荐改动

入口：`src/reprollm/diff/drift_severity.yaml`、`src/reprollm/diff/severity.py`、`src/reprollm/profiles/llm_judge.yaml`、`judge_only.yaml`、`tests/unit/diff/test_severity.py`、`tests/unit/cli/test_diff.py`。

当前 `*` 只匹配一个路径 segment，first-match 生效，profile overrides 在默认表前。`evaluation.judge.*` 不匹配 `evaluation.judge.params.max_tokens`，后者落到默认 MEDIUM。这与 Issue #9 的待审议范围一致。

推荐仅在默认表较宽的 judge 行前加入：

```yaml
- { path: "evaluation.judge.params.*", severity: HIGH }
```

该行是拟修改内容，不代表当前已生效。保留现有单段 wildcard 语义和 built-in profiles；不在父 profile 塞入新的宽泛 override，以免覆盖用户子 profile 的精确 LOW / NONE 设置。

### 修改前 / 后验收表

| 路径 / 场景 | 当前默认 | 提案通过后的默认 |
|---|---|---|
| `evaluation.judge.params.max_tokens` | MEDIUM | HIGH |
| `evaluation.judge.params.temperature` | MEDIUM | HIGH |
| 其他 judge 直接 params 叶子 | MEDIUM | HIGH，按该窄层级合同 |
| `evaluation.judge.params.nested.x` | 未命中新行，按原表 | 保持原合同，不递归提升 |
| `privacy.mechanism.params.target_epsilon` | MEDIUM | 不变，交 R08-B |
| 用户精确 override 为 LOW / NONE | 用户设置优先 | 用户设置仍优先 |

新增、修改、删除三种 drift 都测试；不能只测 max_tokens 的 changed。验证继承 profile 下用户精确覆盖、JSON 确定性、severity 过滤、self-diff 和 `--fail-on HIGH`。

### 防止被其他 HIGH 掩盖的验收

1. 创建纯 CLI cap A / B，不修改已跟踪 config 文件，也不留下 dirty tree。
2. 确认除目标 judge 叶子外没有其他 HIGH 路径；argv 等变化可以按当前低等级存在。
3. 修改后默认目标 HIGH，HIGH gate 失败退出；用户将该叶子 override 为 LOW / NONE 后 HIGH gate 不再因该叶子失败。
4. 对 formal FastChat / DeepSeek 256 → 384 案例，保留历史记录中 nested leaf MEDIUM、config hash HIGH 的事实。只对新策略实施后的回放建立前瞻性 gold 补充，不重写历史结果。

### 交付与批准后执行

- [ ] 读取 Issue #9 和最新维护者决定，复用已有讨论。
- [ ] 策略行、规格 §18、CHANGELOG、窄范围回归和 gold amendment 草稿齐全。
- [ ] 决定明确后，仅实施该范围，运行 full quality + Gate A；触发 formal 回放时按资源状态执行。
- [ ] UI / README 不再用原有 config-hash HIGH 结果证明 judge 参数政策已经正确。

建议提交：`fix(diff): classify direct judge parameter drift as high (R08-A)`。

## 3.1 R05-S：精确版本与 requirements-as-lock 的规范修订前置

### 已确认冲突

在 `781366e89362a54d9036d3aed070fad169ba8204`，规范 §12.2 将 Conda `name=version`（single `=` with a full version）视为精确固定，并把 requirements-as-lock 描述为每个非注释行使用 `==`。前者与无 build 的 Conda 单等号前缀语义冲突；后者未明确排除 `==2.5.*` 及解释 include 闭包。

2026-10-03 核对的独立依据：[Conda MatchSpec](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/) 将无 build 的 `=1.2.3` 规范化为前缀匹配，而 `foo=1.0=py27_0` 规范化为 `foo==1.0=py27_0`；[PyPA version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/) 将 `.*` 明确定义为 prefix matching。实施前核对来源，不新增 Conda 依赖来完成产品解析。

### 具体待接受范围

| 项目 | 拟定规范文字 / 语义 |
|---|---|
| Python 单版本 | 受支持格式下的无通配符单版本限制可视为版本精确；local/pre/post/dev/epoch 不因纯数字正则被拒绝；不宣称构建或文件哈希一致 |
| Python 通配版本 | `==2.5.*` 非 exact，不能单独使 requirements 成为精确 lock |
| Conda 单等号且无 build | `python=3.11`、`torch=2.5.1` 均为前缀限制，非 exact；不能用点的个数判断 |
| Conda 双等号 / 精确三段形式 | 支持 `torch==2.5.1` 与无 wildcard 的 `torch=2.5.1=cuda12.1`；version/build/channel/platform 的保证分别说明 |
| requirements-as-lock | 只使用合法根内实际 include 闭包；有效声明均精确且没有未解决的引用/语法问题时才满足本轮合同；未引用 sibling 不提供证明 |

这是具体提案，状态仍为 PROPOSED。本次维护者授权修订开发方案，不代替规范文字批准或任何 D-41 代码审阅。

### 交付与依赖

1. 在 R00 后准备 §12.2 的精确 before/after 修订、格式支持表、相关测试及完整 finding 变化。检查 R05-A / R06-P 的规范措辞是否需同步，不机械阻塞已有明确缺陷修复。
2. 按 AGENTS 的 spec issue/决定流程记录接受范围。R05-B 的实现合入必须引用该决定，不能保留矛盾规范却修改测试期望。
3. 核对五项目固定源文件，以独立版本语义解释每项 delta；gold 变化另审，不复制 parser 当前输出。
4. 通过后同步规范、实现测试、文档与 CHANGELOG；未通过则保持旧行为并准确记录冲突，继续其他任务。

- [ ] 冲突明确登记，官方来源、日期、完整示例和负例可审阅。
- [ ] 决定与 R05-B 的依赖在总索引、会话报告中一致。
- [ ] 没有将“完整版本”误写为完全相同的可安装产物。

建议提案提交：`docs(spec): clarify exact dependency and requirements lock semantics (R05-S)`。

## 4. R06-B：依赖和 lock 的 scope

### 当前需要解决的歧义

根 / 子项目各有声明或 lock 时，哪些依赖共同构成一个可复现环境？“保留所有来源”“报告仓库中出现的依赖”和“某 lock 覆盖本实验依赖”是三个不同判断。

`val.md §4` 明确依赖 HarmBench 的嵌套 alignment-handbook 精确 pin：`accelerate, bitsandbytes, datasets, deepspeed, evaluate, peft, torch, transformers, trl` 不应出现在当前 warning 集合。直接 root-only 会改变已接受 gold。

### 推荐的决策顺序

1. 接受 S2 已实现的路径身份和实际 requirements include 图；它们提供确定事实，不自动决定整个 monorepo scope。
2. 第一阶段保持 L0 的仓库级来源汇总合同和现有 HarmBench gold；在文档 / provenance 中说明其范围，避免将其展示为某个实验已完整锁定。
3. requirements-as-lock 的覆盖严格来自 R06-P 的可达闭包；独立 sibling 文件不因位于相同目录而被算入。格式 lock 与声明的关联先使用明确同项目证据；不把全仓任意 lock 视作任意声明的证明。
4. 若要进一步引入“只验证选定实验环境”，必须提出用户如何选定该环境及旧 manifest 的默认解释；当前没有可用配置字段时，不虚构一个字段直接写进 schema v1。

### 供维护者裁决的备选

| 方案 | 行为与代价 | 建议 |
|---|---|---|
| A：保留 L0 汇总，明确 provenance，严格限定有明确引用关系的 lock 归属 | 保持已接受输入语义；消除已知错误归属；暂不声称完整多项目实验隔离 | 本阶段优先 |
| B：显式实验 dependency scope | 能回答某实验真正被哪个 lock 覆盖；需要选择合同、兼容设计及 gold 重审 | 有真实多项目使用需求后单独推进 |
| C：默认 root-only | 实现较小，但丢弃 HarmBench 等有效嵌套证据，改变默认结论 | 不建议直接采用 |

### 提案与验收用例

为根 pyproject + 根 lock、根 requirements include、两个独立子项目、工具-only pyproject、嵌套研究依赖、跨文件冲突版本逐一写 expected source / covered packages / warning set。对 HarmBench 从固定源码逐包列出 pin 位置与包含关系。

- [ ] 同一 input 的 inventory 与 lock 覆盖解释不会相互矛盾。
- [ ] 决策明确默认 L0 的语义，而不是在实现中临时猜选一个根。
- [ ] 未选择方案 B 时，不新增 workspace / monorepo schema。
- [ ] 如 gold 需要改变，独立依据、当前与新预期集合、历史保留方式齐全，单独审阅。

建议提案提交：`docs(spec): define dependency and lock scope (R06-B)`。实施提交名按最终接受范围确定。

## 5. R07-C：扫描不完整时，哪些结论仍成立

### 当前问题与推荐原则

`src/reprollm/core/engine.py` 可在规则 applicable 且没有 finding 时合成 PASS。当分析因 cap、不可读或其他限制不完整时，“没有发现反例”不总能支持整个仓库通过。

不得把任何截断都当作所有规则 FAIL，也不得简单让全部规则 SKIP。先完成 R07-A / B 的候选和诊断，再按证据类型列规则表。

| 规则所需证据 | 截断时建议行为 | 例子性质 |
|---|---|---|
| 完整 Git / manifest / lock 事实，不依赖受限 AST | 正常评估 | commit、声明字段存在等 |
| 已找到足以支持结论的具体证据 | 正常输出该证据支持的 finding | 明确的违规参数 / 不安全文件 |
| 需要完整扫描才能从“未发现”推出通过 | 信息不足，建议 SKIP 并说明覆盖边界；具体状态待规格批准 | 全仓不存在某类遗漏 / 反例 |
| 只承诺“已分析范围”的规则 | 仅在明确改写的规则合同内使用 scoped 结论，并展示范围 | 不得仍写成整个实验完整可复现 |

### 实施前必须完成

1. 从真实规则实现列出 rule ID、使用的 scanner / AST / manifest 数据、证据是否完整、positive / negative 结论条件。
2. 至少选择一个依赖完整扫描的规则做 end-to-end 设计：cap 前有证据、cap 后有证据、无证据、不可读四种情况。
3. 明确如何将 coverage 信息传给规则 / engine，以及默认 JSON / text 是否能沿用现有结构。必要新字段另走 schema 决策。
4. 对五项目完整 findings 预写差异，尤其 lm-eval 的已知截断。不变的 Git / 安全 finding 明确列出。
5. 准备 engine 的 D-41 审阅材料；未接受前不改全局 PASS 合成行为。

### 验收

- [ ] 状态变化逐 rule 有独立逻辑；不会因扫描限制压制已经发现的真实违规。
- [ ] 无覆盖限制时结果兼容；默认 fail-on 门槛不随本任务改变。
- [ ] 默认诊断仍由 R07-B 保证；不依赖用户必须开 verbose。
- [ ] full quality、必要 schema freshness、D-41 审阅及 Gate A 均完成后才合入实现。

建议提案提交：`docs(spec): define conclusions under incomplete scans (R07-C)`。

## 6. R04-S：环境来源与输入时点的条件 schema 方案

触发条件：R04-A 的环境来源或 R04-B 的输入阶段/变化矩阵无法通过现有字段、内部类型与已有 provenance 合理表达，并需要持久化供后续读取。只纳入实际触发的字段，不将两个任务变成一次宽泛 schema 重做。

### 提案要求

1. 以真实 before / after run JSON 展示最少字段。环境方案区分 recorder Python / packages、host facts、启动前继承 env、child verification 状态；输入方案区分启动前基线、结束后状态与变化/未知，不能将它们伪装成同一快照或已验证消费。
2. 固定字段枚举和 unknown 的含义。不得把 unknown 解释成 empty package set；不得记录解释器绝对路径作身份。
3. 新读者读旧 run：按可识别 producer 合同解释；不能还原的来源保留 unknown。旧文件原字节不改。
4. 旧读者读新产物：检查 `extra='forbid'` 与版本拒绝行为。不要把“optional 字段”直接当作双向兼容。
5. 若 breaking，按 D-39 安排 minor release 和 schema version 策略；同步所有受影响 loader、导出 schema、fixtures、文档、CHANGELOG 和迁移说明。
6. 包装运行的退出码合同、隐私保证和 R03 的 State 幂等不受破坏。

### 必须给出的兼容矩阵

| Writer → Reader | 预期 |
|---|---|
| 旧 writer → 新 reader | 读取成功；来源在可证实范围内解释，其他 unknown |
| 新 writer → 新 reader | 所有来源 / 时点能 round-trip，消费端语义一致 |
| 新 writer → 旧 reader | 若不能兼容，清晰识别较新 schema 并给升级提示，不产生误导性半读取 |
| 新 run → State → export / diff | 来源不丢失，既有 semantic leaf 选择稳定 |

- [ ] 没有触发条件时记录 NOT_NEEDED，不实施字段扩张。
- [ ] 有触发条件时，D-41 审阅和版本策略在写新格式前明确。
- [ ] 新 child hook / 主动探针属于后续 opt-in 设计，不自动纳入本次 schema 改动。

建议提案提交：`docs(schema): propose environment provenance compatibility (R04-S)`。

## 7. R08-B：privacy / training 自由参数风险分级

本项先产出清单和窄范围提案，不将所有深层字段统一 HIGH，也不改变 `*` 成递归匹配。

### 动作

1. 从当前 schemas、profiles、实际 examples 和 formal DP 案例收集允许的自由参数路径；不要凭空列不存在的字段。
2. 每项列出实验含义、当前 severity、为何影响可比较性、来源、推荐等级、用户覆盖方式。
3. 优先分析 `privacy.mechanism.params.target_epsilon` 等已用于真实 paired run 的字段。保持历史 formal DP epsilon 8 → 4 的 MEDIUM 记录，未来变化另立 gold 补充。
4. 分开真正影响训练 / 隐私保证的参数和日志、资源、输出位置等字段；只为有依据的路径提出新默认。
5. 已接受字段逐条加入默认表并验证 first-match / override；其余保持当前合同。

### 验收

- [ ] 每条拟提升路径有实际 schema / 案例与实验含义证据。
- [ ] 默认表、profile 继承、用户 LOW / NONE 覆盖均测试。
- [ ] 无 blanket HIGH、无递归 wildcard 改动、无历史结果重写。
- [ ] 可独立实施或延期，不阻塞 R08-A。

建议提案提交：`docs(diff): inventory high-impact free-form parameters (R08-B)`。

## 8. 决策收尾

每项记录 `PROPOSED / APPROVED / REJECTED / NOT_NEEDED`，附具体范围与证据。被拒绝的选择不是产品失败；待决项不是已完成修复。把被批准的任务精确插回相关 Sprint 或具名后续 Sprint，并列出接续提交。

依据：[Issue #9](https://github.com/EnumaElish123/ReproLLM/issues/9)、[severity resolver](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/diff/severity.py)、[默认 drift 表](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/diff/drift_severity.yaml)、[val.md](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/val.md)。
