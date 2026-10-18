# R08-A：judge 直接参数叶子的窄范围政策提案

状态：**PROPOSED — 审阅材料；尚未批准或应用**。日期：2026-10-18。
本提案的行为补丁均未应用；当前 judge 直接 max_tokens/temperature 仍为 MEDIUM。
本目录新增审阅文档、patch 和复现摘要；主线程另行维护工作流文档与 CHANGELOG。
P-A 材料交付不等于 P-B 实施完成，产品政策、规格、profiles、测试、gold、版本与依赖保持现状。

## 1. 来源、当前合同与决定状态

依据 [05 §2–3](../../05_Policy_and_Compatibility.md)、[规格 §18](../../../01_specification.md#18-diff-semantics-m6)、
[D-28 / D-39 / D-41](../../../00_architecture_and_decisions.md)、[验证流程](../../../validation-workflow-2026-10-13.md)
和既有 [Issue #9](https://github.com/EnumaElish123/ReproLLM/issues/9)。
原 UX3-T02 要求先审议窄政策；执行后续任务的概括授权没有自动批准本政策。
2026-10-18 通过公开 GitHub API 只读核对该 issue 及 comments endpoint：issue 为 open，
`updated_at=2026-10-02T15:31:06Z`，评论数为 0，未发现新增批准决定。见
[在线核对摘要](online-review.json)。没有发评论、重复建 issue 或写入外部服务。
本提案的裁决仍为待定，见 [decision.json](decision.json)。
当前候选及相关文件原始 SHA-256 见 [本地复现](current-resolver-evidence.json)。
`severity.py::matches` 使用 `[^.]+` 表示一个 segment；resolver 把已解析 profile 的
overrides 放在默认表前，再按 first-match 取值。当前默认表与规格 §18.2 一致：
`evaluation.judge.*: HIGH` 不覆盖 `evaluation.judge.params.max_tokens`。
当前实现遵循现行规格，改动须经过政策裁决。
`llm_judge.yaml` 与 `judge_only.yaml` 也只有现有的 `evaluation.judge.*: HIGH`。
本提案保留这些文件和 profile loader 的字节及优先级。父 profile 新增宽泛 params
override 可能先于子 profile 精确 LOW/NONE 命中，因此推荐把新行放在默认表。
真实案例来自 [val §8.4](../../../../../val.md#84-approved-deepseekfastchat-supplementary-judge-2026-09-27)：
formal FastChat/DeepSeek cap 256→384 历史叶子为 MEDIUM，独立 config hash 为 HIGH。
当前 stdlib CLI 复现也观察到目标 MEDIUM，证明该 HIGH config hash 不能证明叶子政策正确。

## 2. 精确 before / after 与推荐选择

推荐 A：仅在默认表 `evaluation.judge.*` 之前增加一行：

```yaml
- { path: "evaluation.judge.params.*", severity: HIGH }
```

`*`、first-match、profile 解析顺序、CLI flags 和默认 fail-on 行为保持现有合同。
新增行匹配一个直接 segment；它不判断该 segment 的值类型，也不会递归提升子路径。
当前 State flatten 产生的直接叶子适用；本任务不更改 flatten。

| 路径或场景 | 当前 | 接受并实施 A 后 |
|---|---|---|
| `evaluation.judge.params.max_tokens` 256→384 | MEDIUM | HIGH |
| `evaluation.judge.params.temperature` 0→0.2 | MEDIUM | HIGH |
| 任意其他直接 params 叶子，如 `vendor_option` | MEDIUM | HIGH |
| 上述直接叶子的 added / removed | MEDIUM | HIGH |
| `evaluation.judge.params.nested.x` | MEDIUM | MEDIUM |
| `evaluation.judge.model_ref` / `repetitions` | HIGH | HIGH |
| `privacy.mechanism.params.target_epsilon` | MEDIUM | MEDIUM |
| `training.params.custom_option` | MEDIUM | MEDIUM |
| 用户精确 override 为 LOW / NONE | LOW / NONE | LOW / NONE |
| 用户自行提供且先命中的宽泛 override | 按现有 first-match | 按现有 first-match |

影响的是 DiffChange 的 severity、完整 summary、文本分组/结论以及显式 `--fail-on` 的退出码。
没有 audit finding、rule ID、audit severity 或 audit 默认退出门槛变化。
对仅有该目标 HIGH、argv MEDIUM、其余 NONE 的合成 CLI pair：

| 命令/输出 | 当前 | 实施 A 后 |
|---|---|---|
| `diff A B --format json`，不传 `--fail-on` | exit 0，目标 MEDIUM | exit 0，目标 HIGH |
| `diff A B --fail-on HIGH` | exit 0 | exit 1 |
| 上述命令再加 `--min-severity HIGH` | changes 空，完整 summary 保留 | changes 仅含目标，完整 summary 保留 |
| 精确 LOW/NONE override 后，`--fail-on HIGH` | exit 0 | exit 0；argv 仍为 MEDIUM |
| `diff A A --fail-on LOW` | exit 0，changes 空 | 相同 |

示例只描述目标并省略 note；原始值、来源与 recorder/pre_child、child unverified 说明保持不变：

```json
{"path":"evaluation.judge.params.max_tokens","status":"changed","a":256,"b":384,"severity":"HIGH"}
```

备选 B：维持 MEDIUM，不产生行为兼容成本，judge 直接参数仍不能独立触发 HIGH gate。
备选 C：只列举 temperature/max_tokens 精确行；vendor 参数继续 MEDIUM，后续逐字段审议。
推荐 A 与 Issue #9 / 05 的窄层级合同一致；递归、privacy/training、父 profile 优先级不在范围。

## 3. 文件清单与未应用草稿

| 草稿 | 拟修改的实际文件 | 精确目的 |
|---|---|---|
| [default-proposed.patch](default-proposed.patch) | `src/reprollm/diff/drift_severity.yaml` | 仅增加一个默认行 |
| [spec-proposed.patch](spec-proposed.patch) | `docs/plan/01_specification.md` §18.1/18.2 | 明确单段、override 和阈值边界，同步表行 |
| [tests-proposed.patch](tests-proposed.patch) | `tests/unit/diff/test_severity.py` | 20 项窄 resolver 回归；CLI 回归的后续目标为现有 `tests/unit/cli/test_diff.py`，设计见 §5 |
| [changelog-proposed.patch](changelog-proposed.patch) | `CHANGELOG.md` Unreleased/Fixed | 说明默认 severity 与显式 HIGH 退出行为变化 |
| [gold-amendment-proposed.patch](gold-amendment-proposed.patch) | `val.md` 新增前瞻性 §8.4.1 | 经独立审阅后才纳入；历史原文保留 |

patch 检查不表示批准或产品回归通过。不触碰 redaction/engine/schema 等 D-41 文件、
`severity.py`、loader/profiles、依赖/版本、发布 workflow 或历史 run；任何扩展另行审议。

## 4. 兼容矩阵与历史 gold

| reader / writer / 数据组合 | 行为 |
|---|---|
| 旧程序读取旧 run1/run2、lock1、manifest1 | 保持旧政策和原有支持范围 |
| 新程序读取已有且其本身支持的 run1/run2、lock1、manifest1 | 原始值/来源不变；重新 diff 的直接叶子按新默认 HIGH |
| 旧程序读取新程序生成的 diff_report1 | 字段/枚举不变，HIGH 已为合法值；不赋予旧程序读取其原本不支持 run2 的能力 |
| 新程序读取历史 diff_report1 或历史报告 | 原记录作为历史证据保留，不重写 MEDIUM 为 HIGH |
| 用户精确 LOW/NONE、自定义 first-match overrides | 继续按当前 profile 合并与匹配顺序生效 |

本方案改变新计算报告的默认政策，没有持久化 schema 变更或强制数据迁移，故不提出 schema
版本 bump。实施时 CHANGELOG 必须明确显式 HIGH gate 可从 0 变 1；版本和发布决定另行处理。
旧新结果比较必须记录 ReproLLM 版本/commit 和是否适用 R08-A，不能要求历史报告字节一致。
五项目独立预期如下；本轮仅列预期，没有重跑或更新 gold：

| val 固定项目 | Gate A 完整 audit/init 等非 diff 预期 | 既有 paired diff 的前瞻性差异 |
|---|---|---|
| lm-evaluation-harness | finding/rule/profile/hint/path/diagnostic 不变 | `generation.max_tokens` 保持 HIGH；无新增 judge 直接叶子时逐路径不变 |
| FastChat | 同上，保留固定 pin 与完整 finding 集 | native answer cap 保持 HIGH；formal paid judge cap 256→384 才由 MEDIUM→HIGH，其余路径逐项保留 |
| LlamaFactory | 同上 | 原训练/LoRA cap 路径不在新 pattern 下，逐路径不变 |
| HarmBench | 同上，包含已接受的嵌套依赖 gold | 原 native generation cap 保持 HIGH，其余逐路径不变 |
| llm-dp-finetune | 同上 | epsilon 8→4 继续 MEDIUM、config hash HIGH；R08-B 未决 |

上述不变性依据新 pattern 仅覆盖 `evaluation.judge.params.<一个segment>`，不以当前输出充当
新 oracle。实际输入若出现该集合内额外路径，应逐路径列出来源和独立预期再审阅，不能静默
扩大此表。本轮不移动五个 pins，不改变原始 manifest/driver/input hash。
formal judge 的历史 MEDIUM + config HIGH、clean commit MEDIUM 和其余真实 delta 完整保留。
只有接受并实施后的新回放才按拟定 §8.4.1 比较 cap HIGH；config HIGH 仍须独立说明。
原正式输入 bundle、provider 凭据和新批准预算尚未 provision，因此 VAL-R02/formal paid
replay 仍为 BLOCKED。本地 stdlib、内存表比较或 mock 不关闭 Gate B；VAL-R01/03 也未改变。

## 5. 独立回归矩阵与执行顺序

| ID | 独立输入与预期 | 草稿位置 / 状态 |
|---|---|---|
| T01 | max_tokens/temperature/vendor_option × changed/added/removed，默认 HIGH | tests patch；未应用/未执行 |
| T02 | nested.x、privacy epsilon、training nested 仍 MEDIUM；legacy judge model_ref HIGH | tests patch；未应用/未执行 |
| T03 | 精确 LOW/NONE × changed/added/removed 优先于默认；新行唯一且在宽 judge 行前 | tests patch；未应用/未执行 |
| T04 | 真实 `run -- python -c <stdlib argparse> --cap` A/B；固定 manifest，无 config binding，无 tracked 变化 | CLI 设计；当前政策另有 2-run 实证 |
| T05 | CLI cap changed/added/removed × default/LOW/NONE × 继承 judge_only/llm_judge；目标独立决定 HIGH gate | CLI 设计；未实现/未执行 |
| T06 | 完整非 NONE 路径仅目标（若非 NONE）与 argv MEDIUM；任何 config/code HIGH 都使测试失败 | CLI 设计；当前 changed/default 已实证 |
| T07 | JSON 同输入字节一致、HIGH 过滤保留完整 summary、隐藏 MEDIUM 仍触发 MEDIUM gate、self-diff 空 | CLI 设计；当前 repeat/HIGH-filter/self 已实证，隐藏 MEDIUM 留待实施回归 |
| T08 | actual profile/default/resolver/schema/dependency 原始文件 hash 不变 | [文档检查摘要](review-validation.json) |
| T09 | full quality + 五项目 fresh Gate A + 受影响 diff 扩展；不可用 formal 输入/资源明确 BLOCKED | 批准后的 P-B；本轮 NOT_APPLICABLE/未执行 |

CLI 设计要求用现有 `test_diff.py` / `test_run.py` fixture：通过 `proc.run_cmd` stub 固定
clean Git，硬件 unavailable，沿用无网络 guard，并运行真实 stdlib argparse child。
manifest/profile 在 A/B 前固定；不改 config、源码或 Git commit。精确 LOW/NONE 分别继承
judge_only/llm_judge；断言全部非 NONE 路径、目标 status/value、阈值、过滤及 self-diff。
这些 CLI 测试尚未编写，须在 P-B 先补成真实 RED；不将 unit draft 冒充其覆盖。
当前实证为真实 clean Git、固定 manifest/inline prompt、无 captured config：child 实际
argparse 消费 cap。2 run + pair/repeat/filter/self 共 6 条产品命令均 exit 0，墙钟 0.855 秒；
目标 MEDIUM、argv MEDIUM，没有其他 HIGH。硬件 capture 为 unavailable；公开摘要无原始
临时路径、机器身份或日志。sandbox 拒绝和无效合成 fixture 两次准备失败另列，不计成功。
批准后先补齐 CLI 回归并取得真实 RED，再实施默认表/spec/CHANGELOG 取得 GREEN，审阅
gold supplement，执行一次完整质量门与适用五项目检查。本轮不宣称这些未来门已通过。

## 6. 可直接裁决的问题

请选择 A（推荐）：接受本文件中一个默认 pattern 的精确 before/after、现有 override 顺序、
无 schema/版本变更、历史保留和前瞻性 gold 补充，并授权单独 P-B 实施与相应验证；
或选择 B 维持 MEDIUM；或选择 C 两个精确字段并据此收窄 patch。
接受 A 不授权递归匹配、privacy/training、profile 优先级变化、付费资源、版本发布或新 pins。
决定须记录原话、来源/日期、接受范围及 patch hash；目前批准字段为 null，产品合同未改。
