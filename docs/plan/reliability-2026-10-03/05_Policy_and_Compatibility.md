# 专项方案：语义决策、策略变更与兼容性

版本：v1.2 · 初始日期：2026-10-03 · 状态：MIXED（已交付与逐项待审并存；2026-10-19 导航更新）

共同合同：[00_Execution_Guide.md](00_Execution_Guide.md)。审查 SHA：`590ee1739484bd21e21594e294e7ddf14bfd093f`。

## 1. 使用方式与交付边界

本文件处理需要明确产品语义或兼容性决定的工作。每个任务先产出完整提案、源证据、测试预期和可审阅改动，再按仓库要求取得适用决定。已在当前会话 / 仓库记录中获准的决定直接沿用，不重复索要许可。

| 会话 | 交付 |
|---|---|
| P-A | 核对已有决定；提前准备 R05-S，并按 R08-A、R06-B、R07-C、R04-S、R08-B 的相关性准备具体提案；没有触发的 R04-S 标明 NOT_NEEDED |
| P-B | 根据逐项决定落实被接受的范围、测试和迁移；被拒绝或待决事项保持原合同并记录理由 |

这是独立的设计 / 审议工作流。实际代码任务按“一任务一提交、先测试”执行；检查频率及五项目门按[验证流程优化](../validation-workflow-2026-10-13.md)分层，收尾证据覆盖全部任务。范围不足以在一次会话完成时记录后续会话，不压缩验收。

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

2026-10-18：维护者明确接受方案 A，见[具体决定](proposals/R08-A/decision.json)。
默认表/规格已按窄范围实施，gold 仅增加面向新比较的 §8.4.1；
验收及资源状态见 [P-B 报告](../../dogfooding/2026-10-18-r08a/README.md)。
[原提案、旧政策复现及补丁快照](proposals/R08-A/R08-A_direct_judge_params.md)保留当时状态。

入口：`src/reprollm/diff/drift_severity.yaml`、`src/reprollm/diff/severity.py`、`src/reprollm/profiles/llm_judge.yaml`、`judge_only.yaml`、`tests/unit/diff/test_severity.py`、`tests/unit/cli/test_diff.py`。

实施前 `*` 只匹配一个路径 segment，first-match 生效，profile overrides 在默认表前。
`evaluation.judge.*` 不匹配 `evaluation.judge.params.max_tokens`，后者曾落到默认 MEDIUM。
方案 A 保留这些匹配/覆盖规则，仅补直接 params 叶子的默认 HIGH 行。

已按批准仅在默认表较宽的 judge 行前加入：

```yaml
- { path: "evaluation.judge.params.*", severity: HIGH }
```

该行已生效。保留现有单段 wildcard 语义和 built-in profiles；不在父 profile 塞入新的宽泛 override，以免覆盖用户子 profile 的精确 LOW / NONE 设置。

### 修改前 / 后验收表

| 路径 / 场景 | 实施前默认 | 方案 A 实施后的默认 |
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

- [x] 读取 Issue #9 和最新维护者决定，复用已有讨论；旧在线核验快照及本次明确接受分别保留。
- [x] 策略行、规格 §18、CHANGELOG、窄范围回归和前瞻性 gold amendment 齐全。
- [x] 决定明确后，仅实施该范围；10-18 的 full quality + 五项目 Gate A 及 diff 扩展通过，当次 formal 未执行。10-19 的 [R02-R 后续正式 judge 验收](../../dogfooding/2026-10-19-judge-snapshot-fix/README.md)已在 `75d1b0` 通过；不回写旧资源记录。CI 按精确推送提交单独确认。
- [x] UI / README 使用无其他 HIGH 遮蔽的直接参数回归，不用原有 config-hash HIGH 结果证明本策略。

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

2026-10-10：维护者对完整 before/after 提案明确回复“接受 A/P+C，执行完整 S2（推荐）”，A/P 与 C 均为 ACCEPTED。见 [固定提案](proposals/R05-S/R05-S_exact_dependencies.md) 与 [具体决定记录](proposals/R05-S/decision.json)。提案快照保留原 PROPOSED 状态及原摘要；接受记录独立保存。Python/requirements 规范随 R05-A 同步，Conda 规范随 R05-B 同步；每项实现仍须独立验收，不以该决定替代 D-41 审阅。

### 交付与依赖

1. 在 R00 后准备 §12.2 的精确 before/after 修订、格式支持表、相关测试及完整 finding 变化。检查 R05-A / R06-P 的规范措辞是否需同步，不机械阻塞已有明确缺陷修复。
2. 按 AGENTS 的 spec issue/决定流程记录接受范围。R05-B 的实现合入必须引用该决定，不能保留矛盾规范却修改测试期望。
3. 核对五项目固定源文件，以独立版本语义解释每项 delta；gold 变化另审，不复制 parser 当前输出。
4. 通过后同步规范、实现测试、文档与 CHANGELOG；未通过则保持旧行为并准确记录冲突，继续其他任务。

- [x] 冲突明确登记，官方来源、日期、完整示例和负例可审阅。
- [x] 具体 A/P+C 决定已记录；R05-B 引用该接受记录。
- [x] 没有将“完整版本”误写为完全相同的可安装产物。A/P+C规范与实现已于S2同步，见[交付报告](../../dogfooding/2026-10-10-reliability-s2/README.md)。

建议提案提交：`docs(spec): clarify exact dependency and requirements lock semantics (R05-S)`。

## 4. R06-B：依赖和 lock 的 scope

2026-10-19 P-A 材料：[具体提案](proposals/R06-B/R06-B_dependency_lock_scope.md)、
[源码/离线观察](proposals/R06-B/implementation-evidence.md)、
[五项目来源](proposals/R06-B/portfolio-evidence.md)保留准备时身份。
2026-10-20：维护者明确[接受方案 A](proposals/R06-B/decision.json)及原规范补丁；P-B 实施与验收见[接续报告](../../dogfooding/2026-10-20-r06b/README.md)。
接受的 A 保留全仓 existential exact 汇总，只收紧有明确来源关联的格式 lock 包名信用；
`env.lockfile_present` 的存在性合同保持独立。旧/新行为、同目录 manager 边界、
import 最近项目根、unknown barrier、workspace 兼容成本及后续验收均在具体提案中定义。
下列验收由 P-B 独立验证；原 P-A 观察不冒充新政策结果。

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

- [x] 同一 input 的 inventory 与 lock 覆盖解释不会相互矛盾。
- [x] 决策明确默认 L0 的语义，而不是在实现中临时猜选一个根。
- [x] 未选择方案 B 时，不新增 workspace / monorepo schema。
- [x] 如 gold 需要改变，独立依据、当前与新预期集合、历史保留方式齐全，单独审阅。

建议提案提交：`docs(spec): define dependency and lock scope (R06-B)`。实施提交名按最终接受范围确定。

## 5. R07-C：扫描不完整时，哪些结论仍成立

2026-10-29：维护者已[明确接受最终有限A](proposals/R07-C/final-coverage/decision-accepted.json)。
§12.3.16九文件实现及全部本地验收已通过，源/测试冻结于3157，5295测试、完整质量24及fresh五项目230/184与独立复核PASS。
[最终报告](../../dogfooding/2026-10-29-r07c-final-coverage/README.md)和[完成账本](07_Completion_Status.md)
记录当前结论；最终推送HEAD CI另核。下列旧局部OPEN/PROPOSED保持历史身份，不再作为当前开发待办。


2026-10-29：完整剩余范围已合并为[有限六规则收尾方案](proposals/R07-C/final-coverage/README.md)。
具体源码/规范/前瞻验收patch未应用；69条规则矩阵、现行故障观察和五项目来源预期已准备，
新合同仍PROPOSED，不能据总体继续授权当作接受。两项既有框架合同修复可独立验收。


2026-10-20 P-A：[具体局部方案](proposals/R07-C/R07-C_incomplete_scan_conclusions.md)、
[逐规则证据](proposals/R07-C/rule-evidence.md)、
[四格与混合反例](proposals/R07-C/acceptance-cases.md)、
[五项目完整条件差异](proposals/R07-C/portfolio/portfolio-evidence.md)、
[规范 patch](proposals/R07-C/spec-proposed.patch)及
[D-41 engine / 内部接口 patch](proposals/R07-C/implementation-proposed.patch)保存准备时快照。
2026-10-20，维护者明确[接受局部 A、规范及 D-41 patch](proposals/R07-C/decision-accepted.json)。
原 [PROPOSED 决定快照](proposals/R07-C/decision.json)原字节保留，不能作为最新决定。
P-B 仅实施两规则空结果的 primary-Python gap / unavailable veto，见[实施与验收报告](../../dogfooding/2026-10-20-r07c-pb/README.md)。
保留其他现合同；广义 R07-C 的 mixed evidence、listing/deps/framework 和充分证书仍 OPEN，不因局部 A 交付关闭。

2026-10-21，维护者[明确接受 profile-absence 局部 P 与具体规则 / 规范补丁](proposals/R07-C/profile-absence/decision-accepted.json)。
P-B 只改 declared-but-undetected 分支：Python gap/unavailable 时逐 profile SKIPPED，
正向 high/shipped 未声明 FAIL 保留；见[实施与验收报告](../../dogfooding/2026-10-21-r07c-profile-pb/README.md)。
原[提案](proposals/R07-C/profile-absence/R07-C_profile_absence.md)、[PROPOSED 决定](proposals/R07-C/profile-absence/decision.json)
及[P-A 报告](../../dogfooding/2026-10-21-r07c-profile-pa/README.md)保留准备时状态，不作为当前执行结果。
这不关闭依赖 absence、其他覆盖域或充分证书的广义 R07-C 工作。

本批 [D-L 具体提案](proposals/R07-C/dependency-lock-credit/R07-C_dependency_lock_credit.md)已准备：
在固定已采集依赖视图下，只对 Python gap/unavailable 且在格式 lock 包集合中出现的原待警告包逐项 SKIPPED/INFO，
保留 exact/qualified 信用、其他包与完整视图旧行为；格式 membership 是保守上界，不赋予 lock 信用。
维护者已[明确接受具体 D-L 与补丁](proposals/R07-C/dependency-lock-credit/decision-accepted.json)，
[P-B 报告](../../dogfooding/2026-10-21-r07c-dependency-pb/README.md)记录已完成实施、完整质量门及五项目验收；最终 HEAD CI 另行核对。
[原决定](proposals/R07-C/dependency-lock-credit/decision.json)及[P-A](../../dogfooding/2026-10-21-r07c-dependency-pa/README.md)保留准备时快照，条件结果不冒充 P-B 验收。

维护者已[接受 D-F 的具体规范和实现补丁](proposals/R07-C/format-lock-read/decision-accepted.json)，
仅处理具备既有 R06-B 合格捕获来源的格式锁 body-read/decoder 已知失败，先保留 exact/qualified 信用，再逐包 SKIPPED/INFO，独立于 Python coverage。
[P-B 报告](../../dogfooding/2026-10-21-r07c-lock-read-pb/README.md)记录已通过的完整本地质量门及五项目/受影响验证；最终 HEAD CI 另行核对。
[原提案](proposals/R07-C/format-lock-read/R07-C_associated_format_lock_failures.md)、PROPOSED 决定和 P-A 条件观察保持快照。
错误结构/部分提取、一般依赖/requirements、遗漏 import、listing/README/config/framework 和广义证书继续 OPEN。

维护者已[具体接受 D-S](proposals/R07-C/format-lock-structure/decision-accepted.json)。
P-B 仅增加 `invalid_structure` 并复用 D-F 关联/输出，保留部分成员信用及空/null 明确边界；
[P-B 报告](../../dogfooding/2026-10-21-r07c-lock-structure-pb/README.md)记录实施和当前验收状态。
原[P-A 报告](../../dogfooding/2026-10-21-r07c-lock-structure-pa/README.md)、PROPOSED 决定及条件证据保留；
这不关闭整个 R07-C，一般依赖/requirements、其他 grammar、listing/framework 和广义证书仍 OPEN。

维护者已[具体接受D-M及规范/实现/测试补丁](proposals/R07-C/declaration-read/decision-accepted.json)。
P-B仅为已采集声明正文的现有读取/解码失败增加内部事实，含实际requirements正文read None，
保留现有信用及D-F/D-S、D-L，再把剩余缺pin项保守SKIP；依现行existential exact影响全仓。
[P-B报告](../../dogfooding/2026-10-21-r07c-declaration-read-pb/README.md)记录实施与当前验收状态。
原[提案](proposals/R07-C/declaration-read/R07-C_declaration_body_failures.md)、PROPOSED快照及
[P-A条件证据](../../dogfooding/2026-10-21-r07c-declaration-read-pa/README.md)保持历史字节。
decoded结构/行语法、一般include图、未知use和遗漏候选/listing/framework仍OPEN；不关闭整个R07-C。

2026-10-22：维护者已[具体接受 D-M-S 方案 A 及规范补丁](proposals/R07-C/declaration-structure/decision-accepted.json)。
P-B 对成功解码后的指定容器／成员实施有界检查，保留部分有效声明、信用与既有优先级，复用 D-M 消费。
[P-B 报告](../../dogfooding/2026-10-22-r07c-declaration-structure-pb/README.md)记录实施与最终验收状态。
原[具体 P-A](proposals/R07-C/declaration-structure/R07-C_declaration_structure.md)、PROPOSED 决定和
[P-A 报告](../../dogfooding/2026-10-22-r07c-declaration-structure-pa.md)保持历史字节。
单包值／字符串语法、requirements 引用图及更广覆盖继续 OPEN；本批不关闭整个 R07-C。

2026-10-22：维护者明确委托“裁决D-G A/B”，agent独立核对后
[裁决采用A及具体补丁](proposals/R07-C/requirements-depth/decision-accepted.json)，接受全仓SKIP和退出1→0成本。
本片仅记录全部roots后仍无最终node的既有normalized include targets，保留信用及
D-F/D-S、D-L、D-M优先级，无新增读取、预算或grammar扩张。
`d823f90`已通过最终本地质量门、五项目Gate A和受影响D-G消费者；
见 [P-B报告](../../dogfooding/2026-10-22-r07c-requirements-depth-pb/README.md)。精确推送HEAD的CI在交付时另核。
原 [P-A报告](../../dogfooding/2026-10-22-r07c-requirements-depth-pa.md)和PROPOSED材料保持历史字节；
“later shallow root”的实际先后顺序另立 [证据勘误](proposals/R07-C/requirements-depth/decision-evidence/README.md)。
这项委托裁决不等于其他R07-C政策的批准，也不关闭整个R07-C。

D-C 于 2026-10-22 启动、2026-10-23 完成本地验收。维护者已[明确接受方案 A 及具体补丁](proposals/R07-C/requirements-comments/decision-accepted.json)，
产品提交为 `0f8c4df`，见[P-B 报告](../../dogfooding/2026-10-22-r07c-requirements-comments-pb/README.md)。
仅实施 requirements ordinary 分支有界注释回退，保留原 route／完整行成功优先、整文件尾反斜线 veto、既有信用和不确定性优先级。
141 个新增回归、完整本地质量门、五项目 Gate A、graph／verbose 与公共 CLI 重放、原件最终身份及归档独立回读均 PASS；
HarmBench 的两条新声明、两条诊断删除与 closure 变化按独立预期完整验证。最终推送 head 的五项 CI 和 Linux 精确 schema 检查在交付时另行核验。
[P-A 报告](../../dogfooding/2026-10-22-r07c-requirements-comments-pa.md)和原 PROPOSED 材料保留准备时快照；其余 R07-C 仍 OPEN，资源阻塞不关闭，不发布版本。

### R07-C D-M-P：PEP 621 字符串失败 P-B（2026-10-23）

维护者在具体 A、精确补丁和全仓保守成本交付后指示继续下一步；
[接受记录](proposals/R07-C/pep621-strings/decision-accepted.json)如实记为本片上下文授权，不伪造逐字“接受 A”。
产品提交 `26a4d30` 仅将两个现有 PEP 621 调用的实际失败记为内部 `unparsed_requirement`，
复用 D-M，保留部分声明、已有原因、信用及优先级。规范补丁已应用，包含空白／无关项目失败
也可全仓 WARNING→SKIPPED、孤立 exit 1→0 的成本。
[P-B 报告](../../dogfooding/2026-10-23-r07c-pep621-strings-pb/README.md)记录 170 个新增用例、
完整失败／修正历史、最终质量门、五项目 Gate A、受影响验证、24 份完整内部记录与归档回读，均本地 PASS。
精确最终推送 HEAD 的五项 CI 与 Linux schema 检查在交付时另核。
原 [P-A](proposals/R07-C/pep621-strings/README.md)、PROPOSED 决定和观察保留历史字节。
后续 environment 嵌入 pip 独立 P-A 已准备，见下节；不得自动套用本片空白触发或授权。
更广 R07-C 仍 OPEN；资源与外部反馈阻塞保留，不发布版本。

### R07-C D-M-E：environment 嵌入 pip 提取失败 P-B（2026-10-23）

维护者已[明确接受 A 及精确规范补丁](proposals/R07-C/environment-pip/decision-accepted.json)，包括全仓 WARNING→SKIPPED、孤立 exit 1→0 成本。
产品 `a221e9d` 只消费既有非空字符串经strip后的单次Requirement失败，以setdefault记录既有原因；空白、原序号、诊断、部分声明、信用和优先级保持。
[P-B报告](../../dogfooding/2026-10-23-r07c-environment-pip-pb/README.md)记录154新增用例、最终质量门、五项目Gate A、受影响验证、27份完整内部记录和归档回读，均本地PASS。
最终精确推送HEAD的五项CI及Linux schema/docs/examples交付时另核。
原[P-A](proposals/R07-C/environment-pip/README.md)、PROPOSED决定、38项设计和原观察保留准备时字节；不把pip可支持而提取器未解析等同非法环境。
后续仅建议独立P-A核对Poetry显式version提取边界，不能把空值／非exact直接当失败。更广R07-C、资源、外部反馈仍OPEN；不发布版本。

维护者已[接受D-M-V A、精确补丁及全仓成本](proposals/R07-C/poetry-version/decision-accepted.json)。产品`b18ed19`仅在原Poetry循环记录显式非str version的invalid_structure，保留先因/声明/信用/line fallback。
[P-B报告](../../dogfooding/2026-10-23-r07c-poetry-version-pb/README.md)记录171新增回归、最终质量、fresh五项目Gate A/受影响、35完整record和归档回读，适用本地门均PASS；最终精确HEAD五项CI交付另核。
原[P-A](proposals/R07-C/poetry-version/README.md)、PROPOSED决定和原观察保持字节。下一步只建议独立P-A核Pipfile显式version、packages/dev-packages两节和allow_bare=False；不套用本次批准。更广R07-C、资源及外部反馈仍OPEN，不发布版本。

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

2026-10-27：下一项独立 P-A 为 [D-M-CE Conda 字符串省略](proposals/R07-C/conda-omissions/README.md)。
具体 A/B、两份精确未应用补丁、36组未来验收、官方边界和独立复核已准备。
A只增加内部 unparsed_conda，并在两个原 native helper 提前返回点 setdefault；
所有仍append声明的range/复杂suffix保持。32个current helper与36个集成观察通过，
候选执行0；五项目supported environment文件为0，不能据此称触发或Gate A已通过。
状态PROPOSED，须独立接受全仓保守WARNING→SKIP、孤立exit1→0及text/export成本；
Pipfile/Poetry接受不扩展。详见[P-A报告](../../dogfooding/2026-10-27-r07c-conda-omissions-pa.md)。
规范仍按旧合同；更广R07-C保持OPEN，公共模型资源门的已有通过保持原绑定。

同日P-B：维护者已[明确接受A及具体补丁](proposals/R07-C/conda-omissions/decision-accepted.json)。
`c9ee53d`只增加已接受的内部code和两个原返回点setdefault；
[P-B报告](../../dogfooding/2026-10-27-r07c-conda-omissions-pb/README.md)分别记录已完成和待完成门。
原P-A/PROPOSED字节不重写，Conda其余grammar和更广R07-C保持OPEN。

同日接续P-A：[D-M-CS保留名称的specifier提取边界](proposals/R07-C/conda-retained-suffix/README.md)。
基线`22e3dbc`已有全部适用验收及五项CI；本片按相邻OPEN范围准备，不重开旧验证。
A仅建议在原specifier-placeholder赋值点记录独立`unparsed_conda_specifier`，保留六种原
numeric RANGE、CE两返回、regex/声明/信用/消费优先级。明确非exact或无关条目也可
全仓WARNING→SKIP、孤立exit1→0，须独立接受具体patch和成本；B保持当前合同。
本片PROPOSED，不实施grammar或候选；完整材料及38组未来验收见该目录。

同日P-B：维护者已[明确接受D-M-CS A及两份具体补丁](proposals/R07-C/conda-retained-suffix/decision-accepted.json)。
`1607ee0`只增加原placeholder分支的内部`unparsed_conda_specifier`；`bd74330`仅补齐
两处跨管理器首因旧预期，产品/规范字节相同。230项新增回归、51项旧预期同步及
最终`bd74330`完整质量、fresh五项目基础/受影响验收均通过；首轮质量失败保持原身份。
详见[P-B报告](../../dogfooding/2026-10-27-r07c-conda-retained-pb/README.md)及38组实际映射，
精确交付HEAD五项CI另核。原29份P-A/PROPOSED字节不重写；六种numeric RANGE、CE省略、
声明/诊断/信用/现消费优先级保持，全仓SKIP和孤立exit1→0是已接受成本。
Conda其余grammar、遗漏use/listing/framework及更广R07-C仍OPEN，不发布版本。

2026-10-28既有合同跟进：预算内Python源码可令`ast.parse`抛`RecursionError`，原audit退出3，
未能完成§13成功才计parsed及§12.3.1–2的现有gap消费。`40c92d2`只加原解析try的独立
异常分支、固定安全诊断和continue；不增解析成功数，不改预算、规范、规则、engine或schema。
此为现合同崩溃修复，不将新的OPEN政策视为已接受。15项公开CLI新增、167项定向回归、
最终24项质量及fresh五项目180命令/25完整JSON和init/export全文比较通过，详见
[会话报告](../../dogfooding/2026-10-28-r07c-python-parser-recursion/README.md)。
原生证明限本轮Python3.12.14；其他平台的条件和精确交付HEAD五项CI另核。
独立InspectAI解析器和YAML配置对象自环是尚未实测的后续静态候选；listing、filtered include、
遗漏use/framework和充分性证书仍分域OPEN，新政策按独立P-A审议，不发布版本。

同日InspectAI独立跟进：先核精确`960a1fd`全部五项CI与Ubuntu3.12十二步成功，
再于`3c21749`仅把其原SyntaxError捕获扩大至parser RecursionError，复用完全相同的regex。
这是既有fallback意图与规范§3.2/§14候选合同的修复，规范未逐项枚举该异常，
不把更广OPEN政策当已批准。原生80,073字节真实CLI旧退出3→新0；18项新增、59项定向、
最终24项质量、fresh五项目180主体命令与额外5个完整list-tasks均通过，见
[本批报告](../../dogfooding/2026-10-28-r07c-inspect-parser-recursion/README.md)。
安全库存/显式选择/不推断metric implementation、regex语法、扫描边界和窄异常范围保持；
不改规则、engine、schema、预算或版本，精确交付CI另核。YAML配置对象自环仍未实测，
其余listing/filtered include/遗漏use/framework及更广R07-C保持OPEN，不发布版本。

同日YAML对象自环独立跟进：精确`347eae7`五项CI及Ubuntu3.12十二步成功后，
`ccf9baf`仅用active祖先id剪除dict/list回边，不使用全局visited，保留每个健康可达key、
原有无环共享alias的DFS重复及顺序。原decoder/parser、key-only扫描、预算和意外遍历异常合同保持。
46字节真实YAML让旧CLI退出3→新0；18新增、177定向、最终24项质量和fresh五项目
180主体命令及额外5次完整list-tasks/40只读Git守卫均通过本地验收，见
[本批报告](../../dogfooding/2026-10-28-r07c-yaml-config-cycles/README.md)。
公开CLI比较证明规范化关键词结果，不证明容器访问次数；共享alias遍历保持由源码结构审阅支持。
本片不增加depth/node或alias扩展预算，不改规则、engine、schema、依赖或版本，最终交付CI另核。
更广R07-C、decoder处理和alias资源边界仍待独立审议，不发布；此前InspectAI/primary及历史文字保持。

同日配置遍历深度独立跟进：精确`a8806aa`五项CI及Ubuntu3.12十二步成功后，
`9903627`仅用live iterator frames替代递归调用栈，保持原DFS key/value顺序、active祖先回边处理、
无环共享alias重复、key-only扫描及意外遍历异常传播；不把已成功解码的数据因walker深度而丢弃。
2,033字节、depth1,000真实JSON成功解码后旧CLI退出3→新0；13新增、190定向、最终24项质量
及fresh五项目180主体/5完整list-tasks/40只读Git守卫均通过本地验收，见
[本批报告](../../dogfooding/2026-10-28-r07c-config-depth/README.md)。
CLI比较证明规范化关键词结果，不证明容器访问次数；顺序、alias重复及异常清理由结构与定向fixture支持。
原decoder、source/read预算、规则、engine、schema、依赖、版本保持；不增加depth/node/alias扩展预算。
最终交付CI另核，更广R07-C与decoder/alias资源边界待独立审议，不发布，历史原文保留。

同日D-I下一批P-A：[filtered include具体方案](proposals/R07-C/filtered-include/README.md)
及两份patch已准备，未接受/应用；现行24case/27CLI与独立静态审阅不替代新政策验收。
A仅记录实际candidate拒绝的已达supported target，在全部旧信用及D-G之后逐包SKIP；
明确全仓、目标可能不存在、孤立门1→0与默认显示成本。五项目无include边仅支持零delta预测。
具体决定后才实施和fresh验收，见[准备报告](../../dogfooding/2026-10-28-r07c-filtered-include-pa.md)。
前批精确e3aa653五CI/Ubuntu3.12十二步已成功。更广R07-C继续OPEN，不发布。

2026-10-29 D-I P-B：[维护者具体接受A及两份补丁](proposals/R07-C/filtered-include/decision-accepted.json)，
3aadb9a按§12.3.15原样实施，保留旧信用/D-FS/D-L/D-M/D-G优先及完整证据。
已接受无关/不存在目标的全仓保守SKIP与孤立门1→0成本；不新增读取/候选/预算/语法/未知use或信用。
[实施报告](../../dogfooding/2026-10-29-r07c-filtered-include-pb/README.md)记录39新增、688既有回归，
最终24项质量及fresh五项目225旧投影+5新tuple采集，共230外层/184检查，gold无差异。
新字段五pins实测为空与旧facts投影分开验证，不以零触发替代边界回归。
精确交付HEAD五CI另核；PA原字节及接受记录各自保留，更广R07-C/发布仍未关闭。

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

2026-10-20，维护者已[接受 A4 四条精确路径及规范 / 前瞻补丁](proposals/R08-B/decision-accepted.json)。
P-B 仅将 `privacy.mechanism.params.target_epsilon` / `target_delta` / `max_grad_norm`
和 `training.params.num_train_epochs` 默认设为 HIGH，见[实施与验收报告](../../dogfooding/2026-10-20-r08b-pb/README.md)。
LOW/NONE、first-match、其他参数及历史 gold 保持。原[提案](proposals/R08-B/R08-B_exact_parameter_risk.md)、
[来源清单与条件实验报告](../../dogfooding/2026-10-20-r08b-pa/README.md)及
[PROPOSED 决定](proposals/R08-B/decision.json)保留准备时状态，不能冒充 P-B 验收。


### 动作

1. 从当前 schemas、profiles、实际 examples 和 formal DP 案例收集允许的自由参数路径；不要凭空列不存在的字段。
2. 每项列出实验含义、当前 severity、为何影响可比较性、来源、推荐等级、用户覆盖方式。
3. 优先分析 `privacy.mechanism.params.target_epsilon` 等已用于真实 paired run 的字段。保持历史 formal DP epsilon 8 → 4 的 MEDIUM 记录，未来变化另立 gold 补充。
4. 分开真正影响训练 / 隐私保证的参数和日志、资源、输出位置等字段；只为有依据的路径提出新默认。
5. 已接受字段逐条加入默认表并验证 first-match / override；其余保持当前合同。

### 验收

- [x] 每条拟提升路径有实际 schema / 案例与实验含义证据。
- [x] 默认表、profile 继承、用户 LOW / NONE 覆盖均测试。
- [x] 无 blanket HIGH、无递归 wildcard 改动、无历史结果重写。
- [x] 可独立实施或延期，不阻塞 R08-A。

建议提案提交：`docs(diff): inventory high-impact free-form parameters (R08-B)`。

## 8. 决策收尾

每项记录 `PROPOSED / APPROVED / REJECTED / NOT_NEEDED`，附具体范围与证据。被拒绝的选择不是产品失败；待决项不是已完成修复。把被批准的任务精确插回相关 Sprint 或具名后续 Sprint，并列出接续提交。

依据：[Issue #9](https://github.com/EnumaElish123/ReproLLM/issues/9)、[severity resolver](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/diff/severity.py)、[默认 drift 表](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/src/reprollm/diff/drift_severity.yaml)、[val.md](https://github.com/EnumaElish123/ReproLLM/blob/590ee1739484bd21e21594e294e7ddf14bfd093f/val.md)。

### R07-C D-M-PF：Pipfile 显式 version 独立 P-A（2026-10-24）

[具体提案与精确未应用补丁](proposals/R07-C/pipfile-version/README.md)、[P-A报告](../../dogfooding/2026-10-24-r07c-pipfile-version-pa.md)为PROPOSED，推荐A，候选执行0。当前规范/实现一致；只建议在已有packages/dev-packages entry循环按dict+显式version+非str setdefault invalid_structure，原allow_bare=False、声明、信用、line fallback及barrier保持。官方类型边界不证明隐藏exact；全仓保守WARNING→SKIPPED、孤立exit1→0及text/export成本必须具体接受。38例当前观察、五项目源盘点、45组未执行未来验收及独立审阅已备齐；Poetry批准不扩大。下一步先裁决A/精确补丁/成本，再P-B先RED实施与最终质量、fresh五项目Gate A及受影响验证。更广R07-C、资源/采用保持OPEN，不发布版本。

### R07-C D-M-PF：接受A并完成P-B本地验收（2026-10-24）

维护者[明确接受A/精确补丁及全仓成本](proposals/R07-C/pipfile-version/decision-accepted.json)。产品`ba1415b`仅在已有Pipfile两节entry循环对dict+显式version+非str setdefault既有invalid_structure；allow_bare=False、声明、先因、credit、line fallback和barrier保持。
[P-B报告](../../dogfooding/2026-10-24-r07c-pipfile-version-pb/README.md)记录267新增回归、8既有预期同步、首轮5旧断言失败与完整原件保留，新的最终输入上质量、fresh五项目Gate A/受影响、38完整记录均通过；精确最终HEAD五项CI交付另核。原P-A/PROPOSED和历史记录不重写。全仓WARNING→SKIPPED及孤立exit1→0是已接受成本，不是pin或完整分析证书。更广R07-C、资源/采用仍OPEN，不发布版本。
