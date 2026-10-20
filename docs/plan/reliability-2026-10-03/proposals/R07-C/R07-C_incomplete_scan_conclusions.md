# R07-C：已知 Python 扫描缺口下的空结果 PASS

状态：**PROPOSED；未接受、未实施**。日期：2026-10-20。
审查源码：`055c5fb880f4e374555a1d229b79d0d612c80350`。
本次完成 P-A 的逐规则分析、复现、具体政策及审阅材料；不把继续开发的总体授权解释为新政策批准。
[决定记录](decision.json)的接受范围仍为空；两个 patch 均未应用。

## 1. 当前合同与实际问题

依据：[05 §5](../../05_Policy_and_Compatibility.md#5-r07-c扫描不完整时哪些结论仍成立)、
[规格 §11](../../../01_specification.md#11-audit-engine-semantics)、
[§13](../../../01_specification.md#13-deterministic-profile-detection-m2)、
[执行总则 §5](../../00_Execution_Guide.md)、
[D-41](../../../00_architecture_and_decisions.md)。
当前 applicable 规则返回空列表即合成 PASS；R07-B 只披露超过 Python 文件数量上限的诊断，不改变规则状态。
这与当前规范一致，不能将新政策伪装成已有合同的 bug fix。

[全部规则追踪](rule-evidence.md)按实际 ID 区分 Git、受限扫描、manifest、lock、State 和运行记录。
[当前程序观察](implementation-evidence.md)包含 11 个受控输入、13 项独立条件和完整 findings；
是现程序的离线观察，不是未来方案已通过。
例如，`z.py` 中唯一的 vLLM import 位于上限之外时，当前 profile mismatch 可以 PASS；
同一来源进入分析后成为 INFO finding。未超数量上限但文件不可读时，也可能出现这种 PASS。

“非空 finding”也不等于不受遗漏影响的正向证明。
已声明 profile 缺少检测、关键包未找到 exact/合格 lock，均可能由后来读到的证据推翻。
R06-B 保留全仓 existential exact，一份不可读的 nested requirements 就可能藏有这种证据。
本提案明确保留这些现有分支并列出余留问题；不声称它们已被本轮全面修正。

## 2. 推荐 A：两条规则的保守空结果 veto

仅以下内置规则 opt in：

- `env.llm_critical_deps_pinned`：已知包均有固定证据时，未分析 Python 仍可能藏有另一个关键包。
- `exec.profile_detection_mismatch`：已观察的检测与声明一致时，未分析 Python 仍可能藏有未声明的 high profile。

逐规则执行顺序：先保持当前 level / applies / check；**只有 applies=true 且 check 返回空列表**，才调用
`Rule.pass_skip_reason(ctx)`。默认返回 None；这两条规则读取 typed Python candidate coverage。
若视图未观察、计数不满足不变量，或者 parsed < candidate，则输出现有形状的一条 `status=skipped`、`severity=INFO` finding。
否则沿用当前合成 PASS。该 hook 不扩展到 generated project rules。

非空 finding 原样经过既有 severity override、suppression、排序、summary 和 exit 流程。
不额外附加第二条 coverage finding；不改显式逐字段 PASS；不因 Python 缺口改 Git / manifest / lock / State 规则。
`applies=false` 已是 SKIPPED，继续原理由。两条规则的 ID、默认 failure severity、fix hint 和阈值不变。

这是**有意保守的局部政策**：即使某输入的声明已包含全部可能产生的 high profile，A 仍可将空结果 PASS 改为 SKIPPED。
更精细的充分证书不是 A 的隐含行为。A 只处理已知 primary-Python candidate view 缺口；
R07-C 的其他混合证据分支、目录枚举、依赖解析和 framework 覆盖问题保持 OPEN，不能据此勾选整个 R07-C 完成。

### 2.1 具体接口与 D-41 patch

[未应用的实现补丁](implementation-proposed.patch)只有五个源码文件：

| 文件 | 具体改变 |
|---|---|
| `core/pyscan.py` | 冻结的内部 `PythonCandidateCoverage`，复用四个实际计数；增加内部 observed marker，正常扫描返回前置 true |
| `core/registry.py` | 增加默认无效的 `pass_skip_reason(ctx) -> str | None`，并修正文档中的空结果描述 |
| `core/engine.py` | 仅在内置 rule 的空结果分支问 hook；有理由用既有 skipped 构造器，否则旧 PASS |
| `rules/env.py` | 仅 critical-deps rule opt in |
| `rules/exec_.py` | 仅 profile-mismatch rule opt in |

路径均相对于 `src/reprollm/`。完整规范文字见[规范 patch](spec-proposed.patch)，覆盖 §11、§12.3.1、§13。
这两份文件是供维护者审阅的具体差异，尚未对源码或规范生效；补丁适用性检查不等于执行了未来实现。
P-B 仍先写独立验收测试再实现；若实际 engine hunk 或政策范围发生实质变化，需补充相应 D-41 审阅。

[覆盖接口分析](coverage-design.md)逐项区分 primary AST、framework、deps、README/config、listing 和 runtime scopes。
计数仅来自现有 `analysis_files` 候选视图，不能证明 Git 列表或文件系统完整。
2 MiB listing limit、512 KiB read limit、根内读取、静态排除均不变；未进入候选的路径不冒充“已成功解析”。
observed=false 不当成空仓库；正常零候选且 observed=true 仍按旧行为。预算与失败原因不从 warning 字符串推断。

### 2.2 before / after 与输出

A 复用 audit schema 1 的既有字段、枚举和文本/JSON reporter。
新 SKIPPED 的 evidence=[]、message 为以下固定文字和实际整数，其余身份与 fix_hint 沿用：

```text
Python candidate analysis incomplete: parsed {parsed} of {candidate} candidate files; selected {selected} (limit {limit}); no rule-wide PASS is established.
```

内部未观察或计数不满足不变量的结果使用：`Python candidate coverage is unavailable; no rule-wide PASS is established.`
不持久化 coverage 字段。默认 stderr 的 R07-B 数量诊断及可见性不变；不可读/语法失败但未超数量上限时，
只有选中且原本要合成 PASS 的上述规则会在已有 finding 中给出说明，不新增全局诊断。

| 条件（profile mismatch） | 当前 | A 的独立预期 |
|---|---|---|
| cap 前发现未声明的 high inference | INFO FAIL | 原 FAIL 保留 |
| cap 后才有该信号，已分析范围没有 mismatch | PASS | SKIPPED INFO；不能预测隐藏内容是什么 |
| 全部候选解析成功且确无该信号 | PASS | PASS，完整输出兼容 |
| 已选文件不可读，check 为空 | PASS | SKIPPED INFO；不误说是数量截断 |
| 已声明 inference 但 cap 内未发现 | INFO FAIL | 保持现有 absence finding，列为未解决分支 |
| 已知 torch 全已固定、另一个包在 cap 外 | critical-deps PASS | critical-deps SKIPPED INFO |
| 已有包 WARNING，另一个 exact 来源不可读 | WARNING FAIL | 原 finding 保留，不能称作已全域证明的违规 |

完整四格、对照恢复及余留反例见[独立验收设计](acceptance-cases.md)。
默认 `--fail-on critical` / `warning` 的门槛不变；PASS→SKIPPED/INFO 不计入 fail info，故不会自行使 exit 失败。
summary 中 pass 减一、skipped 加一；显示顺序按现有 severity/category/id 重排。
已有 ignore 规则仍按原机制变为 SUPPRESSED；不得把 suppression 当 coverage PASS。

## 3. 三个明确选择

| 选项 | 范围与兼容成本 |
|---|---|
| **A（推荐）** | 上述两规则、空结果路径、captured primary-Python view；无新 schema。能消除一个已证明的错误确信来源，允许保守 SKIP；广义 R07-C 保持部分待办 |
| B：充分证书与更广 coverage | 为每条分支设计可证明的 listing/deps/detection/framework scopes 和输入特定证书；可能减少不必要 SKIP，但需要另行完整具体 patch、兼容和 gold 设计，本次不自动实施 |
| C：保持现合同 | 继续只提示数量上限，保留当前空结果 PASS；记录局限，A 不实施 |

A 不把 B 的复杂度藏进实现，也不授予后续规则 blanket SKIP。未批准前保留现合同。

## 4. 五项目、历史与兼容

[完整条件对比](portfolio/portfolio-evidence.md)保留十份完整既有报告与来源，逐 rule 比较，不能只看数量。
A 的预写差异仅为 lm-eval 与 HarmBench 的初始化 L1 `exec.profile_detection_mismatch`：
PASS→SKIPPED INFO、上述固定 message、pass−1/skipped+1，并按旧排序重排。
它们当前检测与声明可能已构成输入特定充分证据，故这里是政策保守成本，不是声称它们必有隐藏违规。
五项目 L0 全部保持，另三个 L1 保持；Git、安全 finding、所有原 failure/evidence/hints/profiles/diagnostics 不变。
这些是 **DESIGN_EXPECTATION_NOT_EXECUTED**，不是新 gold、不是 P-B 验收。

| Writer / reader / 消费者 | A 的合同 |
|---|---|
| 旧 audit1 → 新 reader | 原字节、状态和历史解释保留，不回写为新政策结果 |
| 新 audit1 → 旧 reader | 既有 skipped/INFO 字段可读取；某些用户的 PASS/skipped 计数和顺序会变化 |
| manifest1 / lock1 / run1、run2 / export | schema 不变，不新增覆盖字段或迁移；新 export 内嵌 audit 可反映 A 的新状态 |
| audit / init / export 消费 | init 默认 profiles 选择不变；audit 与 export 使用新规则结果，R07-B stderr 保持 |
| suppression / explicit field PASS / generated rules | 保持现合同，不沿用全局扫描 gate |
| 历史 GPU、H2、judge、discover 和五项目 gold | 保留原候选和原字节；不因本提案重跑或重新归属 |

本次不修改 redaction、schema、profile、依赖、发布版本；不运行 paid/GPU/network validation。
当前原始 metadata 缺口与 HF 403 仍按[先行补验报告](../../../../dogfooding/2026-10-20-validation-followup/README.md)记录，
既有 R06-B 产品验收见[报告](../../../../dogfooding/2026-10-20-r06b/README.md)。

## 5. 审阅决定、后续实施和验证

待裁决的问题是：**是否接受 A 的精确局部政策、规范 patch 和 D-41 engine patch，并在此范围实施 P-B？**
这不是对 R07-C 其他分支、schema 或未来 B 的批准。
[完整 spec issue 草稿](spec-issue-draft.md)供维护者使用；本次不向 GitHub 发 issue/comment。
依据是执行总则 §5.8–5.9 和 R07-C §5 的逐项决定要求；D-41 明确要求 engine 维护者审阅。

接受后 P-B 的精确文件范围是上述五个源码、规范、CHANGELOG，以及现有
`tests/unit/core/test_pyscan.py`、`test_engine.py`、`tests/unit/rules/test_env.py`、`test_exec.py`、
相关 `tests/unit/cli/test_audit.py` / `test_export.py`；以上测试文件已核对存在。
必要 fixture 只新增独立合成反例，不自动刷新历史 gold/snapshots。
若需要超出上述 product 或 schema 范围，先补充材料；不借本次决定扩大。

P-B 必须先证明 RED，再 focused GREEN、完整 final quality、redaction/security、schema/generated freshness、
五项目 fresh Gate A 及受影响 L1/export/threshold/determinism 验收，最后提交推送并核对精确 HEAD 的 CI。
本任务不改变推理/训练、Hub 解析、judge 或 discover transport；这些 Gate B 不适用，不申请新预算。
本次 P-A 是纯文档和未应用 patch：执行内容、链接、源码身份、patch applicability、独立复核和保密检查；
按 validation workflow 将本地产品 full quality / Gate A 标为 NOT_APPLICABLE，不能借旧证据写成 PASS。
